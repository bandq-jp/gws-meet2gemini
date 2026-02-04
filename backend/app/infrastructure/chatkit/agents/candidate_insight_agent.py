"""
Candidate Insight Agent - Advanced candidate analysis.

Handles competitive risk, urgency assessment, and transfer pattern analysis
by combining Zoho CRM data with structured meeting notes.
Tools: 4 function tools + native tools
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from agents import Agent, ModelSettings
from openai.types.shared.reasoning import Reasoning

from .base import SubAgentFactory
from ..candidate_insight_tools import CANDIDATE_INSIGHT_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings


class CandidateInsightAgentFactory(SubAgentFactory):
    """
    Factory for Candidate Insight sub-agent.

    Specializes in:
    - Competitive agent risk analysis
    - Candidate urgency assessment
    - Transfer pattern analysis
    - Interview briefing generation
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
            "Zoho CRMと議事録構造化データを組み合わせた高度な分析を担当。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return Candidate Insight function tools."""
        # Candidate Insight tools require Zoho to be enabled
        if not self._settings.zoho_refresh_token:
            return []

        return list(CANDIDATE_INSIGHT_TOOLS)

    def _build_instructions(self) -> str:
        return """
あなたは候補者インサイト分析の専門家です。

## 担当領域
- 競合エージェント利用状況の分析
- 緊急度評価（転職希望時期、離職状況）
- 転職パターン・動機の分析
- 面談準備用ブリーフィング生成

## データソース
- **Zoho CRM**: 求職者基本情報（流入経路・ステータス・年収等）
- **Supabase**: 構造化抽出データ（議事録から抽出した詳細情報）

## 利用可能なツール (4個)

### analyze_competitor_risk
競合エージェント分析。他社利用状況、選考中企業、他社オファーから高リスク候補者を特定。

### assess_candidate_urgency
緊急度評価。転職希望時期、離職状況、選考進捗から優先順位付け。

### analyze_transfer_patterns
転職パターン分析。転職理由・動機の傾向分析（マーケティング施策の参考）。

### generate_candidate_briefing
候補者ブリーフィング。面談前準備用のZoho + 議事録統合表示。

## 構造化データフィールド（議事録から抽出）

### 転職活動状況
- transfer_activity_status: 転職活動状況
- current_agents: 利用中エージェント
- companies_in_selection: 選考中企業
- other_offer_salary: 他社オファー年収

### 転職理由・希望
- transfer_reasons: 転職理由（23種）
- desired_timing: 希望転職時期
- current_job_status: 現在の就業状況
- transfer_priorities: 転職の優先事項

### キャリアビジョン
- career_vision: キャリアビジョン
- business_vision: 事業への関心

## 回答方針
- リスクスコア・緊急度スコアを明示
- 優先対応すべき候補者を特定
- 面談準備に必要な情報を網羅
- パターン分析はマーケティング施策に活用可能な形で提示
"""

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """Build agent (no MCP servers, only function tools)."""
        tools = self._get_native_tools() + self._get_domain_tools(mcp_servers, asset)

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
        )
