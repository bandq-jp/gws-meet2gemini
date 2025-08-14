from __future__ import annotations
from typing import List, Optional

from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl

class GetMeetingListUseCase:
    async def execute(self, accounts: Optional[List[str]] = None, structured: Optional[bool] = None) -> List[dict]:
        repo = MeetingRepositoryImpl()
        meetings = repo.list_meetings(accounts)
        
        # 構造化フィルタが指定されている場合のみフィルタリング
        if structured is not None:
            meetings = [m for m in meetings if m.get('is_structured', False) == structured]
        
        return meetings
