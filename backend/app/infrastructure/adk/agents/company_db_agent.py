"""
Company Database Agent (ADK version) - Company information analysis.

Handles company search, requirements matching, and appeal point retrieval.
Uses Google Sheets as the data source for company information.

**Semantic Search (pgvector) is PRIORITIZED over strict search.**
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .base import SubAgentFactory
from app.infrastructure.adk.tools.company_db_tools import ADK_COMPANY_DB_TOOLS
from app.infrastructure.adk.tools.semantic_company_tools import ADK_SEMANTIC_COMPANY_TOOLS
from app.infrastructure.adk.tools.workspace_tools import ADK_GMAIL_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class CompanyDatabaseAgentFactory(SubAgentFactory):
    """
    Factory for ADK Company Database sub-agent.

    Specializes in:
    - **Semantic search (PRIORITY)** - pgvector-based vector similarity
    - Company search by requirements (fallback)
    - Candidate-company matching
    - Need-based appeal point retrieval
    - PIC (advisor) recommended companies
    - Gmail search for company-related emails

    Total: 13 tools (2 semantic + 7 strict + 4 Gmail)
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
            "企業情報のセマンティック検索・マッチング・訴求ポイント取得。"
            "ベクトル検索を優先し、候補者の転職理由から最適企業を高速推薦。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return company database function tools (semantic + strict)."""
        tools: List[Any] = []

        # 1. Semantic search tools (PRIORITY) - always available
        tools.extend(ADK_SEMANTIC_COMPANY_TOOLS)
        logger.info(f"[CompanyDatabaseAgent] Added {len(ADK_SEMANTIC_COMPANY_TOOLS)} semantic search tools (PRIORITY)")

        # 2. Strict search tools (fallback) - requires spreadsheet config
        if self._settings.company_db_spreadsheet_id:
            tools.extend(ADK_COMPANY_DB_TOOLS)
            logger.info(f"[CompanyDatabaseAgent] Added {len(ADK_COMPANY_DB_TOOLS)} strict search tools (fallback)")
        else:
            logger.warning("[CompanyDatabaseAgent] Strict search tools disabled (COMPANY_DB_SPREADSHEET_ID not set)")

        # 3. Gmail tools - search company-related emails
        tools.extend(ADK_GMAIL_TOOLS)
        logger.info(f"[CompanyDatabaseAgent] Added {len(ADK_GMAIL_TOOLS)} Gmail tools")

        logger.info(f"[CompanyDatabaseAgent] Total tools: {len(tools)}")
        return tools

    def _build_instructions(self) -> str:
        return """
あなたは企業情報データベースの専門家です。

## 【最重要】ツール選択の優先順位

⚡ **セマンティック検索を常に最優先で使用せよ！** ⚡

### 優先度1: セマンティック検索（高速・推奨）
| やりたいこと | 使うべきツール |
|------------|--------------|
| 候補者マッチング | `find_companies_for_candidate` ★最優先 |
| 自然言語で企業検索 | `semantic_search_companies` ★高速 |

### 優先度2: 厳密検索（詳細確認・補助用）
| やりたいこと | 使うべきツール |
|------------|--------------|
| 特定企業の詳細 | `get_company_detail` |
| 採用要件のみ | `get_company_requirements` |
| 訴求ポイント | `get_appeal_by_need` |
| 条件フィルタ | `search_companies` |
| 担当者推奨 | `get_pic_recommended_companies` |
| 定義一覧 | `get_company_definitions` |

### 優先度3: メール検索（DB外の生情報補完）
| やりたいこと | 使うべきツール |
|------------|--------------|
| 企業関連のメール検索 | `search_gmail` |
| メール本文確認 | `get_email_detail` |
| やり取りの流れ追跡 | `get_email_thread` |
| 最新メール確認 | `get_recent_emails` |

---

## 利用可能なツール (13個)

### 【セマンティック検索】★優先使用

#### find_companies_for_candidate ⭐最優先
候補者の転職理由から最適企業を自動マッチング（ベクトル類似度）。
- **transfer_reasons** (必須): 転職理由・希望（自然言語）
  - 例: 「給与を上げたい、リモートワークしたい、成長できる環境」
- **age** (任意): 候補者年齢
- **desired_salary** (任意): 希望年収（万円）
- **desired_locations** (任意): 希望勤務地リスト
- **limit** (任意): 取得件数（default: 10）

**戻り値**: match_score付き企業リスト + appeal_points

#### semantic_search_companies ⭐高速
自然言語クエリで企業を検索（ベクトル類似度）。
- **query** (必須): 検索クエリ
  - 例: 「リモートワーク可能でワークライフバランス重視の企業」
- **chunk_types** (任意): 検索対象（overview/requirements/salary/growth/wlb/culture）
- **max_age** (任意): 候補者年齢
- **min_salary** (任意): 希望年収
- **locations** (任意): 希望勤務地リスト
- **limit** (任意): 取得件数（max 20）

---

### 【厳密検索】補助・詳細確認用

#### get_company_detail
企業詳細。基本情報・採用要件・条件・訴求ポイントを一括取得。
- **company_name** (必須): 企業名

#### get_company_requirements
採用要件のみ取得。年齢・学歴・経験社数・スキルなど。
- **company_name** (必須): 企業名

#### get_appeal_by_need
ニーズ別訴求ポイント取得。
- **company_name** (必須): 企業名
- **need_type** (必須): salary/growth/wlb/atmosphere/future

#### search_companies
企業検索（条件フィルタリング）。セマンティック検索で十分な場合は使用不要。
- **industry** (任意): 業種（部分一致）
- **location** (任意): 勤務地（部分一致）
- **min_salary** (任意): 最低年収（万円）
- **max_age** (任意): 候補者年齢
- **education** (任意): 学歴要件
- **remote_ok** (任意): リモート可否

#### match_candidate_to_companies
候補者マッチング（厳密スコアリング）。セマンティック検索後の補助に使用。
- **record_id** (任意): Zoho候補者ID
- **age/desired_salary/education等** (任意): 手動指定

#### get_pic_recommended_companies
担当者別推奨企業リスト。
- **pic_name** (必須): 担当者名

#### get_company_definitions
マスタ定義一覧（業種・勤務地・ニーズタイプ・担当者名）。

---

### 【Gmail検索】企業関連メールの発掘

メールには企業DBに載っていない生の情報（採用担当とのやり取り、選考フィードバック、条件交渉の経緯、非公開求人の案内等）が含まれる。
DB検索だけでは得られない企業のリアルな情報をメールから補完できる。

#### search_gmail
Gmailを検索。企業名・担当者名・求人キーワードで絞り込み。
- **query** (必須): Gmail検索クエリ（例: `subject:株式会社○○ newer_than:90d`）
- **max_results** (任意): 取得件数（デフォルト10、max 20）

#### get_email_detail
メール本文を取得（最大3000文字）。企業からの連絡内容を確認。
- **message_id** (必須): search_gmailの結果から取得

#### get_email_thread
スレッド全体を時系列で取得。企業とのやり取りの流れを追跡。
- **thread_id** (必須): search_gmailまたはget_email_detailから取得

#### get_recent_emails
直近N時間のメール一覧。最新の企業連絡を確認。
- **hours** (任意): 遡る時間数（デフォルト24h）
- **label** (任意): ラベルフィルタ
- **max_results** (任意): 取得件数（デフォルト15）

---

## ワークフロー例

### 1. 候補者への企業提案（推奨パターン）
```
1. find_companies_for_candidate(
     transfer_reasons="年収を上げたい、リモートワーク希望",
     age=32, desired_salary=600
   )
   → match_score付き企業リスト取得（これだけで完了！）

2. （必要に応じて）get_company_detail(company_name) で詳細確認
```

### 2. 自然言語で企業検索
```
semantic_search_companies("IT企業で成長できる環境、フレックス制度あり")
→ 類似度スコア付き結果
```

### 3. 特定条件での厳密検索（補助）
```
search_companies(location="東京都", max_age=35, min_salary=500)
→ 条件完全一致の企業リスト
```

### 4. 企業情報をメールから補完
```
1. get_company_detail(company_name="株式会社○○") → DB上の公式情報を取得
2. search_gmail(query="subject:株式会社○○ newer_than:90d") → 最近のメール確認
3. get_email_detail(message_id) → 採用担当からの連絡、条件交渉の経緯、非公開情報を確認
→ DBの情報 + メールの生情報を統合して提案
```

### 5. 企業からの最新連絡を一括確認
```
get_recent_emails(hours=72, max_results=20) → 直近3日のメール
→ 企業名でフィルタしてDB情報と照合
```

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

## 回答方針
- **まずセマンティック検索で候補を絞る**（高速・自然言語対応）
- 詳細確認が必要な場合のみ厳密検索を併用
- **DBにない情報はメールで補完**: 採用担当とのやり取り、条件交渉の経緯、非公開求人などはメール検索で取得
- 企業名・年収レンジを明確に提示
- マッチスコアと理由を説明
- 訴求ポイントは候補者への説明に使える形で出力
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
