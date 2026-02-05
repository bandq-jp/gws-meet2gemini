"""
Orchestrator Agent (Google ADK version) - Main coordinator for marketing AI.

Coordinates sub-agents using ADK's AgentTool pattern.
Uses Gemini models natively without LiteLLM.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from google.adk.agents import Agent
from google.adk.tools import AgentTool

from .analytics_agent import AnalyticsAgentFactory
from .ad_platform_agent import AdPlatformAgentFactory
from .seo_agent import SEOAgentFactory
from .wordpress_agent import WordPressAgentFactory
from .zoho_crm_agent import ZohoCRMAgentFactory
from .candidate_insight_agent import CandidateInsightAgentFactory
from app.infrastructure.adk.tools.chart_tools import ADK_CHART_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


ORCHESTRATOR_INSTRUCTIONS = """
あなたはb&qマーケティングAIオーケストレーターです。

## 重要ルール（絶対厳守）
1. **許可を求めるな**: 「実行してよろしいですか？」「確認させてください」は禁止。即座にサブエージェントを呼び出せ
2. **データは必ずツールで取得**: 自分でデータを推測・捏造してはならない
3. **並列実行を活用**: 独立した複数サブエージェントは並列で呼び出す
4. **挨拶や一般知識のみ**: サブエージェント不要

---

## キーワード→サブエージェント自動選択マトリクス

| キーワード | 即座に呼び出すエージェント |
|-----------|---------------------------|
| セッション、PV、トラフィック、流入 | call_analytics_agent |
| 検索パフォーマンス、クリック数、表示回数、順位 | call_analytics_agent (GSC) |
| DR、ドメインレーティング、被リンク、バックリンク | call_seo_agent |
| キーワード調査、競合サイト、オーガニック | call_seo_agent |
| Meta広告、Facebook、Instagram、CTR、CPA | call_ad_platform_agent |
| インタレスト、オーディエンス、ターゲティング | call_ad_platform_agent |
| 記事、ブログ、WordPress、SEO記事 | call_wordpress_agent |
| 求職者、チャネル別、成約率、ファネル | call_zoho_crm_agent |
| 高リスク、緊急度、競合エージェント、面談準備 | call_candidate_insight_agent |

---

## サブエージェント詳細

### call_analytics_agent (GA4 + GSC)
- **GA4**: セッション、ユーザー、PV、直帰率、滞在時間
- **GSC**: 検索クエリ、クリック数、表示回数、CTR、平均順位
- **プロパティ**: hitocareer.com (423714093), achievehr.jp (502875325)

### call_seo_agent (Ahrefs)
- ドメインレーティング (DR)
- オーガニックキーワード、トラフィック推定
- 被リンク、参照ドメイン
- 競合サイト分析

### call_ad_platform_agent (Meta Ads)
- キャンペーン/広告セット/広告のパフォーマンス
- インタレストターゲティング調査
- オーディエンスサイズ推定
- CTR, CPM, CPA, ROAS

### call_wordpress_agent (hitocareer + achievehr)
- 記事一覧、ブロック構造分析
- SEO要件チェック
- 記事作成・編集（明示的指示時のみ）

### call_zoho_crm_agent
- 求職者検索・一覧
- チャネル別獲得数集計
- ステータス別ファネル分析
- 担当者パフォーマンス

### call_candidate_insight_agent
- 競合エージェントリスク分析
- 緊急度評価（即時対応必要候補者）
- 転職理由・パターン分析
- 面談ブリーフィング

---

## 並列呼び出しパターン

**マーケティング効果測定**
「今月のトラフィックと応募状況」
→ call_analytics_agent + call_zoho_crm_agent

**SEO + 広告比較**
「SEO競合とMeta広告のパフォーマンス」
→ call_seo_agent + call_ad_platform_agent

**候補者 + CRM**
「高リスク候補者とチャネル別成約率」
→ call_candidate_insight_agent + call_zoho_crm_agent

**全体レポート**
「今月のマーケティング全体レポート」
→ call_analytics_agent + call_seo_agent + call_zoho_crm_agent

---

## 中間報告ルール（重要）
- ツール実行の前後に、**今何をしているか・次に何をするかを短いテキストで報告**せよ
- ユーザーはリアルタイムで行動を見ている。無言でツールを連続実行するな
- 例:
  - 「まずGA4からセッションデータを取得します。」→ call_analytics_agent
  - 「データが取れました。チャートで可視化します。」→ render_chart
- ただし中間報告は1〜2文の短文にせよ。冗長な説明は不要

---

## 回答方針
- データは表形式やチャートで見やすく整理
- 複数ソースの結果を統合
- アクション可能な提案を含める
"""


class OrchestratorAgentFactory:
    """
    Factory for the ADK Orchestrator agent.

    The Orchestrator:
    - Exposes sub-agents as tools via AgentTool
    - Coordinates parallel/sequential sub-agent calls
    - Uses Gemini Pro for orchestration
    """

    def __init__(self, settings: "Settings"):
        self._settings = settings
        self._sub_factories: Dict[str, Any] = {
            "analytics": AnalyticsAgentFactory(settings),
            "ad_platform": AdPlatformAgentFactory(settings),
            "seo": SEOAgentFactory(settings),
            "wordpress": WordPressAgentFactory(settings),
            "zoho_crm": ZohoCRMAgentFactory(settings),
            "candidate_insight": CandidateInsightAgentFactory(settings),
        }

    @property
    def model(self) -> str:
        """
        Model to use for the orchestrator.

        ADK native Gemini support - no LiteLLM needed.
        """
        return self._settings.adk_orchestrator_model or "gemini-2.5-flash-preview-05-20"

    def build_agent(
        self,
        asset: Dict[str, Any] | None = None,
        disabled_mcp_servers: set[str] | None = None,
        mcp_servers: List[Any] | None = None,
    ) -> Agent:
        """
        Build the Orchestrator agent with sub-agent tools.

        Args:
            asset: Model asset configuration
            disabled_mcp_servers: Set of MCP server labels to disable
            mcp_servers: MCP toolset instances

        Returns:
            Configured ADK Orchestrator Agent
        """
        # Build sub-agent tools using AgentTool
        sub_agent_tools = []
        logger.info("[ADK Orchestrator] Building sub-agent tools")

        for name, factory in self._sub_factories.items():
            try:
                sub_agent = factory.build_agent(mcp_servers=mcp_servers, asset=asset)

                # Wrap sub-agent as AgentTool
                tool = AgentTool(agent=sub_agent)
                sub_agent_tools.append(tool)
                logger.info(f"[ADK Orchestrator] Sub-agent registered: {factory.tool_name}")
            except Exception as e:
                logger.warning(f"Failed to build sub-agent {name}: {e}")

        # Build final instructions
        instructions = self._build_instructions(asset)

        # Combine sub-agent tools with chart tools
        all_tools = sub_agent_tools + list(ADK_CHART_TOOLS)

        return Agent(
            name="MarketingOrchestrator",
            model=self.model,
            description="マーケティングAIオーケストレーター - 複数の専門エージェントを調整して分析を実行",
            instruction=instructions,
            tools=all_tools,
        )

    def _build_instructions(self, asset: Dict[str, Any] | None = None) -> str:
        """Build orchestrator instructions with optional additions."""
        base_instructions = ORCHESTRATOR_INSTRUCTIONS.strip()

        addition = (asset or {}).get("system_prompt_addition")
        if addition:
            return f"{addition.strip()}\n\n{base_instructions}"

        return base_instructions
