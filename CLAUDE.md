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
- **サブエージェント (10個)**: AnalyticsAgent(GA4), SEOAgent(GSC), AdPlatformAgent(Meta Ads 20ツール), ZohoCRMAgent(3層12ツール), CompanyDatabaseAgent(20ツール: semantic+strict+Gmail+Slack), CASupportAgent(31ツール), WorkspaceAgent(Gmail+Calendar 8ツール), SlackAgent(7ツール), GoogleSearchAgent, CodeExecutionAgent
- **共通機能**: ask_user_clarification, マルチモーダルアップロード, State永続化, OTelテレメトリ(Phoenix)
- **State注入**: app:user_name/email/id, app:slack_*, app:current_date/time/day_of_week

### フィードバックシステム
- ThumbsUp/Down + テキストアノテーション (mark.js), AnnotationPanel
- FBレビューダッシュボード (/feedback), JSONL/CSVエクスポート
- DB: feedback_dimensions, feedback_tags, message_feedback, message_annotations

### トークン最適化
- MCPResponseOptimizerPlugin: GA4/Zoho/Meta Adsレスポンス圧縮 (60-80%削減)
- MCPツールフィルタ: GA4 6→2, GSC 9→7, Meta Ads 30→20
- before_model_callback: ツール説明文の自動圧縮
- 広告画像: after_tool→before_model 2段パイプラインでマルチモーダル注入

### エラー耐性
- サブエージェント503: on_tool_error_callbackでdict返却→re-raise回避
- オーケストレーター503: _pump_adk_events()で指数バックオフリトライ (2s→4s→8s, 最大3回)

### 候補者管理ページ (2026-02-16追加)
- **一覧**: `/hitocari/candidates` — Zoho CRM (APP-hc) からCOQL+メモリ内フィルタでページネーション取得
  - フィルタ: ステータス(customer_status), チャネル(field14), 名前検索, ソート(登録日/更新日/ステータス)
  - URL search params + replaceState でブラウザバック対応
  - `count_meetings_by_zoho_record_ids()` で関連議事録数をバッチ集約
- **詳細**: `/hitocari/candidates/[id]` — Zoho全フィールド + structured_outputs + 関連議事録
  - 2カラムレイアウト: 左=基本情報+構造化データ, 右=関連議事録+AIマッチング
- **求人マッチング**: `POST /api/v1/candidates/{record_id}/job-match`
  - ADK JobMatchAgent (Gemini 3 Flash) がセマンティック検索+分析を実行
  - フォールバック: ADKエージェント失敗時は `find_companies_for_candidate()` 直接呼出し
  - 候補者プロフィール = Zohoデータ + 面談構造化データ(transfer_reasons等) を統合
  - 結果: JSON形式 (analysis_text + recommended_companies[])
- **Backend**: `candidates.py` router → use cases (list, detail, meetings, match) → ZohoClient.list_candidates_paginated()
- **Frontend**: `api.ts` に CandidateSummary/CandidateDetail/CompanyMatch/JobMatchResult interfaces追加
- **サイドバー**: `app-sidebar.tsx` "候補者管理" enabled: true

### 議事録一覧ページネーション
- `meeting_documents_enriched` VIEW: `is_structured`, `zoho_sync_status` を計算列で持つ
- 全タブ1クエリ: `count="exact"` + `.range()` でSQL側フィルタ+ページネーション
- マイグレーション: `0023_add_meeting_documents_enriched_view.sql`
- ブラウザバック対応: URL search params (`?tab=sync_failed&page=2`) + `replaceState`

### Zoho自動同期 名前マッチング (2026-02-11改善)
- **extract_from_title**: `_TIME_PREFIX_RE` でJP時間プレフィックス事前除去 (修正前56%→修正後74%正常抽出)
- **`~`→`[~〜～]`**: 全角チルダ`〜`/`～`もlookbehind対象に追加
- **ダブルスペース対応**: regex中の `[\s　]` → `[\s　]+` で複数スペース許容
- **CandidateTitleMatcher**: `_normalize_spaceless()` で全スペース除去比較を追加
- **is_exact_match**: 2段階比較 (1.標準正規化 → 2.スペース除去比較)
- **get_search_variations**: 名前バリエーション生成 (raw, normalized, spaceless)
- **search_app_hc_by_exact_name**: 多バリエーション×equals → starts_withフォールバック
- **auto_process**: 複数Zohoヒット時は正規化マッチで1件に絞り込み
- **実データ分析**: Zoho名はスペースあり/なし混在。`向井直也`(spaceless)で検索ヒット確認済み
- **全角括弧対応**: `（仮）石岡様` → regex除外+`_NOISE_PREFIX_RE`で`（仮）`除去。Zoho API 400を回避
- **残課題**: 姓のみタイトル (`田中様_初回面談`) は26%存在→データ制約で改善不可
- **残課題**: Zoho重複レコード（同名別ID: 向井直也×2, 大石周×2）→正しくスキップするが手動対応必要

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
- **Zoho Search API**: `equals`はスペース含む完全一致。日本語名は`equals`+`starts_with`フォールバック+名前バリエーション(spaceless等)で検索精度向上
- **Meta Ads**: `get_insights`のbreakdownは1つずつ、7d_view/28d_viewは2026年1月廃止、budgetはcents
- **PostgREST NOT IN**: 大量UUIDのNOT INフィルタはURL長制限で400エラー。VIEWで計算列を使うのが正解

---

> ## **【最重要・再掲】記憶の更新は絶対に忘れるな**
> 作業が完了したら、コミットする前に、必ずこのファイルに変更内容を記録せよ。
> **「後で更新しよう」は禁止。今すぐ更新せよ。**
