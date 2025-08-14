from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class MeetingOut(BaseModel):
    id: str
    doc_id: str
    title: Optional[str]
    meeting_datetime: Optional[str]
    organizer_email: Optional[str]
    organizer_name: Optional[str]
    document_url: Optional[str]
    invited_emails: List[str] = Field(default_factory=list)
    text_content: Optional[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_structured: bool = Field(default=False, description="構造化済みかどうか")
