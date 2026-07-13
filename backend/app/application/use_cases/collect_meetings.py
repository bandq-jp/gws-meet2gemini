from __future__ import annotations
from typing import List, Optional
import logging
import asyncio
from app.infrastructure.background.job_tracker import JobTracker

from app.infrastructure.google.drive_docs_collector import DriveDocsCollector
from app.infrastructure.notta.drive_xlsx_collector import NottaDriveXlsxCollector
from app.infrastructure.config.settings import get_settings
from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl

logger = logging.getLogger(__name__)


class CollectMeetingsUseCase:
    async def execute(
        self,
        accounts: Optional[List[str]] = None,
        include_structure: bool = False,
        force_update: bool = False,
        job_id: Optional[str] = None,
        since_days: Optional[int] = None,
    ) -> None:
        logger.info(
            "CollectMeetingsUseCase started: accounts=%s include_structure=%s force_update=%s since_days=%s",
            accounts,
            include_structure,
            force_update,
            since_days,
        )
        try:
            settings = get_settings()
            source = (settings.meeting_source or "google_docs").strip().lower()
            collectors = []
            if source in ("google_docs", "google", "docs", "drive"):
                collectors.append(DriveDocsCollector())
            elif source in ("notta",):
                collectors.append(NottaDriveXlsxCollector())
            elif source in ("both", "all"):
                collectors.extend([DriveDocsCollector(), NottaDriveXlsxCollector()])
            else:
                raise RuntimeError(f"Unknown MEETING_SOURCE: {settings.meeting_source}")
            repo = MeetingRepositoryImpl()

            collected = []
            collect_errors: List[str] = []
            for collector in collectors:
                # 片方のソース障害でもう片方まで止めない(both運用時の隔離)
                try:
                    collected.extend(
                        await collector.collect_meeting_docs(
                            accounts,
                            include_structure=include_structure,
                            since_days=since_days,
                        )
                    )
                except Exception as e:
                    name = type(collector).__name__
                    collect_errors.append(f"{name}: {e}")
                    logger.exception("Collector failed (continuing with others): %s", name)
            if collect_errors and not collected:
                raise RuntimeError("; ".join(collect_errors))
            logger.info("Collected meetings from Drive: %d", len(collected))
            if job_id:
                JobTracker.update(job_id, collected=len(collected))

            stored = 0
            skipped = 0
            failed = 0
            for meeting in collected:
                try:
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
                except Exception as e:
                    failed += 1
                    logger.error(
                        "Failed to store meeting: doc_id=%s organizer=%s error=%s",
                        meeting.doc_id,
                        meeting.organizer_email or "unknown",
                        str(e)
                    )

            logger.info(
                "CollectMeetingsUseCase finished. Stored/updated=%d, skipped=%d, failed=%d, total=%d",
                stored,
                skipped,
                failed,
                len(collected),
            )
            if job_id:
                JobTracker.mark_success(
                    job_id,
                    message="Collection completed",
                    stored=stored,
                    skipped=skipped,
                    failed=failed,
                    collected=len(collected),
                )
        except Exception as e:
            logger.exception("CollectMeetingsUseCase error: %s", e)
            # Do not re-raise; this runs in background
            if job_id:
                JobTracker.mark_failed(job_id, error=str(e))
            return None
