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
        # 構造化済みかどうかを判定するため、structured_outputsテーブルを別途チェック
        query = sb.table(self.TABLE).select("*")
        if accounts:
            query = query.in_("organizer_email", accounts)
        res = query.order("meeting_datetime", desc=True).execute()
        data = getattr(res, "data", None)
        
        if isinstance(data, list):
            # 各meeting_idに対してstructured_outputsの存在をチェック
            meeting_ids = [item.get('id') for item in data if item.get('id')]
            structured_meetings = set()
            
            if meeting_ids:
                # 構造化データが存在するmeeting_idを取得
                structured_res = sb.table("structured_outputs").select("meeting_id").in_("meeting_id", meeting_ids).execute()
                structured_data = getattr(structured_res, "data", None)
                if isinstance(structured_data, list):
                    structured_meetings = {item['meeting_id'] for item in structured_data}
            
            # is_structuredフィールドを追加
            for item in data:
                item['is_structured'] = item.get('id') in structured_meetings
            return data
        return []
    
    def list_meetings_paginated(
        self, 
        page: int = 1, 
        page_size: int = 40,
        accounts: Optional[List[str]] = None,
        structured: Optional[bool] = None
    ) -> Dict[str, Any]:
        """ページネーション付きの軽量な議事録一覧取得"""
        sb = get_supabase()
        
        # text_contentを除いた軽量なフィールドのみ取得
        select_fields = """
            id, doc_id, title, meeting_datetime, organizer_email, organizer_name, 
            document_url, invited_emails, created_at, updated_at
        """
        
        # ベースクエリ
        base_query = sb.table(self.TABLE).select(select_fields)
        
        # アカウントフィルタ
        if accounts:
            base_query = base_query.in_("organizer_email", accounts)
        
        # 総件数を取得（structuredフィルタ適用前）
        count_res = base_query.execute()
        all_items = getattr(count_res, "data", [])
        
        if not isinstance(all_items, list):
            all_items = []
            
        # 構造化状況の判定
        meeting_ids = [item.get('id') for item in all_items if item.get('id')]
        structured_meetings = set()
        
        if meeting_ids:
            structured_res = sb.table("structured_outputs").select("meeting_id").in_("meeting_id", meeting_ids).execute()
            structured_data = getattr(structured_res, "data", None)
            if isinstance(structured_data, list):
                structured_meetings = {item['meeting_id'] for item in structured_data}
        
        # is_structuredフィールドを追加
        for item in all_items:
            item['is_structured'] = item.get('id') in structured_meetings
        
        # 構造化状況でフィルタ
        if structured is not None:
            all_items = [item for item in all_items if item.get('is_structured', False) == structured]
        
        # 日付順でソート
        all_items.sort(key=lambda x: x.get('meeting_datetime') or x.get('created_at') or '', reverse=True)
        
        # ページネーション計算
        total = len(all_items)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        start = (page - 1) * page_size
        end = start + page_size
        
        items = all_items[start:end]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }

    def get_meeting(self, meeting_id: str) -> Dict[str, Any]:
        sb = get_supabase()
        # 会議データを取得
        res = sb.table(self.TABLE).select("*").eq("id", meeting_id).limit(1).execute()
        data = getattr(res, "data", None)
        
        if isinstance(data, list) and data:
            item = data[0]
            # 構造化データの存在をチェック
            structured_res = sb.table("structured_outputs").select("meeting_id").eq("meeting_id", meeting_id).limit(1).execute()
            structured_data = getattr(structured_res, "data", None)
            item['is_structured'] = bool(structured_data and len(structured_data) > 0)
            return item
        elif isinstance(data, dict):
            # 構造化データの存在をチェック
            structured_res = sb.table("structured_outputs").select("meeting_id").eq("meeting_id", meeting_id).limit(1).execute()
            structured_data = getattr(structured_res, "data", None)
            data['is_structured'] = bool(structured_data and len(structured_data) > 0)
            return data
        return {}
