from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from app.infrastructure.zoho.client import ZohoClient
from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl

logger = logging.getLogger(__name__)


class ListCandidatesUseCase:
    def __init__(self):
        self.zoho_client = ZohoClient()
        self.structured_repo = StructuredRepositoryImpl()

    def execute(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        channel: Optional[str] = None,
        sort_by: str = "registration_date",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Fetch paginated candidates from Zoho
        result = self.zoho_client.list_candidates_paginated(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            channel=channel,
            sort_by=sort_by,
            date_from=date_from,
            date_to=date_to,
        )

        candidates = result.get("data", [])

        # Enrich with linked meetings count
        record_ids = [c["record_id"] for c in candidates if c.get("record_id")]
        if record_ids:
            try:
                counts = self.structured_repo.count_meetings_by_zoho_record_ids(record_ids)
                for c in candidates:
                    c["linked_meetings_count"] = counts.get(c["record_id"], 0)
            except Exception as e:
                logger.warning("[list_candidates] count enrichment failed: %s", e)
                for c in candidates:
                    c["linked_meetings_count"] = 0
        else:
            for c in candidates:
                c["linked_meetings_count"] = 0

        return {
            "items": candidates,
            "total": result.get("total", 0),
            "page": result.get("page", page),
            "page_size": result.get("page_size", page_size),
            "total_pages": result.get("total_pages", 1),
            "has_next": result.get("has_next", False),
            "has_previous": result.get("has_previous", False),
            "filters": {
                "statuses": ZohoClient.STATUSES,
                "channels": ZohoClient.CHANNELS,
            },
        }
