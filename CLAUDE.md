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

---

> ## **【最重要・再掲】記憶の更新は絶対に忘れるな**
> 作業が完了したら、コミットする前に、必ずこのファイルに変更内容を記録せよ。
> **「後で更新しよう」は禁止。今すぐ更新せよ。**
