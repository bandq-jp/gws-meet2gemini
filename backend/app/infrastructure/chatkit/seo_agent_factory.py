from __future__ import annotations

from typing import Any, Dict, List

from agents import (
    Agent,
    CodeInterpreterTool,
    HostedMCPTool,
    ModelSettings,
    WebSearchTool,
)
from openai.types.shared.reasoning import Reasoning

from app.infrastructure.config.settings import Settings

MARKETING_WORKFLOW_ID = (
    "wf_690a1d2e1ce881908e92b6826428f3af060621f24cf1b2bb"
)


MARKETING_INSTRUCTIONS = """
下記のタスクを段階的かつ分かりやすく実行してください。ただし、指示があったときに限ります。ユーザーからの入力に従って答えてください（日本語で回答）：

SEO状況の分析・調査を、Ahrefs、Google Search Console（GSC）、Google Analytics（GA4）をすべて活用して行い、その過程・根拠・結果を整理し、人間に分かりやすく報告してください。各分析ステップごとに明確に分けて解説し、分析の根拠や着目点を示しつつ、最終的に全体を分かりやすくまとめてください。

対象アカウント・プロパティ：
- アナリティクス アカウント: hitocareer.com（ID: 299317813）
- プロパティとアプリ: hitocareer.com（ID: 423714093）

# 手順

1. **Ahrefsを用いたSEO状況の初期分析**  
   - Ahrefsの主要指標やデータを用いて、現時点でのサイトSEO状況を客観的に分析してください。
   - どの項目や課題に着目したのか、その理由を併記してください。

2. **必要な追加分析の特定**  
   - Ahrefsの分析結果から、さらに詳細に調査すべき領域や指標を明示し、なぜそれらが必要か説明してください。

3. **Google Search ConsoleおよびGoogle Analyticsによる深掘り分析**  
   - GSCやGA4で具体的にどんなデータやレポートを確認するかを明記し、それによって何が分かるか説明してください。
   - 各ツールで得られた主要な結果をそれぞれまとめてください。

4. **総括と提案**  
   - 全ての分析結果を踏まえて、総括的に状況・課題・次のアクション案を整理してください。
   - 専門用語や業界用語は一般的に分かりやすく補足してください。

# 出力形式

- 各ステップを見出し・番号付きで分けてください（例: 「1. Ahrefsを用いた初期分析」）。
- 箇条書き、表、マークダウンを適宜使い、要点を明瞭にまとめてください。
- 各ツールで得たデータや根拠を具体的に引用してください。
- 全体のまとめ・提案・解説は文章で簡潔に述べてください。

---
**1. Ahrefsを用いた初期分析**  
- ドメイン評価（DR）がXXであるため、競合と比較して状況は○○。
- 流入キーワードの上位は[例: ○○]で、～～に強み/課題あり。

**2. 追加分析事項**  
- 流入減少のあるキーワード群：クリック数推移の詳細調査が必要（理由：上位表示の変動があったため）。

**3. GSC/GA4による深掘り**  
- GSCでCTRが大きく低下しているクエリを抽出し、流入減の要因を分析。
- GA4で直帰率や新規/リピーター率を確認し、ユーザ挙動の変化を評価。

**4. 総括と提案**  
- 主な課題：特定クエリの順位低下とCTR低下
- 対応案：該当ページのタイトル改善＆内部リンク追加を推奨

---

# 注意事項
- 事実データ・定量情報は、具体的に示してください。
- 解説や提案は初心者にも分かりやすい簡潔な表現も含めてください。
- 必要に応じて、エキスパート向けに補足解説も加えてください。
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
