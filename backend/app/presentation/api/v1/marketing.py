from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from functools import lru_cache
from typing import Annotated
import mimetypes
import cgi
import httpx
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
    UploadFile,
)
from fastapi import File as FastAPIFile
from fastapi import Form
from starlette.responses import StreamingResponse
from openai import OpenAI

from chatkit.server import NonStreamingResult, StreamingResult

from app.infrastructure.chatkit.context import MarketingRequestContext
from app.infrastructure.chatkit.model_assets import (
    list_model_assets,
    upsert_model_asset,
    get_model_asset,
    delete_model_asset,
)
from app.infrastructure.chatkit.marketing_server import get_marketing_chat_server
from app.infrastructure.marketing.agent_service import get_marketing_agent_service
from app.infrastructure.chatkit.supabase_store import SupabaseChatStore, PermissionDeniedError
from app.infrastructure.config.settings import get_settings
from app.infrastructure.supabase.client import get_supabase
from app.infrastructure.security.marketing_token_service import (
    MarketingTokenError,
    MarketingTokenService,
)
from pydantic import BaseModel


class ChatStreamRequest(BaseModel):
    """Request body for the native SSE chat endpoint."""
    message: str
    conversation_id: str | None = None
    context_items: list[dict] | None = None
    model_asset_id: str | None = None

router = APIRouter(prefix="/marketing", tags=["marketing"])
logger = logging.getLogger(__name__)
ATTACHMENT_BUCKET = "marketing-attachments"


@lru_cache(maxsize=1)
def _token_service() -> MarketingTokenService:
    settings = get_settings()
    return MarketingTokenService(settings.marketing_chatkit_token_secret)


def _build_signed_download_url(
    *,
    file_id: str,
    container_id: str | None,
    context: MarketingRequestContext,
) -> str:
    """
    Build a signed relative URL for downloading files via the frontend proxy.
    """
    svc = _token_service()
    settings = get_settings()
    now = int(time.time())
    ttl = max(settings.marketing_chatkit_token_ttl, 60)
    payload = {
        "sub": context.user_id,
        "email": context.user_email,
        "name": context.user_name,
        "iat": now,
        "exp": now + ttl,
        "file_id": file_id,
    }
    if container_id:
        payload["container_id"] = container_id
    token = svc.sign(payload)
    query = f"token={token}"
    if container_id:
        query += f"&container_id={container_id}"
    encoded_file = quote(file_id, safe="")
    return f"/api/marketing/files/{encoded_file}?{query}"


async def require_marketing_context(
    authorization: Annotated[str | None, Header(convert_underscores=False)] = None,
    marketing_client_secret: Annotated[
        str | None, Header(alias="x-marketing-client-secret", convert_underscores=False)
    ] = None,
    model_asset_id: Annotated[
        str | None, Header(alias="x-model-asset-id", convert_underscores=False)
    ] = None,
) -> MarketingRequestContext:
    token: str | None = None

    if marketing_client_secret:
        token = marketing_client_secret.strip()
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing marketing client token",
        )
    try:
        claims = _token_service().verify(token)
    except MarketingTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return MarketingRequestContext(
        user_id=claims.sub,
        user_email=claims.email,
        user_name=claims.name,
        model_asset_id=model_asset_id,
    )


@router.api_route("/attachments/{attachment_id}/upload", methods=["PUT", "POST", "OPTIONS"])
async def upload_marketing_attachment(
    attachment_id: str,
    request: Request,
    token: str | None = Query(default=None),
    thread_id: str | None = Query(default=None),
    authorization: Annotated[str | None, Header(convert_underscores=False)] = None,
    marketing_client_secret: Annotated[
        str | None, Header(alias="x-marketing-client-secret", convert_underscores=False)
    ] = None,
):
    """
    Two-phase upload target used by ChatKit AttachmentStore.
    Accepts a short-lived token (preferred) or the standard marketing client secret.
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        logger.info(
            "CORS preflight request: attachment_id=%s origin=%s",
            attachment_id,
            request.headers.get("origin"),
        )
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
                "Access-Control-Allow-Methods": "POST, PUT, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "600",
            },
        )

    context: MarketingRequestContext | None = None
    attachment_meta: dict = {}

    # 1) Try standard header-based auth (used when custom fetch forwards headers)
    if marketing_client_secret or authorization:
        try:
            context = await require_marketing_context(
                authorization=authorization,
                marketing_client_secret=marketing_client_secret,
                model_asset_id=None,
            )
        except HTTPException:
            context = None

    # 2) Fallback to token-based auth
    if context is None and token:
        try:
            claims = _token_service().verify(token)
            attachment_meta = (claims.extra or {}).get("attachment", {}) if claims.extra else {}
            if attachment_meta.get("id") and attachment_meta["id"] != attachment_id:
                raise HTTPException(status_code=403, detail="Attachment token mismatch")
            context = MarketingRequestContext(
                user_id=claims.sub,
                user_email=claims.email,
                user_name=claims.name,
            )
        except MarketingTokenError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    if context is None:
        raise HTTPException(status_code=401, detail="Missing marketing client token")

    settings = get_settings()
    sb = get_supabase()
    _ensure_bucket_exists(sb, ATTACHMENT_BUCKET)
    content_type_header = request.headers.get("content-type") or ""
    body: bytes
    header_filename = None
    cd_filename = None

    logger.info(
        "Upload attachment request: id=%s content_type=%s content_length=%s",
        attachment_id,
        content_type_header,
        request.headers.get("content-length"),
    )

    # ChatKit two-phase upload sends raw bytes (not multipart) with content-type: application/octet-stream
    # but in some cases can be multipart; handle both.
    body = b""
    mime_type = "application/octet-stream"

    if "multipart/form-data" in content_type_header.lower():
        logger.info("Processing multipart/form-data upload")
        form = await request.form()
        upload_file: UploadFile | None = None

        # Debug: log all form items with their types
        for key, value in form.multi_items():
            logger.info(f"Form item: key={key}, type={type(value).__name__}")
            # Check if it's an UploadFile by duck typing (has read method)
            if hasattr(value, 'read') and key == 'file':
                upload_file = value
                break

        if upload_file:
            # Always treat it as an UploadFile-like object
            body = await upload_file.read()
            header_filename = getattr(upload_file, 'filename', None)
            # Get mime_type from upload_file first, then from token metadata
            upload_content_type = getattr(upload_file, 'content_type', None)
            mime_type = upload_content_type or attachment_meta.get("mime_type") or "application/octet-stream"
            logger.info("Found file in multipart: filename=%s size=%s mime=%s", header_filename, len(body), mime_type)
        else:
            # No file found in multipart request
            logger.error("No file found in multipart request, form keys: %s", list(form.keys()))
            raise HTTPException(status_code=400, detail="No file found in multipart upload")
    else:
        logger.info("Processing raw body upload")
        body = await request.body()
        mime_type = attachment_meta.get("mime_type") or request.headers.get("content-type") or "application/octet-stream"
        logger.info("Received raw body: size=%s mime=%s", len(body), mime_type)

    if not body:
        raise HTTPException(status_code=400, detail="Empty upload body")

    # --- Determine original filename as best as possible ---
    header_filename = (
        header_filename
        or request.headers.get("x-filename")
        or request.headers.get("x-file-name")
        or request.headers.get("X-Filename")
    )
    # Content-Disposition: attachment; filename="..." or filename*=utf-8''...
    cd = request.headers.get("content-disposition")
    if cd:
        _, cd_params = cgi.parse_header(cd)
        cd_filename = cd_params.get("filename") or cd_params.get("filename*")

    filename = attachment_meta.get("name") or header_filename or cd_filename or attachment_id

    size_hint = attachment_meta.get("size")
    if size_hint and len(body) != int(size_hint):
        logger.warning(
            "Uploaded size mismatch for attachment %s (expected=%s, actual=%s)",
            attachment_id,
            size_hint,
            len(body),
        )

    # Ensure file has proper extension
    import os
    base, ext = os.path.splitext(filename)

    # If no extension or filename is just the attachment_id, add extension from MIME type
    if not ext or filename == attachment_id:
        ext_from_mime = mimetypes.guess_extension(mime_type.split(";")[0].strip()) or ""
        if ext_from_mime:
            # Use the base name if available, otherwise use attachment_id
            candidate_name = f"{base or attachment_id}{ext_from_mime}"
        else:
            candidate_name = filename
    else:
        candidate_name = filename

    safe_name = _safe_filename(candidate_name)
    logger.info(
        "Attachment upload: raw_filename=%s header_filename=%s cd_filename=%s chosen=%s mime=%s size=%s",
        filename,
        header_filename,
        cd_filename,
        safe_name,
        mime_type,
        len(body),
    )
    storage_path = f"attachments/{attachment_id}/{safe_name}"
    bucket = sb.storage.from_(ATTACHMENT_BUCKET)

    try:
        bucket.upload(
            path=storage_path,
            file=body,
            file_options={"content-type": mime_type, "x-upsert": "true"},
        )
    except Exception as exc:
        logger.exception("Failed to upload attachment to Supabase Storage")
        raise HTTPException(status_code=500, detail="Failed to store attachment") from exc

    # Upload to OpenAI Files so Code Interpreter can access it
    client = OpenAI(api_key=settings.openai_api_key)
    try:
        # Responses/Agents では assistants 用のファイルとしてアップロードする
        openai_file = client.files.create(
            purpose="assistants",
            file=(safe_name, body),
        )
    except Exception as exc:
        logger.exception("Failed to upload attachment to OpenAI")
        raise HTTPException(status_code=502, detail="Failed to upload to OpenAI") from exc

    storage_metadata = {
        "id": attachment_id,
        "openai_file_id": getattr(openai_file, "id", None),
        "openai_file_name": safe_name,
        "name": safe_name,
        "mime_type": mime_type,
        "size": len(body),
        "storage_path": storage_path,
        "thread_id": thread_id or attachment_meta.get("thread_id"),
        "uploaded_by": context.user_email,
    }

    try:
        bucket.upload(
            path=f"attachments/{attachment_id}/meta.json",
            file=json.dumps(storage_metadata).encode("utf-8"),
            file_options={"content-type": "application/json", "x-upsert": "true"},
        )
    except Exception:
        logger.exception("Failed to cache attachment metadata for %s", attachment_id)

    # Persist DB row if thread_id is available (FK constraint)
    conversation_id = storage_metadata.get("thread_id")
    if conversation_id:
        try:
            sb.table("marketing_attachments").upsert(
                {
                    "id": attachment_id,
                    "conversation_id": conversation_id,
                    "owner_email": context.user_email,
                    "filename": safe_name,
                    "mime_type": mime_type,
                    "size_bytes": len(body),
                    "storage_metadata": storage_metadata,
                }
            ).execute()
        except Exception:
            logger.exception("Failed to upsert attachment row (id=%s thread=%s)", attachment_id, conversation_id)

    return {"id": attachment_id, "file_id": storage_metadata.get("openai_file_id")}


@router.get("/files/{file_id}")
async def download_openai_file(
    file_id: str,
    container_id: str | None = Query(default=None),
    filename: str | None = Query(default=None),
    token: str | None = Query(default=None),
    marketing_client_secret: Annotated[
        str | None, Header(alias="x-marketing-client-secret", convert_underscores=False)
    ] = None,
    authorization: Annotated[str | None, Header(convert_underscores=False)] = None,
):
    """
    Proxy downloads for files produced by Code Interpreter / Responses API.
    Caches the payload in Supabase Storage to avoid repeated egress.

    AuthN:
      - Preferred: query param `token` signed with MARKETING_CHATKIT_TOKEN_SECRET
      - Fallback: x-marketing-client-secret header or Bearer token (same as chat)

    For Code Interpreter generated files, container_id should be provided.
    For regular uploaded files, container_id can be omitted.
    """
    settings = get_settings()
    sb = get_supabase()
    bucket = sb.storage.from_(ATTACHMENT_BUCKET)
    storage_path = f"openai_cache/{file_id}"

    resolved_filename = filename or f"{file_id}.bin"

    # Serve cached copy if available
    try:
        cached = bucket.download(storage_path)
        if cached:
            headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
            return Response(content=cached, media_type="application/octet-stream", headers=headers)
    except Exception:
        logger.info("Cache miss for generated file %s", file_id)

    file_bytes: bytes
    meta_filename: str | None = None

    # --- AuthN: token or header ---
    context: MarketingRequestContext | None = None
    token_service = _token_service()

    if token:
        try:
            claims = token_service.verify(token)
            extra = claims.extra or {}
            token_file_id = extra.get("file_id")
            token_container_id = extra.get("container_id")
            if token_file_id and token_file_id != file_id:
                raise HTTPException(status_code=403, detail="Token file mismatch")
            if token_container_id and container_id and token_container_id != container_id:
                raise HTTPException(status_code=403, detail="Token container mismatch")
            context = MarketingRequestContext(
                user_id=claims.sub,
                user_email=claims.email,
                user_name=claims.name,
            )
        except MarketingTokenError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    if context is None:
        # Fallback to header-based auth
        try:
            context = await require_marketing_context(
                authorization=authorization,
                marketing_client_secret=marketing_client_secret,
                model_asset_id=None,
            )
        except HTTPException as exc:
            raise exc

    # Guard against missing container_id when cfile is requested
    if file_id.startswith("cfile") and not container_id:
        raise HTTPException(
            status_code=400,
            detail="container_id is required to download Code Interpreter files",
        )

    try:
        if container_id and file_id.startswith("cfile"):
            # Use Container Files API via raw HTTP (not yet supported in SDK)
            headers = {
                "Authorization": f"Bearer {settings.openai_api_key}",
                "OpenAI-Beta": "containers=v1",
            }
            base_url = "https://api.openai.com/v1"
            async with httpx.AsyncClient(timeout=60) as client:
                content_url = f"{base_url}/containers/{container_id}/files/{file_id}/content"
                resp = await client.get(content_url, headers=headers)
                if resp.status_code != 200:
                    logger.error(
                        "Failed to download container file %s (status=%s): %s",
                        file_id,
                        resp.status_code,
                        resp.text,
                    )
                    raise HTTPException(status_code=404, detail="File not found")

                file_bytes = resp.content

                meta_url = f"{base_url}/containers/{container_id}/files/{file_id}"
                meta_resp = await client.get(meta_url, headers=headers)
                if meta_resp.status_code == 200:
                    meta = meta_resp.json()
                    meta_filename = meta.get("filename") or meta.get("name") or meta_filename
        else:
            # Use regular Files API for uploads or fine-tuning artifacts
            logger.info(f"Using regular files API for: file_id={file_id}")
            client = OpenAI(api_key=settings.openai_api_key)
            content_stream = client.files.content(file_id)
            file_bytes = content_stream.read()
            file_info = client.files.retrieve(file_id)
            meta_filename = getattr(file_info, "filename", None) or meta_filename

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to download file {file_id}")
        raise HTTPException(status_code=404, detail=f"File not found or expired: {exc}") from exc

    # Resolve best filename (priority: query > OpenAI meta > DB > default)
    if filename:
        resolved_filename = filename
    elif meta_filename:
        resolved_filename = meta_filename
    else:
        try:
            row = (
                sb.table("marketing_attachments")
                .select("filename")
                .eq("id", file_id)
                .limit(1)
                .execute()
                .data
            )
            if row and row[0].get("filename"):
                resolved_filename = row[0]["filename"]
        except Exception:
            logger.info("Filename lookup in marketing_attachments failed for %s", file_id)

    # Cache the file
    try:
        bucket.upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "application/octet-stream", "x-upsert": "true"},
        )
    except Exception:
        logger.exception("Failed to cache OpenAI file %s", file_id)

    headers = {"Content-Disposition": f'attachment; filename="{resolved_filename}"'}
    return Response(content=file_bytes, media_type="application/octet-stream", headers=headers)


@router.get("/threads/{thread_id}/attachments")
async def list_marketing_attachments(
    thread_id: str,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """
    Return container/file attachment metadata for a thread so the frontend can render download buttons.
    """
    sb = get_supabase()
    try:
        rows = (
            sb.table("marketing_messages")
            .select("id, role, attachments, created_at")
            .eq("conversation_id", thread_id)
            .order("created_at", desc=True)
            .limit(80)
            .execute()
            .data
        )
    except Exception as exc:
        logger.exception("Failed to load attachments for thread %s", thread_id)
        raise HTTPException(status_code=500, detail="failed to load attachments") from exc

    attachments: list[dict] = []
    for row in rows or []:
        att_list = row.get("attachments") or []
        if not isinstance(att_list, list):
            continue
        for att in att_list:
            file_id = att.get("file_id")
            if not file_id:
                continue
            container_id = att.get("container_id")
            download_url = _build_signed_download_url(
                file_id=file_id,
                container_id=container_id,
                context=context,
            )
            attachments.append(
                {
                    "message_id": row.get("id"),
                    "file_id": file_id,
                    "container_id": container_id,
                    "filename": att.get("filename"),
                    "download_url": download_url,
                    "created_at": row.get("created_at"),
                }
            )

    # Sort newest first by message timestamp
    attachments.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return {"attachments": attachments}


def _safe_filename(value: str) -> str:
    """
    Sanitize a filename for Supabase Storage (ASCII-only).
    - Keeps only ASCII letters/digits, hyphens, underscores.
    - Replaces other chars with underscore.
    - Ensures there is always a base name (`file`) and keeps the original extension (lowercased).
    """
    import os
    import unicodedata

    if not value:
        return "file"

    # Strip path parts if any
    name = value.split("/")[-1].split("\\")[-1]
    base, ext = os.path.splitext(name)

    def _clean(s: str) -> str:
        # Normalize unicode characters to ASCII equivalents where possible
        try:
            s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
        except:
            pass

        cleaned = []
        for ch in s:
            # Only allow ASCII alphanumeric, hyphen, and underscore
            if ch.isascii() and (ch.isalnum() or ch in ("-", "_")):
                cleaned.append(ch)
            elif ch == ' ':
                cleaned.append('_')
            # Skip non-ASCII characters

        result = "".join(cleaned).strip("_")
        return result if result else "file"

    base_clean = _clean(base)
    ext_clean = ext.lower() if ext else ""

    return base_clean + ext_clean


def _ensure_bucket_exists(sb, bucket: str) -> None:
    try:
        info = sb.storage.get_bucket(bucket)
        if info:
            return
    except Exception:
        logger.info("Attachment bucket %s not found, creating...", bucket)
    try:
        # storage3 Sync API signature: create_bucket(id, name=None, **options)
        sb.storage.create_bucket(bucket)
    except Exception:
        # If it already exists or creation forbidden, log but continue
        logger.exception("Failed to create or verify attachment bucket %s", bucket)


@router.post("/chatkit")
async def marketing_chatkit(
    request: Request,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    server = get_marketing_chat_server()
    body = await request.body()
    result = await server.process(body, context=context)
    if isinstance(result, StreamingResult):
        return StreamingResponse(
            result,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx/proxy buffering
            },
        )
    if isinstance(result, NonStreamingResult):
        return Response(
            content=result.json,
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unhandled ChatKit response",
    )


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    body: ChatStreamRequest,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """
    Native SSE streaming endpoint for marketing AI chat.

    Replaces ChatKit with direct OpenAI Agents SDK streaming.
    Returns SSE events in the format:
    - text_delta: Incremental text content
    - tool_call: Tool invocation start
    - tool_result: Tool execution result
    - reasoning: Agent reasoning/thinking
    - sub_agent_event: Sub-agent activity (detailed)
    - progress: Keepalive progress indicator
    - done: Stream completion
    - error: Error event
    """
    from app.infrastructure.chatkit.model_assets import get_model_asset
    from app.infrastructure.chatkit.supabase_store import generate_thread_title
    import uuid

    agent_service = get_marketing_agent_service()
    sb = get_supabase()

    # Load model asset if specified
    model_asset = None
    asset_id = body.model_asset_id or context.model_asset_id
    if asset_id:
        model_asset = get_model_asset(asset_id, context=context)

    # Determine or create conversation ID
    conversation_id = body.conversation_id or str(uuid.uuid4())
    is_new_conversation = not body.conversation_id

    async def event_generator():
        # --- DB: Save user message before streaming ---
        user_msg_id = str(uuid.uuid4())
        try:
            # Ensure conversation exists
            if is_new_conversation:
                # Generate title asynchronously
                title = await generate_thread_title(body.message) or "新しい会話"
                sb.table("marketing_conversations").insert({
                    "id": conversation_id,
                    "title": title,
                    "owner_email": context.user_email,
                    "owner_clerk_id": context.user_id,
                    "status": "active",
                    "metadata": {"context_items": body.context_items} if body.context_items else {},
                }).execute()
                logger.info(f"[DB] Created conversation: {conversation_id}")
            else:
                # Update last_message_at for existing conversation
                sb.table("marketing_conversations").update({
                    "last_message_at": datetime.utcnow().isoformat(),
                }).eq("id", conversation_id).execute()

            # Save user message
            sb.table("marketing_messages").insert({
                "id": user_msg_id,
                "conversation_id": conversation_id,
                "role": "user",
                "message_type": "content",
                "content": {"text": body.message},
                "plain_text": body.message,
                "created_by": context.user_email,
            }).execute()
            logger.info(f"[DB] Saved user message: {user_msg_id}")
        except Exception as e:
            logger.exception(f"[DB] Failed to save user message: {e}")
            # Continue streaming even if DB save fails

        # --- Streaming with activity items accumulation ---
        activity_items: list[dict] = []
        full_text_content = ""
        seq = 0
        current_text_id: str | None = None

        try:
            async for event in agent_service.stream_chat(
                user_id=context.user_id,
                user_email=context.user_email,
                conversation_id=conversation_id,
                message=body.message,
                context_items=body.context_items,
                model_asset=model_asset,
            ):
                if await request.is_disconnected():
                    logger.info("Client disconnected during chat stream")
                    break

                event_type = event.get("type")

                # --- Accumulate activity items for DB storage ---
                if event_type == "text_delta":
                    content = event.get("content", "")
                    full_text_content += content
                    if current_text_id is None:
                        current_text_id = str(uuid.uuid4())
                        activity_items.append({
                            "kind": "text",
                            "sequence": seq,
                            "id": current_text_id,
                            "content": content,
                        })
                        seq += 1
                    else:
                        # Update existing text item
                        for item in activity_items:
                            if item.get("id") == current_text_id:
                                item["content"] = item.get("content", "") + content
                                break

                elif event_type == "response_created":
                    current_text_id = None  # Reset for new response

                elif event_type == "tool_call":
                    activity_items.append({
                        "kind": "tool",
                        "sequence": seq,
                        "id": event.get("call_id"),
                        "name": event.get("name"),
                        "call_id": event.get("call_id"),
                        "arguments": event.get("arguments"),
                    })
                    seq += 1

                elif event_type == "tool_result":
                    # Update matching tool item with output (search from end, match call_id + no output)
                    call_id = event.get("call_id")
                    for item in reversed(activity_items):
                        if (
                            item.get("kind") == "tool"
                            and item.get("call_id") == call_id
                            and "output" not in item
                        ):
                            item["output"] = event.get("output", "(completed)")
                            break

                elif event_type == "reasoning":
                    activity_items.append({
                        "kind": "reasoning",
                        "sequence": seq,
                        "id": str(uuid.uuid4()),
                        "content": event.get("content"),
                    })
                    seq += 1

                elif event_type == "sub_agent_event":
                    activity_items.append({
                        "kind": "sub_agent",
                        "sequence": seq,
                        "id": str(uuid.uuid4()),
                        "agent": event.get("agent"),
                        "event_type": event.get("event_type"),
                        "data": event.get("data"),
                    })
                    seq += 1

                elif event_type == "_context_items":
                    # Save context_items to conversation metadata
                    try:
                        sb.table("marketing_conversations").update({
                            "metadata": {"context_items": event.get("items")},
                        }).eq("id", conversation_id).execute()
                        logger.info(f"[DB] Saved context_items for: {conversation_id}")
                    except Exception as e:
                        logger.warning(f"[DB] Failed to save context_items: {e}")
                    # Send to client so frontend can maintain context for next turn
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    continue

                # Translate reasoning summary from English to Japanese
                if event.get("_needs_translation"):
                    try:
                        if event.get("content"):
                            translated = await agent_service._translate_to_japanese(
                                event["content"]
                            )
                            event["content"] = translated
                        elif event.get("data", {}).get("content"):
                            translated = await agent_service._translate_to_japanese(
                                event["data"]["content"]
                            )
                            event["data"]["content"] = translated
                    except Exception as te:
                        logger.warning(f"Translation failed: {te}")

                # Remove internal flags before sending
                event.pop("_needs_translation", None)

                # Override conversation_id in done event
                if event_type == "done":
                    event["conversation_id"] = conversation_id

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # --- Safety net: Mark any unfinished tools as completed ---
            for item in activity_items:
                if item.get("kind") == "tool" and "output" not in item:
                    item["output"] = "(completed)"
                elif item.get("kind") == "sub_agent" and item.get("is_running"):
                    item["is_running"] = False

            # --- DB: Save assistant message with activity_items ---
            if full_text_content or activity_items:
                assistant_msg_id = str(uuid.uuid4())
                try:
                    sb.table("marketing_messages").insert({
                        "id": assistant_msg_id,
                        "conversation_id": conversation_id,
                        "role": "assistant",
                        "message_type": "content",
                        "content": {
                            "text": full_text_content,
                            "activity_items": activity_items,
                        },
                        "plain_text": full_text_content[:10000] if full_text_content else None,
                        "created_by": "assistant",
                    }).execute()
                    logger.info(f"[DB] Saved assistant message: {assistant_msg_id}")

                    # Update conversation last_message_at
                    sb.table("marketing_conversations").update({
                        "last_message_at": datetime.utcnow().isoformat(),
                    }).eq("id", conversation_id).execute()
                except Exception as e:
                    logger.exception(f"[DB] Failed to save assistant message: {e}")

        except Exception as e:
            logger.exception("Error in chat stream")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/model-assets")
async def get_model_assets(
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    # context is validated; assets are shared globally
    assets = list_model_assets(context)
    for asset in assets:
        asset["verbosity"] = _normalize_verbosity_to_client(asset.get("verbosity"))
    return {"data": assets}


@router.post("/model-assets")
async def create_or_update_model_asset(
    payload: dict,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    allowed_keys = {
        "id",
        "name",
        "description",
        "base_model",
        "reasoning_effort",
        "verbosity",
        "enable_web_search",
        "enable_code_interpreter",
        "enable_ga4",
        "enable_meta_ads",
        "enable_gsc",
        "enable_ahrefs",
        "enable_wordpress",
        "enable_canvas",
        "enable_zoho_crm",
        "system_prompt_addition",
        "metadata",
        "visibility",
    }
    data = {k: v for k, v in payload.items() if k in allowed_keys}
    if "name" not in data or not data["name"]:
        raise HTTPException(status_code=400, detail="name is required")

    data["verbosity"] = _normalize_verbosity_to_db(data.get("verbosity"))

    visibility = data.get("visibility") or "public"
    if visibility not in ("public", "private"):
        raise HTTPException(status_code=400, detail="visibility must be public|private")
    data["visibility"] = visibility

    reasoning = data.get("reasoning_effort")
    if reasoning and reasoning not in ("low", "medium", "high", "xhigh"):
        raise HTTPException(
            status_code=400,
            detail="reasoning_effort must be low|medium|high|xhigh",
        )

    result = upsert_model_asset(data, context=context)
    result["verbosity"] = _normalize_verbosity_to_client(result.get("verbosity"))
    return {"data": result}


@router.get("/model-assets/{asset_id}")
async def get_model_asset_by_id(
    asset_id: str,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    asset = get_model_asset(asset_id, context=context)
    if not asset:
        raise HTTPException(status_code=404, detail="Model asset not found")
    asset["verbosity"] = _normalize_verbosity_to_client(asset.get("verbosity"))
    return {"data": asset}


@router.put("/model-assets/{asset_id}")
async def update_model_asset(
    asset_id: str,
    payload: dict,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    # Verify asset exists
    existing = get_model_asset(asset_id, context=context)
    if not existing:
        raise HTTPException(status_code=404, detail="Model asset not found")

    # Prevent updating standard preset
    if asset_id == "standard":
        raise HTTPException(status_code=400, detail="Cannot update standard preset")

    allowed_keys = {
        "name",
        "description",
        "base_model",
        "reasoning_effort",
        "verbosity",
        "enable_web_search",
        "enable_code_interpreter",
        "enable_ga4",
        "enable_meta_ads",
        "enable_gsc",
        "enable_ahrefs",
        "enable_wordpress",
        "enable_canvas",
        "enable_zoho_crm",
        "system_prompt_addition",
        "metadata",
        "visibility",
    }
    data = {k: v for k, v in payload.items() if k in allowed_keys}
    data["id"] = asset_id  # Ensure ID is preserved

    if "name" in data and not data["name"]:
        raise HTTPException(status_code=400, detail="name cannot be empty")

    data["verbosity"] = _normalize_verbosity_to_db(data.get("verbosity"))

    visibility = data.get("visibility") or existing.get("visibility") or "public"
    if visibility not in ("public", "private"):
        raise HTTPException(status_code=400, detail="visibility must be public|private")
    data["visibility"] = visibility

    reasoning = data.get("reasoning_effort")
    if reasoning and reasoning not in ("low", "medium", "high", "xhigh"):
        raise HTTPException(
            status_code=400,
            detail="reasoning_effort must be low|medium|high|xhigh",
        )

    result = upsert_model_asset(data, context=context)
    result["verbosity"] = _normalize_verbosity_to_client(result.get("verbosity"))
    return {"data": result}


@router.delete("/model-assets/{asset_id}")
async def delete_model_asset_by_id(
    asset_id: str,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    # Prevent deletion of standard preset
    if asset_id == "standard":
        raise HTTPException(status_code=400, detail="Cannot delete standard preset")

    asset = get_model_asset(asset_id, context=context)
    if not asset:
        raise HTTPException(status_code=404, detail="Model asset not found")

    success = delete_model_asset(asset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model asset not found")

    return {"message": "Model asset deleted successfully"}
def _normalize_verbosity_to_db(value: str | None) -> str | None:
    if value is None:
        return None
    if value in ("low", "medium", "high"):
        return value
    # backward compatibility with older stored values
    if value == "short":
        return "low"
    if value == "long":
        return "high"
    raise HTTPException(status_code=400, detail="verbosity must be low|medium|high")


def _normalize_verbosity_to_client(value: str | None) -> str | None:
    if value is None:
        return None
    if value == "short":
        return "low"
    if value == "long":
        return "high"
    return value


# --- Thread/Conversation Endpoints ---


@router.get("/threads/{thread_id}")
async def get_thread_detail(
    thread_id: str,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """
    Get conversation detail with messages.

    Returns conversation metadata and messages with activity_items for UI restoration.
    """
    sb = get_supabase()

    try:
        # Get conversation
        conv_result = (
            sb.table("marketing_conversations")
            .select("*")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        )
        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conversation = conv_result.data[0]

        # Check access (owner or shared)
        is_owner = conversation.get("owner_email") == context.user_email
        is_shared = conversation.get("metadata", {}).get("is_shared", False)
        if not is_owner and not is_shared:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get messages
        messages_result = (
            sb.table("marketing_messages")
            .select("id, role, message_type, content, plain_text, created_at")
            .eq("conversation_id", thread_id)
            .order("created_at", desc=False)
            .limit(500)
            .execute()
        )

        messages = []
        for row in messages_result.data or []:
            content = row.get("content") or {}
            msg = {
                "id": row["id"],
                "role": row["role"],
                "content": content.get("text") or row.get("plain_text") or "",
                "activity_items": content.get("activity_items"),
                "created_at": row.get("created_at"),
            }
            messages.append(msg)

        # Get context_items from conversation metadata
        context_items = conversation.get("metadata", {}).get("context_items")

        return {
            "conversation": {
                "id": conversation["id"],
                "title": conversation.get("title"),
                "status": conversation.get("status"),
                "created_at": conversation.get("created_at"),
                "last_message_at": conversation.get("last_message_at"),
                "is_owner": is_owner,
            },
            "messages": messages,
            "context_items": context_items,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to load conversation") from exc


# --- Thread Sharing Endpoints ---


@router.post("/threads/{thread_id}/share")
async def toggle_thread_share(
    thread_id: str,
    payload: dict,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """
    Toggle sharing for a thread. Only the owner can change sharing status.

    Body: { "is_shared": bool }
    Returns: { "thread_id", "is_shared", "share_url" }
    """
    is_shared = payload.get("is_shared")
    if is_shared is None:
        raise HTTPException(status_code=400, detail="is_shared is required")

    store = SupabaseChatStore()
    try:
        result = await store.toggle_share(thread_id, bool(is_shared), context)
        return result
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to toggle share for thread %s", thread_id)
        raise HTTPException(status_code=404, detail="Thread not found") from exc


@router.get("/threads/{thread_id}/share")
async def get_thread_share_status(
    thread_id: str,
    context: MarketingRequestContext = Depends(require_marketing_context),
):
    """
    Get current sharing status for a thread.

    Returns: { "thread_id", "is_shared", "shared_at", "is_owner", "can_toggle", "share_url" }
    """
    store = SupabaseChatStore()
    try:
        result = await store.get_share_status(thread_id, context)
        return result
    except Exception as exc:
        logger.exception("Failed to get share status for thread %s", thread_id)
        raise HTTPException(status_code=404, detail="Thread not found") from exc
