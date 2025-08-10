from __future__ import annotations
from typing import List, Optional
import logging

from app.infrastructure.google.drive_docs_collector import DriveDocsCollector
from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl

logger = logging.getLogger(__name__)


class CollectMeetingsUseCase:
    async def execute(
        self,
        accounts: Optional[List[str]] = None,
        include_structure: bool = False,
        force_update: bool = False,
    ) -> int:
        logger.debug(
            "CollectMeetingsUseCase.execute start: accounts=%s include_structure=%s force_update=%s",
            accounts,
            include_structure,
            force_update,
        )
        collector = DriveDocsCollector()
        repo = MeetingRepositoryImpl()

        collected = await collector.collect_meeting_docs(
            accounts, include_structure=include_structure
        )
        logger.debug("Collected meetings: %d", len(collected))
        stored = 0
        for meeting in collected:
            existing = repo.get_by_doc_and_organizer(
                meeting.doc_id, meeting.organizer_email or ""
            )
            if existing and not force_update:
                try:
                    existing_modified = (existing.get("metadata") or {}).get(
                        "modifiedTime"
                    )
                    current_modified = (meeting.metadata or {}).get("modifiedTime")
                    if (
                        existing_modified
                        and current_modified
                        and existing_modified == current_modified
                    ):
                        logger.debug(
                            "Skip unchanged meeting: doc_id=%s organizer=%s",
                            meeting.doc_id,
                            meeting.organizer_email,
                        )
                        continue
                except Exception as ex:
                    logger.debug(
                        "Comparison failed for doc_id=%s organizer=%s: %s",
                        meeting.doc_id,
                        meeting.organizer_email,
                        ex,
                    )
            repo.upsert_meeting(meeting)
            stored += 1
        logger.debug("Stored/updated meetings: %d", stored)
        return stored
