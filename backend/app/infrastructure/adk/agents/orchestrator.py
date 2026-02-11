"""
Orchestrator Agent (Google ADK version) - Main coordinator for marketing AI.

Coordinates sub-agents using ADK's AgentTool pattern.
Uses Gemini models natively without LiteLLM.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools import AgentTool
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .analytics_agent import AnalyticsAgentFactory
from .ad_platform_agent import AdPlatformAgentFactory
from .seo_agent import SEOAgentFactory
from .wordpress_agent import WordPressAgentFactory
from .zoho_crm_agent import ZohoCRMAgentFactory
from .candidate_insight_agent import CandidateInsightAgentFactory
from .company_db_agent import CompanyDatabaseAgentFactory
from .ca_support_agent import CASupportAgentFactory
from .google_search_agent import GoogleSearchAgentFactory
from .code_execution_agent import CodeExecutionAgentFactory
from .workspace_agent import GoogleWorkspaceAgentFactory
from .slack_agent import SlackAgentFactory
from app.infrastructure.adk.tools.chart_tools import ADK_CHART_TOOLS
from app.infrastructure.adk.tools.ask_user_tools import ADK_ASK_USER_TOOLS
from app.infrastructure.adk.mcp_manager import ADKMCPToolsets

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


ORCHESTRATOR_INSTRUCTIONS = """
あなたは株式会社b&qエージェント（統合AIアシスタント）です。マーケティング・採用・候補者支援を横断して分析・提案を行います。

## 現在の日時（日本時間）
- **{app:current_date}（{app:day_of_week}曜日） {app:current_time}**
- 全ての日付計算はこの日付を基準にYYYY-MM-DD形式で算出

## 現在のユーザー
- 氏名: {app:user_name}
- メール: {app:user_email}
- Slack: {app:slack_display_name?}（@{app:slack_username?}）
- 「○○さん」と呼びかけること
- 「自分のメール/予定」→ GoogleWorkspaceAgent、「自分のSlack」→ SlackAgent
- 「自分の担当候補者」→ ZohoCRMAgent / CASupportAgent（PIC = ユーザー名で検索）

## 重要ルール（絶対厳守）
1. **許可を求めるな**: 即座にサブエージェントを呼び出せ。ユーザーへ情報を求める場合は例外
2. **データは必ずツールで取得**: 推測・捏造禁止。数値には根拠・ソースを添える
3. **並列実行を活用**: 独立した複数サブエージェントは並列で呼び出す
4. **挨拶や一般知識のみ**: サブエージェント不要
5. **記憶を活用**: <PAST_CONVERSATIONS>タグの過去の会話を理解して回答

---

## サブエージェント選択ガイド

| エージェント | 代表キーワード |
|------------|-------------|
| AnalyticsAgent | セッション, PV, トラフィック, 検索パフォーマンス, 順位 (GA4: hitocareer 423714093, achievehr 502875325) |
| SEOAgent | DR, 被リンク, オーガニック, キーワード調査, 競合サイト |
| AdPlatformAgent | Meta広告, Facebook, Instagram, CTR, CPA, CPM, ROAS, ターゲティング, クリエイティブ |
| WordPressAgent | 記事, ブログ, WordPress |
| ZohoCRMAgent | 求職者, チャネル別, 成約率, ファネル, CRM, COQL, JOB, HRBP |
| CandidateInsightAgent | 高リスク, 緊急度, 競合エージェント |
| CompanyDatabaseAgent | 企業検索, 採用要件, 訴求ポイント, セマンティック検索, 候補者マッチング |
| CASupportAgent | CA支援, 面談準備, 企業提案, 候補者プロファイル, 議事録 |
| GoogleSearchAgent | 最新, ニュース, トレンド, Web検索, 市場動向 |
| CodeExecutionAgent | 計算, Python, コード実行, 集計, シミュレーション |
| GoogleWorkspaceAgent | メール, Gmail, 予定, カレンダー, スケジュール |
| SlackAgent | Slack, チャネル, スレッド, メンション |

## CASupportAgent vs 専門エージェントの使い分け
- **CASupportAgent**: 特定候補者のクロスドメイン分析（CRM + 議事録 + 企業DB）、面談準備、候補者プロファイル + 企業マッチング一括
- **専門エージェント**: 集団分析（チャネル全体の成約率等）→ ZohoCRMAgent、企業DBのみ検索 → CompanyDatabaseAgent、単一ドメイン深堀り → 各専門エージェント

## 並列呼び出し例
- マーケ全体: AnalyticsAgent + AdPlatformAgent + ZohoCRMAgent
- CA面談準備: CASupportAgent（統合エージェント1つで対応）
- 企業多面調査: CompanyDatabaseAgent + SlackAgent
- データ+最新情報: GoogleSearchAgent + ZohoCRMAgent

---

## 中間報告ルール
ツール実行前後に今何をしているかを**1〜2文の短文**で報告。無言でツールを連続実行するな。

## チャート描画ルール（厳守）
数値データ可視化は **`render_chart` ツールを function call で呼び出せ**。テキスト中に ```json で chart spec を貼るな。

| データの性質 | type | 必須キー |
|------------|------|---------|
| 時系列推移 | line | xKey, yKeys |
| カテゴリ比較 | bar | xKey, yKeys |
| 構成比 | pie / donut | nameKey, valueKey |
| ファネル | funnel | nameField, valueField |
| 相関 | scatter | xKey, yKeys |
| 多軸比較 | radar | xKey, yKeys |
| 一覧データ | table | columns |

## 回答方針
- 複数ソースの結果を統合し、アクション可能な提案を含める
- **出典・ソースの提示**: データの出所を添える。Web検索結果にはURLを必ず含める
- **大量データ**: 上位10件に絞り、全体サマリー付き
- **日付デフォルト**: 期間未指定→直近3ヶ月

## ユーザーへの確認（ask_user_clarification）
質問が複数解釈可能な場合のみ使用。明確な質問には即座にサブエージェントを呼べ。
- `header`: 12文字以内の短いラベル
- `options`: 2〜4個。`label`は1〜5語
- 「その他」は自動追加されるので含めない
- 選択肢提示後はテキスト出力を止めてユーザーの選択を待つ
"""


class OrchestratorAgentFactory:
    """
    Factory for the ADK Orchestrator agent.

    The Orchestrator:
    - Exposes sub-agents as tools via AgentTool
    - Coordinates parallel/sequential sub-agent calls
    - Uses Gemini Pro for orchestration
    """

    def __init__(self, settings: "Settings"):
        self._settings = settings
        self._sub_factories: Dict[str, Any] = {
            "analytics": AnalyticsAgentFactory(settings),
            "ad_platform": AdPlatformAgentFactory(settings),
            "seo": SEOAgentFactory(settings),
            "wordpress": WordPressAgentFactory(settings),
            "zoho_crm": ZohoCRMAgentFactory(settings),
            "candidate_insight": CandidateInsightAgentFactory(settings),
            "company_db": CompanyDatabaseAgentFactory(settings),
            "ca_support": CASupportAgentFactory(settings),
            "google_search": GoogleSearchAgentFactory(settings),
            "code_execution": CodeExecutionAgentFactory(settings),
            "google_workspace": GoogleWorkspaceAgentFactory(settings),
            "slack": SlackAgentFactory(settings),
        }

    @property
    def model(self) -> str:
        """
        Model to use for the orchestrator.

        ADK native Gemini support - no LiteLLM needed.
        """
        return self._settings.adk_orchestrator_model or "gemini-2.5-flash-preview-05-20"

    def build_agent(
        self,
        asset: Dict[str, Any] | None = None,
        disabled_mcp_servers: set[str] | None = None,
        mcp_toolsets: ADKMCPToolsets | None = None,
    ) -> Agent:
        """
        Build the Orchestrator agent with sub-agent tools.

        Args:
            asset: Model asset configuration
            disabled_mcp_servers: Set of MCP server labels to disable
            mcp_toolsets: ADK MCP toolsets container (GA4, GSC, Meta Ads, etc.)

        Returns:
            Configured ADK Orchestrator Agent
        """
        # Build sub-agent tools using AgentTool
        sub_agent_tools = []
        logger.info("[ADK Orchestrator] Building sub-agent tools")

        # Map sub-agent factories to their MCP toolsets
        mcp_mapping: Dict[str, List[Any]] = {
            "analytics": [],
            "ad_platform": [],
            "seo": [],
            "wordpress": [],
            "zoho_crm": [],  # Uses function tools, no MCP
            "candidate_insight": [],  # Uses function tools, no MCP
            "company_db": [],  # Uses function tools (Google Sheets), no MCP
            "ca_support": [],  # Unified agent with all function tools, no MCP
            "google_search": [],  # Uses built-in google_search, no MCP
            "code_execution": [],  # Uses BuiltInCodeExecutor, no MCP
            "google_workspace": [],  # Uses function tools (Gmail/Calendar API), no MCP
            "slack": [],  # Uses function tools (Slack API), no MCP
        }

        # Populate MCP mapping if toolsets are provided
        if mcp_toolsets:
            if mcp_toolsets.ga4:
                mcp_mapping["analytics"].append(mcp_toolsets.ga4)
            if mcp_toolsets.gsc:
                mcp_mapping["analytics"].append(mcp_toolsets.gsc)
            if mcp_toolsets.meta_ads:
                mcp_mapping["ad_platform"].append(mcp_toolsets.meta_ads)
            if mcp_toolsets.ahrefs:
                mcp_mapping["seo"].append(mcp_toolsets.ahrefs)
            if mcp_toolsets.wordpress_hitocareer:
                mcp_mapping["wordpress"].append(mcp_toolsets.wordpress_hitocareer)
            if mcp_toolsets.wordpress_achievehr:
                mcp_mapping["wordpress"].append(mcp_toolsets.wordpress_achievehr)

        for name, factory in self._sub_factories.items():
            try:
                # Get domain-specific MCP toolsets
                domain_mcp = mcp_mapping.get(name, [])
                sub_agent = factory.build_agent(mcp_servers=domain_mcp, asset=asset)

                # Wrap sub-agent as AgentTool
                tool = AgentTool(agent=sub_agent)
                sub_agent_tools.append(tool)
                mcp_count = len(domain_mcp)
                logger.info(f"[ADK Orchestrator] Sub-agent registered: {factory.agent_name} ({mcp_count} MCP toolsets)")
            except Exception as e:
                logger.warning(f"Failed to build sub-agent {name}: {e}")

        # Build final instructions
        instructions = self._build_instructions(asset)

        # Combine sub-agent tools with chart tools and ask_user tools
        all_tools = sub_agent_tools + list(ADK_CHART_TOOLS) + list(ADK_ASK_USER_TOOLS)

        # Add PreloadMemoryTool if memory is enabled
        # This automatically injects relevant past conversations into system prompt
        if self._settings.memory_preload_enabled:
            all_tools.append(PreloadMemoryTool())
            logger.info("[ADK Orchestrator] PreloadMemoryTool enabled")

        return Agent(
            name="MarketingOrchestrator",
            model=self.model,
            description="マーケティングAIオーケストレーター - 複数の専門エージェントを調整して分析を実行",
            instruction=instructions,
            tools=all_tools,
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    thinking_level="medium",
                ),
            ),
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=self._settings.adk_max_output_tokens,
            ),
        )

    def _build_instructions(self, asset: Dict[str, Any] | None = None) -> str:
        """Build orchestrator instructions with optional additions."""
        base_instructions = ORCHESTRATOR_INSTRUCTIONS.strip()

        addition = (asset or {}).get("system_prompt_addition")
        if addition:
            return f"{addition.strip()}\n\n{base_instructions}"

        return base_instructions
