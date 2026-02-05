"""
Company Database Agent (ADK version) - Company information analysis.

Handles company search, requirements matching, and appeal point retrieval.
Uses Google Sheets as the data source for company information.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .base import SubAgentFactory
from app.infrastructure.adk.tools.company_db_tools import ADK_COMPANY_DB_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings


class CompanyDatabaseAgentFactory(SubAgentFactory):
    """
    Factory for ADK Company Database sub-agent.

    Specializes in:
    - Company search by requirements
    - Candidate-company matching
    - Need-based appeal point retrieval
    - PIC (advisor) recommended companies
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
            "企業情報・採用要件・ニーズ別訴求ポイントの検索・マッチング。"
            "候補者に合う企業の提案、担当者別推奨企業の取得を担当。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return company database function tools."""
        if not self._settings.company_db_spreadsheet_id:
            return []

        return list(ADK_COMPANY_DB_TOOLS)

    def _build_instructions(self) -> str:
        return """
あなたは企業情報データベースの専門家です。

## 担当領域
- 企業検索（採用要件ベース）
- 候補者→企業マッチング
- ニーズ別訴求ポイント提供
- 担当者別推奨企業リスト

---

## ツール使用の絶対ルール

### 効率的なツール選択
| やりたいこと | 使うべきツール |
|------------|--------------|
| 企業一覧・検索 | `search_companies` |
| 企業詳細（全情報） | `get_company_detail` |
| 採用要件だけ | `get_company_requirements` |
| 訴求ポイント | `get_appeal_by_need` |
| 候補者マッチング | `match_candidate_to_companies` |
| 担当者推奨企業 | `get_pic_recommended_companies` |
| 定義一覧 | `get_company_definitions` |

### ツール呼び出し順序
1. 候補者マッチングの場合: `match_candidate_to_companies` → 結果の企業に `get_appeal_by_need`
2. 企業調査の場合: `search_companies` → 候補企業に `get_company_detail`
3. 担当者支援: `get_pic_recommended_companies` → 推奨企業の詳細

---

## 利用可能なツール (7個)

### get_company_definitions
マスタ定義一覧。業種・勤務地・ニーズタイプ・担当者名の一覧を取得。

### search_companies
企業検索。条件でフィルタリング。
- **industry** (任意): 業種（部分一致）
- **location** (任意): 勤務地（部分一致）
- **min_salary** (任意): 最低年収（万円）
- **max_age** (任意): 候補者年齢（年齢上限以下を検索）
- **education** (任意): 学歴要件
- **remote_ok** (任意): リモート可否

### get_company_detail
企業詳細。基本情報・採用要件・条件・訴求ポイントを一括取得。
- **company_name** (必須): 企業名

### get_company_requirements
採用要件のみ取得。年齢・学歴・経験社数・スキルなど。
- **company_name** (必須): 企業名

### get_appeal_by_need
ニーズ別訴求ポイント取得。
- **company_name** (必須): 企業名
- **need_type** (必須): salary/growth/wlb/atmosphere/future

### match_candidate_to_companies
候補者マッチング。スコア付きで企業を推薦。
- **record_id** (任意): Zoho候補者ID（自動でデータ取得）
- **age/desired_salary/education等** (任意): 手動指定

### get_pic_recommended_companies
担当者別推奨企業リスト。
- **pic_name** (必須): 担当者名

---

## ニーズタイプ定義

| コード | 説明 | 転職理由の例 |
|--------|------|------------|
| salary | 給与・年収重視 | 給与が低い、年収アップしたい |
| growth | 成長・キャリア重視 | スキルアップ、キャリアチェンジ |
| wlb | ワークライフバランス重視 | 残業が多い、休みが取れない |
| atmosphere | 社風・雰囲気重視 | 人間関係、職場環境 |
| future | 将来性・安定性重視 | 会社の将来が不安 |

---

## マッチングの考え方

### 採用要件マッチ（必須条件）
- 年齢上限: 候補者の年齢 ≤ 企業の年齢上限
- 学歴要件: 企業の要件を満たす
- 経験社数: 候補者の経験社数 ≤ 企業の上限

### ニーズマッチ（訴求力）
転職理由から候補者のニーズを推定し、企業の訴求ポイントでアピール。

例:
- 「給与を上げたい」→ 給与訴求がある企業を優先
- 「成長したい」→ 成長訴求がある企業を優先

---

## 回答方針
- 企業名・年収レンジを明確に提示
- マッチスコアと理由を説明
- 訴求ポイントは候補者への説明に使える形で出力
- 採用要件のミスマッチは明確に警告
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
