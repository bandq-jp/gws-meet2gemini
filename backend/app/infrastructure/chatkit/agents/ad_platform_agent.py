"""
Ad Platform Agent - Meta Ads integration.

Handles Meta (Facebook/Instagram) advertising analysis.
Tools: 20 MCP tools + native tools
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from agents import HostedMCPTool

from .base import SubAgentFactory
from ..seo_agent_factory import META_ADS_ALLOWED_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings


class AdPlatformAgentFactory(SubAgentFactory):
    """
    Factory for Ad Platform sub-agent.

    Specializes in:
    - Meta Ads campaign analysis
    - Ad performance insights
    - Audience targeting research
    """

    @property
    def agent_name(self) -> str:
        return "AdPlatformAgent"

    @property
    def tool_name(self) -> str:
        return "call_ad_platform_agent"

    @property
    def tool_description(self) -> str:
        return (
            "Meta広告（Facebook/Instagram）のキャンペーン分析とターゲティング調査。"
            "広告パフォーマンス、オーディエンス分析、インタレスト調査を担当。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return Meta Ads MCP tools."""
        tools: List[Any] = []

        # Check if local Meta Ads MCP is available
        meta_local = None
        if mcp_servers:
            for server in mcp_servers:
                if hasattr(server, "_params"):
                    cmd = getattr(server._params, "command", "")
                    if "meta-ads-mcp" in cmd:
                        meta_local = server

        # Use local MCP if available and token is configured
        use_local_meta = (
            self._settings.use_local_mcp
            and self._settings.local_mcp_meta_ads_enabled
            and self._settings.meta_access_token
        )

        if meta_local and use_local_meta:
            # Local MCP server will be added to agent's mcp_servers
            pass
        elif (
            self._settings.meta_ads_mcp_server_url
            and self._settings.meta_ads_mcp_authorization
        ):
            tools.append(
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

        return tools

    def _build_instructions(self) -> str:
        return """
あなたはMeta広告（Facebook/Instagram）の専門家です。

## 担当領域
- キャンペーン・広告セット・広告のパフォーマンス分析
- オーディエンスターゲティング調査
- クリエイティブ分析
- インタレスト・行動・デモグラフィック調査

## 利用可能なツール (20個)

### Account & Pages (4個)
- get_ad_accounts: 広告アカウント一覧
- get_account_info: アカウント詳細情報
- get_account_pages: 連携ページ一覧
- search_pages_by_name: ページ検索

### Campaigns & Ads (9個)
- get_campaigns: キャンペーン一覧
- get_campaign_details: キャンペーン詳細
- get_adsets: 広告セット一覧
- get_adset_details: 広告セット詳細
- get_ads: 広告一覧
- get_ad_details: 広告詳細
- get_ad_creatives: クリエイティブ情報
- get_ad_image: 広告画像取得
- get_insights: パフォーマンスインサイト

### Targeting Research (7個)
- search_interests: インタレスト検索
- get_interest_suggestions: インタレスト提案
- estimate_audience_size: オーディエンスサイズ推定
- validate_interests: インタレスト有効性確認
- search_behaviors: 行動ターゲティング検索
- search_demographics: デモグラフィック検索
- search_geo_locations: 地域検索

## 回答方針
- CTR, CPM, CPA, ROASなどのKPIを明示
- 期間比較でトレンドを可視化
- 改善提案を含める
- 競合トレンドはWeb Searchで補足
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

        # Filter local MCP servers for Meta Ads only
        agent_mcp_servers = []
        if mcp_servers:
            for server in mcp_servers:
                if hasattr(server, "_params"):
                    cmd = getattr(server._params, "command", "")
                    if "meta-ads-mcp" in cmd:
                        agent_mcp_servers.append(server)

        return Agent(
            name=self.agent_name,
            instructions=self._build_instructions(),
            tools=tools,
            model=self.model,
            model_settings=ModelSettings(
                store=True,
                parallel_tool_calls=True,
                reasoning=Reasoning(
                    effort=self.reasoning_effort,
                    summary="concise",
                ),
            ),
            tool_use_behavior="run_llm_again",
            mcp_servers=agent_mcp_servers,
        )
