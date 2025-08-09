from __future__ import annotations

from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl

class GetStructuredDataUseCase:
    async def execute(self, meeting_id: str) -> dict:
        repo = StructuredRepositoryImpl()
        data = repo.get_by_meeting_id(meeting_id)
        if not data:
            return {"meeting_id": meeting_id, "data": {}}
        return {"meeting_id": meeting_id, "data": data.get("data", {})}
