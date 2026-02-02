# CLAUDE.md - 永続メモリ & 自己改善ログ

> ## **【最重要】記憶の更新は絶対に忘れるな**
> **作業の開始時・途中・完了時に必ずこのファイルを確認・更新せよ。**
> コード変更、設計変更、新しい知見、バグ修正、アーキテクチャ変更 — どんな小さな変更でも、発生したらその場で即座にこのファイルに記録すること。
> **ユーザーに「記憶を更新して」と言われる前に、自分から更新するのが当たり前。言われてからでは遅い。**
> これは最優先の義務であり、他のどんなタスクよりも優先される。

> **このファイルはClaude Codeの永続メモリであり、自己改善の記録である。**
> セッションをまたいで知識を保持し、過去の失敗・学び・判断を蓄積して次のセッションの自分をより賢くするためのファイルである。
>
> ## 運用ルール
> 1. **毎回の作業開始時**にこのファイルを読み込み、内容に従って行動する
> 2. **作業中に新しい知見・決定・変更が生じたら**、即座にこのファイルを更新する（追記・修正・削除）
> 3. **更新対象**: アーキテクチャ変更、新しい依存関係、デプロイ設定、踏んだ罠・解決策、環境差異、運用ルールなど
> 4. このファイルの情報が古くなった場合は削除・修正し、常に最新状態を維持する
> 5. **あとで思い出せるように書く**: 技術的な知見を記録する際は、調査元の公式ドキュメントURL・GitHubリポジトリ・SDKソースファイルパスなどの**情報ソース**も一緒に記録する
> 6. **セクションは自由に増減してよい**: 新しいテーマが出てきたらセクションを追加し、不要になったら統合・削除する
> 7. **自己改善**: ユーザーに指摘された間違い・非効率・判断ミスは「自己改善ログ」セクションに記録する
> 8. **常時更新の義務**: 新情報の発見、コードリーディング中の新発見、設計変更、UIの変更、技術的知見の獲得、バグの発見と修正など — あらゆる新たな情報や更新が発生した場合は**必ずその場でこのファイルを更新する**

---

## Package Management (STRICT)

- **Backend (Python)**: `uv add <package>` for dependencies. **Never use `pip install`.**
- **Frontend (JS/TS)**: `bun add <package>` for dependencies. **Never use `npm install` or `yarn add`.**
- Backend lock: `uv sync` to sync after changes
- Frontend lock: `bun install` to sync after changes

---

## プロジェクト概要

**b&q Hub** — Google Workspace / 外部SaaS連携によるAIプラットフォーム。議事録AI構造化・CRM連携・マーケティングAIチャット・画像生成を提供するモノレポ。

### 主要機能
1. **ひとキャリ (HitoCari)**: Google Meet/Docs/Notta → Gemini AI構造化抽出 → Supabase保存 → Zoho CRM連携
2. **マーケティングAIチャット**: OpenAI ChatKit + Agents SDK によるSEO/コンテンツ戦略アシスタント（GPT-5.2対応、Web Search / Code Interpreter / MCP連携）
3. **画像生成**: Gemini 2.5 Pro によるAI画像生成（テンプレート・リファレンス画像・セッション管理）

---

## Tech Stack

### Backend
- **Framework**: FastAPI + Uvicorn (Python 3.12)
- **Package Manager**: uv
- **AI/ML**: Google GenAI (Gemini 2.5 Pro/Flash), OpenAI Agents SDK 0.7.0
- **Database**: Supabase (PostgreSQL HTTP API, RLS対応)
- **Authentication**: Clerk JWT + ドメイン制限 (@bandq.jp)
- **External APIs**: Zoho CRM SDK, Google Drive/Docs API, Google Cloud Tasks, Google Cloud Storage
- **MCP Servers**: GA4, GSC, Ahrefs, Meta Ads, WordPress (オプション)

### Frontend
- **Framework**: Next.js 16 + React 19 + TypeScript
- **Package Manager**: Bun
- **UI**: Tailwind CSS 4 + shadcn/ui (Radix UI) + Lucide React
- **Auth**: @clerk/nextjs (Google OAuth, @bandq.jp ドメイン制限)
- **Chat**: カスタムSSEフック (useMarketingChat) + ActivityItemタイムライン
- **Markdown**: react-markdown + remark-gfm + rehype-sanitize
- **Search**: cmdk (Command Menu)

### Infrastructure
- **DB**: Supabase (PostgreSQL + Storage + RLS)
- **Deploy**: Google Cloud Run (backend), Vercel (frontend推定)
- **Async**: Google Cloud Tasks (バックグラウンドジョブ)
- **Storage**: Supabase Storage (marketing-attachments, image-gen-references, image-gen-outputs)
- **Container**: Docker (Cloud Run用)

---

## Project Structure

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

---

## Backend Architecture (DDD/オニオン)

### レイヤー構成
1. **Presentation** (`presentation/api/v1/`): FastAPIルーター, Pydanticスキーマ
2. **Application** (`application/use_cases/`): オーケストレーション (15ユースケース)
3. **Domain** (`domain/`): エンティティ, ドメインサービス, リポジトリ(抽象)
4. **Infrastructure** (`infrastructure/`): 外部連携の具象実装

### 主要APIエンドポイント
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

---

## マーケティングAI チャット 詳細設計

### アーキテクチャ (2026-02-02 大規模改修後)
```
Frontend (カスタムReact) → Next.js API Route (SSE proxy) → FastAPI → MarketingAgentService → Agents SDK → OpenAI API
```

**ChatKit SDKを完全廃止**し、直接Agents SDK + カスタムSSEストリーミング + ActivityItemタイムラインに移行。

### 主要ファイル
| ファイル | 役割 |
|---------|------|
| `backend/app/infrastructure/chatkit/agent_service.py` | MarketingAgentService: Runner.run_streamed() → Queue → SSE dict生成 |
| `backend/app/infrastructure/chatkit/seo_agent_factory.py` | Agent構築 (モデル, ツール, MCP, reasoning設定) |
| `backend/app/infrastructure/chatkit/keepalive.py` | SSEキープアライブ (20秒間隔でdict型イベント) |
| `backend/app/infrastructure/chatkit/ask_user_store.py` | ask_user構造化質問のインメモリストア |
| `backend/app/infrastructure/chatkit/model_assets.py` | モデルプリセット管理 |
| `backend/app/infrastructure/chatkit/context.py` | リクエストコンテキスト |
| `backend/app/presentation/api/v1/marketing_chat.py` | SSEストリーミング + スレッドCRUDルーター |
| `backend/app/presentation/api/v1/marketing.py` | モデルアセット, 添付ファイル, 共有エンドポイント |
| `frontend/src/app/marketing/page.tsx` | メインチャットUI (~400行) |
| `frontend/src/hooks/use-marketing-chat.ts` | カスタムSSEフック (fetch + ReadableStream) |
| `frontend/src/lib/marketing-types.ts` | ActivityItem型定義, Message, StreamEvent等 |
| `frontend/src/components/marketing/chat/ChatWindow.tsx` | チャットウィンドウ + EmptyState |
| `frontend/src/components/marketing/chat/ChatMessage.tsx` | メッセージ表示 (ActivityItemタイムライン) |
| `frontend/src/components/marketing/chat/ChatInput.tsx` | 入力コンポーネント + モデルアセットセレクター |
| `frontend/src/components/marketing/chat/ThinkingIndicator.tsx` | 思考中アニメーション |
| `frontend/src/components/marketing/chat/HistoryPanel.tsx` | 会話履歴シートパネル |
| `frontend/src/app/api/marketing/chat/stream/route.ts` | SSEプロキシ |
| `frontend/src/app/api/marketing/chat/threads/route.ts` | スレッドCRUDプロキシ |
| `frontend/src/app/api/marketing/chatkit/start/route.ts` | JWT トークン生成 (保持) |

### SSEキープアライブ機構 (keepalive.py)
- **目的**: 長時間推論中のSSEタイムアウト防止
- **仕組み**: pump task + asyncio.Queue + wait_for(timeout=20s) パターン
- **イベント**: タイムアウト時に `{"type": "keepalive", "text": "📊 考え中…"}` dictを送信
- **適用箇所**: `agent_service.py` の `stream_chat()` メソッドで適用

### ActivityItemタイムライン
- `ReasoningActivityItem`: 思考過程 (日本語翻訳済み)
- `ToolActivityItem`: ツール実行 (名前, 引数, 出力)
- `TextActivityItem`: テキストコンテンツ
- `AskUserActivityItem`: 構造化質問 (choice/text/confirm)
- ストリーミング中は全アイテム表示、完了後はreasoning/toolを「思考 N · ツール M」に折りたたみ

### 推論翻訳機構
- `agent_service.py` の `translate_to_japanese()` で英語reasoning summaryを日本語に翻訳
- gpt-5-nano, effort=minimal で低コスト翻訳
- `marketing_chat.py` のイベントループ内でインライン実行

### MCP フェイルオーバー
- MCPツールリスト取得エラー時、失敗したMCPサーバーを除外してエージェントを再構築
- `_is_mcp_toollist_error()` でエラー判定
- `_infer_mcp_source()` でエラーソースのMCPサーバーを推定

### コンテキスト永続化
- `context_items` JSONB: Responses API `to_input_list()` をシリアライズして保存
- マルチターン会話で正確なコンテキストを維持
- フォールバック: context_itemsがない場合、メッセージ履歴から平文コンテキストを構築

---

## SDK バージョン & 技術的知見

### ChatKit SDK — 廃止済み (2026-02-02)
- Python SDK `openai-chatkit` と Frontend SDK `@openai/chatkit`, `@openai/chatkit-react` は完全に削除済み
- 代わりにカスタムSSEストリーミング + ActivityItemタイムラインパターンを使用

### OpenAI Agents SDK v0.7.0
- **ソース**: `backend/.venv/lib/python3.12/site-packages/agents/`
- **SSEキープアライブ**: **なし**
- `nest_handoff_history` デフォルトが `True`→`False` に変更 (v0.7.0)
- GPT-5.1/5.2 のデフォルト reasoning effort が `'none'` に変更

### OpenAI Responses API (SSE)
- **キープアライブ/ハートビート**: **なし** — OpenAI APIもSSEキープアライブを送信しない
- **Background mode** (`"background": true`): 長時間推論タスクの公式ワークアラウンド
- **reasoning_summary streaming**: `reasoning.summary="detailed"` で推論中にイベントが流れるが、初期遅延やsummary間の間隔が長い場合がある
- **情報ソース**:
  - https://platform.openai.com/docs/api-reference/responses-streaming
  - https://platform.openai.com/docs/guides/streaming-responses
  - https://openai.github.io/openai-agents-python/streaming/

---

## Database Tables (Supabase PostgreSQL)

### ひとキャリ関連
| テーブル | 概要 |
|---------|------|
| `meeting_documents` | 議事録メタデータ・本文 (doc_id, title, meeting_datetime, text_content) |
| `structured_outputs` | Gemini抽出結果 (meeting_id FK, data JSONB) |
| `zoho_candidate_links` | 議事録→Zoho候補者マッピング (zoho_sync_status, sync_error) |
| `custom_schemas` | ユーザー定義抽出スキーマ |
| `schema_fields` | スキーマフィールド定義 |
| `field_enum_options` | フィールド列挙値 |
| `ai_usage_logs` | AI API トークン使用量追跡 |

### マーケティングAI関連
| テーブル | 概要 |
|---------|------|
| `marketing_conversations` | ChatKitスレッドメタデータ (owner_email, status, pinned_insights) |
| `marketing_messages` | メッセージ (role, content JSONB, tool_calls JSONB) |
| `marketing_attachments` | ファイルアップロード |
| `marketing_articles` | 記事キャンバス (title, outline, body_markdown) |
| `marketing_model_assets` | モデルプリセット (model_id, reasoning_effort, web_search等) |
| `chat_shares` | スレッド共有権限 |

### 画像生成関連
| テーブル | 概要 |
|---------|------|
| `image_gen_templates` | スタイルテンプレート |
| `image_gen_references` | リファレンス画像 |
| `image_gen_sessions` | 生成セッション |
| `image_gen_messages` | セッション内メッセージ |

---

## Frontend Routes

| Path | 概要 |
|------|------|
| `/` | ダッシュボード (サービスカード) |
| `/hitocari` | 議事録一覧 (ページネーション, フィルタ) |
| `/hitocari/[id]` | 議事録詳細 (トランスクリプト, 構造化データ) |
| `/hitocari/mypage` | マイページ |
| `/hitocari/settings` | 設定 |
| `/marketing` | マーケティングAIチャット (ChatKit) |
| `/marketing/[threadId]` | チャットスレッド詳細 |
| `/marketing/dashboard` | 会話一覧 |
| `/marketing/image-gen` | 画像生成UI |
| `/sign-in`, `/sign-up` | Clerk認証 |
| `/unauthorized` | アクセス拒否 |

---

## Environment Variables

### Backend (.env) — 主要項目
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

# マーケティングAI
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

# MCP Servers (optional)
GA4_MCP_SERVER_URL=
GSC_MCP_SERVER_URL=
AHREFS_MCP_SERVER_URL=
META_ADS_MCP_SERVER_URL=
WORDPRESS_MCP_SERVER_URL=

# Server
ENV=local  # local / production
CORS_ALLOW_ORIGINS=
LOG_LEVEL=INFO
```

### Frontend (.env.local) — 主要項目
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
ALLOWED_EMAIL_DOMAINS=bandq.jp
NEXT_PUBLIC_MARKETING_CHATKIT_URL=  # Backend ChatKitエンドポイント
MARKETING_CHATKIT_TOKEN_SECRET=     # Backend と一致必須
USE_LOCAL_BACKEND=true              # ローカル開発用
DEV_BACKEND_BASE=http://localhost:8000
```

---

## Development Commands

### Backend
```bash
cd backend
uv sync                                                    # 依存同期
uv run uvicorn app.main:app --reload --host 0.0.0.0       # 開発サーバー (port 8000)
uv run pytest                                              # テスト
```

### Frontend
```bash
cd frontend
bun install                                                # 依存インストール
bun dev                                                    # 開発サーバー (port 3000, Turbopack)
bun run build                                              # 本番ビルド
bun lint                                                   # ESLint
```

### Docker (Cloud Run)
```bash
docker build -t meet2gemini:latest backend/
docker run -p 8000:8080 -e SUPABASE_URL=... meet2gemini:latest
```

### Database
```bash
# Supabase CLIでマイグレーション適用
npx supabase db push
```

---

## Git Branching

- **main**: 本番ブランチ
- **develop**: 開発ブランチ
- **feat/***: フィーチャーブランチ → develop へPR
- コミットメッセージ: `type(scope): description` (feat, refactor, fix, chore)

---

## セッション内の変更履歴 (2026-02-01)

### 1. マーケティングAI SSEキープアライブ実装
**問題**: 推論量が多い場合 (reasoning_effort: high/xhigh)、`stream_agent_response()` がトークン出力開始まで30秒〜数分沈黙 → Cloud Run / Vercel / ブラウザがSSEタイムアウト

**調査結果**:
- ChatKit SDK (Python v1.6.0, Frontend v1.5.0): キープアライブ機能なし
- OpenAI Agents SDK (v0.7.0): キープアライブ機能なし
- OpenAI Responses API: SSEハートビートを送信しない
- `reasoning.summary="detailed"` で推論中にイベントは流れるが、初期遅延が問題

**実装**:
- **新規**: `backend/app/infrastructure/chatkit/keepalive.py`
  - `with_keepalive(events, interval=20)` async generator
  - pump task + asyncio.Queue + wait_for(timeout) パターン
  - `_DoneSentinel` / `_ExceptionSentinel` で完了/例外を伝搬
  - `finally` で pump task を確実にキャンセル

- **変更**: `backend/app/infrastructure/chatkit/marketing_server.py`
  - メイン・フォールバック両ストリームを `with_keepalive()` でラップ

- **変更**: `backend/app/infrastructure/chatkit/tool_events.py`
  - `ToolUsageTracker` に `_bg_tasks` + `_fire_and_forget()` 追加
  - DB書き込み (`_save_tool_call_as_context`, `_save_tool_output_as_context`) を非同期化
  - `close()` で未完了タスクを10秒タイムアウトで待機

- **変更**: `frontend/src/app/marketing/page.tsx`
  - カスタム経過時間UIを追加後、ユーザーの指摘により**完全削除** → ChatKitネイティブ推論表示に委ねる

### 2. SDKバージョンアップ (ユーザーが実施)
- Backend: chatkit 1.5.3→1.6.0, agents 0.6.9→0.7.0, openai 2.15.0→2.16.0
- Frontend: chatkit 1.4.0→1.5.0, chatkit-react 1.4.2→1.4.3
- 破壊的変更なし（調査済み）

### 3. Supabaseエグレス削減 (2026-02-02)
**問題**: PostgRESTエグレスが908MB/日 (100%)、月間21.32GB でFree Plan (5GB) を大幅超過

**原因分析**:
- `collect-task` が30分〜2時間毎に実行され、全ドキュメントに対して `get_by_doc_and_organizer()` で `select("*")` (text_content含む) を毎回取得
- 変更チェックには `metadata.modifiedTime` しか不要なのに、5-50KB/件の text_content を毎回返却
- `upsert_meeting()`, `upsert_structured()`, `update_zoho_sync_status()` が返却値を使わないのに全カラムをレスポンスで受信
- ChatKit `load_threads()` で N+1 問題（スレッド一覧取得後、各スレッドを個別に再取得）

**修正内容**:
- **`meeting_repository_impl.py`**:
  - `get_by_doc_and_organizer()`: `select("*")` → `select("id,metadata")` — **最大の削減効果**
  - `upsert_meeting()`: `returning="minimal"` で返却データ抑制
  - `list_meetings()` (レガシー): `select("*")` → 軽量フィールドのみ (text_content除外)
  - `get_meeting()`: `select("*")` → 明示的カラム指定
  - `update_transcript()`: `returning="minimal"` で返却データ抑制

- **`structured_repository_impl.py`**:
  - `upsert_structured()`: `returning="minimal"` で data JSONB 返却抑制
  - `upsert_structured_legacy()`: 同上
  - `update_zoho_sync_status()`: `returning="minimal"` で data JSONB 返却抑制

- **`ai_usage_repository_impl.py`**:
  - `insert_many()`: `returning="minimal"` で返却データ抑制

- **`supabase_store.py`** (ChatKit):
  - `load_threads()`: N+1解消 — `_row_to_thread()` ヘルパーで取得済み行データを直接変換
  - `add_thread_item()`: upsert/update に `returning="minimal"` 追加
  - `save_item()`: update に `returning="minimal"` 追加

**技術的知見**:
- supabase-py (postgrest) の upsert/update/insert/delete は `returning` パラメータを受け付ける
- `returning="minimal"` で PostgREST が `Prefer: return=minimal` ヘッダーを送信し、レスポンスボディが空になる
- `ReturnMethod` enum は `postgrest.types` に定義: `minimal` / `representation`

**期待効果**: 908MB/日 → ~50-100MB/日 (Free Plan 5GB内に収まる見込み)

### 4. マーケティングAI ChatKit→カスタムSSE大規模改修 (2026-02-02)

**概要**: ChatKit SDK (Python `openai-chatkit`, Frontend `@openai/chatkit-react`) を完全廃止し、ga4-oauth-aiagentプロジェクトのパターンに基づく直接Agents SDK + カスタムSSE + ActivityItemタイムラインアーキテクチャに移行。

**変更範囲**:

**新規作成**:
- `supabase/migrations/0020_add_context_activity_items.sql` — context_items, activity_items カラム追加
- `backend/app/infrastructure/chatkit/agent_service.py` — MarketingAgentService (Runner.run_streamed → Queue → SSE dict)
- `backend/app/infrastructure/chatkit/ask_user_store.py` — 構造化質問のインメモリストア
- `backend/app/presentation/api/v1/marketing_chat.py` — SSEストリーミング + スレッドCRUDルーター
- `frontend/src/lib/marketing-types.ts` — ActivityItem型定義
- `frontend/src/hooks/use-marketing-chat.ts` — カスタムSSEフック
- `frontend/src/components/marketing/chat/` — ChatWindow, ChatMessage, ChatInput, ThinkingIndicator, HistoryPanel
- `frontend/src/app/api/marketing/chat/` — stream, respond, threads プロキシルート

**大幅修正**:
- `backend/app/infrastructure/chatkit/keepalive.py` — ChatKit型 → dict型
- `backend/app/presentation/api/v1/marketing.py` — ChatKitエンドポイント削除、共有を直接Supabaseクエリに変更
- `frontend/src/app/marketing/page.tsx` — 1056行 → ~400行に簡素化
- `frontend/src/app/globals.css` — ThinkingIndicatorアニメーション追加
- `frontend/src/components/marketing/share-dialog.tsx` — import先をmarketing-types.tsに変更

**削除**:
- `backend/app/infrastructure/chatkit/marketing_server.py` — agent_service.pyに置換
- `backend/app/infrastructure/chatkit/supabase_store.py` — 直接DBクエリに置換
- `backend/app/infrastructure/chatkit/tool_events.py` — agent_serviceに統合
- `backend/app/infrastructure/chatkit/attachment_store.py` — 未使用
- `backend/app/infrastructure/chatkit/seo_article_tools.py` — 無効化済み(コメントアウト)
- `frontend/src/hooks/use-marketing-chatkit.ts` — use-marketing-chat.tsに置換
- `frontend/src/app/api/marketing/chatkit/server/route.ts` — chat/stream/route.tsに置換

**パッケージ削除**: `openai-chatkit` (Python), `@openai/chatkit`, `@openai/chatkit-react` (Frontend)

### 5. クロスチェック修正 (2026-02-02)
**問題**: 参考プロジェクト (ga4-oauth-aiagent) との比較で、重要な機能が欠落していることが判明

**agent_service.py 修正内容**:
- **ChatContext dataclass 追加**: `emit_event` コールバック + `ask_user_store` + `conversation_id` を持つコンテキスト
- **ask_user @function_tool 追加**: `ToolContext[ChatContext]` 経由で `emit_event` を呼び、質問をSSEストリームに送出。`asyncio.wait_for(timeout=300)` でユーザー応答を待機
- **Queue multiplexing をサービスレベルに移動**: `_run_streamed()` 内で queue を作成し、`emit_event` → queue → yield の経路を確立。SDK stream events と ask_user 等の out-of-band events を統合
- **`context=chat_context` を Runner.run_streamed() に渡す**: ToolContext 経由でツール関数が ChatContext にアクセス可能に
- **`done` イベントを最後に yield**: `_run_streamed()` 終了時に `{"type": "done"}` を送出（参考プロジェクトと同じ）
- **`_ask_user_responses` 内部イベント**: ユーザー回答をルーターが activity_items に永続化できるよう emit

**marketing_chat.py 修正内容**:
- **`tool_calls_data` トラッキング追加**: tool_call イベントを蓄積（参考プロジェクトと同じ）
- **`ask_user` イベントの activity_items 蓄積追加**: kind="ask_user", groupId, questions
- **`_ask_user_responses` インターセプション追加**: 内部イベントを受信し、対応する ask_user activity_item に responses を永続化。クライアントには送信しない
- **content 保存形式を plain text に修正**: `json.dumps({"type": "text", "text": ...})` → `full_response or ""` (plain string)
- **user message 保存も plain text に修正**: `json.dumps(...)` → `body.message` (plain string)
- **try/except フォールバック追加**: activity_items カラムが未存在の場合のフォールバック

**技術的知見**:
- `Runner.run_streamed()` の `context=` パラメータに ChatContext を渡すと、`@function_tool` の `ToolContext[ChatContext]` で `ctx.context` 経由でアクセス可能
- out-of-band events (ask_user, chart 等) は `emit_event` → queue に put し、SDK events と同じ queue から yield することで統合ストリームを実現
- `_ask_user_responses` は内部イベントとしてルーターで消費し、activity_items の永続化に使用。クライアントには送信しない

---

## 自己改善ログ

> ユーザーから指摘された失敗・判断ミス・非効率を記録し、同じ過ちを繰り返さないための学習記録。

### 2026-02-01
- **カスタムUIの過剰実装**: SSE問題の対策としてフロントエンドにカスタム経過時間インジケーターを実装したが、ユーザーに「まったくよくありません。しっかりとChatkitの仕様に合わせてやってほしい。カスタムUIでやる必要はありません。思考過程とかもちゃんとchatkitでできるようになっています」と強く指摘された。**SDKの公式機能を先に徹底的に調査し、ネイティブ機能で解決できるかを最優先で確認すべき。カスタム実装は最終手段。**
- **SDK機能の調査不足**: ChatKit SDKの `WorkflowItem(type="reasoning")` + `ThoughtTask` によるネイティブ推論表示を最初に見落としていた。**外部SDKを使う場合、まずソースコードを全て読んで機能を把握してから設計に入るべき。**
- **記憶ファイル (CLAUDE.md) の未整備**: プロジェクトの記憶が全くない状態で作業していた。新しいプロジェクトを開始する時点で、まずCLAUDE.mdを作成・整備すべき。

---

> ## **【最重要・再掲】記憶の更新は絶対に忘れるな**
> **このファイルの冒頭にも書いたが、改めて念押しする。**
> 作業が完了したら、コミットする前に、必ずこのファイルに変更内容を記録せよ。
> 新しいファイルを作成した、既存ファイルを変更した、設計を変更した、バグを見つけた、知見を得た — すべて記録対象。
> **「後で更新しよう」は禁止。今すぐ更新せよ。**
