"""
Chart rendering function tools for Marketing AI.

Supports: line, bar, area, pie, donut, scatter, radar, funnel, table
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Awaitable

from agents import function_tool
from agents.tool_context import ToolContext

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class MarketingChatContext:
    """Context passed to tool functions via ToolContext."""
    emit_event: Callable[[dict], Awaitable[None]]
    user_id: str
    user_email: str
    conversation_id: str


@function_tool
async def render_chart(
    ctx: ToolContext[MarketingChatContext],
    chart_spec: str,
) -> str:
    """チャットUIにインタラクティブなチャートを描画する。

    データを可視化したい時に使用する。テーブル表示よりもチャートの方が分かりやすい場合に積極的に使用せよ。

    Args:
        chart_spec: チャート仕様のJSON文字列。以下のフォーマット:
            {
                "type": "line|bar|area|pie|donut|scatter|radar|funnel|table",
                "title": "チャートタイトル",
                "description": "補足説明（任意）",
                "data": [{"label": "値1", "metric": 100}, ...],
                "xKey": "X軸のキー名（line/bar/area/scatter用）",
                "yKeys": [{"key": "metric", "label": "表示名", "color": "#3b82f6"}],
                "nameKey": "名前キー（pie/donut用）",
                "valueKey": "値キー（pie/donut用）",
                "columns": [{"key": "col", "label": "列名", "align": "left|right|center"}],
                "categories": ["カテゴリ1", ...],
                "nameField": "名前フィールド（funnel用）",
                "valueField": "値フィールド（funnel用）"
            }
            チャートタイプ別の必須パラメータ:
            - type="line": 時系列トレンド。xKey + yKeys 必須
            - type="bar": カテゴリ比較。xKey + yKeys 必須
            - type="area": 累積/スタックエリア。xKey + yKeys 必須
            - type="pie"/"donut": 構成比。nameKey + valueKey 必須
            - type="scatter": 散布図。xKey + yKeys 必須（yKeys[0]がY軸）
            - type="radar": レーダーチャート。xKey + yKeys 必須
            - type="funnel": ファネル。nameField + valueField 必須
            - type="table": テーブル表示。columns 必須
            - data配列の数値は文字列ではなく数値型で入れること

    Returns:
        チャート描画結果のメッセージ
    """
    try:
        spec = json.loads(chart_spec)
    except json.JSONDecodeError:
        return "(チャート仕様のJSON解析に失敗しました)"

    if not isinstance(spec, dict) or "type" not in spec or "data" not in spec:
        return "(チャート仕様に type と data が必要です)"

    # Emit chart event through context
    await ctx.context.emit_event({"type": "chart", "spec": spec})
    return f"チャート「{spec.get('title', '')}」を描画しました。"


# Export for use in orchestrator
CHART_TOOLS = [render_chart]
