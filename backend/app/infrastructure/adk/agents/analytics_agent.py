"""
Analytics Agent (ADK version) - GA4 + GSC integration.

Handles Google Analytics 4 and Search Console data analysis.
Uses MCP toolsets for GA4 and GSC.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .base import SubAgentFactory

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class AnalyticsAgentFactory(SubAgentFactory):
    """
    Factory for ADK Analytics sub-agent.

    Specializes in:
    - GA4 traffic analysis, reports, real-time data
    - GSC search performance, URL inspection, sitemaps
    """

    @property
    def agent_name(self) -> str:
        return "AnalyticsAgent"

    @property
    def tool_name(self) -> str:
        return "call_analytics_agent"

    @property
    def tool_description(self) -> str:
        return (
            "Google Analytics 4とSearch Consoleのデータ分析を実行。"
            "トラフィック分析、検索パフォーマンス、URLインスペクション、"
            "リアルタイムレポート、期間比較などを担当。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """
        Return MCP toolsets for GA4 and GSC.

        In ADK, MCP toolsets are pre-filtered by the orchestrator
        and passed directly to this agent.
        """
        # Orchestrator passes pre-filtered toolsets for this domain
        if mcp_servers:
            logger.info(f"[AnalyticsAgent] Using {len(mcp_servers)} MCP toolsets")
            return list(mcp_servers)
        return []

    def _build_instructions(self) -> str:
        return """
あなたはWebアナリティクスの専門家です。

## 重要ルール（絶対厳守）
1. **許可を求めるな**: 即座にツールを実行せよ
2. **推測するな**: データが必要なら必ずツールを呼び出す
3. **効率的に**: 1-2回のツール呼び出しで必要なデータを取得

## 担当領域
- **GA4 (Google Analytics 4)**: トラフィック分析、ユーザー行動、コンバージョン
- **GSC (Google Search Console)**: 検索パフォーマンス、インデックス状況、URL検査

## 対象プロパティ
- hitocareer.com (GA4 ID: 423714093)
- achievehr.jp (GA4 ID: 502875325)

---

## GA4 run_report パラメータ仕様

### 必須パラメータ
- `property_id`: "423714093" または "502875325"
- `date_ranges`: 必須！例: [{"start_date": "2026-01-06", "end_date": "2026-02-04"}]
- `metrics`: 有効なメトリクス名のリスト

### 有効なメトリクス
- `sessions` - セッション数
- `activeUsers` - アクティブユーザー
- `screenPageViews` - ページビュー
- `bounceRate` - 直帰率
- `averageSessionDuration` - 平均セッション時間
- `newUsers` - 新規ユーザー
- **注意**: `clicks`, `impressions`はGA4にない。GSCを使え

### 有効なディメンション
- `date` - 日付
- `sessionDefaultChannelGroup` - チャネル
- `deviceCategory` - デバイス
- `country` - 国

---

## GSC get_search_analytics パラメータ仕様

### 必須パラメータ
- `site_url`: "https://hitocareer.com" または "https://achievehr.jp"
- `days`: 日数（例: 30）

### レスポンス
- `clicks` - クリック数
- `impressions` - 表示回数
- `ctr` - クリック率
- `position` - 平均掲載順位

---

## 回答方針
- データは表形式で見やすく整理
- 前期比・推移を可視化
- 改善提案を含める
"""

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """Build ADK agent with MCP toolsets."""
        tools = self._get_domain_tools(mcp_servers, asset)

        return Agent(
            name=self.agent_name,
            model=self.model,
            description=self.tool_description,
            instruction=self._build_instructions(),
            tools=tools,
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    thinking_level="high",
                ),
            ),
        )
