"""
Ask User Clarification Tool - LongRunningFunctionTool for user interaction.

When the orchestrator needs clarification or confirmation from the user,
it calls this tool to present structured choices. The tool returns None
(long-running pattern), and the frontend renders interactive choice buttons.
The user's selection is sent as a new message in the next turn.
"""
from __future__ import annotations

from typing import List, Optional

from google.adk.tools import LongRunningFunctionTool
from google.adk.tools.tool_context import ToolContext


def ask_user_clarification(
    questions: list[dict],
    tool_context: ToolContext = None,
) -> None:
    """ユーザーに確認事項を提示し、選択を待つ。ユーザーが選択肢を選ぶまで処理を中断する。

    このツールはユーザーの意図が曖昧な場合や、複数の分析方向がある場合に使用する。
    ユーザーにはボタン形式の選択UIが表示される。

    Args:
        questions: 質問のリスト。各質問は以下の形式:
            [
                {
                    "question": "どの分析を実行しますか？",
                    "header": "分析方法",
                    "options": [
                        {"label": "候補者リスク分析", "description": "転職リスク・緊急度・競合状況を評価"},
                        {"label": "企業マッチング", "description": "希望条件に合う企業を自動検索"}
                    ],
                    "multiSelect": false
                }
            ]
            注意: 「その他」「自由入力」等の選択肢はシステムが自動追加するため含めないこと。
        tool_context: ADKが自動注入するToolContext（パラメータ名は固定）

    Returns:
        None（ユーザー応答を待つ）
    """
    if tool_context:
        tool_context.actions.skip_summarization = True
    return None


# Wrap as LongRunningFunctionTool to prevent re-invocation
ask_user_tool = LongRunningFunctionTool(func=ask_user_clarification)

# Export list for easy registration
ADK_ASK_USER_TOOLS = [ask_user_tool]
