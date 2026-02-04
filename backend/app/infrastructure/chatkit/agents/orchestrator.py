"""
Orchestrator Agent - Main coordinator for marketing AI.

Coordinates sub-agents and manages user interaction.
Tools: 6 sub-agent tools + native tools (Web Search, Code Interpreter)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from agents import Agent, CodeInterpreterTool, ModelSettings, WebSearchTool
from openai.types.shared.reasoning import Reasoning

from .analytics_agent import AnalyticsAgentFactory
from .ad_platform_agent import AdPlatformAgentFactory
from .seo_agent import SEOAgentFactory
from .wordpress_agent import WordPressAgentFactory
from .zoho_crm_agent import ZohoCRMAgentFactory
from .candidate_insight_agent import CandidateInsightAgentFactory

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


ORCHESTRATOR_INSTRUCTIONS = """
あなたはb&qマーケティングAIオーケストレーターです。

## 役割
- ユーザーの質問を分析し、適切なサブエージェントを選択
- 複数ドメインにまたがる質問は並列でサブエージェントを呼び出し
- サブエージェントの結果を統合し、アクショナブルな回答を生成
- 単純な質問（挨拶、一般知識）はサブエージェントを使わず直接回答

## 利用可能なサブエージェント

### call_analytics_agent
Google Analytics 4とSearch Consoleのデータ分析。
用途: トラフィック分析、検索パフォーマンス、URLインスペクション

### call_ad_platform_agent
Meta広告（Facebook/Instagram）のキャンペーン分析とターゲティング調査。
用途: 広告パフォーマンス、オーディエンス分析、インタレスト調査

### call_seo_agent
Ahrefs SEO分析、キーワード調査、バックリンク分析、競合サイト調査。
用途: ドメイン評価、オーガニックキーワード、被リンク分析

### call_wordpress_agent
hitocareer.comとachievehr.jpの記事作成・編集・分析。
用途: 記事構成確認、ブロック編集、メディア管理

### call_zoho_crm_agent
求職者CRMデータの検索・集計・ファネル分析・チャネル比較。
用途: 求職者検索、チャネル効果測定、ファネル分析

### call_candidate_insight_agent
候補者の競合リスク分析、緊急度評価、転職パターン分析。
用途: 高リスク候補者特定、優先対応判断、面談準備

## 対象プロパティ
- GA4: hitocareer.com (423714093) / achievehr.jp (502875325)
- WordPress: wordpress=hitocareer.com / achieve=achievehr.jp

## 並列呼び出しの例

### 例1: マーケティング効果測定
ユーザー: 「今月のトラフィックと求職者応募状況を教えて」
→ call_analytics_agent + call_zoho_crm_agent を並列呼び出し

### 例2: 競合分析
ユーザー: 「SEO競合分析とMeta広告のパフォーマンスを比較して」
→ call_seo_agent + call_ad_platform_agent を並列呼び出し

### 例3: 候補者管理
ユーザー: 「高リスクの候補者とチャネル別の成約率を分析して」
→ call_candidate_insight_agent + call_zoho_crm_agent を並列呼び出し

## 回答方針
- データは表形式やリストで見やすく整理
- 複数ソースからの情報を統合して全体像を提示
- アクション可能な提案を含める
- 不明点はWeb Searchで補足
"""


class OrchestratorAgentFactory:
    """
    Factory for the Orchestrator agent.

    The Orchestrator:
    - Exposes sub-agents as tools via Agent.as_tool()
    - Has native tools (WebSearch, CodeInterpreter)
    - Uses GPT-5.2 for high-quality reasoning
    - Coordinates parallel/sequential sub-agent calls
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
        }

    def build_agent(
        self,
        asset: Dict[str, Any] | None = None,
        disabled_mcp_servers: set[str] | None = None,
        mcp_servers: List[Any] | None = None,
    ) -> Agent:
        """
        Build the Orchestrator agent with sub-agent tools.

        Args:
            asset: Model asset configuration (reasoning_effort, etc.)
            disabled_mcp_servers: Set of MCP server labels to disable
            mcp_servers: Local MCP server instances

        Returns:
            Configured Orchestrator Agent
        """
        # Build sub-agent tools
        sub_agent_tools = []
        for name, factory in self._sub_factories.items():
            try:
                sub_agent = factory.build_agent(mcp_servers=mcp_servers, asset=asset)
                tool = sub_agent.as_tool(
                    tool_name=factory.tool_name,
                    tool_description=factory.tool_description,
                )
                sub_agent_tools.append(tool)
                logger.debug(f"Sub-agent tool registered: {factory.tool_name}")
            except Exception as e:
                logger.warning(f"Failed to build sub-agent {name}: {e}")

        # Native tools for the orchestrator
        native_tools = self._get_native_tools(asset)

        # Get reasoning effort from asset or settings
        reasoning_effort = (
            asset.get("reasoning_effort")
            if asset
            else self._settings.marketing_reasoning_effort
        ) or "high"

        # Build final instructions
        instructions = self._build_instructions(asset)

        return Agent(
            name="MarketingOrchestrator",
            instructions=instructions,
            tools=native_tools + sub_agent_tools,
            model=self._settings.marketing_agent_model,
            model_settings=ModelSettings(
                store=True,
                reasoning=Reasoning(
                    effort=reasoning_effort,
                    summary="detailed",
                ),
                verbosity=self._normalize_verbosity(
                    asset.get("verbosity") if asset else None
                ),
                response_include=["code_interpreter_call.outputs"],
            ),
            tool_use_behavior="run_llm_again",
        )

    def _get_native_tools(self, asset: Dict[str, Any] | None = None) -> List[Any]:
        """Return native tools for the orchestrator."""
        tools: List[Any] = []

        enable_web_search = self._settings.marketing_enable_web_search and (
            asset is None or asset.get("enable_web_search", True)
        )
        enable_code_interpreter = self._settings.marketing_enable_code_interpreter and (
            asset is None or asset.get("enable_code_interpreter", True)
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

        return tools

    def _build_instructions(self, asset: Dict[str, Any] | None = None) -> str:
        """Build orchestrator instructions with optional additions."""
        base_instructions = ORCHESTRATOR_INSTRUCTIONS.strip()

        addition = (asset or {}).get("system_prompt_addition")
        if addition:
            return f"{addition.strip()}\n\n{base_instructions}"

        return base_instructions

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
