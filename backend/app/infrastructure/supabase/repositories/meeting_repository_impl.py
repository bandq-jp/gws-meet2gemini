from __future__ import annotations
from typing import List, Optional, Dict, Any
from app.infrastructure.supabase.client import get_supabase
import logging
from app.domain.entities.meeting_document import MeetingDocument

logger = logging.getLogger(__name__)


class MeetingRepositoryImpl:
    TABLE = "meeting_documents"

    def get_by_doc_and_organizer(self, doc_id: str, organizer_email: str) -> Dict[str, Any]:
        sb = get_supabase()
        logger.debug("Supabase select doc_id=%s organizer=%s", doc_id, organizer_email)
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
        logger.debug("Supabase upsert doc_id=%s organizer=%s", meeting.doc_id, meeting.organizer_email)
        res = sb.table(self.TABLE).upsert(payload, on_conflict="doc_id,organizer_email").execute()
        data = getattr(res, "data", None)
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        return {}

    def list_meetings(self, accounts: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        sb = get_supabase()
        # LEFT JOINで構造化済みかどうかを判定
        query = sb.table(self.TABLE).select(
            "*, structured_outputs!left(meeting_id)"
        )
        if accounts:
            query = query.in_("organizer_email", accounts)
        res = query.order("meeting_datetime", desc=True).execute()
        data = getattr(res, "data", None)
        if isinstance(data, list):
            # is_structuredフィールドを追加
            for item in data:
                item['is_structured'] = bool(item.get('structured_outputs'))
                # structured_outputsフィールドは除去
                item.pop('structured_outputs', None)
            return data
        return []

    def get_meeting(self, meeting_id: str) -> Dict[str, Any]:
        sb = get_supabase()
        # LEFT JOINで構造化済みかどうかを判定
        res = sb.table(self.TABLE).select(
            "*, structured_outputs!left(meeting_id)"
        ).eq("id", meeting_id).limit(1).execute()
        data = getattr(res, "data", None)
        if isinstance(data, list) and data:
            item = data[0]
            item['is_structured'] = bool(item.get('structured_outputs'))
            item.pop('structured_outputs', None)
            return item
        if isinstance(data, dict):
            data['is_structured'] = bool(data.get('structured_outputs'))
            data.pop('structured_outputs', None)
            return data
        return {}
