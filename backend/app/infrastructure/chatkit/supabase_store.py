from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Iterable, Optional

from chatkit.store import NotFoundError, Store
from chatkit.types import Attachment, FileAttachment, Page, ThreadItem, ThreadMetadata
from openai import AsyncOpenAI
from pydantic import TypeAdapter

from app.infrastructure.chatkit.context import MarketingRequestContext
from app.infrastructure.config.settings import get_settings
from app.infrastructure.supabase.client import get_supabase

logger = logging.getLogger(__name__)

# Title generation model (lightweight, fast)
TITLE_GENERATION_MODEL = "gpt-4.1-mini"


async def generate_thread_title(user_message: str) -> str | None:
    """
    Generate a concise Japanese thread title from the first user message.
    Uses a lightweight model for cost efficiency.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured, skipping title generation")
        return None

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Truncate very long messages
        truncated_message = user_message[:500] if len(user_message) > 500 else user_message

        response = await client.chat.completions.create(
            model=TITLE_GENERATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "ユーザーの最初のメッセージから、チャットのタイトルを生成してください。\n"
                        "ルール:\n"
                        "- 日本語で15文字以内\n"
                        "- 内容を端的に表す\n"
                        "- 絵文字は使わない\n"
                        "- タイトルのみを出力（説明不要）"
                    ),
                },
                {
                    "role": "user",
                    "content": truncated_message,
                },
            ],
            max_tokens=50,
            temperature=0.3,
        )

        title = response.choices[0].message.content
        if title:
            # Clean up and truncate if needed
            title = title.strip().strip('"\'')
            if len(title) > 30:
                title = title[:27] + "..."
            return title
        return None
    except Exception as e:
        logger.warning("Failed to generate thread title: %s", e)
        return None


class PermissionDeniedError(Exception):
    """Raised when a user lacks permission to perform an action."""
    pass


_thread_adapter = TypeAdapter(ThreadMetadata)
_item_adapter = TypeAdapter(ThreadItem)
_attachment_adapter = TypeAdapter(Attachment)


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _plain_text_from_item(item: ThreadItem) -> str | None:
    try:
        if item.type == "assistant_message":
            texts = [
                segment.text
                for segment in getattr(item, "content", [])
                if hasattr(segment, "text")
            ]
            return " ".join(texts).strip() or None
        if item.type == "user_message":
            texts = [
                segment.text
                for segment in getattr(item, "content", [])
                if hasattr(segment, "text")
            ]
            return " ".join(texts).strip() or None
    except Exception:
        logger.exception("Failed to extract plain text from thread item")
    return None


class SupabaseChatStore(Store[MarketingRequestContext]):
    THREAD_TABLE = "marketing_conversations"
    ITEM_TABLE = "marketing_messages"
    ATTACHMENT_TABLE = "marketing_attachments"
    ATTACHMENT_BUCKET = "marketing-attachments"

    def __init__(self):
        self._thread_adapter = _thread_adapter
        self._item_adapter = _item_adapter
        self._attachment_adapter = _attachment_adapter

    def _client(self):
        return get_supabase()

    def _storage_prefix(self, attachment_id: str) -> str:
        return f"attachments/{attachment_id}"

    def _load_attachment_metadata(self, attachment_id: str) -> dict[str, Any]:
        """
        Load attachment metadata from DB; fall back to Supabase Storage cache.
        """
        sb = self._client()

        # 1) Try persisted row
        try:
            res = (
                sb.table(self.ATTACHMENT_TABLE)
                .select("storage_metadata")
                .eq("id", attachment_id)
                .limit(1)
                .execute()
            )
            row = (res.data or [None])[0]
            if row and row.get("storage_metadata"):
                return row["storage_metadata"] or {}
        except Exception:
            logger.exception("Failed to load attachment metadata from table for %s", attachment_id)

        # 2) Fallback to storage meta.json
        try:
            raw = (
                sb.storage.from_(self.ATTACHMENT_BUCKET)
                .download(f"{self._storage_prefix(attachment_id)}/meta.json")
            )
            return json.loads(raw) if raw else {}
        except Exception:
            logger.info("No storage metadata found for attachment %s", attachment_id)
            return {}

    def _serialize_thread(self, thread: ThreadMetadata) -> dict[str, Any]:
        payload = thread.model_dump(mode="json")
        status = getattr(thread.status, "type", "active")
        payload.update(
            {
                "title": thread.title or thread.metadata.get("title"),
                "status": status,
                "metadata": thread.metadata,
                "created_at": thread.created_at.isoformat(),
            }
        )
        return payload

    def _row_to_thread(self, row: dict, context: MarketingRequestContext) -> ThreadMetadata:
        """DBの行データからThreadMetadataを構築する（N+1回避用の共通ヘルパー）"""
        # Access control: owner OR shared
        is_owner = row.get("owner_clerk_id") == context.user_id
        is_shared = row.get("is_shared", False)

        if not is_owner and not is_shared:
            raise NotFoundError(f"Thread {row.get('id')} not found")  # 404 for security

        metadata = row.get("metadata") or {}
        # Inject sharing info into metadata for frontend
        metadata["is_shared"] = is_shared
        metadata["is_owner"] = is_owner
        metadata["can_edit"] = is_owner  # Only owner can send messages
        metadata["shared_at"] = row.get("shared_at")
        metadata["shared_by_email"] = row.get("shared_by_email") if is_owner else None

        return self._thread_adapter.validate_python(
            {
                "id": row["id"],
                "title": row.get("title"),
                "created_at": _parse_dt(row.get("created_at") or datetime.utcnow()),
                "status": metadata.get(
                    "status",
                    {"type": row.get("status") or "active"},
                ),
                "metadata": metadata,
            }
        )

    async def load_thread(
        self, thread_id: str, context: MarketingRequestContext
    ) -> ThreadMetadata:
        sb = self._client()
        res = (
            sb.table(self.THREAD_TABLE)
            .select("*")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        )
        data = (res.data or [])
        if not data:
            raise NotFoundError(f"Thread {thread_id} not found")
        row = data[0]

        try:
            thread = self._row_to_thread(row, context)
        except Exception as exc:
            logger.exception("Failed to deserialize marketing thread row")
            raise NotFoundError(f"Thread {thread_id} malformed") from exc
        return thread

    async def save_thread(
        self, thread: ThreadMetadata, context: MarketingRequestContext
    ) -> None:
        sb = self._client()
        metadata = thread.metadata or {}
        # Inject model asset id from context if provided and not already set
        if context.model_asset_id and not metadata.get("model_asset_id"):
            metadata = {**metadata, "model_asset_id": context.model_asset_id}
        payload = {
            "id": thread.id,
            "title": thread.title or f"{context.user_name or 'マーケティング'}のチャット",
            "status": getattr(thread.status, "type", "active"),
            "metadata": metadata,
            "owner_email": context.user_email,
            "owner_clerk_id": context.user_id,
            "last_message_at": thread.metadata.get("last_message_at")
            or datetime.utcnow().isoformat(),
        }
        try:
            sb.table(self.THREAD_TABLE).upsert(payload).execute()
        except Exception:
            logger.exception("Failed to upsert marketing thread id=%s", thread.id)
            raise

    async def load_thread_items(
        self,
        thread_id: str,
        after: str | None,
        limit: int,
        order: str,
        context: MarketingRequestContext,
    ) -> Page[ThreadItem]:
        sb = self._client()
        query = sb.table(self.ITEM_TABLE).select("*").eq("conversation_id", thread_id)
        desc = order == "desc"

        # Cursor pagination with a tie‑breaker on id so items sharing the same timestamp
        # are not skipped or duplicated (ChatKit can emit multiple rows within the same ms).
        if after:
            after_rows = (
                sb.table(self.ITEM_TABLE)
                .select("created_at,id")
                .eq("id", after)
                .limit(1)
                .execute()
            ).data or []
            if not after_rows:
                raise NotFoundError(f"Thread item {after} not found")
            after_created_at = _parse_dt(after_rows[0]["created_at"]).isoformat()
            comparator = "lt" if desc else "gt"
            cursor_filter = (
                f"created_at.{comparator}.{after_created_at},"
                f"and(created_at.eq.{after_created_at},id.{comparator}.{after})"
            )
            query = query.or_(cursor_filter)

        query = (
            query.order("created_at", desc=desc)
            .order("id", desc=desc)
            .limit(limit + 1)
        )
        res = query.execute()
        rows: list[dict[str, Any]] = res.data or []
        has_more = len(rows) > limit
        rows = rows[:limit]
        items: list[ThreadItem] = []
        logger.info(f"Loading {len(rows)} thread items from Supabase for thread {thread_id}")
        for row in rows:
            content = row.get("content") or {}
            item_type = content.get("type", "unknown")
            item_id = row.get("id", "unknown")
            try:
                thread_item = self._item_adapter.validate_python(content)
                logger.debug(f"Successfully validated item: type={item_type}, id={item_id[:8]}...")
            except Exception as e:
                # 1.4 系以降で追加された item.type がある場合、厳密検証だと落ちる。
                # モデル構築のみで通し、コンテキスト欠落を防ぐ。
                logger.info(f"Strict validation failed for type={item_type}, trying lenient construction: {e}")
                try:
                    thread_item = ThreadItem.model_construct(**content)
                    logger.warning(
                        "Leniently accepted unknown ThreadItem type=%s id=%s",
                        content.get("type"),
                        row.get("id"),
                    )
                except Exception as e2:
                    logger.exception(
                        "Failed to deserialize marketing message id=%s type=%s: %s", row.get("id"), item_type, e2
                    )
                    continue
            items.append(thread_item)
            logger.debug(f"Added item to list: type={thread_item.type}, id={thread_item.id[:8]}...")
        next_after = rows[-1]["id"] if has_more and rows else None
        return Page[ThreadItem](data=items, has_more=has_more, after=next_after)

    async def save_attachment(
        self, attachment: Attachment, context: MarketingRequestContext
    ) -> None:
        sb = self._client()
        thread_id = getattr(attachment, "thread_id", None)
        if not thread_id and context.scope:
            thread_id = context.scope.get("thread_id")
        if not thread_id:
            # Without a thread we cannot satisfy the FK constraint; skip quietly.
            logger.warning("Skipping attachment save because thread_id is missing (id=%s)", attachment.id)
            return
        payload = {
            "id": attachment.id,
            "conversation_id": thread_id,
            "owner_email": context.user_email,
            "filename": getattr(attachment, "name", None),
            "mime_type": getattr(attachment, "mime_type", None),
            "size_bytes": getattr(attachment, "size", None),
            "storage_metadata": attachment.model_dump(mode="json"),
        }
        sb.table(self.ATTACHMENT_TABLE).upsert(payload).execute()

    async def load_attachment(
        self, attachment_id: str, context: MarketingRequestContext
    ) -> Attachment:
        metadata = self._load_attachment_metadata(attachment_id)
        if not metadata:
            raise NotFoundError(f"Attachment {attachment_id} not found")

        file_id = metadata.get("openai_file_id") or metadata.get("file_id") or attachment_id
        name = metadata.get("name") or metadata.get("filename") or attachment_id
        mime = metadata.get("mime_type") or "application/octet-stream"

        # Validate to ensure schema compatibility, but return as FileAttachment
        try:
            validated = self._attachment_adapter.validate_python(
                {"id": file_id, "name": name, "mime_type": mime, "type": "file"}
            )
            if isinstance(validated, FileAttachment):
                return validated
        except Exception:
            logger.exception("Failed to validate attachment %s; returning lenient FileAttachment", attachment_id)

        return FileAttachment(id=file_id, name=name, mime_type=mime)

    async def delete_attachment(
        self, attachment_id: str, context: MarketingRequestContext
    ) -> None:
        sb = self._client()
        try:
            sb.table(self.ATTACHMENT_TABLE).delete().eq("id", attachment_id).execute()
        except Exception:
            logger.exception("Failed to delete attachment row for %s", attachment_id)

        try:
            prefix = self._storage_prefix(attachment_id)
            objects = sb.storage.from_(self.ATTACHMENT_BUCKET).list(path=prefix) or []
            targets = [f"{prefix}/{obj['name']}" for obj in objects]
            if targets:
                sb.storage.from_(self.ATTACHMENT_BUCKET).remove(targets)
        except Exception:
            logger.exception("Failed to delete attachment storage objects for %s", attachment_id)

    async def load_threads(
        self,
        limit: int,
        after: str | None,
        order: str,
        context: MarketingRequestContext,
    ) -> Page[ThreadMetadata]:
        sb = self._client()
        query = (
            sb.table(self.THREAD_TABLE)
            .select("*")
            .eq("owner_clerk_id", context.user_id)
        )
        desc = order == "desc"
        if after:
            after_rows = (
                sb.table(self.THREAD_TABLE)
                .select("created_at,id")
                .eq("id", after)
                .limit(1)
                .execute()
            ).data or []
            if not after_rows:
                raise NotFoundError(f"Thread {after} not found")
            after_ts = _parse_dt(after_rows[0]["created_at"]).isoformat()
            comparator = "lt" if desc else "gt"
            cursor_filter = (
                f"created_at.{comparator}.{after_ts},"
                f"and(created_at.eq.{after_ts},id.{comparator}.{after})"
            )
            query = query.or_(cursor_filter)

        query = (
            query.order("created_at", desc=desc)
            .order("id", desc=desc)
            .limit(limit + 1)
        )
        res = query.execute()
        rows = res.data or []
        has_more = len(rows) > limit
        rows = rows[:limit]
        threads: list[ThreadMetadata] = []
        # N+1回避: 既に取得済みの行データから直接ThreadMetadataを構築
        for row in rows:
            try:
                threads.append(self._row_to_thread(row, context))
            except (NotFoundError, Exception):
                continue
        next_after = rows[-1]["id"] if has_more and rows else None
        return Page[ThreadMetadata](data=threads, has_more=has_more, after=next_after)

    async def add_thread_item(
        self, thread_id: str, item: ThreadItem, context: MarketingRequestContext
    ) -> None:
        sb = self._client()
        plain_text = _plain_text_from_item(item)
        payload = {
            "id": item.id,
            "conversation_id": thread_id,
            "role": self._infer_role(item),
            "message_type": item.type,
            "plain_text": plain_text,
            "content": item.model_dump(mode="json"),
            "created_by": context.user_email,
            "created_at": getattr(item, "created_at", datetime.utcnow()).isoformat(),
        }
        logger.info(f"Saving thread item to Supabase: type={item.type}, id={item.id[:8]}..., thread={thread_id[:8]}...")
        sb.table(self.ITEM_TABLE).upsert(payload, returning="minimal").execute()
        logger.info(f"Successfully saved thread item: type={item.type}, id={item.id[:8]}...")
        sb.table(self.THREAD_TABLE).update(
            {"last_message_at": payload["created_at"]}, returning="minimal"
        ).eq("id", thread_id).execute()

        # Generate title for first user message if thread has default title
        if item.type == "user_message" and plain_text:
            asyncio.create_task(
                self._maybe_generate_title(thread_id, plain_text, context)
            )

    async def save_item(
        self, thread_id: str, item: ThreadItem, context: MarketingRequestContext
    ) -> None:
        sb = self._client()
        payload = {
            "role": self._infer_role(item),
            "message_type": item.type,
            "plain_text": _plain_text_from_item(item),
            "content": item.model_dump(mode="json"),
        }
        sb.table(self.ITEM_TABLE).update(payload, returning="minimal").eq("id", item.id).execute()

    async def load_item(
        self, thread_id: str, item_id: str, context: MarketingRequestContext
    ) -> ThreadItem:
        sb = self._client()
        res = (
            sb.table(self.ITEM_TABLE)
            .select("content")
            .eq("id", item_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise NotFoundError(f"Thread item {item_id} not found")
        return self._item_adapter.validate_python(rows[0]["content"])

    async def delete_thread(self, thread_id: str, context: MarketingRequestContext) -> None:
        sb = self._client()
        sb.table(self.THREAD_TABLE).delete().eq("id", thread_id).execute()

    async def delete_thread_item(
        self, thread_id: str, item_id: str, context: MarketingRequestContext
    ) -> None:
        sb = self._client()
        sb.table(self.ITEM_TABLE).delete().eq("id", item_id).execute()

    async def _maybe_generate_title(
        self, thread_id: str, user_message: str, context: MarketingRequestContext
    ) -> None:
        """Generate a title for the thread if it still has the default title."""
        try:
            sb = self._client()
            # Check current title
            res = (
                sb.table(self.THREAD_TABLE)
                .select("title")
                .eq("id", thread_id)
                .limit(1)
                .execute()
            )
            if not res.data:
                return

            current_title = res.data[0].get("title") or ""
            # Check if title is default pattern (ends with "のチャット")
            if not current_title.endswith("のチャット"):
                logger.debug(
                    "Thread %s already has custom title: %s", thread_id[:8], current_title
                )
                return

            # Generate new title
            logger.info("Generating title for thread %s from message: %s...", thread_id[:8], user_message[:50])
            new_title = await generate_thread_title(user_message)
            if not new_title:
                logger.info("Title generation returned empty for thread %s", thread_id[:8])
                return

            # Update thread title
            sb.table(self.THREAD_TABLE).update({"title": new_title}).eq("id", thread_id).execute()
            logger.info("Updated thread %s title to: %s", thread_id[:8], new_title)

        except Exception as e:
            # Don't fail the main flow if title generation fails
            logger.warning("Failed to generate/update title for thread %s: %s", thread_id[:8], e)

    def _infer_role(self, item: ThreadItem) -> str:
        if item.type == "assistant_message":
            return "assistant"
        if item.type == "user_message":
            return "user"
        if item.type == "client_tool_call":
            return "tool"
        if item.type == "tool_output":
            return "tool"
        if item.type == "workflow":
            return "workflow"
        if item.type == "hidden_context_item":
            return "context"
        # Fallback: treat any tool-ish type as tool so it is stored and can be reloaded
        if "tool" in item.type:
            return "tool"
        if item.type in ("progress", "event"):
            return item.type
        return item.type

    # --- Sharing methods ---

    async def _is_owner(self, thread_id: str, context: MarketingRequestContext) -> bool:
        """Check if the current user owns the thread."""
        sb = self._client()
        res = (
            sb.table(self.THREAD_TABLE)
            .select("owner_clerk_id")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return False
        return res.data[0].get("owner_clerk_id") == context.user_id

    async def toggle_share(
        self, thread_id: str, is_shared: bool, context: MarketingRequestContext
    ) -> dict[str, Any]:
        """Toggle sharing status. Only owner can do this."""
        sb = self._client()

        # Verify ownership
        res = (
            sb.table(self.THREAD_TABLE)
            .select("owner_clerk_id, is_shared")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            raise NotFoundError(f"Thread {thread_id} not found")
        if res.data[0].get("owner_clerk_id") != context.user_id:
            raise PermissionDeniedError("Only the owner can share this thread")

        # Update sharing status
        update_payload: dict[str, Any] = {
            "is_shared": is_shared,
        }
        if is_shared and not res.data[0].get("is_shared"):
            # First time sharing - record who and when
            update_payload["shared_at"] = datetime.utcnow().isoformat()
            update_payload["shared_by_email"] = context.user_email
            update_payload["shared_by_clerk_id"] = context.user_id

        sb.table(self.THREAD_TABLE).update(update_payload).eq("id", thread_id).execute()
        logger.info(
            "Thread %s sharing toggled to %s by %s",
            thread_id,
            is_shared,
            context.user_email,
        )

        return {
            "thread_id": thread_id,
            "is_shared": is_shared,
            "share_url": f"/marketing/{thread_id}" if is_shared else None,
        }

    async def get_share_status(
        self, thread_id: str, context: MarketingRequestContext
    ) -> dict[str, Any]:
        """Get current sharing status for a thread."""
        sb = self._client()
        res = (
            sb.table(self.THREAD_TABLE)
            .select("id, is_shared, shared_at, shared_by_email, owner_clerk_id")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        )

        if not res.data:
            raise NotFoundError(f"Thread {thread_id} not found")

        row = res.data[0]
        is_owner = row.get("owner_clerk_id") == context.user_id
        is_shared = row.get("is_shared", False)

        # Non-owners can only see shared threads
        if not is_owner and not is_shared:
            raise NotFoundError(f"Thread {thread_id} not found")

        return {
            "thread_id": thread_id,
            "is_shared": is_shared,
            "shared_at": row.get("shared_at"),
            "shared_by_email": row.get("shared_by_email") if is_owner else None,
            "is_owner": is_owner,
            "can_toggle": is_owner,
            "share_url": f"/marketing/{thread_id}" if is_shared else None,
        }
