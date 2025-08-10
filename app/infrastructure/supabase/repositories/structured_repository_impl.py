from __future__ import annotations
from typing import Dict, Any, Optional
from app.infrastructure.supabase.client import get_supabase
from app.domain.entities.structured_data import StructuredData, ZohoCandidateInfo

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
        res = sb.table(self.TABLE).upsert(payload, on_conflict=["meeting_id"]).execute()
        return res.data[0] if res.data else {}

    # Legacy method for backward compatibility
    def upsert_structured_legacy(self, meeting_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        sb = get_supabase()
        payload = {"meeting_id": meeting_id, "data": data}
        res = sb.table(self.TABLE).upsert(payload, on_conflict=["meeting_id"]).execute()
        return res.data[0] if res.data else {}

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
        """Get StructuredData entity with Zoho candidate info"""
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
        
        return StructuredData(
            meeting_id=data['meeting_id'],
            data=data['data'],
            zoho_candidate=zoho_candidate
        )
