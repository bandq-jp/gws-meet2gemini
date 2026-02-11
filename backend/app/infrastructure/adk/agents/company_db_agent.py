"""
Company Database Agent (ADK version) - Company information analysis.

Handles company search, requirements matching, and appeal point retrieval.
Uses Google Sheets as the data source for company information.

**Semantic Search (pgvector) is PRIORITIZED over strict search.**
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .base import SubAgentFactory
from app.infrastructure.adk.tools.company_db_tools import ADK_COMPANY_DB_TOOLS
from app.infrastructure.adk.tools.semantic_company_tools import ADK_SEMANTIC_COMPANY_TOOLS
from app.infrastructure.adk.tools.workspace_tools import ADK_GMAIL_TOOLS
from app.infrastructure.adk.tools.slack_tools import ADK_SLACK_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class CompanyDatabaseAgentFactory(SubAgentFactory):
    """
    Factory for ADK Company Database sub-agent.

    Specializes in:
    - **Semantic search (PRIORITY)** - pgvector-based vector similarity
    - Company search by requirements (fallback)
    - Candidate-company matching
    - Need-based appeal point retrieval
    - PIC (advisor) recommended companies
    - Gmail search for company-related emails
    - Slack search for company-related messages

    Total: 20 tools (2 semantic + 7 strict + 4 Gmail + 7 Slack)
    """

    @property
    def agent_name(self) -> str:
        return "CompanyDatabaseAgent"

    @property
    def tool_name(self) -> str:
        return "call_company_db_agent"

    @property
    def tool_description(self) -> str:
        return (
            "企業情報のセマンティック検索・マッチング・訴求ポイント取得。"
            "ベクトル検索を優先し、候補者の転職理由から最適企業を高速推薦。"
            "Gmail・Slackから企業のFee・条件・内部議論も検索可能。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return company database function tools (semantic + strict)."""
        tools: List[Any] = []

        # 1. Semantic search tools (PRIORITY) - always available
        tools.extend(ADK_SEMANTIC_COMPANY_TOOLS)
        logger.info(f"[CompanyDatabaseAgent] Added {len(ADK_SEMANTIC_COMPANY_TOOLS)} semantic search tools (PRIORITY)")

        # 2. Strict search tools (fallback) - requires spreadsheet config
        if self._settings.company_db_spreadsheet_id:
            tools.extend(ADK_COMPANY_DB_TOOLS)
            logger.info(f"[CompanyDatabaseAgent] Added {len(ADK_COMPANY_DB_TOOLS)} strict search tools (fallback)")
        else:
            logger.warning("[CompanyDatabaseAgent] Strict search tools disabled (COMPANY_DB_SPREADSHEET_ID not set)")

        # 3. Gmail tools - search company-related emails
        tools.extend(ADK_GMAIL_TOOLS)
        logger.info(f"[CompanyDatabaseAgent] Added {len(ADK_GMAIL_TOOLS)} Gmail tools")

        # 4. Slack tools - search company-related Slack messages
        tools.extend(ADK_SLACK_TOOLS)
        logger.info(f"[CompanyDatabaseAgent] Added {len(ADK_SLACK_TOOLS)} Slack tools")

        logger.info(f"[CompanyDatabaseAgent] Total tools: {len(tools)}")
        return tools

    def _build_instructions(self) -> str:
        return """
あなたは企業情報データベースの専門家です。

## ツール選択の優先順位（厳守）
1. **セマンティック検索を最優先**: find_companies_for_candidate（候補者マッチング）、semantic_search_companies（自然言語検索）
2. **詳細確認のみ厳密検索**: get_company_detail, get_company_requirements, get_appeal_by_need, search_companies
3. **DB外の情報補完**: search_gmail / search_company_in_slack → DB情報と突合

## 代表ワークフロー
- **候補者マッチング**: find_companies_for_candidate → get_company_detail（必要時）
- **自然言語検索**: semantic_search_companies → get_appeal_by_need
- **統合分析**: find_companies_for_candidate + search_gmail + search_company_in_slack → 3ソース統合

## ニーズタイプ: salary / growth / wlb / atmosphere / future

## ルール
- 即座にツール実行（許可を求めるな）
- データは必ずツールで取得（推測・捏造禁止）
- 回答にはデータ出所を添える（例: 「セマンティック検索 類似度0.82」「Gmail from:xxx 直近90日」「Slack #営業 直近30日」）
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
