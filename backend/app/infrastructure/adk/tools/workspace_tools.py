"""
Google Workspace Tools (ADK version) - Gmail and Calendar read-only access.

Provides per-user access to Gmail and Google Calendar via service account
domain-wide delegation. User email is read from tool_context.state["app:user_email"].

Tools:
  Gmail:  search_gmail, get_email_detail, get_email_thread, get_recent_emails
  Calendar: get_today_events, list_calendar_events, search_calendar_events, get_event_detail
"""

from __future__ import annotations

import base64
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# JST timezone
JST = timezone(timedelta(hours=9))

# Lazy singleton for workspace service
_workspace_service = None


def _get_workspace_service():
    """Get GoogleWorkspaceService singleton (lazy init)."""
    global _workspace_service
    if _workspace_service is None:
        from app.infrastructure.google.workspace_service import GoogleWorkspaceService
        from app.infrastructure.config.settings import get_settings
        _workspace_service = GoogleWorkspaceService.get_instance(get_settings())
    return _workspace_service


def _get_user_email(tool_context) -> Optional[str]:
    """Extract user email from tool context state."""
    if tool_context is None:
        return None
    return tool_context.state.get("app:user_email")


def _extract_header(headers: List[Dict], name: str) -> str:
    """Extract a header value from Gmail message headers."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode_body(data: str) -> str:
    """Decode base64url-encoded Gmail message body."""
    if not data:
        return ""
    try:
        padded = data + "=" * (4 - len(data) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_plain_text(payload: Dict) -> str:
    """Extract plain text body from Gmail message payload.

    Priority: text/plain → text/html (stripped) → nested parts.
    """
    mime = payload.get("mimeType", "")

    # Direct text/plain
    if mime == "text/plain":
        body_data = payload.get("body", {}).get("data", "")
        return _decode_body(body_data)

    # Multipart: search parts recursively
    parts = payload.get("parts", [])
    plain_text = ""
    html_text = ""

    for part in parts:
        part_mime = part.get("mimeType", "")
        if part_mime == "text/plain":
            body_data = part.get("body", {}).get("data", "")
            plain_text = _decode_body(body_data)
        elif part_mime == "text/html" and not plain_text:
            body_data = part.get("body", {}).get("data", "")
            html_text = _decode_body(body_data)
        elif part_mime.startswith("multipart/"):
            # Recurse into nested multipart
            nested = _extract_plain_text(part)
            if nested:
                plain_text = nested

    if plain_text:
        return plain_text

    # Fallback: strip HTML tags
    if html_text:
        clean = re.sub(r"<[^>]+>", "", html_text)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    # Last resort: direct body
    body_data = payload.get("body", {}).get("data", "")
    return _decode_body(body_data)


def _has_attachments(payload: Dict) -> bool:
    """Check if message has file attachments."""
    for part in payload.get("parts", []):
        if part.get("filename"):
            return True
        if part.get("parts"):
            if _has_attachments(part):
                return True
    return False


def _format_event(event: Dict) -> Dict[str, Any]:
    """Format a Calendar event for AI consumption."""
    start = event.get("start", {})
    end = event.get("end", {})
    attendees = event.get("attendees", [])

    # Extract Meet link from conferenceData
    meet_link = ""
    conf = event.get("conferenceData", {})
    for ep in conf.get("entryPoints", []):
        if ep.get("entryPointType") == "video":
            meet_link = ep.get("uri", "")
            break

    return {
        "id": event.get("id", ""),
        "summary": event.get("summary", "(タイトルなし)"),
        "start": start.get("dateTime") or start.get("date", ""),
        "end": end.get("dateTime") or end.get("date", ""),
        "location": event.get("location", ""),
        "attendees_count": len(attendees),
        "attendees": [
            {
                "email": a.get("email", ""),
                "name": a.get("displayName", ""),
                "status": a.get("responseStatus", ""),
            }
            for a in attendees[:20]
        ],
        "meet_link": meet_link,
        "status": event.get("status", ""),
        "organizer": event.get("organizer", {}).get("email", ""),
    }


def _jst_now() -> datetime:
    """Get current datetime in JST."""
    return datetime.now(JST)


def _to_rfc3339(dt: datetime) -> str:
    """Convert datetime to RFC 3339 string."""
    return dt.isoformat()


def _parse_date(date_str: str) -> datetime:
    """Parse YYYY-MM-DD string to JST datetime (start of day)."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.replace(tzinfo=JST)


# ============================================================
# Gmail Tools
# ============================================================


def search_gmail(
    query: str,
    max_results: int = 10,
    tool_context=None,
) -> Dict[str, Any]:
    """Gmailを検索。件名・送信者・日付・ラベル等で絞り込み。

    Gmail検索構文をサポート:
    - from:tanaka@bandq.jp（送信者）
    - to:yamada@bandq.jp（宛先）
    - subject:面談（件名）
    - after:2025/01/01, before:2025/12/31（日付範囲）
    - is:unread（未読）
    - has:attachment（添付あり）
    - label:重要（ラベル）
    - 組み合わせ: from:tanaka subject:報告 newer_than:7d

    Args:
        query: Gmail検索クエリ
        max_results: 取得件数（1-20、デフォルト10）

    Returns:
        success: 成功/失敗
        query: 使用した検索クエリ
        total_estimate: 推定ヒット件数
        emails: メールリスト（id, thread_id, subject, from, date, snippet）
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    max_results = max(1, min(20, max_results))

    try:
        svc = _get_workspace_service()
        gmail = svc.get_gmail(user_email)

        result = gmail.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results,
        ).execute()

        messages = result.get("messages", [])
        total_estimate = result.get("resultSizeEstimate", 0)

        if not messages:
            return {
                "success": True,
                "query": query,
                "total_estimate": 0,
                "emails": [],
                "message": "該当するメールが見つかりませんでした。",
            }

        # Batch get metadata for each message
        emails = []
        for msg_ref in messages:
            try:
                msg = gmail.users().messages().get(
                    userId="me",
                    id=msg_ref["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"],
                ).execute()

                headers = msg.get("payload", {}).get("headers", [])
                emails.append({
                    "id": msg["id"],
                    "thread_id": msg.get("threadId", ""),
                    "subject": _extract_header(headers, "Subject"),
                    "from": _extract_header(headers, "From"),
                    "to": _extract_header(headers, "To"),
                    "date": _extract_header(headers, "Date"),
                    "snippet": msg.get("snippet", ""),
                    "labels": msg.get("labelIds", []),
                })
            except Exception as e:
                logger.warning("[search_gmail] Failed to get message %s: %s", msg_ref["id"], e)

        # State tracking
        if tool_context:
            try:
                searches = tool_context.state.get("user:gmail_searches", [])
                searches = searches + [{"query": query, "result_count": len(emails)}]
                if len(searches) > 20:
                    searches = searches[-20:]
                tool_context.state["user:gmail_searches"] = searches
            except Exception:
                pass

        return {
            "success": True,
            "query": query,
            "total_estimate": total_estimate,
            "count": len(emails),
            "emails": emails,
        }

    except Exception as e:
        logger.error("[search_gmail] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"Gmail検索に失敗しました: {type(e).__name__}"}


def get_email_detail(
    message_id: str,
    tool_context=None,
) -> Dict[str, Any]:
    """メール詳細を取得。本文（プレーンテキスト）とヘッダ情報を返す。

    本文は最大3000文字に切り詰め。HTMLメールはプレーンテキスト部分を優先抽出。

    Args:
        message_id: メールID（search_gmailの結果から取得）

    Returns:
        success: 成功/失敗
        message_id: メールID
        thread_id: スレッドID
        subject: 件名
        from_addr: 送信者
        to_addr: 宛先
        date: 日時
        body: 本文（プレーンテキスト、最大3000文字）
        labels: ラベルリスト
        has_attachments: 添付ファイルの有無
        snippet: スニペット
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    try:
        svc = _get_workspace_service()
        gmail = svc.get_gmail(user_email)

        msg = gmail.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()

        payload = msg.get("payload", {})
        headers = payload.get("headers", [])

        body = _extract_plain_text(payload)
        if len(body) > 3000:
            body = body[:3000] + "\n\n...(以下省略、3000文字で切り詰め)"

        return {
            "success": True,
            "message_id": msg["id"],
            "thread_id": msg.get("threadId", ""),
            "subject": _extract_header(headers, "Subject"),
            "from_addr": _extract_header(headers, "From"),
            "to_addr": _extract_header(headers, "To"),
            "cc": _extract_header(headers, "Cc"),
            "date": _extract_header(headers, "Date"),
            "body": body,
            "labels": msg.get("labelIds", []),
            "has_attachments": _has_attachments(payload),
            "snippet": msg.get("snippet", ""),
        }

    except Exception as e:
        logger.error("[get_email_detail] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"メール詳細の取得に失敗しました: {type(e).__name__}"}


def get_email_thread(
    thread_id: str,
    tool_context=None,
) -> Dict[str, Any]:
    """メールスレッド全体を取得。やり取りの流れを時系列で返す。

    各メッセージの本文は最大1000文字に切り詰め。最大20メッセージまで。

    Args:
        thread_id: スレッドID（search_gmailまたはget_email_detailから取得）

    Returns:
        success: 成功/失敗
        thread_id: スレッドID
        subject: スレッド件名
        message_count: メッセージ数
        messages: メッセージリスト（from, to, date, body_preview）
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    try:
        svc = _get_workspace_service()
        gmail = svc.get_gmail(user_email)

        thread = gmail.users().threads().get(
            userId="me",
            id=thread_id,
            format="full",
        ).execute()

        raw_messages = thread.get("messages", [])
        subject = ""
        messages = []

        for msg in raw_messages[:20]:
            payload = msg.get("payload", {})
            headers = payload.get("headers", [])

            if not subject:
                subject = _extract_header(headers, "Subject")

            body = _extract_plain_text(payload)
            if len(body) > 1000:
                body = body[:1000] + "..."

            messages.append({
                "id": msg["id"],
                "from": _extract_header(headers, "From"),
                "to": _extract_header(headers, "To"),
                "date": _extract_header(headers, "Date"),
                "body_preview": body,
            })

        return {
            "success": True,
            "thread_id": thread_id,
            "subject": subject,
            "message_count": len(raw_messages),
            "messages": messages,
        }

    except Exception as e:
        logger.error("[get_email_thread] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"スレッド取得に失敗しました: {type(e).__name__}"}


def get_recent_emails(
    hours: int = 24,
    label: Optional[str] = None,
    max_results: int = 15,
    tool_context=None,
) -> Dict[str, Any]:
    """最近のメールを取得。デフォルト24時間以内。

    Args:
        hours: 遡る時間数（1-168、デフォルト24時間、最大168=1週間）
        label: フィルタするラベル（例: INBOX, SENT, IMPORTANT, STARRED）
        max_results: 取得件数（1-20、デフォルト15）

    Returns:
        success: 成功/失敗
        period: 対象期間の説明
        count: 取得件数
        emails: メールリスト（id, thread_id, subject, from, date, snippet）
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    hours = max(1, min(168, hours))
    max_results = max(1, min(20, max_results))

    try:
        svc = _get_workspace_service()
        gmail = svc.get_gmail(user_email)

        # Build query with time filter
        query_parts = [f"newer_than:{hours}h"]
        if label:
            query_parts.append(f"label:{label}")
        query = " ".join(query_parts)

        result = gmail.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results,
        ).execute()

        messages = result.get("messages", [])

        if not messages:
            return {
                "success": True,
                "period": f"直近{hours}時間",
                "count": 0,
                "emails": [],
                "message": "該当期間のメールはありません。",
            }

        emails = []
        for msg_ref in messages:
            try:
                msg = gmail.users().messages().get(
                    userId="me",
                    id=msg_ref["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"],
                ).execute()

                headers = msg.get("payload", {}).get("headers", [])
                emails.append({
                    "id": msg["id"],
                    "thread_id": msg.get("threadId", ""),
                    "subject": _extract_header(headers, "Subject"),
                    "from": _extract_header(headers, "From"),
                    "date": _extract_header(headers, "Date"),
                    "snippet": msg.get("snippet", ""),
                    "labels": msg.get("labelIds", []),
                })
            except Exception as e:
                logger.warning("[get_recent_emails] Failed to get message %s: %s", msg_ref["id"], e)

        return {
            "success": True,
            "period": f"直近{hours}時間",
            "count": len(emails),
            "emails": emails,
        }

    except Exception as e:
        logger.error("[get_recent_emails] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"最近のメール取得に失敗しました: {type(e).__name__}"}


# ============================================================
# Calendar Tools
# ============================================================


def get_today_events(
    tool_context=None,
) -> Dict[str, Any]:
    """今日の予定を取得。JST基準。

    Returns:
        success: 成功/失敗
        date: 今日の日付（JST）
        count: 予定数
        events: イベントリスト（id, summary, start, end, location, attendees_count, meet_link）
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    try:
        svc = _get_workspace_service()
        calendar = svc.get_calendar(user_email)

        now = _jst_now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        result = calendar.events().list(
            calendarId="primary",
            timeMin=_to_rfc3339(start_of_day),
            timeMax=_to_rfc3339(end_of_day),
            singleEvents=True,
            orderBy="startTime",
            maxResults=50,
        ).execute()

        events = [_format_event(e) for e in result.get("items", [])]

        return {
            "success": True,
            "date": now.strftime("%Y-%m-%d (%a)"),
            "count": len(events),
            "events": events,
        }

    except Exception as e:
        logger.error("[get_today_events] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"今日の予定取得に失敗しました: {type(e).__name__}"}


def list_calendar_events(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    max_results: int = 20,
    tool_context=None,
) -> Dict[str, Any]:
    """カレンダーイベント一覧を取得。期間指定可能。

    日付未指定の場合、今日から7日間のイベントを返す。

    Args:
        date_from: 開始日（YYYY-MM-DD形式）。未指定→今日
        date_to: 終了日（YYYY-MM-DD形式）。未指定→date_from+7日
        max_results: 取得件数（1-50、デフォルト20）

    Returns:
        success: 成功/失敗
        period: 対象期間
        count: 予定数
        events: イベントリスト
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    max_results = max(1, min(50, max_results))

    try:
        svc = _get_workspace_service()
        calendar = svc.get_calendar(user_email)

        now = _jst_now()

        if date_from:
            time_min = _parse_date(date_from)
        else:
            time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if date_to:
            time_max = _parse_date(date_to) + timedelta(days=1)
        else:
            time_max = time_min + timedelta(days=7)

        result = calendar.events().list(
            calendarId="primary",
            timeMin=_to_rfc3339(time_min),
            timeMax=_to_rfc3339(time_max),
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_results,
        ).execute()

        events = [_format_event(e) for e in result.get("items", [])]

        period_from = time_min.strftime("%Y-%m-%d")
        period_to = (time_max - timedelta(days=1)).strftime("%Y-%m-%d")

        return {
            "success": True,
            "period": f"{period_from} ~ {period_to}",
            "count": len(events),
            "events": events,
        }

    except ValueError:
        return {"success": False, "error": "日付形式が不正です。YYYY-MM-DD形式で指定してください。"}
    except Exception as e:
        logger.error("[list_calendar_events] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"カレンダーイベント取得に失敗しました: {type(e).__name__}"}


def search_calendar_events(
    query: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    max_results: int = 15,
    tool_context=None,
) -> Dict[str, Any]:
    """カレンダーイベントを検索。キーワードでタイトル・説明文を絞り込み。

    Args:
        query: 検索キーワード（イベントタイトル・説明に対する部分一致）
        date_from: 検索開始日（YYYY-MM-DD）。未指定→過去30日
        date_to: 検索終了日（YYYY-MM-DD）。未指定→今日+30日
        max_results: 取得件数（1-30、デフォルト15）

    Returns:
        success: 成功/失敗
        query: 検索キーワード
        period: 対象期間
        count: ヒット件数
        events: イベントリスト
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    max_results = max(1, min(30, max_results))

    try:
        svc = _get_workspace_service()
        calendar = svc.get_calendar(user_email)

        now = _jst_now()

        if date_from:
            time_min = _parse_date(date_from)
        else:
            time_min = now - timedelta(days=30)

        if date_to:
            time_max = _parse_date(date_to) + timedelta(days=1)
        else:
            time_max = now + timedelta(days=30)

        result = calendar.events().list(
            calendarId="primary",
            timeMin=_to_rfc3339(time_min),
            timeMax=_to_rfc3339(time_max),
            q=query,
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_results,
        ).execute()

        events = [_format_event(e) for e in result.get("items", [])]

        period_from = time_min.strftime("%Y-%m-%d")
        period_to = time_max.strftime("%Y-%m-%d")

        return {
            "success": True,
            "query": query,
            "period": f"{period_from} ~ {period_to}",
            "count": len(events),
            "events": events,
        }

    except ValueError:
        return {"success": False, "error": "日付形式が不正です。YYYY-MM-DD形式で指定してください。"}
    except Exception as e:
        logger.error("[search_calendar_events] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"カレンダー検索に失敗しました: {type(e).__name__}"}


def get_event_detail(
    event_id: str,
    tool_context=None,
) -> Dict[str, Any]:
    """カレンダーイベント詳細を取得。参加者・場所・説明文・Meet URLなど。

    Args:
        event_id: イベントID（list_calendar_eventsまたはsearch_calendar_eventsの結果から取得）

    Returns:
        success: 成功/失敗
        event_id: イベントID
        summary: タイトル
        start: 開始日時
        end: 終了日時
        location: 場所
        description: 説明文（最大1000文字）
        organizer: 主催者メール
        attendees: 参加者リスト（email, name, status）
        meet_link: Google Meet URL
        status: ステータス（confirmed/tentative/cancelled）
        created: 作成日時
        updated: 更新日時
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    try:
        svc = _get_workspace_service()
        calendar = svc.get_calendar(user_email)

        event = calendar.events().get(
            calendarId="primary",
            eventId=event_id,
        ).execute()

        start = event.get("start", {})
        end = event.get("end", {})
        attendees = event.get("attendees", [])

        # Extract Meet link
        meet_link = ""
        conf = event.get("conferenceData", {})
        for ep in conf.get("entryPoints", []):
            if ep.get("entryPointType") == "video":
                meet_link = ep.get("uri", "")
                break

        # Truncate description
        description = event.get("description", "")
        if len(description) > 1000:
            description = description[:1000] + "\n...(以下省略)"

        return {
            "success": True,
            "event_id": event["id"],
            "summary": event.get("summary", "(タイトルなし)"),
            "start": start.get("dateTime") or start.get("date", ""),
            "end": end.get("dateTime") or end.get("date", ""),
            "location": event.get("location", ""),
            "description": description,
            "organizer": event.get("organizer", {}).get("email", ""),
            "attendees": [
                {
                    "email": a.get("email", ""),
                    "name": a.get("displayName", ""),
                    "status": a.get("responseStatus", ""),
                }
                for a in attendees
            ],
            "meet_link": meet_link,
            "status": event.get("status", ""),
            "created": event.get("created", ""),
            "updated": event.get("updated", ""),
            "recurring": bool(event.get("recurringEventId")),
        }

    except Exception as e:
        logger.error("[get_event_detail] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"イベント詳細の取得に失敗しました: {type(e).__name__}"}


# ============================================================
# Tool Export List
# ============================================================

ADK_GMAIL_TOOLS = [
    search_gmail,
    get_email_detail,
    get_email_thread,
    get_recent_emails,
]

ADK_CALENDAR_TOOLS = [
    get_today_events,
    list_calendar_events,
    search_calendar_events,
    get_event_detail,
]

ADK_WORKSPACE_TOOLS = ADK_GMAIL_TOOLS + ADK_CALENDAR_TOOLS
