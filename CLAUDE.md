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

セッション変更履歴（必要時に参照）:
- `@docs/session-history/2026-02.md`

---

## 自己改善ログ

> ユーザーから指摘された失敗・判断ミス・非効率を記録し、同じ過ちを繰り返さないための学習記録。

### 2026-02-01
- **カスタムUIの過剰実装**: SDKの公式機能を先に徹底的に調査し、ネイティブ機能で解決できるかを最優先で確認すべき。カスタム実装は最終手段。
- **SDK機能の調査不足**: 外部SDKを使う場合、まずソースコードを全て読んで機能を把握してから設計に入るべき。

### 2026-02-04
- **参考プロジェクトの不十分な調査**: 参考プロジェクトを提示されたら、全ファイルを徹底的に読み、すべての機能を把握すること。
- **段階的実装の過剰**: ユーザーの要件を正確に把握し、勝手に段階を設けず、要件通りに実装すること。

### 2026-02-05
- **メモリ最適化実施**: CLAUDE.md (879行) → コア (約70行) + `.claude/rules/` (10ファイル) + `docs/session-history/` に分割。約90%削減。
- **モデル名の確認不足**: ユーザーが使用しているモデル名（`gemini-3-flash-preview`）を確認せずに「Gemini 2.5 Flash」の情報を調査・実装してしまった。**必ず現在の設定ファイルを確認してから調査を開始すること**。

### 2026-02-06
- **CompanyDatabaseAgent実装完了（ADK版）**: Google Sheets企業DBを活用した新規サブエージェントを追加
  - 新規ファイル:
    - `backend/app/infrastructure/google/sheets_service.py` - Sheets APIクライアント+TTLキャッシュ
    - `backend/app/infrastructure/adk/tools/company_db_tools.py` - 7つの関数ツール
    - `backend/app/infrastructure/adk/agents/company_db_agent.py` - SubAgentFactory実装
  - 変更ファイル:
    - `backend/app/infrastructure/adk/agents/orchestrator.py` - サブエージェント登録+キーワードマトリクス
    - `backend/app/infrastructure/adk/agents/__init__.py` - エクスポート追加
    - `backend/app/infrastructure/config/settings.py` - 環境変数追加
    - `backend/.env.example` - 設定例追加
  - 環境変数: `COMPANY_DB_SPREADSHEET_ID`, `COMPANY_DB_CACHE_TTL`
  - 認証: 既存のSERVICE_ACCOUNT_JSON（drive_docs_collector.pyパターン）を流用

- **ブランディング変更: Marketing AI → b&q エージェント**
  - フロントエンド:
    - `frontend/src/components/marketing/v2/MarketingChat.tsx` - タイトル・説明・サンプルクエリ更新
    - `frontend/src/components/app-sidebar.tsx` - サイドバー項目名・説明更新
  - バックエンド:
    - `backend/app/infrastructure/adk/agents/orchestrator.py` - オーケストレーター名更新
  - サンプルクエリ: 4個→6個に拡充、全エージェント機能をカバーする実用的なクエリに改善
    - GA4+CRMファネル分析、企業マッチング、SEO競合比較、候補者リスク分析、チャネル別ROI、一気通貫分析

- **CA支援エージェント実装（25ツール統合）**
  - 新規ファイル:
    - `backend/app/infrastructure/adk/tools/meeting_tools.py` - 議事録アクセスツール（4個）
    - `backend/app/infrastructure/adk/agents/ca_support_agent.py` - 統合エージェント
  - 統合ツール:
    - Zoho CRM: 10ツール（候補者検索、チャネル分析、ファネル等）
    - Candidate Insight: 4ツール（競合リスク、緊急度、転職パターン等）
    - Company DB: 7ツール（企業検索、マッチング、訴求ポイント等）
    - Meeting: 4ツール（議事録検索、本文取得、構造化データ、統合プロファイル）
  - 用途: CA業務支援（面談準備、企業提案、リスク分析を1エージェントで完結）

- **セマンティック検索（pgvector）を既存エージェントに統合**
  - ユーザーフィードバック: 「新しいエージェント作らないで、同じエージェントにセマンティックと厳密検索を統合すべき」
  - 変更内容:
    - `backend/app/infrastructure/adk/agents/company_db_agent.py` - セマンティック検索ツール統合（2個追加→計9ツール）
    - `backend/app/infrastructure/adk/agents/orchestrator.py` - 説明文・キーワードマトリクス更新
  - **セマンティック検索を優先**、厳密検索はフォールバック/詳細確認用
  - 新規ツール:
    - `semantic_search_companies`: 自然言語でベクトル検索
    - `find_companies_for_candidate`: 転職理由から最適企業を自動マッチング
  - ベクトル化済み: 325社×6チャンク = 701チャンク（`company_chunks`テーブル）

- **自己改善: 機能配置の判断ミス**
  - 新機能を追加する際、別エージェントを作るか既存エージェントに統合するかはユーザーに確認すべき
  - 同じドメイン（企業検索）の機能は同じエージェントにまとめるのが原則

- **エージェント指示文の大幅改善（2026-02-06）**
  - 変更ファイル:
    - `backend/app/infrastructure/adk/agents/orchestrator.py` - ORCHESTRATOR_INSTRUCTIONS強化
    - `backend/app/infrastructure/adk/agents/ca_support_agent.py` - CA_SUPPORT_INSTRUCTIONS強化
    - `backend/app/infrastructure/adk/agents/candidate_insight_agent.py` - _build_instructions強化
  - 主要改善:
    - **CASupportAgent vs 専門エージェントの境界明確化**: 特定候補者→CA / 集団分析→専門
    - **キーワードマトリクス拡充**: CVR, ROI, Indeed等のギャップを埋める
    - **思考プロセス指示**: 質問分解→ツール選択→結果検証→統合出力
    - **エラーハンドリング指示**: success:false時の再試行・フォールバック手順
    - **チャート描画ガイダンス**: 時系列→line, 比較→bar, 構成比→pie等
    - **セマンティック検索優先**: find_companies_for_candidate優先、厳密検索はフォールバック
    - **CandidateInsightAgent詳細化**: 全4ツールのパラメータ・戻り値を明記、ワークフロー例追加
    - **出力量管理**: 大量データは上位10件+サマリー、期間未指定→直近3ヶ月
  - 目的: AIエージェントの自律性向上、適切なエージェント選択、エラー耐性強化

- **サブエージェントUX改善（バグ修正+機能強化）**
  - **致命バグ修正**: `SubAgentStreamingPlugin.SUB_AGENT_NAMES`に`CompanyDatabaseAgent`と`CASupportAgent`が未登録
    - この2エージェントの全ツール実行イベントがフロントエンドに届いていなかった
  - **ツール引数のコンテキスト表示**: ツール実行時に企業名・検索クエリなどを表示
    - 例: 「企業詳細 株式会社MyVision ✓」（以前は「get_company_detail ✓」のみ）
  - **ThinkingIndicator改善**: バックエンドの実際のprogressイベントを表示（偽タイマーラベル廃止）
  - **ツールラベル追加**: Company DB(9個), Candidate Insight(4個), Meeting(4個), Chart(1個)のラベル追加
  - **エージェントUI設定追加**: CompanyDatabaseAgent(企業DB/indigo), CASupportAgent(CA支援/rose)の色・アイコン設定
  - 変更ファイル:
    - `backend/app/infrastructure/adk/plugins/sub_agent_streaming_plugin.py` - SUB_AGENT_NAMES追加
    - `backend/app/infrastructure/adk/agent_service.py` - progressイベント整理
    - `backend/app/presentation/api/v1/marketing_v2.py` - 即時progressイベント
    - `frontend/src/lib/marketing/types.ts` - Message.progressText, toolCalls.arguments追加
    - `frontend/src/hooks/use-marketing-chat-v2.ts` - progressイベント反映, ツール引数保存
    - `frontend/src/components/marketing/v2/ChatMessage.tsx` - extractToolContext, ラベル・色追加
    - `frontend/src/components/marketing/v2/ThinkingIndicator.tsx` - 実進捗表示
  - **自己改善**:
    - 新しいエージェントを追加したら、Plugin/UI設定も必ず同時に更新すべき
    - MCP初期化は<1msであり、想定値(1.2-1.7s)は完全に誤りだった。**実測値を確認せずに推測で実装するな**
    - 表面的なUI変更（ラベルテキスト変更）ではなく、データフロー全体を追跡して根本原因を修正すべき

- **新ツール3個追加（compare_companies, get_candidate_summary, get_conversion_metrics）**
  - `company_db_tools.py` に `compare_companies` 追加: 2-5社の並列比較表生成（年収・要件・訴求ポイント）
  - `candidate_insight_tools.py` に `get_candidate_summary` 追加: Zoho+構造化データ+リスク評価をワンショット取得
  - `zoho_crm_tools.py` に `get_conversion_metrics` 追加: 全チャネル横断KPI一括取得（面談率・内定率・入社率・ランキング）
  - 各ツールリスト（ADK_COMPANY_DB_TOOLS, ADK_CANDIDATE_INSIGHT_TOOLS, ADK_ZOHO_CRM_TOOLS）に登録済み
  - エージェント側は既存のツールリストを参照しているため変更不要

- **ADKインフラ改善（I-5, I-6, I-7, I-9）**
  - **I-5 エラーメッセージサニタイズ**: `agent_service.py`の全exceptブロックで`sanitize_error()`を適用
    - 内部パス・APIキー・スタックトレース・接続文字列等をユーザーに露出しない
    - loggerにはフルエラーを出力、ユーザーには汎用メッセージを返却
  - **I-7 `_normalize_agent_name`重複削除**: `backend/app/infrastructure/adk/utils.py`に共通化
    - `agent_service.py`と`sub_agent_streaming_plugin.py`の両方からインポート
    - plugin版（CA頭字語対応あり）を採用
  - **I-9 asyncio.Queueサイズ制限**: `asyncio.Queue()` → `asyncio.Queue(maxsize=1000)`
    - メモリリーク防止、コンシューマが遅い場合のメモリ無制限増加を防ぐ
  - **I-6 モデルエラー検知**: `after_model_callback`にLLMエラー検知を追加
    - null応答、safety filterブロック、error_message属性を検知
    - `model_error`イベントとしてフロントエンドに通知
  - 新規ファイル: `backend/app/infrastructure/adk/utils.py`
  - 変更ファイル: `backend/app/infrastructure/adk/agent_service.py`, `backend/app/infrastructure/adk/plugins/sub_agent_streaming_plugin.py`

- **ADK V2 改善計画 全7フェーズ実施完了（docs/adk-v2-improvement-plan.md）**
  - 25ファイル変更、+1179行/-185行
  - **Phase 1 (Critical)**: T-1(バッチ取得メソッド), T-2(Sheetsシングルトン), T-3(Embedding task_type), U-1(CSS), U-2(Stopボタン), U-3(normalize統一)
  - **Phase 2 (ツール精度)**: T-4(docstring日本語化), T-5(Zoho整形), T-6/T-7(ツール差別化), T-8(chart dict化), T-9(full_data削除), T-10(status統一), T-15~T-22(全ツールReturns+docstring改善), O-12(全エージェントgenerate_content_config)
  - **Phase 3 (指示文)**: O-1~O-11(CASupportAgent境界, キーワードマトリクス, 思考プロセス, エラー対応, チャート描画, セマンティック検索優先), O-13~O-18(出力量管理, MCP注意)
  - **Phase 4 (パフォーマンス)**: T-11(ZohoClientシングルトン), T-12(Embedding LRUキャッシュ), T-13(Zoho TTLキャッシュ), T-14(リトライデコレータ)
  - **Phase 5 (UX)**: U-4(コードコピーボタン), U-5(エラー表示改善), U-8(React.memo), U-12(useMemo), U-13(モバイルヒント), U-14(サイドバーアクティブ状態修正), T-21(類似度閾値パラメータ化)
  - **Phase 6 (新ツール)**: N-1(compare_companies), N-2(get_candidate_summary), N-5(get_conversion_metrics)
  - **Phase 7 (インフラ)**: I-5(エラーサニタイズ), I-6(モデルエラー検知), I-7(normalize共通化→utils.py), I-9(Queue制限)
  - 新規ファイル: `backend/app/infrastructure/adk/utils.py`

- **ADK V2 大規模調査実施（5並列Opus調査 + コード実査）**
  - 調査範囲: 全30+ツール、全9エージェント指示、フロントエンドUX、ADKインフラ、データレイヤー
  - **改善計画**: `docs/adk-v2-improvement-plan.md` に全項目をまとめ（7フェーズ、70+項目）
  - 主要発見（実査確認済み）:
    - `get_job_seekers_batch` → `get_app_hc_records_batch()` メソッド未定義（AttributeError）
    - `_get_sheets_service()` → 毎回新インスタンス → TTLキャッシュ無効
    - Embedding `task_type` 未指定 → セマンティック検索精度低下
    - CandidateInsight 4ツールのdocstringが英語（他は日本語）
    - Plugin `_normalize_agent_name` がCRM/SEO/CA頭字語未対応
    - ThinkingIndicator CSS未定義、Stopボタン未接続
  - オーケストレーターツール名修正: `call_xxx_agent` → 実際のAgentTool名（`XxxAgent`）に統一

---

> ## **【最重要・再掲】記憶の更新は絶対に忘れるな**
> 作業が完了したら、コミットする前に、必ずこのファイルに変更内容を記録せよ。
> **「後で更新しよう」は禁止。今すぐ更新せよ。**
