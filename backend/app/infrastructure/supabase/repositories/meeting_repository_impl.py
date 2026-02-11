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
        # text_content を除外し、変更チェックに必要な id, metadata のみ取得（エグレス削減）
        res = sb.table(self.TABLE).select("id,metadata").eq("doc_id", doc_id).eq("organizer_email", organizer_email).limit(1).execute()
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
        # returning="minimal" でレスポンスからtext_content等を除外（エグレス削減）
        sb.table(self.TABLE).upsert(
            payload, on_conflict="doc_id,organizer_email", returning="minimal"
        ).execute()
        return {}

    def list_meetings(self, accounts: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        sb = get_supabase()
        # text_contentを除外した軽量フィールドのみ取得（エグレス削減）
        select_fields = "id,doc_id,title,meeting_datetime,organizer_email,organizer_name,document_url,invited_emails,created_at,updated_at"
        query = sb.table(self.TABLE).select(select_fields)
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
        search_query: Optional[str] = None,
        zoho_sync_failed: Optional[bool] = None
    ) -> Dict[str, Any]:
        """ページネーション付きの軽量な議事録一覧取得

        structured / zoho_sync_failed フィルタは structured_outputs テーブルから
        対象 meeting_id を事前取得し、SQLレベルで適用する。
        これにより total / total_pages が正確になり、各ページが page_size 件になる。
        """
        try:
            sb = get_supabase()
            start = (page - 1) * page_size
            end = start + page_size - 1

            select_fields = "id,doc_id,title,meeting_datetime,organizer_email,organizer_name,document_url,invited_emails,created_at,updated_at"

            empty_response = {
                "items": [], "total": 0, "page": page,
                "page_size": page_size, "total_pages": 1,
                "has_next": False, "has_previous": False,
            }

            # --- 1. structured_outputs から事前フィルタ用 meeting_id を取得 ---
            include_ids: Optional[List[str]] = None   # .in_("id", ...) 用
            exclude_ids: Optional[List[str]] = None   # NOT IN 用

            if zoho_sync_failed is True:
                failed_statuses = ['failed', 'auth_error', 'field_mapping_error', 'error']
                s_res = sb.table("structured_outputs").select("meeting_id").in_("zoho_sync_status", failed_statuses).execute()
                s_data = getattr(s_res, "data", []) or []
                include_ids = [row["meeting_id"] for row in s_data]
                if not include_ids:
                    return empty_response

            if structured is True:
                s_res = sb.table("structured_outputs").select("meeting_id").execute()
                s_data = getattr(s_res, "data", []) or []
                structured_set = set(row["meeting_id"] for row in s_data)
                if include_ids is not None:
                    # zoho_sync_failed との交差
                    include_ids = [mid for mid in include_ids if mid in structured_set]
                else:
                    include_ids = list(structured_set)
                if not include_ids:
                    return empty_response
            elif structured is False:
                s_res = sb.table("structured_outputs").select("meeting_id").execute()
                s_data = getattr(s_res, "data", []) or []
                exclude_ids = [row["meeting_id"] for row in s_data]

            # --- 2. フィルタ適用関数 ---
            def apply_filters(query):
                if accounts:
                    query = query.in_("organizer_email", accounts)
                if search_query and search_query.strip():
                    query_term = f"%{search_query.strip()}%"
                    query = query.or_(
                        f"title.ilike.{query_term},"
                        f"organizer_email.ilike.{query_term},"
                        f"organizer_name.ilike.{query_term}"
                    )
                if include_ids is not None:
                    query = query.in_("id", include_ids)
                if exclude_ids:
                    ids_csv = ",".join(exclude_ids)
                    query = query.filter("id", "not.in", f"({ids_csv})")
                return query

            # --- 3. 総件数取得 ---
            count_q = sb.table(self.TABLE).select("id", count="exact")
            count_q = apply_filters(count_q)
            count_res = count_q.execute()
            total = getattr(count_res, "count", None) or len(getattr(count_res, "data", []) or [])

            if total == 0:
                return empty_response

            # --- 4. ページデータ取得 ---
            page_q = sb.table(self.TABLE).select(select_fields).order("meeting_datetime", desc=True)
            page_q = apply_filters(page_q)
            page_res = page_q.range(start, end).execute()
            items = getattr(page_res, "data", []) or []

            # --- 5. 構造化有無とZoho同期ステータスの付与 ---
            page_ids = [it.get("id") for it in items if it.get("id")]
            structured_meetings: set = set()
            zoho_sync_statuses: Dict[str, str] = {}
            if page_ids:
                s_res = sb.table("structured_outputs").select("meeting_id,zoho_sync_status").in_("meeting_id", page_ids).execute()
                s_data = getattr(s_res, "data", []) or []
                for row in s_data:
                    structured_meetings.add(row["meeting_id"])
                    zoho_sync_statuses[row["meeting_id"]] = row.get("zoho_sync_status")

            for it in items:
                meeting_id = it.get("id")
                it["is_structured"] = meeting_id in structured_meetings
                it["zoho_sync_status"] = zoho_sync_statuses.get(meeting_id)

            # --- 6. レスポンス ---
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
            raise RuntimeError("failed to fetch meetings")

    def get_meetings_core_batch(self, meeting_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """複数会議のコアデータを一括取得（text_content含む）

        Returns:
            meeting_id -> meeting data の辞書
        """
        if not meeting_ids:
            return {}
        sb = get_supabase()
        select_fields = "id,doc_id,title,meeting_datetime,organizer_email,organizer_name,document_url,invited_emails,text_content,created_at,updated_at"
        res = sb.table(self.TABLE).select(select_fields).in_("id", meeting_ids).execute()
        data = getattr(res, "data", None)
        if isinstance(data, list):
            return {item["id"]: item for item in data if item.get("id")}
        return {}

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
        # 明示的カラム指定で取得（エグレス削減）
        select_fields = "id,doc_id,title,meeting_datetime,organizer_email,organizer_name,document_url,invited_emails,text_content,metadata,created_at,updated_at"
        res = sb.table(self.TABLE).select(select_fields).eq("id", meeting_id).limit(1).execute()
        data = getattr(res, "data", None)

        item = None
        if isinstance(data, list) and data:
            item = data[0]
        elif isinstance(data, dict):
            item = data

        if not item:
            return {}

        # 構造化データの存在をチェック（1回のみ）
        structured_res = sb.table("structured_outputs").select("meeting_id").eq("meeting_id", meeting_id).limit(1).execute()
        structured_data = getattr(structured_res, "data", None)
        item['is_structured'] = bool(structured_data and len(structured_data) > 0)
        return item

    def update_transcript(
        self,
        meeting_id: str,
        text_content: str,
        transcript_provider: Optional[str] = None,
        transcript_source: str = "manual_edit",
    ) -> Dict[str, Any]:
        """議事録本文を上書きする。metadataにtranscript_providerを残す。"""
        sb = get_supabase()

        # 既存metadataのみ軽量取得（get_meeting()の重いstructuredチェックを回避）
        meta_res = sb.table(self.TABLE).select("id,metadata").eq("id", meeting_id).limit(1).execute()
        meta_data = getattr(meta_res, "data", None)
        existing = (meta_data[0] if isinstance(meta_data, list) and meta_data
                    else meta_data if isinstance(meta_data, dict) else None)
        if not existing:
            return {}

        metadata = existing.get("metadata") or {}
        if transcript_provider:
            metadata = {**metadata, "transcript_provider": transcript_provider}

        payload = {
            "text_content": text_content,
            "metadata": metadata,
        }

        sb.table(self.TABLE).update(payload, returning="minimal").eq("id", meeting_id).execute()
        # 更新後のデータを返す
        return self.get_meeting(meeting_id)
