# Project Structure

```
gws-meet2gemini/
├── backend/                          # FastAPI バックエンド
│   ├── app/
│   │   ├── main.py                  # エントリポイント (CORS, ルーティング, ログ)
│   │   ├── application/use_cases/   # ユースケース (15+)
│   │   ├── domain/                  # エンティティ, サービス, リポジトリ(抽象)
│   │   ├── infrastructure/          # 外部連携 (Supabase, Gemini, Zoho, ChatKit, GCP等)
│   │   └── presentation/api/v1/    # APIルーター, スキーマ
│   ├── pyproject.toml               # Python依存関係 (uv管理)
│   ├── Dockerfile                   # Cloud Run用 (Python 3.12-slim + uv)
│   └── .env / .env.example          # 環境変数 (150+設定)
├── frontend/                         # Next.js 16 フロントエンド
│   ├── src/
│   │   ├── app/                     # App Router (hitocari, marketing, image-gen等)
│   │   ├── components/              # UI + feature コンポーネント
│   │   ├── hooks/                   # use-marketing-chatkit, use-image-gen等
│   │   ├── lib/                     # APIクライアント, ユーティリティ
│   │   └── middleware.ts            # Clerk認証 + ルート保護
│   ├── package.json                 # Bun依存関係
│   └── .env.local / .env.local.example
├── supabase/
│   └── migrations/                  # 19 SQLマイグレーション
└── docs/                            # ドキュメント
```
