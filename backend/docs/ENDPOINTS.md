# Meet2Gemini API エンドポイント早見表

ベース: FastAPI（Cloud Run 想定）/ ベースパス `app.main:app`

- ヘルスチェック: `GET /health`
- API v1 ルート: `/api/v1`
  - Meetings: `/api/v1/meetings`
  - Structured: `/api/v1/structured`
  - Zoho (read-only): `/api/v1/zoho`

必要環境変数（抜粋）:
- `SERVICE_ACCOUNT_JSON`: サービスアカウントJSONのパス or JSON文字列
- `GOOGLE_SUBJECT_EMAILS`: 収集対象のアカウント(カンマ区切り)
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- `GEMINI_API_KEY` または `GOOGLE_API_KEY`

---

## ヘルスチェック
- `GET /health`
  - 目的: 稼働確認
  - レスポンス: `{ "status": "ok" }`

認証（任意設定）:
- `.env` に `APP_AUTH_TOKEN` を設定すると、以下が有効になります。
  - `/api/v1/*` と `/test-client` は `Authorization: Bearer <token>` または `?token=<token>` を要求
  - 例外: `/health`, `/oauth/zoho/callback`
  - 例: `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/meetings`

---

## Meetings API

### 1) 収集実行
- `POST /api/v1/meetings/collect`
- クエリ:
  - `accounts`（複数可）: 収集対象アカウント。未指定時は `GOOGLE_SUBJECT_EMAILS` 全員。
  - `include_structure`（bool）: 収集と同時に構造化も実行（将来用。現実装では未使用）。
  - `force_update`（bool）: Drive `modifiedTime` が変わらなくても上書き更新。
- 例:
  - 指定ユーザーで収集: `POST /api/v1/meetings/collect?accounts=a@ex.com&accounts=b@ex.com`
  - すべて（環境変数の既定）: `POST /api/v1/meetings/collect`
- 成功レスポンス: `{ "stored": <保存・更新した件数> }`

### 2) 一覧取得
- `GET /api/v1/meetings`
- クエリ:
  - `accounts`（複数可）: 指定アカウントの議事録にフィルタ。
- 例: `GET /api/v1/meetings?accounts=a@ex.com&accounts=b@ex.com`
- レスポンス: Meeting の配列（主要フィールド）
  - `id`, `doc_id`, `title`, `meeting_datetime`, `organizer_email`, `document_url`, `invited_emails`, `text_content`, `metadata`

### 3) 詳細取得
- `GET /api/v1/meetings/{meeting_id}`
- 目的: 1件の議事録詳細を取得
- 例: `GET /api/v1/meetings/123`
- レスポンス: Meeting 1件

---

## Structured API（Gemini 構造化）

前提: `GEMINI_API_KEY`（または `GOOGLE_API_KEY`）が必要。対象会議の本文は `meeting_documents.text_content` に保存済みであること。

### 1) 構造化処理の実行
- `POST /api/v1/structured/process/{meeting_id}`
- 目的: DB の本文を入力に Gemini で構造化抽出し、`structured_outputs` に upsert。
- 例: `POST /api/v1/structured/process/123`
- レスポンス例: `{ "meeting_id": "123", "data": { ...抽出結果... } }`

### 2) 構造化結果の取得
- `GET /api/v1/structured/{meeting_id}`
- 目的: 保存済みの構造化データ取得（未作成なら `{}`）
- 例: `GET /api/v1/structured/123`
- レスポンス例: `{ "meeting_id": "123", "data": { ... } }`

### 3) 自動処理（Docs タイトル x Zoho 求職者名 100%一致時のみ）
- `POST /api/v1/structured/auto-process`
  - 説明: Docsタイトルから候補者名を抽出し、Zoho APP-hcの「求職者名」と厳密一致（equals）した場合のみ、構造化＋Zoho書き込みを自動実行します。`sync=true` を指定すると同期実行でサマリを即時返却、未指定時は非同期実行で `job_id` を返却（進捗は `/api/v1/meetings/collect/status/{job_id}`）。
  - Body(JSON):
    - `accounts` (string[]): 対象のGoogleアカウント（省略時は `GOOGLE_SUBJECT_EMAILS` 全員）
    - `max_items` (int): 1回の実行で処理する最大件数（デフォルト: `AUTOPROC_MAX_ITEMS` もしくは20）
    - `dry_run` (bool): trueで一致判定のみ行い、Gemini/Zohoの外部I/Oを行わない
    - `title_regex` (string): タイトルから候補者名を抽出する正規表現（未指定時は `CANDIDATE_TITLE_REGEX` を利用。どちらも未設定ならタイトル全体を候補者名として扱う）
    - `sync` (bool): trueで同期実行（ローカル検証向け）
  - レスポンス: `{ message, job_id, status_url }`（sync=true の場合は処理サマリ）

- `POST /api/v1/structured/auto-process-task`
  - 説明: Cloud Tasks に自動処理タスクを投入します。Cloud Run の Worker (`/api/v1/structured/auto-process/worker`) が実処理を行います。
  - Body: 上記と同じ
  - 注意: `TASKS_AUTOPROC_WORKER_URL`（未設定時は `TASKS_WORKER_URL` から自動導出）を正しく設定してください。

- `POST /api/v1/structured/auto-process/worker`
  - 説明: Cloud Tasks からのみ叩かれるWorker用エンドポイント。手動実行不要です。
  - Header: `X-Cloud-Tasks-QueueName` or `X-Requested-By: cloud-tasks-enqueue`

一致ロジックの詳細
- 文字起こし未保存（`text_content` が空/None）の会議はスキップ
- 会議名（Docsタイトル）に「初回」を含まない場合はスキップ
- タイトルから候補者名を抽出（`title_regex` または `CANDIDATE_TITLE_REGEX`）
  - 正規化（NFKC＋lower＋空白圧縮）後に、Zoho側の求職者名と完全一致（equals）
- Zoho検索は APP-hc の「求職者名」に対して `equals` を使用。ヒットがちょうど1件の時のみ続行
- 既に `structured_outputs` が存在する会議はスキップ（再処理しない）
- 1回の実行あたり `max_items` 件まで処理（デフォルト20）

---

## cURL サンプル

- 収集（2ユーザー）
```
curl -X POST "http://localhost:8000/api/v1/meetings/collect?accounts=a@ex.com&accounts=b@ex.com"
```

---

## Zoho CRM API（読み取り専用）

- 検索: `GET /api/v1/zoho/app-hc/search?name=<文字列>&limit=5`
  - 返却: `{ items: [{ record_id, candidate_name, candidate_id }], count }`
- 単一詳細: `GET /api/v1/zoho/app-hc/{record_id}`
  - 返却: `{ record: {...}, record_id }`（全フィールド）
- メタ: 
  - モジュール一覧: `GET /api/v1/zoho/modules`
  - フィールド一覧: `GET /api/v1/zoho/fields?module=CustomModule1`

認証（有効時）:
```
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/zoho/app-hc/search?name=山田&limit=10"
```

- 一覧（フィルタ）
```
curl "http://localhost:8000/api/v1/meetings?accounts=a@ex.com&accounts=b@ex.com"
```

- 詳細
```
curl "http://localhost:8000/api/v1/meetings/123"
```

- 構造化処理
```
curl -X POST "http://localhost:8000/api/v1/structured/process/123"
```

- 構造化取得
```
curl "http://localhost:8000/api/v1/structured/123"
```

---

## Zoho API（読み取り専用）

事前に `.env` に以下を設定してください（読み取りのみ）。
- `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`
- `ZOHO_API_BASE_URL=https://www.zohoapis.jp`, `ZOHO_ACCOUNTS_BASE_URL=https://accounts.zoho.jp`

### 1) APP-hc（CustomModule1）求職者名検索
- `GET /api/v1/zoho/app-hc/search?name=<日本語可>&limit=5`
- 目的: 「求職者名」ラベルのフィールドで部分一致検索し、`record_id / candidate_name / candidate_id` を返却。
- 例:
```
curl --http1.1 "http://localhost:8000/api/v1/zoho/app-hc/search?name=伊藤&limit=5"
```
- 備考: ラベル→API名の自動解決に失敗する場合、`.env` に `ZOHO_APP_HC_NAME_FIELD_API` / `ZOHO_APP_HC_ID_FIELD_API` を明示してください。

### 2) モジュール/フィールドの確認（発見用）
- モジュール一覧: `GET /api/v1/zoho/modules`
```
curl --http1.1 "http://localhost:8000/api/v1/zoho/modules"
```
- フィールド一覧（例）: `GET /api/v1/zoho/fields?module=CustomModule1`
```
curl --http1.1 "http://localhost:8000/api/v1/zoho/fields?module=CustomModule1"
```

---

## 参考: Cloud Functions (別系統)
このリポジトリには、Drive webhook 用の Flask アプリ（`main.py`）も含まれます。
- `POST /`（GCF 側のエンドポイント）: Drive 変更通知を処理し、追加ドキュメントを取り込む仕組み（サンプル実装）。
- `GET /health`（GCF 側）: ヘルスチェック。
Cloud Run の FastAPI とはデプロイ先・用途が異なるため、混同に注意してください。
