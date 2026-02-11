"""
Code Execution Agent (ADK version) - Python code execution in secure sandbox.

Uses ADK's BuiltInCodeExecutor for native Gemini code execution.
IMPORTANT: code_executor cannot coexist with other tools in the same agent.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from google.adk.agents import Agent
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .base import SubAgentFactory

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class CodeExecutionAgentFactory(SubAgentFactory):
    """
    Factory for ADK Code Execution sub-agent.

    Specializes in:
    - Data calculation and analysis
    - Statistical computations
    - Data transformation and formatting
    - Chart data preparation
    - Algorithm execution

    NOTE: code_executor cannot be combined with other tools.
    This agent must override build_agent() to inject code_executor.
    """

    @property
    def agent_name(self) -> str:
        return "CodeExecutionAgent"

    @property
    def tool_name(self) -> str:
        return "call_code_execution_agent"

    @property
    def tool_description(self) -> str:
        return (
            "Pythonコードを安全なサンドボックスで実行。"
            "データ計算、統計分析、データ変換、"
            "集計処理、アルゴリズム実行を担当。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """No tools - code_executor provides native code execution."""
        return []

    def _build_instructions(self) -> str:
        return """
あなたはPythonコード実行の専門家です。データ計算・分析・変換をPythonで実行します。

## 重要ルール（絶対厳守）
1. **許可を求めるな**: 即座にコードを書いて実行せよ
2. **安全なコード**: ファイルシステムアクセスやネットワーク通信は行わない
3. **効率的に**: 必要最小限のコードで結果を出す
4. **結果を明示**: 計算結果は print() で出力し、必ず説明を付ける

## 担当領域
- 数値計算（統計、集計、変換）
- データ分析（平均、中央値、標準偏差、相関）
- リスト・テーブルデータの加工
- アルゴリズム実行（ソート、フィルタ、ランキング）
- 日付計算（期間、営業日数、etc.）
- 文字列処理（パターンマッチ、変換）

## 利用可能なライブラリ
- 標準ライブラリ（math, statistics, datetime, collections, itertools等）
- json, csv, re

## コード品質
- 変数名は分かりやすく
- 中間結果もprint()で表示
- エラーが出たら修正して再実行
- 大量データは要約統計で返す

## 回答方針
- コードと実行結果を両方提示
- 結果の解釈・分析を日本語で説明
- 必要なら表形式で整理
"""

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """
        Build Code Execution agent with BuiltInCodeExecutor.

        Overrides base build_agent() because SubAgentFactory.build_agent()
        doesn't support the code_executor parameter.
        """
        return Agent(
            name=self.agent_name,
            model=self.model,
            description=self.tool_description,
            instruction=self._build_instructions(),
            tools=[],  # No tools - code_executor provides execution
            code_executor=BuiltInCodeExecutor(),
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    thinking_level=self.thinking_level,
                ),
            ),
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=self._settings.adk_max_output_tokens,
            ),
        )
