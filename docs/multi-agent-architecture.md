# マルチエージェントアーキテクチャ設計書

> **Version**: 1.0.0
> **Date**: 2026-02-04
> **Status**: 設計完了・実装待ち

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
3. [アーキテクチャ設計](#3-アーキテクチャ設計)
4. [実装パターン](#4-実装パターン)
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

## 3. アーキテクチャ設計

### 3.1 推奨アーキテクチャ: Router + 専門エージェント

```
┌──────────────────────────────────────────────────────────────┐
│                     Router Agent (トリアージ)                 │
│  Model: gpt-4.1-mini (軽量・高速)                            │
│  Instructions: ~300 tokens                                   │
│  Tools: なし                                                 │
│  Role: 意図分類 → 適切なエージェントへのhandoff              │
└────────────────────────┬─────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬────────────────┐
         ▼               ▼               ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ SEO Agent   │  │ Ads Agent   │  │ CRM Agent   │  │Content Agent│
│             │  │             │  │             │  │             │
│ Tools:      │  │ Tools:      │  │ Tools:      │  │ Tools:      │
│ -GA4 (6)    │  │ -Meta Ads   │  │ -Zoho (9)   │  │ -WordPress  │
│ -GSC (10)   │  │  (20)       │  │ -Candidate  │  │  (28)       │
│ -Ahrefs(20) │  │ -GA4 (6)    │  │  Insight(4) │  │ -Web Search │
│ -Web Search │  │             │  │             │  │ -Code Int.  │
│             │  │             │  │             │  │             │
│ Total: 37   │  │ Total: 26   │  │ Total: 13   │  │ Total: 30   │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

### 3.2 エージェント責務分離

| エージェント | 責務 | ツール群 | トークン予算 |
|-------------|------|---------|-------------|
| **Router** | 意図分類・ルーティング | なし | 300T |
| **SEO Agent** | 検索順位最適化・競合分析 | GA4, GSC, Ahrefs, Web Search | 3,000T |
| **Ads Agent** | 広告パフォーマンス分析 | Meta Ads, GA4 | 2,200T |
| **CRM Agent** | 求職者管理・営業支援 | Zoho CRM, Candidate Insight | 1,200T |
| **Content Agent** | 記事作成・編集 | WordPress, Web Search, Code | 2,500T |

### 3.3 ルーティングロジック

```python
ROUTING_RULES = {
    "seo": [
        "検索順位", "SEO", "キーワード", "競合分析", "被リンク",
        "オーガニック", "GSC", "Ahrefs", "ランキング"
    ],
    "ads": [
        "広告", "Meta Ads", "Facebook", "Instagram", "ROAS", "CPA",
        "コンバージョン", "キャンペーン", "クリエイティブ"
    ],
    "crm": [
        "求職者", "候補者", "チャネル", "ステータス", "パイプライン",
        "成約", "ファネル", "担当者", "Zoho"
    ],
    "content": [
        "記事", "ブログ", "WordPress", "コンテンツ", "執筆",
        "編集", "下書き", "公開"
    ]
}
```

---

## 4. 実装パターン

### 4.1 Router Agent実装

```python
# backend/app/infrastructure/chatkit/router_agent.py

from agents import Agent, handoff, Runner, ModelSettings
from typing import Literal

class RouterAgentFactory:
    """意図分類専用の軽量エージェント"""

    def build_router(
        self,
        seo_agent: Agent,
        ads_agent: Agent,
        crm_agent: Agent,
        content_agent: Agent,
    ) -> Agent:
        return Agent(
            name="MarketingRouter",
            instructions="""
            ユーザーのリクエストを分析し、適切な専門エージェントにルーティング:

            - SEO・検索分析・競合調査 → transfer_to_seo_agent
            - 広告パフォーマンス・ROI分析 → transfer_to_ads_agent
            - 求職者・CRM・チャネル分析 → transfer_to_crm_agent
            - 記事・コンテンツ作成・編集 → transfer_to_content_agent

            複数の意図が混在する場合、主たる意図を判定してルーティング。
            """,
            model="gpt-4.1-mini",
            model_settings=ModelSettings(
                temperature=0.3,  # 確実な分類
                store=False,      # ルーター履歴は不要
            ),
            handoffs=[
                handoff(
                    seo_agent,
                    tool_name_override="transfer_to_seo_agent",
                    tool_description_override="SEO・検索分析・競合調査を担当"
                ),
                handoff(
                    ads_agent,
                    tool_name_override="transfer_to_ads_agent",
                    tool_description_override="広告パフォーマンス・ROI分析を担当"
                ),
                handoff(
                    crm_agent,
                    tool_name_override="transfer_to_crm_agent",
                    tool_description_override="求職者・CRM・チャネル分析を担当"
                ),
                handoff(
                    content_agent,
                    tool_name_override="transfer_to_content_agent",
                    tool_description_override="記事・コンテンツ作成・編集を担当"
                ),
            ],
        )
```

### 4.2 専門エージェント実装

```python
# backend/app/infrastructure/chatkit/specialist_agents.py

class SEOAgentFactory:
    """SEO分析専門エージェント"""

    def build_agent(self, mcp_servers: list) -> Agent:
        return Agent(
            name="SEOSpecialist",
            instructions="""
            SEO・検索分析の専門家。以下を担当:
            - GA4でのトラフィック分析
            - GSCでの検索クエリ・掲載順位分析
            - Ahrefsでの競合・被リンク分析
            - Web検索での最新情報取得

            分析結果は常にアクショナブルな提案を含めて回答。
            """,
            model="gpt-5-mini",
            model_settings=ModelSettings(
                reasoning=Reasoning(effort="high", summary="detailed"),
            ),
            tools=[WebSearchTool()],
            mcp_servers=mcp_servers,  # GA4, GSC, Ahrefs
        )


class CRMAgentFactory:
    """CRM・候補者分析専門エージェント"""

    def build_agent(self) -> Agent:
        return Agent(
            name="CRMAnalyst",
            instructions="""
            Zoho CRM + 議事録データの分析専門家。以下を担当:
            - 求職者の検索・詳細取得
            - チャネル別獲得分析
            - ステータス別ファネル分析
            - 競合リスク・緊急度評価
            - 担当者パフォーマンス分析

            データドリブンな洞察を提供。
            """,
            model="gpt-5-mini",
            model_settings=ModelSettings(
                reasoning=Reasoning(effort="medium"),
            ),
            tools=[
                *ZOHO_CRM_TOOLS,
                *CANDIDATE_INSIGHT_TOOLS,
            ],
        )
```

### 4.3 Sub-Agent as Tool パターン

複雑な分析タスクでサブエージェントをツールとして呼び出す：

```python
# backend/app/infrastructure/chatkit/sub_agent_tools.py

from agents import function_tool, RunContextWrapper, Runner

@function_tool(name_override="deep_competitive_analysis")
async def call_competitive_analysis_agent(
    ctx: RunContextWrapper,
    domain: str,
    analysis_depth: Literal["quick", "standard", "comprehensive"] = "standard",
) -> dict:
    """
    競合分析サブエージェントを呼び出し。
    Ahrefs + Web検索を組み合わせた詳細分析を実行。
    """
    sub_agent = Agent(
        name="CompetitiveAnalyzer",
        instructions=f"""
        ドメイン {domain} の競合分析を実行:
        1. Ahrefsでトラフィック・被リンク取得
        2. Web検索で最新ニュース・動向を調査
        3. 強み・弱みを分析
        4. アクションプランを提案

        分析深度: {analysis_depth}
        """,
        model="gpt-4.1-mini",
        tools=[ahrefs_mcp, WebSearchTool()],
    )

    result = await Runner.run(
        sub_agent,
        input=f"Analyze {domain}",
        max_turns=5,
    )

    return {
        "domain": domain,
        "analysis": result.final_output,
        "tokens_used": result.usage.total_tokens,
    }
```

### 4.4 並列実行パターン

```python
# backend/app/infrastructure/chatkit/parallel_executor.py

import asyncio
from typing import Any

class ParallelTaskExecutor:
    """独立タスクの並列実行"""

    async def execute_parallel(
        self,
        tasks: list[dict],
    ) -> list[dict]:
        """
        依存関係のないタスクを並列実行
        """
        # 依存関係チェック
        independent = [t for t in tasks if not t.get("blocked_by")]
        dependent = [t for t in tasks if t.get("blocked_by")]

        # 独立タスクを並列実行
        results = await asyncio.gather(*[
            self._execute_task(t) for t in independent
        ], return_exceptions=True)

        # 結果をマージ
        completed = {t["id"]: r for t, r in zip(independent, results)}

        # 依存タスクを順次実行
        for task in dependent:
            if all(completed.get(dep) for dep in task["blocked_by"]):
                result = await self._execute_task(task)
                completed[task["id"]] = result

        return list(completed.values())

    async def _execute_task(self, task: dict) -> Any:
        """個別タスクの実行"""
        agent = task["agent"]
        input_text = task["input"]
        return await Runner.run(agent, input=input_text)
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
