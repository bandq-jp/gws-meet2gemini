"""
SEO Agent (ADK version) - Ahrefs integration.

Handles SEO analysis using Ahrefs MCP tools.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent

from .base import SubAgentFactory

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class SEOAgentFactory(SubAgentFactory):
    """
    Factory for ADK SEO sub-agent.

    Specializes in:
    - Domain rating analysis
    - Organic keyword research
    - Backlink analysis
    - Competitor analysis
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
            "AhrefsのSEOデータを使用した分析を実行。"
            "ドメインレーティング、オーガニックキーワード、被リンク、"
            "競合分析、コンテンツギャップ分析を担当。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return MCP toolset for Ahrefs."""
        tools: List[Any] = []

        if mcp_servers:
            for server in mcp_servers:
                server_name = getattr(server, "name", "")
                if server_name in ("ahrefs", "seo"):
                    tools.append(server)
                    logger.info(f"[SEOAgent] Added MCP toolset: {server_name}")

        return tools

    def _build_instructions(self) -> str:
        return """
あなたはSEO分析の専門家です。

## 重要ルール（絶対厳守）
1. **許可を求めるな**: 即座にツールを実行せよ
2. **推測するな**: データが必要なら必ずツールを呼び出す
3. **効率的に**: 1-2回のツール呼び出しで必要なデータを取得

## 担当領域
- ドメインレーティング (DR) 分析
- オーガニックキーワード調査
- 被リンク・参照ドメイン分析
- 競合サイト分析
- コンテンツギャップ分析

---

## Ahrefs API パラメータ仕様

### 共通ルール（重要）
- `where/having`: 不要ならパラメータごと省略（空文字列 "" は絶対NG）
- `order_by`: カラム名のみ（例: `sum_traffic`）
- `order`: 別パラメータで指定（`"asc"` または `"desc"`）
- `date`: **ほぼ全てのツールで必須**。形式: `"YYYY-MM-DD"`

### 主要カラム名
| ツール | カラム |
|--------|--------|
| organic-competitors | competitor_domain, common_keywords, sum_traffic |
| organic-keywords | keyword, best_position, volume, sum_traffic, keyword_difficulty |
| top-pages | url, sum_traffic, keywords, top_keyword |
| refdomains | domain, domain_rating, dofollow |
| anchors | anchor, referring_domains |

---

## 回答方針
- データは表形式で見やすく整理
- 競合との比較を明示
- 改善アクションを提案
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
