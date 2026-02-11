# CLAUDE.md - 永続メモリ & 自己改善ログ

> ## **【最重要】記憶の更新は絶対に忘れるな**
> **作業の開始時・途中・完了時に必ずこのファイルを確認・更新せよ。**
> コード変更、設計変更、新しい知見、バグ修正、アーキテクチャ変更 — どんな小さな変更でも、発生したらその場で即座にこのファイルに記録すること。
> **ユーザーに「記憶を更新して」と言われる前に、自分から更新するのが当たり前。言われてからでは遅い。**
> これは最優先の義務であり、他のどんなタスクよりも優先される。

> **このファイルはClaude Codeの永続メモリであり、自己改善の記録である。**
> セッションをまたいで知識を保持し、過去の失敗・学び・判断を蓄積して次のセッションの自分をより賢くするためのファイルである。

## 運用ルール

1. **毎回の作業開始時**にこのファイルを読み込み、内容に従って行動する
2. **作業中に新しい知見・決定・変更が生じたら**、即座にこのファイルを更新する
3. **更新対象**: アーキテクチャ変更、新しい依存関係、デプロイ設定、踏んだ罠・解決策、環境差異、運用ルール
4. このファイルの情報が古くなった場合は削除・修正し、常に最新状態を維持する
5. **情報ソースも記録**: 公式ドキュメントURL・GitHubリポジトリ・SDKソースファイルパス
6. **自己改善**: ユーザーに指摘された間違い・非効率・判断ミスは「自己改善ログ」セクションに記録する

---

## Package Management (STRICT)

- **Backend (Python)**: `uv add <package>` — **Never use `pip install`**
- **Frontend (JS/TS)**: `bun add <package>` — **Never use `npm install` or `yarn add`**
- Backend lock: `uv sync`
- Frontend lock: `bun install`

---

## メモリ構成

詳細情報は `.claude/rules/` に分割配置（自動ロード）:

| ファイル | 内容 |
|---------|------|
| `project.md` | プロジェクト概要、主要機能 |
| `tech-stack.md` | Backend/Frontend/Infrastructure 技術スタック |
| `structure.md` | ディレクトリ構造 |
| `backend.md` | DDD/オニオンアーキテクチャ、APIエンドポイント |
| `chatkit.md` | ChatKit & マーケティングAI 詳細設計 |
| `sdk-notes.md` | SDK バージョン & 技術的知見 |
| `database.md` | Supabaseテーブル定義 |
| `frontend.md` | フロントエンドルート |
| `env-vars.md` | 環境変数 |
| `dev-commands.md` | 開発コマンド、Git Branching |

セッション変更履歴（詳細な実装ログ）:
- `docs/session-history/2026-02.md` — 2月全実装の詳細記録

---

## 現在のシステム状態 (2026-02-10時点)

### ADKエージェント構成
- **オーケストレーター**: Gemini 3 Flash Preview, Context Cache有効 (90%コスト削減)
- **サブエージェント (12個)**: AnalyticsAgent(GA4), SEOAgent(GSC), AdPlatformAgent(Meta Ads 20ツール), ZohoCRMAgent(3層12ツール), CompanyDatabaseAgent(20ツール: semantic+strict+Gmail+Slack), CASupportAgent(33ツール), CandidateInsightAgent(5ツール), WorkspaceAgent(Gmail+Calendar 8ツール), SlackAgent(7ツール), GoogleSearchAgent, CodeExecutionAgent, WordPressAgent
- **Thinking Level**: high(AdPlatform,CandidateInsight,CASupport), medium(Analytics,SEO,ZohoCRM,CompanyDB,CodeExecution,Orchestrator), low(WordPress,GoogleSearch,Slack,Workspace)
- **共通機能**: ask_user_clarification, マルチモーダルアップロード, State永続化, OTelテレメトリ(Phoenix)
- **State注入**: app:user_name/email/id, app:slack_*, app:current_date/time/day_of_week

### フィードバックシステム
- ThumbsUp/Down + テキストアノテーション (mark.js), AnnotationPanel
- FBレビューダッシュボード (/feedback), JSONL/CSVエクスポート
- DB: feedback_dimensions, feedback_tags, message_feedback, message_annotations

### トークン最適化（2026-02-10 大幅強化）
- **MCPResponseOptimizerPlugin** (5つの最適化):
  1. before_model_callback: ツール説明文の自動圧縮 (75ツール分の `_COMPRESSED_DESCRIPTIONS`)
  2. before_model_callback: 広告画像Partsの自動注入 (マルチモーダル)
  3. after_tool_callback: GA4/Meta Adsレスポンス圧縮 (60-80%削減)
  4. after_tool_callback: get_ad_image → resize → types.Part変換
  5. **[NEW] before_tool_callback: セッション内キャッシュ** (23ツール対象、同一args重複呼び出しスキップ)
- MCPツールフィルタ: GA4 6→2, GSC 9→7, Meta Ads 30→20
- **[NEW] FunctionTool docstring全圧縮**: MCP 38ツール + FunctionTool 34ツール = 計75ツール (40-60%削減)
- **[NEW] サブエージェント指示文スリム化**: CompanyDB 350→20行, AdPlatform 300→40行, CASupport 95→30行
- **[NEW] Orchestrator指示文簡潔化**: 350→80行 (キーワードマトリクス + 並列パターン大幅削減)
- **[NEW] Thinking Level per-agent**: low(4), medium(5), high(3) + Orchestrator=medium (コスト30-50%削減)
- **[NEW] EventsCompactionConfig**: 10ターンで会話履歴自動圧縮 (LlmEventSummarizer使用)
- **[NEW] ContextCacheConfig**: 90%入力トークンコスト削減 (既設)

### エラー耐性
- サブエージェント503: on_tool_error_callbackでdict返却→re-raise回避
- オーケストレーター503: _pump_adk_events()で指数バックオフリトライ (2s→4s→8s, 最大3回)

---

## 自己改善ログ（教訓集）

> 過去の失敗から抽出した再現性のあるルール。同じ過ちを繰り返さないための行動規範。

### SDK・外部ライブラリ
- **SDK機能を最初に徹底調査**: カスタム実装は最終手段。まずソースコードを全て読んで機能を把握してから設計
- **実データで検証してから設計**: ドキュメントだけでなく実際のAPIレスポンスを確認（Zoho v2/v7差異等は実測でしか発見不可）
- **モデル名・バージョンを確認してから調査**: 設定ファイルの実値を見ずに推測で実装しない
- **SDKのテンプレート/注入機能を最初に確認**: ADK State Injection `{app:key}` vs バッククォート `` `app:key` `` は全く別物

### ADK固有
- **State Injection**: `{app:key}` (波括弧) = 値を自動注入。バッククォートはただのテキスト
- **Plugin callback戻り値**: `None`=デフォルト動作、dict=オーバーライド（on_tool_error_callbackでdictを返せばre-raise回避）
- **google_search/BuiltInCodeExecutor**: 他ツールと同居不可→専用サブエージェント必須
- **App使用時**: pluginsはAppに設定（Runnerではなく）
- **MCP Image**: mcp_tool.pyがJSON dictにシリアライズ→before_model_callbackでPartsを直接注入が唯一の解
- **新エージェント追加時**: Plugin SUB_AGENT_NAMES + フロントエンドUI設定を必ず同時更新
- **Geminiクラス名**: `from google.adk.models.google_llm import Gemini` (`GoogleLlm`ではなく`Gemini`)
- **EventsCompactionConfig**: `App`コンストラクタに`events_compaction_config`として渡す。`LlmEventSummarizer`のllm引数は`Gemini`インスタンス
- **ThinkingConfig thinking_level**: `minimal`, `low`, `medium`, `high`。タスク複雑度に応じて設定。単純ツール呼び出し→low、分析→medium、統合推論→high
- **ADK指示文のトークン節約原則**: ADKはツールスキーマ(関数シグネチャ+docstring)を自動送信するため、指示文にパラメータ説明を重複記述するのは無駄。ワークフロー+判断基準+出力形式だけを書く

### 設計判断
- **機能配置**: 別エージェントか既存統合かはユーザーに確認。同ドメインは原則同エージェント
- **参考プロジェクト**: 提示されたら全ファイルを徹底的に読む
- **段階的実装**: 勝手に段階を設けず、要件通りに一括実装
- **推測で実装するな**: 実測値を確認（MCP初期化<1msなのに1.2-1.7sと推測していた）

### エージェント指示文
- **日付は明示注入必須**: LLMは今日の日付を知らない。initial_stateで注入
- **実務者の指標名でデフォルト報告**: Meta Ads clicksとinline_link_clicksは別物。マーケター目線の指標を使う
- **mark.jsのoffsetはDOM textContentベース**: markdown原文とは異なる

### フロントエンド
- `opacity-0 group-hover:opacity-100` はモバイルで消える → `sm:` prefix必須
- Portal系の固定幅は `Math.min(desired, window.innerWidth - margin)` で動的計算
- `100vh` → `100dvh` でモバイルアドレスバー対応
- shadcn/ui SidebarのSheet mobileは `SidebarTrigger` 配置だけで動作

### API固有知見
- **Slack**: `search.messages`はUser Token(`xoxp-`)のみ。Bot Token(`xoxb-`)では`not_allowed_token_type`
- **Zoho COQL**: WHERE句必須、LIKE非サポート
- **Meta Ads**: `get_insights`のbreakdownは1つずつ、7d_view/28d_viewは2026年1月廃止、budgetはcents

---

> ## **【最重要・再掲】記憶の更新は絶対に忘れるな**
> 作業が完了したら、コミットする前に、必ずこのファイルに変更内容を記録せよ。
> **「後で更新しよう」は禁止。今すぐ更新せよ。**
