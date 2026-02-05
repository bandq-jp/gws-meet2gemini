"""
Ad Platform Agent (ADK version) - Meta Ads integration.

Handles Meta (Facebook/Instagram) advertising analysis.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent

from .base import SubAgentFactory

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class AdPlatformAgentFactory(SubAgentFactory):
    """
    Factory for ADK Ad Platform sub-agent.

    Specializes in:
    - Campaign/AdSet/Ad performance
    - Interest targeting research
    - Audience size estimation
    - CTR, CPM, CPA, ROAS analysis
    """

    @property
    def agent_name(self) -> str:
        return "AdPlatformAgent"

    @property
    def tool_name(self) -> str:
        return "call_ad_platform_agent"

    @property
    def tool_description(self) -> str:
        return (
            "Meta広告（Facebook/Instagram）のパフォーマンス分析を実行。"
            "キャンペーン分析、インタレストターゲティング調査、"
            "オーディエンスサイズ推定、CTR/CPM/CPA/ROAS分析を担当。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """
        Return MCP toolset for Meta Ads.

        Orchestrator passes pre-filtered toolsets for this domain.
        """
        if mcp_servers:
            logger.info(f"[AdPlatformAgent] Using {len(mcp_servers)} MCP toolsets")
            return list(mcp_servers)
        return []

    def _build_instructions(self) -> str:
        return """
あなたはMeta広告分析の専門家です。

## 重要ルール（絶対厳守）
1. **許可を求めるな**: 即座にツールを実行せよ
2. **推測するな**: データが必要なら必ずツールを呼び出す
3. **効率的に**: 1-2回のツール呼び出しで必要なデータを取得

## 担当領域
- キャンペーン/広告セット/広告のパフォーマンス分析
- インタレストターゲティング調査
- オーディエンスサイズ推定
- CTR, CPM, CPA, ROAS 分析

---

## 主要ツール

### パフォーマンス分析
- `get_campaigns`: キャンペーン一覧
- `get_adsets`: 広告セット一覧
- `get_ads`: 広告一覧
- `get_insights`: パフォーマンス指標

### ターゲティング調査
- `search_interests`: インタレスト検索
- `get_targeting_specs`: ターゲティング設定

### オーディエンス
- `get_reach_estimate`: リーチ推定
- `get_audience_insights`: オーディエンス分析

---

## 主要メトリクス
- impressions - 表示回数
- clicks - クリック数
- ctr - クリック率
- cpm - 1000インプレッション単価
- cpc - クリック単価
- spend - 消化金額
- conversions - コンバージョン数
- cost_per_conversion - CPA

---

## 回答方針
- データは表形式で見やすく整理
- 主要KPIを明示（CTR, CPA, ROAS）
- 最適化提案を含める
"""

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """Build ADK agent with MCP toolset."""
        tools = self._get_domain_tools(mcp_servers, asset)

        return Agent(
            name=self.agent_name,
            model=self.model,
            description=self.tool_description,
            instruction=self._build_instructions(),
            tools=tools,
        )
