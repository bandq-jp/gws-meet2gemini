"""
Marketing AI Agent - ADK Web entry point.

This file exposes `root_agent` for ADK Web dev UI discovery.
"""

from __future__ import annotations

import os
import sys

# Add backend to path for imports
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools import AgentTool
from google.genai import types

# Import sub-agent factories
from app.infrastructure.adk.agents.analytics_agent import AnalyticsAgentFactory
from app.infrastructure.adk.agents.seo_agent import SEOAgentFactory
from app.infrastructure.adk.agents.zoho_crm_agent import ZohoCRMAgentFactory
from app.infrastructure.adk.agents.candidate_insight_agent import CandidateInsightAgentFactory
from app.infrastructure.adk.tools.chart_tools import ADK_CHART_TOOLS
from app.infrastructure.config.settings import get_settings

# Get settings
settings = get_settings()

# Orchestrator instructions (simplified for dev testing)
INSTRUCTIONS = """
あなたはb&qマーケティングAIオーケストレーターです。

## 重要ルール
1. 許可を求めず即座に実行
2. データは必ずツールで取得
3. 独立したサブエージェントは並列呼び出し

## サブエージェント
- call_analytics_agent: GA4/GSC データ分析
- call_seo_agent: Ahrefs SEO分析
- call_zoho_crm_agent: Zoho CRM 求職者データ
- call_candidate_insight_agent: 候補者インサイト

挨拶や一般的な質問にはサブエージェント不要で直接回答。
"""

# Build sub-agents
def _build_sub_agents():
    """Build sub-agent tools."""
    sub_agent_tools = []

    # Analytics Agent (GA4 + GSC)
    # Note: AgentTool uses agent.name and agent.description automatically
    analytics_factory = AnalyticsAgentFactory(settings)
    analytics_agent = analytics_factory.build_agent()
    sub_agent_tools.append(AgentTool(agent=analytics_agent))

    # SEO Agent (Ahrefs)
    seo_factory = SEOAgentFactory(settings)
    seo_agent = seo_factory.build_agent()
    sub_agent_tools.append(AgentTool(agent=seo_agent))

    # Zoho CRM Agent
    zoho_factory = ZohoCRMAgentFactory(settings)
    zoho_agent = zoho_factory.build_agent()
    sub_agent_tools.append(AgentTool(agent=zoho_agent))

    # Candidate Insight Agent
    candidate_factory = CandidateInsightAgentFactory(settings)
    candidate_agent = candidate_factory.build_agent()
    sub_agent_tools.append(AgentTool(agent=candidate_agent))

    return sub_agent_tools

# Build orchestrator
sub_agents = _build_sub_agents()

root_agent = Agent(
    name="MarketingOrchestrator",
    model=settings.adk_orchestrator_model,
    description="b&qマーケティングAIオーケストレーター",
    instruction=INSTRUCTIONS,
    tools=sub_agents + list(ADK_CHART_TOOLS),
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            thinking_level="medium",
        ),
    ),
)
