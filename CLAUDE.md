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

- **ADK マルチモーダル + Google検索 + コード実行 実装**
  - **Phase 1: Google検索 & コード実行サブエージェント**
    - 新規ファイル:
      - `backend/app/infrastructure/adk/agents/google_search_agent.py` - Google検索専用サブエージェント（`google_search`ツール使用、他ツール同居不可）
      - `backend/app/infrastructure/adk/agents/code_execution_agent.py` - コード実行専用サブエージェント（`BuiltInCodeExecutor`使用、他ツール同居不可、`build_agent()`オーバーライド）
    - 変更ファイル:
      - `backend/app/infrastructure/adk/agents/orchestrator.py` - サブファクトリー登録、キーワードマトリクス追加、サブエージェント説明追加
      - `backend/app/infrastructure/adk/agents/__init__.py` - エクスポート追加
      - `backend/app/infrastructure/adk/plugins/sub_agent_streaming_plugin.py` - `SUB_AGENT_NAMES`追加
  - **Phase 2: コード実行イベント処理**
    - Backend:
      - `agent_service.py` - `executable_code`/`code_execution_result`パート処理（partial=True/False両方）
      - `marketing_v2.py` - `code_execution`/`code_result`イベント蓄積
    - Frontend:
      - `types.ts` - `CodeExecutionEvent`, `CodeResultEvent`, `CodeExecutionActivityItem`, `CodeResultActivityItem`追加
      - `use-marketing-chat-v2.ts` - `processEvent`にケース追加
      - `ChatMessage.tsx` - `CodeBlock`再利用のコード表示、実行結果表示（成功=緑、エラー=赤）、新エージェントUI設定追加
  - **Phase 3: マルチモーダルファイルアップロード**
    - Backend:
      - `marketing_v2.py` - `FileAttachment`スキーマ、バリデーション（10MB/file, 20MB合計, 5ファイル, MIME制限）
      - `agent_service.py` - `attachments`パラメータ追加、`types.Part.from_bytes()`でマルチモーダルContent構築
    - Frontend:
      - `types.ts` - `FileAttachment`型、`Message.attachments`フィールド追加
      - `Composer.tsx` - Paperclipボタン、ファイルプレビューチップ、バリデーション
      - `use-marketing-chat-v2.ts` - `fileToBase64()`ヘルパー、`sendMessage(content, files?)`シグネチャ変更
      - `ChatMessage.tsx` - ユーザーメッセージに添付ファイルバッジ表示
  - **ADK制約**: `google_search`と`BuiltInCodeExecutor`は他ツールと同居不可 → 専用サブエージェント必須

- **UI改善: Sparklesアイコン → Layersアイコンに変更**
  - `MarketingChat.tsx` - ブランドアイコンをLayers（マルチレイヤーデータ統合）に変更
  - `ChatMessage.tsx` - `get_appeal_points`ツールアイコンをTargetに変更
  - サジェストカードにタグラベル追加、ArrowRightホバーアフォーダンス追加

- **ADK user:/app: State永続化（既存Supabaseテーブル拡張）**
  - **目的**: エージェントがユーザー嗜好・学習結果を会話をまたいで保持
  - **方式**: `marketing_conversations.metadata` JSONBに`user_state`/`app_state`を追加保存。新テーブル・asyncpg不要
  - 変更ファイル:
    - `backend/app/infrastructure/adk/agent_service.py`:
      - `stream_chat()`に`initial_state`パラメータ追加
      - `create_session(state=initial_state)`でState復元
      - ターン終了時に`session.state`から`user:`/`app:`プレフィックスを分離抽出
      - `_context_items`イベントに`user_state`/`app_state`を含めてyield
    - `backend/app/presentation/api/v1/marketing_v2.py`:
      - 最新会話の`metadata.user_state`をロード→`initial_state`としてagent_serviceに渡す
      - `_context_items`受信時に`user_state`/`app_state`もmetadataに保存
  - **バグ修正**: `user_id="default"`ハードコード→実ユーザーID(`user_id`パラメータ)に統一（全6箇所）
  - **データフロー**: 最新会話metadata→initial_state→InMemorySession→ツール内でstate読み書き→ターン終了時にmetadataへ保存
  - **制限**: `app:` Stateは会話単位保存（グローバル共有には将来的に専用テーブルが必要）

- **ToolContext.state 書き込み実装（全5ツールファイル・10関数）**
  - `company_db_tools.py`: `search_companies`(user:recent_company_searches), `get_company_detail`(user:viewed_companies), `match_candidate_to_companies`(user:matched_candidates)
  - `semantic_company_tools.py`: `semantic_search_companies`(user:semantic_queries), `find_companies_for_candidate`(user:candidate_company_matches)
  - `zoho_crm_tools.py`: `search_job_seekers`(user:recent_candidate_searches), `get_job_seeker_detail`(user:viewed_candidates)
  - `candidate_insight_tools.py`: `get_candidate_summary`(user:analyzed_candidates), `generate_candidate_briefing`(user:briefed_candidates)
  - `meeting_tools.py`: `get_candidate_full_profile`(user:profiled_candidates)
  - **全ツール共通パターン**: `tool_context: ToolContext = None`パラメータ追加、state書き込みはreturn前、リスト上限付き(20-30件)、try/exceptで安全にラップ
  - **ADK仕様準拠**: パラメータ名`tool_context`は必須（ADKが`inspect.signature`で自動検出・注入）、ネストされた更新は親オブジェクトを再代入

- **GoogleWorkspaceAgent実装（Gmail + Calendar 読み取り）**
  - **目的**: ユーザーのGmailとGoogleカレンダーにサービスアカウントのドメイン全体委任でアクセス
  - **認証**: 既存の `SERVICE_ACCOUNT_JSON` + `subject=user_email` パターン（drive_docs_collector.py流用）
  - **スコープ**: `gmail.readonly`, `calendar.readonly`（Admin Consoleで委任設定済み）
  - 新規ファイル:
    - `backend/app/infrastructure/google/workspace_service.py` - Per-user Gmail/Calendar APIサービス（TTL 50分キャッシュ、スレッドセーフシングルトン）
    - `backend/app/infrastructure/adk/tools/workspace_tools.py` - 8ツール（Gmail 4 + Calendar 4）
    - `backend/app/infrastructure/adk/agents/workspace_agent.py` - SubAgentFactory実装
  - 変更ファイル:
    - `backend/app/infrastructure/adk/agents/orchestrator.py` - サブエージェント登録、キーワードマトリクス追加
    - `backend/app/infrastructure/adk/agents/__init__.py` - エクスポート追加
    - `backend/app/infrastructure/adk/plugins/sub_agent_streaming_plugin.py` - SUB_AGENT_NAMES追加
    - `backend/app/presentation/api/v1/marketing_v2.py` - `app:user_email` をinitial_stateに注入
    - `frontend/src/components/marketing/v2/ChatMessage.tsx` - Workspace UI設定（Mail/Calendarアイコン、赤/オレンジ）
  - ツール一覧:
    - `search_gmail`: Gmail検索構文サポート
    - `get_email_detail`: メール本文取得（3000文字上限）
    - `get_email_thread`: スレッド全体取得（1000文字/msg）
    - `get_recent_emails`: 直近N時間のメール一覧
    - `get_today_events`: 今日の予定（JST）
    - `list_calendar_events`: 期間指定イベント一覧
    - `search_calendar_events`: キーワードでイベント検索
    - `get_event_detail`: イベント詳細（参加者・Meet URL等）
  - **State注入**: `marketing_v2.py` で `initial_state["app:user_email"] = context.user_email` を追加
  - **設計判断**: Per-userサービスインスタンス（SheetsServiceと異なり、subject がユーザーごとに異なるため）

- **企業DB・CA支援エージェントにGmailツール4個を統合**
  - `workspace_tools.py` に `ADK_GMAIL_TOOLS` / `ADK_CALENDAR_TOOLS` サブリスト追加（`ADK_WORKSPACE_TOOLS = GMAIL + CALENDAR`）
  - `company_db_agent.py` に `ADK_GMAIL_TOOLS` をインポート・統合（9→13ツール）
  - `ca_support_agent.py` に `ADK_GMAIL_TOOLS` をインポート・統合（27→31ツール）
  - 両エージェントの指示文に**メールによる企業情報補完**の説明を追加:
    - 企業DBにない情報（採用担当とのやり取り、条件交渉経緯、非公開求人、選考フィードバック）をメールから取得
    - ツール選択マトリクスにGmail系4ツール追加
    - ワークフロー例に「DB情報+メール生情報の統合」パターン追加

- **サンプルクエリ大幅拡充（6個→29個プール、日替わり6個表示）**
  - `MarketingChat.tsx` の `SUGGESTIONS` を `ALL_SUGGESTIONS` (29個) + `pickSuggestions()` に変更
  - カバー範囲: GA4, GSC, SEO, Meta広告, CRM, 企業DB, CA支援, Gmail, カレンダー, Web検索, コード実行, WordPress, 統合分析
  - **日替わりシャッフル**: 日付ベースのシードで毎日異なる6個を表示（セッション内は安定）
  - **タグ多様性保証**: まず異なるタグの候補を優先選出し、同じ分野に偏らないようにする
  - 説明文更新: 「GA4・CRM・企業DB・Gmail・カレンダーを横断して分析・提案」
  - Lucideアイコン追加import: Mail, Calendar, Globe, Code2, Megaphone, FileText

- **Zoho CRM 3層アーキテクチャ全面書き換え**
  - **目的**: 全CRMモジュール（58個）に動的アクセス可能に。旧実装はjobSeekerモジュールの7-17フィールドしかアクセスできなかった
  - **Tier 1 (メタデータ発見)**: 新規3ツール
    - `list_crm_modules`: 全モジュール一覧（レコード件数付き可）
    - `get_module_schema`: フィールド構造（API名・ピックリスト値・ルックアップ先、296フィールド対応）
    - `get_module_layout`: レイアウト（セクション構造・フィールド配置）
  - **Tier 2 (汎用クエリ)**: 新規4ツール
    - `query_crm_records`: 任意モジュールのCOQL検索（SELECT/WHERE/ORDER BY/LIMIT）
    - `aggregate_crm_data`: 任意モジュールのGROUP BY集計
    - `get_record_detail`: 1レコード全フィールド取得（全298フィールド返却確認済み）
    - `get_related_records`: 関連リスト・サブフォーム取得
  - **Tier 3 (専門分析)**: 既存5ツール維持（バグ修正済み）
    - `analyze_funnel_by_channel`, `trend_analysis_by_period`, `compare_channels`, `get_pic_performance`, `get_conversion_metrics`
  - **削除**: 6ツール（Tier 2で代替）
    - `get_channel_definitions`, `search_job_seekers`, `get_job_seeker_detail`, `get_job_seekers_batch`, `aggregate_by_channel`, `count_job_seekers_by_status`
  - **バグ修正**: `_format_job_seeker_detail`のfield19→customer_statusバグ修正（関数自体削除、Tier 2のget_record_detailが全フィールド返却）
  - 変更ファイル:
    - `backend/app/infrastructure/zoho/client.py` - 24h TTLメタデータキャッシュ、list_modules/list_fields_rich/get_layouts/get_record/get_related_records/generic_coql_query追加
    - `backend/app/infrastructure/adk/tools/zoho_crm_tools.py` - 全面書き換え（11→12ツール、3層構造）
    - `backend/app/infrastructure/adk/agents/zoho_crm_agent.py` - 指示文更新（3層ツール体系・COQL Tips）
    - `backend/app/infrastructure/adk/agents/ca_support_agent.py` - ツール一覧・ワークフロー例更新
    - `backend/app/infrastructure/adk/agents/orchestrator.py` - サブエージェント説明・キーワードマトリクス更新
    - `frontend/src/components/marketing/v2/ChatMessage.tsx` - ツールアイコン・ラベル・コンテキスト表示更新
  - **API検証**: 21テスト中20成功、1件（get_related_records）はv7→v2 API切替で修正完了
  - **Zoho v7 API知見**: 関連レコードAPIはv7ではfields必須パラメータ、v2では不要。サブフォーム全フィールド取得にはv2を使用

- **自己改善: 実データ検証の重要性**
  - ドキュメント調査だけでなく、実際のAPIを呼んでレスポンスを確認してから設計すべき
  - Zoho API v2とv7の挙動差異（必須パラメータの違い等）は実測でしか発見できない

- **SlackAgent実装（Slack検索・チャンネル履歴）**
  - **目的**: Slackチャンネル（パブリック+プライベート、DM除外）のメッセージ検索をAIエージェント経由で実現
  - **認証**: User Token (`xoxp-`) + Bot Token (`xoxb-`) のハイブリッド
    - `search.messages`（全文検索）= User Token必須（Slack API仕様制限）
    - `conversations.history/replies/list` = Bot Token
  - **依存追加**: `slack-sdk>=3.39.0` (`uv add slack-sdk`)
  - 新規ファイル:
    - `backend/app/infrastructure/slack/__init__.py` - パッケージ初期化
    - `backend/app/infrastructure/slack/slack_service.py` - Slack APIクライアント（スレッドセーフシングルトン、チャンネル/ユーザーキャッシュTTL 1時間）
    - `backend/app/infrastructure/adk/tools/slack_tools.py` - 6ツール
    - `backend/app/infrastructure/adk/agents/slack_agent.py` - SlackAgentFactory
  - 変更ファイル:
    - `backend/app/infrastructure/config/settings.py` - `slack_bot_token`, `slack_user_token` 追加
    - `backend/app/infrastructure/adk/agents/orchestrator.py` - サブエージェント登録、キーワードマトリクス追加
    - `backend/app/infrastructure/adk/agents/__init__.py` - エクスポート追加
    - `backend/app/infrastructure/adk/plugins/sub_agent_streaming_plugin.py` - `SUB_AGENT_NAMES`追加
    - `backend/.env.example` - Slack環境変数追加
    - `frontend/src/components/marketing/v2/ChatMessage.tsx` - UI設定（fuchsia/purple、MessageSquareアイコン）
  - ツール一覧:
    - `search_slack_messages`: 全文横断検索（in:, from:, after: 構文サポート）
    - `get_channel_messages`: 特定チャンネル直近N時間の履歴
    - `get_thread_replies`: スレッド全返信取得
    - `list_slack_channels`: チャンネル一覧（im/mpim除外強制）
    - `search_company_in_slack`: 企業名検索→Fee・条件構造化
    - `search_candidate_in_slack`: 候補者名検索→進捗構造化
  - 環境変数: `SLACK_BOT_TOKEN`, `SLACK_USER_TOKEN`
  - **Slack API制約**: `search.messages`はUser Token(`xoxp-`)のみ対応、Bot Token(`xoxb-`)では`not_allowed_token_type`エラー

- **b&q Hub部門追加: 業務推進室（2026-02-07）**
  - ユーザー要望: 「サイドバーと最初のページ（ダッシュボード）に新部門として業務推進室を追加」
  - 変更ファイル:
    - `frontend/src/components/app-sidebar.tsx` - `teamItems` に `業務推進室`（`/operations`）を追加、`operations` 用メニューを追加
    - `frontend/src/app/page.tsx` - サービスカードに `業務推進室` を追加、クイックアクションにも導線を追加
    - `frontend/src/app/operations/page.tsx` - 新規部門トップページを追加
    - `frontend/src/app/layout.tsx` - metadata description を `業務推進室` 含む内容に更新

- **b&q Agent Analytics ダッシュボード実装（2026-02-07）**
  - **目的**: `/operations` ページをADKエージェント観測・分析ダッシュボードに変換
  - **アーキテクチャ**: Phoenix + 独自UI ハイブリッド
    - ADK OTelスパン → BatchSpanProcessor × 2（Supabase + Phoenix OTLP）
    - 独自UI (`/operations`): 日常モニタリング（KPI、トレース、ツール統計、トークンコスト）
    - Phoenix UI (`:6006`): 深い分析（スパンウォーターフォール、評価）
  - **Phase 1 - データ収集基盤**:
    - 依存追加: `arize-phoenix`, `openinference-instrumentation-google-adk`, `opentelemetry-exporter-otlp-proto-http`
    - DBマイグレーション: `supabase/migrations/0021_add_agent_traces.sql`
      - `agent_traces` テーブル（trace_id, user_email, tokens, sub_agents_used[], tools_used[]）
      - `agent_spans` テーブル（span_id, operation_name, agent_name, tool_name, attributes JSONB）
      - `agent_daily_summary`, `agent_tool_summary` ビュー
    - カスタムSpanExporter: `backend/app/infrastructure/adk/telemetry/supabase_exporter.py`
      - OTel SpanExporter継承、ADK属性パース、Supabaseバッチ書き込み
      - invocationルートスパン検出 → agent_traces集約
    - OTel初期化: `backend/app/infrastructure/adk/telemetry/setup.py`
      - SupabaseSpanExporter + OTLPSpanExporter（Phoenix）の2つを並列登録
      - `GoogleADKInstrumentor().instrument()` でOpenInference計装
    - 設定追加: `settings.py` に `adk_telemetry_enabled`, `phoenix_endpoint`
    - agent_service.py: OTelスパンに `user.email`, `user.id`, `conversation.id` 注入
    - marketing/agent_service.py: テレメトリ初期化呼び出し追加
  - **Phase 2 - バックエンドAPI**:
    - `backend/app/presentation/api/v1/agent_analytics.py` - 8 GETエンドポイント
      - `/overview`, `/traces`, `/traces/{trace_id}`, `/tool-usage`, `/agent-routing`, `/token-usage`, `/user-usage`, `/errors`
    - 認証: `require_marketing_context` 流用
  - **Phase 3 - フロントエンド**:
    - 型定義: `frontend/src/lib/operations/types.ts`
    - フック: `frontend/src/hooks/use-agent-analytics.ts`（8カスタムフック、トークンキャッシュ付き）
    - コンポーネント（10個、全て新規）:
      - `PeriodFilter.tsx` - Today/7d/30d/All切替
      - `OverviewCards.tsx` - KPIカード4枚
      - `TraceList.tsx` - トレース一覧テーブル（ページネーション、Phoenix UIリンク）
      - `TraceDetail.tsx` - Sheet詳細表示
      - `SpanTree.tsx` - 再帰スパンツリー+ウォーターフォール
      - `ToolUsageChart.tsx` - recharts棒グラフ+テーブル
      - `AgentRoutingChart.tsx` - recharts円グラフ+棒グラフ
      - `TokenUsageChart.tsx` - recharts AreaChart+コストサマリー
      - `UserUsageTable.tsx` - ユーザー別使用状況テーブル
      - `ErrorList.tsx` - エラー追跡一覧
    - メインページ: `frontend/src/app/operations/page.tsx` 全面書き換え
    - サイドバー: `app-sidebar.tsx` - 「業務推進室」→「Agent Analytics」に変更、Activityアイコン
  - 新規ファイル（15）:
    - `supabase/migrations/0021_add_agent_traces.sql`
    - `backend/app/infrastructure/adk/telemetry/__init__.py`
    - `backend/app/infrastructure/adk/telemetry/supabase_exporter.py`
    - `backend/app/infrastructure/adk/telemetry/setup.py`
    - `backend/app/presentation/api/v1/agent_analytics.py`
    - `frontend/src/lib/operations/types.ts`
    - `frontend/src/hooks/use-agent-analytics.ts`
    - `frontend/src/components/operations/` 以下10コンポーネント
  - 変更ファイル（5）:
    - `backend/app/infrastructure/config/settings.py`
    - `backend/app/infrastructure/marketing/agent_service.py`
    - `backend/app/infrastructure/adk/agent_service.py`
    - `backend/app/presentation/api/v1/__init__.py`
    - `frontend/src/components/app-sidebar.tsx`
  - 環境変数: `ADK_TELEMETRY_ENABLED`, `PHOENIX_ENDPOINT`, `NEXT_PUBLIC_PHOENIX_URL`

- **GA4 run_report ツール最適化（2026-02-07）**
  - **目的**: GA4 MCPレスポンスのトークン消費を60-70%削減
  - **MCPレスポンス圧縮プラグイン**: `backend/app/infrastructure/adk/plugins/mcp_response_optimizer.py`
    - `after_tool_callback` でGA4 `run_report` レスポンスをインターセプト
    - 冗長なネストJSON（`dimension_values`/`metric_values`）→ パイプ区切りcompact table
    - 対象: `run_report`, `run_realtime_report`, `run_pivot_report`
    - 200行上限、圧縮率ログ出力
  - **プラグイン登録**: `agent_service.py` に `MCPResponseOptimizerPlugin` 追加（`SubAgentStreamingPlugin` と並列）
  - **AnalyticsAgent指示文強化**: `analytics_agent.py`
    - `limit` 必須化（デフォルト50）、`order_bys` 必須化
    - dimension組み合わせの注意（date × 高カーディナリティ禁止）
    - `dimension_filter` でノイズイベント除外
    - 主要dimension/metric一覧拡充（14 dimensions、15 metrics）
    - サイト固有CVイベント情報（Thanks_All, 法人向け問い合わせ完了等）
    - 効率的なクエリパターン5例
  - 変更ファイル:
    - `backend/app/infrastructure/adk/plugins/mcp_response_optimizer.py` - **新規**
    - `backend/app/infrastructure/adk/plugins/__init__.py` - エクスポート追加
    - `backend/app/infrastructure/adk/agent_service.py` - プラグイン登録
    - `backend/app/infrastructure/adk/agents/analytics_agent.py` - 指示文強化

- **MCPツール定義最適化（入力トークン削減）**
  - **目的**: Gemini APIリクエストのツール定義が~10,000入力トークンを消費 → 大幅削減
  - **McpToolset tool_filter**: 不要ツールを除外してツール数を削減
    - GA4: 6→2ツール（`run_report`, `run_realtime_report`のみ保持）
    - GSC: 9→7ツール（`list_properties`, `get_site_details`, `batch_url_inspection`除外）
    - 合計15→9ツール（40%削減）
  - **before_model_callback**: 残存ツールの冗長な説明文を圧縮
    - `run_report`の巨大なHints/Examples/Notesセクションを除去
    - 事前定義の簡潔な説明文で置換（エージェント指示文に詳細は記載済み）
    - その他MCPツールも200文字超の説明はHints/Notes/Examplesを自動ストリップ
  - 変更ファイル:
    - `backend/app/infrastructure/adk/mcp_manager.py` - `GA4_TOOL_FILTER`, `GSC_TOOL_FILTER`定数追加、`tool_filter`パラメータ適用
    - `backend/app/infrastructure/adk/plugins/mcp_response_optimizer.py` - `before_model_callback`追加（ツール説明圧縮）
  - **ADK知見**: `McpToolset(tool_filter=List[str])` でツール名リストによるフィルタリング。`ToolPredicate`（callable）も使用可能
  - **ADK知見**: `before_model_callback`で`llm_request.config.tools[i].function_declarations[j].description`を直接変更可能

- **Zoho CRMツール最適化（トークン大幅削減）**
  - **目的**: get_module_schemaレスポンス(~29,140トークン/回)を中心にZoho関連トークンを60-80%削減
  - **3段階最適化**:
    1. **ツールレベル（zoho_crm_tools.py）**:
       - `get_module_schema`: picklist値を20件に制限（500+→20）、複合値の重複排除（`「X」×「Y」`形式）
       - `get_record_detail`: null/空フィールドを除去（296→~150フィールド、50%削減）
       - `_clean_lookup_fields(strip_empty=True)` 追加
       - `_deduplicate_picklist_values()` 新規関数
       - `_MAX_PICKLIST_VALUES = 20` 定数
    2. **プラグインレベル（mcp_response_optimizer.py）**:
       - `before_model_callback` にZoho 12ツールの圧縮説明文を追加
       - `MCP_TOOL_NAMES` → `COMPRESSIBLE_TOOL_NAMES` にリネーム（5→21ツール）
       - `_COMPRESSED_DESCRIPTIONS` にZoho Tier 1/2/3 全12ツールを追加
    3. **指示文レベル**:
       - `CASupportAgent`: 4,446→1,685文字（**62%削減**）。ツール個別テーブルをグループ一覧に集約、ワークフロー例を3パターンに圧縮
       - `ZohoCRMAgent`: ツールテーブル→箇条書き、COQL Tipsを簡潔化
  - 変更ファイル:
    - `backend/app/infrastructure/adk/tools/zoho_crm_tools.py` - picklist圧縮、null除去
    - `backend/app/infrastructure/adk/plugins/mcp_response_optimizer.py` - Zoho description圧縮
    - `backend/app/infrastructure/adk/agents/zoho_crm_agent.py` - 指示文簡潔化
    - `backend/app/infrastructure/adk/agents/ca_support_agent.py` - 指示文62%削減

- **ADK Context Caching実装（Gemini Explicit Cache: 入力トークン90%コスト削減）**
  - **目的**: ADKの毎LLMコールで再送信されるsystem_instruction+tools+会話履歴をGeminiサーバー上にキャッシュし、入力トークンコストを90%削減
  - **仕組み**:
    1. 初回LLMコール: フィンガープリント（SHA256）のみ生成
    2. 2回目: フィンガープリント一致 + トークン数 > min_tokens → Gemini CachedContent作成
    3. 3回目以降: キャッシュ再利用（system_instruction/tools/cached_contentsをリクエストから除去、`cached_content=cache_name`をセット）
  - **キャッシュ管理**: `GeminiContextCacheManager`（ADK内蔵）がライフサイクル管理（作成・検証・有効期限・クリーンアップ）
  - 変更ファイル:
    - `backend/app/infrastructure/config/settings.py` - キャッシュ設定4項目追加
    - `backend/app/infrastructure/adk/agent_service.py` - `Runner(agent=...)` → `Runner(app=App(...))` に変換、ContextCacheConfig適用
  - 環境変数:
    - `ADK_CONTEXT_CACHE_ENABLED`: キャッシュ有効/無効（デフォルト: `true`）
    - `ADK_CACHE_TTL_SECONDS`: キャッシュ有効期間（デフォルト: `1800` = 30分）
    - `ADK_CACHE_MIN_TOKENS`: キャッシュ作成の最小トークン数（デフォルト: `2048`）
    - `ADK_CACHE_INTERVALS`: キャッシュを再作成するまでの呼び出し回数（デフォルト: `10`）
  - **ADK知見**:
    - `ContextCacheConfig`は`@experimental`（将来変更の可能性あり）
    - `App`オブジェクト必須（`Runner(agent=..., app_name=...)`では不可）
    - `App`使用時はpluginsを`App`に設定（`Runner`ではなく）
    - `static_instruction`はADK v1.22.1には存在しない
    - OpenAI: 50%割引 vs Gemini: 90%割引（Explicit Cache）
    - Gemini Implicit Cache（自動、設定不要、90%割引）も別途存在するが、ADKのContext CacheはExplicit

- **Phoenix キャッシュトークン表示パッチ**
  - OpenInference instrumentorが`cached_content_token_count`を`llm.token_count.prompt_details.cache_read`にマッピングしていなかった
  - `telemetry/setup.py`に`_patch_cache_token_attributes()`を追加し、モンキーパッチで補完
  - Phoenixのトレース UIでキャッシュヒットトークン数が表示されるように

- **Agent Analytics ページ削除（Phoenix UIに移行）**
  - `/operations`ページ・サイドバー・ダッシュボードカードを全削除
  - SupabaseSpanExporter削除（agent_traces/agent_spansテーブルへの書き込みを停止）
  - agent_analytics API（`/api/v1/agent-analytics`）削除
  - テレメトリはPhoenix OTLPエクスポーターのみに集約
  - 削除ファイル:
    - `frontend/src/app/operations/page.tsx`
    - `frontend/src/components/operations/` (8コンポーネント)
    - `frontend/src/hooks/use-agent-analytics.ts`
    - `backend/app/presentation/api/v1/agent_analytics.py`
    - `backend/app/infrastructure/adk/telemetry/supabase_exporter.py`
  - 変更ファイル:
    - `backend/app/presentation/api/v1/__init__.py` - agent_analytics import削除
    - `backend/app/infrastructure/adk/telemetry/__init__.py` - SupabaseSpanExporter export削除
    - `backend/app/infrastructure/adk/telemetry/setup.py` - SupabaseSpanExporter登録削除、Phoenix only
    - `frontend/src/components/app-sidebar.tsx` - operations項目・case削除
    - `frontend/src/app/page.tsx` - 業務推進室カード・クイックリンク削除

- **フィードバック・アノテーションシステム全面実装（2026-02-07）**
  - **目的**: b&qエージェントの応答品質をユーザーFBで改善するための包括的フィードバック収集・レビュー・エクスポート基盤
  - **UXモード**:
    - **通常モード**: アシスタントメッセージにホバーでThumbsUp/Down表示。ThumbsDownでPopover（タグ選択・コメント・修正案・次元別評価）
    - **FBモード**: ヘッダーのトグルで有効化。メッセージ内テキスト選択→アノテーション作成（重要度・タグ・コメント・修正案）
  - **テキストアンカリング**: W3C Web Annotation Data Model準拠。position（文字オフセット）+ quote（prefix/exact/suffix）デュアルセレクタで永続化
  - **DBスキーマ**: 4テーブル + 3ビュー
    - `feedback_dimensions`: 評価次元マスタ（accuracy, relevance, completeness, tone, tool_usage, helpfulness の6次元プリセット）
    - `feedback_tags`: タグマスタ（positive/negative/neutral 16タグプリセット）
    - `message_feedback`: メッセージ単位FB（rating, tags, comment, correction, dimension_scores, content_hash）UNIQUE(message_id, user_email)
    - `message_annotations`: テキスト範囲アノテーション（selector JSONB, severity, tags, comment, correction）
    - ビュー: `feedback_conversation_summary`, `feedback_tag_frequency`, `feedback_daily_trend`
  - **バックエンドAPI**: `backend/app/presentation/api/v1/feedback.py` - 13エンドポイント
    - FB CRUD: `GET/POST /messages/{id}/feedback`, `POST /messages/{id}/annotations`, `DELETE /annotations/{id}`
    - レビュー: `GET /overview`, `GET /list`, `PUT /messages/{id}/feedback/review`
    - マスタ: `GET /tags`, `GET /dimensions`
    - エクスポート: `GET /export` (JSONL/CSV StreamingResponse)
    - 認証: MarketingTokenService流用（x-marketing-client-secret）
  - **フロントエンド**:
    - 型定義: `frontend/src/lib/feedback/types.ts` - 全型（FeedbackDimension, FeedbackTag, MessageFeedback, MessageAnnotation, セレクタ型等）
    - テキスト選択: `frontend/src/lib/feedback/text-selector.ts` - captureTextSelection（TreeWalker+オフセット計算）、resolveSelector（ファジーフォールバック）
    - フック: `frontend/src/hooks/use-feedback.ts` - useFeedback（チャット用）、useFeedbackDashboard（レビュー用）
    - コンポーネント:
      - `FeedbackBar.tsx` - メッセージ下のFBコントロール（ThumbsUp/Down + Popover）
      - `AnnotationLayer.tsx` - FBモード時のテキスト選択+アノテーション表示
      - `FeedbackModeToggle.tsx` - ヘッダーのFBモード切替トグル
      - `TagSelector.tsx` - チップ型タグ選択（センチメント別フィルタ）
      - `DimensionRating.tsx` - 星評価コンポーネント（1-5）
    - APIプロキシ: `frontend/src/app/api/feedback/[...path]/route.ts` - キャッチオールプロキシ（Cloud Run ID Token対応）
    - レビューダッシュボード: `frontend/src/app/feedback/page.tsx` - KPIカード、日次トレンド、タグ頻度、フィルタ付き一覧、詳細Sheet、レビューワークフロー、JSONL/CSVエクスポート
  - **既存ファイル変更**:
    - `ChatMessage.tsx` - FeedbackBar, AnnotationLayer統合
    - `MessageList.tsx` - FB props パススルー
    - `MarketingChat.tsx` - useFeedbackフック統合、FBモードトグル追加、getClientSecret prop追加
    - `marketing-v2/page.tsx` - getClientSecret propをMarketingChatに渡す
    - `app-sidebar.tsx` - マーケティングメニューに「FB レビュー」追加（ClipboardCheckアイコン）、/feedbackパスでマーケティングチーム判定
    - `backend/app/presentation/api/v1/__init__.py` - feedback router追加
  - 新規ファイル（14）:
    - `supabase/migrations/0022_add_feedback_system.sql`
    - `backend/app/presentation/api/v1/feedback.py`
    - `frontend/src/lib/feedback/types.ts`
    - `frontend/src/lib/feedback/text-selector.ts`
    - `frontend/src/hooks/use-feedback.ts`
    - `frontend/src/components/feedback/FeedbackBar.tsx`
    - `frontend/src/components/feedback/AnnotationLayer.tsx`
    - `frontend/src/components/feedback/FeedbackModeToggle.tsx`
    - `frontend/src/components/feedback/TagSelector.tsx`
    - `frontend/src/components/feedback/DimensionRating.tsx`
    - `frontend/src/components/feedback/index.ts`
    - `frontend/src/app/api/feedback/[...path]/route.ts`
    - `frontend/src/app/feedback/page.tsx`
    - `docs/feedback-system-proposal.md`
  - **設計判断**:
    - 新規ライブラリ依存なし（既存shadcn/ui + recharts + lucideで全UI構築）
    - content_hash（SHA-256）でメッセージ内容変更検知
    - レビューワークフロー: new → reviewed → actioned → dismissed
    - エクスポート: JSONL（RLHF/DPO学習用）、CSV（スプレッドシート分析用）

---

> ## **【最重要・再掲】記憶の更新は絶対に忘れるな**
> 作業が完了したら、コミットする前に、必ずこのファイルに変更内容を記録せよ。
> **「後で更新しよう」は禁止。今すぐ更新せよ。**
