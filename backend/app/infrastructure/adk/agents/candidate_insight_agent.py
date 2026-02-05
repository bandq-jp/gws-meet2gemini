"""
Candidate Insight Agent (ADK version) - Candidate analysis.

Handles competitor risk, urgency assessment, and transfer pattern analysis.
Uses function tools from the existing implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .base import SubAgentFactory
# Import ADK-compatible candidate insight tools
from app.infrastructure.adk.tools.candidate_insight_tools import ADK_CANDIDATE_INSIGHT_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings


class CandidateInsightAgentFactory(SubAgentFactory):
    """
    Factory for ADK Candidate Insight sub-agent.

    Specializes in:
    - Competitor agent risk analysis
    - Urgency assessment
    - Transfer pattern analysis
    - Interview briefings
    """

    @property
    def agent_name(self) -> str:
        return "CandidateInsightAgent"

    @property
    def tool_name(self) -> str:
        return "call_candidate_insight_agent"

    @property
    def tool_description(self) -> str:
        return (
            "候補者の競合リスク分析、緊急度評価、転職パターン分析、面談ブリーフィング生成。"
            "Supabase構造化データとZoho CRMデータを統合した高度な分析を実施。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return candidate insight function tools."""
        # ADK automatically wraps Python functions as tools
        return list(ADK_CANDIDATE_INSIGHT_TOOLS)

    def _build_instructions(self) -> str:
        return """
あなたは候補者分析の専門家です。

## 担当領域
- 競合エージェントリスク分析
- 緊急度評価（即時対応必要候補者の特定）
- 転職理由・パターン分析
- 面談ブリーフィング生成

---

## 利用可能なツール

### analyze_competitor_risk
- 競合エージェント利用状況の分析
- 他社オファー有無の確認
- 高リスク候補者の特定

### assess_candidate_urgency
- 転職希望時期の評価
- 離職状況の確認
- 優先対応候補者の特定

### analyze_transfer_patterns
- 転職理由の傾向分析
- 動機パターンの可視化
- マーケティング施策への示唆

### generate_candidate_briefing
- 面談前準備用の統合情報
- Zoho基本情報 + 議事録詳細の統合
- アクションポイントの提示

---

## 回答方針
- リスクレベルを明確に提示
- 優先順位付けを行う
- 具体的なアクション提案を含める
"""

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """Build ADK agent with function tools."""
        tools = self._get_domain_tools(mcp_servers, asset)

        return Agent(
            name=self.agent_name,
            model=self.model,
            description=self.tool_description,
            instruction=self._build_instructions(),
            tools=tools,
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    thinking_level="high",
                ),
            ),
        )
