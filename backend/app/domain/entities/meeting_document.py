from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class MeetingDocument:
    id: Optional[str]
    doc_id: str
    title: Optional[str]
    meeting_datetime: Optional[str]
    organizer_email: Optional[str]
    organizer_name: Optional[str]
    document_url: Optional[str]
    invited_emails: List[str] = field(default_factory=list)
    text_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
