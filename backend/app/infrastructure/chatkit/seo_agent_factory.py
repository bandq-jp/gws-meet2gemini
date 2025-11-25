from __future__ import annotations

from typing import Any, List

from agents import (
    Agent,
    CodeInterpreterTool,
    HostedMCPTool,
    ModelSettings,
    WebSearchTool,
)
from agents.agent import StopAtTools
from openai.types.shared.reasoning import Reasoning

from app.infrastructure.config.settings import Settings
from app.infrastructure.chatkit.seo_article_tools import (
    apply_patch_to_article,
    create_seo_article,
    get_seo_article,
    save_seo_article,
    seo_open_canvas,
    seo_update_canvas,
)

MARKETING_WORKFLOW_ID = (
    "wf_690a1d2e1ce881908e92b6826428f3af060621f24cf1b2bb"
)


MARKETING_INSTRUCTIONS = """
あなたは日本語でSEO記事を分析・執筆・編集するマーケティングエージェントです。記事執筆モードになったら左ペインはチャット、右ペインは記事キャンバス（Canvas）として使います。以下の原則を守ってください。

## 役割
- BtoB/BtoC いずれも対応するSEOライター兼エディター。
- ユーザーの指示が「記事を書く」「ここを編集」などマーケ用途のときだけキャンバスを開く。

## ツールの使い方
- 新規作成: `create_seo_article` → 直後に `seo_open_canvas` で右ペインを開く。
- 途中経過/完了時: `save_seo_article` または `seo_update_canvas` でアウトライン/本文を同期する。
- 現状取得: `get_seo_article`。
- 差分編集: `apply_patch_to_article` を優先して使い、編集後は `seo_update_canvas` で最新本文を送る。
- SERP/計測が必要なときだけ Web Search / GA4 / GSC / Ahrefs MCP を呼ぶ。

## 執筆フロー（推奨）
1) ユーザーの検索意図・主要キーワード・ターゲットを短く確認。
2) `create_seo_article` で記事IDを確保しキャンバスを開く。
3) 競合・補足調査が必要なら Web Search/MCP を最小限で実行。
4) H2/H3 のアウトラインを提示し、`seo_update_canvas` で右ペインへ送る。
5) セクションごとに本文を生成し、都度 `seo_update_canvas` → 要約を左ペインに報告。
6) 完了後 `save_seo_article` で確定し、次の編集希望を尋ねる。

## 編集フロー（差分重視）
- ユーザーの編集指示を短く要約 → `get_seo_article` で最新本文 → `apply_patch_to_article` を呼んで最小差分で修正。
- 変更理由・影響箇所を左ペインで1段落+箇条書きで説明し、キャンバスも更新する。

## 品質・スタイル
- SEO基本: 検索意図に沿った導入、見出し階層の一貫性、具体例とCTA、冗長回避。
- 数値や根拠は出典（ツール名/指標）を添える。曖昧な推測はラベルを付ける。
- 読みやすさを優先し、日本語で簡潔に。
- **チャット欄には本文全文を貼らない。** 本文やアウトラインは `seo_update_canvas` / `save_seo_article` でキャンバスへ送り、チャット側は進捗と変更概要だけを短く報告する。
"""


GA4_ALLOWED_TOOLS = [
    "get_account_summaries",
    "list_google_ads_links",
    "get_property_details",
    "get_custom_dimensions_and_metrics",
    "run_realtime_report",
    "run_report",
]

AHREFS_ALLOWED_TOOLS = [
    "management-projects-create",
    "site-explorer-domain-rating-history",
    "rank-tracker-overview",
    "serp-overview-serp-overview",
    "site-explorer-total-search-volume-history",
    "site-explorer-linked-anchors-external",
    "site-explorer-organic-competitors",
    "keywords-explorer-related-terms",
    "site-explorer-linked-anchors-internal",
    "site-explorer-best-by-internal-links",
    "site-explorer-refdomains-history",
    "site-explorer-organic-keywords",
    "doc",
    "keywords-explorer-volume-history",
    "keywords-explorer-matching-terms",
    "management-project-keywords",
    "subscription-info-limits-and-usage",
    "rank-tracker-competitors-pages",
    "management-locations",
    "site-explorer-outlinks-stats",
    "management-project-competitors-post",
    "site-audit-page-content",
    "keywords-explorer-search-suggestions",
    "site-audit-issues",
    "site-explorer-top-pages",
    "rank-tracker-competitors-stats",
    "site-explorer-broken-backlinks",
    "site-explorer-backlinks-stats",
    "batch-analysis-batch-analysis",
    "site-explorer-refdomains",
    "site-explorer-keywords-history",
    "site-explorer-anchors",
    "site-explorer-best-by-external-links",
    "rank-tracker-competitors-overview",
    "site-explorer-metrics-history",
    "brand-radar-ai-responses",
    "keywords-explorer-overview",
    "site-audit-page-explorer",
    "site-explorer-domain-rating",
    "keywords-explorer-volume-by-country",
    "management-projects",
    "site-explorer-url-rating-history",
    "site-explorer-pages-history",
    "site-explorer-linkeddomains",
    "management-project-competitors",
    "management-keyword-list-keywords",
    "rank-tracker-serp-overview",
    "site-explorer-pages-by-traffic",
    "management-keyword-list-keywords-put",
    "management-project-keywords-put",
    "site-explorer-paid-pages",
    "site-explorer-metrics",
    "site-audit-projects",
    "site-explorer-metrics-by-country",
    "site-explorer-all-backlinks",
]

GSC_ALLOWED_TOOLS = [
    "list_properties",
    "add_site",
    "delete_site",
    "get_search_analytics",
    "get_site_details",
    "get_sitemaps",
    "inspect_url_enhanced",
    "batch_url_inspection",
    "check_indexing_issues",
    "get_performance_overview",
    "get_advanced_search_analytics",
    "compare_search_periods",
    "get_search_by_page_query",
    "list_sitemaps_enhanced",
    "get_sitemap_details",
    "submit_sitemap",
    "delete_sitemap",
    "manage_sitemaps",
    "get_creator_info",
]


class MarketingAgentFactory:
    def __init__(self, settings: Settings):
        self._settings = settings

    def build_agent(self) -> Agent:
        tools: List[Any] = []
        if self._settings.marketing_enable_web_search:
            tools.append(
                WebSearchTool(
                    search_context_size="medium",
                    user_location={
                        "country": self._settings.marketing_search_country,
                        "type": "approximate",
                    },
                )
            )
        if self._settings.marketing_enable_code_interpreter:
            tools.append(
                CodeInterpreterTool(
                    tool_config={
                        "type": "code_interpreter",
                        "container": {
                            "type": "auto",
                            "file_ids": [],
                        },
                    }
                )
            )

        tools.extend(self._hosted_tools())

        tools.extend(
            [
                create_seo_article,
                get_seo_article,
                save_seo_article,
                seo_open_canvas,
                seo_update_canvas,
                apply_patch_to_article,
            ]
        )

        agent = Agent(
            name="SEOAgent",
            instructions=MARKETING_INSTRUCTIONS.strip(),
            tools=tools,
            model=self._settings.marketing_agent_model,
            model_settings=ModelSettings(
                store=True,
                reasoning=Reasoning(
                    effort=self._settings.marketing_reasoning_effort,
                    summary="detailed",
                ),
            ),
            tool_use_behavior=StopAtTools(
                stop_at_tool_names=[
                    "seo_open_canvas",
                    "seo_update_canvas",
                    "create_seo_article",
                    "get_seo_article",
                    "save_seo_article",
                    "apply_patch_to_article",
                ]
            ),
        )
        return agent

    def _hosted_tools(self) -> list[HostedMCPTool]:
        hosted: list[HostedMCPTool] = []
        if (
            self._settings.ga4_mcp_server_url
            and self._settings.ga4_mcp_authorization
        ):
            hosted.append(
                HostedMCPTool(
                    tool_config={
                        "type": "mcp",
                        "server_label": "ga4",
                        "server_url": self._settings.ga4_mcp_server_url,
                        "allowed_tools": GA4_ALLOWED_TOOLS,
                        "require_approval": "never",
                        "headers": {
                            "Authorization": self._settings.ga4_mcp_authorization
                        },
                    }
                )
            )
        if (
            self._settings.ahrefs_mcp_server_url
            and self._settings.ahrefs_mcp_authorization
        ):
            hosted.append(
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
        if (
            self._settings.gsc_mcp_server_url
            and self._settings.gsc_mcp_api_key
        ):
            hosted.append(
                HostedMCPTool(
                    tool_config={
                        "type": "mcp",
                        "server_label": "gsc",
                        "server_url": self._settings.gsc_mcp_server_url,
                        "allowed_tools": GSC_ALLOWED_TOOLS,
                        "require_approval": "never",
                        "headers": {
                            "x-api-key": self._settings.gsc_mcp_api_key,
                        },
                    }
                )
            )
        return hosted
