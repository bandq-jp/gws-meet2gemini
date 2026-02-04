"""
Orchestrator Agent - Main coordinator for marketing AI.

Coordinates sub-agents and manages user interaction.
Tools: 6 sub-agent tools + native tools (Web Search, Code Interpreter)

Performance Optimizations:
- Native tools are cached to avoid re-instantiation
- Sub-agent factories are reused across requests
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Tuple

from agents import Agent, CodeInterpreterTool, ModelSettings, WebSearchTool
from openai.types.shared.reasoning import Reasoning

from app.infrastructure.marketing.chart_tools import CHART_TOOLS
from .analytics_agent import AnalyticsAgentFactory
from .ad_platform_agent import AdPlatformAgentFactory
from .seo_agent import SEOAgentFactory
from .wordpress_agent import WordPressAgentFactory
from .zoho_crm_agent import ZohoCRMAgentFactory
from .candidate_insight_agent import CandidateInsightAgentFactory

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)

# Module-level cache for orchestrator native tools
# Key: (country, enable_web_search, enable_code_interpreter)
_ORCHESTRATOR_NATIVE_TOOLS_CACHE: Dict[Tuple[str, bool, bool], List[Any]] = {}


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
  - 「データが取れました。次にチャートで可視化します。」→ render_chart
- ただし中間報告は1〜2文の短文にせよ。冗長な説明は不要

---

## チャート描画ルール（render_chart）
- 数値データを取得したら、**積極的にチャートで可視化**せよ
- テーブルよりもチャートの方がユーザーは理解しやすい
- チャートタイプの選び方:
  - 時系列トレンド → `line` (例: 日別セッション推移)
  - カテゴリ比較 → `bar` (例: チャネル別獲得数)
  - 構成比 → `pie`/`donut` (例: デバイス別比率)
  - ファネル → `funnel` (例: ステータス別転換)
  - 多次元比較 → `radar` (例: 複数KPI比較)
- render_chartを呼び出す前にテキストで「チャートで可視化します」と伝えてから呼び出せ

---

## 回答方針
- データは表形式やチャートで見やすく整理
- 複数ソースの結果を統合
- アクション可能な提案を含める
- チャートで可視化可能なデータは積極的にrender_chartを使う
"""


class OrchestratorAgentFactory:
    """
    Factory for the Orchestrator agent.

    The Orchestrator:
    - Exposes sub-agents as tools via Agent.as_tool()
    - Has native tools (WebSearch, CodeInterpreter) - OpenAI only
    - Coordinates parallel/sequential sub-agent calls

    Model Support:
    - OpenAI (gpt-5.1, gpt-5.2): Full features including WebSearch, CodeInterpreter
    - LiteLLM/Gemini: Sub-agent tools only (WebSearch, CodeInterpreter not supported)
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

    def build_agent(
        self,
        asset: Dict[str, Any] | None = None,
        disabled_mcp_servers: set[str] | None = None,
        mcp_servers: List[Any] | None = None,
        on_sub_agent_stream: Callable[[dict], Awaitable[None]] | None = None,
    ) -> Agent:
        """
        Build the Orchestrator agent with sub-agent tools.

        Args:
            asset: Model asset configuration (reasoning_effort, etc.)
            disabled_mcp_servers: Set of MCP server labels to disable
            mcp_servers: Local MCP server instances
            on_sub_agent_stream: Callback for sub-agent streaming events

        Returns:
            Configured Orchestrator Agent
        """
        # Build sub-agent tools
        sub_agent_tools = []
        has_stream_callback = on_sub_agent_stream is not None
        logger.info(f"[Orchestrator] Building sub-agent tools (stream_callback={has_stream_callback})")

        for name, factory in self._sub_factories.items():
            try:
                sub_agent = factory.build_agent(mcp_servers=mcp_servers, asset=asset)

                # Create stream callback that passes AgentToolStreamEvent directly
                # SDK passes AgentToolStreamEvent with keys: event, agent, tool_call
                stream_callback = on_sub_agent_stream if on_sub_agent_stream else None

                tool = sub_agent.as_tool(
                    tool_name=factory.tool_name,
                    tool_description=factory.tool_description,
                    on_stream=stream_callback,
                )
                sub_agent_tools.append(tool)
                logger.info(f"[Orchestrator] Sub-agent tool registered: {factory.tool_name} (on_stream={'yes' if stream_callback else 'no'})")
            except Exception as e:
                logger.warning(f"Failed to build sub-agent {name}: {e}")

        # Native tools for the orchestrator
        native_tools = self._get_native_tools(asset)

        # Get reasoning effort from asset or settings
        reasoning_effort = (
            asset.get("reasoning_effort")
            if asset
            else self._settings.marketing_reasoning_effort
        ) or "high"

        # Build final instructions
        instructions = self._build_instructions(asset)

        # Build model settings based on model type
        if self.is_litellm_model:
            # LiteLLM/Gemini: Minimal settings (Responses API features not available)
            model_settings = ModelSettings()
            logger.info("[Orchestrator] LiteLLM model - using minimal model settings")
        else:
            # OpenAI: Full settings with parallel tool calls enabled
            # Note: verbosity and response_include are NOT valid ModelSettings params
            model_settings = ModelSettings(
                store=True,
                parallel_tool_calls=True,  # Enable parallel sub-agent execution
                reasoning=Reasoning(
                    effort=reasoning_effort,
                    summary="detailed",
                ),
            )

        return Agent(
            name="MarketingOrchestrator",
            instructions=instructions,
            tools=native_tools + sub_agent_tools + list(CHART_TOOLS),
            model=self._settings.marketing_agent_model,
            model_settings=model_settings,
            tool_use_behavior="run_llm_again",
        )

    @property
    def is_litellm_model(self) -> bool:
        """Check if the orchestrator model is a LiteLLM model (non-OpenAI)."""
        return self._settings.marketing_agent_model.startswith("litellm/")

    def _get_native_tools(self, asset: Dict[str, Any] | None = None) -> List[Any]:
        """
        Return native tools for the orchestrator.

        For OpenAI models: WebSearchTool, CodeInterpreterTool
        For LiteLLM models: Empty (these are Responses API only)

        Performance: Tools are cached based on settings to avoid re-instantiation.
        """
        # WebSearchTool and CodeInterpreterTool are OpenAI Responses API features
        # They are not available via ChatCompletions API (LiteLLM/Gemini)
        if self.is_litellm_model:
            logger.info("[Orchestrator] LiteLLM model detected - native tools disabled")
            return []

        enable_web_search = self._settings.marketing_enable_web_search and (
            asset is None or asset.get("enable_web_search", True)
        )
        enable_code_interpreter = self._settings.marketing_enable_code_interpreter and (
            asset is None or asset.get("enable_code_interpreter", True)
        )

        # Check cache
        cache_key = (
            self._settings.marketing_search_country,
            enable_web_search,
            enable_code_interpreter,
        )
        if cache_key in _ORCHESTRATOR_NATIVE_TOOLS_CACHE:
            return _ORCHESTRATOR_NATIVE_TOOLS_CACHE[cache_key]

        # Build and cache tools
        tools: List[Any] = []

        if enable_web_search:
            tools.append(
                WebSearchTool(
                    search_context_size="medium",
                    user_location={
                        "country": self._settings.marketing_search_country,
                        "type": "approximate",
                    },
                )
            )

        if enable_code_interpreter:
            tools.append(
                CodeInterpreterTool(
                    tool_config={
                        "type": "code_interpreter",
                        "container": {
                            "type": "auto",
                            "file_ids": [],
                        },
                    }
                )
            )

        _ORCHESTRATOR_NATIVE_TOOLS_CACHE[cache_key] = tools
        logger.debug(f"[Orchestrator] Native tools cached: key={cache_key}")
        return tools

    def _build_instructions(self, asset: Dict[str, Any] | None = None) -> str:
        """Build orchestrator instructions with optional additions."""
        base_instructions = ORCHESTRATOR_INSTRUCTIONS.strip()

        addition = (asset or {}).get("system_prompt_addition")
        if addition:
            return f"{addition.strip()}\n\n{base_instructions}"

        return base_instructions

    @staticmethod
    def _normalize_verbosity(value: Any | None) -> str:
        """Map deprecated verbosity labels to valid ones."""
        if value is None:
            return "medium"
        if value == "short":
            return "low"
        if value == "long":
            return "high"
        if value in ("low", "medium", "high"):
            return value
        return "medium"
