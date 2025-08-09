# Meet2Gemini API エンドポイント早見表

ベース: FastAPI（Cloud Run 想定）/ ベースパス `app.main:app`

- ヘルスチェック: `GET /health`
- API v1 ルート: `/api/v1`
  - Meetings: `/api/v1/meetings`
  - Structured: `/api/v1/structured`

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

---

## cURL サンプル

- 収集（2ユーザー）
```
curl -X POST "http://localhost:8000/api/v1/meetings/collect?accounts=a@ex.com&accounts=b@ex.com"
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

## 参考: Cloud Functions (別系統)
このリポジトリには、Drive webhook 用の Flask アプリ（`main.py`）も含まれます。
- `POST /`（GCF 側のエンドポイント）: Drive 変更通知を処理し、追加ドキュメントを取り込む仕組み（サンプル実装）。
- `GET /health`（GCF 側）: ヘルスチェック。
Cloud Run の FastAPI とはデプロイ先・用途が異なるため、混同に注意してください。
