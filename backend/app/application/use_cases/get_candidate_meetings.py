from __future__ import annotations
import logging
from typing import Any, Dict

from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl

logger = logging.getLogger(__name__)


class GetCandidateMeetingsUseCase:
    def __init__(self):
        self.structured_repo = StructuredRepositoryImpl()

    def execute(self, record_id: str) -> Dict[str, Any]:
        meetings = self.structured_repo.get_meetings_with_structured_by_zoho_record_id(record_id)

        items = [
            {
                "meeting_id": m.get("meeting_id"),
                "title": m.get("title"),
                "meeting_datetime": m.get("meeting_datetime"),
                "organizer_email": m.get("organizer_email"),
                "is_structured": m.get("is_structured", False),
            }
            for m in meetings
        ]

        return {
            "items": items,
            "total": len(items),
        }
