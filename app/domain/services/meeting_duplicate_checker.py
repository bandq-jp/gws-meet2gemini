from __future__ import annotations
from app.domain.entities.meeting_document import MeetingDocument

class MeetingDuplicateChecker:
    def is_duplicate(self, meeting: MeetingDocument) -> bool:
        # Implement additional logic if needed. Repository upsert will dedupe by doc_id+organizer
        return False
