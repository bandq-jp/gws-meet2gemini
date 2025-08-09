from __future__ import annotations

from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl

class GetMeetingDetailUseCase:
    async def execute(self, meeting_id: str) -> dict:
        repo = MeetingRepositoryImpl()
        return repo.get_meeting(meeting_id)
