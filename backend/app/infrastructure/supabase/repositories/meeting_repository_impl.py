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
        structured: Optional[bool] = None,
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """ページネーション付きの軽量な議事録一覧取得"""
        try:
            sb = get_supabase()
            start = (page - 1) * page_size
            end = start + page_size - 1
            
            # text_contentを除いた軽量なフィールドのみ取得
            select_fields = "id,doc_id,title,meeting_datetime,organizer_email,organizer_name,document_url,invited_emails,created_at,updated_at"
            
            # 検索条件の適用関数
            def apply_filters(query):
                if accounts:
                    query = query.in_("organizer_email", accounts)
                if search_query and search_query.strip():
                    query_term = f"%{search_query.strip()}%"
                    # title、organizer_email、organizer_nameで検索
                    query = query.or_(
                        f"title.ilike.{query_term},"
                        f"organizer_email.ilike.{query_term},"
                        f"organizer_name.ilike.{query_term}"
                    )
                return query

            # 総件数取得
            count_q = sb.table(self.TABLE).select("id", count="exact")
            count_q = apply_filters(count_q)
            count_res = count_q.execute()
            total = getattr(count_res, "count", None) or len(getattr(count_res, "data", []) or [])
            
            # ページ分のみ取得
            page_q = sb.table(self.TABLE).select(select_fields).order("meeting_datetime", desc=True)
            page_q = apply_filters(page_q)
            page_res = page_q.range(start, end).execute()
            items = getattr(page_res, "data", []) or []
            
            # 構造化有無の付与（空配列は照会しない）。長いINクエリを避けるため分割。
            page_ids = [it.get("id") for it in items if it.get("id")]
            structured_meetings: set = set()
            if page_ids:
                chunk_size = 10
                for i in range(0, len(page_ids), chunk_size):
                    sub = page_ids[i:i+chunk_size]
                    s_res = sb.table("structured_outputs").select("meeting_id").in_("meeting_id", sub).execute()
                    s_data = getattr(s_res, "data", []) or []
                    structured_meetings.update({row["meeting_id"] for row in s_data})
                
            for it in items:
                it["is_structured"] = it.get("id") in structured_meetings
            
            # structuredフィルタが指定されていればページ内で間引く
            if structured is not None:
                original_items = items
                items = [it for it in items if it.get("is_structured", False) == structured]
                
                # フィルタした結果が空の場合、より多くのページを取得して再試行
                if len(items) == 0 and len(original_items) > 0:
                    # より多くのデータを取得して再フィルタ
                    extended_size = page_size * 5  # 5倍のサイズで再取得
                    extended_end = start + extended_size - 1
                    
                    extended_q = sb.table(self.TABLE).select(select_fields).order("meeting_datetime", desc=True)
                    extended_q = apply_filters(extended_q)
                    extended_res = extended_q.range(start, extended_end).execute()
                    extended_items = getattr(extended_res, "data", []) or []
                    
                    # 構造化有無の付与（INクエリ分割）
                    extended_ids = [it.get("id") for it in extended_items if it.get("id")]
                    structured_meetings = set()
                    if extended_ids:
                        chunk_size = 20
                        for i in range(0, len(extended_ids), chunk_size):
                            sub = extended_ids[i:i+chunk_size]
                            s_res = sb.table("structured_outputs").select("meeting_id").in_("meeting_id", sub).execute()
                            s_data = getattr(s_res, "data", []) or []
                            structured_meetings.update({row["meeting_id"] for row in s_data})
                        
                        for it in extended_items:
                            it["is_structured"] = it.get("id") in structured_meetings
                        
                        # フィルタして必要な分だけ取得
                        filtered_items = [it for it in extended_items if it.get("is_structured", False) == structured]
                        items = filtered_items[:page_size]
            
            total_pages = max(1, (total + page_size - 1) // page_size)
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            }
        except Exception as e:
            logger.exception("list_meetings_paginated failed: %s", e)
            raise RuntimeError("failed to fetch meetings")  # API層で400へ変換

    def get_meeting_core(self, meeting_id: str) -> Dict[str, Any]:
        sb = get_supabase()
        select_fields = ("id,doc_id,title,meeting_datetime,organizer_email,organizer_name,document_url,invited_emails,text_content,created_at,updated_at")
        res = sb.table(self.TABLE).select(select_fields).eq("id", meeting_id).limit(1).execute()
        data = getattr(res, "data", None)
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        return {}

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
