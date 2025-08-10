from __future__ import annotations
from typing import Optional

from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl
from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl
from app.infrastructure.gemini.structured_extractor_split import GeminiStructuredExtractorSplit
from app.domain.entities.structured_data import StructuredData, ZohoCandidateInfo

class ProcessStructuredDataUseCase:
    async def execute(self, meeting_id: str, zoho_candidate_id: Optional[str] = None, 
                     zoho_record_id: Optional[str] = None, 
                     zoho_candidate_name: Optional[str] = None, 
                     zoho_candidate_email: Optional[str] = None) -> dict:
        meetings = MeetingRepositoryImpl()
        structured_repo = StructuredRepositoryImpl()
        meeting = meetings.get_meeting(meeting_id)
        if not meeting or not meeting.get("text_content"):
            raise ValueError("Meeting text not found")
        
        # Require Zoho candidate selection
        if not zoho_record_id:
            raise ValueError("Zoho candidate selection is required for structured output processing")
        
        extractor = GeminiStructuredExtractorSplit()
        data = extractor.extract_all_structured_data(meeting["text_content"], use_parallel=True)
        
        # Create structured data with Zoho candidate info
        zoho_candidate = ZohoCandidateInfo(
            candidate_id=zoho_candidate_id,
            record_id=zoho_record_id,
            candidate_name=zoho_candidate_name,
            candidate_email=zoho_candidate_email
        )
        
        structured_data = StructuredData(
            meeting_id=meeting_id,
            data=data,
            zoho_candidate=zoho_candidate
        )
        
        structured_repo.upsert_structured(structured_data)
        return {"meeting_id": meeting_id, "data": data, "zoho_candidate": zoho_candidate}
