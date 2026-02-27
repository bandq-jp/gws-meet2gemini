"""
Zoho CRM Agent (ADK version) - CRM data analysis.

Handles job seeker data search, aggregation, and funnel analysis.
Uses function tools from the existing implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .base import SubAgentFactory
# Import ADK-compatible Zoho CRM tools
from app.infrastructure.adk.tools.zoho_crm_tools import ADK_ZOHO_CRM_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings


class ZohoCRMAgentFactory(SubAgentFactory):
    """
    Factory for ADK Zoho CRM sub-agent.

    3-tier architecture:
    - Tier 1: Metadata discovery (modules, schemas, layouts)
    - Tier 2: Universal queries (any module, any field, COQL)
    - Tier 3: Specialized jobSeeker analysis (funnel, trends, comparison)
    """

    @property
    def agent_name(self) -> str:
        return "ZohoCRMAgent"

    @property
    def tool_name(self) -> str:
        return "call_zoho_crm_agent"

    @property
    def tool_description(self) -> str:
        return (
            "Zoho CRM全モジュールのデータ検索・集計・分析。"
            "求職者(jobSeeker)、求人(JOB)、企業(HRBP)、面接(interview_hc)等あらゆるモジュールに動的アクセス。"
            "ファネル分析・チャネル比較・トレンド分析も可能。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return Zoho CRM function tools."""
        if not self._settings.zoho_refresh_token:
            return []

        return list(ADK_ZOHO_CRM_TOOLS)

    def _build_instructions(self) -> str:
        return """
あなたはZoho CRMデータ分析の専門家です。全CRMモジュールに動的にアクセスできます。

## 現在の日時（日本時間）: {app:current_date}（{app:day_of_week}曜日） {app:current_time}
COQL WHERE句の日付条件は今日から正確に計算すること。

## 3層ツール体系
- **Tier 1（メタデータ）**: list_crm_modules → get_module_schema → get_module_layout
- **Tier 2（汎用クエリ）**: query_crm_records, aggregate_crm_data, get_record_detail, get_related_records
- **Tier 3（jobSeeker専門）**: analyze_funnel_by_channel, trend_analysis_by_period, compare_channels, get_pic_performance, get_conversion_metrics

## 手順
1. 初めてのモジュール → get_module_schemaでフィールドAPI名を確認
2. query_crm_records / aggregate_crm_data でデータ取得
3. 詳細が必要 → get_record_detail

## jobSeekerの主要フィールド
- チャネル: field14 / ステータス: customer_status / 登録日: field18

## COQL Tips
- WHERE: =, !=, >, <, like '%値%', in ('a','b'), is null
- JOIN: Owner.name, field64.Account_Name（ドット記法）
- GROUP BY最大4, LIMIT最大2000

## チャネル別分析ルール
- **メディア流入（ひとキャリ）分析**: `field14 = 'org_hitocareer'` でフィルタ必須
- **有料広告分析**: `field14 like 'paid_%'` でフィルタ
- **スカウト分析**: `field14 like 'sco_%'` でフィルタ
- **全チャネル横断の全体分析**: フィルタ不要

## ステータスの取り扱い（厳守）
- candidateのステータス（customer_status）は**CRMの実データをそのまま使用**し、推測や変更は禁止
- ステータス値: "1. リード" ～ "14. 入社" の番号付き文字列
- 「内定」= "12. 内定" のみ、「入社」= "14. 入社" のみ。曖昧なマッチは禁止
- レポート時は使用したCOQLクエリまたはツール名と対象期間を明記

## 回答方針
- 表形式で整理、転換率・成約率を明示、改善施策を提案
- データの出所を添える（例: 「Zoho CRM jobSeekerモジュール」「COQL: SELECT ... WHERE ...」「対象期間: 2025/4〜6」等）
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
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=self._settings.adk_max_output_tokens,
            ),
        )
