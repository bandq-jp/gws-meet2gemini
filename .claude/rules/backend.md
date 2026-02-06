# Backend Architecture (DDD/オニオン)

## レイヤー構成
1. **Presentation** (`presentation/api/v1/`): FastAPIルーター, Pydanticスキーマ
2. **Application** (`application/use_cases/`): オーケストレーション (15ユースケース)
3. **Domain** (`domain/`): エンティティ, ドメインサービス, リポジトリ(抽象)
4. **Infrastructure** (`infrastructure/`): 外部連携の具象実装

## 主要APIエンドポイント
| Prefix | 機能 |
|--------|------|
| `/api/v1/meetings` | 議事録収集・一覧・詳細 |
| `/api/v1/structured` | Gemini AI構造化抽出・自動処理 |
| `/api/v1/zoho` | Zoho CRM連携 |
| `/api/v1/marketing` | ChatKit SSEストリーム, モデルアセット, アタッチメント |
| `/api/v1/image-gen` | テンプレート・セッション・画像生成 |
| `/api/v1/custom-schemas` | 抽出スキーマCRUD |
| `/api/v1/ai-costs` | AI使用量・コスト追跡 |
| `/api/v1/settings` | アプリ設定 |
| `/health` | ヘルスチェック |
