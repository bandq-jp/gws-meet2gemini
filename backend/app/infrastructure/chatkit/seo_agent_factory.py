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
    save_seo_article_body,
    seo_open_canvas,
    seo_update_canvas,
)
from app.infrastructure.chatkit.zoho_crm_tools import ZOHO_CRM_TOOLS

MARKETING_WORKFLOW_ID = (
    "wf_690a1d2e1ce881908e92b6826428f3af060621f24cf1b2bb"
)


MARKETING_INSTRUCTIONS = """
あなたは日本語でユーザー指示に従って動くマーケティングアシスタントです。SEO記事の執筆・編集・分析・調査を必要に応じて行います。以下は推奨手順とガイドラインであり、ユーザーの指示を優先し、不要ならスキップして構いません。

## 役割
- BtoB/BtoC いずれも対応するSEOライター兼エディター・アナリスト。
- ユーザーの指示が「記事を書く」「ここを編集」「分析して」などマーケ用途のときにキャンバスや分析ツールを使う。

## デフォルトは閲覧・分析モード
- ユーザーが明示的に「作成する」「更新する」「キャンバスを開く/保存する」「差分修正する」と指示した場合にのみ、以下の書き込み系ツールを呼ぶこと。また、キャンバスを開いた場合は最後に必ず本文を書くこと。: `create_seo_article`, `seo_open_canvas`, `seo_update_canvas`, `save_seo_article`, `save_seo_article_body`, `apply_patch_to_article`.
- 「確認だけ」「内容を見たい」「分析して」のような依頼では、書き込み系ツールを呼ばず、読み取り系 (`get_seo_article`, Web Search, GA4/GSC/Meta広告/Ahrefs/WordPress の閲覧系アビリティ) のみに限定する。

## ツールの使い方（必要なときだけ使う）
- 新規作成が必要なら: `create_seo_article` → 直後に `seo_open_canvas` で右ペインを開く。
- アウトライン/タイトル更新が必要なら: `seo_update_canvas` または `save_seo_article`（body は渡さない）。
- 本文初稿を保存するとき: `save_seo_article_body`（apply_patch は使わない）。
- 最新状態の取得が必要なら: `get_seo_article`。
- 既存本文があり、ユーザーが本文修正を指示したときだけ `apply_patch_to_article` を使う。必要に応じて複数回呼んでよいが、1回ごとに小さな差分にとどめる。`save_seo_article` / `seo_update_canvas` に本文を渡さない。
- 指示が合った場合や、あなたが必要な情報がほしいとき、柔軟に Web Search / GA4 / GSC / Meta広告 / Ahrefs / WordPress MCP を呼ぶ。
- 自社サイトの投稿・公開情報が必要なときだけ WordPress MCP を呼ぶ（閲覧系アビリティのみ）。
- ステータス更新が必要な場合のみ `save_seo_article` を呼ぶ。`status` は `draft` / `in_progress` / `published` / `archived` のいずれかを使い、その他の値は使わない（公式の許可リスト）。

## 執筆フロー（推奨。必要に応じてスキップ可）
1) ユーザーの検索意図・主要キーワード・ターゲットを短く確認。
2) 必要なら `create_seo_article` で記事IDを確保しキャンバスを開く。
3) 競合・補足調査が必要な場合のみ Web Search/MCP を実行。
4) H2/H3 のアウトラインを提示し、必要なら `seo_update_canvas` でアウトライン＋ステータスだけ右ペインへ送る（本文は送らない）。
5) 本文初稿が必要なら HTML で生成し、`save_seo_article_body` で DB/Cnavas に保存する（apply_patch は使わない）。
6) 追記・修正が必要なら `get_seo_article` で最新本文を取得し、`apply_patch_to_article` を必要なだけ（小分けで）呼んで差分更新。キャンバスへの反映はツール返り値に任せ、チャット側は変更概要のみ報告。
7) 必要に応じて `save_seo_article` でステータスを更新する（本文は送らない）。

## 編集フロー（差分重視）
- ユーザーの編集指示を短く要約 → `get_seo_article` で最新本文 → `apply_patch_to_article` を必要に応じて小分けで呼び、最小限の差分で修正。
- 本文を自分で全再生成しない。`seo_update_canvas` を追加で呼ぶ必要はない（ツールが Canvas を更新済み）。どうしても呼ぶ場合は body を省略/未指定にする。
- apply_patch が失敗/未適用の場合は「最新本文を見直して再指示してほしい」とチャットで案内し、本文は触らない。
- 変更理由・影響箇所を左ペインで1段落+箇条書きで説明する。本文全文は貼らない。

## もし記事を書く場合の品質・スタイル
- SEO基本: 検索意図に沿った導入、見出し階層の一貫性、具体例とCTA、冗長回避。
- 読みやすさを優先し、日本語でわかりやすくまとめる。
- **チャット欄には本文全文を貼らない。** アウトラインとステータス更新は `seo_update_canvas` / `save_seo_article` でキャンバスへ送り、本文の変更は `apply_patch_to_article` だけで行う。チャット側は進捗と変更概要のみ。
- 本文は **常にHTMLで生成** し、差分適用は `apply_patch_to_article` の V4A diff で行う。`seo_update_canvas` / `save_seo_article` に本文を渡さない。

## SEO計測・調査タスク（Ahrefs / GSC / GA4 / Meta広告 / WordPress を使う場合。用途はこれに限らない。）
- Ahrefs を使って現状のSEO指標を初期分析し、着目ポイントを理由付きで示すなど。
- 追加で深掘りすべき項目を明示し、理由を説明することもできる。
- GSC / GA4 / Meta広告 でどのデータを確認するかを示し、それで何が分かるかを説明し、得られた結果をまとめることもできる。
- 全体を総括し、課題と次アクションを分かりやすく提示する（専門用語には簡単な補足を）。
- 必要に応じて WordPress MCP で記事やメタ情報の現状を確認し、改善案の根拠にする（公開/下書きなど状態確認のみ行う）。

## WordPress MCP 利用ルール
- WordPress MCP は適切に必要な機能を使用する。
- まずアビリティ一覧を確認して、必要な機能を使用する。


出力形式: 見出し付きステップ（例: 1. Ahrefsを用いた初期分析）、箇条書き・表を活用し、根拠データを具体的に引用する。

対象アカウント/プロパティ（必要時のみ参照）:
- GA4: hitocareer.com (ID: 423714093) / achievehr.jp (ID: 502875325)
- WordPress MCP: ラベル `wordpress` = hitocareer.com（閲覧専用）、ラベル `achieve` = achievehr.jp（閲覧専用）。サイトを取り違えないこと。
- Analyticsアカウント: hitocareer.com (ID: 299317813) / achievehr.jp (ID: 366605478)

## Zoho CRM（APP-hc: 求職者データ）利用ガイド

### 利用可能なツール
- `search_job_seekers`: 流入経路・ステータス等で顧客検索
- `get_job_seeker_detail`: 特定顧客の詳細取得
- `aggregate_by_channel`: 流入経路別の集計
- `count_job_seekers_by_status`: ステータス別の集計（ファネル分析）
- `get_channel_definitions`: 流入経路・ステータスの定義一覧

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
- `5. 選考中`: 企業選考中
- `6. 内定`: 内定獲得
- `7. 入社`: 入社決定
- `16. クローズ`: 案件終了

### 横断分析の例
1. **広告効果分析**: Meta広告のパフォーマンス（Meta Ads MCP）→ `paid_meta` 流入顧客のステータス分布（Zoho）
2. **ROAS分析**: 広告費（Meta Ads MCP）÷ 成約数（Zoho）= CPA算出
3. **流入経路比較**: スカウト系 vs 広告系の成約率比較
4. **ファネル分析**: 特定流入経路のリード→面談→入社の転換率確認
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


class MarketingAgentFactory:
    def __init__(self, settings: Settings):
        self._settings = settings

    def build_agent(
        self,
        asset: dict[str, Any] | None = None,
        disabled_mcp_servers: set[str] | None = None,
    ) -> Agent:
        tools: List[Any] = []

        enable_web_search = self._settings.marketing_enable_web_search and (
            asset is None or asset.get("enable_web_search", True)
        )
        enable_code_interpreter = self._settings.marketing_enable_code_interpreter and (
            asset is None or asset.get("enable_code_interpreter", True)
        )
        enable_canvas = self._settings.marketing_enable_canvas and (
            asset is None or asset.get("enable_canvas", True)
        )

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

        canvas_tools = [
            create_seo_article,
            get_seo_article,
            save_seo_article,
            save_seo_article_body,
            seo_open_canvas,
            seo_update_canvas,
            apply_patch_to_article,
        ]
        if enable_canvas:
            tools.extend(canvas_tools)

        # Zoho CRM ツールを追加（顧客検索・集計用）
        enable_zoho_crm = asset is None or asset.get("enable_zoho_crm", True)
        if enable_zoho_crm and self._settings.zoho_refresh_token:
            tools.extend(ZOHO_CRM_TOOLS)

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
        if not enable_canvas:
            parts.append(
                "このプリセットでは記事キャンバス（Canvas）/SEO記事編集ツールが無効です。"
                "seo_open_canvas, seo_update_canvas, create_seo_article, save_seo_article, "
                "save_seo_article_body, get_seo_article, apply_patch_to_article などのキャンバス系ツールは呼び出さず、"
                "アウトラインや本文が必要な場合はチャット欄で直接提示してください。"
                "記事の永続化や右ペイン更新は行いません。"
            )
        parts.append(base_instructions)
        final_instructions = "\n\n".join(parts)

        stop_at_tool_names = [
            "seo_open_canvas",
            "seo_update_canvas",
            "create_seo_article",
            "save_seo_article",
        ] if enable_canvas else []

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
            tool_use_behavior=StopAtTools(stop_at_tool_names=stop_at_tool_names)
            if stop_at_tool_names
            else "run_llm_again",
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

        if (
            self._settings.ga4_mcp_server_url
            and self._settings.ga4_mcp_authorization
            and allow_ga4
            and not is_disabled("ga4")
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
            self._settings.meta_ads_mcp_server_url
            and self._settings.meta_ads_mcp_authorization
            and allow_meta_ads
            and not is_disabled("meta_ads")
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
        if (
            self._settings.gsc_mcp_server_url
            and self._settings.gsc_mcp_api_key
            and allow_gsc
            and not is_disabled("gsc")
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
                        "allowed_tools": WORDPRESS_ALLOWED_TOOLS,
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
                        "allowed_tools": WORDPRESS_ALLOWED_TOOLS,
                        "require_approval": "never",
                        "headers": {
                            "Authorization": self._settings.wordpress_achieve_mcp_authorization
                        },
                    }
                )
            )
        return hosted
