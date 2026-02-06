# Tech Stack

## Backend
- **Framework**: FastAPI + Uvicorn (Python 3.12)
- **Package Manager**: uv
- **AI/ML**: Google GenAI (Gemini 2.5 Pro/Flash), OpenAI Agents SDK 0.7.0, OpenAI ChatKit 1.6.0
- **Database**: Supabase (PostgreSQL HTTP API, RLS対応)
- **Authentication**: Clerk JWT + ドメイン制限 (@bandq.jp)
- **External APIs**: Zoho CRM SDK, Google Drive/Docs API, Google Cloud Tasks, Google Cloud Storage
- **MCP Servers**: GA4, GSC (ローカルSTDIO対応), Ahrefs, Meta Ads, WordPress (オプション)

## Frontend
- **Framework**: Next.js 16 + React 19 + TypeScript
- **Package Manager**: Bun
- **UI**: Tailwind CSS 4 + shadcn/ui (Radix UI) + Lucide React
- **Auth**: @clerk/nextjs (Google OAuth, @bandq.jp ドメイン制限)
- **Chat**: @openai/chatkit 1.5.0, @openai/chatkit-react 1.4.3
- **Markdown**: react-markdown + remark-gfm + rehype-sanitize
- **Search**: cmdk (Command Menu)

## Infrastructure
- **DB**: Supabase (PostgreSQL + Storage + RLS)
- **Deploy**: Google Cloud Run (backend), Vercel (frontend推定)
- **Async**: Google Cloud Tasks (バックグラウンドジョブ)
- **Storage**: Supabase Storage (marketing-attachments, image-gen-references, image-gen-outputs)
- **Container**: Docker (Cloud Run用)
