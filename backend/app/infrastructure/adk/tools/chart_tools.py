"""
Chart rendering tools for Google ADK.

ADK-native tool definitions for chart rendering.
These are plain Python functions that ADK will automatically wrap.

Note: ADK does not have an equivalent to OpenAI's ToolContext with emit_event.
Instead, charts are returned as structured data that the orchestrator can process.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def render_chart(chart_spec: str) -> Dict[str, Any]:
    """チャートを描画する。数値データは必ずこのツールで可視化せよ。JSONをテキスト出力するな。

    Args:
        chart_spec: チャート仕様のJSON文字列。例:
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
        チャート描画結果（JSON形式で返し、フロントエンドでレンダリング）
    """
    try:
        spec = json.loads(chart_spec)
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "チャート仕様のJSON解析に失敗しました",
        }

    if not isinstance(spec, dict) or "type" not in spec or "data" not in spec:
        return {
            "success": False,
            "error": "チャート仕様に type と data が必要です",
        }

    logger.info(f"[ADK Chart] Rendering chart: type={spec.get('type')}, title={spec.get('title')}")

    # Return chart spec with success marker
    # The agent_service will detect this and emit a chart event
    return {
        "success": True,
        "_chart_spec": spec,  # Special marker for chart rendering
        "message": f"チャート「{spec.get('title', '')}」を描画しました。",
    }


# List of ADK-compatible chart tools
ADK_CHART_TOOLS = [render_chart]
