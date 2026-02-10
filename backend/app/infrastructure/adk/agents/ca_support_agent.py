"""
CA Support Agent (ADK version) - Unified Career Advisor Support.

Comprehensive agent combining:
- Zoho CRM tools (candidate search, channel analysis, funnel)
- Candidate Insight tools (competitor risk, urgency, patterns)
- Company DB tools (matching, requirements, appeal points)
- Meeting tools (transcripts, structured data)

Designed for Career Advisors to support their full workflow.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .base import SubAgentFactory
from app.infrastructure.adk.tools.zoho_crm_tools import ADK_ZOHO_CRM_TOOLS
from app.infrastructure.adk.tools.candidate_insight_tools import ADK_CANDIDATE_INSIGHT_TOOLS
from app.infrastructure.adk.tools.company_db_tools import ADK_COMPANY_DB_TOOLS
from app.infrastructure.adk.tools.meeting_tools import ADK_MEETING_TOOLS
from app.infrastructure.adk.tools.semantic_company_tools import ADK_SEMANTIC_COMPANY_TOOLS
from app.infrastructure.adk.tools.workspace_tools import ADK_GMAIL_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


CA_SUPPORT_INSTRUCTIONS = """
あなたはb&qのCA（キャリアアドバイザー）支援AIです。

## 現在の日時（日本時間）: {app:current_date}（{app:day_of_week}曜日） {app:current_time}

## 現在のユーザー（担当CA）
- CA氏名: {app:user_name}
- メール: {app:user_email}（Gmail検索の対象、Zoho PIC検索にも使用可能）
回答時はそのままの名前で「○○さん」と呼びかけること。
- 「自分の担当候補者」→ Zoho CRMの `Owner` or `PIC` フィールドで上記CA氏名を検索
- 「自分の面談」→ 議事録ツールで上記CA氏名を検索

## ミッション
候補者の転職成功を支援するため、Zoho CRM・議事録・企業DB・メールを統合的に分析・提案します。

---

## ツール概要（33個）

- **Zoho CRM系（12個）**: 全モジュール動的アクセス（メタデータ発見→COQL検索→専門分析の3層構造）
  - Tier 1: list_crm_modules, get_module_schema, get_module_layout
  - Tier 2: query_crm_records, aggregate_crm_data, get_record_detail, get_related_records
  - Tier 3: analyze_funnel_by_channel, trend_analysis_by_period, compare_channels, get_pic_performance, get_conversion_metrics
- **候補者インサイト（4個）**: analyze_competitor_risk, assess_candidate_urgency, analyze_transfer_patterns, generate_candidate_briefing
- **企業DB（7個）**: search_companies, get_company_detail, get_company_requirements, get_appeal_by_need, match_candidate_to_companies, get_pic_recommended_companies, get_company_definitions
- **セマンティック検索（2個）★優先**: find_companies_for_candidate, semantic_search_companies
- **議事録（4個）**: search_meetings, get_meeting_transcript, get_structured_data_for_candidate, get_candidate_full_profile
- **Gmail（4個）**: search_gmail, get_email_detail, get_email_thread, get_recent_emails

---

## 主要ワークフロー

### 企業提案（推奨）
get_candidate_full_profile → find_companies_for_candidate → get_appeal_by_need

### 面談準備
get_record_detail("jobSeeker", id) → get_structured_data_for_candidate → analyze_competitor_risk

### 情報補完（メール）
search_gmail("from:候補者名 newer_than:30d") → get_email_thread → CRM情報と突合

---

## 検索優先順位
1. **セマンティック検索**: find_companies_for_candidate / semantic_search_companies
2. **条件緩和**: limit増加、フィルタ除外
3. **厳密検索**: search_companies（フォールバック）

## ニーズタイプ: salary / growth / wlb / atmosphere / future

---

## ルール
- 即座にツール実行（許可を求めるな）
- データは必ずツールで取得（推測・捏造禁止）
- Zoho + 議事録 + 企業DB + メールを統合して提案
- 表形式で整理、アクション可能な提案を含める
- データの出所を添える（例: 「Zoho CRM ID:xxx」「議事録 2025/5/15」「企業DB セマンティック検索」「Gmail from:xxx 直近30日」等）
"""


class CASupportAgentFactory(SubAgentFactory):
    """
    Factory for ADK CA Support sub-agent.

    Unified agent combining:
    - Zoho CRM tools (10)
    - Candidate Insight tools (4)
    - Company DB tools (7)
    - Meeting tools (4)
    - Semantic Search tools (2)
    - Gmail tools (4)
    Total: 31 tools
    """

    @property
    def agent_name(self) -> str:
        return "CASupportAgent"

    @property
    def tool_name(self) -> str:
        return "call_ca_support_agent"

    @property
    def tool_description(self) -> str:
        return (
            "特定候補者のクロスドメイン分析（CRM+議事録+企業DB統合）。"
            "面談準備・企業提案・リスク分析を一括実行。"
            "集団分析や単一ドメインの質問には専門エージェントを使用。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return all combined tools."""
        tools = []

        # Add Zoho CRM tools
        tools.extend(ADK_ZOHO_CRM_TOOLS)
        logger.info(f"[CASupportAgent] Added {len(ADK_ZOHO_CRM_TOOLS)} Zoho CRM tools")

        # Add Candidate Insight tools
        tools.extend(ADK_CANDIDATE_INSIGHT_TOOLS)
        logger.info(f"[CASupportAgent] Added {len(ADK_CANDIDATE_INSIGHT_TOOLS)} Candidate Insight tools")

        # Add Company DB tools (only if spreadsheet configured)
        if self._settings.company_db_spreadsheet_id:
            tools.extend(ADK_COMPANY_DB_TOOLS)
            logger.info(f"[CASupportAgent] Added {len(ADK_COMPANY_DB_TOOLS)} Company DB tools")
        else:
            logger.warning("[CASupportAgent] Company DB tools disabled (COMPANY_DB_SPREADSHEET_ID not set)")

        # Add Meeting tools
        tools.extend(ADK_MEETING_TOOLS)
        logger.info(f"[CASupportAgent] Added {len(ADK_MEETING_TOOLS)} Meeting tools")

        # Add Semantic Search tools (always available if company_chunks table exists)
        tools.extend(ADK_SEMANTIC_COMPANY_TOOLS)
        logger.info(f"[CASupportAgent] Added {len(ADK_SEMANTIC_COMPANY_TOOLS)} Semantic Search tools")

        # Add Gmail tools (per-user access via domain-wide delegation)
        tools.extend(ADK_GMAIL_TOOLS)
        logger.info(f"[CASupportAgent] Added {len(ADK_GMAIL_TOOLS)} Gmail tools")

        logger.info(f"[CASupportAgent] Total tools: {len(tools)}")
        return tools

    def _build_instructions(self) -> str:
        return CA_SUPPORT_INSTRUCTIONS

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """Build ADK agent with all combined tools."""
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
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=self._settings.adk_max_output_tokens,
            ),
        )
