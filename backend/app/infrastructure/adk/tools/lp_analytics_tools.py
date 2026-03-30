"""
LP流入分析ツール (ADK版).

スプレッドシート(responses02)を直接読み取り、GAS/スプシと同じCV数を返す。
Zoho CRMを経由しないSSoTアクセス。
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from google.adk.tools.tool_context import ToolContext

from app.infrastructure.google.lp_lead_evaluator import (
    calc_age,
    classify_channel,
    extract_utm_params,
    is_tcv,
    is_test_row,
    is_valid_lead,
)

logger = logging.getLogger(__name__)

# Singleton
_lp_service_instance = None


def _get_lp_service():
    global _lp_service_instance
    if _lp_service_instance is None:
        from app.infrastructure.config.settings import get_settings
        from app.infrastructure.google.lp_sheets_service import LPSheetsService
        _lp_service_instance = LPSheetsService(get_settings())
    return _lp_service_instance


def _parse_ym(timestamp: str) -> str:
    """タイムスタンプから YYYYMM を抽出."""
    ts = timestamp.strip()
    if not ts:
        return ""
    # "2025-10-15 12:34:56" or "2025/10/15 12:34:56" or "10/15/2025 ..."
    for fmt in [r"(\d{4})[-/](\d{1,2})", r"(\d{1,2})/(\d{1,2})/(\d{4})"]:
        import re
        m = re.match(fmt, ts)
        if m:
            groups = m.groups()
            if len(groups) == 2:
                return f"{groups[0]}{int(groups[1]):02d}"
            elif len(groups) == 3:
                return f"{groups[2]}{int(groups[0]):02d}"
    return ""


def _filter_by_period(
    rows: List[Dict[str, Any]],
    date_from: Optional[str],
    date_to: Optional[str],
) -> List[Dict[str, Any]]:
    """日付範囲でフィルタ (YYYY-MM-DD)."""
    if not date_from and not date_to:
        return rows

    result = []
    for row in rows:
        ts = row.get("timestamp", "")[:10]
        if date_from and ts < date_from:
            continue
        if date_to and ts > date_to:
            continue
        result.append(row)
    return result


def _enrich_row(row: Dict[str, Any], criteria: Dict[str, Any]) -> Dict[str, Any]:
    """行に有効リード/TCV/チャネル等の計算フィールドを追加."""
    age = calc_age(row.get("birthdate", ""))
    locations = row.get("location", "")
    salesexp = row.get("salesexp", "")
    parent_path = row.get("parent_path", "")

    row["age"] = age
    row["channel"] = classify_channel(parent_path)
    row["is_test"] = is_test_row(row.get("fullname", ""), row.get("email", ""))
    row["is_valid_lead"] = is_valid_lead(age, locations, criteria.get("valid_lead"))
    row["is_tcv"] = is_tcv(age, locations, salesexp, criteria.get("tcv"))
    row["has_interview"] = bool(row.get("interview_date"))
    row["has_zoho_id"] = bool(row.get("zoho_id"))
    return row


# ============================================================
# ツール
# ============================================================

def get_lp_cv_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """LP流入のCV数サマリ（月別・全体）。スプレッドシートSSoTから直接取得。

    Zoho CRMではなく、GAS/スプレッドシート（responses02）を直接読み取るため
    データ漏れがない正確なCV数を返す。

    Args:
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)

    Returns:
        success, total, test_excluded, valid_leads, tcv, monthly
    """
    logger.info("[LP] get_lp_cv_summary: %s ~ %s", date_from, date_to)

    try:
        svc = _get_lp_service()
        all_rows = svc.get_responses02()
        criteria = svc.get_valid_lead_criteria()
        rows = _filter_by_period(all_rows, date_from, date_to)

        monthly = defaultdict(lambda: {"total": 0, "real": 0, "valid_lead": 0, "tcv": 0, "with_interview": 0})
        total = test_count = valid_lead_count = tcv_count = interview_count = 0

        for row in rows:
            _enrich_row(row, criteria)
            total += 1
            ym = _parse_ym(row.get("timestamp", ""))

            if row["is_test"]:
                test_count += 1
                continue

            monthly[ym]["total"] += 1
            monthly[ym]["real"] += 1
            if row["is_valid_lead"]:
                valid_lead_count += 1
                monthly[ym]["valid_lead"] += 1
            if row["is_tcv"]:
                tcv_count += 1
                monthly[ym]["tcv"] += 1
            if row["has_interview"]:
                interview_count += 1
                monthly[ym]["with_interview"] += 1

        real = total - test_count
        return {
            "success": True,
            "data_source": "Google Sheets (responses02) — SSoT",
            "period": {"from": date_from or "全期間", "to": date_to or "現在"},
            "total_rows": total,
            "test_excluded": test_count,
            "real_cv": real,
            "valid_leads": valid_lead_count,
            "tcv": tcv_count,
            "with_interview": interview_count,
            "valid_lead_rate": f"{valid_lead_count/real*100:.1f}%" if real > 0 else "N/A",
            "tcv_rate": f"{tcv_count/real*100:.1f}%" if real > 0 else "N/A",
            "monthly": dict(sorted(monthly.items())),
        }
    except Exception as e:
        logger.error("[LP] get_lp_cv_summary error: %s", e)
        return {"success": False, "error": str(e)}


def get_lp_cv_by_channel(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """チャネル別LP CV内訳。parentPathベースの分類（GASと同じロジック）。

    Args:
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)

    Returns:
        success, channels (各チャネルの件数・有効リード・TCV)
    """
    logger.info("[LP] get_lp_cv_by_channel: %s ~ %s", date_from, date_to)

    try:
        svc = _get_lp_service()
        all_rows = svc.get_responses02()
        criteria = svc.get_valid_lead_criteria()
        rows = _filter_by_period(all_rows, date_from, date_to)

        channels = defaultdict(lambda: {"total": 0, "valid_lead": 0, "tcv": 0, "with_interview": 0})

        for row in rows:
            _enrich_row(row, criteria)
            if row["is_test"]:
                continue
            ch = row["channel"]
            channels[ch]["total"] += 1
            if row["is_valid_lead"]:
                channels[ch]["valid_lead"] += 1
            if row["is_tcv"]:
                channels[ch]["tcv"] += 1
            if row["has_interview"]:
                channels[ch]["with_interview"] += 1

        return {
            "success": True,
            "data_source": "Google Sheets (responses02) — SSoT",
            "period": {"from": date_from or "全期間", "to": date_to or "現在"},
            "channels": dict(sorted(channels.items(), key=lambda x: -x[1]["total"])),
            "channel_definitions": {
                "meta": "Meta広告(Facebook/Instagram)経由",
                "media": "SEOメディア(hitocareer.com)経由",
                "ad": "Google広告/アフィリエイト経由",
                "jobs": "自社求人サイト経由",
                "other_lp": "その他LP経由",
                "direct": "直接アクセス",
                "test": "テストページ",
                "other": "分類不能",
            },
        }
    except Exception as e:
        logger.error("[LP] get_lp_cv_by_channel error: %s", e)
        return {"success": False, "error": str(e)}


def get_lp_interview_bookings(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """面談予約数（カレンダー照合済み）。

    Args:
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)

    Returns:
        success, total, monthly, by_source
    """
    logger.info("[LP] get_lp_interview_bookings: %s ~ %s", date_from, date_to)

    try:
        svc = _get_lp_service()
        bookings = svc.get_interview_bookings()

        monthly = Counter()
        by_source = Counter()
        total = 0

        for b in bookings:
            dt = b.get("datetime", "")[:10]
            if date_from and dt < date_from:
                continue
            if date_to and dt > date_to:
                continue
            total += 1
            ym = dt[:4] + dt[5:7] if len(dt) >= 7 else ""
            if ym:
                monthly[ym] += 1
            source = b.get("source", "") or "不明"
            by_source[source] += 1

        return {
            "success": True,
            "data_source": "Google Sheets (面談予約) — カレンダー照合済み",
            "period": {"from": date_from or "全期間", "to": date_to or "現在"},
            "total": total,
            "monthly": dict(sorted(monthly.items())),
            "by_source": dict(by_source.most_common()),
        }
    except Exception as e:
        logger.error("[LP] get_lp_interview_bookings error: %s", e)
        return {"success": False, "error": str(e)}


def get_lp_funnel(
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """LP CV → 有効リード → TCV → 面談予約 のファネル分析。

    Args:
        channel: チャネルフィルタ(meta, media, ad等)
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)

    Returns:
        success, funnel stages with conversion rates
    """
    logger.info("[LP] get_lp_funnel: channel=%s, %s ~ %s", channel, date_from, date_to)

    try:
        svc = _get_lp_service()
        all_rows = svc.get_responses02()
        criteria = svc.get_valid_lead_criteria()
        rows = _filter_by_period(all_rows, date_from, date_to)

        total = valid = tcv = interviewed = with_zoho = 0

        for row in rows:
            _enrich_row(row, criteria)
            if row["is_test"]:
                continue
            if channel and row["channel"] != channel:
                continue
            total += 1
            if row["is_valid_lead"]:
                valid += 1
            if row["is_tcv"]:
                tcv += 1
            if row["has_interview"]:
                interviewed += 1
            if row["has_zoho_id"]:
                with_zoho += 1

        funnel = [
            {"stage": "LP CV（フォーム送信）", "count": total, "rate": "100%"},
            {
                "stage": "有効リード（年齢+勤務地）",
                "count": valid,
                "rate": f"{valid/total*100:.1f}%" if total > 0 else "N/A",
            },
            {
                "stage": "TCV（有効リード+営業経験）",
                "count": tcv,
                "rate": f"{tcv/total*100:.1f}%" if total > 0 else "N/A",
            },
            {
                "stage": "面談予約あり",
                "count": interviewed,
                "rate": f"{interviewed/total*100:.1f}%" if total > 0 else "N/A",
            },
            {
                "stage": "Zoho CRM連携済み",
                "count": with_zoho,
                "rate": f"{with_zoho/total*100:.1f}%" if total > 0 else "N/A",
            },
        ]

        return {
            "success": True,
            "data_source": "Google Sheets (responses02) — SSoT",
            "period": {"from": date_from or "全期間", "to": date_to or "現在"},
            "channel_filter": channel or "全体",
            "funnel": funnel,
            "zoho_gap": total - with_zoho,
            "zoho_gap_note": f"{total - with_zoho}件がスプシにあるがZohoに未到達" if total > with_zoho else None,
        }
    except Exception as e:
        logger.error("[LP] get_lp_funnel error: %s", e)
        return {"success": False, "error": str(e)}


def compare_lp_vs_zoho(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """スプシCV数 vs Zohoレコード数の差分を比較。データ漏れを可視化。

    Args:
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)

    Returns:
        success, spreadsheet counts, zoho_linked counts, gap analysis
    """
    logger.info("[LP] compare_lp_vs_zoho: %s ~ %s", date_from, date_to)

    try:
        svc = _get_lp_service()
        all_rows = svc.get_responses02()
        criteria = svc.get_valid_lead_criteria()
        rows = _filter_by_period(all_rows, date_from, date_to)

        by_channel = defaultdict(lambda: {"total": 0, "with_zoho": 0, "gap": 0})

        for row in rows:
            _enrich_row(row, criteria)
            if row["is_test"]:
                continue
            ch = row["channel"]
            by_channel[ch]["total"] += 1
            if row["has_zoho_id"]:
                by_channel[ch]["with_zoho"] += 1

        for data in by_channel.values():
            data["gap"] = data["total"] - data["with_zoho"]
            data["sync_rate"] = f"{data['with_zoho']/data['total']*100:.0f}%" if data["total"] > 0 else "N/A"

        total_all = sum(d["total"] for d in by_channel.values())
        total_zoho = sum(d["with_zoho"] for d in by_channel.values())

        return {
            "success": True,
            "data_source": "Google Sheets vs Zoho CRM",
            "period": {"from": date_from or "全期間", "to": date_to or "現在"},
            "overall": {
                "spreadsheet_total": total_all,
                "zoho_linked": total_zoho,
                "gap": total_all - total_zoho,
                "sync_rate": f"{total_zoho/total_all*100:.0f}%" if total_all > 0 else "N/A",
            },
            "by_channel": dict(sorted(by_channel.items(), key=lambda x: -x[1]["total"])),
        }
    except Exception as e:
        logger.error("[LP] compare_lp_vs_zoho error: %s", e)
        return {"success": False, "error": str(e)}


# ============================================================
# ツールリスト
# ============================================================

ADK_LP_ANALYTICS_TOOLS = [
    get_lp_cv_summary,
    get_lp_cv_by_channel,
    get_lp_interview_bookings,
    get_lp_funnel,
    compare_lp_vs_zoho,
]
