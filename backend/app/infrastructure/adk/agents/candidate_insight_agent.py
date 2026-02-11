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

    @property
    def thinking_level(self) -> str:
        return "high"

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

## 現在の日時（日本時間）: {app:current_date}（{app:day_of_week}曜日） {app:current_time}

## 重要ルール（絶対厳守）
1. **許可を求めるな**: 即座にツールを実行せよ
2. **推測するな**: データが必要なら必ずツールを呼び出す
3. **効率的に**: 1-2回のツール呼び出しで必要なデータを取得

## 担当領域
- 競合エージェントリスク分析
- 緊急度評価（即時対応必要候補者の特定）
- 転職理由・パターン分析
- 面談ブリーフィング生成

---

## 利用可能なツール (4個)

### analyze_competitor_risk
競合エージェント利用状況の分析。
- **channel** (任意): チャネル指定 (paid_meta, sco_bizreach等)
- **date_from/date_to** (任意): 期間 (YYYY-MM-DD)
- **limit** (任意): 分析対象最大件数 (default: 50)
- **戻り値**: high_risk_candidates（高リスク候補者リスト）, competitor_agents（競合頻度）, popular_companies（選考企業頻度）

### assess_candidate_urgency
候補者の緊急度を評価。転職希望時期・離職状況・他社オファーからスコアリング。
- **channel/status** (任意): フィルタ条件
- **date_from/date_to** (任意): 期間 (YYYY-MM-DD)
- **limit** (任意): 分析対象最大件数 (default: 50)
- **戻り値**: urgency_distribution（緊急度分布）, priority_queue（スコア順リスト）

### analyze_transfer_patterns
転職パターン分析。転職理由・希望時期・キャリアビジョンの傾向を可視化。
- **channel** (任意): チャネル指定
- **group_by** (必須): "reason"（転職理由）, "timing"（希望時期）, "vision"（キャリアビジョン）
- **戻り値**: distribution（パターン分布）, total_analyzed（分析件数）

### generate_candidate_briefing
面談ブリーフィング生成。Zoho基本情報+構造化データ統合。
- **record_id** (必須): ZohoレコードID
- **戻り値**: briefing（basic_info, transfer_profile, conditions, competition_status）

---

## ワークフロー例

### 高リスク候補者対応
```
1. assess_candidate_urgency() → 緊急対応が必要な候補者リスト
2. analyze_competitor_risk() → 他社オファー・競合状況
```

### 面談準備
```
generate_candidate_briefing(record_id="xxx") → 統合ブリーフィング
```

### トレンド分析
```
analyze_transfer_patterns(group_by="reason") → 転職理由の傾向
```

---

## 回答方針
- リスクレベルを 即時/高/中/低 で明示
- 優先順位付けを行い、上位から対応提案
- 具体的なアクション（電話/メール/面談設定）を提案
- データは表形式で整理
- 分析の根拠を添える（例: 「対象: 直近3ヶ月 paid_meta経由 50件分析」「Zoho ID:xxx ブリーフィング」等）
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
                    thinking_level=self.thinking_level,
                ),
            ),
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=self._settings.adk_max_output_tokens,
            ),
        )
