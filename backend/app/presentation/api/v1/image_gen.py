"""
画像生成 API ルーター

テンプレート管理、リファレンス画像管理、セッション管理、画像生成のエンドポイント。
"""
from __future__ import annotations

import io
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel

from app.application.use_cases import image_gen as use_cases
from app.application.use_cases.image_gen import QuotaExceededError
from app.infrastructure.supabase.repositories.image_gen_repository import (
    OUTPUTS_BUCKET,
    REFERENCES_BUCKET,
    ImageGenRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/image-gen", tags=["image-gen"])

IMMUTABLE_IMAGE_CACHE_CONTROL = "private, max-age=31536000, immutable"


# ── Schemas ──


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    aspect_ratio: str = "auto"
    image_size: str = "1K"
    system_prompt: Optional[str] = None
    visibility: str = "public"
    created_by: Optional[str] = None
    created_by_email: Optional[str] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    aspect_ratio: Optional[str] = None
    image_size: Optional[str] = None
    system_prompt: Optional[str] = None
    visibility: Optional[str] = None
    thumbnail_url: Optional[str] = None


class SessionCreate(BaseModel):
    template_id: Optional[str] = None
    title: Optional[str] = None
    aspect_ratio: str = "auto"
    image_size: str = "1K"
    created_by: Optional[str] = None
    created_by_email: Optional[str] = None


class GenerateRequest(BaseModel):
    prompt: str
    aspect_ratio: Optional[str] = None
    image_size: Optional[str] = None


class SessionUpdate(BaseModel):
    template_id: Optional[str] = None


class ReorderRequest(BaseModel):
    reference_ids: List[str]


# ── Templates ──


@router.get("/templates")
def list_templates(
    created_by: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    return use_cases.list_templates(created_by=created_by)


@router.get("/templates/{template_id}")
def get_template(template_id: str) -> Dict[str, Any]:
    result = use_cases.get_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.post("/templates")
def create_template(body: TemplateCreate) -> Dict[str, Any]:
    return use_cases.create_template(**body.model_dump())


@router.put("/templates/{template_id}")
def update_template(template_id: str, body: TemplateUpdate) -> Dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    return use_cases.update_template(template_id, payload)


@router.delete("/templates/{template_id}")
def delete_template(template_id: str) -> Dict[str, str]:
    use_cases.delete_template(template_id)
    return {"status": "deleted"}


# ── References ──


@router.post("/templates/{template_id}/references")
async def upload_reference(
    template_id: str,
    file: UploadFile = File(...),
    label: str = Form("style"),
) -> Dict[str, Any]:
    if label not in ("object", "person", "style"):
        raise HTTPException(status_code=400, detail="label must be object, person, or style")

    content = await file.read()
    mime = file.content_type or "image/png"

    try:
        return use_cases.upload_reference(
            template_id=template_id,
            filename=file.filename or "image.png",
            file_bytes=content,
            mime_type=mime,
            size_bytes=len(content),
            label=label,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/references/{reference_id}")
def delete_reference(reference_id: str) -> Dict[str, str]:
    use_cases.delete_reference(reference_id)
    return {"status": "deleted"}


@router.put("/templates/{template_id}/references/order")
def reorder_references(template_id: str, body: ReorderRequest) -> Dict[str, str]:
    use_cases.reorder_references(template_id, body.reference_ids)
    return {"status": "reordered"}


# ── Sessions ──


@router.get("/sessions")
def list_sessions(
    created_by: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    return use_cases.list_sessions(created_by=created_by)


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> Dict[str, Any]:
    result = use_cases.get_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.post("/sessions")
def create_session(body: SessionCreate) -> Dict[str, Any]:
    return use_cases.create_session(**body.model_dump())


@router.patch("/sessions/{session_id}")
def update_session(session_id: str, body: SessionUpdate) -> Dict[str, Any]:
    """Update session (e.g. change template)."""
    from app.infrastructure.supabase.repositories.image_gen_repository import ImageGenRepository
    repo = ImageGenRepository()
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # exclude_unset=True: リクエストに含まれたフィールドのみ（null も含む）
    sent_fields = body.model_dump(exclude_unset=True)
    payload: Dict[str, Any] = {}
    if "template_id" in sent_fields:
        payload["template_id"] = sent_fields["template_id"]
    if not payload:
        from datetime import datetime, timezone
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    return repo.update_session(session_id, payload)


# ── Usage / Quota ──


@router.get("/usage")
def get_usage() -> Dict[str, Any]:
    """Get current month's image generation usage and quota."""
    return use_cases.get_usage()


# ── Image Generation ──


@router.post("/sessions/{session_id}/generate")
def generate_image(session_id: str, body: GenerateRequest) -> Dict[str, Any]:
    try:
        return use_cases.generate_image(
            session_id=session_id,
            prompt=body.prompt,
            aspect_ratio=body.aspect_ratio,
            image_size=body.image_size,
        )
    except QuotaExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Image generation failed: %s", e, exc_info=True)
        # Gemini APIのエラーコードをそのまま伝搬（503 UNAVAILABLE等）
        error_msg = str(e)
        status_code = 500
        if "503" in error_msg or "UNAVAILABLE" in error_msg:
            status_code = 503
            detail = "画像生成サービスが一時的に混雑しています。しばらく待ってからもう一度お試しください。"
        elif "400" in error_msg or "INVALID_ARGUMENT" in error_msg:
            status_code = 400
            detail = f"画像生成リクエストが無効です: {error_msg[:200]}"
        elif "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            status_code = 429
            detail = "API利用制限に達しました。しばらく待ってからもう一度お試しください。"
        else:
            detail = f"画像生成に失敗しました: {error_msg[:200]}"
        raise HTTPException(status_code=status_code, detail=detail)


# ── Image Serving ──


def _detect_image_mime(path: str) -> str:
    path_lower = path.lower()
    if path_lower.endswith(".jpeg") or path_lower.endswith(".jpg"):
        return "image/jpeg"
    if path_lower.endswith(".webp"):
        return "image/webp"
    return "image/png"


def _resolve_output_format(
    requested_format: Optional[str],
    original_mime: str,
) -> tuple[str, str]:
    if requested_format == "jpeg":
        return "JPEG", "image/jpeg"
    if requested_format == "webp":
        return "WEBP", "image/webp"
    if requested_format == "png":
        return "PNG", "image/png"

    if original_mime == "image/jpeg":
        return "JPEG", "image/jpeg"
    if original_mime == "image/webp":
        return "WEBP", "image/webp"
    return "PNG", "image/png"


def _resize_image(
    data: bytes,
    original_mime: str,
    width: Optional[int],
    height: Optional[int],
    fit: str,
    quality: int,
    requested_format: Optional[str],
) -> tuple[bytes, str]:
    should_transform = (
        width is not None
        or height is not None
        or requested_format is not None
    )
    if not should_transform:
        return data, original_mime

    try:
        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)

            target_width = min(width or image.width, image.width)
            target_height = min(height or image.height, image.height)

            if target_width > 0 or target_height > 0:
                if target_width > 0 and target_height > 0 and fit == "cover":
                    image = ImageOps.fit(
                        image,
                        (target_width, target_height),
                        method=Image.Resampling.LANCZOS,
                    )
                else:
                    image.thumbnail(
                        (
                            target_width or image.width,
                            target_height or image.height,
                        ),
                        Image.Resampling.LANCZOS,
                    )

            output_format, output_mime = _resolve_output_format(
                requested_format=requested_format,
                original_mime=original_mime,
            )

            save_kwargs: Dict[str, Any] = {}
            if output_format == "JPEG":
                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True
            elif output_format == "WEBP":
                if image.mode == "P":
                    image = image.convert("RGBA")
                save_kwargs["quality"] = quality
                save_kwargs["method"] = 6
            else:
                save_kwargs["optimize"] = True

            out = io.BytesIO()
            image.save(out, format=output_format, **save_kwargs)
            return out.getvalue(), output_mime
    except (UnidentifiedImageError, OSError) as e:
        logger.warning("Failed to transform image: %s", e)
        return data, original_mime


@router.get("/images/{bucket}/{path:path}")
def serve_image(
    bucket: str,
    path: str,
    w: Optional[int] = Query(None, ge=32, le=4096),
    h: Optional[int] = Query(None, ge=32, le=4096),
    q: int = Query(82, ge=40, le=100),
    fit: str = Query("contain", pattern="^(contain|cover)$"),
    format: Optional[str] = Query(None, pattern="^(png|jpeg|webp)$"),
) -> Response:
    if bucket not in (REFERENCES_BUCKET, OUTPUTS_BUCKET):
        raise HTTPException(status_code=400, detail="Invalid bucket")
    try:
        repo = ImageGenRepository()
        data = repo.download_image(bucket, path)
        mime = _detect_image_mime(path)
        transformed_data, transformed_mime = _resize_image(
            data=data,
            original_mime=mime,
            width=w,
            height=h,
            fit=fit,
            quality=q,
            requested_format=format,
        )
        return Response(
            content=transformed_data,
            media_type=transformed_mime,
            headers={
                "Cache-Control": IMMUTABLE_IMAGE_CACHE_CONTROL,
                "Content-Length": str(len(transformed_data)),
            },
        )
    except Exception as e:
        logger.error("Failed to serve image %s/%s: %s", bucket, path, e)
        raise HTTPException(status_code=404, detail="Image not found")
