from __future__ import annotations

from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl

class GetStructuredDataUseCase:
    async def execute(self, meeting_id: str) -> dict:
        repo = StructuredRepositoryImpl()
        structured_data = repo.get_structured_data(meeting_id)
        if not structured_data:
            return {"meeting_id": meeting_id, "data": {}, "zoho_candidate": None, "zoho_sync": None}

        zoho_candidate_dict = None
        if structured_data.zoho_candidate:
            zoho_candidate_dict = {
                "candidate_id": structured_data.zoho_candidate.candidate_id,
                "record_id": structured_data.zoho_candidate.record_id,
                "candidate_name": structured_data.zoho_candidate.candidate_name,
                "candidate_email": structured_data.zoho_candidate.candidate_email,
            }

        zoho_sync_dict = None
        if structured_data.zoho_sync:
            zoho_sync_dict = {
                "status": structured_data.zoho_sync.status,
                "error": structured_data.zoho_sync.error,
                "synced_at": structured_data.zoho_sync.synced_at.isoformat() if structured_data.zoho_sync.synced_at else None,
                "fields_count": structured_data.zoho_sync.fields_count,
            }

        return {
            "meeting_id": meeting_id,
            "data": structured_data.data,
            "zoho_candidate": zoho_candidate_dict,
            "zoho_sync": zoho_sync_dict
        }
