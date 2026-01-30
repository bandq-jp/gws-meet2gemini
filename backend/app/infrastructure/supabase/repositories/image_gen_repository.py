"""
画像生成プラットフォーム用 Supabase リポジトリ

テンプレート、リファレンス画像、セッション、メッセージのCRUD操作と
Supabase Storage へのファイルアップロード/ダウンロードを管理する。
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from app.infrastructure.supabase.client import get_supabase

logger = logging.getLogger(__name__)

TEMPLATES_TABLE = "image_gen_templates"
REFERENCES_TABLE = "image_gen_references"
SESSIONS_TABLE = "image_gen_sessions"
MESSAGES_TABLE = "image_gen_messages"

REFERENCES_BUCKET = "image-gen-references"
OUTPUTS_BUCKET = "image-gen-outputs"


class ImageGenRepository:
    """画像生成リポジトリ"""

    # ── Templates ──

    def list_templates(
        self,
        created_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        sb = get_supabase()
        q = sb.table(TEMPLATES_TABLE).select("*, image_gen_references(*)").order("created_at", desc=True)
        if created_by:
            q = q.or_(f"visibility.eq.public,created_by.eq.{created_by}")
        else:
            q = q.eq("visibility", "public")
        res = q.execute()
        return res.data or []

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        sb = get_supabase()
        res = (
            sb.table(TEMPLATES_TABLE)
            .select("*, image_gen_references(*)")
            .eq("id", template_id)
            .limit(1)
            .execute()
        )
        data = res.data
        if isinstance(data, list) and data:
            return data[0]
        return None

    def create_template(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sb = get_supabase()
        if "id" not in payload:
            payload["id"] = str(uuid.uuid4())
        res = sb.table(TEMPLATES_TABLE).insert(payload).execute()
        data = res.data
        if isinstance(data, list) and data:
            return data[0]
        return payload

    def update_template(self, template_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        sb = get_supabase()
        res = (
            sb.table(TEMPLATES_TABLE)
            .update(payload)
            .eq("id", template_id)
            .execute()
        )
        data = res.data
        if isinstance(data, list) and data:
            return data[0]
        return {}

    def delete_template(self, template_id: str) -> bool:
        sb = get_supabase()
        # Delete references storage first
        refs = self._list_references(template_id)
        for ref in refs:
            self._delete_storage(REFERENCES_BUCKET, ref.get("storage_path", ""))
        sb.table(TEMPLATES_TABLE).delete().eq("id", template_id).execute()
        return True

    # ── References ──

    def _list_references(self, template_id: str) -> List[Dict[str, Any]]:
        sb = get_supabase()
        res = (
            sb.table(REFERENCES_TABLE)
            .select("*")
            .eq("template_id", template_id)
            .order("sort_order")
            .execute()
        )
        return res.data or []

    def add_reference(
        self,
        template_id: str,
        filename: str,
        file_bytes: bytes,
        mime_type: str,
        size_bytes: int,
        label: str = "style",
    ) -> Dict[str, Any]:
        sb = get_supabase()
        ref_id = str(uuid.uuid4())
        # Use only the extension for storage path to avoid non-ASCII key errors
        ext = os.path.splitext(filename)[1] or ".png"
        storage_path = f"{template_id}/{ref_id}{ext}"

        # Upload to storage
        sb.storage.from_(REFERENCES_BUCKET).upload(
            storage_path,
            file_bytes,
            file_options={"content-type": mime_type},
        )

        # Get current max sort_order
        existing = self._list_references(template_id)
        max_order = max((r.get("sort_order", 0) for r in existing), default=-1)

        payload = {
            "id": ref_id,
            "template_id": template_id,
            "filename": filename,
            "storage_path": storage_path,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "sort_order": max_order + 1,
            "label": label,
        }
        res = sb.table(REFERENCES_TABLE).insert(payload).execute()
        data = res.data
        if isinstance(data, list) and data:
            return data[0]
        return payload

    def delete_reference(self, reference_id: str) -> bool:
        sb = get_supabase()
        # Get reference to find storage path
        res = sb.table(REFERENCES_TABLE).select("*").eq("id", reference_id).limit(1).execute()
        data = res.data
        if isinstance(data, list) and data:
            self._delete_storage(REFERENCES_BUCKET, data[0].get("storage_path", ""))
        sb.table(REFERENCES_TABLE).delete().eq("id", reference_id).execute()
        return True

    def reorder_references(self, template_id: str, reference_ids: List[str]) -> bool:
        sb = get_supabase()
        for idx, ref_id in enumerate(reference_ids):
            sb.table(REFERENCES_TABLE).update({"sort_order": idx}).eq("id", ref_id).execute()
        return True

    def get_reference_images(self, template_id: str) -> List[tuple[bytes, str]]:
        """テンプレートのリファレンス画像をバイナリで取得"""
        sb = get_supabase()
        refs = self._list_references(template_id)
        images = []
        for ref in refs:
            path = ref.get("storage_path", "")
            mime = ref.get("mime_type", "image/png")
            if path:
                try:
                    data = sb.storage.from_(REFERENCES_BUCKET).download(path)
                    images.append((data, mime))
                except Exception as e:
                    logger.warning("Failed to download reference %s: %s", path, e)
        return images

    # ── Sessions ──

    def list_sessions(
        self,
        created_by: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        sb = get_supabase()
        q = sb.table(SESSIONS_TABLE).select("*").order("updated_at", desc=True).limit(limit)
        if created_by:
            q = q.eq("created_by", created_by)
        res = q.execute()
        return res.data or []

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        sb = get_supabase()
        res = (
            sb.table(SESSIONS_TABLE)
            .select("*")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )
        data = res.data
        if isinstance(data, list) and data:
            return data[0]
        return None

    def create_session(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sb = get_supabase()
        if "id" not in payload:
            payload["id"] = str(uuid.uuid4())
        res = sb.table(SESSIONS_TABLE).insert(payload).execute()
        data = res.data
        if isinstance(data, list) and data:
            return data[0]
        return payload

    def update_session(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        sb = get_supabase()
        res = (
            sb.table(SESSIONS_TABLE)
            .update(payload)
            .eq("id", session_id)
            .execute()
        )
        data = res.data
        if isinstance(data, list) and data:
            return data[0]
        return {}

    # ── Messages ──

    def list_messages(self, session_id: str) -> List[Dict[str, Any]]:
        sb = get_supabase()
        res = (
            sb.table(MESSAGES_TABLE)
            .select("*")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        return res.data or []

    def add_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sb = get_supabase()
        if "id" not in payload:
            payload["id"] = str(uuid.uuid4())
        res = sb.table(MESSAGES_TABLE).insert(payload).execute()
        data = res.data
        if isinstance(data, list) and data:
            return data[0]
        return payload

    # ── Storage helpers ──

    def upload_output_image(
        self,
        session_id: str,
        image_data: bytes,
        mime_type: str = "image/png",
    ) -> str:
        """生成画像をStorageにアップロードし、パスを返す"""
        sb = get_supabase()
        ext = "png" if "png" in mime_type else "jpeg" if "jpeg" in mime_type else "webp"
        image_id = str(uuid.uuid4())
        path = f"{session_id}/{image_id}.{ext}"

        sb.storage.from_(OUTPUTS_BUCKET).upload(
            path,
            image_data,
            file_options={"content-type": mime_type},
        )
        return path

    def get_image_public_url(self, bucket: str, path: str) -> str:
        """Storage画像の公開URLを取得"""
        sb = get_supabase()
        return sb.storage.from_(bucket).get_public_url(path)

    def get_image_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        """Storage画像の署名付きURLを取得"""
        sb = get_supabase()
        res = sb.storage.from_(bucket).create_signed_url(path, expires_in)
        if isinstance(res, dict):
            return res.get("signedURL", "")
        return ""

    def download_image(self, bucket: str, path: str) -> bytes:
        """Storage画像をダウンロード"""
        sb = get_supabase()
        return sb.storage.from_(bucket).download(path)

    def _delete_storage(self, bucket: str, path: str) -> None:
        if not path:
            return
        try:
            sb = get_supabase()
            sb.storage.from_(bucket).remove([path])
        except Exception as e:
            logger.warning("Failed to delete storage %s/%s: %s", bucket, path, e)
