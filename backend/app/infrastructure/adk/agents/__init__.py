"""
ADK-based Marketing AI Agents.

This module provides Google ADK-native implementations of the marketing agents,
replacing the OpenAI Agents SDK implementation.

Usage:
    from app.infrastructure.adk.agents import OrchestratorAgentFactory

    factory = OrchestratorAgentFactory(settings)
    agent = factory.build_agent()
"""

from .base import SubAgentFactory
from .orchestrator import OrchestratorAgentFactory
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

__all__ = [
    "SubAgentFactory",
    "OrchestratorAgentFactory",
    "AnalyticsAgentFactory",
    "AdPlatformAgentFactory",
    "SEOAgentFactory",
    "WordPressAgentFactory",
    "ZohoCRMAgentFactory",
    "CandidateInsightAgentFactory",
    "CompanyDatabaseAgentFactory",
    "CASupportAgentFactory",
    "GoogleSearchAgentFactory",
    "CodeExecutionAgentFactory",
    "GoogleWorkspaceAgentFactory",
    "SlackAgentFactory",
]
