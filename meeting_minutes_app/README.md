# Meeting Minutes Management System

## 概要

Google Meet の議事録を自動収集し、Gemini API を使用して構造化データとして分析するシステムです。DDDとオニオンアーキテクチャに基づいて設計されており、拡張性と保守性を重視しています。

## 機能

- ✅ Google Drive から議事録の自動収集
- ✅ 重複排除機能
- ✅ Gemini 2.5 Pro による構造化データ抽出
- ✅ マルチアカウント対応
- ✅ RESTful API
- ✅ PostgreSQL データベース（複数プロバイダー対応）

## 対応データベース

- **Supabase PostgreSQL**
- **GCP Cloud SQL PostgreSQL**
- **ローカル PostgreSQL**
- **その他の PostgreSQL プロバイダー**

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、適切な値を設定してください：

```bash
cp .env.example .env
```

#### データベース設定例

**Supabase の場合:**
```env
DATABASE_URL="postgresql+asyncpg://postgres.your-project:[YOUR-PASSWORD]@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
```

**GCP Cloud SQL の場合:**
```env
# 本番環境（Cloud Run）
DATABASE_URL="postgresql+asyncpg://meeting_user:[PASSWORD]@/meeting_minutes_db?host=/cloudsql/[CONNECTION_NAME]"

# ローカル開発（Cloud SQL Proxy経由）
DATABASE_URL="postgresql+asyncpg://meeting_user:[PASSWORD]@localhost:5432/meeting_minutes_db"
```

### 3. Google サービスアカウントの設定

1. Google Cloud Console でサービスアカウントを作成
2. 必要な API を有効化：
   - Google Drive API
   - Google Docs API
3. サービスアカウントキーをダウンロードして `service_account.json` として保存
4. Domain-wide delegation を設定（組織のドライブアクセス用）

### 4. データベースマイグレーション

```bash
# 最新のマイグレーションを適用
python migrations.py upgrade

# マイグレーション状態を確認
python migrations.py current

# マイグレーション履歴を表示
python migrations.py history
```

### 5. アプリケーション起動

```bash
# 開発サーバー起動
python main.py

# または uvicorn を直接使用
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API エンドポイント

### 議事録管理

- `POST /api/v1/meetings/collect` - 議事録収集
- `GET /api/v1/meetings` - 議事録一覧取得
- `GET /api/v1/meetings/{id}` - 議事録詳細取得
- `GET /api/v1/meetings/recent` - 最近の議事録取得
- `GET /api/v1/meetings/statistics` - 統計情報取得

### 構造化データ

- `POST /api/v1/structured-data/analyze/{meeting_document_id}` - 構造化分析実行
- `GET /api/v1/structured-data/{id}` - 構造化データ取得
- `GET /api/v1/structured-data/meeting/{meeting_document_id}` - 議事録の構造化データ取得
- `GET /api/v1/structured-data` - 構造化データ一覧取得
- `GET /api/v1/structured-data/statistics` - 分析統計情報取得
- `POST /api/v1/structured-data/retry/{structured_data_id}` - 失敗した分析のリトライ

### システム

- `GET /health` - ヘルスチェック
- `GET /config` - システム設定情報
- `GET /docs` - API ドキュメント（開発環境）

## マイグレーション管理

### 基本コマンド

```bash
# データベースを最新にアップグレード
python migrations.py upgrade

# 特定のリビジョンまでアップグレード
python migrations.py upgrade 001

# ダウングレード
python migrations.py downgrade 001

# 新しいマイグレーションを作成
python migrations.py create "add new table"

# 現在の状態を確認
python migrations.py current

# マイグレーション履歴を表示
python migrations.py history
```

### 本番環境でのマイグレーション

**Cloud Run での実行例:**
```bash
# Cloud Run インスタンスに接続してマイグレーション実行
gcloud run services update meeting-minutes-app \
  --region=asia-northeast1 \
  --command="python,migrations.py,upgrade"
```

## Docker での実行

```bash
# Docker イメージをビルド
docker build -t meeting-minutes-app .

# Docker で実行
docker run -p 8000:8000 \
  -e DATABASE_URL="your-database-url" \
  -e GEMINI_API_KEY="your-api-key" \
  -v ./service_account.json:/app/service_account.json \
  meeting-minutes-app
```

## アーキテクチャ

```
meeting_minutes_app/
├── domain/                 # ドメイン層（ビジネスロジック）
├── application/            # アプリケーション層（ユースケース）
├── infrastructure/         # インフラストラクチャ層（外部システム）
├── presentation/           # プレゼンテーション層（API）
├── alembic/               # データベースマイグレーション
├── main.py                # アプリケーションエントリーポイント
└── migrations.py          # マイグレーション管理スクリプト
```

## 環境別設定

### 開発環境
- ローカル PostgreSQL またはSupabase
- サービスアカウントJSONファイル
- デバッグモード有効

### 本番環境（Cloud Run）
- GCP Cloud SQL
- サービスアカウントによる認証（ADC）
- プロダクションモード

## トラブルシューティング

### よくある問題

1. **データベース接続エラー**
   - `DATABASE_URL` の形式を確認
   - データベースが起動しているか確認
   - 認証情報が正しいか確認

2. **Google API 認証エラー**
   - サービスアカウントファイルのパスを確認
   - 必要な API が有効化されているか確認
   - Domain-wide delegation の設定を確認

3. **Gemini API エラー**
   - `GEMINI_API_KEY` または `GOOGLE_API_KEY` が設定されているか確認
   - API クォータを確認

### ログの確認

```bash
# ログレベルを調整
export LOG_LEVEL=DEBUG
python main.py
```

## 開発

### 新しいマイグレーションの作成

```bash
# モデルを変更後、自動的にマイグレーションを生成
python migrations.py create "describe your changes"
```

### テストの実行

```bash
pytest tests/
```

### コードフォーマット

```bash
black .
isort .
flake8 .
```