from __future__ import annotations

from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl
from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl
from app.infrastructure.gemini.structured_extractor_split import GeminiStructuredExtractorSplit

class ProcessStructuredDataUseCase:
    async def execute(self, meeting_id: str) -> dict:
        meetings = MeetingRepositoryImpl()
        structured_repo = StructuredRepositoryImpl()
        meeting = meetings.get_meeting(meeting_id)
        if not meeting or not meeting.get("text_content"):
            raise ValueError("Meeting text not found")
        extractor = GeminiStructuredExtractorSplit()
        data = extractor.extract_all_structured_data(meeting["text_content"], use_parallel=True)
        structured_repo.upsert_structured(meeting_id, data)
        return {"meeting_id": meeting_id, "data": data}
