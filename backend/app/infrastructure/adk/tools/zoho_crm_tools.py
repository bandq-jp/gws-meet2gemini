"""
Zoho CRM Tools for Google ADK.

ADK-native tool definitions for Zoho CRM operations.
These are plain Python functions that ADK will automatically wrap.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.infrastructure.zoho.client import ZohoClient, ZohoAuthError

logger = logging.getLogger(__name__)

# Channel definitions
CHANNEL_DEFINITIONS = {
    "sco_bizreach": "BizReachスカウト",
    "sco_dodaX": "dodaXスカウト",
    "sco_ambi": "Ambiスカウト",
    "sco_rikunavi": "リクナビスカウト",
    "sco_nikkei": "日経転職版スカウト",
    "sco_liiga": "外資就活ネクスト",
    "sco_openwork": "OpenWorkスカウト",
    "sco_carinar": "Carinarスカウト",
    "sco_dodaX_D&P": "dodaXダイヤモンド/プラチナ",
    "paid_google": "Googleリスティング広告",
    "paid_meta": "Meta広告（Facebook/Instagram）",
    "paid_affiliate": "アフィリエイト広告",
    "org_hitocareer": "SEOメディア（hitocareer）",
    "org_jobs": "自社求人サイト",
    "feed_indeed": "Indeed",
    "referral": "紹介",
    "other": "その他",
}

# Status definitions
STATUS_DEFINITIONS = {
    "1. リード": "初期獲得状態",
    "2. コンタクト": "連絡済み",
    "3. 面談待ち": "面談予約済み",
    "4. 面談済み": "面談完了",
    "5. 提案中": "求人提案中",
    "6. 応募意思獲得": "応募意思獲得",
    "7. 打診済み": "企業へ打診済み",
    "8. 一次面接待ち": "一次面接待ち",
    "9. 一次面接済み": "一次面接済み",
    "10. 最終面接待ち": "最終面接待ち",
    "11. 最終面接済み": "最終面接済み",
    "12. 内定": "内定獲得",
    "13. 内定承諾": "内定承諾",
    "14. 入社": "入社決定",
}


def get_channel_definitions() -> Dict[str, Any]:
    """
    Get channel and status definitions for reference.

    Returns:
        Dictionary with channel_definitions and status_definitions
    """
    return {
        "channel_definitions": CHANNEL_DEFINITIONS,
        "status_definitions": STATUS_DEFINITIONS,
    }


def search_job_seekers(
    channel: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Search job seekers in Zoho CRM.

    Args:
        channel: Channel code (paid_meta, sco_bizreach, etc.)
        status: Status string ("1. リード", etc.)
        name: Name for partial match
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        limit: Max results (max 100)

    Returns:
        Dictionary with count and records
    """
    logger.info(f"[ADK Zoho] search_job_seekers: channel={channel}, status={status}")

    try:
        zoho = ZohoClient()
        results = zoho.search_by_criteria(
            channel=channel,
            status=status,
            name=name,
            date_from=date_from,
            date_to=date_to,
            limit=min(limit, 100),
        )
        return {
            "count": len(results),
            "records": results[:limit],
        }
    except ZohoAuthError as e:
        logger.error(f"[ADK Zoho] Auth error: {e}")
        return {"error": "認証エラー。管理者に連絡してください。"}
    except Exception as e:
        logger.error(f"[ADK Zoho] Error: {e}")
        return {"error": str(e)}


def aggregate_by_channel(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Aggregate job seekers by channel.

    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)

    Returns:
        Dictionary with channel counts
    """
    logger.info(f"[ADK Zoho] aggregate_by_channel: {date_from} to {date_to}")

    try:
        zoho = ZohoClient()
        results = zoho.count_by_channel(date_from=date_from, date_to=date_to)
        return {
            "aggregation": results,
            "total": sum(results.values()) if isinstance(results, dict) else 0,
        }
    except ZohoAuthError as e:
        return {"error": "認証エラー"}
    except Exception as e:
        return {"error": str(e)}


def count_job_seekers_by_status(
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Count job seekers by status (funnel analysis).

    Args:
        channel: Optional channel filter
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)

    Returns:
        Dictionary with status counts
    """
    logger.info(f"[ADK Zoho] count_by_status: channel={channel}")

    try:
        zoho = ZohoClient()
        results = zoho.count_by_status(
            channel=channel,
            date_from=date_from,
            date_to=date_to,
        )
        return {
            "status_counts": results,
            "total": sum(results.values()) if isinstance(results, dict) else 0,
        }
    except Exception as e:
        return {"error": str(e)}


# List of ADK-compatible tools
ADK_ZOHO_CRM_TOOLS = [
    get_channel_definitions,
    search_job_seekers,
    aggregate_by_channel,
    count_job_seekers_by_status,
]
