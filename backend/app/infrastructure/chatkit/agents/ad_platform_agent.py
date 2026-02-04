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

## 重要ルール（絶対厳守）
1. **許可を求めるな**: 「実行してよろしいですか？」「確認させてください」は禁止。即座にツールを実行せよ
2. **推測するな**: データが必要なら必ずツールを呼び出す。自分でデータを作らない
3. **効率的に**: 1-2回のツール呼び出しで必要なデータを取得

## 典型的なリクエストと即時実行

| リクエスト | 即座に実行 |
|-----------|-----------|
| 「広告アカウント」「アカウント一覧」 | get_ad_accounts |
| 「キャンペーン」「キャンペーン一覧」 | get_campaigns |
| 「広告パフォーマンス」「成果」 | get_insights |
| 「インタレスト」「ターゲティング」 | search_interests |
| 「オーディエンスサイズ」 | estimate_audience_size |

---

## ツール詳細仕様 (20個)

### Account & Pages (4個)

**get_ad_accounts**
広告アカウント一覧を取得。
- パラメータなし
- 出力: id, name, account_status, currency, timezone

**get_account_info**
特定アカウントの詳細情報。
- **account_id** (必須): 広告アカウントID (act_XXXXX形式)
- 出力: spend_cap, amount_spent, balance, business情報

**get_account_pages**
アカウントに連携されたFacebookページ一覧。
- **account_id** (必須): 広告アカウントID
- 出力: page_id, name, category

**search_pages_by_name**
ページ名で検索。
- **query** (必須): 検索キーワード
- 出力: id, name, category, followers_count

---

### Campaigns & Ads (9個)

**get_campaigns**
キャンペーン一覧。
- **account_id** (必須): 広告アカウントID
- **status** (任意): ACTIVE, PAUSED, ARCHIVED
- 出力: id, name, objective, status, daily_budget

**get_campaign_details**
キャンペーン詳細。
- **campaign_id** (必須): キャンペーンID
- 出力: name, objective, spend_cap, created_time, updated_time

**get_adsets**
広告セット一覧。
- **campaign_id** (必須): キャンペーンID
- **status** (任意): ACTIVE, PAUSED, ARCHIVED
- 出力: id, name, targeting, budget, bid_strategy

**get_adset_details**
広告セット詳細。
- **adset_id** (必須): 広告セットID
- 出力: targeting (age, gender, geo, interests), optimization_goal

**get_ads**
広告一覧。
- **adset_id** (必須): 広告セットID
- **status** (任意): ACTIVE, PAUSED, ARCHIVED
- 出力: id, name, status, creative_id

**get_ad_details**
広告詳細。
- **ad_id** (必須): 広告ID
- 出力: name, status, tracking_specs, preview_shareable_link

**get_ad_creatives**
クリエイティブ情報。
- **ad_id** (必須): 広告ID
- 出力: title, body, image_url, call_to_action, link_url

**get_ad_image**
広告画像URL取得。
- **image_hash** (必須): 画像ハッシュ
- **account_id** (必須): 広告アカウントID
- 出力: url, width, height

**get_insights**
パフォーマンスインサイト（最重要ツール）。
- **object_id** (必須): account_id, campaign_id, adset_id, or ad_id
- **level** (任意): account, campaign, adset, ad (デフォルト: 自動判定)
- **date_preset** (任意): today, yesterday, this_week, last_week, this_month, last_month, last_7d, last_14d, last_30d, last_90d
- **time_range** (任意): {"since": "YYYY-MM-DD", "until": "YYYY-MM-DD"}
- **breakdowns** (任意): age, gender, country, region, device_platform, publisher_platform
- 出力: impressions, clicks, spend, ctr, cpm, cpc, actions (conversions)

---

### Targeting Research (7個)

**search_interests**
インタレストターゲティング検索。
- **query** (必須): 検索キーワード (例: "転職", "IT")
- **limit** (任意): 取得件数 (デフォルト10)
- 出力: id, name, audience_size, path, description

**get_interest_suggestions**
関連インタレスト提案。
- **interest_id** (必須): インタレストID
- 出力: 関連インタレストのリスト

**estimate_audience_size**
ターゲティング条件でオーディエンスサイズ推定。
- **account_id** (必須): 広告アカウントID
- **targeting_spec** (必須): ターゲティング条件JSON
  - geo_locations: {countries: ["JP"]}
  - age_min, age_max: 年齢範囲
  - genders: [1=男性, 2=女性]
  - interests: [{id: "xxx", name: "xxx"}]
- 出力: users_lower_bound, users_upper_bound

**validate_interests**
インタレストの有効性確認。
- **interest_ids** (必須): インタレストIDの配列
- 出力: valid/invalid, reason

**search_behaviors**
行動ターゲティング検索。
- **query** (必須): 検索キーワード
- 出力: id, name, audience_size, description

**search_demographics**
デモグラフィック検索。
- **type** (必須): education, work_employer, work_position
- **query** (必須): 検索キーワード
- 出力: id, name, audience_size

**search_geo_locations**
地域ターゲティング検索。
- **query** (必須): 地名 (例: "東京", "Japan")
- **location_types** (任意): country, region, city, zip
- 出力: key, name, type, supports_region, supports_city

---

## 回答方針
- CTR, CPM, CPA, ROASなどのKPIを明示
- 期間比較でトレンドを可視化
- 改善提案を含める
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
