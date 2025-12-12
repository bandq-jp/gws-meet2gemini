from __future__ import annotations

import json
import logging
import time
from typing import Any

from chatkit.store import AttachmentStore
from chatkit.types import AttachmentCreateParams, FileAttachment

from app.infrastructure.chatkit.context import MarketingRequestContext
from app.infrastructure.security.marketing_token_service import MarketingTokenService
from app.infrastructure.config.settings import get_settings
from app.infrastructure.supabase.client import get_supabase

logger = logging.getLogger(__name__)


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
        # If creation failed because it already exists or policy, just log.
        logger.exception("Failed to create or verify attachment bucket %s", bucket)


class SupabaseAttachmentStore(AttachmentStore[MarketingRequestContext]):
    """
    AttachmentStore that issues upload URLs and signs short‑lived tokens.

    The actual file bytes are uploaded via the FastAPI endpoint
    `/api/v1/marketing/attachments/{attachment_id}/upload`.
    """

    BUCKET = "marketing-attachments"
    TOKEN_TTL_SECONDS = 600

    def __init__(self) -> None:
        settings = get_settings()
        self._token_service = MarketingTokenService(settings.marketing_chatkit_token_secret)
        self._supabase = get_supabase()
        _ensure_bucket_exists(self._supabase, self.BUCKET)

    async def create_attachment(
        self, input: AttachmentCreateParams, context: MarketingRequestContext
    ) -> FileAttachment:
        attachment_id = self.generate_attachment_id(input.mime_type, context)
        now = int(time.time())
        token_payload: dict[str, Any] = {
            "sub": context.user_id,
            "email": context.user_email,
            "name": context.user_name,
            "iat": now,
            "exp": now + self.TOKEN_TTL_SECONDS,
            "attachment": {
                "id": attachment_id,
                "name": input.name,
                "mime_type": input.mime_type,
                "size": input.size,
            },
        }
        signed = self._token_service.sign(token_payload)

        # Use absolute URL so ChatKit (pydantic) accepts it and the browser can reach it.
        settings = get_settings()
        base = (settings.marketing_upload_base_url or "").strip()

        if not base:
            raise ValueError(
                "MARKETING_UPLOAD_BASE_URL must be set to an absolute URL "
                "(e.g. https://your-frontend.vercel.app or backend public URL)"
            )

        upload_url = f"{base.rstrip('/')}/api/v1/marketing/attachments/{attachment_id}/upload?token={signed}"

        logger.info(
            "Issued attachment upload URL",
            extra={"attachment_id": attachment_id, "mime_type": input.mime_type, "size": input.size},
        )
        return FileAttachment(
            id=attachment_id,
            name=input.name,
            mime_type=input.mime_type,
            upload_url=upload_url,
        )

    async def delete_attachment(self, attachment_id: str, context: MarketingRequestContext) -> None:
        bucket = self._supabase.storage.from_(self.BUCKET)
        prefix = f"attachments/{attachment_id}"
        try:
            objects = bucket.list(path=prefix) or []
            to_remove = [f"{prefix}/{obj['name']}" for obj in objects]
            if to_remove:
                bucket.remove(to_remove)
        except Exception:
            logger.exception("Failed to delete attachment objects for %s", attachment_id)

        try:
            self._supabase.table("marketing_attachments").delete().eq("id", attachment_id).execute()
        except Exception:
            logger.exception("Failed to delete attachment row for %s", attachment_id)
