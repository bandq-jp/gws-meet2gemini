from __future__ import annotations
from typing import List, Optional

from app.infrastructure.google.drive_docs_collector import DriveDocsCollector
from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl

class CollectMeetingsUseCase:
    async def execute(self, accounts: Optional[List[str]] = None, include_structure: bool = False, force_update: bool = False) -> int:
        collector = DriveDocsCollector()
        repo = MeetingRepositoryImpl()

        collected = await collector.collect_meeting_docs(accounts, include_structure=include_structure)
        stored = 0
        for meeting in collected:
            existing = repo.get_by_doc_and_organizer(meeting.doc_id, meeting.organizer_email or "")
            if existing and not force_update:
                try:
                    existing_modified = (existing.get("metadata") or {}).get("modifiedTime")
                    current_modified = (meeting.metadata or {}).get("modifiedTime")
                    if existing_modified and current_modified and existing_modified == current_modified:
                        # unchanged, skip
                        continue
                except Exception:
                    pass
            repo.upsert_meeting(meeting)
            stored += 1
        return stored
