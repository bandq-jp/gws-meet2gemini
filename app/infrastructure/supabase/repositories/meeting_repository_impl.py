from __future__ import annotations
from typing import List, Optional, Dict, Any
from app.infrastructure.supabase.client import get_supabase
from app.domain.entities.meeting_document import MeetingDocument

class MeetingRepositoryImpl:
    TABLE = "meeting_documents"

    def get_by_doc_and_organizer(self, doc_id: str, organizer_email: str) -> Dict[str, Any]:
        sb = get_supabase()
        res = sb.table(self.TABLE).select("*").eq("doc_id", doc_id).eq("organizer_email", organizer_email).limit(1).execute()
        data = getattr(res, "data", None)
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        return {}

    def upsert_meeting(self, meeting: MeetingDocument) -> Dict[str, Any]:
        sb = get_supabase()
        payload = {
            "doc_id": meeting.doc_id,
            "title": meeting.title,
            "meeting_datetime": meeting.meeting_datetime,
            "organizer_email": meeting.organizer_email,
            "organizer_name": meeting.organizer_name,
            "document_url": meeting.document_url,
            "invited_emails": meeting.invited_emails,
            "text_content": meeting.text_content,
            "metadata": meeting.metadata,
        }
        # dedupe by doc_id + organizer_email
        res = sb.table(self.TABLE).upsert(payload, on_conflict="doc_id,organizer_email").execute()
        data = getattr(res, "data", None)
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        return {}

    def list_meetings(self, accounts: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        sb = get_supabase()
        query = sb.table(self.TABLE).select("*")
        if accounts:
            query = query.in_("organizer_email", accounts)
        res = query.order("meeting_datetime", desc=True).execute()
        data = getattr(res, "data", None)
        if isinstance(data, list):
            return data
        return []

    def get_meeting(self, meeting_id: str) -> Dict[str, Any]:
        sb = get_supabase()
        res = sb.table(self.TABLE).select("*").eq("id", meeting_id).limit(1).execute()
        data = getattr(res, "data", None)
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        return {}
