"""
Analytics Agent - GA4 + GSC integration.

Handles Google Analytics 4 and Search Console data analysis.
Tools: 16 MCP tools (6 GA4 + 10 GSC) + native tools
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from agents import HostedMCPTool

from .base import SubAgentFactory
from ..seo_agent_factory import GA4_ALLOWED_TOOLS, GSC_ALLOWED_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings


class AnalyticsAgentFactory(SubAgentFactory):
    """
    Factory for Analytics sub-agent.

    Specializes in:
    - GA4 traffic analysis, reports, real-time data
    - GSC search performance, URL inspection, sitemaps
    """

    @property
    def agent_name(self) -> str:
        return "AnalyticsAgent"

    @property
    def tool_name(self) -> str:
        return "call_analytics_agent"

    @property
    def tool_description(self) -> str:
        return (
            "Google Analytics 4とSearch Consoleのデータ分析を実行。"
            "トラフィック分析、検索パフォーマンス、URLインスペクション、"
            "リアルタイムレポート、期間比較などを担当。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return GA4 and GSC MCP tools."""
        tools: List[Any] = []

        # Check if local MCP servers are provided
        ga4_local = None
        gsc_local = None
        if mcp_servers:
            for server in mcp_servers:
                # Identify by command or name
                if hasattr(server, "_params"):
                    cmd = getattr(server._params, "command", "")
                    if "analytics-mcp" in cmd:
                        ga4_local = server
                    elif "gsc_server" in str(getattr(server._params, "args", [])):
                        gsc_local = server

        # GA4: Use local MCP if available, otherwise hosted
        use_local_ga4 = self._settings.use_local_mcp and self._settings.local_mcp_ga4_enabled
        if ga4_local and use_local_ga4:
            # Local MCP server is passed and will be added to agent's mcp_servers
            pass
        elif (
            self._settings.ga4_mcp_server_url
            and self._settings.ga4_mcp_authorization
        ):
            tools.append(
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

        # GSC: Use local MCP if available, otherwise hosted
        use_local_gsc = self._settings.use_local_mcp and self._settings.local_mcp_gsc_enabled
        if gsc_local and use_local_gsc:
            # Local MCP server is passed and will be added to agent's mcp_servers
            pass
        elif (
            self._settings.gsc_mcp_server_url
            and self._settings.gsc_mcp_api_key
        ):
            tools.append(
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

        return tools

    def _build_instructions(self) -> str:
        return """
あなたはWebアナリティクスの専門家です。

## 担当領域
- **GA4 (Google Analytics 4)**: トラフィック分析、ユーザー行動、コンバージョン
- **GSC (Google Search Console)**: 検索パフォーマンス、インデックス状況、URL検査

## 対象プロパティ
- hitocareer.com (GA4 ID: 423714093)
- achievehr.jp (GA4 ID: 502875325)

## 利用可能なツール

### GA4 (6個)
- get_account_summaries: アカウント一覧取得
- list_google_ads_links: Google Ads連携確認
- get_property_details: プロパティ詳細
- get_custom_dimensions_and_metrics: カスタム寸法/メトリクス
- run_realtime_report: リアルタイムレポート
- run_report: カスタムレポート実行

### GSC (10個)
- list_properties: プロパティ一覧
- get_site_details: サイト詳細
- get_search_analytics: 検索パフォーマンス
- get_performance_overview: パフォーマンス概要
- get_advanced_search_analytics: 高度な検索分析
- compare_search_periods: 期間比較
- get_search_by_page_query: ページ/クエリ別分析
- inspect_url_enhanced: URL検査
- batch_url_inspection: 一括URL検査
- get_sitemaps: サイトマップ一覧

## 回答方針
- データは表形式で見やすく整理
- 前期比・推移を可視化
- 改善提案を含める
- Web Searchで最新のSEO/アナリティクストレンドを補足
"""

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> "Agent":
        """Build agent with local MCP servers if available."""
        from agents import Agent, ModelSettings
        from openai.types.shared.reasoning import Reasoning

        tools = self._get_native_tools() + self._get_domain_tools(mcp_servers, asset)

        # Filter local MCP servers for GA4/GSC only
        agent_mcp_servers = []
        if mcp_servers:
            for server in mcp_servers:
                if hasattr(server, "_params"):
                    cmd = getattr(server._params, "command", "")
                    args = str(getattr(server._params, "args", []))
                    if "analytics-mcp" in cmd or "gsc_server" in args:
                        agent_mcp_servers.append(server)

        return Agent(
            name=self.agent_name,
            instructions=self._build_instructions(),
            tools=tools,
            model=self.model,
            model_settings=ModelSettings(
                store=True,
                reasoning=Reasoning(
                    effort=self.reasoning_effort,
                    summary="detailed",
                ),
                verbosity="medium",
            ),
            tool_use_behavior="run_llm_again",
            mcp_servers=agent_mcp_servers,
        )
