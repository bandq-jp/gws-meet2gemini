"""
Google Search Agent (ADK version) - Web search grounding.

Uses ADK's built-in google_search tool for real-time web information retrieval.
IMPORTANT: google_search cannot coexist with other tools in the same agent.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search
from google.genai import types

from .base import SubAgentFactory

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class GoogleSearchAgentFactory(SubAgentFactory):
    """
    Factory for ADK Google Search sub-agent.

    Specializes in:
    - Real-time web search for latest information
    - News and trend research
    - Fact-checking and grounding responses with sources
    - Industry/market research

    NOTE: google_search tool CANNOT be combined with other tools.
    This agent must be a dedicated search-only agent.
    """

    @property
    def agent_name(self) -> str:
        return "GoogleSearchAgent"

    @property
    def tool_name(self) -> str:
        return "call_google_search_agent"

    @property
    def tool_description(self) -> str:
        return (
            "Google検索を使用してリアルタイムのWeb情報を取得。"
            "最新ニュース、トレンド、業界動向、事実確認、"
            "競合情報の調査を担当。"
        )

    @property
    def thinking_level(self) -> str:
        return "low"

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return google_search tool (must be sole tool)."""
        return [google_search]

    def _build_instructions(self) -> str:
        return """
あなたはGoogle検索を使ったリアルタイム情報収集の専門家です。

## 現在の日時（日本時間）: {app:current_date}（{app:day_of_week}曜日） {app:current_time}

## 重要ルール（絶対厳守）
1. **許可を求めるな**: 即座に検索を実行せよ
2. **複数角度で検索**: 1つの質問に対して必要なら2-3回検索し、情報を総合せよ
3. **ソースURLを明記**: 検索結果には必ず出典URLを含めよ
4. **日本語優先**: 日本の情報は日本語クエリ、グローバル情報は英語クエリを使い分けよ

## 担当領域
- 最新ニュース・トレンド調査
- 業界動向・市場調査
- 競合企業情報の収集
- 技術・ツール・サービスの最新情報
- 事実確認・ファクトチェック
- 法規制・制度変更の確認

## 検索クエリ最適化
- 日本語の質問 → 日本語の検索クエリに変換
- 曖昧な質問 → 具体的なキーワードに分解
- 複合的な質問 → 複数の検索クエリに分割して実行
- 最新情報が必要な場合 → 年号やキーワード「2025」「最新」を付与

## 回答方針
- 検索結果を整理・要約して提示
- 出典URL（ソース）を必ず明記
- 複数ソースの情報を統合し、信頼性を示す
- 情報の鮮度（いつの情報か）を明示
"""

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """Build Google Search agent with dedicated search tool."""
        return Agent(
            name=self.agent_name,
            model=self.model,
            description=self.tool_description,
            instruction=self._build_instructions(),
            tools=self._get_domain_tools(mcp_servers, asset),
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    thinking_level=self.thinking_level,
                ),
            ),
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=self._settings.adk_max_output_tokens,
            ),
        )
