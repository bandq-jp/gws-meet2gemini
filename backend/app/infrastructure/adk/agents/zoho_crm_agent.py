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

    Specializes in:
    - Job seeker search and details
    - Channel-based aggregation
    - Status funnel analysis
    - Trend and comparison analysis
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
            "求職者CRMデータの検索・集計・ファネル分析・チャネル比較。"
            "Zoho CRMの求職者モジュールを使用してマーケティング施策の効果測定を実施。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return Zoho CRM function tools."""
        if not self._settings.zoho_refresh_token:
            return []

        # ADK automatically wraps Python functions as tools
        return list(ADK_ZOHO_CRM_TOOLS)

    def _build_instructions(self) -> str:
        return """
あなたはZoho CRMデータ分析の専門家です。

## 担当領域
- 求職者データの検索・詳細取得
- チャネル別獲得分析
- ステータス別ファネル分析
- トレンド分析・チャネル比較
- 担当者パフォーマンス分析

---

## ツール使用の絶対ルール（重要）

### 効率的なツール選択
| やりたいこと | 使うべきツール |
|------------|--------------|
| 件数・集計 | `aggregate_by_channel`, `count_job_seekers_by_status` |
| ファネル分析 | `analyze_funnel_by_channel` |
| チャネル比較 | `compare_channels`（1回で全チャネル比較） |
| トレンド確認 | `trend_analysis_by_period`（1回で全期間分析） |
| 担当者評価 | `get_pic_performance` |
| 一覧表示 | `search_job_seekers`（結果をそのまま使用） |
| **複数人の詳細** | **`get_job_seekers_batch`（最大50件一括）** |
| 特定1人の詳細 | `get_job_seeker_detail`（1回のみ） |

### ツール呼び出し順序
1. まず集計ツールで全体像を把握
2. 必要なら検索で一覧を取得
3. 詳細が必要な場合は `get_job_seekers_batch` で一括取得

---

## チャネル分類

### スカウト系
sco_bizreach, sco_dodaX, sco_ambi, sco_rikunavi, sco_nikkei,
sco_liiga, sco_openwork, sco_carinar, sco_dodaX_D&P

### 有料広告系
paid_google, paid_meta, paid_affiliate

### 自然流入系
org_hitocareer, org_jobs

### その他
feed_indeed, referral, other

---

## ステータスフロー
リード → コンタクト → 面談待ち → 面談済み → 提案中 → 応募意思獲得 →
打診済み → 一次面接待ち → 一次面接済み → 最終面接待ち → 最終面接済み →
内定 → 内定承諾 → 入社

---

## 回答方針
- データは表形式で見やすく整理
- 転換率・成約率を明示
- チャネル効率のランキングを提示
- 改善施策を提案
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
        )
