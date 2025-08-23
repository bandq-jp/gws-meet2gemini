from __future__ import annotations
from typing import List, Optional
import logging
import asyncio
from app.infrastructure.background.job_tracker import JobTracker

from app.infrastructure.google.drive_docs_collector import DriveDocsCollector
from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl

logger = logging.getLogger(__name__)


class CollectMeetingsUseCase:
    async def execute(
        self,
        accounts: Optional[List[str]] = None,
        include_structure: bool = False,
        force_update: bool = False,
        job_id: Optional[str] = None,
    ) -> None:
        logger.info(
            "CollectMeetingsUseCase started: accounts=%s include_structure=%s force_update=%s",
            accounts,
            include_structure,
            force_update,
        )
        try:
            collector = DriveDocsCollector()
            repo = MeetingRepositoryImpl()

            collected = await collector.collect_meeting_docs(
                accounts, include_structure=include_structure
            )
            logger.info("Collected meetings from Drive: %d", len(collected))
            if job_id:
                JobTracker.update(job_id, collected=len(collected))

            stored = 0
            skipped = 0
            for meeting in collected:
                # Offload Supabase calls to thread to avoid blocking event loop
                existing = await asyncio.to_thread(
                    repo.get_by_doc_and_organizer,
                    meeting.doc_id,
                    meeting.organizer_email or "",
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
                            skipped += 1
                            continue
                    except Exception as ex:
                        logger.debug(
                            "Comparison failed for doc_id=%s organizer=%s: %s (proceed to upsert)",
                            meeting.doc_id,
                            meeting.organizer_email,
                            ex,
                        )
                await asyncio.to_thread(repo.upsert_meeting, meeting)
                stored += 1

            logger.info(
                "CollectMeetingsUseCase finished. Stored/updated=%d, skipped=%d, total=%d",
                stored,
                skipped,
                len(collected),
            )
            if job_id:
                JobTracker.mark_success(
                    job_id,
                    message="Collection completed",
                    stored=stored,
                    skipped=skipped,
                    collected=len(collected),
                )
        except Exception as e:
            logger.exception("CollectMeetingsUseCase error: %s", e)
            # Do not re-raise; this runs in background
            if job_id:
                JobTracker.mark_failed(job_id, error=str(e))
            return None
