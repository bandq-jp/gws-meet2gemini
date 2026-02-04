# マルチエージェントアーキテクチャ設計書

> **Version**: 2.0.0
> **Date**: 2026-02-04
> **Status**: Sub-Agent as Tool方式に更新

## エグゼクティブサマリー

本ドキュメントは、b&q Hubマーケティングエージェントを単一エージェントからマルチエージェント構成に移行するための包括的な設計書です。

### 期待効果

| 指標 | 現状 | 目標 | 改善率 |
|------|------|------|--------|
| 入力トークン/リクエスト | ~11,000 | ~2,800 | **-75%** |
| ツール定義数/エージェント | 97 | 25-35 | **-67%** |
| 平均レスポンス時間 | 8-12秒 | 2-4秒 | **-70%** |
| 月間APIコスト | $1,650/100ユーザー | $420 | **-75%** |

---

## 目次

1. [現状分析](#1-現状分析)
2. [技術調査結果](#2-技術調査結果)
3. [Sub-Agent as Tool アーキテクチャ](#3-sub-agent-as-tool-アーキテクチャ) ⭐ **推奨**
4. [実装コード](#4-実装コード)
5. [コンテキスト最適化](#5-コンテキスト最適化)
6. [エラーハンドリング](#6-エラーハンドリング)
7. [実装ロードマップ](#7-実装ロードマップ)
8. [技術的知見](#8-技術的知見)

---

## 1. 現状分析

### 1.1 現在のアーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│              MarketingAgent (単一エージェント)            │
│                                                         │
│  Model: gpt-5-mini                                      │
│  Instructions: ~800 chars (最適化済み)                   │
│                                                         │
│  Tools (97個):                                          │
│  ├─ Web Search (1)                                      │
│  ├─ Code Interpreter (1)                                │
│  ├─ GA4 MCP (6)                                         │
│  ├─ GSC MCP (10)                                        │
│  ├─ Ahrefs MCP (20)                                     │
│  ├─ Meta Ads MCP (20)                                   │
│  ├─ WordPress MCP (28)                                  │
│  ├─ Zoho CRM Tools (9)                                  │
│  └─ Candidate Insight Tools (4)                         │
└─────────────────────────────────────────────────────────┘
```

### 1.2 問題点

1. **コンテキストウィンドウの圧迫**
   - 97ツールの定義だけで ~7,000トークン消費
   - 長期会話で推論品質が低下

2. **ツール選択の精度低下**
   - 多すぎるツールからの選択でミスが発生
   - 類似ツール間での混乱

3. **レイテンシ**
   - すべてのMCPサーバーを初期化
   - 不要なツール定義の読み込み

4. **スケーラビリティ**
   - 新機能追加でツール数が線形増加
   - 保守性の低下

---

## 2. 技術調査結果

### 2.1 OpenAI Agents SDK v0.7.0

#### Handoffs機能

エージェント間で会話を引き継ぐ仕組み。

```python
from agents import Agent, handoff

specialist = Agent(name="Specialist", instructions="...")

main_agent = Agent(
    name="MainAgent",
    handoffs=[handoff(specialist, tool_description="専門分析")]
)
```

**主要オプション**:
- `nest_handoff_history=True`: 履歴を要約して伝搬（トークン40-60%削減）
- `input_filter`: コンテキストのフィルタリング
- `on_handoff`: ハンドオフ時のコールバック

#### Agent.as_tool() メソッド

エージェントをツールとして呼び出すパターン。

```python
search_agent = Agent(name="SearchAgent", tools=[...])

# ツールとして変換
search_tool = search_agent.as_tool(
    tool_name="deep_search",
    tool_description="詳細検索"
)

# 親エージェントで使用
main_agent = Agent(tools=[search_tool])
```

**Handoff vs Tool Agent 比較**:

| 特性 | Handoff | Tool Agent |
|------|---------|-----------|
| 履歴継承 | ✓ 完全継承 | ✗ LLM生成入力のみ |
| 制御フロー | 子が会話を引き継ぐ | 親が制御を維持 |
| 用途 | オープンエンドな会話 | 明確なサブタスク |

### 2.2 Responses API

- `previous_response_id`: ステートフル会話の構築
- Built-in tools: Web Search, Code Interpreter, File Search, MCP
- Agents SDKとの組み合わせ使用が可能

### 2.3 群知能パターン

**OpenAI Swarm → Agents SDK**への進化：
- Swarmは教育・実験目的
- Agents SDKが本番用進化版
- 「プリミティブを最小限に保つ」設計哲学

**主要オーケストレーションパターン**:

| パターン | 説明 | 適用条件 |
|---------|------|---------|
| Router | タスク要件に基づくルーティング | 多様な専門性が必要 |
| Hierarchical | ツリー構造で上位が委任 | 明確な責任分担 |
| Sequential | 直列処理 | 依存関係のある段階的処理 |
| Concurrent | 独立タスクを並列実行 | タスク間依存なし |

### 2.4 Claude Codeアーキテクチャからの学び

- **シングルエージェント + ツール専門化**: サブエージェント分割ではなく、ツール群による機能分離
- **明示的な依存関係**: blocks/blockedBy による実行順序の明確化
- **並列実行の積極活用**: 独立タスクは常に同時実行
- **進捗の可視化**: リアルタイムフィードバック

---

## 3. Sub-Agent as Tool アーキテクチャ

> ⭐ **推奨方式**: Handoff方式ではなく、Sub-Agent as Tool方式を採用

### 3.1 Handoff vs Sub-Agent as Tool

| 特性 | Handoff | Sub-Agent as Tool |
|------|---------|-------------------|
| **制御権** | 子エージェントに完全移譲 | 親エージェントが保持 ✅ |
| **並列実行** | 不可（1対1の引き継ぎ） | 可能 ✅ |
| **エラー復旧** | 困難（制御が戻らない） | 親で対応可能 ✅ |
| **対話継続** | 途切れる（子が引き継ぐ） | 継続可能 ✅ |
| **履歴共有** | 完全継承 | LLM生成入力のみ |
| **用途** | オープンエンドな会話委任 | 明確なサブタスク実行 |

**結論**: マーケティングAIでは「親が制御を保持」「並列実行」「エラー復旧」が重要なため、**Sub-Agent as Tool方式を採用**。

### 3.2 推奨アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                  Orchestrator Agent (GPT-5.2)                   │
│                                                                 │
│  役割:                                                          │
│  - ユーザーとの対話管理                                          │
│  - タスク分解・サブエージェント振り分け                          │
│  - 結果統合・最終回答生成                                        │
│                                                                 │
│  ネイティブツール: Web Search, Code Interpreter                 │
│  サブエージェントツール: SEO, Zoho, Candidate                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ 並列/順次実行 (asyncio.gather / TaskGroup)
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  SEO Analysis   │  │  Zoho CRM       │  │  Candidate      │
│  Agent          │  │  Agent          │  │  Insight Agent  │
│                 │  │                 │  │                 │
│ Model: GPT-5-mini│  │ Model: GPT-5-mini│  │ Model: GPT-5-mini│
│                 │  │                 │  │                 │
│ Tools:          │  │ Tools:          │  │ Tools:          │
│ - GA4 MCP (6)   │  │ - search (1)    │  │ - competitor (1)│
│ - GSC MCP (10)  │  │ - aggregate (4) │  │ - urgency (1)   │
│ - Ahrefs MCP(20)│  │ - funnel (1)    │  │ - patterns (1)  │
│ - Web Search    │  │ - trend (1)     │  │ - briefing (1)  │
│                 │  │ - compare (1)   │  │                 │
│ Total: 37       │  │ Total: 9        │  │ Total: 4        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 3.3 Agent.as_tool() API詳細

OpenAI Agents SDK v0.7.0 の `Agent.as_tool()` メソッド:

```python
def as_tool(
    self,
    tool_name: str | None = None,              # ツール名 (デフォルト: エージェント名)
    tool_description: str | None = None,        # ツール説明
    custom_output_extractor: Callable | None = None,  # 結果加工関数
    on_stream: Callable | None = None,          # ストリーミングコールバック
    max_turns: int = 10,                        # 最大ターン数
) -> FunctionTool:
```

**使用例**:
```python
seo_agent = Agent(name="SEOAnalyst", instructions="...", tools=[...])

# ツールとして登録
seo_tool = seo_agent.as_tool(
    tool_name="run_seo_analysis",
    tool_description="SEO分析を実行（GA4, GSC, Ahrefs連携）",
    custom_output_extractor=lambda result: {
        "analysis": result.final_output,
        "tokens": result.usage.total_tokens,
    },
    max_turns=20,
)

# オーケストレーターに登録
orchestrator = Agent(
    name="Orchestrator",
    model="gpt-5.2",
    tools=[seo_tool, zoho_tool, candidate_tool],
)
```

### 3.4 並列実行パターン

Python 3.11+ の `asyncio.TaskGroup` を使用した構造化並列処理:

```python
async def run_parallel_subagents(tasks: list[dict]) -> list[dict]:
    """複数サブエージェントを並列実行"""
    async with asyncio.TaskGroup() as tg:
        futures = [
            tg.create_task(
                Runner.run(task["agent"], input=task["input"]),
                name=task["name"],
            )
            for task in tasks
        ]
    return [f.result() for f in futures]

# 使用例
results = await run_parallel_subagents([
    {"name": "seo", "agent": seo_agent, "input": "トラフィック分析"},
    {"name": "zoho", "agent": zoho_agent, "input": "チャネル別集計"},
    {"name": "candidate", "agent": candidate_agent, "input": "緊急度評価"},
])
```

**並列実行のメリット**:
- 3つのサブエージェントを同時実行 → レイテンシ 1/3
- 親エージェントは結果を待機後、統合回答を生成
- 1つが失敗しても他は継続（エラー伝搬オプション可）

### 3.5 コスト分析

| クエリ種別 | 割合 | 構成 | コスト/クエリ |
|-----------|------|------|--------------|
| 単純クエリ | 60% | GPT-5-mini 単体 | ¥0.96 |
| 中程度クエリ | 30% | GPT-5-mini × 2並列 | ¥1.5 |
| 複雑クエリ | 10% | GPT-5.2 + mini × 2 | ¥5.5 |
| **加重平均** | - | - | **¥1.5/クエリ** |

現在の単一エージェント方式（¥3-5/クエリ）と比較して**50-70%削減**。

### 3.6 エージェント責務分離

| エージェント | 責務 | モデル | ツール数 |
|-------------|------|--------|---------|
| **Orchestrator** | 対話管理・タスク分解・結果統合 | GPT-5.2 | 3 (サブエージェント) |
| **SEO Agent** | 検索順位・競合分析・トラフィック | GPT-5-mini | 37 |
| **Zoho Agent** | 求職者検索・チャネル集計・ファネル | GPT-5-mini | 9 |
| **Candidate Agent** | 競合リスク・緊急度・転職パターン | GPT-5-mini | 4 |

---

## 4. 実装コード

### 4.1 Orchestrator Agent

```python
# backend/app/infrastructure/chatkit/orchestrator_agent.py

from agents import Agent, Runner, ModelSettings, Reasoning
from agents.tool import WebSearchTool, CodeInterpreterTool

class OrchestratorAgentFactory:
    """メインオーケストレーターエージェント (GPT-5.2)"""

    def __init__(self, settings: Settings):
        self._settings = settings

    def build_agent(
        self,
        asset: dict,
        mcp_servers: list,
    ) -> Agent:
        """
        オーケストレーターエージェントを構築
        """
        # サブエージェントをツールとして登録
        subagent_tools = self._build_subagent_tools(mcp_servers)

        # ネイティブツール
        native_tools = [
            WebSearchTool(),
            CodeInterpreterTool(),
        ]

        return Agent(
            name="MarketingOrchestrator",
            instructions=self._build_instructions(asset),
            model="gpt-5.2",
            model_settings=ModelSettings(
                reasoning=Reasoning(
                    effort=asset.get("reasoning_effort", "high"),
                    summary="detailed",
                ),
            ),
            tools=native_tools + subagent_tools,
        )

    def _build_subagent_tools(self, mcp_servers: list) -> list:
        """サブエージェントをツールとして構築"""
        from .subagent_tools import (
            run_seo_analysis_agent,
            run_zoho_analysis_agent,
            run_candidate_insight_agent,
        )
        return [
            run_seo_analysis_agent,
            run_zoho_analysis_agent,
            run_candidate_insight_agent,
        ]

    def _build_instructions(self, asset: dict) -> str:
        return """
あなたはマーケティング分析のオーケストレーターです。

## 利用可能なサブエージェント

1. **run_seo_analysis_agent**: SEO・検索分析（GA4, GSC, Ahrefs連携）
2. **run_zoho_analysis_agent**: Zoho CRM分析（求職者、チャネル、ファネル）
3. **run_candidate_insight_agent**: 候補者インサイト（競合リスク、緊急度）

## 行動原則

- ユーザーの質問を分析し、必要なサブエージェントを選択
- 複数データソースが必要な場合、並列でサブエージェントを呼び出し
- サブエージェントの結果を統合し、アクショナブルな回答を生成
- 単純な質問（挨拶、一般知識）はサブエージェントを使わず直接回答

## 並列実行の例

ユーザー: 「今月の採用状況と、どのチャネルからの応募が多いか教えて」
→ run_zoho_analysis_agent + run_candidate_insight_agent を並列呼び出し
→ 結果を統合して回答
        """
```

### 4.2 サブエージェントツール

```python
# backend/app/infrastructure/chatkit/subagent_tools.py

from agents import function_tool, RunContextWrapper, Agent, Runner
from typing import Optional, Any
import asyncio

@function_tool(name_override="run_seo_analysis_agent")
async def run_seo_analysis_agent(
    ctx: RunContextWrapper[Any],
    query: str,
    property_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """
    SEO分析サブエージェントを実行。
    GA4, GSC, Ahrefsを使用してトラフィック・検索順位・競合分析を行う。

    Args:
        query: 分析クエリ（例: "トラフィック推移を分析"）
        property_name: GA4/GSCプロパティ名（省略可）
        date_from: 開始日（YYYY-MM-DD形式、省略可）
        date_to: 終了日（YYYY-MM-DD形式、省略可）
    """
    from app.infrastructure.config.settings import get_settings
    settings = get_settings()

    # サブエージェント構築
    agent = Agent(
        name="SEOAnalysisAgent",
        instructions=f"""
SEO分析の専門家として以下を実行:
- GA4: トラフィック分析
- GSC: 検索クエリ・掲載順位分析
- Ahrefs: 競合・被リンク分析

対象プロパティ: {property_name or "デフォルト"}
期間: {date_from or "直近"} 〜 {date_to or "現在"}

分析後、具体的な改善提案を含めて回答。
        """,
        model="gpt-5-mini",
        tools=[WebSearchTool()],
        # mcp_serversはコンテキストから取得
    )

    # 実行
    result = await Runner.run(
        agent,
        input=query,
        max_turns=20,
    )

    return {
        "success": True,
        "analysis": result.final_output,
        "tokens_used": result.usage.total_tokens if result.usage else 0,
    }


@function_tool(name_override="run_zoho_analysis_agent")
async def run_zoho_analysis_agent(
    ctx: RunContextWrapper[Any],
    query: str,
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """
    Zoho CRM分析サブエージェントを実行。
    求職者データの検索・集計・ファネル分析を行う。

    Args:
        query: 分析クエリ（例: "チャネル別の応募数を集計"）
        channel: フィルタするチャネル（省略可）
        date_from: 開始日（YYYY-MM-DD形式、省略可）
        date_to: 終了日（YYYY-MM-DD形式、省略可）
    """
    from .zoho_crm_tools import ZOHO_CRM_TOOLS

    agent = Agent(
        name="ZohoAnalysisAgent",
        instructions=f"""
Zoho CRM分析の専門家として以下を実行:
- 求職者の検索・詳細取得
- チャネル別獲得分析
- ステータス別ファネル分析
- トレンド分析・チャネル比較

フィルタ条件:
- チャネル: {channel or "全て"}
- 期間: {date_from or "全期間"} 〜 {date_to or "現在"}

データドリブンな洞察を提供。
        """,
        model="gpt-5-mini",
        tools=list(ZOHO_CRM_TOOLS),
    )

    result = await Runner.run(
        agent,
        input=query,
        max_turns=15,
    )

    return {
        "success": True,
        "analysis": result.final_output,
        "tokens_used": result.usage.total_tokens if result.usage else 0,
    }


@function_tool(name_override="run_candidate_insight_agent")
async def run_candidate_insight_agent(
    ctx: RunContextWrapper[Any],
    query: str,
    analysis_type: Optional[str] = None,
) -> dict:
    """
    候補者インサイトサブエージェントを実行。
    競合リスク・緊急度評価・転職パターン分析を行う。

    Args:
        query: 分析クエリ（例: "高リスク候補者を特定"）
        analysis_type: 分析種別（competitor_risk, urgency, patterns, briefing）
    """
    from .candidate_insight_tools import CANDIDATE_INSIGHT_TOOLS

    agent = Agent(
        name="CandidateInsightAgent",
        instructions=f"""
候補者インサイト分析の専門家として以下を実行:
- 競合エージェント利用状況の分析
- 緊急度評価（転職希望時期、離職状況）
- 転職パターン・動機の分析
- 面談準備用ブリーフィング生成

分析タイプ: {analysis_type or "自動判定"}

アクショナブルな提案を含めて回答。
        """,
        model="gpt-5-mini",
        tools=list(CANDIDATE_INSIGHT_TOOLS),
    )

    result = await Runner.run(
        agent,
        input=query,
        max_turns=10,
    )

    return {
        "success": True,
        "analysis": result.final_output,
        "tokens_used": result.usage.total_tokens if result.usage else 0,
    }
```

### 4.3 並列実行ユーティリティ

```python
# backend/app/infrastructure/chatkit/parallel_executor.py

import asyncio
from typing import Any, Callable, Coroutine, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_parallel_subagents(
    tasks: list[dict],
    timeout: int = 300,
) -> list[dict]:
    """
    複数のサブエージェントを並列実行。

    Args:
        tasks: [{"name": str, "coro": Coroutine}, ...]
        timeout: タイムアウト秒数

    Returns:
        [{"name": str, "result": Any, "success": bool, "error": str?}, ...]
    """
    async def _run_with_timeout(
        coro: Coroutine,
        name: str,
    ) -> dict:
        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            return {
                "name": name,
                "result": result,
                "success": True,
            }
        except asyncio.TimeoutError:
            logger.warning(f"Subagent {name} timed out after {timeout}s")
            return {
                "name": name,
                "result": None,
                "success": False,
                "error": f"タイムアウト ({timeout}秒)",
            }
        except Exception as e:
            logger.error(f"Subagent {name} failed: {e}")
            return {
                "name": name,
                "result": None,
                "success": False,
                "error": str(e),
            }

    # Python 3.11+ TaskGroup
    async with asyncio.TaskGroup() as tg:
        futures = [
            tg.create_task(
                _run_with_timeout(task["coro"], task["name"]),
                name=task["name"],
            )
            for task in tasks
        ]

    return [f.result() for f in futures]


def merge_subagent_results(
    results: list[dict],
    include_tokens: bool = True,
) -> dict:
    """
    サブエージェント結果をマージ。

    Args:
        results: run_parallel_subagents の結果
        include_tokens: トークン使用量を集計するか

    Returns:
        {
            "analyses": {name: analysis},
            "total_tokens": int,
            "success_count": int,
            "failure_count": int,
            "errors": {name: error},
        }
    """
    analyses = {}
    errors = {}
    total_tokens = 0

    for r in results:
        name = r["name"]
        if r["success"]:
            result = r["result"]
            analyses[name] = result.get("analysis", result)
            if include_tokens:
                total_tokens += result.get("tokens_used", 0)
        else:
            errors[name] = r.get("error", "Unknown error")

    return {
        "analyses": analyses,
        "total_tokens": total_tokens,
        "success_count": len(analyses),
        "failure_count": len(errors),
        "errors": errors if errors else None,
    }
```

---

## 5. コンテキスト最適化

### 5.1 Handoff履歴圧縮

```python
from agents.run import RunConfig

# 履歴を要約して伝搬（トークン40-60%削減）
run_config = RunConfig(
    nest_handoff_history=True,
)
```

**圧縮前**:
```
[全履歴: 20ターン × 500トークン = 10,000トークン]
```

**圧縮後**:
```
<CONVERSATION HISTORY>
1. user: SEO分析を依頼
2. assistant: GA4/GSCでデータ取得、競合分析を実施
3. 結果: オーガニックトラフィック20%増の施策を提案
</CONVERSATION HISTORY>
[圧縮後: ~500トークン]
```

### 5.2 選択的コンテキスト伝搬

```python
from agents.extensions.handoff_filters import remove_all_tools

async def selective_context_filter(data: HandoffInputData) -> HandoffInputData:
    """機密データ除外 + 必要なツール結果のみ抽出"""

    # 最新5アイテムのみ保持
    filtered_items = data.new_items[-5:]

    # 機密フィールド除外
    cleaned = [
        item for item in filtered_items
        if "api_key" not in str(item).lower()
    ]

    return data.clone(
        new_items=tuple(cleaned),
        input_items=tuple(cleaned),
    )

# Handoffで使用
handoff(
    specialist_agent,
    input_filter=selective_context_filter,
    nest_handoff_history=True,
)
```

### 5.3 動的ツール割り当て

```python
class DynamicToolLoader:
    """インテントに応じたツールセットの動的ロード"""

    def __init__(self):
        self._mcp_cache: dict[str, MCPServerStdio] = {}

    async def load_tools_for_intent(
        self,
        intent: str,
    ) -> list[Tool]:
        """必要なツールのみをロード"""

        if intent == "seo":
            return [
                await self._get_or_create_mcp("ga4"),
                await self._get_or_create_mcp("gsc"),
                await self._get_or_create_mcp("ahrefs"),
                WebSearchTool(),
            ]
        elif intent == "crm":
            return [
                *ZOHO_CRM_TOOLS,
                *CANDIDATE_INSIGHT_TOOLS,
            ]
        # ... 他のインテント

    async def _get_or_create_mcp(self, name: str) -> MCPServerStdio:
        """MCPサーバーをキャッシュから取得または作成"""
        if name not in self._mcp_cache:
            self._mcp_cache[name] = await self._create_mcp(name)
        return self._mcp_cache[name]
```

### 5.4 メモリ設計

```
┌─────────────────────────────────────────────────────────┐
│                     メモリ層構造                         │
├─────────────────────────────────────────────────────────┤
│ L1: 短期記憶 (Session Memory)                           │
│     - 最新3ターンの会話履歴                              │
│     - 現在のツール実行結果                               │
│     - TTL: 30分                                         │
├─────────────────────────────────────────────────────────┤
│ L2: 中期記憶 (Thread Context)                           │
│     - スレッド内の分析サマリー                           │
│     - 抽出されたインサイト                               │
│     - TTL: 7日                                          │
├─────────────────────────────────────────────────────────┤
│ L3: 長期記憶 (User Preferences)                         │
│     - ユーザーの分析パターン                             │
│     - 過去の重要な洞察                                   │
│     - TTL: 90日                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 6. エラーハンドリング

### 6.1 Handoff失敗時のフォールバック

```python
class HandoffErrorHandler:
    """Handoffエラーの統一管理"""

    async def handle_error(
        self,
        error: Exception,
        context: RunContextWrapper,
        source_agent: Agent,
        target_agent_name: str,
    ) -> dict:
        error_type = type(error).__name__

        # 一時的エラー → リトライ
        if isinstance(error, (ConnectionError, TimeoutError)):
            return {
                "action": "retry",
                "message": f"{target_agent_name}への接続を再試行中...",
                "retry_count": context.context.get("retry_count", 0) + 1,
            }

        # 権限エラー → エスカレーション
        elif error_type == "PermissionError":
            return {
                "action": "escalate",
                "message": "この操作には追加の権限が必要です。",
            }

        # フォールバック → 汎用エージェント
        else:
            return {
                "action": "fallback",
                "message": "別の方法で対応します。",
                "fallback_agent": "GeneralAgent",
            }
```

### 6.2 タイムアウト処理

```python
import asyncio

async def run_with_timeout(
    agent: Agent,
    input_text: str,
    timeout_sec: int = 30,
) -> dict:
    """タイムアウト付きエージェント実行"""
    try:
        result = await asyncio.wait_for(
            Runner.run(agent, input=input_text),
            timeout=timeout_sec,
        )
        return {"success": True, "result": result}
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "タイムアウト",
            "message": "処理に時間がかかっています。",
        }
```

### 6.3 リトライ戦略

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class HandoffRetryManager:
    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def execute_with_retry(
        handoff_func,
        context,
        input_data,
    ):
        """指数バックオフでリトライ"""
        try:
            return await handoff_func(context, input_data)
        except Exception as e:
            if _is_transient_error(e):
                raise  # リトライ対象
            else:
                raise ValueError(f"リトライ不可: {e}")
```

---

## 7. 実装ロードマップ

### Phase 1: 基盤整備 (Week 1-2)

```
目標: Router Agent + 専門エージェントファクトリー
成果物:
  - router_agent.py
  - specialist_agents.py (SEO, Ads, CRM, Content)
  - 単体テスト

タスク:
  □ RouterAgentFactory 実装
  □ SEOAgentFactory 実装
  □ AdsAgentFactory 実装
  □ CRMAgentFactory 実装
  □ ContentAgentFactory 実装
  □ ルーティング精度テスト (F1 > 0.85)
```

### Phase 2: Handoff統合 (Week 3-4)

```
目標: Handoff機構の統合
成果物:
  - handoff_manager.py
  - context_filters.py
  - 統合テスト

タスク:
  □ Handoff設定の実装
  □ nest_handoff_history の検証
  □ カスタム入力フィルタの実装
  □ エラーハンドリングの実装
  □ marketing_server.py への統合
```

### Phase 3: コンテキスト最適化 (Week 5-6)

```
目標: トークン消費の最適化
成果物:
  - context_compressor.py
  - dynamic_tool_loader.py
  - メモリ管理

タスク:
  □ 会話履歴圧縮の実装
  □ 動的ツールローディングの実装
  □ MCPサーバーキャッシュの実装
  □ トークン消費計測
```

### Phase 4: 並列実行 (Week 7-8)

```
目標: 独立タスクの並列化
成果物:
  - parallel_executor.py
  - task_dependency_graph.py

タスク:
  □ タスク依存関係グラフの実装
  □ 並列実行エンジンの実装
  □ 結果マージロジックの実装
  □ パフォーマンステスト
```

### Phase 5: 本番デプロイ (Week 9-10)

```
目標: 段階的ロールアウト
計画:
  - Day 1-3: カナリアデプロイ (5%)
  - Day 4-7: 監視・調整 (10%)
  - Day 8-10: 段階的拡大 (25%)
  - Day 11-14: 全面展開 (100%)

監視項目:
  □ レスポンス時間
  □ エラー率
  □ トークン消費量
  □ ユーザー満足度
```

---

## 8. 技術的知見

### 8.1 SDK バージョン要件

| パッケージ | バージョン | 備考 |
|-----------|-----------|------|
| agents | 0.7.0+ | nest_handoff_history対応 |
| chatkit | 1.6.0+ | SSEキープアライブ対応 |
| openai | 2.16.0+ | Responses API対応 |

### 8.2 重要な設定

```python
# v0.7.0でのデフォルト変更
RunConfig(
    nest_handoff_history=False,  # 明示的にTrueを指定
)

# 推論設定
ModelSettings(
    reasoning=Reasoning(
        effort="high",    # SEO/CRM分析向け
        summary="detailed",
    ),
)
```

### 8.3 パフォーマンス考慮事項

1. **MCPサーバー初期化**
   - 初回接続で ~2秒のオーバーヘッド
   - キャッシュで2回目以降は即時

2. **Handoff履歴圧縮**
   - 圧縮率80%が最適（過度な圧縮は品質低下）
   - 最新3ターンは常に保持

3. **並列実行**
   - asyncio.gatherで独立タスクを同時実行
   - 依存タスクは順次実行

### 8.4 監視メトリクス

```python
METRICS = {
    "handoff_count": "Handoff回数",
    "handoff_latency": "Handoffレイテンシ",
    "agent_selection_accuracy": "エージェント選択精度",
    "token_per_request": "リクエスト当たりトークン",
    "error_rate": "エラー率",
    "user_satisfaction": "ユーザー満足度",
}
```

---

## 付録

### A. ファイル構成

```
backend/app/infrastructure/chatkit/
├── router_agent.py           # Router Agent (新規)
├── specialist_agents.py      # 専門エージェント群 (新規)
├── handoff_manager.py        # Handoff管理 (新規)
├── context_filters.py        # コンテキストフィルタ (新規)
├── parallel_executor.py      # 並列実行 (新規)
├── seo_agent_factory.py      # 既存 (修正)
├── marketing_server.py       # 既存 (修正)
└── mcp_manager.py            # 既存 (修正)
```

### B. 環境変数

```bash
# マルチエージェント設定
MULTI_AGENT_ENABLED=true
ROUTER_MODEL=gpt-4.1-mini
SPECIALIST_MODEL=gpt-5-mini
HANDOFF_HISTORY_NESTED=true
MAX_HANDOFF_DEPTH=3
PARALLEL_EXECUTION_ENABLED=true
```

### C. 参考資料

- [OpenAI Agents SDK Documentation](https://openai.github.io/openai-agents-python/)
- [OpenAI Agents SDK Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [OpenAI Swarm GitHub](https://github.com/openai/swarm)
- [LangGraph Multi-Agent](https://docs.langchain.com/oss/python/langchain/multi-agent)

---

*Last Updated: 2026-02-04*
