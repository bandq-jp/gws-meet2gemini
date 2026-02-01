from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime
from app.infrastructure.supabase.client import get_supabase
from app.domain.entities.structured_data import StructuredData, ZohoCandidateInfo, ZohoSyncInfo

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
