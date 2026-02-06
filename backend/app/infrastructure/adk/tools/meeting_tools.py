"""
Meeting Notes Tools for Google ADK.

ADK-native tool definitions for accessing meeting transcripts and structured data.
These tools connect Zoho candidates to their meeting notes in Supabase.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.infrastructure.supabase.client import get_supabase

logger = logging.getLogger(__name__)


def search_meetings(
    title_keyword: Optional[str] = None,
    candidate_name: Optional[str] = None,
    organizer_email: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """議事録を検索。候補者名・タイトル・日付で絞り込み。

    candidate_nameとtitleは独立検索（AND条件ではない）。候補者名での検索を優先。

    Args:
        title_keyword: タイトルに含むキーワード（部分一致）
        candidate_name: 候補者名（タイトルまたはZoho連携から検索）
        organizer_email: 主催者メール
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)
        limit: 件数(max50)

    Returns:
        Dict[str, Any]: 検索結果。
            success: True/False
            total: ヒット件数
            meetings: 議事録リスト
            filters: 適用したフィルタ
    """
    logger.info(f"[ADK Meeting] search_meetings: title={title_keyword}, candidate={candidate_name}")

    try:
        sb = get_supabase()
        query = sb.table("meeting_documents").select(
            "id,doc_id,title,meeting_datetime,organizer_email,organizer_name"
        )

        if title_keyword:
            query = query.ilike("title", f"%{title_keyword}%")

        if organizer_email:
            query = query.eq("organizer_email", organizer_email)

        if date_from:
            query = query.gte("meeting_datetime", date_from)

        if date_to:
            query = query.lte("meeting_datetime", date_to)

        query = query.order("meeting_datetime", desc=True).limit(min(limit, 50))
        res = query.execute()

        meetings = res.data or []

        # If candidate_name provided, also search structured_outputs
        if candidate_name and not meetings:
            # Search by zoho_candidate_name in structured_outputs
            struct_query = sb.table("structured_outputs").select(
                "meeting_id, zoho_candidate_name, zoho_record_id"
            ).ilike("zoho_candidate_name", f"%{candidate_name}%").limit(limit)

            struct_res = struct_query.execute()
            struct_data = struct_res.data or []

            if struct_data:
                meeting_ids = [s["meeting_id"] for s in struct_data]
                meeting_res = sb.table("meeting_documents").select(
                    "id,doc_id,title,meeting_datetime,organizer_email,organizer_name"
                ).in_("id", meeting_ids).execute()
                meetings = meeting_res.data or []

        # Check structured status for each meeting
        if meetings:
            meeting_ids = [m["id"] for m in meetings]
            struct_check = sb.table("structured_outputs").select(
                "meeting_id, zoho_candidate_name, zoho_record_id"
            ).in_("meeting_id", meeting_ids).execute()

            struct_map = {s["meeting_id"]: s for s in (struct_check.data or [])}

            for m in meetings:
                struct_info = struct_map.get(m["id"], {})
                m["is_structured"] = m["id"] in struct_map
                m["zoho_candidate_name"] = struct_info.get("zoho_candidate_name")
                m["zoho_record_id"] = struct_info.get("zoho_record_id")

        return {
            "success": True,
            "total": len(meetings),
            "meetings": meetings,
            "filters": {
                "title_keyword": title_keyword,
                "candidate_name": candidate_name,
                "organizer_email": organizer_email,
                "date_range": f"{date_from or '*'} ~ {date_to or '*'}",
            },
        }

    except Exception as e:
        logger.error(f"[ADK Meeting] Error: {e}")
        return {"success": False, "error": str(e)}


def get_meeting_transcript(meeting_id: str) -> Dict[str, Any]:
    """議事録の本文（トランスクリプト）を取得。

    10000文字を超える場合は切り詰めて返す。

    Args:
        meeting_id: 議事録ID（meeting_documentsのid）

    Returns:
        Dict[str, Any]: 議事録本文。
            success: True/False
            meeting_id: 議事録ID
            title: タイトル
            transcript: 本文（10000文字まで）
    """
    logger.info(f"[ADK Meeting] get_meeting_transcript: {meeting_id}")

    if not meeting_id:
        return {"success": False, "error": "meeting_idが必要です"}

    try:
        sb = get_supabase()
        res = sb.table("meeting_documents").select(
            "id,doc_id,title,meeting_datetime,organizer_email,organizer_name,text_content"
        ).eq("id", meeting_id).maybe_single().execute()

        if not res.data:
            return {"success": False, "error": f"議事録が見つかりません: {meeting_id}"}

        meeting = res.data
        # Truncate very long transcripts
        text_content = meeting.get("text_content", "")
        if len(text_content) > 10000:
            text_content = text_content[:10000] + "\n\n... (truncated, full text is longer)"

        return {
            "success": True,
            "meeting_id": meeting_id,
            "title": meeting.get("title"),
            "meeting_datetime": meeting.get("meeting_datetime"),
            "organizer": meeting.get("organizer_name") or meeting.get("organizer_email"),
            "transcript": text_content,
        }

    except Exception as e:
        logger.error(f"[ADK Meeting] Error: {e}")
        return {"success": False, "error": str(e)}


def get_structured_data_for_candidate(
    zoho_record_id: Optional[str] = None,
    candidate_name: Optional[str] = None,
) -> Dict[str, Any]:
    """候補者の構造化データ（AI抽出済み情報）を取得。

    Args:
        zoho_record_id: ZohoレコードID（優先）
        candidate_name: 候補者名（部分一致）

    Returns:
        Dict[str, Any]: 構造化データ。
            success: True/False
            meeting_id: 議事録ID
            candidate_name: 候補者名
            extracted_data: 抽出済みキーフィールド
            full_data: 全抽出データ
    """
    logger.info(f"[ADK Meeting] get_structured_data: record_id={zoho_record_id}, name={candidate_name}")

    if not zoho_record_id and not candidate_name:
        return {"success": False, "error": "zoho_record_id または candidate_name が必要です"}

    try:
        sb = get_supabase()

        if zoho_record_id:
            res = sb.table("structured_outputs").select(
                "meeting_id, data, zoho_candidate_name, zoho_record_id, zoho_sync_status, created_at"
            ).eq("zoho_record_id", zoho_record_id).maybe_single().execute()
        else:
            res = sb.table("structured_outputs").select(
                "meeting_id, data, zoho_candidate_name, zoho_record_id, zoho_sync_status, created_at"
            ).ilike("zoho_candidate_name", f"%{candidate_name}%").limit(1).execute()
            if res.data and isinstance(res.data, list):
                res.data = res.data[0] if res.data else None

        if not res.data:
            return {
                "success": False,
                "error": f"構造化データが見つかりません",
                "hint": "候補者との面談議事録がまだ処理されていない可能性があります"
            }

        structured = res.data
        data = structured.get("data", {})

        # Extract key fields for CA use
        key_fields = {
            "転職活動状況": data.get("transfer_activity_status"),
            "転職希望時期": data.get("desired_timing"),
            "転職理由": data.get("transfer_reasons"),
            "現年収": data.get("current_salary"),
            "希望年収": data.get("desired_first_year_salary"),
            "他社エージェント": data.get("current_agents"),
            "他社オファー年収": data.get("other_offer_salary"),
            "選考中企業": data.get("companies_in_selection"),
            "キャリアビジョン": data.get("career_vision"),
            "希望条件_業種": data.get("desired_industry"),
            "希望条件_職種": data.get("desired_job_type"),
            "希望条件_勤務地": data.get("desired_location"),
            "懸念点": data.get("concerns"),
        }

        # Remove None values
        key_fields = {k: v for k, v in key_fields.items() if v is not None}

        return {
            "success": True,
            "meeting_id": structured.get("meeting_id"),
            "zoho_record_id": structured.get("zoho_record_id"),
            "candidate_name": structured.get("zoho_candidate_name"),
            "zoho_sync_status": structured.get("zoho_sync_status"),
            "extracted_data": key_fields,
            "full_data": data,  # Full extracted data for detailed analysis
        }

    except Exception as e:
        logger.error(f"[ADK Meeting] Error: {e}")
        return {"success": False, "error": str(e)}


def get_candidate_full_profile(zoho_record_id: str) -> Dict[str, Any]:
    """候補者の完全プロファイル取得（Zoho + 議事録構造化データ統合）。

    generate_candidate_briefingとの違い：こちらはZoho+議事録の全情報統合プロファイル。
    面談準備には generate_candidate_briefing を推奨。

    Args:
        zoho_record_id: ZohoレコードID

    Returns:
        Dict[str, Any]: 完全プロファイル。
            success: True/False
            record_id: ZohoレコードID
            profile: 統合プロファイル（basic/from_zoho/from_meeting/meeting_info）
    """
    logger.info(f"[ADK Meeting] get_candidate_full_profile: {zoho_record_id}")

    if not zoho_record_id:
        return {"success": False, "error": "zoho_record_idが必要です"}

    try:
        from app.infrastructure.zoho.client import ZohoClient

        # Get Zoho record
        zoho = ZohoClient()
        zoho_record = zoho.get_app_hc_record(zoho_record_id)

        if not zoho_record:
            return {"success": False, "error": f"Zohoレコードが見つかりません: {zoho_record_id}"}

        # Get structured data
        sb = get_supabase()
        struct_res = sb.table("structured_outputs").select(
            "meeting_id, data, zoho_candidate_name, created_at"
        ).eq("zoho_record_id", zoho_record_id).maybe_single().execute()

        structured_data = struct_res.data.get("data", {}) if struct_res.data else {}

        # Get meeting info
        meeting_info = None
        if struct_res.data and struct_res.data.get("meeting_id"):
            meeting_res = sb.table("meeting_documents").select(
                "title, meeting_datetime, organizer_name"
            ).eq("id", struct_res.data["meeting_id"]).maybe_single().execute()
            if meeting_res.data:
                meeting_info = meeting_res.data

        # Build unified profile
        owner = zoho_record.get("Owner")
        pic_name = owner.get("name") if isinstance(owner, dict) else str(owner) if owner else "未割当"

        profile = {
            "basic": {
                "name": zoho_record.get("Name"),
                "record_id": zoho_record_id,
                "channel": zoho_record.get("field14"),
                "status": zoho_record.get("customer_status"),
                "pic": pic_name,
                "registration_date": zoho_record.get("field18"),
            },
            "from_zoho": {
                "age": zoho_record.get("field15"),
                "gender": zoho_record.get("field16"),
                "current_salary": zoho_record.get("field17"),
                "desired_salary": zoho_record.get("field20"),
                "experience_industry": zoho_record.get("field21"),
                "experience_job": zoho_record.get("field22"),
            },
            "from_meeting": {
                "transfer_status": structured_data.get("transfer_activity_status"),
                "transfer_reasons": structured_data.get("transfer_reasons"),
                "desired_timing": structured_data.get("desired_timing"),
                "other_agents": structured_data.get("current_agents"),
                "other_offer": structured_data.get("other_offer_salary"),
                "companies_in_selection": structured_data.get("companies_in_selection"),
                "career_vision": structured_data.get("career_vision"),
            },
            "meeting_info": meeting_info,
        }

        return {
            "success": True,
            "record_id": zoho_record_id,
            "profile": profile,
        }

    except Exception as e:
        logger.error(f"[ADK Meeting] Error: {e}")
        return {"success": False, "error": str(e)}


# List of ADK-compatible meeting tools
ADK_MEETING_TOOLS = [
    search_meetings,
    get_meeting_transcript,
    get_structured_data_for_candidate,
    get_candidate_full_profile,
]
