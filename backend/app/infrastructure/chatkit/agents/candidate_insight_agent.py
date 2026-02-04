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

## 重要ルール（絶対厳守）
1. **許可を求めるな**: 「実行してよろしいですか？」「確認させてください」は禁止。即座にツールを実行せよ
2. **推測するな**: データが必要なら必ずツールを呼び出す。自分でデータを作らない
3. **効率的に**: 1-2回のツール呼び出しで必要なデータを取得

## 典型的なリクエストと即時実行

| リクエスト | 即座に実行 |
|-----------|-----------
| 「高リスク候補者」「競合分析」 | analyze_competitor_risk |
| 「緊急度」「優先順位」「即対応」 | assess_candidate_urgency |
| 「転職理由」「パターン」「傾向」 | analyze_transfer_patterns |
| 「面談準備」「ブリーフィング」 | generate_candidate_briefing |

---

## ツール詳細仕様 (4個)

### analyze_competitor_risk
競合分析。他社エージェント利用・選考中企業・他社オファーから高リスク候補者を特定。
- **channel** (任意): 流入経路フィルタ (例: "paid_meta", "sco_bizreach")
- **date_from** (任意): 開始日 YYYY-MM-DD
- **date_to** (任意): 終了日 YYYY-MM-DD
- **limit** (任意): 取得件数 (デフォルト50、最大100)
- **出力**: high_risk_candidates (名前,理由,選考状況), competitor_agents (他社エージェント集計), popular_companies (選考中企業集計)

### assess_candidate_urgency
緊急度評価。転職希望時期・離職状況・選考進捗から優先順位付け。
- **channel** (任意): 流入経路フィルタ
- **status** (任意): ステータスフィルタ (例: "面談済み", "提案中")
- **date_from** (任意): 開始日
- **date_to** (任意): 終了日
- **limit** (任意): 取得件数 (デフォルト50)
- **出力**: urgency_distribution (即時/高/中/低), priority_queue (スコア順), immediate_action_required (即時対応必要リスト)

### analyze_transfer_patterns
転職パターン分析。転職理由・動機の傾向を集計。
- **channel** (任意): 流入経路フィルタ
- **group_by** (必須): 集計軸 = "reason" | "timing" | "vision"
  - `reason`: 転職理由別 (給与,キャリア,スキルアップ等)
  - `timing`: 希望時期別 (すぐ,3ヶ月,6ヶ月等)
  - `vision`: キャリアビジョン別
- **出力**: distribution (項目別件数+%), top_3, insights, marketing_suggestions

### generate_candidate_briefing
面談準備用ブリーフィング。Zoho基本情報+議事録構造化データを統合。
- **record_id** (必須): Zoho候補者のrecord_id
- **出力**: basic_info, transfer_profile, career_summary, conditions, competition_status, talking_points (面談ポイント)

---

## 回答方針
- リスクスコア・緊急度スコアを明示
- 優先対応すべき候補者を上位に表示
- 面談準備には必ずtaking_pointsを強調
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
