from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Iterable, Optional

from chatkit.store import NotFoundError, Store
from chatkit.types import Attachment, Page, ThreadItem, ThreadMetadata
from pydantic import TypeAdapter

from app.infrastructure.chatkit.context import MarketingRequestContext
from app.infrastructure.supabase.client import get_supabase

logger = logging.getLogger(__name__)


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

    def __init__(self):
        self._thread_adapter = _thread_adapter
        self._item_adapter = _item_adapter
        self._attachment_adapter = _attachment_adapter

    def _client(self):
        return get_supabase()

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
        metadata = row.get("metadata") or {}
        try:
            thread = self._thread_adapter.validate_python(
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
        if after:
            after_rows = (
                sb.table(self.ITEM_TABLE)
                .select("created_at")
                .eq("id", after)
                .limit(1)
                .execute()
            ).data or []
            if not after_rows:
                raise NotFoundError(f"Thread item {after} not found")
            after_ts = after_rows[0]["created_at"]
            comparator = "lt" if desc else "gt"
            query = getattr(query, comparator)("created_at", after_ts)

        query = query.order("created_at", desc=desc).limit(limit + 1)
        res = query.execute()
        rows: list[dict[str, Any]] = res.data or []
        has_more = len(rows) > limit
        rows = rows[:limit]
        items: list[ThreadItem] = []
        for row in rows:
            content = row.get("content") or {}
            try:
                thread_item = self._item_adapter.validate_python(content)
                items.append(thread_item)
            except Exception:
                logger.exception(
                    "Failed to deserialize marketing message id=%s", row.get("id")
                )
                continue
        next_after = rows[-1]["id"] if rows else None
        return Page[ThreadItem](data=items, has_more=has_more, after=next_after)

    async def save_attachment(
        self, attachment: Attachment, context: MarketingRequestContext
    ) -> None:
        sb = self._client()
        payload = {
            "id": attachment.id,
            "conversation_id": attachment.thread_id,
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
        sb = self._client()
        res = (
            sb.table(self.ATTACHMENT_TABLE)
            .select("storage_metadata")
            .eq("id", attachment_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise NotFoundError(f"Attachment {attachment_id} not found")
        return self._attachment_adapter.validate_python(rows[0]["storage_metadata"])

    async def delete_attachment(
        self, attachment_id: str, context: MarketingRequestContext
    ) -> None:
        sb = self._client()
        sb.table(self.ATTACHMENT_TABLE).delete().eq("id", attachment_id).execute()

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
                .select("created_at")
                .eq("id", after)
                .limit(1)
                .execute()
            ).data or []
            if not after_rows:
                raise NotFoundError(f"Thread {after} not found")
            after_ts = after_rows[0]["created_at"]
            comparator = "lt" if desc else "gt"
            query = getattr(query, comparator)("created_at", after_ts)

        query = query.order("created_at", desc=desc).limit(limit + 1)
        res = query.execute()
        rows = res.data or []
        has_more = len(rows) > limit
        rows = rows[:limit]
        threads: list[ThreadMetadata] = []
        for row in rows:
            try:
                threads.append(await self.load_thread(row["id"], context))
            except NotFoundError:
                continue
        next_after = rows[-1]["id"] if rows else None
        return Page[ThreadMetadata](data=threads, has_more=has_more, after=next_after)

    async def add_thread_item(
        self, thread_id: str, item: ThreadItem, context: MarketingRequestContext
    ) -> None:
        sb = self._client()
        payload = {
            "id": item.id,
            "conversation_id": thread_id,
            "role": self._infer_role(item),
            "message_type": item.type,
            "plain_text": _plain_text_from_item(item),
            "content": item.model_dump(mode="json"),
            "created_by": context.user_email,
            "created_at": getattr(item, "created_at", datetime.utcnow()).isoformat(),
        }
        sb.table(self.ITEM_TABLE).upsert(payload).execute()
        sb.table(self.THREAD_TABLE).update(
            {
                "last_message_at": payload["created_at"],
            }
        ).eq("id", thread_id).execute()

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
        sb.table(self.ITEM_TABLE).update(payload).eq("id", item.id).execute()

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

    def _infer_role(self, item: ThreadItem) -> str:
        if item.type == "assistant_message":
            return "assistant"
        if item.type == "user_message":
            return "user"
        if item.type == "client_tool_call":
            return "tool"
        if item.type == "workflow":
            return "workflow"
        if item.type == "hidden_context_item":
            return "context"
        return item.type
