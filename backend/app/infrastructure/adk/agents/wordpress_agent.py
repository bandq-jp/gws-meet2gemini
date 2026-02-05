"""
WordPress Agent (ADK version) - WordPress integration.

Handles WordPress content management for hitocareer and achievehr sites.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent

from .base import SubAgentFactory

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class WordPressAgentFactory(SubAgentFactory):
    """
    Factory for ADK WordPress sub-agent.

    Specializes in:
    - Article listing and search
    - Block structure analysis
    - SEO requirements check
    - Content creation and editing
    """

    @property
    def agent_name(self) -> str:
        return "WordPressAgent"

    @property
    def tool_name(self) -> str:
        return "call_wordpress_agent"

    @property
    def tool_description(self) -> str:
        return (
            "WordPressサイト（hitocareer, achievehr）の記事管理を実行。"
            "記事一覧、ブロック構造分析、SEO要件チェック、"
            "記事作成・編集を担当。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return MCP toolsets for WordPress sites."""
        tools: List[Any] = []

        if mcp_servers:
            for server in mcp_servers:
                server_name = getattr(server, "name", "")
                if server_name in ("wordpress", "wp_hitocareer", "wp_achievehr"):
                    tools.append(server)
                    logger.info(f"[WordPressAgent] Added MCP toolset: {server_name}")

        return tools

    def _build_instructions(self) -> str:
        return """
あなたはWordPressコンテンツ管理の専門家です。

## 重要ルール（絶対厳守）
1. **閲覧系は即実行**: 記事一覧・検索・詳細表示は許可不要で即実行
2. **編集系は確認**: 記事作成・編集・削除は明示的指示があった場合のみ
3. **推測するな**: データが必要なら必ずツールを呼び出す

## 担当領域
- 記事一覧・検索
- ブロック構造分析
- SEO要件チェック
- 記事作成・編集（明示的指示時のみ）

---

## 対象サイト
- hitocareer.com - 転職メディア
- achievehr.jp - HR業界メディア

---

## 主要ツール

### 閲覧系（即実行OK）
- `list_posts`: 記事一覧取得
- `get_post`: 記事詳細取得
- `search_posts`: 記事検索
- `list_categories`: カテゴリ一覧
- `list_tags`: タグ一覧

### 分析系（即実行OK）
- `get_post_blocks`: ブロック構造分析
- `check_seo_requirements`: SEO要件チェック

### 編集系（明示的指示のみ）
- `create_post`: 記事作成
- `update_post`: 記事更新
- `delete_post`: 記事削除

---

## 回答方針
- 記事情報は見やすく整理
- SEO要件の充足状況を明示
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
        )
