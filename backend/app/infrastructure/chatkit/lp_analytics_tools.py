"""
LP流入分析ツール (ChatKit版).

ADK版と同じロジックだが @function_tool + async + RunContextWrapper パターン。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from agents import function_tool, RunContextWrapper

from app.infrastructure.adk.tools.lp_analytics_tools import (
    _get_lp_service,
    _filter_by_period,
    _enrich_row,
    _parse_ym,
)
from app.infrastructure.google.lp_lead_evaluator import classify_channel

logger = logging.getLogger(__name__)


@function_tool(name_override="get_lp_cv_summary")
async def get_lp_cv_summary(
    ctx: RunContextWrapper[Any],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """LP流入のCV数サマリ。スプシSSoTから直接取得。Zoho経由ではない正確な数字。"""
    from app.infrastructure.adk.tools.lp_analytics_tools import get_lp_cv_summary as _impl
    return _impl(date_from=date_from, date_to=date_to)


@function_tool(name_override="get_lp_cv_by_channel")
async def get_lp_cv_by_channel(
    ctx: RunContextWrapper[Any],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """チャネル別LP CV内訳。parentPathベース分類（meta, media, ad等）。"""
    from app.infrastructure.adk.tools.lp_analytics_tools import get_lp_cv_by_channel as _impl
    return _impl(date_from=date_from, date_to=date_to)


@function_tool(name_override="get_lp_interview_bookings")
async def get_lp_interview_bookings(
    ctx: RunContextWrapper[Any],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """面談予約数（カレンダー照合済み）。月別・流入経路別。"""
    from app.infrastructure.adk.tools.lp_analytics_tools import get_lp_interview_bookings as _impl
    return _impl(date_from=date_from, date_to=date_to)


@function_tool(name_override="get_lp_funnel")
async def get_lp_funnel(
    ctx: RunContextWrapper[Any],
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """LP CV → 有効リード → TCV → 面談 のファネル。チャネル絞込可。"""
    from app.infrastructure.adk.tools.lp_analytics_tools import get_lp_funnel as _impl
    return _impl(channel=channel, date_from=date_from, date_to=date_to)


@function_tool(name_override="compare_lp_vs_zoho")
async def compare_lp_vs_zoho(
    ctx: RunContextWrapper[Any],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """スプシCV数 vs Zohoレコード数の差分。データ漏れを可視化。"""
    from app.infrastructure.adk.tools.lp_analytics_tools import compare_lp_vs_zoho as _impl
    return _impl(date_from=date_from, date_to=date_to)


CHATKIT_LP_ANALYTICS_TOOLS = [
    get_lp_cv_summary,
    get_lp_cv_by_channel,
    get_lp_interview_bookings,
    get_lp_funnel,
    compare_lp_vs_zoho,
]
