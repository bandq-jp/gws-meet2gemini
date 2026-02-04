"""
WordPress Agent - Content management integration.

Handles WordPress content creation and editing for both hitocareer.com and achievehr.jp.
Tools: 52 MCP tools (26 × 2 sites) + native tools
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from agents import Agent, HostedMCPTool, ModelSettings
from openai.types.shared.reasoning import Reasoning

from .base import SubAgentFactory
from ..seo_agent_factory import WORDPRESS_HITOCAREER_ALLOWED_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings


class WordPressAgentFactory(SubAgentFactory):
    """
    Factory for WordPress sub-agent.

    Specializes in:
    - Article creation and editing
    - Block structure management
    - Media management
    - Category and tag management
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
            "hitocareer.comとachievehr.jpの記事作成・編集・分析。"
            "ブロック構造管理、メディアアップロード、カテゴリ/タグ管理を担当。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return WordPress MCP tools for both sites."""
        tools: List[Any] = []

        # hitocareer.com WordPress MCP
        if (
            self._settings.wordpress_mcp_server_url
            and self._settings.wordpress_mcp_authorization
        ):
            tools.append(
                HostedMCPTool(
                    tool_config={
                        "type": "mcp",
                        "server_label": "wordpress",
                        "server_url": self._settings.wordpress_mcp_server_url,
                        "allowed_tools": WORDPRESS_HITOCAREER_ALLOWED_TOOLS,
                        "require_approval": "never",
                        "headers": {
                            "Authorization": self._settings.wordpress_mcp_authorization
                        },
                    }
                )
            )

        # achievehr.jp WordPress MCP
        if (
            self._settings.wordpress_achieve_mcp_server_url
            and self._settings.wordpress_achieve_mcp_authorization
        ):
            tools.append(
                HostedMCPTool(
                    tool_config={
                        "type": "mcp",
                        "server_label": "achieve",
                        "server_url": self._settings.wordpress_achieve_mcp_server_url,
                        "allowed_tools": WORDPRESS_HITOCAREER_ALLOWED_TOOLS,
                        "require_approval": "never",
                        "headers": {
                            "Authorization": self._settings.wordpress_achieve_mcp_authorization
                        },
                    }
                )
            )

        return tools

    def _build_instructions(self) -> str:
        return """
あなたはWordPressコンテンツ管理の専門家です。

## 担当サイト
- **wordpress** (server_label): hitocareer.com
- **achieve** (server_label): achievehr.jp

## 基本方針
- デフォルトは**閲覧・分析モード**
- 書き込みはユーザーの**明示的な指示時のみ**
- 削除は**再確認必須**
- 記事は常に**ドラフト状態**で保存、公開は明示的な指示がある場合のみ

## 利用可能なツール (26個 × 2サイト)

### 記事取得・分析 (8個)
- wp-mcp-get-posts-by-category: カテゴリ別記事一覧
- wp-mcp-get-post-block-structure: ブロック構造取得
- wp-mcp-analyze-category-format-patterns: カテゴリフォーマットパターン分析
- wp-mcp-get-post-raw-content: 生コンテンツ取得
- wp-mcp-extract-used-blocks: 使用ブロック抽出
- wp-mcp-get-theme-styles: テーマスタイル取得
- wp-mcp-get-block-patterns: ブロックパターン取得
- wp-mcp-get-reusable-blocks: 再利用可能ブロック取得

### 規約・SEO検証 (4個)
- wp-mcp-get-article-regulations: 記事規約取得
- wp-mcp-validate-block-content: ブロックコンテンツ検証
- wp-mcp-check-regulation-compliance: 規約準拠チェック
- wp-mcp-check-seo-requirements: SEO要件チェック

### 記事作成・編集 (6個)
- wp-mcp-create-draft-post: ドラフト作成
- wp-mcp-update-post-content: コンテンツ更新
- wp-mcp-update-post-meta: メタ情報更新
- wp-mcp-publish-post: 記事公開（明示的指示時のみ）
- wp-mcp-delete-post: 記事削除（再確認必須）

### メディア管理 (3個)
- wp-mcp-get-media-library: メディアライブラリ取得
- wp-mcp-upload-media: メディアアップロード
- wp-mcp-set-featured-image: アイキャッチ画像設定

### 分類管理 (5個)
- wp-mcp-get-categories: カテゴリ一覧
- wp-mcp-get-tags: タグ一覧
- wp-mcp-create-term: 分類作成
- wp-mcp-get-site-info: サイト情報
- wp-mcp-get-post-types: 投稿タイプ一覧

## 回答方針
- 記事構成をブロック単位で説明
- SEO改善点を具体的に指摘
- 類似記事の参照パターンを提示
- 最新コンテンツマーケティングトレンドはWeb Searchで補足
"""
