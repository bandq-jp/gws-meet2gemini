"""
Zoho CRM Agent - CRM data analysis.

Handles job seeker data search, aggregation, and funnel analysis.
Tools: 9 function tools + native tools
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from agents import Agent, ModelSettings
from openai.types.shared.reasoning import Reasoning

from .base import SubAgentFactory
from ..zoho_crm_tools import ZOHO_CRM_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings


class ZohoCRMAgentFactory(SubAgentFactory):
    """
    Factory for Zoho CRM sub-agent.

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
        # Check if Zoho is enabled
        if not self._settings.zoho_refresh_token:
            return []

        return list(ZOHO_CRM_TOOLS)

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
| **複数人の詳細** | **`get_job_seekers_batch`（最大50件一括、COQL最適化）** |
| 特定1人の詳細 | `get_job_seeker_detail`（1回のみ） |

### ツール呼び出し順序
1. まず集計ツールで全体像を把握
2. 必要なら検索で一覧を取得（結果をそのまま使用）
3. 詳細が必要な場合は **`get_job_seekers_batch`** で一括取得

---

## 利用可能なツール (10個)

### 集計ツール（最優先で使用）
- **aggregate_by_channel**: チャネル別件数集計（COQL最適化）
- **count_job_seekers_by_status**: ステータス別件数集計（COQL最適化）

### 分析ツール（1回のAPI呼び出しで完結）
- **analyze_funnel_by_channel**: ファネル分析 + ボトルネック特定 + 改善提案
- **trend_analysis_by_period**: 月次/週次トレンド + 前期比（メモリ内期間分割）
- **compare_channels**: 複数チャネル比較 + ランキング（メモリ内チャネル分割）
- **get_pic_performance**: 担当者別成約率ランキング

### 検索・詳細
- **search_job_seekers**: 一覧取得（基本情報含む）
- **get_job_seekers_batch**: **複数件の詳細を一括取得（最大50件、COQL IN句）**
- **get_job_seeker_detail**: 特定1件の詳細
- **get_channel_definitions**: チャネル・ステータスの定義一覧

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
        """Build agent (no MCP servers, only function tools)."""
        tools = self._get_native_tools() + self._get_domain_tools(mcp_servers, asset)

        return Agent(
            name=self.agent_name,
            instructions=self._build_instructions(),
            tools=tools,
            model=self.model,
            model_settings=ModelSettings(
                store=True,
                reasoning=Reasoning(
                    effort=self.reasoning_effort,
                    summary="detailed",
                ),
                verbosity="medium",
            ),
            tool_use_behavior="run_llm_again",
        )
