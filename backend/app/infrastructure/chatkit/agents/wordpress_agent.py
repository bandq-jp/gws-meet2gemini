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

    @property
    def reasoning_effort(self) -> str:
        """WordPress agent uses high reasoning for complex content creation."""
        return "high"

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

## 重要ルール（絶対厳守）
1. **閲覧系は即実行**: 記事一覧、カテゴリ、分析などの閲覧系ツールは許可なく即座に実行
2. **書き込み系は明示的指示時のみ**: 作成・更新・削除はユーザーの明示的な指示がある場合のみ
3. **推測するな**: データが必要なら必ずツールを呼び出す。自分でデータを作らない

## 典型的なリクエストと即時実行

| リクエスト | 即座に実行 |
|-----------|-----------|
| 「記事一覧」「カテゴリの記事」 | wp-mcp-get-posts-by-category |
| 「記事構造」「ブロック構造」 | wp-mcp-get-post-block-structure |
| 「カテゴリ一覧」 | wp-mcp-get-categories |
| 「SEOチェック」 | wp-mcp-check-seo-requirements |
| 「フォーマット分析」 | wp-mcp-analyze-category-format-patterns |

---

## 担当サイト
- **wordpress** (server_label): hitocareer.com
- **achieve** (server_label): achievehr.jp

---

## 主要ツール詳細仕様

### 記事取得・分析

**wp-mcp-get-posts-by-category**
カテゴリ別記事一覧を取得。
- **category_id** (必須): カテゴリID
- **per_page** (任意): 取得件数 (デフォルト10)
- **status** (任意): publish, draft, private
- 出力: id, title, date, link, excerpt

**wp-mcp-get-post-block-structure**
記事のGutenbergブロック構造を取得。
- **post_id** (必須): 記事ID
- 出力: blocks (blockName, attrs, innerBlocks)

**wp-mcp-analyze-category-format-patterns**
カテゴリ内の記事フォーマットパターンを分析。
- **category_id** (必須): カテゴリID
- **sample_size** (任意): 分析サンプル数 (デフォルト5)
- 出力: common_blocks, heading_patterns, avg_word_count

**wp-mcp-get-post-raw-content**
記事の生HTMLコンテンツ取得。
- **post_id** (必須): 記事ID
- 出力: content (raw HTML), title, excerpt

### 規約・SEO検証

**wp-mcp-check-seo-requirements**
SEO要件をチェック。
- **post_id** (必須): 記事ID
- 出力: meta_title, meta_description, h1_count, image_alt, internal_links, issues

**wp-mcp-check-regulation-compliance**
記事規約への準拠チェック。
- **post_id** (必須): 記事ID
- 出力: violations, warnings, passed

### 記事作成・編集（明示的指示時のみ）

**wp-mcp-create-draft-post**
ドラフト記事を作成。
- **title** (必須): 記事タイトル
- **content** (必須): 記事内容（Gutenbergブロック形式）
- **categories** (任意): カテゴリIDの配列
- **tags** (任意): タグIDの配列
- 出力: id, link (プレビューURL)

**wp-mcp-update-post-content**
記事内容を更新。
- **post_id** (必須): 記事ID
- **content** (必須): 新しいコンテンツ
- 出力: id, modified

**wp-mcp-update-post-meta**
メタ情報を更新。
- **post_id** (必須): 記事ID
- **meta_fields** (必須): メタフィールド辞書
  - yoast_title, yoast_metadesc, _thumbnail_id 等
- 出力: updated_fields

### 分類管理

**wp-mcp-get-categories**
カテゴリ一覧を取得。
- **per_page** (任意): 取得件数 (デフォルト100)
- **parent** (任意): 親カテゴリID
- 出力: id, name, slug, count, parent

**wp-mcp-get-tags**
タグ一覧を取得。
- **per_page** (任意): 取得件数 (デフォルト100)
- **search** (任意): 検索キーワード
- 出力: id, name, slug, count

---

## 回答方針
- 記事構成をブロック単位で説明
- SEO改善点を具体的に指摘
- 類似記事の参照パターンを提示
"""
