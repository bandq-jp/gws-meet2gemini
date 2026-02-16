from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from app.infrastructure.supabase.client import get_supabase
from app.domain.entities.structured_data import StructuredData, ZohoCandidateInfo, ZohoSyncInfo

logger = logging.getLogger(__name__)

class StructuredRepositoryImpl:
    TABLE = "structured_outputs"

    def upsert_structured(self, structured_data: StructuredData) -> Dict[str, Any]:
        sb = get_supabase()
        payload = {
            "meeting_id": structured_data.meeting_id,
            "data": structured_data.data,
            "zoho_candidate_id": structured_data.zoho_candidate.candidate_id if structured_data.zoho_candidate else None,
            "zoho_record_id": structured_data.zoho_candidate.record_id if structured_data.zoho_candidate else None,
            "zoho_candidate_name": structured_data.zoho_candidate.candidate_name if structured_data.zoho_candidate else None,
            "zoho_candidate_email": structured_data.zoho_candidate.candidate_email if structured_data.zoho_candidate else None,
        }
        # Add Zoho sync info if provided
        if structured_data.zoho_sync:
            payload["zoho_sync_status"] = structured_data.zoho_sync.status
            payload["zoho_sync_error"] = structured_data.zoho_sync.error
            payload["zoho_synced_at"] = structured_data.zoho_sync.synced_at.isoformat() if structured_data.zoho_sync.synced_at else None
            payload["zoho_sync_fields_count"] = structured_data.zoho_sync.fields_count
        # returning="minimal" でレスポンスからdata JSONB等を除外（エグレス削減）
        sb.table(self.TABLE).upsert(
            payload, on_conflict=["meeting_id"], returning="minimal"
        ).execute()
        return {}

    # Legacy method for backward compatibility
    def upsert_structured_legacy(self, meeting_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        sb = get_supabase()
        payload = {"meeting_id": meeting_id, "data": data}
        sb.table(self.TABLE).upsert(
            payload, on_conflict=["meeting_id"], returning="minimal"
        ).execute()
        return {}

    def get_by_meeting_id(self, meeting_id: str) -> Dict[str, Any]:
        sb = get_supabase()
        query = sb.table(self.TABLE).select("*").eq("meeting_id", meeting_id)
        try:
            # Prefer maybe_single to avoid raising when 0 rows
            res = query.maybe_single().execute()
            return res.data or {}
        except Exception:
            # Fallback: take first row if exists, otherwise return empty
            try:
                res = query.limit(1).execute()
                return (res.data[0] if res.data else {})
            except Exception:
                return {}
    
    def get_structured_data(self, meeting_id: str) -> Optional[StructuredData]:
        """Get StructuredData entity with Zoho candidate info and sync status"""
        data = self.get_by_meeting_id(meeting_id)
        if not data:
            return None

        zoho_candidate = None
        if any([data.get('zoho_candidate_id'), data.get('zoho_record_id'),
                data.get('zoho_candidate_name'), data.get('zoho_candidate_email')]):
            zoho_candidate = ZohoCandidateInfo(
                candidate_id=data.get('zoho_candidate_id'),
                record_id=data.get('zoho_record_id'),
                candidate_name=data.get('zoho_candidate_name'),
                candidate_email=data.get('zoho_candidate_email')
            )

        # Build Zoho sync info if any sync data exists
        zoho_sync = None
        if any([data.get('zoho_sync_status'), data.get('zoho_sync_error'),
                data.get('zoho_synced_at'), data.get('zoho_sync_fields_count')]):
            synced_at = None
            if data.get('zoho_synced_at'):
                try:
                    synced_at = datetime.fromisoformat(data['zoho_synced_at'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
            zoho_sync = ZohoSyncInfo(
                status=data.get('zoho_sync_status'),
                error=data.get('zoho_sync_error'),
                synced_at=synced_at,
                fields_count=data.get('zoho_sync_fields_count')
            )

        return StructuredData(
            meeting_id=data['meeting_id'],
            data=data['data'],
            zoho_candidate=zoho_candidate,
            zoho_sync=zoho_sync
        )

    def delete_by_meeting_id(self, meeting_id: str) -> None:
        """構造化データを削除する（再処理前にクリアしたい場合に使用）"""
        sb = get_supabase()
        sb.table(self.TABLE).delete().eq("meeting_id", meeting_id).execute()

    def update_zoho_sync_status(
        self,
        meeting_id: str,
        status: str,
        error: Optional[str] = None,
        fields_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update only the Zoho sync status for a structured output record

        Args:
            meeting_id: The meeting ID to update
            status: Sync status (success, failed, auth_error, field_mapping_error, error)
            error: Error message if sync failed
            fields_count: Number of fields successfully synced

        Returns:
            Updated record data
        """
        sb = get_supabase()
        payload = {
            "zoho_sync_status": status,
            "zoho_sync_error": error,
            "zoho_sync_fields_count": fields_count,
        }
        # Only set synced_at on success
        if status == "success":
            payload["zoho_synced_at"] = datetime.utcnow().isoformat()

        # returning="minimal" でレスポンスからdata JSONB等を除外（エグレス削減）
        sb.table(self.TABLE).update(payload, returning="minimal").eq("meeting_id", meeting_id).execute()
        return {}

    # --- 候補者ページ用メソッド ---

    def get_by_zoho_record_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get first structured output linked to a Zoho record ID."""
        sb = get_supabase()
        try:
            res = (
                sb.table(self.TABLE)
                .select("meeting_id, data, zoho_candidate_id, zoho_record_id, zoho_candidate_name, zoho_candidate_email, zoho_sync_status, created_at, updated_at")
                .eq("zoho_record_id", record_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.warning("[structured_repo] get_by_zoho_record_id failed: %s", e)
            return None

    def get_all_by_zoho_record_id(self, record_id: str) -> List[Dict[str, Any]]:
        """Get all structured outputs linked to a Zoho record ID (multiple meetings)."""
        sb = get_supabase()
        try:
            res = (
                sb.table(self.TABLE)
                .select("meeting_id, data, zoho_sync_status, created_at, updated_at")
                .eq("zoho_record_id", record_id)
                .order("created_at", desc=True)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning("[structured_repo] get_all_by_zoho_record_id failed: %s", e)
            return []

    def count_meetings_by_zoho_record_ids(self, record_ids: List[str]) -> Dict[str, int]:
        """Batch count of linked meetings per Zoho record ID.

        Returns:
            Dict mapping record_id -> count
        """
        if not record_ids:
            return {}
        sb = get_supabase()
        try:
            res = (
                sb.table(self.TABLE)
                .select("zoho_record_id")
                .in_("zoho_record_id", record_ids)
                .execute()
            )
            counts: Dict[str, int] = {}
            for row in res.data or []:
                rid = row.get("zoho_record_id")
                if rid:
                    counts[rid] = counts.get(rid, 0) + 1
            return counts
        except Exception as e:
            logger.warning("[structured_repo] count_meetings_by_zoho_record_ids failed: %s", e)
            return {}

    def get_meetings_with_structured_by_zoho_record_id(self, record_id: str) -> List[Dict[str, Any]]:
        """Get meeting documents linked to a Zoho record ID via structured_outputs.

        Returns list of dicts with meeting info + structured status.
        """
        sb = get_supabase()
        try:
            # First get meeting_ids from structured_outputs
            so_res = (
                sb.table(self.TABLE)
                .select("meeting_id, data, zoho_sync_status, created_at")
                .eq("zoho_record_id", record_id)
                .order("created_at", desc=True)
                .execute()
            )
            if not so_res.data:
                return []

            meeting_ids = [row["meeting_id"] for row in so_res.data]

            # Fetch meeting documents
            m_res = (
                sb.table("meeting_documents")
                .select("id, title, meeting_datetime, organizer_email")
                .in_("id", meeting_ids)
                .execute()
            )
            meeting_map = {m["id"]: m for m in (m_res.data or [])}

            # Merge
            results = []
            for so in so_res.data:
                mid = so["meeting_id"]
                meeting = meeting_map.get(mid, {})
                results.append({
                    "meeting_id": mid,
                    "title": meeting.get("title"),
                    "meeting_datetime": meeting.get("meeting_datetime"),
                    "organizer_email": meeting.get("organizer_email"),
                    "is_structured": True,
                    "structured_data": so.get("data"),
                })
            return results
        except Exception as e:
            logger.warning("[structured_repo] get_meetings_with_structured failed: %s", e)
            return []

    def get_full_transcripts_by_zoho_record_id(self, record_id: str) -> List[Dict[str, Any]]:
        """候補者に紐づく全議事録の全文テキストを取得。

        Returns:
            List of dicts: meeting_id, title, meeting_datetime, text_content, structured_data
        """
        sb = get_supabase()
        try:
            # structured_outputs から meeting_id を取得
            so_res = (
                sb.table(self.TABLE)
                .select("meeting_id, data, created_at")
                .eq("zoho_record_id", record_id)
                .order("created_at", desc=True)
                .execute()
            )
            if not so_res.data:
                return []

            meeting_ids = [row["meeting_id"] for row in so_res.data]

            # meeting_documents から全文を取得
            m_res = (
                sb.table("meeting_documents")
                .select("id, title, meeting_datetime, text_content")
                .in_("id", meeting_ids)
                .execute()
            )
            meeting_map = {m["id"]: m for m in (m_res.data or [])}

            results = []
            for so in so_res.data:
                mid = so["meeting_id"]
                meeting = meeting_map.get(mid, {})
                text = meeting.get("text_content") or ""
                results.append({
                    "meeting_id": mid,
                    "title": meeting.get("title"),
                    "meeting_datetime": meeting.get("meeting_datetime"),
                    "text_content": text,
                    "structured_data": so.get("data"),
                })
            return results
        except Exception as e:
            logger.warning("[structured_repo] get_full_transcripts failed: %s", e)
            return []
