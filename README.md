# gws-meet2gemini API

Google Meet の議事録（Google ドキュメント）を収集し、Supabase に保存、Gemini で構造化要約を生成する FastAPI ベースのサーバー（Cloud Run 対応）です。DDD/オニオンアーキテクチャに基づき、拡張性・保守性に配慮した構成になっています。

---

## 特長
- FastAPI によるシンプルな REST API
- Google Drive/Docs API を用いた議事録の一括収集（対象アカウントを指定可）
- Supabase（HTTP API）への保存（DB直接続は不使用）
- Gemini 2.5 Pro の構造化出力（分割・並列処理）により大規模スキーマへ対応
- Cloud Run 本番では Workload Identity（添付サービスアカウント）で認証、ローカルは `service_account.json` を使用

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

## ライセンス
社内利用/私的プロジェクト前提。外部公開する場合は適切なライセンスを追加してください。
