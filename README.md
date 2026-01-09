# b&qHubモノレポ

b&q 社内の業務をまとめる Hub です。ひとキャリの議事録収集・構造化（Meet/Docs → Supabase → Gemini）に加え、マーケティング分析アシスタント（ChatKit/SEO Canvas）など複数ドメインを同一基盤で運用します。FastAPI + Supabase + Next.js を DDD/オニオンで組み、Cloud Run 対応の拡張性・保守性を重視しています。

---

## ひとキャリ（議事録）
既存の議事録収集・構造化 API の説明です。

## 特長
- FastAPI によるシンプルな REST API
- Google Drive/Docs API を用いた議事録の一括収集（対象アカウントを指定可）
- Supabase（HTTP API）への保存（DB直接続は不使用）
- Gemini 2.5 Pro の構造化出力（分割・並列処理）により大規模スキーマへ対応
- ローカルは `service_account.json` を使用

---

## ディレクトリ構成（DDD/オニオン）
```
app/
  application/
    use_cases/                  # ユースケース層（アプリケーションサービス）
  domain/
    entities/                   # エンティティ（永続境界から独立）
    services/                   # ドメインサービス
  infrastructure/
    config/                     # 設定、環境変数
    gemini/                     # Gemini 構造化抽出
    google/                     # Google API クライアント（Drive/Docs）
    supabase/                   # Supabase クライアントとリポジトリ
  presentation/
    api/v1/                     # FastAPI ルーター
    schemas/                    # Pydantic スキーマ

supabase/
  migrations/0001_init.sql      # DB スキーマ（SQL）

Dockerfile                      # Cloud Run 用
.env.example                    # 環境変数サンプル
```

---

## 必要要件
- Python 3.12 以上
- Google Workspace（ドメインワイド デリゲーションを利用する場合）
- Supabase プロジェクト
- Gemini API キー（`GEMINI_API_KEY` または `GOOGLE_API_KEY`）

---

## 環境変数
`.env.example` を参照して `.env` を作成してください。

- Google/認証
  - `SERVICE_ACCOUNT_JSON`（ローカルのみ）: サービスアカウント JSON のパス。例: `service_account.json`
  - `GOOGLE_SUBJECT_EMAILS`: 収集対象のアカウント（偽装対象）をカンマ区切りで。例: `a@ex.com,b@ex.com`
- Supabase
  - `SUPABASE_URL`: Supabase プロジェクトの URL
  - `SUPABASE_SERVICE_ROLE_KEY`: Service Role キー（サーバーサイド）
    - 本番は Secret Manager から Cloud Run に注入してください
- Gemini
  - `GEMINI_API_KEY` または `GOOGLE_API_KEY`

注意: 本実装は Supabase の HTTP API（`supabase-py`）のみ利用し、Postgres への直接接続は行いません。

---

## セットアップ手順
1) 依存関係をインストール
- uv または pip を使用
- 例（pip）:
  ```bash
  pip install -e .
  ```

2) Supabase マイグレーションを適用
- SQL エディタで `supabase/migrations/0001_init.sql` を実行
  - テーブル: `meeting_documents`, `structured_outputs`
  - 一意制約: `(doc_id, organizer_email)`

3) .env 設定
- `.env.example` を複製して値を設定
- ローカルでは `SERVICE_ACCOUNT_JSON` を配置

4) サーバー起動（ローカル）
```bash
uvicorn app.main:app --reload
```

5) 簡易テストクライアント（任意）
- `docs/test-client.html` をブラウザで直接開くか、`/test-client` で配信
  - 画面上部に「議事録」「ZohoCRM」のタブがあります
  - 議事録タブ: 会議一覧/詳細、構造化出力（表形式/JSON）の表示と実行
  - ZohoCRMタブ: 求職者名で検索 → 結果リスト → クリックで詳細（2カラム表）
  - ベースURLに `http://localhost:8000` を指定
  - 必要に応じて `.env` で `CORS_ALLOW_ORIGINS` を設定（ローカル未設定時は `http://localhost:3000` のみ許可 / 本番では必須）

---

## 簡易認証（API / テストクライアントの保護）
任意で、Bearer トークンによる簡易保護を有効化できます。

1) `.env` に設定
```
APP_AUTH_TOKEN=your-secret-token
```
2) 有効化される対象
- `/api/v1/*` と `/test-client` が保護対象になります
- `Authorization: Bearer <token>` ヘッダ、または `?token=<token>` クエリを要求
- 例外: `/health`, `/oauth/zoho/callback` は無認証

3) テストクライアントの使い方
- 画面右上の「Auth Token」欄にトークンを入力（LocalStorageに保存）
- または `http://localhost:8000/test-client?token=your-secret-token` のようにクエリで付与
- 以降の API 呼び出しは自動で `Authorization` ヘッダが付与されます

4) cURL 例
```
curl -H "Authorization: Bearer your-secret-token" http://localhost:8000/api/v1/meetings
```

---

## API 仕様（v1）
ベースパス: `/api/v1`

- 収集
  - `POST /meetings/collect?accounts=<email>&accounts=<email>`
    - 指定したアカウントの Google ドキュメント（Meet Recordings フォルダ配下の Docs）を収集して Supabase に upsert
    - 指定なしの場合、`GOOGLE_SUBJECT_EMAILS` の全ユーザー
    - レスポンス例: `{ "stored": 12 }`

- 議事録
  - `GET /meetings`（クエリ `accounts` でフィルタ可）
  - `GET /meetings/{id}`

- 構造化出力（Gemini）
  - `POST /structured/process/{meeting_id}`: DB の本文を入力に Gemini で構造化抽出し保存
  - `GET  /structured/{meeting_id}`: 保存済み構造化出力を取得

保存される主な情報（`meeting_documents`）:
- `text_content`: ドキュメント本文（プレーンテキスト）
- `organizer_email`（収集に使ったメールアドレス）, `organizer_name`（所有者表示名）
- `document_url`: Docs の閲覧 URL
- `invited_emails`: 権限から取得（取得不可時は空）
- `title`, `meeting_datetime`: ファイル名から推定（なければ更新日時）
- `metadata`: Drive ファイルメタ

---

## アーキテクチャ設計
- Presentation 層（FastAPI）: 入出力変換のみ
- Application 層（UseCase）: 収集・保存・構造化処理のオーケストレーション
- Domain 層: エンティティ/ドメインサービス（重複判定は拡張ポイント）
- Infrastructure 層: 
  - Google API クライアント（Drive/Docs）: ローカル=サービスアカウントJSON、Cloud Run=Workload Identity
  - Supabase リポジトリ（HTTP API）: Upsert/Select 等
  - Gemini 抽出器: 分割・並列で大規模スキーマ安定化

---

## Cloud Run デプロイ
1) コンテナビルド
```bash
gcloud builds submit --tag gcr.io/<PROJECT>/meet2gemini
```

2) デプロイ
```bash
gcloud run deploy meet2gemini \
  --image gcr.io/<PROJECT>/meet2gemini \
  --region <REGION> \
  --set-env-vars SUPABASE_URL=... \
  --set-env-vars SUPABASE_SERVICE_ROLE_KEY=... \
  --set-env-vars GOOGLE_SUBJECT_EMAILS=... \
  --set-env-vars GEMINI_API_KEY=... \
  --allow-unauthenticated
```

3) サービスアカウント権限
- Cloud Run の実行サービスアカウントに Drive/Docs への適切な読み取り権限を付与
- 組織側で DWD（ドメインワイドデリゲーション）を用いる場合は SSO 側設定が必要

---

## セキュリティ/運用
- Supabase キーは Secret Manager で管理し Cloud Run に注入
- RLS を有効化し、必要に応じて RPC（security definer）やポリシーで制限強化
- ログや本文テキストは PII を含む可能性があるため、アクセス制御とマスキングに注意

---

## 将来拡張（要求整理）
- Zoho CRM 連携による面談者紐付け（DB スキーマ拡張）
- 構造化出力の CRM スキーマ項目へのマッピング/同期

---

## マーケティング部門
SEO/集客向けの ChatKit ベース「マーケティング分析アシスタント」を提供します。Supabase に会話・添付・記事ドラフトを保存し、GA4/GSC/Meta広告/Ahrefs/WordPress などの外部データも統合できます。

### 主な機能
- ChatKit 経由のマーケティング対話（GPT-5.1、高推論、Web検索・コード実行・各種 MCP を利用可）
- 添付ファイルのアップロード/検索（Supabase Storage `marketing-attachments` バケットに保存）
- Gemini Code Interpreter 生成物のプロキシダウンロード（OpenAI Files/Containers 対応、キャッシュ保存）
- 記事キャンバス連携：アウトライン/本文を Supabase `marketing_articles` に保存し、UI と同期
- モデルプリセット管理：`marketing_model_assets` にプリセットを保存し、Web検索/CI/Canvas 有効可否を切替

### バックエンド API（`/api/v1/marketing`）
- `POST /chatkit` — ChatKit サーバー呼び出し（SSE ストリーム対応）
- `POST|PUT /attachments/{attachment_id}/upload` — 2 段階アップロード（ヘッダ `x-marketing-client-secret` または `token` クエリで認証）
- `GET /files/{file_id}` — Code Interpreter/アップロード済みファイルのプロキシダウンロード（`container_id` が必要な場合あり）
- `GET /threads/{thread_id}/attachments` — 会話ごとの添付一覧
- `GET /model-assets` / `POST /model-assets` / `PUT|DELETE /model-assets/{id}` — モデルプリセット CRUD

認証: `x-marketing-client-secret` ヘッダ、または `Authorization: Bearer <token>`（いずれも `MARKETING_CHATKIT_TOKEN_SECRET` で署名された短期 JWT）。

### 必要な環境変数（バックエンド）
- `MARKETING_CHATKIT_TOKEN_SECRET`（必須） / `MARKETING_CHATKIT_TOKEN_TTL`（デフォルト 900 秒）
- `MARKETING_AGENT_MODEL`（デフォルト `gpt-5.1`）, `MARKETING_REASONING_EFFORT`（`low|medium|high`）
- `MARKETING_ENABLE_WEB_SEARCH`, `MARKETING_ENABLE_CODE_INTERPRETER`, `MARKETING_ENABLE_CANVAS`（各 true/false）
- `MARKETING_SEARCH_COUNTRY`（デフォルト `JP`）
- `MARKETING_WORKFLOW_ID`, `MARKETING_CHATKIT_API_BASE`, `MARKETING_UPLOAD_BASE_URL`
- 外部 MCP 連携: `GA4_MCP_SERVER_URL`, `GA4_MCP_AUTHORIZATION`, `META_ADS_MCP_SERVER_URL`, `META_ADS_MCP_AUTHORIZATION`, `AHREFS_MCP_SERVER_URL`, `AHREFS_MCP_AUTHORIZATION`, `GSC_MCP_SERVER_URL`, `GSC_MCP_API_KEY`, `WORDPRESS_MCP_SERVER_URL`, `WORDPRESS_MCP_AUTHORIZATION`, `WORDPRESS_ACHIEVE_MCP_SERVER_URL`, `WORDPRESS_ACHIEVE_MCP_AUTHORIZATION`

### Supabase テーブル/ストレージ
- テーブル: `marketing_conversations`, `marketing_messages`, `marketing_attachments`, `marketing_articles`, `marketing_model_assets`
- バケット: `marketing-attachments`（添付 & Code Interpreter 生成物キャッシュ）

### フロントエンド（任意で利用）
- `frontend/src/app/marketing` に ChatKit UI（記事キャンバス付き）。`bun dev` 後に `/marketing` へアクセス。
- トークンは Next.js サーバールート `/api/marketing/chatkit/start|refresh` で発行し、ブラウザでは `x-marketing-client-secret` ヘッダとして送信・Cookie に保存。

---

## ライセンス
社内利用/私的プロジェクト前提。外部公開する場合は適切なライセンスを追加してください。
