# Environment Variables

## Backend (.env) — 主要項目
```env
# Google
SERVICE_ACCOUNT_JSON=        # ローカル用サービスアカウント
GOOGLE_SUBJECT_EMAILS=       # 収集対象メール (カンマ区切り)
MEETING_SOURCE=              # google_docs / notta / both

# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

# AI
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-pro  # デフォルト
OPENAI_API_KEY=
IMAGE_GEN_GEMINI_API_KEY=    # 画像生成用個別キー (未設定時はGEMINI_API_KEYを使用)

# ChatKit
MARKETING_AGENT_MODEL=gpt-5-mini
MARKETING_REASONING_EFFORT=  # low/medium/high/xhigh
MARKETING_CHATKIT_TOKEN_SECRET=  # JWT署名用 (32+バイト)
MARKETING_UPLOAD_BASE_URL=

# Zoho (optional)
ZOHO_CLIENT_ID=
ZOHO_CLIENT_SECRET=
ZOHO_REFRESH_TOKEN=

# Cloud Tasks
GCP_PROJECT=
TASKS_QUEUE=
TASKS_WORKER_URL=
TASKS_OIDC_SERVICE_ACCOUNT=

# Local MCP (高速化)
USE_LOCAL_MCP=false          # true でローカルMCP有効化
LOCAL_MCP_GA4_ENABLED=true   # GA4ローカルMCP
LOCAL_MCP_GSC_ENABLED=true   # GSCローカルMCP
MCP_CLIENT_TIMEOUT_SECONDS=120

# MCP Servers (リモート, optional)
GA4_MCP_SERVER_URL=
GSC_MCP_SERVER_URL=
AHREFS_MCP_SERVER_URL=
META_ADS_MCP_SERVER_URL=
WORDPRESS_MCP_SERVER_URL=

# ADK (Google Agent Development Kit)
USE_ADK=false                           # ADK V2マーケティングAI有効化
ADK_ORCHESTRATOR_MODEL=gemini-3-flash-preview
ADK_SUB_AGENT_MODEL=gemini-3-flash-preview
ADK_MAX_LLM_CALLS=0                    # 0=無制限
ADK_MAX_OUTPUT_TOKENS=65536
ADK_CONTEXT_CACHE_ENABLED=true          # Gemini Explicit Cache (90%コスト削減)
ADK_CACHE_TTL_SECONDS=1800              # キャッシュ有効期間 (30分)
ADK_CACHE_MIN_TOKENS=2048               # キャッシュ作成の最小トークン数
ADK_CACHE_INTERVALS=10                  # 再作成までの呼び出し回数

# Server
ENV=local  # local / production
CORS_ALLOW_ORIGINS=
LOG_LEVEL=INFO
```

## Frontend (.env.local) — 主要項目
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
ALLOWED_EMAIL_DOMAINS=bandq.jp
NEXT_PUBLIC_MARKETING_CHATKIT_URL=  # Backend ChatKitエンドポイント
MARKETING_CHATKIT_TOKEN_SECRET=     # Backend と一致必須
USE_LOCAL_BACKEND=true              # ローカル開発用
DEV_BACKEND_BASE=http://localhost:8000
```
