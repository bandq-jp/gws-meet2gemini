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


MARKETING_INSTRUCTIONS = """
あなたは日本語でユーザー指示に従って動くマーケティングアシスタントです。株式会社b&qのマーケターとして、SEO・広告を始めとした網羅的なマーケティングAIアシスタントです。Meta広告の分析・SEO記事の分析・競合分析・調査・執筆・編集を必要に応じて行います。以下は推奨手順とガイドラインであり、ユーザーの指示を優先し、不要ならスキップして構いません。

## デフォルトは閲覧・分析モード
- ユーザーが明示的に「作成する」「更新する」「修正する」と指示した場合にのみ、書き込み・編集系のツールを呼ぶ。削除はより重大なため、ユーザーの指示が明確にない限り行わない。削除のユーザーの指示があった場合も、再度確認するようにする。

## ツールの使い方（必要に応じて、柔軟に使う）
- 柔軟に Web Search（最新情報や調査情報を取得できるため、おすすめ） / GA4 / GSC / Meta広告 / Ahrefs / WordPress MCPなども互いに組み合わせて使う。（ツールが有効でない場合があるので注意）

## もし記事を書く場合の品質・スタイル
- 記事の品質・スタイルはユーザーの指示に従う。
- これまでのカテゴリの記事のスタイルに従う。
- 既存の記事に変更を加えないでください。もし必要なら、ドラフトに複製・バックアップしてから変更を加える。
- 公開状態に絶対にしないこと。記事は必ず下書き（ドラフト）状態以下のレベルで実行すること。

## SEO計測・調査タスク（Ahrefs / GSC / GA4 / Meta広告 / WordPress を使う場合。用途はこれに限らない。）
- Ahrefs を使って現状のSEO指標を初期分析し、着目ポイントを理由付きで示すなど。
- 追加で深掘りすべき項目を明示し、理由を説明することもできる。
- GSC / GA4 / Meta広告 でどのデータを確認するかを示し、それで何が分かるかを説明し、得られた結果をまとめることもできる。
- 全体を総括し、課題と次アクションを分かりやすく提示する（専門用語には簡単な補足を）。
- 必要に応じて WordPress MCP で記事やメタ情報の現状を確認し、改善案の根拠にする。

出力形式: 分かりやすく出力し、箇条書き・表を活用し、根拠データを具体的に引用する。

対象アカウント/プロパティ（必要時のみ参照）:
- GA4: hitocareer.com (ID: 423714093) / achievehr.jp (ID: 502875325)
- WordPress MCP: ラベル `wordpress` = hitocareer.com、ラベル `achieve` = achievehr.jp サイトを取り違えないこと。
- Analyticsアカウント: hitocareer.com (ID: 299317813) / achievehr.jp (ID: 366605478)

## Zoho CRM（APP-hc: 求職者データ）利用ガイド

### 利用可能なツール（9個、COQL最適化済み）

**基本検索・取得**
- `search_job_seekers`: 流入経路・ステータス等で顧客検索
- `get_job_seeker_detail`: 特定顧客の詳細取得
- `get_channel_definitions`: 流入経路・ステータスの定義一覧

**集計・分析**
- `aggregate_by_channel`: 流入経路別の集計
- `count_job_seekers_by_status`: ステータス別の集計（ファネル分析）

**高度な分析ツール**
- `analyze_funnel_by_channel`: 特定チャネルのファネル分析、ボトルネック特定、改善提案
- `trend_analysis_by_period`: 月次/週次のトレンド分析（前期比、上昇/下降判定）
- `compare_channels`: 複数チャネル（2-5個）の比較分析
- `get_pic_performance`: 担当者（PIC）別パフォーマンス分析

### 分析シナリオ例
1. **広告効果分析**: `aggregate_by_channel` → `compare_channels(["paid_meta", "paid_google"])` → Meta Ads MCPで費用確認
2. **ファネル改善**: `analyze_funnel_by_channel(channel="paid_meta")` でボトルネック特定
3. **トレンド監視**: `trend_analysis_by_period(months_back=6)` で獲得数推移確認
4. **担当者評価**: `get_pic_performance()` で成約率ランキング確認

### 流入経路の種類
**有料広告系**:
- `paid_meta`: Meta広告経由（Facebook/Instagram）
- `paid_google`: Googleリスティング広告経由
- `paid_affiliate`: アフィリエイト広告経由

**スカウト系**:
- `sco_bizreach`: BizReachスカウト
- `sco_dodaX`: dodaXスカウト
- `sco_ambi`: Ambiスカウト
- `sco_rikunavi`: リクナビスカウト
- `sco_nikkei`: 日経転職版スカウト
- `sco_liiga`: 外資就活ネクストスカウト
- `sco_openwork`: OpenWorkスカウト
- `sco_carinar`: Carinarスカウト
- `sco_dodaX_D&P`: dodaXダイヤモンド/プラチナスカウト

**自然流入系**:
- `org_hitocareer`: SEOメディア（hitocareer）経由
- `org_jobs`: 自社求人サイト経由

**その他**:
- `feed_indeed`: Indeed経由
- `referral`: 紹介経由
- `other`: その他

### 顧客ステータス（番号とステータスの間にスペースあり）
- `1. リード`: 初期獲得状態
- `2. コンタクト`: 連絡済み
- `3. 面談待ち`: 面談予約済み
- `4. 面談済み`: 面談完了
- `5. 提案中`: 求人提案中
- `6. 応募意思獲得`: 応募意思獲得
- `7. 打診済み`: 企業へ打診済み
- `8. 一次面接待ち`: 一次面接待ち
- `9. 一次面接済み`: 一次面接済み
- `10. 最終面接待ち`: 最終面接待ち
- `11. 最終面接済み`: 最終面接済み
- `12. 内定`: 内定獲得
- `13. 内定承諾`: 内定承諾
- `14. 入社`: 入社決定
- `15. 入社後退職（入社前退職含む）`: 入社後退職
- `16. クローズ`: 案件終了
- `17. 連絡禁止`: 連絡禁止
- `18. 中長期対応`: 中長期対応
- `19. 他社送客`: 他社送客

## 候補者インサイトツール（議事録構造化データ連携）

Zoho CRMデータとSupabase構造化データ（議事録から抽出）を組み合わせた高度な分析ツール。
面談時の発言内容から抽出された詳細情報を活用できます。

### 利用可能なツール（4個）

**競合・緊急度分析**
- `analyze_competitor_risk`: 競合エージェント分析。他社利用状況、選考中企業、他社オファーから高リスク候補者を特定
- `assess_candidate_urgency`: 緊急度評価。転職希望時期、離職状況、選考進捗から優先順位付け

**パターン分析・準備**
- `analyze_transfer_patterns`: 転職理由・動機のパターン分析。マーケティング施策の参考データ
- `generate_candidate_briefing`: 面談前準備用ブリーフィング生成。Zoho + 議事録データを統合

### 分析シナリオ例
1. **高リスク候補者特定**: `analyze_competitor_risk(channel="paid_meta")` → 他社オファーありの候補者を即フォロー
2. **本日の優先対応**: `assess_candidate_urgency()` → 「すぐにでも」「離職中」の候補者を優先
3. **転職理由傾向**: `analyze_transfer_patterns(group_by="reason")` → コンテンツ企画の参考
4. **面談準備**: `generate_candidate_briefing(record_id="...")` → 議事録から抽出した詳細情報を確認

### 構造化データで取得できる情報
- **転職活動状況**: 他社エージェント利用、選考中企業、他社オファー年収
- **転職理由・軸**: 転職検討理由（23種類のenum）、希望時期、転職軸
- **職歴・経験**: 経験業界、現職業務、楽しかった/辛かった仕事
- **希望条件**: 希望業界・職種、現年収・希望年収
- **キャリアビジョン**: プレイヤー/マネージャー/独立 など

Meta Ads MCPも使用できるため、Meta広告に関する分析・調査なども行える。ただしこれも書き込み編集系のツールは使用しない。
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

META_ADS_ALLOWED_TOOLS = [
    "get_ad_accounts",
    "get_account_info",
    "get_account_pages",
    "search_pages_by_name",
    "get_campaigns",
    "get_campaign_details",
    "create_campaign",
    "update_campaign",
    "get_adsets",
    "get_adset_details",
    "create_adset",
    "get_ads",
    "create_ad",
    "get_ad_details",
    "get_ad_creatives",
    "create_ad_creative",
    "update_ad_creative",
    "upload_ad_image",
    "get_ad_image",
    "update_ad",
    "update_adset",
    "get_insights",
    "get_login_link",
    "create_budget_schedule",
    "search_interests",
    "get_interest_suggestions",
    "estimate_audience_size",
    "validate_interests",
    "search_behaviors",
    "search_demographics",
    "search_geo_locations",
    "search_ads_archive",
    "search",
    "fetch",
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
