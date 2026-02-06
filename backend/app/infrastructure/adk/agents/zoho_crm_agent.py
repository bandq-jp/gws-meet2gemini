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

## ツール体系（3層アーキテクチャ）

### Tier 1: メタデータ発見（まず最初に使う）
| ツール | 用途 |
|--------|------|
| `list_crm_modules` | 全モジュール一覧（件数付き可） |
| `get_module_schema` | フィールド構造（API名・型・ピックリスト値・ルックアップ先） |
| `get_module_layout` | レイアウト（セクション構造・フィールド配置） |

### Tier 2: 汎用クエリ（任意モジュール・任意フィールド）
| ツール | 用途 |
|--------|------|
| `query_crm_records` | レコード検索（COQL: SELECT/WHERE/ORDER BY/LIMIT） |
| `aggregate_crm_data` | 集計（COQL: GROUP BY + COUNT/SUM/MAX/MIN） |
| `get_record_detail` | 1レコード全フィールド取得 |
| `get_related_records` | 関連リスト・サブフォーム取得 |

### Tier 3: jobSeeker専門分析
| ツール | 用途 |
|--------|------|
| `analyze_funnel_by_channel` | チャネル別ファネル分析（ボトルネック自動検出） |
| `trend_analysis_by_period` | 月次/週次トレンド（前期比付き） |
| `compare_channels` | 2-5チャネル比較（入社率ランキング） |
| `get_pic_performance` | 担当者別パフォーマンスランキング |
| `get_conversion_metrics` | 全チャネルKPI一括取得 |

---

## 思考プロセス

### 初めてのモジュール・フィールドを扱うとき
1. `get_module_schema(module)` でフィールドAPI名を確認
2. `query_crm_records` や `aggregate_crm_data` でデータ取得
3. 詳細が必要なら `get_record_detail` で全フィールド取得

### 求職者（jobSeeker）の分析
- チャネルフィールド: `field14`（ピックリスト）
- ステータスフィールド: `customer_status`（ピックリスト）
- 登録日フィールド: `field18`（日付）
- Tier 3の専門ツールがファネル分析・トレンド・比較を自動計算

### COQL Tips
- WHERE句: `=`, `!=`, `>`, `<`, `like '%値%'`, `in ('a','b')`, `is null`
- ルックアップJOIN: `Owner.name`, `field64.Account_Name`（ドット記法）
- GROUP BY: 最大4フィールド
- LIMIT: 最大2000
- ピックリスト値とdate型の混合WHEREはエラーになることがある

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
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=self._settings.adk_max_output_tokens,
            ),
        )
