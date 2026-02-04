"""
SEO Agent - Ahrefs integration.

Handles SEO analysis, keyword research, and competitive intelligence.
Tools: 20 MCP tools + native tools
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from agents import Agent, HostedMCPTool, ModelSettings
from openai.types.shared.reasoning import Reasoning

from .base import SubAgentFactory
from ..seo_agent_factory import AHREFS_ALLOWED_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings


class SEOAgentFactory(SubAgentFactory):
    """
    Factory for SEO sub-agent.

    Specializes in:
    - Ahrefs SEO analysis
    - Keyword research
    - Backlink analysis
    - Competitive intelligence
    """

    @property
    def agent_name(self) -> str:
        return "SEOAgent"

    @property
    def tool_name(self) -> str:
        return "call_seo_agent"

    @property
    def tool_description(self) -> str:
        return (
            "Ahrefs SEO分析、キーワード調査、バックリンク分析、競合サイト調査。"
            "ドメイン評価、オーガニックキーワード、被リンクプロファイルを分析。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return Ahrefs MCP tools (always hosted, no local MCP)."""
        tools: List[Any] = []

        # Ahrefs is always hosted (no local MCP implementation)
        if (
            self._settings.ahrefs_mcp_server_url
            and self._settings.ahrefs_mcp_authorization
        ):
            tools.append(
                HostedMCPTool(
                    tool_config={
                        "type": "mcp",
                        "server_label": "Ahrefs",
                        "server_url": self._settings.ahrefs_mcp_server_url,
                        "allowed_tools": AHREFS_ALLOWED_TOOLS,
                        "require_approval": "never",
                        "authorization": self._settings.ahrefs_mcp_authorization,
                    }
                )
            )

        return tools

    def _build_instructions(self) -> str:
        return """
あなたはSEO分析と競合調査の専門家です。

## 担当領域
- ドメイン分析（DR、トラフィック、キーワード）
- キーワードリサーチ
- バックリンク分析
- 競合サイト調査

## 利用可能なツール (20個)

### Site Explorer (10個)
- site-explorer-domain-rating: ドメイン評価
- site-explorer-metrics: サイト指標
- site-explorer-organic-keywords: オーガニックキーワード
- site-explorer-top-pages: 上位ページ
- site-explorer-pages-by-traffic: トラフィック別ページ
- site-explorer-organic-competitors: オーガニック競合
- site-explorer-backlinks-stats: 被リンク統計
- site-explorer-refdomains: 参照ドメイン
- site-explorer-all-backlinks: 全被リンク
- site-explorer-anchors: アンカーテキスト

### Keywords Explorer (5個)
- keywords-explorer-overview: キーワード概要
- keywords-explorer-related-terms: 関連キーワード
- keywords-explorer-matching-terms: マッチングキーワード
- keywords-explorer-volume-history: 検索ボリューム推移
- keywords-explorer-search-suggestions: 検索サジェスト

### Site Audit (2個)
- site-audit-issues: サイト問題点
- site-audit-page-explorer: ページエクスプローラー

### Rank Tracker (1個)
- rank-tracker-overview: ランキング概要

### Batch & Usage (2個)
- batch-analysis-batch-analysis: バッチ分析
- subscription-info-limits-and-usage: API使用状況

## 回答方針
- DR、トラフィック、キーワード数などのKPIを明示
- 競合比較を表形式で提示
- アクション可能な改善提案を含める
- 最新SEOトレンドはWeb Searchで補足
"""
