"""
Slack Tools (ADK version) - Slack workspace search and channel history.

Provides read-only access to Slack workspace via dual-token auth.
User Token (xoxp-) for search.messages, Bot Token (xoxb-) for conversations API.

Tools:
  Search: search_slack_messages, search_company_in_slack, search_candidate_in_slack
  History: get_channel_messages, get_thread_replies
  Channels: list_slack_channels
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

# Lazy singleton for Slack service
_slack_service = None


def _get_slack_service():
    """Get SlackService singleton (lazy init)."""
    global _slack_service
    if _slack_service is None:
        from app.infrastructure.slack.slack_service import SlackService
        from app.infrastructure.config.settings import get_settings
        _slack_service = SlackService.get_instance(get_settings())
    return _slack_service


def _build_search_query(
    query: str,
    channel: Optional[str] = None,
    from_user: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> str:
    """Build Slack search query with modifiers."""
    parts = [query]
    if channel:
        ch = channel.lstrip("#").strip()
        parts.append(f"in:#{ch}")
    if from_user:
        user = from_user.lstrip("@").strip()
        parts.append(f"from:@{user}")
    if date_from:
        parts.append(f"after:{date_from}")
    if date_to:
        parts.append(f"before:{date_to}")
    return " ".join(parts)


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max length."""
    if not text or len(text) <= max_len:
        return text or ""
    return text[:max_len] + "..."


def _days_ago_date(days: int) -> str:
    """Get date string N days ago in YYYY-MM-DD format."""
    dt = datetime.now(JST) - timedelta(days=days)
    return dt.strftime("%Y-%m-%d")


# ============================================================
# Core Search Tool
# ============================================================


def search_slack_messages(
    query: str,
    channel: Optional[str] = None,
    from_user: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    max_results: int = 20,
    tool_context=None,
) -> Dict[str, Any]:
    """Slack全体をフルテキスト検索。チャネル横断でメッセージを検索。

    Slack検索構文をサポート:
    - in:#channel-name（チャネル指定）
    - from:@username（送信者指定）
    - after:2026-01-01（日付以降）
    - before:2026-02-01（日付以前）
    - has:link（リンク含む）
    - has:reaction（リアクション付き）
    - 組み合わせ: 企業名 in:#営業 after:2026-01-01

    Args:
        query: 検索キーワード（必須）
        channel: チャネル名で絞り込み（例: 営業、general）
        from_user: 送信者で絞り込み（例: tanaka）
        date_from: 検索開始日（YYYY-MM-DD）
        date_to: 検索終了日（YYYY-MM-DD）
        max_results: 取得件数（1-50、デフォルト20）

    Returns:
        success: 成功/失敗
        query: 使用した検索クエリ
        total: ヒット件数
        count: 返却件数
        messages: メッセージリスト（channel_name, user_name, text, datetime_jst, permalink）
    """
    max_results = max(1, min(50, max_results))

    full_query = _build_search_query(query, channel, from_user, date_from, date_to)

    try:
        svc = _get_slack_service()
        result = svc.search_messages(query=full_query, count=max_results)

        if not result.get("success"):
            return result

        # Truncate message texts
        for msg in result.get("messages", []):
            msg["text"] = _truncate(msg.get("text", ""), 1000)

        # State tracking
        if tool_context:
            try:
                searches = tool_context.state.get("user:slack_searches", [])
                searches = searches + [{
                    "query": full_query,
                    "result_count": result.get("total", 0),
                    "timestamp": datetime.now(JST).isoformat(),
                }]
                if len(searches) > 20:
                    searches = searches[-20:]
                tool_context.state["user:slack_searches"] = searches
            except Exception:
                pass

        return {
            "success": True,
            "query": full_query,
            "total": result.get("total", 0),
            "count": result.get("count", 0),
            "messages": result.get("messages", []),
        }

    except Exception as e:
        logger.error("[search_slack_messages] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"Slack検索に失敗しました: {type(e).__name__}"}


# ============================================================
# Channel History Tool
# ============================================================


def get_channel_messages(
    channel_name_or_id: str,
    hours: int = 24,
    max_results: int = 50,
    tool_context=None,
) -> Dict[str, Any]:
    """特定チャネルの最近のメッセージを取得。

    チャネル名（#なし）またはチャネルIDで指定可能。
    Botがチャネルに参加している必要がある（プライベートチャネルの場合）。

    Args:
        channel_name_or_id: チャネル名（例: general, 営業）またはチャネルID
        hours: 遡る時間数（1-168、デフォルト24時間 = 1日）
        max_results: 取得件数（1-100、デフォルト50）

    Returns:
        success: 成功/失敗
        channel_name: チャネル名
        period: 対象期間の説明
        count: メッセージ数
        messages: メッセージリスト（user_name, text, datetime_jst, thread_ts, reply_count）
    """
    hours = max(1, min(168, hours))
    max_results = max(1, min(100, max_results))

    try:
        svc = _get_slack_service()

        # Resolve channel name to ID
        channel_id = svc.resolve_channel_id(channel_name_or_id)
        if not channel_id:
            return {
                "success": False,
                "error": f"チャンネル '{channel_name_or_id}' が見つかりません。list_slack_channelsでチャネル一覧を確認してください。",
            }

        # Calculate oldest timestamp
        oldest_ts = str(time.time() - (hours * 3600))

        result = svc.get_channel_history(
            channel_id=channel_id,
            oldest=oldest_ts,
            limit=max_results,
        )

        if not result.get("success"):
            return result

        # Truncate message texts
        for msg in result.get("messages", []):
            msg["text"] = _truncate(msg.get("text", ""), 1000)

        # Filter out bot join/leave messages
        messages = [
            msg for msg in result.get("messages", [])
            if msg.get("subtype") not in ("channel_join", "channel_leave", "bot_add", "bot_remove")
        ]

        return {
            "success": True,
            "channel_name": channel_name_or_id.lstrip("#"),
            "channel_id": channel_id,
            "period": f"直近{hours}時間",
            "count": len(messages),
            "has_more": result.get("has_more", False),
            "messages": messages,
        }

    except Exception as e:
        logger.error("[get_channel_messages] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"チャネル履歴の取得に失敗しました: {type(e).__name__}"}


# ============================================================
# Thread Replies Tool
# ============================================================


def get_thread_replies(
    channel_name_or_id: str,
    thread_ts: str,
    tool_context=None,
) -> Dict[str, Any]:
    """スレッドの全返信を取得。

    get_channel_messagesの結果にthread_tsがあるメッセージのスレッドを取得可能。
    親メッセージ + 全返信を時系列で返す。

    Args:
        channel_name_or_id: チャネル名またはチャネルID
        thread_ts: スレッドのタイムスタンプ（get_channel_messagesの結果から取得）

    Returns:
        success: 成功/失敗
        channel_name: チャネル名
        thread_ts: スレッドタイムスタンプ
        reply_count: 返信数（親メッセージ除く）
        messages: メッセージリスト（user_name, text, datetime_jst）
    """
    try:
        svc = _get_slack_service()

        channel_id = svc.resolve_channel_id(channel_name_or_id)
        if not channel_id:
            return {
                "success": False,
                "error": f"チャンネル '{channel_name_or_id}' が見つかりません。",
            }

        result = svc.get_thread_replies(channel_id=channel_id, thread_ts=thread_ts)

        if not result.get("success"):
            return result

        # Truncate message texts
        for msg in result.get("messages", []):
            msg["text"] = _truncate(msg.get("text", ""), 1000)

        return {
            "success": True,
            "channel_name": channel_name_or_id.lstrip("#"),
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "reply_count": result.get("reply_count", 0),
            "messages": result.get("messages", []),
        }

    except Exception as e:
        logger.error("[get_thread_replies] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"スレッド取得に失敗しました: {type(e).__name__}"}


# ============================================================
# Channel List Tool
# ============================================================


def list_slack_channels(
    types: str = "public_channel,private_channel",
    max_results: int = 100,
    tool_context=None,
) -> Dict[str, Any]:
    """アクセス可能なSlackチャネルの一覧を取得。

    パブリック・プライベートチャネルのみ（DMは対象外）。
    プライベートチャネルはBotが参加しているもののみ表示。

    Args:
        types: チャネルタイプ（デフォルト: public_channel,private_channel）
        max_results: 取得件数（1-200、デフォルト100）

    Returns:
        success: 成功/失敗
        count: チャネル数
        channels: チャネルリスト（id, name, topic, purpose, member_count, is_private）
    """
    max_results = max(1, min(200, max_results))

    try:
        svc = _get_slack_service()
        result = svc.list_channels(types=types, limit=max_results)

        if not result.get("success"):
            return result

        return {
            "success": True,
            "count": result.get("count", 0),
            "channels": result.get("channels", [])[:max_results],
        }

    except Exception as e:
        logger.error("[list_slack_channels] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"チャネル一覧の取得に失敗しました: {type(e).__name__}"}


# ============================================================
# High-Level Domain Tools
# ============================================================


def search_company_in_slack(
    company_name: str,
    days_back: int = 30,
    tool_context=None,
) -> Dict[str, Any]:
    """企業名でSlackを横断検索。Fee・条件・最新状況を抽出。

    企業に関するSlack上の言及を検索し、以下を構造化して返す:
    - 言及チャネルと頻度
    - 最新メッセージのサマリー
    - Fee・条件に関する言及

    Args:
        company_name: 企業名（例: ラフロジック、株式会社MyVision）
        days_back: 遡る日数（1-90、デフォルト30）

    Returns:
        success: 成功/失敗
        company_name: 検索した企業名
        period: 検索期間
        mention_count: 言及数
        channels_mentioned: 言及されたチャネルリスト
        messages: 関連メッセージ（最大20件、text最大500文字）
    """
    days_back = max(1, min(90, days_back))
    date_from = _days_ago_date(days_back)

    try:
        svc = _get_slack_service()
        full_query = f"{company_name} after:{date_from}"
        result = svc.search_messages(query=full_query, count=30, sort="timestamp", sort_dir="desc")

        if not result.get("success"):
            return result

        raw_messages = result.get("messages", [])

        # Extract unique channels mentioned
        channels_seen: Dict[str, int] = {}
        for msg in raw_messages:
            ch_name = msg.get("channel_name", "")
            if ch_name:
                channels_seen[ch_name] = channels_seen.get(ch_name, 0) + 1

        channels_mentioned = [
            {"name": name, "mention_count": count}
            for name, count in sorted(channels_seen.items(), key=lambda x: -x[1])
        ]

        # Truncate and limit messages
        messages = []
        for msg in raw_messages[:20]:
            messages.append({
                "channel_name": msg.get("channel_name", ""),
                "user_name": msg.get("user_name", ""),
                "text": _truncate(msg.get("text", ""), 500),
                "datetime_jst": msg.get("datetime_jst", ""),
                "permalink": msg.get("permalink", ""),
            })

        return {
            "success": True,
            "company_name": company_name,
            "period": f"直近{days_back}日間",
            "mention_count": result.get("total", 0),
            "channels_mentioned": channels_mentioned,
            "count": len(messages),
            "messages": messages,
        }

    except Exception as e:
        logger.error("[search_company_in_slack] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"企業Slack検索に失敗しました: {type(e).__name__}"}


def search_candidate_in_slack(
    candidate_name: str,
    days_back: int = 30,
    tool_context=None,
) -> Dict[str, Any]:
    """候補者名でSlackを横断検索。進捗・状況・やりとりを抽出。

    候補者に関するSlack上の言及を検索し、以下を構造化して返す:
    - 言及チャネルと頻度
    - 最新の進捗情報
    - 関連するやりとりのサマリー

    Args:
        candidate_name: 候補者名（例: 山田太郎、山川マイケル風太）
        days_back: 遡る日数（1-90、デフォルト30）

    Returns:
        success: 成功/失敗
        candidate_name: 検索した候補者名
        period: 検索期間
        mention_count: 言及数
        channels_mentioned: 言及されたチャネルリスト
        messages: 関連メッセージ（最大20件、text最大500文字）
    """
    days_back = max(1, min(90, days_back))
    date_from = _days_ago_date(days_back)

    try:
        svc = _get_slack_service()
        full_query = f"{candidate_name} after:{date_from}"
        result = svc.search_messages(query=full_query, count=30, sort="timestamp", sort_dir="desc")

        if not result.get("success"):
            return result

        raw_messages = result.get("messages", [])

        # Extract unique channels mentioned
        channels_seen: Dict[str, int] = {}
        for msg in raw_messages:
            ch_name = msg.get("channel_name", "")
            if ch_name:
                channels_seen[ch_name] = channels_seen.get(ch_name, 0) + 1

        channels_mentioned = [
            {"name": name, "mention_count": count}
            for name, count in sorted(channels_seen.items(), key=lambda x: -x[1])
        ]

        # Truncate and limit messages
        messages = []
        for msg in raw_messages[:20]:
            messages.append({
                "channel_name": msg.get("channel_name", ""),
                "user_name": msg.get("user_name", ""),
                "text": _truncate(msg.get("text", ""), 500),
                "datetime_jst": msg.get("datetime_jst", ""),
                "permalink": msg.get("permalink", ""),
            })

        return {
            "success": True,
            "candidate_name": candidate_name,
            "period": f"直近{days_back}日間",
            "mention_count": result.get("total", 0),
            "channels_mentioned": channels_mentioned,
            "count": len(messages),
            "messages": messages,
        }

    except Exception as e:
        logger.error("[search_candidate_in_slack] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"候補者Slack検索に失敗しました: {type(e).__name__}"}


# ============================================================
# Tool Export List
# ============================================================

ADK_SLACK_TOOLS = [
    search_slack_messages,
    get_channel_messages,
    get_thread_replies,
    list_slack_channels,
    search_company_in_slack,
    search_candidate_in_slack,
]
