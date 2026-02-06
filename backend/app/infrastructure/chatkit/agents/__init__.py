"""
Sub-Agent as Tool Architecture for Marketing AI.

This module provides a multi-agent architecture where specialized sub-agents
are exposed as tools to an orchestrator agent. Each sub-agent focuses on
a specific domain (analytics, ads, SEO, etc.) and includes native tools
(Web Search, Code Interpreter) for enhanced capabilities.

Architecture:
    Orchestrator (GPT-5.2)
    ├── AnalyticsAgent (GA4 + GSC)
    ├── AdPlatformAgent (Meta Ads)
    ├── SEOAgent (Ahrefs)
    ├── WordPressAgent (WP hitocareer + achieve)
    ├── ZohoCRMAgent
    └── CandidateInsightAgent

Usage:
    from app.infrastructure.chatkit.agents import OrchestratorAgentFactory

    factory = OrchestratorAgentFactory(settings)
    agent = factory.build_agent(asset=asset, mcp_servers=mcp_servers)
"""

from .orchestrator import OrchestratorAgentFactory
from .base import SubAgentFactory
from .analytics_agent import AnalyticsAgentFactory
from .ad_platform_agent import AdPlatformAgentFactory
from .seo_agent import SEOAgentFactory
from .wordpress_agent import WordPressAgentFactory
from .zoho_crm_agent import ZohoCRMAgentFactory
from .candidate_insight_agent import CandidateInsightAgentFactory

__all__ = [
    "OrchestratorAgentFactory",
    "SubAgentFactory",
    "AnalyticsAgentFactory",
    "AdPlatformAgentFactory",
    "SEOAgentFactory",
    "WordPressAgentFactory",
    "ZohoCRMAgentFactory",
    "CandidateInsightAgentFactory",
]
