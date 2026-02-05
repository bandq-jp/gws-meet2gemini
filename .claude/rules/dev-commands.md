# Development Commands

## Backend
```bash
cd backend
uv sync                                                    # 依存同期
uv run uvicorn app.main:app --reload --host 0.0.0.0       # 開発サーバー (port 8000)
uv run pytest                                              # テスト
```

## Frontend
```bash
cd frontend
bun install                                                # 依存インストール
bun dev                                                    # 開発サーバー (port 3000, Turbopack)
bun run build                                              # 本番ビルド
bun lint                                                   # ESLint
```

## Docker (Cloud Run)
```bash
docker build -t meet2gemini:latest backend/
docker run -p 8000:8080 -e SUPABASE_URL=... meet2gemini:latest
```

## Database
```bash
# Supabase CLIでマイグレーション適用
npx supabase db push
```

# Git Branching

- **main**: 本番ブランチ
- **develop**: 開発ブランチ
- **feat/***: フィーチャーブランチ → develop へPR
- コミットメッセージ: `type(scope): description` (feat, refactor, fix, chore)
