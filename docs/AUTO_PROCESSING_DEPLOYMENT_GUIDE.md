# 自動処理システム デプロイ・運用ガイド

このドキュメントでは、自動構造化処理システムのローカル実験方法とGCPでの本番運用設定について説明します。

## 目次

1. [ローカル実験方法](#1-ローカル実験方法)
2. [GCP Cloud Tasks設定](#2-gcp-cloud-tasks設定)
3. [GCP Cloud Scheduler設定](#3-gcp-cloud-scheduler設定)
4. [デプロイ後の運用確認](#4-デプロイ後の運用確認)
5. [監視とトラブルシューティング](#5-監視とトラブルシューティング)

---

## 1. ローカル実験方法

### 1.1 サーバー起動

```bash
cd /home/als0028/study/bandq-jp/gws-meet2gemini/backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

サーバーが起動したら、ブラウザで `http://localhost:8000/docs` にアクセスしてSwagger UIを確認できます。

### 1.2 基本的なAPI呼び出し

#### 自動処理実行（同期処理）

**ドライランテスト（実際には処理せず、候補のみ表示）:**
```bash
curl -X POST "http://localhost:8000/api/v1/structured/auto-process" \
  -H "Content-Type: application/json" \
  -d '{
    "accounts": ["agent@bandq.jp"],
    "max_items": 5,
    "dry_run": true,
    "sync": true,
    "parallel_workers": 3,
    "batch_size": 5
  }'
```

**実際の処理実行:**
```bash
curl -X POST "http://localhost:8000/api/v1/structured/auto-process" \
  -H "Content-Type: application/json" \
  -d '{
    "accounts": ["agent@bandq.jp"],
    "max_items": 3,
    "dry_run": false,
    "sync": true,
    "parallel_workers": 2,
    "batch_size": 3
  }'
```

**パラメータ説明:**
- `accounts`: 処理対象のGoogleアカウント（空配列で全アカウント）
- `max_items`: 最大処理件数
- `dry_run`: `true`で実際の処理をスキップ（テスト用）
- `sync`: `true`で同期処理、`false`でバックグラウンド処理
- `parallel_workers`: 並列ワーカー数（1-10）
- `batch_size`: バッチサイズ（1-50）

**🔍 候補収集の範囲:**
- システムは `max_items * 5` ページまで、または十分な候補が見つかるまで検索
- 例：`max_items=5` なら最大25ページ（1000件）を確認
- 既に構造化済みのデータは自動的にスキップ
- 優先度の高い順に候補を選択

#### 自動処理実行（非同期処理）

```bash
# バックグラウンドで実行（15分までの長時間処理に対応）
curl -X POST "http://localhost:8000/api/v1/structured/auto-process" \
  -H "Content-Type: application/json" \
  -d '{
    "accounts": ["agent@bandq.jp"],
    "max_items": 10,
    "dry_run": false,
    "sync": false
  }'
```

レスポンス例:
```json
{
  "message": "Auto-processing started (background).",
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "status_url": "/api/v1/meetings/collect/status/12345678-1234-1234-1234-123456789abc"
}
```

### 1.3 統計情報とヘルスチェック

#### 統計情報取得

```bash
# 基本統計（過去7日間）
curl -X GET "http://localhost:8000/api/v1/structured/auto-process/stats"

# 詳細統計（過去14日間、コスト分析・モデル別使用量含む）
curl -X GET "http://localhost:8000/api/v1/structured/auto-process/stats?days_back=14&detailed=true"

# 見やすい形式で表示
curl -s -X GET "http://localhost:8000/api/v1/structured/auto-process/stats" | python -m json.tool
```

統計レスポンス例:
```json
{
  "period": {
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-08T00:00:00Z",
    "days": 7
  },
  "basic_stats": {
    "total_meetings": 150,
    "unstructured_meetings": 45,
    "structured_meetings": 105,
    "zoho_matchable_meetings": 38
  },
  "processing_stats": {
    "total_processed": 35,
    "successful_processed": 33,
    "failed_processed": 2,
    "success_rate": 0.943,
    "daily_processing_rate": 5.0
  },
  "cost_metrics": {
    "estimated_cost_usd": 12.45,
    "total_tokens_used": 245000,
    "avg_tokens_per_meeting": 7000
  }
}
```

#### ヘルスチェック

```bash
# システム健全性確認
curl -X GET "http://localhost:8000/api/v1/structured/auto-process/health"

# ステータスのみ確認
curl -s -X GET "http://localhost:8000/api/v1/structured/auto-process/health" | jq '.status'
```

ヘルスチェックレスポンス例:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "metrics": {
    "success_rate": 0.95,
    "error_rate": 0.02,
    "total_processed_24h": 45,
    "active_alerts": 0
  },
  "alerts": [],
  "checks": {
    "success_rate_ok": true,
    "error_rate_ok": true,
    "no_critical_alerts": true
  }
}
```

### 1.4 Cloud Tasks形式テスト（参考用）

```bash
# Cloud Tasksキューに登録する形式（ローカルでは実際には動作しません）
curl -X POST "http://localhost:8000/api/v1/structured/auto-process-task" \
  -H "Content-Type: application/json" \
  -d '{
    "accounts": ["agent@bandq.jp"],
    "max_items": 5,
    "parallel_workers": 3,
    "batch_size": 5
  }'
```

---

## 2. GCP Cloud Tasks設定

### 2.1 Cloud Tasksキューの作成

1. **GCPコンソールにアクセス**
   - https://console.cloud.google.com/
   - プロジェクトを選択

2. **Cloud Tasks APIの有効化**
   ```bash
   gcloud services enable cloudtasks.googleapis.com
   ```

3. **Cloud Tasksコンソールに移動**
   - 左側メニュー → 「Cloud Tasks」を選択
   - または検索バーで「Cloud Tasks」と検索

4. **キューを作成**

   **基本設定:**
   ```
   キュー名: auto-process-queue
   リージョン: asia-northeast1 (東京)
   ```

   **レート制限設定:**
   ```
   最大ディスパッチレート: 10 requests/秒
   最大同時ディスパッチ数: 5
   バケットサイズ: 100
   ```

   **再試行設定:**
   ```
   最大試行回数: 3
   最小バックオフ: 10秒
   最大バックオフ: 300秒 (5分)
   最大倍数: 3
   ```

### 2.2 gcloudコマンドでの作成（代替方法）

```bash
# Cloud Tasksキュー作成
gcloud tasks queues create auto-process-queue \
  --location=asia-northeast1 \
  --max-dispatches-per-second=10 \
  --max-concurrent-dispatches=5 \
  --max-attempts=3 \
  --min-backoff=10s \
  --max-backoff=300s
```

### 2.3 IAM権限設定

```bash
# Cloud TasksがCloud Runを呼び出すためのサービスアカウント作成
gcloud iam service-accounts create cloud-tasks-invoker \
  --display-name="Cloud Tasks Invoker"

# Cloud Run呼び出し権限付与
gcloud run services add-iam-policy-binding meet2gemini \
  --region=asia-northeast1 \
  --member="serviceAccount:cloud-tasks-invoker@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Cloud Tasksエンキュー権限付与
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:cloud-tasks-invoker@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudtasks.enqueuer"
```

---

## 3. GCP Cloud Scheduler設定

### 3.1 Cloud Schedulerジョブの作成

1. **Cloud Scheduler APIの有効化**
   ```bash
   gcloud services enable cloudscheduler.googleapis.com
   ```

2. **Cloud Schedulerコンソールに移動**
   - 左側メニュー → 「Cloud Scheduler」を選択

3. **ジョブを作成**

   **基本設定:**
   ```
   ジョブ名: auto-process-scheduler
   リージョン: asia-northeast1
   説明: 自動構造化処理の定期実行（30分間隔）
   ```

   **スケジュール設定:**
   ```
   頻度（Cron形式): 0 */30 10-23 * * *
   タイムゾーン: Asia/Tokyo
   ```
   
   **Cron式の説明:**
   - `0 */30 10-23 * * *` = 毎日10:00-23:00の間、30分ごとに実行
   - `0 0 */2 * * *` = 2時間ごとに実行
   - `0 0 9,13,17,21 * * *` = 9時、13時、17時、21時に実行

   **ターゲット設定:**
   ```
   ターゲットタイプ: HTTP
   URL: https://YOUR_CLOUD_RUN_SERVICE_URL/api/v1/structured/auto-process-task
   HTTPメソッド: POST
   ```

   **認証設定:**
   ```
   Auth header: Add OIDC token
   Service account: cloud-tasks-invoker@YOUR_PROJECT_ID.iam.gserviceaccount.com
   Audience: https://YOUR_CLOUD_RUN_SERVICE_URL
   ```

   **リクエストボディ:**
   ```json
   {
     "accounts": [],
     "max_items": 20,
     "dry_run": false,
     "parallel_workers": 5,
     "batch_size": 10
   }
   ```

   **HTTPヘッダー:**
   ```
   Content-Type: application/json
   X-Requested-By: cloud-scheduler
   ```

### 3.2 gcloudコマンドでの作成（代替方法）

```bash
# Cloud Schedulerジョブ作成
gcloud scheduler jobs create http auto-process-scheduler \
  --location=asia-northeast1 \
  --schedule="0 */30 10-23 * * *" \
  --time-zone="Asia/Tokyo" \
  --uri="https://YOUR_CLOUD_RUN_SERVICE_URL/api/v1/structured/auto-process-task" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"accounts":[],"max_items":20,"dry_run":false,"parallel_workers":5,"batch_size":10}' \
  --oidc-service-account-email="cloud-tasks-invoker@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --oidc-token-audience="https://YOUR_CLOUD_RUN_SERVICE_URL"
```

---

## 4. デプロイ後の運用確認

### 4.1 Cloud Run環境変数の設定

Cloud Runコンソールで以下の環境変数を設定:

```bash
# 自動処理設定
AUTOPROC_PARALLEL_WORKERS=5
AUTOPROC_BATCH_SIZE=10
AUTOPROC_MAX_ITEMS=20
AUTOPROC_SUCCESS_RATE_THRESHOLD=0.9
AUTOPROC_ERROR_RATE_THRESHOLD=0.05

# Cloud Tasks設定
EXPECTED_QUEUE_NAME=auto-process-queue
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID

# その他の既存設定
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_key
GEMINI_API_KEY=your_api_key
# ... 他の環境変数
```

### 4.2 手動テスト実行

**Cloud Run Proxy経由でのテスト:**
```bash
# Cloud Runサービスにプロキシ接続（認証付き）
gcloud run services proxy meet2gemini --region=asia-northeast1 --port=8080

# 別ターミナルでテスト実行
curl -X POST "http://localhost:8080/api/v1/structured/auto-process-task" \
  -H "Content-Type: application/json" \
  -H "X-Requested-By: manual-test" \
  -d '{
    "max_items": 3,
    "dry_run": true,
    "parallel_workers": 2,
    "batch_size": 3
  }'
```

**認証付き直接アクセス:**
```bash
# アクセストークン取得
ACCESS_TOKEN=$(gcloud auth print-access-token)

# Cloud Runサービスに直接リクエスト
curl -X POST "https://YOUR_CLOUD_RUN_SERVICE_URL/api/v1/structured/auto-process-task" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"max_items": 5, "dry_run": true}'
```

### 4.3 スケジューラー手動実行

```bash
# Cloud Schedulerジョブを手動実行
gcloud scheduler jobs run auto-process-scheduler --location=asia-northeast1
```

---

## 5. 監視とトラブルシューティング

### 5.1 ログ確認

**Cloud Runログ:**
```bash
# リアルタイムログ
gcloud run services logs tail meet2gemini --region=asia-northeast1

# 特定期間のログ
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=meet2gemini" \
  --limit=50 \
  --format="table(timestamp, textPayload)"
```

**GCPコンソールでのログ確認:**
1. Cloud Logging → ログエクスプローラ
2. フィルター設定:
   ```
   resource.type="cloud_run_revision"
   resource.labels.service_name="meet2gemini"
   severity>=ERROR
   ```

### 5.2 Cloud Tasks監視

**Cloud Tasksキュー状態確認:**
```bash
# キュー状態表示
gcloud tasks queues describe auto-process-queue --location=asia-northeast1

# 実行中タスク一覧
gcloud tasks list --queue=auto-process-queue --location=asia-northeast1
```

**GCPコンソールでの確認:**
1. Cloud Tasks → auto-process-queue
2. タスク一覧で実行状況を確認
3. 失敗したタスクの詳細を確認

### 5.3 Cloud Scheduler監視

**スケジューラー実行履歴:**
```bash
# ジョブ状態確認
gcloud scheduler jobs describe auto-process-scheduler --location=asia-northeast1

# 実行履歴確認（GCPコンソール推奨）
```

**GCPコンソールでの確認:**
1. Cloud Scheduler → auto-process-scheduler
2. 実行履歴タブで成功/失敗状況を確認
3. 失敗したジョブのログを確認

### 5.4 API監視・ヘルスチェック

**定期ヘルスチェック:**
```bash
#!/bin/bash
# health_check.sh
SERVICE_URL="https://YOUR_CLOUD_RUN_SERVICE_URL"
ACCESS_TOKEN=$(gcloud auth print-access-token)

HEALTH_STATUS=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$SERVICE_URL/api/v1/structured/auto-process/health" | jq -r '.status')

echo "Health Status: $HEALTH_STATUS"

if [ "$HEALTH_STATUS" != "healthy" ]; then
  echo "⚠️ System is not healthy! Check the logs."
  # アラート送信などの処理
fi
```

**統計ダッシュボード:**
```bash
#!/bin/bash
# stats_dashboard.sh
SERVICE_URL="https://YOUR_CLOUD_RUN_SERVICE_URL"
ACCESS_TOKEN=$(gcloud auth print-access-token)

echo "=== Auto-Processing Statistics ==="
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$SERVICE_URL/api/v1/structured/auto-process/stats?detailed=true" | \
  jq '{
    period: .period,
    success_rate: .processing_stats.success_rate,
    total_processed: .processing_stats.total_processed,
    estimated_cost: .cost_metrics.estimated_cost_usd,
    alerts_count: (.alerts | length)
  }'
```

### 5.5 アラート設定

**Cloud Monitoringアラートポリシー:**

1. **成功率低下アラート:**
   ```
   条件: HTTP応答コードが400-500の割合が10%を超える
   期間: 5分間
   通知: メール、Slack
   ```

2. **レスポンス時間アラート:**
   ```
   条件: 平均レスポンス時間が30秒を超える
   期間: 5分間
   通知: メール
   ```

3. **エラー率アラート:**
   ```
   条件: ログにERRORレベルのメッセージが10件/分を超える
   期間: 5分間
   通知: メール、Slack
   ```

### 5.6 トラブルシューティング

**よくある問題と対処法:**

1. **Cloud Tasks認証エラー:**
   ```bash
   # サービスアカウント権限確認
   gcloud projects get-iam-policy YOUR_PROJECT_ID \
     --flatten="bindings[].members" \
     --filter="bindings.members:cloud-tasks-invoker@YOUR_PROJECT_ID.iam.gserviceaccount.com"
   ```

2. **メモリ不足エラー:**
   ```bash
   # Cloud Runメモリ制限を増やす
   gcloud run services update meet2gemini \
     --region=asia-northeast1 \
     --memory=2Gi
   ```

3. **タイムアウトエラー:**
   ```bash
   # Cloud Runタイムアウト設定を延長
   gcloud run services update meet2gemini \
     --region=asia-northeast1 \
     --timeout=900  # 15分
   ```

4. **並列処理の負荷問題:**
   - 環境変数`AUTOPROC_PARALLEL_WORKERS`を削減（5→3）
   - 環境変数`AUTOPROC_BATCH_SIZE`を削減（10→5）

**パフォーマンス最適化:**
```bash
# Cloud Runインスタンス設定
gcloud run services update meet2gemini \
  --region=asia-northeast1 \
  --min-instances=1 \
  --max-instances=10 \
  --cpu=2 \
  --memory=2Gi \
  --concurrency=10
```

---

## 6. 運用スケジュール例

### 6.1 日次運用

```bash
# 毎日実行する監視スクリプト例
#!/bin/bash
# daily_check.sh

echo "=== Daily Auto-Processing Health Check ==="
date

# ヘルスチェック
./health_check.sh

# 統計確認
./stats_dashboard.sh

# 前日の処理結果確認
echo "=== Yesterday's Processing Summary ==="
# ログから前日の処理結果を抽出
gcloud logging read "resource.type=cloud_run_revision AND textPayload:'[auto] batch' AND timestamp>='-1d'" \
  --format="value(textPayload)" | grep "completed"
```

### 6.2 週次運用

- 詳細統計の確認とレポート作成
- エラー傾向の分析
- コスト分析とGemini使用量レビュー
- パフォーマンス最適化の検討

### 6.3 月次運用

- 全体的な成功率とKPI確認
- Zoho連携の精度確認
- システム設定の最適化レビュー
- 容量計画の見直し

---

このドキュメントに従って設定することで、1000件以上の既存議事録データと継続的な30分間隔データ収集に対応した自動処理システムの本番運用が可能になります。