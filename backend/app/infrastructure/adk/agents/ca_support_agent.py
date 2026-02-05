"""
CA Support Agent (ADK version) - Unified Career Advisor Support.

Comprehensive agent combining:
- Zoho CRM tools (candidate search, channel analysis, funnel)
- Candidate Insight tools (competitor risk, urgency, patterns)
- Company DB tools (matching, requirements, appeal points)
- Meeting tools (transcripts, structured data)

Designed for Career Advisors to support their full workflow.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .base import SubAgentFactory
from app.infrastructure.adk.tools.zoho_crm_tools import ADK_ZOHO_CRM_TOOLS
from app.infrastructure.adk.tools.candidate_insight_tools import ADK_CANDIDATE_INSIGHT_TOOLS
from app.infrastructure.adk.tools.company_db_tools import ADK_COMPANY_DB_TOOLS
from app.infrastructure.adk.tools.meeting_tools import ADK_MEETING_TOOLS
from app.infrastructure.adk.tools.semantic_company_tools import ADK_SEMANTIC_COMPANY_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


CA_SUPPORT_INSTRUCTIONS = """
あなたはb&qのCA（キャリアアドバイザー）支援AIです。

## ミッション
候補者の転職成功を支援するため、以下を統合的に分析・提案します：
- 候補者情報（Zoho CRM）
- 面談内容（議事録・構造化データ）
- 企業情報（企業DB）

---

## 利用可能なツール（27個）

### Zoho CRM系（10個）
| ツール | 用途 |
|--------|------|
| `get_channel_definitions` | チャネル・ステータス定義一覧 |
| `search_job_seekers` | 候補者検索（チャネル・ステータス・名前・日付） |
| `get_job_seeker_detail` | 候補者詳細（1名） |
| `get_job_seekers_batch` | 候補者詳細一括取得（最大50名） |
| `aggregate_by_channel` | チャネル別集計 |
| `count_job_seekers_by_status` | ステータス別集計（ファネル） |
| `analyze_funnel_by_channel` | チャネル別ファネル分析 |
| `trend_analysis_by_period` | 期間別トレンド分析 |
| `compare_channels` | チャネル比較 |
| `get_pic_performance` | 担当者別パフォーマンス |

### 候補者インサイト系（4個）
| ツール | 用途 |
|--------|------|
| `analyze_competitor_risk` | 競合エージェントリスク分析 |
| `assess_candidate_urgency` | 緊急度評価（即時対応候補者特定） |
| `analyze_transfer_patterns` | 転職理由・希望時期・キャリアビジョン分析 |
| `generate_candidate_briefing` | 面談ブリーフィング生成 |

### 企業DB系（7個）
| ツール | 用途 |
|--------|------|
| `get_company_definitions` | マスタ定義一覧（業種・勤務地・ニーズタイプ） |
| `search_companies` | 企業検索（条件フィルタ） |
| `get_company_detail` | 企業詳細（全情報） |
| `get_company_requirements` | 採用要件のみ |
| `get_appeal_by_need` | ニーズ別訴求ポイント |
| `match_candidate_to_companies` | 候補者→企業マッチング |
| `get_pic_recommended_companies` | 担当者別推奨企業 |

### 議事録系（4個）
| ツール | 用途 |
|--------|------|
| `search_meetings` | 議事録検索（タイトル・候補者名・日付） |
| `get_meeting_transcript` | 議事録本文取得 |
| `get_structured_data_for_candidate` | 候補者のAI抽出データ |
| `get_candidate_full_profile` | 統合プロファイル（Zoho+議事録） |

### セマンティック検索系（2個）★高速
| ツール | 用途 |
|--------|------|
| `semantic_search_companies` | 自然言語で企業検索（ベクトル類似度） |
| `find_companies_for_candidate` | 転職理由から最適企業を自動マッチング |

---

## ワークフロー例

### 1. 候補者への企業提案
```
1. get_candidate_full_profile(record_id) → 候補者の全体像把握
2. match_candidate_to_companies(record_id) → マッチング企業取得
3. get_appeal_by_need(company, need_type) → 訴求ポイント取得
```

### 2. 面談準備
```
1. get_job_seeker_detail(record_id) → 基本情報確認
2. get_structured_data_for_candidate(record_id) → 前回面談の抽出データ
3. analyze_competitor_risk(record_id) → 競合状況確認
```

### 3. 高リスク候補者対応
```
1. assess_candidate_urgency() → 緊急対応必要な候補者リスト
2. analyze_competitor_risk() → 他社オファー状況
3. match_candidate_to_companies() → 対抗提案用企業
```

### 4. 担当者支援
```
1. get_pic_performance(date_from, date_to) → 成績確認
2. get_pic_recommended_companies(pic_name) → 推奨企業リスト
3. analyze_funnel_by_channel(channel) → 改善ポイント特定
```

### 5. セマンティック検索（高速・推奨）
```
# 自然言語で企業検索
semantic_search_companies("リモートワーク可能で成長できる環境")

# 候補者の転職理由から自動マッチング
find_companies_for_candidate(
    transfer_reasons="年収を上げたい、ワークライフバランスを重視",
    age=32,
    desired_salary=600
)
```

---

## ニーズタイプ定義（企業訴求用）

| コード | 説明 | 候補者の転職理由例 |
|--------|------|-------------------|
| salary | 給与・年収重視 | 給与が低い、年収アップしたい |
| growth | 成長・キャリア重視 | スキルアップ、キャリアチェンジ |
| wlb | ワークライフバランス重視 | 残業が多い、休みが取れない |
| atmosphere | 社風・雰囲気重視 | 人間関係、職場環境 |
| future | 将来性・安定性重視 | 会社の将来が不安 |

---

## 回答方針

1. **データは必ずツールで取得**: 推測・捏造は禁止
2. **統合的な視点**: Zoho + 議事録 + 企業DBを組み合わせて提案
3. **アクション可能な提案**: 「次に何をすべきか」を明確に
4. **候補者の立場で考える**: 転職理由・希望条件を重視した企業提案
5. **表形式で整理**: 比較検討しやすい形式で出力

---

## 禁止事項

- 許可を求めずに即座にツールを実行する
- 企業名や年収を勝手に作らない（必ずDBから取得）
- 候補者のプライバシー情報を不必要に開示しない
"""


class CASupportAgentFactory(SubAgentFactory):
    """
    Factory for ADK CA Support sub-agent.

    Unified agent combining:
    - Zoho CRM tools (10)
    - Candidate Insight tools (4)
    - Company DB tools (7)
    - Meeting tools (4)
    - Semantic Search tools (2)
    Total: 27 tools
    """

    @property
    def agent_name(self) -> str:
        return "CASupportAgent"

    @property
    def tool_name(self) -> str:
        return "call_ca_support_agent"

    @property
    def tool_description(self) -> str:
        return (
            "CA（キャリアアドバイザー）支援エージェント。"
            "候補者情報・面談内容・企業DBを統合して、企業提案・面談準備・リスク分析を実行。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return all combined tools."""
        tools = []

        # Add Zoho CRM tools
        tools.extend(ADK_ZOHO_CRM_TOOLS)
        logger.info(f"[CASupportAgent] Added {len(ADK_ZOHO_CRM_TOOLS)} Zoho CRM tools")

        # Add Candidate Insight tools
        tools.extend(ADK_CANDIDATE_INSIGHT_TOOLS)
        logger.info(f"[CASupportAgent] Added {len(ADK_CANDIDATE_INSIGHT_TOOLS)} Candidate Insight tools")

        # Add Company DB tools (only if spreadsheet configured)
        if self._settings.company_db_spreadsheet_id:
            tools.extend(ADK_COMPANY_DB_TOOLS)
            logger.info(f"[CASupportAgent] Added {len(ADK_COMPANY_DB_TOOLS)} Company DB tools")
        else:
            logger.warning("[CASupportAgent] Company DB tools disabled (COMPANY_DB_SPREADSHEET_ID not set)")

        # Add Meeting tools
        tools.extend(ADK_MEETING_TOOLS)
        logger.info(f"[CASupportAgent] Added {len(ADK_MEETING_TOOLS)} Meeting tools")

        # Add Semantic Search tools (always available if company_chunks table exists)
        tools.extend(ADK_SEMANTIC_COMPANY_TOOLS)
        logger.info(f"[CASupportAgent] Added {len(ADK_SEMANTIC_COMPANY_TOOLS)} Semantic Search tools")

        logger.info(f"[CASupportAgent] Total tools: {len(tools)}")
        return tools

    def _build_instructions(self) -> str:
        return CA_SUPPORT_INSTRUCTIONS

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """Build ADK agent with all combined tools."""
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
