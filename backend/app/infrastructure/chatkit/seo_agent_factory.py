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
# [DISABLED] キャンバスツールはWordPress MCPに移行したため一時無効化
# from app.infrastructure.chatkit.seo_article_tools import (
#     apply_patch_to_article,
#     create_seo_article,
#     get_seo_article,
#     save_seo_article,
#     save_seo_article_body,
#     seo_open_canvas,
#     seo_update_canvas,
# )
from app.infrastructure.chatkit.zoho_crm_tools import ZOHO_CRM_TOOLS
from app.infrastructure.chatkit.candidate_insight_tools import CANDIDATE_INSIGHT_TOOLS

MARKETING_WORKFLOW_ID = (
    "wf_690a1d2e1ce881908e92b6826428f3af060621f24cf1b2bb"
)


# Optimized instructions - reduced from ~5000 to ~1500 chars
# Channel/status definitions moved to get_channel_definitions tool
MARKETING_INSTRUCTIONS = """
b&qマーケティングAIアシスタント。SEO・広告分析、競合調査、記事編集を支援。

## 基本方針
- デフォルトは閲覧・分析モード。書き込みはユーザーの明示的な指示時のみ
- 削除は再確認必須。記事は常にドラフト状態で保存、公開禁止
- Web Search / GA4 / GSC / Meta Ads / Ahrefs / WordPress / Zohoを柔軟に組み合わせる

## 対象プロパティ
- GA4: hitocareer.com (423714093) / achievehr.jp (502875325)
- WordPress: `wordpress`=hitocareer.com / `achieve`=achievehr.jp

## Zoho CRM (求職者分析)
流入経路・ステータスの定義は `get_channel_definitions` ツールで取得可能。

**基本ツール**: search_job_seekers, get_job_seeker_detail, aggregate_by_channel, count_job_seekers_by_status
**分析ツール**: analyze_funnel_by_channel, trend_analysis_by_period, compare_channels, get_pic_performance

## 候補者インサイト (議事録構造化データ連携)
**ツール**: analyze_competitor_risk (競合分析), assess_candidate_urgency (緊急度評価), analyze_transfer_patterns (転職パターン), generate_candidate_briefing (面談準備)

出力: 箇条書き・表を活用、根拠データを引用。
"""


GA4_ALLOWED_TOOLS = [
    "get_account_summaries",
    "list_google_ads_links",
    "get_property_details",
    "get_custom_dimensions_and_metrics",
    "run_realtime_report",
    "run_report",
]

# Ahrefs tools - essential read-only tools (20 tools, removed write ops and less-used)
AHREFS_ALLOWED_TOOLS = [
    # Site Explorer - core metrics
    "site-explorer-domain-rating",
    "site-explorer-metrics",
    "site-explorer-organic-keywords",
    "site-explorer-top-pages",
    "site-explorer-pages-by-traffic",
    "site-explorer-organic-competitors",
    "site-explorer-backlinks-stats",
    "site-explorer-refdomains",
    "site-explorer-all-backlinks",
    "site-explorer-anchors",
    # Keywords Explorer
    "keywords-explorer-overview",
    "keywords-explorer-related-terms",
    "keywords-explorer-matching-terms",
    "keywords-explorer-volume-history",
    "keywords-explorer-search-suggestions",
    # Site Audit
    "site-audit-issues",
    "site-audit-page-explorer",
    # Rank Tracker
    "rank-tracker-overview",
    # Batch & Usage
    "batch-analysis-batch-analysis",
    "subscription-info-limits-and-usage",
]

# GSC tools - only implemented tools (10 tools)
GSC_ALLOWED_TOOLS = [
    "list_properties",
    "get_search_analytics",
    "get_site_details",
    "get_sitemaps",
    "inspect_url_enhanced",
    "batch_url_inspection",
    "get_performance_overview",
    "get_advanced_search_analytics",
    "compare_search_periods",
    "get_search_by_page_query",
]

# Meta Ads tools - read-only analysis (20 tools, removed write ops)
META_ADS_ALLOWED_TOOLS = [
    # Account & Pages
    "get_ad_accounts",
    "get_account_info",
    "get_account_pages",
    "search_pages_by_name",
    # Campaigns & Ads (read-only)
    "get_campaigns",
    "get_campaign_details",
    "get_adsets",
    "get_adset_details",
    "get_ads",
    "get_ad_details",
    "get_ad_creatives",
    "get_ad_image",
    "get_insights",
    # Targeting Research
    "search_interests",
    "get_interest_suggestions",
    "estimate_audience_size",
    "validate_interests",
    "search_behaviors",
    "search_demographics",
    "search_geo_locations",
]

WORDPRESS_ALLOWED_TOOLS = [
    "mcp-adapter-discover-abilities",
    "mcp-adapter-get-ability-info",
    "mcp-adapter-execute-ability",
]

# hitocareer.com 専用の新WordPress MCPツール
WORDPRESS_HITOCAREER_ALLOWED_TOOLS = [
    "wp-mcp-get-posts-by-category",
    "wp-mcp-get-post-block-structure",
    "wp-mcp-analyze-category-format-patterns",
    "wp-mcp-get-post-raw-content",
    "wp-mcp-extract-used-blocks",
    "wp-mcp-get-theme-styles",
    "wp-mcp-get-block-patterns",
    "wp-mcp-get-reusable-blocks",
    "wp-mcp-get-article-regulations",
    "wp-mcp-create-draft-post",
    "wp-mcp-update-post-content",
    "wp-mcp-update-post-meta",
    "wp-mcp-publish-post",
    "wp-mcp-delete-post",
    "wp-mcp-validate-block-content",
    "wp-mcp-check-regulation-compliance",
    "wp-mcp-check-seo-requirements",
    "wp-mcp-get-media-library",
    "wp-mcp-upload-media",
    "wp-mcp-set-featured-image",
    "wp-mcp-get-categories",
    "wp-mcp-get-tags",
    "wp-mcp-create-term",
    "wp-mcp-get-site-info",
    "wp-mcp-get-post-types",
]


class MarketingAgentFactory:
    def __init__(self, settings: Settings):
        self._settings = settings

    def build_agent(
        self,
        asset: dict[str, Any] | None = None,
        disabled_mcp_servers: set[str] | None = None,
        mcp_servers: list[Any] | None = None,
    ) -> Agent:
        tools: List[Any] = []

        enable_web_search = self._settings.marketing_enable_web_search and (
            asset is None or asset.get("enable_web_search", True)
        )
        enable_code_interpreter = self._settings.marketing_enable_code_interpreter and (
            asset is None or asset.get("enable_code_interpreter", True)
        )
        # [DISABLED] キャンバスツールはWordPress MCPに移行したため一時無効化
        # enable_canvas = self._settings.marketing_enable_canvas and (
        #     asset is None or asset.get("enable_canvas", True)
        # )

        if enable_web_search:
            tools.append(
                WebSearchTool(
                    search_context_size="medium",
                    user_location={
                        "country": self._settings.marketing_search_country,
                        "type": "approximate",
                    },
                )
            )
        if enable_code_interpreter:
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

        tools.extend(self._hosted_tools(asset, disabled_mcp_servers))

        # [DISABLED] キャンバスツールはWordPress MCPに移行したため一時無効化
        # canvas_tools = [
        #     create_seo_article,
        #     get_seo_article,
        #     save_seo_article,
        #     save_seo_article_body,
        #     seo_open_canvas,
        #     seo_update_canvas,
        #     apply_patch_to_article,
        # ]
        # if enable_canvas:
        #     tools.extend(canvas_tools)

        # Zoho CRM ツールを追加（顧客検索・集計用）
        enable_zoho_crm = asset is None or asset.get("enable_zoho_crm", True)
        if enable_zoho_crm and self._settings.zoho_refresh_token:
            tools.extend(ZOHO_CRM_TOOLS)
            # 候補者インサイトツールも追加（Zoho + Supabase構造化データ連携）
            tools.extend(CANDIDATE_INSIGHT_TOOLS)

        reasoning_effort = (
            asset.get("reasoning_effort") if asset else self._settings.marketing_reasoning_effort
        )
        raw_verbosity = asset.get("verbosity") if asset else None
        verbosity = self._normalize_verbosity(raw_verbosity)

        base_instructions = MARKETING_INSTRUCTIONS.strip()
        addition = (asset or {}).get("system_prompt_addition")
        parts: list[str] = []
        if addition:
            parts.append(addition.strip())
        # [DISABLED] キャンバスツールはWordPress MCPに移行したため一時無効化
        # if not enable_canvas:
        #     parts.append(
        #         "このプリセットでは記事キャンバス（Canvas）/SEO記事編集ツールが無効です。"
        #         "seo_open_canvas, seo_update_canvas, create_seo_article, save_seo_article, "
        #         "save_seo_article_body, get_seo_article, apply_patch_to_article などのキャンバス系ツールは呼び出さず、"
        #         "アウトラインや本文が必要な場合はチャット欄で直接提示してください。"
        #         "記事の永続化や右ペイン更新は行いません。"
        #     )
        parts.append(base_instructions)
        final_instructions = "\n\n".join(parts)

        # [DISABLED] キャンバスツールはWordPress MCPに移行したため一時無効化
        # stop_at_tool_names = [
        #     "seo_open_canvas",
        #     "seo_update_canvas",
        #     "create_seo_article",
        #     "save_seo_article",
        # ] if enable_canvas else []

        agent = Agent(
            name="SEOAgent",
            instructions=final_instructions,
            tools=tools,
            model=self._settings.marketing_agent_model,
            model_settings=ModelSettings(
                store=True,
                reasoning=Reasoning(
                    effort=reasoning_effort,
                    summary="detailed",
                ),
                verbosity=verbosity or "medium",
                response_include=["code_interpreter_call.outputs"],
            ),
            # [DISABLED] キャンバスツール無効化に伴い常にrun_llm_again
            # tool_use_behavior=StopAtTools(stop_at_tool_names=stop_at_tool_names)
            # if stop_at_tool_names
            # else "run_llm_again",
            tool_use_behavior="run_llm_again",
            # Local MCP servers (GA4/GSC when USE_LOCAL_MCP=true)
            mcp_servers=mcp_servers or [],
        )
        return agent

    @staticmethod
    def _normalize_verbosity(value: Any | None) -> str:
        """Map deprecated verbosity labels to valid ones."""
        if value is None:
            return "medium"
        if value == "short":
            return "low"
        if value == "long":
            return "high"
        if value in ("low", "medium", "high"):
            return value
        return "medium"

    def _hosted_tools(
        self,
        asset: dict[str, Any] | None,
        disabled_mcp_servers: set[str] | None = None,
    ) -> list[HostedMCPTool]:
        hosted: list[HostedMCPTool] = []
        disabled = {item.lower() for item in (disabled_mcp_servers or set())}

        def is_disabled(label: str) -> bool:
            return label.lower() in disabled

        allow_ga4 = asset is None or asset.get("enable_ga4", True)
        allow_meta_ads = asset is None or asset.get("enable_meta_ads", True)
        allow_ahrefs = asset is None or asset.get("enable_ahrefs", True)
        allow_gsc = asset is None or asset.get("enable_gsc", True)
        allow_wordpress = asset is None or asset.get("enable_wordpress", True)

        # Skip GA4 HostedMCPTool when local MCP is enabled
        use_local_ga4 = self._settings.use_local_mcp and self._settings.local_mcp_ga4_enabled
        if (
            self._settings.ga4_mcp_server_url
            and self._settings.ga4_mcp_authorization
            and allow_ga4
            and not is_disabled("ga4")
            and not use_local_ga4  # Skip if using local MCP
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
        # Skip Meta Ads HostedMCPTool when local MCP is enabled AND token is configured
        # If META_ACCESS_TOKEN is not set, local MCP will return None, so we need hosted fallback
        use_local_meta_ads = (
            self._settings.use_local_mcp
            and self._settings.local_mcp_meta_ads_enabled
            and self._settings.meta_access_token  # Only skip hosted if local can actually work
        )
        if (
            self._settings.meta_ads_mcp_server_url
            and self._settings.meta_ads_mcp_authorization
            and allow_meta_ads
            and not is_disabled("meta_ads")
            and not use_local_meta_ads  # Skip if using local MCP
        ):
            hosted.append(
                HostedMCPTool(
                    tool_config={
                        "type": "mcp",
                        "server_label": "meta_ads",
                        "server_url": self._settings.meta_ads_mcp_server_url,
                        "allowed_tools": META_ADS_ALLOWED_TOOLS,
                        "require_approval": "never",
                        "headers": {
                            "Authorization": self._settings.meta_ads_mcp_authorization
                        },
                    }
                )
            )
        if (
            self._settings.ahrefs_mcp_server_url
            and self._settings.ahrefs_mcp_authorization
            and allow_ahrefs
            and not is_disabled("ahrefs")
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
        # Skip GSC HostedMCPTool when local MCP is enabled
        use_local_gsc = self._settings.use_local_mcp and self._settings.local_mcp_gsc_enabled
        if (
            self._settings.gsc_mcp_server_url
            and self._settings.gsc_mcp_api_key
            and allow_gsc
            and not is_disabled("gsc")
            and not use_local_gsc  # Skip if using local MCP
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
        if (
            self._settings.wordpress_mcp_server_url
            and self._settings.wordpress_mcp_authorization
            and allow_wordpress
            and not is_disabled("wordpress")
        ):
            hosted.append(
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
        if (
            self._settings.wordpress_achieve_mcp_server_url
            and self._settings.wordpress_achieve_mcp_authorization
            and allow_wordpress
            and not is_disabled("achieve")
        ):
            hosted.append(
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
        return hosted
