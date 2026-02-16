from __future__ import annotations
import logging
from typing import Any, Dict

from app.infrastructure.zoho.client import ZohoClient
from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl

logger = logging.getLogger(__name__)


class GetCandidateDetailUseCase:
    def __init__(self):
        self.zoho_client = ZohoClient()
        self.structured_repo = StructuredRepositoryImpl()

    def execute(self, record_id: str) -> Dict[str, Any]:
        # Fetch full Zoho record
        zoho_record = self.zoho_client.get_app_hc_record(record_id)
        if not zoho_record:
            return {"error": "Zoho record not found", "record_id": record_id}

        # Fetch all structured outputs for this candidate
        structured_outputs = self.structured_repo.get_all_by_zoho_record_id(record_id)

        # Fetch linked meetings with structured data
        meetings = self.structured_repo.get_meetings_with_structured_by_zoho_record_id(record_id)

        return {
            "record_id": record_id,
            "zoho_record": zoho_record,
            "structured_outputs": [
                {
                    "meeting_id": so.get("meeting_id"),
                    "data": so.get("data", {}),
                    "created_at": so.get("created_at"),
                }
                for so in structured_outputs
            ],
            "linked_meetings": [
                {
                    "meeting_id": m.get("meeting_id"),
                    "title": m.get("title"),
                    "meeting_datetime": m.get("meeting_datetime"),
                    "organizer_email": m.get("organizer_email"),
                    "is_structured": m.get("is_structured", False),
                }
                for m in meetings
            ],
        }
