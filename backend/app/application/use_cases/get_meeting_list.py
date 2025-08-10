from __future__ import annotations
from typing import List, Optional

from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl

class GetMeetingListUseCase:
    async def execute(self, accounts: Optional[List[str]] = None) -> List[dict]:
        repo = MeetingRepositoryImpl()
        return repo.list_meetings(accounts)
