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
2. **マーケティングAIチャット**: OpenAI Agents SDK ネイティブSSEストリーミングによるSEO/コンテンツ戦略アシスタント（GPT-5.2対応、Web Search / Code Interpreter / MCP連携、Sub-Agent詳細表示）
3. **画像生成**: Gemini 2.5 Pro によるAI画像生成（テンプレート・リファレンス画像・セッション管理）

---

## Tech Stack

### Backend
- **Framework**: FastAPI + Uvicorn (Python 3.12)
- **Package Manager**: uv
- **AI/ML**: Google GenAI (Gemini 2.5 Pro/Flash), OpenAI Agents SDK 0.7.0, OpenAI ChatKit 1.6.0
- **Database**: Supabase (PostgreSQL HTTP API, RLS対応)
- **Authentication**: Clerk JWT + ドメイン制限 (@bandq.jp)
- **External APIs**: Zoho CRM SDK, Google Drive/Docs API, Google Cloud Tasks, Google Cloud Storage
- **MCP Servers**: GA4, GSC (ローカルSTDIO対応), Ahrefs, Meta Ads, WordPress (オプション)

### Frontend
- **Framework**: Next.js 16 + React 19 + TypeScript
- **Package Manager**: Bun
- **UI**: Tailwind CSS 4 + shadcn/ui (Radix UI) + Lucide React
- **Auth**: @clerk/nextjs (Google OAuth, @bandq.jp ドメイン制限)
- **Chat**: Native SSE streaming (ChatKit完全削除済み)
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

## ChatKit & マーケティングAI 詳細設計

### アーキテクチャ
```
Frontend (ChatKit React) → Next.js API Route (SSE proxy) → FastAPI → ChatKitServer → Agents SDK → OpenAI API
```

### 主要ファイル
| ファイル | 役割 |
|---------|------|
| `backend/app/infrastructure/chatkit/marketing_server.py` | ChatKitServerサブクラス。respond()でエージェントストリーム生成 |
| `backend/app/infrastructure/chatkit/seo_agent_factory.py` | Agent構築 (モデル, ツール, MCP, reasoning設定) |
| `backend/app/infrastructure/chatkit/mcp_manager.py` | MCPサーバーライフサイクル管理 (ローカルSTDIO) |
| `backend/app/infrastructure/chatkit/tool_events.py` | ToolUsageTracker: ツール実行のUI表示+DB保存 |
| `backend/app/infrastructure/chatkit/keepalive.py` | SSEキープアライブ (20秒間隔でProgressUpdateEvent) |
| `backend/app/infrastructure/chatkit/supabase_store.py` | ChatKit用Supabaseストア |
| `backend/app/infrastructure/chatkit/model_assets.py` | モデルプリセット管理 |
| `backend/app/infrastructure/chatkit/context.py` | リクエストコンテキスト |
| `backend/scripts/gsc_server.py` | GSC MCPサーバー (FastMCP, ローカルSTDIO) |
| `frontend/src/app/marketing/page.tsx` | メインチャットUI (1000+行) |
| `frontend/src/hooks/use-marketing-chatkit.ts` | ChatKitフック (streaming, attachments, sharing) |
| `frontend/src/app/api/marketing/chatkit/start/route.ts` | JWT トークン生成 |

### SSEキープアライブ機構 (keepalive.py)
- **目的**: 長時間推論 (reasoning_effort: high/xhigh) 中のSSEタイムアウト防止
- **仕組み**: pump task + asyncio.Queue + wait_for(timeout=20s) パターン
- **イベント**: タイムアウト時に `ProgressUpdateEvent(text="📊 考え中…")` を送信
- **適用箇所**: `marketing_server.py` の `respond()` メソッドでメイン・フォールバック両ストリームに適用

### ChatKit ネイティブ推論表示
- ChatKit agents.py L622-743 で `response.reasoning_summary_text.delta/done` を自動処理
- `WorkflowItem(type="reasoning")` + `ThoughtTask` でUI表示
- `seo_agent_factory.py` で `Reasoning(effort=..., summary="detailed")` を設定

### ToolUsageTracker の非同期DB書き込み
- `_fire_and_forget()` でDB保存を非ブロッキング化
- `_save_tool_call_as_context()`, `_save_tool_output_as_context()` が対象
- `close()` で未完了タスクを10秒タイムアウトで待機

---

## SDK バージョン & 技術的知見

### ChatKit Python SDK v1.6.0
- **ソース**: `backend/.venv/lib/python3.12/site-packages/chatkit/`
- **SSEキープアライブ**: **なし** — SDK側にはキープアライブ機能が存在しない。カスタム `keepalive.py` が必要
- **ProgressUpdateEvent**: 型は `chatkit/types.py` に定義済み。複数回安全に送信可能
- **推論表示**: `chatkit/agents.py` の `stream_agent_response()` が `response.reasoning_summary_text.delta/done` を自動処理し `WorkflowItem(type="reasoning")` + `ThoughtTask` として出力
- **キャンセル対応**: v1.6.0 で `handle_stream_cancelled()` が改善。`pending_items` の追跡と保存

### ChatKit Frontend SDK v1.5.0 / React v1.4.3
- **ソース**: `frontend/node_modules/@openai/chatkit/`, `@openai/chatkit-react/`
- **SSEキープアライブ**: **なし** — フロントエンド側にもタイムアウト対策は存在しない
- 推論表示はネイティブでサポート（WorkflowItem rendering）

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

### 4. Zoho CRM 日付フィルタリングバグ修正 (2026-02-03)
**問題**: マーケティングチャットのZoho API統合で、日付フィルタ（date_from/date_to）を指定すると0件が返る

**調査結果**:
- Zoho CRM Search API は、カスタムモジュール（jobSeeker）で日付/日時フィールドの**比較演算子**（`greater_equal`, `less_equal`, `between`等）を**サポートしていない**
- `equals` 演算子のみ動作する（完全一致のみ）
- エラーメッセージ: `{"code":"INVALID_QUERY","details":{"reason":"invalid operator found","api_name":"Created_Time","operator":"greater_equal"}}`
- COQL（CRM Object Query Language）はOAuthスコープ不足で使用不可

**根本原因**:
- `backend/app/infrastructure/zoho/client.py` L338-342 で `Created_Time:greater_equal:...` を使用していたが、Zoho Search APIがこの演算子をサポートしていない
- Zohoドキュメントには「サポートされている」と記載があるが、実際にはカスタムモジュールでは動作しない

**修正内容** (`backend/app/infrastructure/zoho/client.py`):
- **新規メソッド**: `_fetch_all_records()` — Records APIで全件取得（ページング対応、max_pages=15）
- **新規メソッド**: `_filter_by_date()` — `field18`（登録日）でクライアントサイドフィルタリング
- **修正**: `search_by_criteria()` — 日付フィルタがある場合はRecords API + クライアントサイドフィルタに切り替え
- **新規定数**: `DATE_FIELD_API = "field18"` — 登録日フィールド（YYYY-MM-DD形式）
- **返却データ変更**: `登録日` を `Created_Time` から `field18` に変更（正しい登録日を返す）

**修正前後の結果**:
| クエリ | 修正前 | 修正後 |
|--------|--------|--------|
| 日付フィルタ (2026-01) | 0件 | 100件 |
| paid_meta + 日付 (2026-01) | 0件 | **83件** |

**追加最適化** (パフォーマンス問題修正):
- 当初の修正では `count_by_channel()` が17チャネル分、`count_by_status()` が19ステータス分のAPI呼び出しを行っていた
- 各呼び出しで全件取得（最大15ページ）を行うため、最大 17×15=255 回のAPI呼び出しが発生
- **解決**: 集計系メソッドは1回だけ全件取得し、メモリ内でフィルタ・集計するように最適化
- **効果**: 最適化前 ~255秒 → 最適化後 ~12秒 (約20倍高速化)

**技術的知見**:
- Zoho CRM Search API (`/crm/v2/{module}/search`) は、システムフィールド・カスタムフィールド問わず、日付/日時型で比較演算子が動作しない場合がある（モジュール依存）
- Records API (`/crm/v2/{module}`) + クライアントサイドフィルタは確実に動作する
- `field18` は登録日（date型、YYYY-MM-DD形式）、`Created_Time` はシステム作成日時（datetime型、ISO8601形式）
- 集計系クエリはN+1問題に注意（1回取得→メモリ集計がベストプラクティス）
- **情報ソース**: [Zoho CRM API Search Records](https://www.zoho.com/crm/developer/docs/api/v8/search-records.html)

### 5. Zoho CRM COQL最適化 & 新規マーケティングツール追加 (2026-02-03)

**背景**: OAuthスコープ拡張（`ZohoCRM.coql.READ`追加）により、COQL APIが使用可能に

**新スコープ**:
```
ZohoCRM.modules.READ,ZohoCRM.settings.ALL,ZohoCRM.users.READ,ZohoCRM.coql.READ,ZohoCRM.bulk.READ,offline_access
```

**COQL最適化結果**:
| メソッド | 最適化前 | 最適化後 | 改善倍率 |
|----------|----------|----------|---------|
| `search_by_criteria` | ~25秒 | 0.52秒 | **48倍** |
| `count_by_channel` | ~23秒 | 0.21秒 | **110倍** |
| `count_by_status` | ~26秒 | 0.25秒 | **104倍** |

**実装内容** (`backend/app/infrastructure/zoho/client.py`):

1. **COQLインフラ追加**:
   - `_coql_query()`: COQL APIエンドポイント (`/crm/v7/coql`) への汎用クエリ
   - `_coql_aggregate()`: GROUP BY + COUNT集計用ヘルパー
   - `_with_coql_fallback()`: COQL失敗時のレガシーAPIフォールバック

2. **既存メソッドのCOQL化**:
   - `search_by_criteria()`: 日付フィルタのみCOQL、channel/status/nameはメモリ内フィルタ
   - `count_by_channel()`: COQL GROUP BY集計
   - `count_by_status()`: channelフィルタがある場合はCOQL取得+メモリフィルタ

**Zoho COQL制限事項**（カスタムモジュール jobSeeker での検証結果）:
- **WHERE句が必須**: `missing clause` エラー → `WHERE id is not null` で回避
- **LIKE演算子非サポート**: `invalid operator found` → メモリ内フィルタで対応
- **フィールドタイプ混合でエラー**: picklist(field14) + date(field18) の同時WHERE不可 → 日付のみCOQL、他はメモリ
- **ORDER BY はWHERE必須**: WHERE句がないとエラー

**情報ソース**: [Zoho CRM COQL Overview](https://www.zoho.com/crm/developer/docs/api/v8/COQL-Overview.html)

**新規マーケティングツール追加** (`backend/app/infrastructure/chatkit/zoho_crm_tools.py`):

| ツール名 | 説明 |
|---------|------|
| `analyze_funnel_by_channel` | 特定チャネルのファネル分析（ステータス別転換率、ボトルネック特定） |
| `trend_analysis_by_period` | 月次/週次トレンド分析（前期比、増減方向） |
| `compare_channels` | 複数チャネル比較（獲得数、入社率ランキング） |
| `get_pic_performance` | 担当者別パフォーマンス（成約率ランキング） |

**ツール登録更新** (`ZOHO_CRM_TOOLS`):
```python
ZOHO_CRM_TOOLS = [
    # 基本ツール (5個)
    search_job_seekers, get_job_seeker_detail, get_channel_definitions,
    aggregate_by_channel, count_job_seekers_by_status,
    # 新規分析ツール (4個)
    analyze_funnel_by_channel, trend_analysis_by_period,
    compare_channels, get_pic_performance,
]
```

**エージェント指示更新** (`backend/app/infrastructure/chatkit/seo_agent_factory.py`):
- MARKETING_INSTRUCTIONSに新ツール説明と分析シナリオ例を追加

### 6. 候補者インサイトツール追加 (2026-02-03)

**背景**: Supabase構造化データ（議事録から抽出）とZoho CRMデータを組み合わせた高度な転職エージェント業務向けツールを追加

**Supabase構造化データスキーマ** (`backend/app/domain/schemas/structured_extraction_schema.py`):
| グループ | 主要フィールド |
|---------|--------------|
| 転職活動状況 | `transfer_activity_status`, `current_agents`, `companies_in_selection`, `other_offer_salary` |
| 転職理由・希望 | `transfer_reasons` (23種enum), `desired_timing`, `current_job_status`, `transfer_priorities` |
| 職歴・経験 | `career_history`, `current_duties`, `experience_industry` |
| 希望業界・職種 | `desired_industry`, `desired_position` |
| 年収・待遇 | `current_salary`, `desired_first_year_salary` |
| キャリアビジョン | `career_vision`, `business_vision` |

**新規ツールモジュール** (`backend/app/infrastructure/chatkit/candidate_insight_tools.py`):

| ツール名 | 説明 | 主な用途 |
|---------|------|---------|
| `analyze_competitor_risk` | 競合エージェント分析 | 他社利用状況、選考中企業、他社オファーから高リスク候補者特定 |
| `assess_candidate_urgency` | 緊急度評価 | 転職希望時期、離職状況、選考進捗から優先順位付け |
| `analyze_transfer_patterns` | 転職パターン分析 | 転職理由・動機の傾向分析（マーケティング施策参考） |
| `generate_candidate_briefing` | 候補者ブリーフィング | 面談前準備用のZoho+議事録データ統合表示 |

**ツール登録更新** (`CANDIDATE_INSIGHT_TOOLS`):
```python
CANDIDATE_INSIGHT_TOOLS = [
    analyze_competitor_risk,
    assess_candidate_urgency,
    analyze_transfer_patterns,
    generate_candidate_briefing,
]
```

**分析シナリオ例**:
1. **高リスク候補者特定**: `analyze_competitor_risk(channel="paid_meta")` → 他社オファーありの候補者を即フォロー
2. **本日の優先対応**: `assess_candidate_urgency()` → 「すぐにでも」「離職中」の候補者を優先
3. **転職理由傾向**: `analyze_transfer_patterns(group_by="reason")` → コンテンツ企画の参考
4. **面談準備**: `generate_candidate_briefing(record_id="...")` → 議事録から抽出した詳細情報を確認

**データアクセス設計**:
- Supabaseから`zoho_record_id`で紐付けられた構造化データを取得
- Zoho CRMの基本情報 + 議事録からの詳細情報を統合
- エグレス削減のため軽量カラムのみ取得

### 7. ローカルMCP移行実装 (2026-02-04)

**問題**: マーケティングエージェントのMCPサーバー（GA4, GSC, Meta Ads, Ahrefs, WordPress×2）がCloud Run上でリモート実行されており、エージェント初期化時に各MCPへ逐次接続するため15-30秒の遅延が発生

**解決策**: GA4/GSCをローカルSTDIO実行に移行（`MCPServerStdio`使用）し、初期化時間を1-2秒に短縮

**新規依存関係** (`backend/pyproject.toml`):
```toml
# Local MCP servers (STDIO)
"analytics-mcp>=0.1.1",  # GA4 MCP (PyPI)
"mcp>=1.0.0",            # FastMCP for GSC
"meta-ads-mcp>=1.0.0",   # Meta Ads MCP (PyPI)
```

**新規ファイル**:

1. **`backend/app/infrastructure/chatkit/mcp_manager.py`** — MCPサーバーライフサイクル管理
   - `MCPServerPair`: GA4/GSCサーバーインスタンスを保持するdataclass
   - `MCPSessionManager`: サーバー生成・設定管理
   - `create_ga4_server()`: `analytics-mcp`をSTDIOで起動
   - `create_gsc_server()`: カスタムGSCサーバーをSTDIOで起動
   - `create_server_pair()`: 設定に応じて有効なサーバーペアを生成

2. **`backend/scripts/gsc_server.py`** — GSC MCP サーバー（FastMCPベース）
   - ga4-oauth-aiagentのGSC実装をコピー・適用
   - サービスアカウント認証（`GOOGLE_APPLICATION_CREDENTIALS`環境変数経由）
   - 13+ツール: `list_properties`, `get_search_analytics`, `get_performance_overview`, `get_indexing_status`, `get_sitemaps`, `get_url_inspection` 等
   - `mcp.run(transport="stdio")` で実行

**変更ファイル**:

1. **`backend/app/infrastructure/config/settings.py`**:
   ```python
   # Local MCP settings (STDIO-based) - default enabled for faster initialization
   use_local_mcp: bool = os.getenv("USE_LOCAL_MCP", "true").lower() == "true"  # デフォルト有効
   local_mcp_ga4_enabled: bool = os.getenv("LOCAL_MCP_GA4_ENABLED", "true").lower() == "true"
   local_mcp_gsc_enabled: bool = os.getenv("LOCAL_MCP_GSC_ENABLED", "true").lower() == "true"
   local_mcp_meta_ads_enabled: bool = os.getenv("LOCAL_MCP_META_ADS_ENABLED", "true").lower() == "true"
   mcp_client_timeout_seconds: int = int(os.getenv("MCP_CLIENT_TIMEOUT_SECONDS", "120"))
   meta_access_token: str = os.getenv("META_ACCESS_TOKEN", "")
   ```

2. **`backend/app/infrastructure/chatkit/seo_agent_factory.py`**:
   - `build_agent()` に `mcp_servers` パラメータ追加
   - ローカルMCP有効時はGA4/GSCの`HostedMCPTool`をスキップ
   - `Agent`コンストラクタに`mcp_servers`を渡す

3. **`backend/app/infrastructure/chatkit/marketing_server.py`**:
   - `AsyncExitStack`でMCPサーバーのライフサイクル管理
   - `respond()`メソッド内でMCPサーバーを起動・接続
   - `finally`ブロックで`mcp_stack.aclose()`による確実なクリーンアップ
   - `get_marketing_chat_server()`で`MCPSessionManager`を生成・注入

4. **`backend/.env.example`**:
   - ローカルMCP設定セクション追加

**新規環境変数**:
```bash
# Local MCP 設定（デフォルト有効）
USE_LOCAL_MCP=true                # デフォルト有効（リモートMCP使用時はfalse）
LOCAL_MCP_GA4_ENABLED=true        # GA4ローカルMCP使用
LOCAL_MCP_GSC_ENABLED=true        # GSCローカルMCP使用
LOCAL_MCP_META_ADS_ENABLED=true   # Meta AdsローカルMCP使用
MCP_CLIENT_TIMEOUT_SECONDS=120    # MCPクライアントタイムアウト
META_ACCESS_TOKEN=                # Meta Ads用長寿命アクセストークン
```

**認証の互換性**:
| 項目 | HostedMCPTool (Before) | MCPServerStdio (After) |
|------|------------------------|------------------------|
| GA4認証 | HTTPヘッダー `Authorization` | `GOOGLE_APPLICATION_CREDENTIALS` |
| GSC認証 | HTTPヘッダー `x-api-key` | `GOOGLE_APPLICATION_CREDENTIALS` |
| Meta Ads認証 | HTTPヘッダー `Authorization` | `META_ACCESS_TOKEN` 環境変数 |
| 認証情報 | リモートMCPサーバーが管理 | **ローカル環境変数** |

**ハイブリッドアプローチ**:
- GA4/GSC/Meta Ads: ローカルSTDIO (`MCPServerStdio`) — 高速化対象
- Ahrefs/WordPress: 既存の`HostedMCPTool` — 変更なし（HTTP-RPCのまま）

**技術的知見**:
- `MCPServerStdio`: OpenAI Agents SDK (`agents.mcp`) のクラス。STDIOトランスポートでMCPサーバーをサブプロセス起動
- `MCPServerStdioParams`: `command`, `args`, `env` でサブプロセス設定
- `cache_tools_list=True`: ツール一覧をキャッシュして再接続を高速化
- `AsyncExitStack`: 複数の非同期コンテキストマネージャを動的に管理
- サービスアカウントパス解決: ファイルパスまたはインラインJSONの両方に対応

**期待効果**:
| 指標 | Before | After |
|------|--------|-------|
| MCP初期化時間 | 15-30秒 | 1-2秒 |
| SSEタイムアウトリスク | 高 | 低 |
| Cloud Run依存 | あり | なし（GA4/GSC/Meta Ads） |

**情報ソース**:
- [OpenAI Agents SDK MCP](https://openai.github.io/openai-agents-python/mcp/)
- [analytics-mcp PyPI](https://pypi.org/project/analytics-mcp/)
- [meta-ads-mcp PyPI](https://pypi.org/project/meta-ads-mcp/)
- 参考実装: `/home/als0028/study/shintairiku/ga4-oauth-aiagent` — GA4/GSC/Meta Ads/WordPress全てのローカルMCP実装例

### 8. Vercel SSEタイムアウト修正 (2026-02-04)

**問題**: マーケティングAIチャットで3-5分以上経過すると画面更新が停止する

**調査結果**:
- CLAUDE.mdには「maxDuration設定済み」と記載されていたが、**実際のコードには設定されていなかった**
- `X-Accel-Buffering: no` ヘッダーも未設定

**修正内容**:

1. **`frontend/src/app/api/marketing/chatkit/server/route.ts`**:
   ```typescript
   export const maxDuration = 300; // 5 minutes for Vercel Pro plan
   ```
   - L6に追加: Vercelのデフォルト60秒タイムアウトを5分に延長
   - `X-Accel-Buffering: no` ヘッダー追加: 中間プロキシのバッファリング無効化

2. **`backend/app/presentation/api/v1/marketing.py`**:
   - StreamingResponseヘッダーに `X-Accel-Buffering: no` 追加

**SSEタイムアウト対策の全体像**:
| レイヤー | 対策 | 設定値 |
|---------|------|--------|
| Vercel API Route | `maxDuration` | 300秒 |
| Backend keepalive | `ProgressUpdateEvent` | 20秒間隔 |
| レスポンスヘッダー | `X-Accel-Buffering: no` | Nginx/プロキシバッファ無効化 |
| レスポンスヘッダー | `Connection: keep-alive` | 接続維持 |
| レスポンスヘッダー | `Cache-Control: no-cache` | キャッシュ無効化 |

**タイムアウトチェーン（修正後）**:
```
t=0s    : ユーザーがメッセージ送信
t=1s    : Next.js API Route → Backend fetch 開始
t=20s   : Backend keepalive (ProgressUpdateEvent) ✅
t=40s   : Backend keepalive ✅
t=60s   : ✅ Vercel タイムアウト回避 (maxDuration=300)
...
t=300s  : Vercel maxDuration 上限 (Pro プラン最大)
```

**情報ソース**:
- [Vercel Functions Duration](https://vercel.com/docs/functions/configuring-functions/duration)
- 参考実装: `/home/als0028/study/shintairiku/ga4-oauth-aiagent` — `X-Accel-Buffering` ヘッダー使用例

### 9. ローカルMCPログ最適化 (2026-02-04)

**問題**: mcp_manager.pyのログが冗長（装飾的区切り線、重複メッセージ、絵文字）

**参照プロジェクト調査** (`/home/als0028/study/shintairiku/ga4-oauth-aiagent`):
- `print()` + `[Component]` プレフィックス形式
- 最小限のログ（接続成功/失敗のみ）
- サマリー: `[Agent] MCP servers total: X`

**最適化内容**:

1. **`mcp_manager.py`**:
   - 装飾的区切り線 (`====`, `----`) を削除
   - 各`create_*_server()`メソッドの重複ログ削除
   - 絵文字（✅⚠️❌⏭️）をプレーンテキストに変更

2. **`marketing_server.py`**:
   - 冗長なモード表示ログ削除

**最適化前:**
```
INFO ============================================================
INFO [Local MCP] Creating local MCP servers (STDIO transport)
INFO ============================================================
INFO Creating GA4 MCP server with service account: /path/to/sa.json...
INFO [Local MCP] ✅ GA4: enabled (analytics-mcp)
...
INFO [Local MCP] Summary: 2/3 servers ready
INFO ============================================================
INFO [MCP Mode] Using LOCAL MCP servers (STDIO transport)
INFO [MCP Mode] 2 local MCP server(s) connected
```

**最適化後:**
```
INFO [Local MCP] GA4: ready (analytics-mcp)
INFO [Local MCP] GSC: ready (gsc_server.py)
INFO [Local MCP] Meta Ads: skipped (no META_ACCESS_TOKEN)
INFO [Local MCP] Total: 2/3 servers ready
```

**技術的知見**:
- Cloud Runログ: 絵文字が正しく表示されない場合がある
- `logger.info()` vs `print()`: 本番環境では`logging`モジュールが推奨（構造化ログ、レベル制御）
- 情報密度: 1行で状態が分かるコンパクトなフォーマットが理想

### 10. Meta Ads MCPフォールバックバグ修正 (2026-02-04)

**問題**: マーケティングチャットで「Meta広告専用のツールAPIは登録されていません」と表示される

**根本原因分析**:
1. `seo_agent_factory.py`で`use_local_meta_ads`の判定が不完全だった:
   ```python
   # 修正前（バグ）
   use_local_meta_ads = self._settings.use_local_mcp and self._settings.local_mcp_meta_ads_enabled
   # → META_ACCESS_TOKEN未設定でもTrueになり、ホステッド版がスキップされる
   ```

2. `mcp_manager.create_meta_ads_server()`は`META_ACCESS_TOKEN`未設定時に`None`を返す
3. 結果: ホステッド版スキップ + ローカル版`None` = **ツール0個**

**修正内容**:

1. **`seo_agent_factory.py`** (L505-510):
   ```python
   # 修正後
   use_local_meta_ads = (
       self._settings.use_local_mcp
       and self._settings.local_mcp_meta_ads_enabled
       and self._settings.meta_access_token  # ← 追加: トークン存在確認
   )
   ```
   - `META_ACCESS_TOKEN`未設定時はホステッド版にフォールバック

2. **`mcp_manager.py`** (L222):
   ```python
   logger.info("[Local MCP] Meta Ads: skipped (no META_ACCESS_TOKEN, will use hosted if configured)")
   ```
   - フォールバック動作を明示するログメッセージに変更

**修正後の動作フロー**:

| 条件 | ローカルMCP | ホステッドMCP | 結果 |
|------|------------|--------------|------|
| `META_ACCESS_TOKEN`設定済み | 使用 | スキップ | ローカルツール使用 |
| `META_ACCESS_TOKEN`未設定 + ホステッドURL設定済み | スキップ | 使用 | ホステッドツール使用 |
| 両方未設定 | スキップ | スキップ | Meta Adsツールなし（正常） |

**技術的知見**:
- フラグベースのスキップロジックは、実際のリソース可用性も確認すべき
- 「有効化フラグ=true」と「実際に動作可能」は異なる概念
- フォールバックチェーンの設計時は各段階の前提条件を明確にする

### 11. マーケティングエージェントトークン最適化 (2026-02-04)

**問題**: OpenAIダッシュボードで入力トークンが約32,000を示しており、コストと応答時間に影響

**調査結果（12並列エージェントで調査）**:
1. システム指示: ~2,200トークン（チャネル/ステータス定義が重複）
2. MCP許可ツールリスト: 149ツール（多くが未使用または未実装）
3. ツールdocstring: 冗長な説明とサンプル

**最適化内容**:

1. **GSC許可リスト削減** (19→10ツール):
   - 削除: `add_site`, `delete_site`, `check_indexing_issues`, `list_sitemaps_enhanced`, `get_sitemap_details`, `submit_sitemap`, `delete_sitemap`, `manage_sitemaps`, `get_creator_info`（すべて未実装）

2. **Ahrefs許可リスト削減** (52→20ツール):
   - 書き込み系削除: `management-projects-create`, `management-project-competitors-post`, `management-keyword-list-keywords-put`, `management-project-keywords-put`
   - 低使用ツール削除: 32ツール

3. **Meta Ads許可リスト削減** (31→20ツール):
   - 書き込み系削除: `create_campaign`, `update_campaign`, `create_adset`, `update_adset`, `create_ad`, `update_ad`, `create_ad_creative`, `update_ad_creative`, `upload_ad_image`, `create_budget_schedule`
   - 不要ツール削除: `get_login_link`

4. **システム指示簡素化** (~5,100→809文字):
   - チャネル/ステータス定義を削除（`get_channel_definitions`ツールで取得可能）
   - 冗長なツール説明を削除
   - 分析シナリオ例をコンパクト化

5. **ツールdocstring簡素化**:
   - `zoho_crm_tools.py`: 9ツールのdocstringを1-2行に簡素化
   - `candidate_insight_tools.py`: 4ツールのdocstringを1行に簡素化

**最適化結果**:
| 指標 | Before | After | 削減率 |
|------|--------|-------|--------|
| MCP許可ツール数 | 149 | 97 | 35% |
| システム指示文字数 | ~5,100 | 809 | 84% |
| 入力トークン（13ツールテスト） | N/A | 1,351 | - |
| 推定フル入力トークン | ~32,000 | ~8,000 | 75% |

**テストスクリプト**: `backend/scripts/test_token_usage.py`
```bash
cd backend && uv run python scripts/test_token_usage.py
```

**技術的知見**:
- OpenAI Agents SDK: `result.raw_responses[i].usage` で各レスポンスのトークン使用量を取得
- MCP許可リストは`allowed_tools`でフィルタされるため、不要ツールはトークン消費のみ
- システム指示の情報は専用ツール（`get_channel_definitions`）に移動可能
- ツールdocstringは最初の1文が最も重要（OpenAI APIでトランケートされる場合あり）

### 12. マルチエージェントアーキテクチャ設計 (2026-02-04)

**背景**: 単一エージェント（97ツール）のコンテキスト問題を解決するため、マルチエージェント化を検討

**調査方法**: 8並列エージェントで大規模調査を実施
1. OpenAI Agents SDK マルチエージェント機能
2. Responses API マルチエージェント対応
3. 現コードベース分析
4. 群知能・Swarmアプローチ
5. Handoffパターン詳細
6. Tool Agentパターン詳細
7. コンテキスト最適化戦略
8. Claude Code内部アーキテクチャ

**主要調査結果**:

1. **OpenAI Agents SDK v0.7.0**:
   - `Handoff`: エージェント間で会話を引き継ぐ（履歴継承）
   - `Agent.as_tool()`: エージェントをツールとして呼び出す（制御維持）
   - `nest_handoff_history=True`: 履歴要約でトークン40-60%削減
   - `RunConfig`: グローバルハンドオフ設定

2. **推奨アーキテクチャ**: Router + 専門エージェント
   ```
   Router Agent (gpt-4.1-mini, 軽量)
     ├─ SEO Agent (GA4, GSC, Ahrefs, Web Search) - 37ツール
     ├─ Ads Agent (Meta Ads, GA4) - 26ツール
     ├─ CRM Agent (Zoho, Candidate Insight) - 13ツール
     └─ Content Agent (WordPress, Web Search, Code) - 30ツール
   ```

3. **期待効果**:
   | 指標 | 現状 | 目標 | 改善率 |
   |------|------|------|--------|
   | 入力トークン | ~11,000 | ~2,800 | -75% |
   | ツール数/エージェント | 97 | 25-35 | -67% |
   | レスポンス時間 | 8-12秒 | 2-4秒 | -70% |

4. **実装パターン**:
   - `handoff()`: 専門エージェントへの委譲
   - `@function_tool`: Sub-Agent as Tool
   - `asyncio.gather`: 独立タスクの並列実行
   - `nest_handoff_history=True`: コンテキスト圧縮

**設計ドキュメント**: `docs/multi-agent-architecture.md` (新規作成)

**実装ロードマップ**:
- Phase 1 (Week 1-2): Router + 専門エージェントファクトリー
- Phase 2 (Week 3-4): Handoff統合
- Phase 3 (Week 5-6): コンテキスト最適化
- Phase 4 (Week 7-8): 並列実行
- Phase 5 (Week 9-10): 本番デプロイ

**技術的知見**:
- `nest_handoff_history=False` がv0.7.0のデフォルト（明示的にTrue指定が必要）
- OpenAI Swarm → Agents SDK への進化（Swarmは教育・実験目的）
- Claude Codeはシングルエージェント + タスク管理パターン（サブエージェント分割ではない）
- 群知能パターン: Router, Hierarchical, Sequential, Concurrent

**情報ソース**:
- [OpenAI Agents SDK Documentation](https://openai.github.io/openai-agents-python/)
- [OpenAI Agents SDK Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [OpenAI Swarm GitHub](https://github.com/openai/swarm)
- SDK ソースコード: `agents/handoffs/`, `agents/run.py`, `agents/_run_impl.py`

### 9. Sub-Agent as Tool マルチエージェント調査 (2026-02-04)

**背景**: Router + Handoff方式の調査後、ユーザーからSub-Agent as Tool方式の提案があり、大規模調査を実施

**調査結果**: Sub-Agent as Tool方式を**推奨**

**Handoff vs Sub-Agent as Tool 比較**:
| 特性 | Handoff | Sub-Agent as Tool |
|------|---------|-------------------|
| 制御権 | 子に完全移譲 | 親が保持 ✅ |
| 並列実行 | 不可 | 可能 ✅ |
| エラー復旧 | 困難 | 親で対応可能 ✅ |
| 対話継続 | 途切れる | 継続可能 ✅ |

**結論**: マーケティングAIでは「親が制御を保持」「並列実行」「エラー復旧」が重要なため、Sub-Agent as Tool方式を採用

**推奨アーキテクチャ**:
```
Orchestrator (GPT-5.2) ─┬─ SEO Agent (GPT-5-mini)
                        ├─ Zoho Agent (GPT-5-mini)
                        └─ Candidate Agent (GPT-5-mini)
```

**Agent.as_tool() API**:
```python
sub_agent.as_tool(
    tool_name="run_seo_analysis",
    tool_description="SEO分析を実行",
    custom_output_extractor=lambda result: result.final_output,
    max_turns=20,
)
```

**並列実行パターン**:
```python
async with asyncio.TaskGroup() as tg:
    futures = [tg.create_task(run_agent(a)) for a in agents]
results = [f.result() for f in futures]
```

**コスト分析**:
- 単純クエリ (60%): GPT-5-mini単体 → ¥0.96/クエリ
- 中程度クエリ (30%): mini×2並列 → ¥1.5/クエリ
- 複雑クエリ (10%): 5.2 + mini×2 → ¥5.5/クエリ
- **加重平均**: ¥1.5/クエリ（現在の¥3-5から**50-70%削減**）

**ドキュメント更新**: `docs/multi-agent-architecture.md` → v2.0.0 (Sub-Agent as Tool方式)

**情報ソース**:
- SDK ソースコード: `agents/extensions/handoff_prompt.py` (as_tool実装)
- SDK ソースコード: `agents/tool.py` (FunctionTool)
- SDK ソースコード: `agents/run.py` (Runner.run)

### 10. Sub-Agent as Tool マルチエージェント実装 (2026-02-04)

**実装完了**: Sub-Agent as Tool アーキテクチャをマーケティングAIに統合

**新規ファイル** (`backend/app/infrastructure/chatkit/agents/`):
| ファイル | 説明 | ツール数 |
|---------|------|---------|
| `__init__.py` | モジュール初期化 | - |
| `base.py` | SubAgentFactory基底クラス（ネイティブツール共有） | - |
| `orchestrator.py` | OrchestratorAgentFactory (GPT-5.2) | 8 (6 sub-agent + 2 native) |
| `analytics_agent.py` | AnalyticsAgentFactory (GA4 + GSC) | 18 |
| `ad_platform_agent.py` | AdPlatformAgentFactory (Meta Ads) | 22 |
| `seo_agent.py` | SEOAgentFactory (Ahrefs) | 22 |
| `wordpress_agent.py` | WordPressAgentFactory (WP×2) | 54 |
| `zoho_crm_agent.py` | ZohoCRMAgentFactory | 11 |
| `candidate_insight_agent.py` | CandidateInsightAgentFactory | 6 |

**変更ファイル**:
- `marketing_server.py`: `MarketingAgentFactory` → `OrchestratorAgentFactory` に変更

**アーキテクチャ**:
```
Orchestrator (GPT-5.2) ─┬─ AnalyticsAgent (GA4+GSC, 16 MCP)
                        ├─ AdPlatformAgent (Meta, 20 MCP)
                        ├─ SEOAgent (Ahrefs, 20 MCP)
                        ├─ WordPressAgent (WP×2, 52 MCP)
                        ├─ ZohoCRMAgent (9 function)
                        └─ CandidateInsightAgent (4 function)
```

**全エージェントに共通のネイティブツール**:
- WebSearchTool (日本向け設定)
- CodeInterpreterTool

**期待効果**:
- ツール定義トークン: ~12,100 → ~800 (93%削減)
- 複合クエリ応答時間: 30-60秒 → 10-20秒 (並列実行)
- コスト: サブエージェントがGPT-5-miniを使用（大幅削減）

**検証コマンド**:
```bash
cd backend
uv run python -c "from app.infrastructure.chatkit.agents import OrchestratorAgentFactory; print('OK')"
```

### 11. SEOエージェント Ahrefs APIパラメータ仕様追加 (2026-02-04)

**問題**: SEOエージェントが225秒かかった。ログ分析の結果、Ahrefs APIのパラメータエラーが多発し、何度もリトライしていたことが判明。

**根本原因**: SEOエージェントのインストラクションにAhrefs APIの正確なパラメータ仕様が書かれていなかったため、エージェントが試行錯誤でパラメータを推測していた。

**失敗パターン（ログから判明）**:
| 試行 | エラー | 正しいパラメータ |
|------|--------|-----------------|
| `where: ""` | `bad where: invalid filter expression` | フィルタ不要なら**省略** |
| `volume_mode: "latest"` | `bad value latest for type enum` | 省略推奨 |
| `select: "domain"` | `column 'domain' not found` | `competitor_domain` |
| `order_by: "traffic_desc"` | `column 'traffic_desc' not found` | `traffic` + `order: "desc"` |

**修正内容** (`seo_agent.py`):

インストラクションを大幅拡充（約4倍のボリューム）:

1. **共通パラメータ仕様**:
   - `where/having`: 不要なら**パラメータごと省略**（空文字列禁止）
   - `order_by`: カラム名のみ（`traffic`）、方向は別パラメータ `order: "desc"`
   - `select`: 正確なカラム名をカンマ区切り
   - `where`構文例: `where: "traffic > 1000"`, `where: "position <= 10"`

2. **全20ツールの詳細仕様**:
   - 必須パラメータ / オプションパラメータを明記
   - 正確なカラム名一覧
   - 使用例コード

3. **主要カラム名（ログから判明）**:
   | ツール | 主要カラム |
   |--------|-----------|
   | `organic-competitors` | `competitor_domain` (※`domain`無効), `common_keywords`, `traffic` |
   | `organic-keywords` | `keyword`, `position`, `volume`, `traffic`, `difficulty`, `url` |
   | `top-pages` | `url`, `traffic`, `keywords`, `top_keyword`, `position` |
   | `anchors` | `anchor`, `referring_domains`, `referring_pages` |
   | `refdomains` | `domain`, `domain_rating`, `traffic`, `dofollow` |

**期待効果**:
- SEOエージェント応答時間: 225秒 → 30-60秒（リトライ削減）
- API呼び出し回数: 6-10回 → 1-2回（エラー回避）

**技術的知見**:
- Ahrefs MCP Server: https://github.com/ahrefs/ahrefs-mcp-server
- Ahrefs API v3: https://docs.ahrefs.com/docs/api/reference/introduction
- パラメータ仕様はドキュメント化が不十分なため、エラーログから逆算して仕様を把握
- `order_by`と`order`は**必ず別パラメータ**で指定
- `where`パラメータは空文字列`""`が**絶対に無効**（使わないなら省略）

### 12. ZohoCRMツール COQL最適化 (2026-02-04)

**問題**: ZohoCRMエージェントが`search_job_seekers`で58件取得後、58回の`get_job_seeker_detail`を並列呼び出し。全て"No output"でタイムアウト。

**解決策**: インストラクションで禁止するのではなく、**ツール自体を最適化**。

**修正内容**:

1. **新規ツール追加** (`zoho_crm_tools.py`):
   - `get_job_seekers_batch(record_ids: List[str])`: COQL IN句で最大50件一括取得

2. **クライアント改善** (`client.py`):
   - `get_app_hc_records_batch()`: COQL IN句でバッチ取得（詳細フィールド含む）

3. **既存ツール最適化**:
   | ツール | 最適化前 | 最適化後 |
   |--------|---------|---------|
   | `compare_channels` | チャネルごとに個別API | 1回取得→メモリ分割 |
   | `trend_analysis_by_period` | 期間ごとに個別API | 1回取得→メモリ分割 |

4. **インストラクション更新** (`zoho_crm_agent.py`):
   ```
   | 複数人の詳細 | get_job_seekers_batch（最大50件一括、COQL最適化） |
   ```

**技術的詳細**:
- COQL IN句: `SELECT * FROM jobSeeker WHERE id IN ('id1', 'id2', ...)`
- 詳細フィールド: 年齢、現年収、希望年収、経験業種/職種、転職希望時期など
- フォールバック: COQL失敗時は個別API呼び出し

**期待効果**:
| 操作 | 最適化前 | 最適化後 |
|------|---------|---------|
| 58件詳細取得 | 58回API | **1回API** |
| 5チャネル比較 | 5回API | **1回API** |
| 6ヶ月トレンド | 6回API | **1回API** |

---

## 自己改善ログ

> ユーザーから指摘された失敗・判断ミス・非効率を記録し、同じ過ちを繰り返さないための学習記録。

### 2026-02-01
- **カスタムUIの過剰実装**: SSE問題の対策としてフロントエンドにカスタム経過時間インジケーターを実装したが、ユーザーに「まったくよくありません。しっかりとChatkitの仕様に合わせてやってほしい。カスタムUIでやる必要はありません。思考過程とかもちゃんとchatkitでできるようになっています」と強く指摘された。**SDKの公式機能を先に徹底的に調査し、ネイティブ機能で解決できるかを最優先で確認すべき。カスタム実装は最終手段。**
- **SDK機能の調査不足**: ChatKit SDKの `WorkflowItem(type="reasoning")` + `ThoughtTask` によるネイティブ推論表示を最初に見落としていた。**外部SDKを使う場合、まずソースコードを全て読んで機能を把握してから設計に入るべき。**
- **記憶ファイル (CLAUDE.md) の未整備**: プロジェクトの記憶が全くない状態で作業していた。新しいプロジェクトを開始する時点で、まずCLAUDE.mdを作成・整備すべき。

### 2026-02-04
- **参考プロジェクトの不十分な調査**: ローカルMCP移行でGA4/GSCのみ対応し、Meta Ads MCPを見落とした。ユーザーに「なぜその3つのローカルサーバー環境変数を用意したの？」「META_ACCESS_TOKEN=の環境変数でできるはずだけど？もっとga4-oauth-aiagentちゃんと調べて」と指摘された。**参考プロジェクトを提示されたら、全ファイルを徹底的に読み、すべての機能を把握すること。部分的な実装は中途半端な結果を生む。**
- **段階的実装の過剰**: 「Phase 1: GA4/GSC」「Phase 2: Meta Ads」と勝手に段階を設けたが、ユーザーは全てローカル化したかった。**ユーザーの要件を正確に把握し、勝手に段階を設けず、要件通りに実装すること。**
- **UI/UXの不十分な実装**: ChatKit脱却後のUIがサブエージェント情報を表示していなかった。ユーザーに「まったくUIUXデザインもサブエージェントの内容も全く表示されてないし、最悪です」と指摘。**機能移行時は、単にバックエンド接続だけでなく、フロントエンドのUX品質（視覚的フィードバック、ステータス表示、デザイン）も同時に確認・実装すること。参考プロジェクトのUIコンポーネントも徹底的に調査すること。**

### 13. ChatKit → Native SSE ストリーミング移行実装 (2026-02-04)

**背景**: ChatKit SDK（`@openai/chatkit`, `@openai/chatkit-react`）依存を完全に排除し、OpenAI Agents SDKのネイティブストリーミングに移行

**参照プロジェクト**:
- `/home/als0028/study/shintairiku/ga4-oauth-aiagent` - SSEストリーミング実装パターン
- `/home/als0028/study/shintairiku/marketing-automation` - Blog AIのパターン

**ユーザー要件決定事項**:
- **サブエージェント表示**: 詳細表示（エージェント名、実行中ツール、推論内容をリアルタイム表示）
- **キャンバス機能**: 削除（SEO記事キャンバスは廃止）

**アーキテクチャ (After)**:
```
Frontend                           Backend
┌────────────────────────┐        ┌──────────────────────────────┐
│ useMarketingChat hook  │        │ MarketingAgentService        │
│ <MarketingChat>        │──SSE───│ Runner.run_streamed()        │
│ ActivityItems          │  ↑     │ Queue + pump task            │
│ (custom components)    │  │     │ _process_sdk_event()         │
└────────────────────────┘  │     └──────────────────────────────┘
                            │
                   data: {"type":"text_delta","content":"..."}
                   data: {"type":"sub_agent_event","agent":"SEO",...}
                   data: {"type":"done"}
```

**新規ファイル (Backend)**:
| ファイル | 説明 |
|---------|------|
| `backend/app/infrastructure/marketing/__init__.py` | モジュール初期化 |
| `backend/app/infrastructure/marketing/agent_service.py` | SDKイベント処理サービス（Queue + pump task パターン） |

**新規ファイル (Frontend)**:
| ファイル | 説明 |
|---------|------|
| `frontend/src/lib/marketing/types.ts` | SSEイベント型定義、ActivityItem型 |
| `frontend/src/hooks/use-marketing-chat.ts` | ネイティブSSEフック |
| `frontend/src/app/api/marketing/chat/stream/route.ts` | SSEプロキシエンドポイント |
| `frontend/src/components/marketing/MarketingChat.tsx` | メインチャットコンポーネント |
| `frontend/src/components/marketing/MessageList.tsx` | メッセージ一覧 |
| `frontend/src/components/marketing/ActivityItems.tsx` | アクティビティアイテム描画 |
| `frontend/src/components/marketing/ToolBadge.tsx` | ツール呼び出し表示 |
| `frontend/src/components/marketing/ReasoningLine.tsx` | 推論表示 |
| `frontend/src/components/marketing/SubAgentEvent.tsx` | サブエージェント詳細表示 |
| `frontend/src/components/marketing/Composer.tsx` | 入力コンポーザー |
| `frontend/src/components/marketing/index.ts` | エクスポートインデックス |

**変更ファイル**:
| ファイル | 変更内容 |
|---------|---------|
| `backend/app/infrastructure/chatkit/agents/orchestrator.py` | `on_sub_agent_stream` コールバック追加 |
| `backend/app/presentation/api/v1/marketing.py` | `/chat/stream` SSEエンドポイント追加 |

**SSEイベント型**:
```typescript
export type StreamEventType =
  | "text_delta"           // テキスト増分
  | "response_created"     // レスポンス境界
  | "tool_call"            // ツール呼び出し開始
  | "tool_result"          // ツール実行結果
  | "reasoning"            // 推論/思考
  | "sub_agent_event"      // サブエージェントイベント
  | "agent_updated"        // エージェント切り替え
  | "progress"             // キープアライブ
  | "done"                 // 完了
  | "error";               // エラー
```

**サブエージェントイベント詳細表示**:
- エージェント名: 色分けバッジ（Analytics=青、SEO=緑、Meta=紫、Zoho=オレンジ等）
- イベントタイプ: `tool_called`, `tool_output`, `reasoning`, `text_delta`, `message_output`
- ステータス: 実行中=スピナー、完了=チェックマーク

**技術的詳細**:
- `Queue + pump task` パターン: SDKストリームイベントとアウトオブバンドイベントをマルチプレクス
- `_SENTINEL` オブジェクト: ストリーム終了シグナル
- `on_stream` コールバック: `Agent.as_tool()` でサブエージェントイベントをキャプチャ
- キープアライブ: 20秒間隔で `{"type": "progress", "text": "処理中..."}` を送信
- コンテキスト永続化: `result.to_input_list()` で次ターン用にシリアライズ

**削除ファイル (Phase 4クリーンアップ)**:
- `frontend/src/hooks/use-marketing-chatkit.ts` - 旧ChatKitフック削除

**キャンバス関連削除 (Phase 4)**:
- `ModelAssetForm.tsx`: `enable_canvas` フィールドとTOOL_CONFIGエントリ削除
- `ModelAssetSelector.tsx`: `enable_canvas` フィールドとTOOL_ICONSエントリ削除
- `ModelAssetTable.tsx`: `enable_canvas` フィールドとTOOL_ICONSエントリ削除
- `types.ts`: `enable_canvas` フィールド削除

**移行ステータス**: ✅ 完了 (Phase 1-4)

**情報ソース**:
- [OpenAI Agents SDK Streaming](https://openai.github.io/openai-agents-python/streaming/)
- 参考実装: `ga4-oauth-aiagent/backend/app/services/agent_service.py`
- 参考実装: `ga4-oauth-aiagent/frontend/lib/hooks/useChat.ts`

### 14. マーケティングAI UI/UX 完全再実装 (2026-02-04)

**背景**: ChatKit脱却後、UI/UXとサブエージェント表示が不十分との指摘
- 「まったくUIUXデザインもサブエージェントの内容も全く表示されてないし、最悪です」

**参照プロジェクト**: `/home/als0028/study/shintairiku/ga4-oauth-aiagent`
- ChatWindow.tsx, ChatMessage.tsx, ThinkingIndicator.tsx, ChatInput.tsx
- Interleaved Timeline パターン（テキスト・ツール・推論・サブエージェントを到着順表示）

**新規・変更ファイル (Frontend)**:
| ファイル | 説明 |
|---------|------|
| `ThinkingIndicator.tsx` | 3ドットパルスアニメーション + ローテーションラベル |
| `ChatMessage.tsx` | 完全再実装 (560行): SubAgentBadge, ToolBadge, ReasoningLine, InterleavedTimeline |
| `Composer.tsx` | ChatGPT風カプセル入力（auto-resize, 停止ボタン） |
| `MessageList.tsx` | シンプル化、ChatMessage使用 |
| `MarketingChat.tsx` | 完全再設計: EmptyState, ヘッダー, アタッチメントパネル |
| `globals.css` | マーケティングチャット用スタイル追加 |

**UI設計ルール** (ga4-oauth-aiagent準拠):
| 項目 | 値 |
|------|-----|
| メインカラー | Navy #1a1a2e |
| グレー系 | #6b7280〜#f0f1f5 |
| アクセント | #e94560 (ピンク赤) |
| 成功色 | #10b981 (緑) |
| フォント | 本文 13-14px、補助 11px |
| 角丸 | rounded-xl (12px), rounded-2xl (16px) |
| メッセージ幅 | max-w-3xl mx-auto |

**サブエージェント色分け**:
| エージェント | 背景 | テキスト | ボーダー |
|-------------|------|---------|---------|
| Analytics | bg-blue-50 | text-blue-700 | border-blue-200 |
| SEO | bg-emerald-50 | text-emerald-700 | border-emerald-200 |
| Meta Ads | bg-purple-50 | text-purple-700 | border-purple-200 |
| Zoho | bg-orange-50 | text-orange-700 | border-orange-200 |
| Candidate | bg-amber-50 | text-amber-700 | border-amber-200 |
| WordPress | bg-cyan-50 | text-cyan-700 | border-cyan-200 |

**Interleaved Timeline 動作**:
1. **ストリーミング中**: 全アクティビティを到着順に展開表示
2. **完了後**: テキストは展開、activity (reasoning/tool/sub_agent) は折りたたみ

**ThinkingIndicator ラベルローテーション**:
```typescript
const LABELS = ["考えています", "データを確認しています", "分析しています", "情報を整理しています"];
// 3秒ごとにローテーション
```

**CSS アニメーション** (globals.css):
```css
.thinking-dot { animation: thinking-pulse 1.4s ease-in-out infinite; }
.thinking-dot-1 { animation-delay: 0s; }
.thinking-dot-2 { animation-delay: 0.2s; }
.thinking-dot-3 { animation-delay: 0.4s; }
```

**ビルドステータス**: ✅ 成功 (TypeScript + Next.js)

### 15. サブエージェントUI改善 & 思考過程翻訳 (2026-02-04)

**ユーザー指摘**:
- サブエージェントの実行がUIに表示されない
- 思考過程（reasoning）が英語のまま表示される

**改善内容**:

1. **思考過程の日本語翻訳** (Backend):
   - `settings.py`: `reasoning_translate_model` 設定追加 (デフォルト: `gpt-5-nano`)
   - `agent_service.py`: `_translate_to_japanese()` メソッド追加
   - `_process_reasoning_item()`: `_needs_translation` フラグ追加
   - `marketing.py`: SSE送信前に翻訳処理を実行

2. **サブエージェントカードUI** (Frontend):
   - `SubAgentCard`: 各サブエージェントをカード形式で表示
   - 実行中: グラデーションアイコン + パルスアニメーション + 「実行中」バッジ
   - 完了: コンパクト表示 + 「完了」バッジ + 自動折りたたみ
   - 内部にツール呼び出し・推論内容を表示

3. **エージェントごとのグループ化**:
   - `use-marketing-chat.ts`: サブエージェントイベントをエージェント単位でグループ化
   - `toolCalls`: 各エージェントのツール呼び出しを配列で追跡
   - `reasoningContent`: 推論内容を蓄積

4. **CSSアニメーション**:
   ```css
   .sub-agent-card-enter { animation: sub-agent-card-in 300ms ease-out; }
   .sub-agent-card-complete { animation: sub-agent-card-complete 400ms ease-out; }
   .sub-agent-running::before { animation: shimmer 2s infinite; }
   ```

**サブエージェント設定**:
| Agent | Label | Gradient | Icon |
|-------|-------|----------|------|
| analytics | Analytics | blue-cyan | BarChart3 |
| seo | SEO | emerald-teal | TrendingUp |
| ad_platform | Meta Ads | purple-pink | Megaphone |
| zoho_crm | Zoho CRM | orange-amber | Users |
| candidate_insight | Candidate Insight | amber-yellow | Users |
| wordpress | WordPress | cyan-sky | FileText |

**翻訳処理フロー**:
```
Backend: reasoning event → _needs_translation=True
       → marketing.py: _translate_to_japanese()
       → GPT-5-nano で翻訳
       → _needs_translation フラグ削除
       → SSEで日本語を送信
```

**ビルドステータス**: ✅ 成功

### 16. サブエージェントストリームイベント修正 (2026-02-04)

**問題**: サブエージェント（`call_seo_agent`, `call_zoho_crm_agent`等）がUIで「ぐるぐる回る」ツールコールとして表示されるが、サブエージェントの内部イベント（ツール呼び出し・推論・完了）が追跡・表示されない

**根本原因分析**:
1. `orchestrator.py`でコールバックが二重ラップされていた
2. SDKの`Agent.as_tool(on_stream=callback)`は`AgentToolStreamEvent`（TypedDict）を直接渡す
3. コールバックが`{"agent": agent, "event": event}`で再ラップしていたため、構造が破壊されていた

**SDKの`AgentToolStreamEvent`構造**:
```python
class AgentToolStreamEvent(TypedDict):
    event: StreamEvent      # 実際のストリームイベント
    agent: Agent[Any]       # イベントを発火したサブエージェント
    tool_call: ResponseFunctionToolCall | None  # 元のツール呼び出し
```

**修正内容**:

1. **`orchestrator.py`** - コールバック修正:
   ```python
   # Before (バグ)
   def make_callback(agent: Agent) -> Callable:
       async def callback(event: dict) -> None:
           await on_sub_agent_stream({"agent": agent, "event": event})
       return callback
   stream_callback = make_callback(sub_agent)

   # After (修正)
   stream_callback = on_sub_agent_stream  # 直接渡す
   ```

2. **`agent_service.py`** - イベント処理改善:
   - `on_sub_agent_stream()`: 詳細ログ追加、例外ハンドリング強化
   - `_process_sub_agent_event()`: `response.created` → `started` SSEイベント追加
   - サブエージェント開始時にUIカードを即時表示可能に

3. **`ChatMessage.tsx`** - エージェント名マッピング拡張:
   ```typescript
   // バックエンド名 (AnalyticsAgent, ZohoCRMAgent等) と
   // フロントエンド名 (analytics, zoho_crm等) の両方に対応
   SUB_AGENT_CONFIG = {
     analyticsagent: {...},
     analytics: {...},
     zohocrmagent: {...},
     zoho_crm: {...},
     // ...
   }
   ```

4. **`use-marketing-chat.ts`** - イベントハンドリング追加:
   - `started` イベントタイプ追加（サブエージェント開始時にカード作成）
   - デバッグ用 `console.log` 追加

5. **`types.ts`** - 型定義更新:
   ```typescript
   event_type: "started" | "tool_called" | "tool_output" | "reasoning" | "text_delta" | "message_output"
   ```

**期待されるイベントフロー**:
```
1. Orchestrator → call_seo_agent ツール呼び出し
2. SDK → on_stream(AgentToolStreamEvent) コールバック
3. agent_service → _process_sub_agent_event() でSSEイベント変換
4. Queue → SSE送信
5. Frontend → sub_agent_event 受信 → SubAgentCard 表示/更新
```

**デバッグログ**:
- Backend (INFO): `[Sub-agent] SEOAgent: received event type=run_item_stream_event`
- Backend (INFO): `[Sub-agent] SEOAgent: emitting SSE event={"type": "sub_agent_event", ...}`
- Frontend (console): `[Sub-agent event] {...}`

**技術的知見**:
- SDKの`Agent.as_tool(on_stream=callback)`は`AgentToolStreamEvent`を直接渡す
- コールバック内の例外はSDKがログに記録するが、呼び出し元には伝播しない（サイレント失敗）
- `response.created`イベントでサブエージェント開始を検知可能
- エージェント名の正規化: `AnalyticsAgent` → `analyticsagent` (`toLowerCase() + replace(/[^a-z0-9_]/g, "")`)

**情報ソース**:
- SDK ソースコード: `agents/agent.py` L406-539 (`as_tool`実装)
- SDK ソースコード: `agents/agent.py` L72-83 (`AgentToolStreamEvent` TypedDict)

**ビルドステータス**: ✅ 成功 (Backend + Frontend)

### 17. サブエージェントUI簡素化 & 自動スクロール修正 (2026-02-04)

**ユーザー指摘**:
- サブエージェントUIがカード形式で重すぎる
- 自動スクロールが頻繁に発生して使いにくい
- `raw_response_event` ログが大量に出力される

**修正内容**:

1. **SubAgentBadge** (インライン形式に変更):
   - `SubAgentCard` → `SubAgentBadge` に置き換え
   - ToolBadgeと同じインラインスタイル
   - 展開可能: ツール呼び出し・推論の詳細を表示
   - 実行中=グレー+スピナー、完了=グリーン+チェック

2. **ActivityTimeline** (インターリーブ表示):
   - sequence順にソートして到着順表示
   - 連続する同種アイテムをグループ化（コンパクト表示）

3. **MessageList** (スマートスクロール):
   - ユーザーが下部付近にいる場合のみ自動スクロール
   - 新しいメッセージ追加時のみスクロール
   - `isNearBottomRef` でスクロール位置を追跡

4. **ログ削減**:
   - `raw_response_event` をDEBUGレベルに変更
   - 重要イベント（started, tool_called, reasoning, message_output）のみINFO

5. **text_delta除外**:
   - サブエージェントのtext_deltaイベントをSSEから除外
   - オーケストレーターの最終出力に統合されるため不要

**技術的詳細**:
- サブエージェントの最終出力は `Agent.as_tool()` の戻り値としてオーケストレーターに返される
- オーケストレーターがその内容を統合して最終回答を生成
- フロントエンドにはオーケストレーターの `text_delta` として表示される
- これは **OpenAI Agents SDK の設計通り**

### 18. Native SSE実装 DB保存機能追加 (2026-02-04)

**問題発見**: 大規模調査の結果、Native SSE実装（`agent_service.py`）ではDB保存がまったく実装されていないことが判明

**影響**:
- 会話履歴が保存されない
- ページリロード/再訪問で会話が消失
- 会話ダッシュボードに表示されない

**参照プロジェクト**: `/home/als0028/study/shintairiku/ga4-oauth-aiagent/backend/app/routers/chat.py`

**実装内容**:

1. **`marketing.py` `/chat/stream` エンドポイント修正**:
   - ストリーム開始前: user message 保存
   - 新規会話: `marketing_conversations` に作成（タイトル自動生成）
   - `_context_items` イベント時: context_items を conversation.metadata に保存
   - ストリーム終了時: assistant message + activity_items を一括保存
   - `last_message_at` を更新

2. **DB保存データ構造**:
   ```python
   # marketing_messages.content (JSONB)
   {
       "text": "最終テキスト",
       "activity_items": [
           {"kind": "text", "sequence": 0, "content": "..."},
           {"kind": "tool", "sequence": 1, "name": "...", "output": "..."},
           {"kind": "reasoning", "sequence": 2, "content": "..."},
           {"kind": "sub_agent", "sequence": 3, "agent": "...", "event_type": "..."},
       ]
   }
   ```

3. **新規APIエンドポイント**:
   - `GET /api/v1/marketing/threads/{thread_id}` - 会話詳細 + メッセージ一覧取得
   - activity_items を含めてUI復元可能

4. **フロントエンドAPI Route追加**:
   - `frontend/src/app/api/marketing/threads/[id]/route.ts` - バックエンドプロキシ

5. **`use-marketing-chat.ts` 会話履歴ロード機能**:
   - `loadConversation(id)` - DBから会話をロード
   - `isLoading` 状態追加
   - `initialConversationId` 変更時に自動ロード
   - activity_items の復元（新規IDで再生成）
   - context_items の復元（次ターン継続用）

**2段階永続化パターン** (ga4-oauth-aiagent準拠):
| 項目 | 保存先 | 目的 |
|------|--------|------|
| context_items | conversations.metadata | Agent コンテキスト継続用 |
| activity_items | messages.content | UI復元用 |

**保存タイミング**:
```
1. user message: SSE開始前に即座保存
2. context_items: "_context_items"イベント時に保存
3. assistant message + activity_items: "done"イベント時に一括保存
```

**技術的知見**:
- `generate_thread_title()` を再利用（ChatKit実装から）
- activity_items の復元時はクライアント側で新規UUIDを生成
- context_items 優先: DB から復元 → リクエストbody でフォールバック

**ビルドステータス**: ✅ 成功 (Backend + Frontend)

### 19. サブエージェント Gemini 移行対応 (2026-02-04)

**背景**: マーケティングAIのサブエージェント（GPT-5-mini）をGemini 3 Flash Previewに移行可能にする

**調査結果**: OpenAI Agents SDK v0.7.0 は **LiteLLM 統合**で Gemini を完全サポート

**技術的詳細**:
- `agents.extensions.models.litellm_provider.LitellmProvider` がSDK組み込み済み
- `MultiProvider` がプレフィックスでルーティング（`litellm/` → LitellmProvider）
- `LitellmModel` にGemini固有処理実装済み:
  - `_fix_tool_message_ordering()`: ツールメッセージ順序修正
  - `_convert_gemini_extra_content_to_provider_specific_fields()`: thought_signature処理

**モデル指定形式**:
```python
# OpenAI (デフォルト)
model = "gpt-5-mini"

# Gemini via LiteLLM
model = "litellm/gemini/gemini-3-flash-preview"
```

**変更ファイル**:
| ファイル | 変更内容 |
|---------|---------|
| `backend/pyproject.toml` | `litellm>=1.55.0` 依存関係追加 |
| `backend/app/infrastructure/config/settings.py` | `sub_agent_model` 環境変数追加 |
| `backend/app/infrastructure/chatkit/agents/base.py` | `model` プロパティを設定から取得 |
| `backend/.env.example` | `SUB_AGENT_MODEL` ドキュメント追加 |

**環境変数**:
```bash
# Gemini サブエージェント有効化
SUB_AGENT_MODEL=litellm/gemini/gemini-3-flash-preview
GEMINI_API_KEY=your-gemini-api-key

# OpenAI のまま（デフォルト）
SUB_AGENT_MODEL=gpt-5-mini
```

**アーキテクチャ**:
```
Orchestrator (gpt-5.1, OpenAI)
    ├─ AnalyticsAgent ──→ Gemini 3 Flash (LiteLLM)
    ├─ SEOAgent ────────→ Gemini 3 Flash (LiteLLM)
    ├─ AdPlatformAgent ─→ Gemini 3 Flash (LiteLLM)
    ├─ WordPressAgent ──→ Gemini 3 Flash (LiteLLM)
    ├─ ZohoCRMAgent ────→ Gemini 3 Flash (LiteLLM)
    └─ CandidateAgent ──→ Gemini 3 Flash (LiteLLM)
```

**コスト比較**:
| モデル | 入力 | 出力 | 削減率 |
|--------|------|------|--------|
| gpt-5-mini | $1.10/1M | $4.40/1M | - |
| gemini-3-flash-preview | $0.50/1M | $3.00/1M | **~45%** |

**検証コマンド**:
```bash
# LiteLLM統合確認
uv run python -c "
from agents.models.multi_provider import MultiProvider
provider = MultiProvider()
model = provider.get_model('litellm/gemini/gemini-3-flash-preview')
print(f'{model.__class__.__name__}: {model.model}')
"
# 出力: LitellmModel: gemini/gemini-3-flash-preview
```

**発見した問題と修正** (2026-02-04 追記):

**大規模調査結果: Geminiサブエージェントは現時点で実用的ではない**

OpenAI Agents SDK の `chatcmpl_converter.py` L735-750 で、ChatCompletions API（LiteLLM/Gemini使用時）では以下が**明示的に拒否**される：

| ツール | Responses API (OpenAI) | ChatCompletions API (LiteLLM/Gemini) |
|--------|------------------------|-------------------------------------|
| `HostedMCPTool` (HTTP-RPC MCP) | ✅ | ❌ **拒否** |
| `WebSearchTool` | ✅ | ❌ **拒否** |
| `CodeInterpreterTool` | ✅ | ❌ **拒否** |
| `FileSearchTool` | ✅ | ❌ **拒否** |
| `FunctionTool` | ✅ | ✅ |
| `MCPServerStdio` (ローカルSTDIO) | ✅ | ✅ |

**現在のサブエージェント互換性**:
| エージェント | 使用ツール | Gemini対応 |
|-------------|-----------|-----------|
| AnalyticsAgent | `HostedMCPTool` | ❌ |
| SEOAgent | `HostedMCPTool` | ❌ |
| AdPlatformAgent | `HostedMCPTool` | ❌ |
| WordPressAgent | `HostedMCPTool` | ❌ |
| ZohoCRMAgent | `FunctionTool` | ✅ |
| CandidateInsightAgent | `FunctionTool` | ✅ |

**結論**: 6つ中4つのサブエージェントが `HostedMCPTool` を使用しているため、Gemini移行は不可。

**追加の制限事項** (LiteLLM GitHub Issues):
- Issue #13597: Responses API + MCP で認証エラー
- Issue #236: Tool calling + Structured Output 同時使用不可
- Gemini Sub-Agent as Tool パターンが動作しない

**修正内容**:
| メソッド | 変更 |
|---------|------|
| `is_litellm_model` | 新規プロパティ追加（`model.startswith("litellm/")` で判定） |
| `_get_native_tools()` | LiteLLMモデルの場合は空リストを返す |
| `_build_model_settings()` | 新規メソッド追加。LiteLLMモデルの場合はデフォルト設定を使用 |

**推奨**: `SUB_AGENT_MODEL` 環境変数を設定せず、デフォルト `gpt-5-mini` を使用

**情報ソース**:
- [OpenAI Agents SDK Models](https://openai.github.io/openai-agents-python/models/)
- [LiteLLM Integration](https://docs.litellm.ai/docs/projects/openai-agents)
- SDKソース: `agents/extensions/models/litellm_model.py`
- SDKソース: `agents/models/multi_provider.py`

### 20. リアルタイム表示バグ修正 (2026-02-04)

**報告された症状**:
1. Reactコンソールエラー: `Cannot update a component (MarketingPage) while rendering a different component (MarketingChat)`
2. メインエージェントの最終出力がDBには保存されるが、リアルタイムでは表示されない

**大規模調査結果**: 3並列エージェントで調査し、2つの重大なバグを特定

**問題1: React setState-during-render**

**原因** (`use-marketing-chat.ts` L356-357):
```typescript
case "done": {
  if (event.conversation_id) {
    setConversationId(event.conversation_id);
    onConversationChangeRef.current?.(event.conversation_id);  // ← 同期的に親state更新
  }
  break;
}
```

SSEストリーム処理中に`processEvent()`が呼ばれ、`onConversationChangeRef.current?.()`が同期的に親コンポーネントのsetStateを呼び出し、子コンポーネントのレンダリング中に親stateが更新される。

**修正**: `pendingConversationId` stateを追加し、`useEffect`で遅延実行

```typescript
// 新規state追加
const [pendingConversationId, setPendingConversationId] = useState<string | null | undefined>(undefined);

// 遅延実行useEffect
useEffect(() => {
  if (pendingConversationId !== undefined) {
    onConversationChangeRef.current?.(pendingConversationId);
    setPendingConversationId(undefined);
  }
}, [pendingConversationId]);

// processEvent内: 直接コールバックではなくstateをセット
case "done":
  setPendingConversationId(event.conversation_id);  // 遅延実行
```

**問題2: text_delta の silent no-op（致命的）**

**原因** (`use-marketing-chat.ts` L139-151):
```typescript
case "text_delta": {
  if (currentTextIdRef.current) {
    const textIdx = items.findIndex((i) => i.id === currentTextIdRef.current);
    if (textIdx !== -1) {
      // 更新
    }
    // ← textIdx === -1 の場合、何もしない！（silent no-op）
  } else {
    // 新規作成
  }
}
```

`currentTextIdRef.current`が設定されているが、`items.findIndex()`でそのIDが見つからない場合（エッジケース）、何も処理されずテキストが消失する。

**修正**: `textIdx === -1` の場合も新規item作成

```typescript
if (textIdx !== -1) {
  // 更新
} else {
  // ← 追加: item が見つからない場合は新規作成
  const newId = generateId();
  currentTextIdRef.current = newId;
  items.push({ id: newId, kind: "text", ... });
}
```

**修正対象ファイル**: `frontend/src/hooks/use-marketing-chat.ts`

**修正箇所**:
| 行 | 変更内容 |
|----|---------|
| L65 | `pendingConversationId` state追加 |
| L94-100 | 遅延実行useEffect追加 |
| L163-172 | text_delta の else 分岐追加 |
| L379 | `done` case で `setPendingConversationId` 使用 |
| L558 | `clearMessages` で `setPendingConversationId` 使用 |
| L565 | `handleSetConversationId` で `setPendingConversationId` 使用 |
| L635 | `loadConversation` で `setPendingConversationId` 使用 |

**技術的知見**:
- Reactでは子コンポーネントのレンダリング中に親コンポーネントのstateを更新してはならない
- コールバックを同期的に呼び出すと、その中のsetStateが親更新を引き起こす
- `useEffect`でコールバック実行を次のレンダリングサイクルに遅延させることで解決
- エッジケース（item not found）のハンドリングは静かに失敗するのではなく、フォールバック処理を入れるべき

### 21. レスポンス速度最適化 - LazyMCPServer実装 (2026-02-04)

**報告された症状**: 単純な「こんにちは」でも約5秒かかる

**ログ分析**:
```
22:03:43,201 - MCP servers ready logging (create_server_pair完了)
22:03:45,997 - [Local MCP] 3 servers initialized (~2.8秒遅延!)
22:03:46,014 - LiteLLM completion started
```

**根本原因分析**（大規模調査結果）:
- MCPサーバーは**サブエージェントが呼び出されたときだけ**使用される
- サブエージェントは**オーケストレーターがLLM判断で呼び出す**ときだけ実行される
- 単純クエリ（「こんにちは」）→ サブエージェント不要 → **MCP初期化が完全に無駄**

**解決策: LazyMCPServerラッパー**

**新規ファイル**: `backend/app/infrastructure/chatkit/lazy_mcp_server.py`

```python
class LazyMCPServer:
    """
    MCP接続をサブエージェントが実際に使用するまで遅延するラッパー.

    - 初期化時: 接続なし（即座に完了）
    - list_tools()呼び出し時: 初めて接続
    - call_tool()呼び出し時: 初めて接続
    """
    def __init__(self, server_factory, name, cache_tools_list=True):
        self._server_factory = server_factory
        self._server = None
        self._connected = False

    async def _ensure_connected(self):
        if not self._connected:
            self._server = self._server_factory()
            await self._server.__aenter__()
            self._connected = True
        return self._server

    async def list_tools(self, ...):
        server = await self._ensure_connected()  # ここで初めて接続
        return await server.list_tools(...)
```

**変更ファイル**:

1. **`mcp_manager.py`**:
   - `create_lazy_server_pair()` メソッド追加
   - LazyMCPServerでラップしたサーバーペアを返す

2. **`agent_service.py`**:
   - `create_server_pair()` → `create_lazy_server_pair()` に変更
   - キーワード検出ロジック削除（LazyLoadingで自動的にスキップ）
   - `AsyncExitStack` → `lazy_pair.cleanup_all()` に変更

**動作フロー**:

```
Before (Eager):
リクエスト開始
  ↓
[GA4接続] ~1秒
[GSC接続] ~1秒
[Meta接続] ~1秒
  ↓
オーケストレーター開始
  ↓ (単純クエリなら)
サブエージェント呼び出しなし → 3秒無駄

After (Lazy):
リクエスト開始
  ↓
[LazyWrapper作成] ~0ms (接続なし)
  ↓
オーケストレーター開始
  ↓ (単純クエリなら)
サブエージェント呼び出しなし → 0秒オーバーヘッド ✅
  ↓ (複雑クエリなら)
サブエージェント呼び出し → [ここで初めてMCP接続]
```

**期待される改善**:
| クエリタイプ | Before | After | 改善 |
|------------|--------|-------|------|
| 単純クエリ（こんにちは） | ~5秒 | **~1.5秒** | **-70%** |
| サブエージェント1つ | ~5秒 | ~3秒 | **-40%** |
| サブエージェント複数 | ~6秒 | ~4秒 | **-33%** |

**技術的知見**:
- OpenAI Agents SDK: `Agent.mcp_servers`に渡されたサーバーは、`list_tools()`が呼ばれるまで接続不要
- `list_tools()`は`Runner.run_streamed()`内でサブエージェントが実行される時に初めて呼ばれる
- LazyMCPServerは`asyncio.Lock()`で複数呼び出し時の重複接続を防止
- 参考: https://openai.github.io/openai-agents-python/mcp/

**情報ソース**:
- OpenAI Agents SDK MCP Documentation
- SDK Source: `agents/mcp/server.py` L367-403 (`list_tools()`)
- SDK Source: `agents/agent.py` L128-133 (`get_mcp_tools()`)

### 22. 会話履歴バグ修正 & オーバーヘッド最適化 (2026-02-04)

**背景**: 大規模調査（4並列エージェント）で致命的なバグとオーバーヘッドを特定

#### 🚨 致命的バグ: _context_items SSEイベント未送信

**問題発見**:
- `marketing.py` L838 で `continue` により `_context_items` イベントがSSEに送信されていなかった
- フロントエンドの `contextItemsRef.current` は常に `null`
- **複数ターンの会話で前のターンの文脈が完全に喪失**

**影響**:
```
Turn 1: User: "こんにちは"
  → Backend: context_items 生成・DB保存 ✓
  → SSE送信なし ✗
  → Frontend: contextItemsRef.current = null

Turn 2: User: "前の話について"
  → input_messages = [{"role": "user", "content": "前の話について"}] ← 前のターンが消失!
  → Agent: "前の話がわかりません" ← コンテキスト喪失
```

**修正** (`marketing.py` L838):
```python
# Before (バグ)
continue  # Don't send to client

# After (修正)
yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
continue
```

#### オーバーヘッド分析結果

大規模調査で特定されたボトルネック：

| ボトルネック | 時間 | 原因 | 対策 |
|-------------|------|------|------|
| Sub-Agent Build（逐次） | 1,400ms | 6エージェント逐次loop | (並列化検討中) |
| Native Tools再生成 | 300ms | 毎回新規インスタンス | ✅ キャッシュ実装 |
| Tool Definition再パース | 200ms | 毎回再生成 | (キャッシュ検討中) |

#### Native Tools キャッシュ実装

**修正ファイル**:
- `backend/app/infrastructure/chatkit/agents/base.py`
- `backend/app/infrastructure/chatkit/agents/orchestrator.py`

**実装**:
```python
# モジュールレベルキャッシュ
_NATIVE_TOOLS_CACHE: dict[str, list[Any]] = {}

def _get_native_tools(self) -> List[Any]:
    cache_key = self._settings.marketing_search_country
    if cache_key in _NATIVE_TOOLS_CACHE:
        return _NATIVE_TOOLS_CACHE[cache_key]

    # 作成してキャッシュ
    tools = [WebSearchTool(...), CodeInterpreterTool(...)]
    _NATIVE_TOOLS_CACHE[cache_key] = tools
    return tools
```

**期待効果**:
- Native Tools 再インスタンス化: 300ms → 5ms (94%削減)
- 2回目以降のリクエストで効果発揮

#### OpenAI Agents SDK 最適化知見

大規模調査で判明した追加最適化ポイント：

| 設定 | デフォルト | 推奨 | 効果 |
|------|-----------|------|------|
| `max_turns` | 10 | 3-5 | API呼び出し上限削減 |
| `parallel_tool_calls` | None | False (サブエージェント) | 順序実行で安定性向上 |
| `temperature` | 1.0 | 0.2-0.3 (サブエージェント) | 出力の一貫性向上 |
| `custom_output_extractor` | None | 実装推奨 | トークン30%削減 |

**参照**: `agents/run.py`, `agents/agent.py`, `agents/model_settings.py`

#### テストスクリプト

```bash
cd backend
uv run python scripts/test_response_time.py
```

**計測項目**:
- TTFT (Time to First Token)
- Total Response Time
- Sub-Agent呼び出し数・名前
- イベント数

### 22. マルチエージェント並列実行最適化 (2026-02-04)

**実装した最適化**:

1. **Orchestrator `parallel_tool_calls=True`** (`orchestrator.py`):
   - 複数サブエージェントを並列で呼び出し可能に
   - COMPLEXクエリで `call_analytics_agent` と `call_zoho_crm_agent` が同時実行

2. **SubAgent最適化** (`base.py`):
   - `reasoning_effort: "low"` (デフォルト`"medium"`から変更)
   - `reasoning.summary: "concise"` (デフォルト`"detailed"`から変更)
   - `verbosity: "low"` (デフォルト`"medium"`から変更)
   - `parallel_tool_calls: true` (サブエージェント内のツール並列実行)

**ベンチマーク結果比較**:

| シナリオ | 最適化前 | 最適化後 | 改善率 |
|---------|---------|---------|--------|
| SIMPLE | 4.06s | 4.32s | - |
| MEDIUM | 58.57s | **37.28s** | **36%** |
| COMPLEX | 125.67s | **72.80s** | **42%** |

**技術的知見**:
- `parallel_tool_calls=True`: OpenAI Agents SDKでサブエージェント（as_tool化）を並列実行
- サブエージェントの`reasoning_effort: "low"`: 速度優先、精度は十分維持
- `max_tool_calls`: Agent.__init__()には存在しない（無効パラメータ）
- 並列実行は`Runner.run_streamed()`内で自動的に処理される

**残存ボトルネック**:
- ZohoCRMAgent: 単純カウントクエリでも7回のサブエージェントイベント
- Zoho API: COQLでも複数ラウンドトリップが発生

**情報ソース**:
- SDK Source: `agents/model_settings.py` (ModelSettings)
- SDK Source: `agents/run.py` (Runner.run_streamed)
- 大規模並列調査結果 (10エージェント同時実行)

### 23. 大規模最適化実装 (2026-02-05)

**5並列エージェント調査**で以下の最適化パターンを発見・実装:

#### 実装済み最適化

| 最適化 | ファイル | 効果 |
|--------|---------|------|
| CompactMCPServer | `compact_mcp.py` (新規) | GA4 JSON→TSV圧縮 (76%トークン削減) |
| LazyMCPServer統合 | `lazy_mcp_server.py` | GA4にCompactMCPServer自動適用 |
| 無効ModelSettings削除 | `orchestrator.py`, `base.py` | `verbosity`, `response_include` は存在しないパラメータ |
| Simple Query Fast Path | `agent_service.py` | 挨拶はgpt-5-nano直接応答 |
| オーケストレーター指示強化 | `orchestrator.py` | データクエリは必ずサブエージェント使用を明示 |

#### 発見・修正したバグ

1. **Simple Query Pattern Bug**: `hi`パターンが`hitocareer`にマッチしていた
   - 修正: ワード境界 `(\s|$|!)` を追加

2. **無効なModelSettingsパラメータ**: `verbosity`, `response_include`
   - 原因: OpenAI Agents SDKに存在しないパラメータがサイレントに無視されていた
   - 影響: 「よくわかんないバックグラウンドみたいな」応答の一因

#### ベンチマーク結果比較

| シナリオ | 最適化前 | 最適化後 | 改善率 |
|---------|---------|---------|--------|
| SIMPLE | 4.06s | 4.17s | ~0% |
| MEDIUM | 58.57s | **43.83s** | **25%** |
| COMPLEX | 125.67s | **48.01s** | **62%** |

#### 参照プロジェクトからの知見

**ga4-oauth-aiagent:**
- CompactMCPServer: GA4 proto_to_dict JSON→TSV変換で76%圧縮
- MCP Session Caching: 接続再利用でリクエスト毎の接続オーバーヘッド削減
- Queue + Pump Task: SDKイベントとカスタムイベントのマルチプレクス

**marketing-automation:**
- `result.to_input_list()` でコンテキスト永続化
- `Reasoning(summary="detailed")` でストリーミング推論表示
- `ContextVar` でスレッドセーフなクレデンシャル伝搬

**wordpress-ability-plugin:**
- Static closures: メモリ効率向上
- Input schema constraints: 早期バリデーション
- Permission callback separation: キャッシング機会

#### 90%削減に向けた追加最適化候補

| 最適化 | 期待効果 | 実装難易度 |
|--------|---------|-----------|
| Semantic Caching (Redis) | 頻出クエリの即時応答 | 高 |
| Tool Output Caching | 同じツール結果の再利用 | 中 |
| Zoho COQL最適化 | 7回→1回のAPI呼び出し | 中 |
| Model Routing | 簡単クエリはgpt-5-nano | 低（実装済み） |
| Prompt Caching | 80%レイテンシ削減 | OpenAI自動 |

**技術的知見**:
- `verbosity` はOpenAI Agents SDK ModelSettingsに**存在しない**
- `response_include` も同様に存在しない
- これらのパラメータはサイレントに無視される（エラーにならない）
- Gemini via LiteLLMはツール呼び出しが不安定な場合がある
- オーケストレーターはOpenAI (gpt-5.1/5.2) 推奨

### 24. サブエージェント最適化: ツールAPIパラメータ修正 (2026-02-05)

**問題**: OpenAI Dashboardログで以下のエラーが大量発生
- SEO Agent: 38秒かかりAhrefs APIエラー多発
- Analytics Agent: 77秒かかり「実行してよろしいですか？」と許可を求める

**Ahrefs API カラム名修正** (`seo_agent.py`):
| 指示書の記載 | 実際のAPIカラム名 | 影響ツール |
|-------------|-----------------|-----------|
| `position` | `best_position` | organic-keywords, top-pages |
| `traffic` | `sum_traffic` | organic-keywords, top-pages, organic-competitors |
| `difficulty` | `keyword_difficulty` | organic-keywords, keywords-explorer |
| なし | `date` (必須) | すべてのsite-explorerツール |

**Analytics Agent指示修正** (`analytics_agent.py`):
- 「許可を求めるな」ルールを追加
- 即時実行パターン表を追加
- 典型的なリクエスト→ツールマッピングを明示

**全サブエージェントModelSettings修正**:
| ファイル | 修正内容 |
|---------|---------|
| `ad_platform_agent.py` | `verbosity="medium"` 削除、`parallel_tool_calls=True`追加 |
| `candidate_insight_agent.py` | `verbosity="medium"` 削除、`parallel_tool_calls=True`追加 |
| `zoho_crm_agent.py` | `verbosity="medium"` 削除、`parallel_tool_calls=True`追加 |
| `analytics_agent.py` | `verbosity="medium"` 削除、`summary="concise"`に変更 |

**期待効果**:
| 指標 | 最適化前 | 最適化後 |
|------|---------|---------|
| SEO Agent | 38秒 (リトライ多発) | ~10秒 (1-2回呼び出し) |
| Analytics Agent | 77秒 (許可確認) | ~15秒 (即時実行) |
| 無効パラメータ | 4ファイルに存在 | 0 |

**技術的知見**:
- Ahrefs API v3: `date`パラメータが多くのエンドポイントで**必須**
- Ahrefs API: カラム名は公式ドキュメントと実際のAPIで異なる場合がある
- エラーログから正確なカラム名を逆算可能
- サブエージェントの指示に「許可を求めない」を明示しないと、許可確認で時間を浪費

**修正ファイル一覧**:
- `backend/app/infrastructure/chatkit/agents/seo_agent.py` - Ahrefsカラム名修正
- `backend/app/infrastructure/chatkit/agents/analytics_agent.py` - 指示・ModelSettings修正
- `backend/app/infrastructure/chatkit/agents/ad_platform_agent.py` - ModelSettings修正
- `backend/app/infrastructure/chatkit/agents/candidate_insight_agent.py` - ModelSettings修正
- `backend/app/infrastructure/chatkit/agents/zoho_crm_agent.py` - ModelSettings修正

### 25. サブエージェント追加最適化: 許可確認バグ・Code Interpreter無効化 (2026-02-05)

**問題**: OpenAI Dashboardログで発見した深刻な問題
1. **SEO Agent**: 「許可を求めるな」ルールが欠落 → Ahrefsツールを1度も呼び出さず許可確認で終了
2. **Analytics Agent**: Code Interpreterで無意味な`pass`を4回実行、GA4パラメータエラー連発
3. **全体**: サブエージェントがMCPツールではなくCode Interpreterを誤用

**修正内容**:

1. **SEO Agent 指示追加** (`seo_agent.py`):
   - 「許可を求めるな」ルール追加
   - 典型的なリクエスト→ツールマッピング表追加

2. **Analytics Agent 指示強化** (`analytics_agent.py`):
   - GA4 `run_report` パラメータ仕様を詳細追加
   - `date_ranges` が必須であることを明記
   - `clicks`, `impressions` はGA4にない → GSCを使うよう明記
   - 「Code Interpreterは計算のみ」ルール追加

3. **サブエージェント Code Interpreter 無効化** (`settings.py`, `base.py`):
   - 新設定: `SUB_AGENT_ENABLE_CODE_INTERPRETER=false` (デフォルトOFF)
   - Code Interpreterがサブエージェントで無意味な`pass`を連発する問題を解決
   - Web Searchはデフォルトでオン維持

**新環境変数**:
```bash
# サブエージェントのCode Interpreter (デフォルト: 無効)
SUB_AGENT_ENABLE_CODE_INTERPRETER=false

# サブエージェントのWeb Search (デフォルト: 有効)
SUB_AGENT_ENABLE_WEB_SEARCH=true
```

**期待効果**:
| 問題 | 修正前 | 修正後 |
|------|--------|--------|
| SEO許可確認 | 28秒で許可確認のみ | 即座にAhrefs呼び出し |
| Analytics Code Interpreter | 4回の無駄な`pass`実行 | Code Interpreter無効化 |
| GA4パラメータエラー | date_ranges未指定エラー | パラメータ仕様を指示に明記 |
| GA4 clicks使用 | 無効メトリクスエラー | GSC使用を明記 |

**技術的知見**:
- サブエージェントは専門ツール（MCP）を持っているため、汎用のCode Interpreterは不要
- Code Interpreterはオーケストレーター側でのみ有効にすべき（最終集計・可視化用）
- GA4 Data API v1: `clicks`, `impressions` は存在しない（GSCのみ）
- 指示に「即時実行パターン」表を入れると、モデルが正しいツール選択をしやすい

### 24. 全サブエージェント最適化 & N+1修正 (2026-02-05)

**背景**: ユーザーから「100個以上あるすべてのツールをチェック・最適化し、90%以上の効率化を進めてほしい」との要求

**実施内容**:

#### 1. N+1問題修正 (`candidate_insight_tools.py`)

**問題**: `analyze_competitor_risk()`, `assess_candidate_urgency()` がループ内で個別にSupabaseクエリを実行
```python
# 修正前: N+1問題 (50件 → 50回クエリ)
for record in records:
    structured = _get_structured_data_by_zoho_record(record_id)  # 毎回クエリ
```

**修正**: バッチ取得ヘルパー追加
```python
# 修正後: 1回のIN句クエリで全件取得
def _get_all_structured_data_by_zoho_ids(zoho_record_ids: List[str]) -> Dict[str, Dict]:
    res = sb.table("structured_outputs").select(...).in_("zoho_record_id", zoho_record_ids[:100]).execute()
    return {row["zoho_record_id"]: row for row in res.data}

# 使用箇所
record_ids = [r.get("record_id") for r in records if r.get("record_id")]
structured_map = _get_all_structured_data_by_zoho_ids(record_ids)  # 1回のクエリ
```

**期待効果**:
| 操作 | 修正前 | 修正後 | 改善 |
|------|--------|--------|------|
| 50件の競合分析 | 50回クエリ (~25秒) | **1回クエリ (~0.5秒)** | **98%削減** |

#### 2. 全サブエージェント「許可を求めるな」ルール追加

**問題**: SEOエージェントが「実行してよろしいですか？」と確認を求め、28秒無駄にしていた

**修正対象ファイル**:
| ファイル | 追加内容 |
|---------|---------|
| `seo_agent.py` | 「許可を求めるな」ルール + Ahrefsパラメータ仕様 |
| `analytics_agent.py` | 「許可を求めるな」ルール + GA4/GSCパラメータ仕様 |
| `ad_platform_agent.py` | 「許可を求めるな」ルール + Meta Adsパラメータ仕様 (20ツール) |
| `wordpress_agent.py` | 「閲覧系は即実行」ルール + WordPressパラメータ仕様 |
| `candidate_insight_agent.py` | 「許可を求めるな」ルール + ツールパラメータ仕様 |
| `zoho_crm_agent.py` | 「許可を求めるな」ルール (既存) |

**共通追加ルール**:
```
## 重要ルール（絶対厳守）
1. **許可を求めるな**: 「実行してよろしいですか？」「確認させてください」は禁止。即座にツールを実行せよ
2. **推測するな**: データが必要なら必ずツールを呼び出す。自分でデータを作らない
3. **効率的に**: 1-2回のツール呼び出しで必要なデータを取得
```

#### 3. オーケストレーター選択マトリクス強化 (`orchestrator.py`)

**追加内容**: キーワード→サブエージェント自動選択マトリクス
```
| キーワード | 即座に呼び出すエージェント |
|-----------|---------------------------|
| セッション、PV、トラフィック、流入 | call_analytics_agent |
| DR、ドメインレーティング、被リンク | call_seo_agent |
| Meta広告、Facebook、CTR、CPA | call_ad_platform_agent |
| 記事、ブログ、WordPress | call_wordpress_agent |
| 求職者、チャネル別、成約率 | call_zoho_crm_agent |
| 高リスク、緊急度、面談準備 | call_candidate_insight_agent |
```

#### 4. 詳細パラメータ仕様追加

| エージェント | ツール数 | パラメータ仕様 |
|-------------|---------|---------------|
| SEO (Ahrefs) | 20 | 全ツールの必須/任意パラメータ、カラム名 |
| Analytics (GA4+GSC) | 16 | date_ranges必須、有効メトリクス一覧 |
| Ad Platform (Meta) | 20 | 全ツールのパラメータ、出力形式 |
| WordPress | 26×2 | 主要ツールのパラメータ仕様 |
| Candidate Insight | 4 | 全ツールのパラメータ、出力形式 |

**期待される全体効果**:
| 問題 | 修正前 | 修正後 |
|------|--------|--------|
| N+1クエリ | 25秒 | **0.5秒** (-98%) |
| 許可確認 | 28秒 | **0秒** (-100%) |
| パラメータエラー | リトライ多発 | **1-2回で成功** |
| ツール選択ミス | 頻発 | **自動選択マトリクスで回避** |

**技術的知見**:
- Supabase `.in_()` メソッドでIN句バッチ取得（最大100件）
- 「即時実行パターン」表をインストラクションに入れるとモデルが正しいツール選択をしやすい
- パラメータエラー（Ahrefs `where: ""`）は「省略」を明記しないと空文字列を渡してしまう
- 全エージェントに「許可を求めるな」ルールを入れることで、不要な確認ターンを排除

### 24. チャート出力機能実装 (2026-02-05)

**背景**: マーケティングAIでデータを可視化するためのインタラクティブチャート機能を追加

**実装内容**:

#### Backend: `render_chart` Function Tool

**新規ファイル**: `backend/app/infrastructure/marketing/chart_tools.py`
```python
@function_tool
async def render_chart(
    ctx: ToolContext[MarketingChatContext],
    chart_spec: str,  # JSON文字列
) -> str:
    """チャットUIにインタラクティブなチャートを描画する。"""
    spec = json.loads(chart_spec)
    await ctx.context.emit_event({"type": "chart", "spec": spec})
    return f"チャート「{spec.get('title', '')}」を描画しました。"

CHART_TOOLS = [render_chart]
```

**循環インポート回避**:
- `CHART_TOOLS`と`MarketingChatContext`を`chart_tools.py`に分離
- `agent_service.py`では遅延インポート (`from ... import OrchestratorAgentFactory`)

**オーケストレーターへの統合**:
- `orchestrator.py`: `tools=native_tools + sub_agent_tools + list(CHART_TOOLS)`
- チャート描画ルールをインストラクションに追加

#### Frontend: Recharts統合

**依存関係**: `recharts@3.7.0`

**新規ファイル群**: `frontend/src/components/marketing/charts/`
| ファイル | 説明 |
|---------|------|
| `ChartRenderer.tsx` | メインレンダラー（タイプ別ディスパッチ） |
| `LineChartView.tsx` | 時系列トレンド |
| `BarChartView.tsx` | カテゴリ比較 |
| `AreaChartView.tsx` | 累積/スタックエリア |
| `PieChartView.tsx` | 円グラフ/ドーナツ |
| `RadarChartView.tsx` | レーダーチャート |
| `FunnelChartView.tsx` | ファネル（横棒） |
| `TableChartView.tsx` | テーブル表示 |
| `chart-colors.ts` | カラーパレット、formatNumber |

**ChartSpec型** (`types.ts`):
```typescript
export interface ChartSpec {
  type: "line" | "bar" | "area" | "pie" | "donut" | "scatter" | "radar" | "funnel" | "table";
  title?: string;
  description?: string;
  data: Record<string, unknown>[];
  xKey?: string;
  yKeys?: ChartYKey[];
  nameKey?: string;
  valueKey?: string;
  columns?: ChartColumn[];
  nameField?: string;
  valueField?: string;
}
```

**hook更新** (`use-marketing-chat.ts`):
- `case "chart":` イベントハンドリング追加
- `ChartActivityItem`をアクティビティに追加

**ChatMessage更新**:
- `ActivityTimeline`に`case "chart":`追加
- `ChartRenderer`でレンダリング

**技術的知見**:
- Rechartsの`Tooltip`の`formatter`型: `value: number | undefined` なので型アノテーションを付けない
- `PieChart`の`label`の`percent`: `undefined`の可能性があるので`?? 0`でデフォルト値
- `ResponsiveContainer`でレスポンシブ対応（`ChartContainer`は不要）

### 25. サブエージェントUI改善 (2026-02-05)

**ユーザー要望**:
1. 実行中はデフォルトで展開（現在は閉じている）
2. 推論内容は省略せず全文表示（現在は`line-clamp-2`）
3. マークダウンレンダリング

**修正内容** (`ChatMessage.tsx`の`SubAgentBadge`):

```tsx
// Before
const [isExpanded, setIsExpanded] = useState(false);

// After - 実行中はデフォルト展開
const [isExpanded, setIsExpanded] = useState(item.isRunning);

// 新規: 詳細が到着したら自動展開
useEffect(() => {
  if (item.isRunning && hasDetails) {
    setIsExpanded(true);
  }
}, [item.isRunning, hasDetails]);
```

**推論表示の改善**:
```tsx
// Before
<p className="text-[10px] text-[#9ca3af] leading-relaxed line-clamp-2">
  {item.reasoningContent}
</p>

// After - line-clamp削除 + マークダウンレンダリング
<div className="text-[10px] text-[#9ca3af] leading-relaxed ...">
  <ReactMarkdown remarkPlugins={[remarkGfm]}>
    {item.reasoningContent}
  </ReactMarkdown>
</div>
```

**UI改善詳細**:
- ツール名の`max-w`を150px→200pxに拡大
- 推論アイコンを`Brain`に変更
- spacing調整 (`space-y-1` → `space-y-1.5`)

### 26. 中間報告機能（既存機能確認） (2026-02-05)

**確認結果**: オーケストレーターインストラクションに「中間報告ルール」が既に実装済み

```markdown
## 中間報告ルール（重要）
- ツール実行の前後に、**今何をしているか・次に何をするかを短いテキストで報告**せよ
- ユーザーはリアルタイムで行動を見ている。無言でツールを連続実行するな
- 例:
  - 「まずGA4からセッションデータを取得します。」→ call_analytics_agent
  - 「データが取れました。次にチャートで可視化します。」→ render_chart
- ただし中間報告は1〜2文の短文にせよ
```

**動作確認**: SSEストリーミングはinterleaved timeline方式で、テキストとツール呼び出しが到着順に表示される

### 27. 大規模調査: サブエージェント完了判定 & UX改善提案 (2026-02-05)

**調査方法**: 6並列エージェントによる大規模調査を実施
- Supabase会話履歴: 314会話, 6311メッセージ
- 参照プロジェクト: `/home/als0028/study/shintairiku/ga4-oauth-aiagent`
- Web検索: UXベストプラクティス

**発見された重大な問題**:

| カテゴリ | 健全性スコア | 状態 |
|---------|-------------|------|
| ツール完了判定 | 94% | ✅ Good |
| サブエージェント完了判定 | 0% | ❌ **CRITICAL** |
| Activity Items 永続化 | 7% | ❌ **CRITICAL** |
| エラーハンドリング | 94% | ✅ Good |

**修正内容**:

1. **`agent_service.py`** - サブエージェント `is_running` フィールド追加:
   ```python
   # 各イベントタイプで is_running を設定
   - started → is_running: True
   - tool_called → is_running: True
   - tool_output → is_running: True
   - reasoning → is_running: True
   - message_output → is_running: False  # 完了マーカー
   ```

2. **`marketing.py`** - DB保存時に `is_running` を含める

3. **`use-marketing-chat.ts`** - reasoningContent Markdown修正:
   ```typescript
   // Before: 空白区切り（Markdown破壊）
   reasoningContent: (subItem.reasoningContent || "") + " " + reasoningContent,
   // After: 改行区切り（Markdown保持）
   reasoningContent: (subItem.reasoningContent || "") + "\n\n" + reasoningContent,
   ```

4. **`ChatMessage.tsx`** - SubAgentBadge自動折りたたみ:
   ```typescript
   useEffect(() => {
     if (item.isRunning && hasDetails) {
       setIsExpanded(true);
     } else if (!item.isRunning) {
       // 完了時に1秒後自動折りたたみ
       const timer = setTimeout(() => setIsExpanded(false), 1000);
       return () => clearTimeout(timer);
     }
   }, [item.isRunning, hasDetails]);
   ```

**新規ドキュメント**: `docs/marketing-ai-ux-improvement-proposal.md`
- 調査結果の完全版
- 推奨アクションと実装タイムライン
- UXベストプラクティス

**残課題**:
- Activity Items永続化バグ（93.5%空）の調査 - 原因特定が必要
- HostedMCPTool互換性問題 - LiteLLM/Geminiでは使用不可

### 28. ChatGPT/Claude風サイドバー & 履歴パネル実装 (2026-02-05)

**背景**: ユーザーから「履歴一覧を開くUIがない」との指摘。参照プロジェクト (ga4-oauth-aiagent) のChatGPT/Claude風UIをポーティング。

**新規コンポーネント**:

| ファイル | 説明 |
|---------|------|
| `frontend/src/components/marketing/AppSidebar.tsx` | 左サイドバー (220px ↔ 60px 折りたたみ) |
| `frontend/src/components/marketing/HistoryPanel.tsx` | 右履歴パネル (Sheet形式) |

**AppSidebar機能**:
- 新しいチャットボタン (アクセント色 #e94560)
- ナビゲーション: チャット、ダッシュボード、設定
- 折りたたみ時はTooltip表示
- Clerk UserButton統合
- モバイル対応 (Sheet)

**HistoryPanel機能**:
- 日付グループ化: 今日、昨日、過去7日間、それ以前
- 相対日時: 「今」「X分前」「X時間前」「X日前」「12月15」
- 削除ボタン (ホバーで表示)
- Empty state

**バックエンドAPI追加** (`marketing.py`):
```python
@router.get("/threads")      # 会話一覧
@router.delete("/threads/{thread_id}")  # 会話削除
```

**フロントエンドAPI Route追加**:
- `frontend/src/app/api/marketing/threads/route.ts`
- `frontend/src/app/api/marketing/threads/[id]/route.ts` (DELETE追加)

**MarketingChat変更**:
- `forwardRef` + `useImperativeHandle` で `clearMessages` を公開
- 親コンポーネントから新規チャット開始可能に

**レイアウト構造**:
```
┌─────────────┬────────────────────────────────┐
│ AppSidebar  │ Header (履歴ボタン)            │
│ (220/60px)  ├────────────────────────────────┤
│             │ MarketingChat                  │
│ - 新規      │                                │
│ - チャット  │                                │
│ - ダッシュ  │                                │
│ - 設定      │                                │
│             │                                │
│ [User]      │                                │
└─────────────┴────────────────────────────────┘
                              [HistoryPanel →]
```

**UIデザイン**:
- プライマリ: Navy #1a1a2e
- グレー: #6b7280, #9ca3af, #c4c7cc, #f0f1f5
- アクセント: ピンク赤 #e94560
- アクティブ: 背景色 + ring-1

### 29. Google ADK 完全移行実装 (2026-02-05)

**背景**: OpenAI Agents SDK からGoogle Agent Development Kit (ADK) への完全移行

**有効化方法**:
```bash
# .env に追加
USE_ADK=true
ADK_ORCHESTRATOR_MODEL=gemini-3-flash-preview
ADK_SUB_AGENT_MODEL=gemini-3-flash-preview
GEMINI_API_KEY=your-gemini-api-key
```

**アーキテクチャ**:
```
                  ┌─────────────────────────────────────┐
                  │        get_marketing_agent_service() │
                  │                                      │
                  │  USE_ADK=true   │   USE_ADK=false   │
                  │  → ADKAgentService │ → MarketingAgentService │
                  └─────────────────────────────────────┘
                              │
        ┌───────────────────────────────────────┐
        ▼                                       ▼
┌───────────────────┐               ┌───────────────────┐
│  ADKAgentService  │               │ MarketingAgentService │
│  (Gemini 3 Flash) │               │ (GPT-5.2 + GPT-5-mini) │
├───────────────────┤               ├───────────────────┤
│ Google ADK Runner │               │ OpenAI Agents SDK │
│   ├─ Analytics    │               │   ├─ Analytics    │
│   ├─ SEO          │               │   ├─ SEO          │
│   ├─ AdPlatform   │               │   ├─ AdPlatform   │
│   ├─ ZohoCRM      │               │   ├─ ZohoCRM      │
│   ├─ Candidate    │               │   ├─ Candidate    │
│   └─ WordPress    │               │   └─ WordPress    │
│   + render_chart  │               │   + render_chart  │
└───────────────────┘               └───────────────────┘
```

**実装済み機能**:
| 機能 | OpenAI SDK版 | ADK版 |
|------|-------------|-------|
| Queue + pump task | ✅ | ✅ |
| Simple query fast path | ✅ | ✅ |
| Sub-agent events | ✅ | ✅ |
| Chart rendering | ✅ | ✅ |
| Keepalive (20s) | ✅ | ✅ |
| Reasoning events | ✅ | ✅ |
| Translation | ✅ (GPT-5-nano) | ✅ (パススルー) |

**新規/変更ファイル (ADK)**:
| ファイル | 説明 |
|---------|------|
| `backend/app/infrastructure/adk/agent_service.py` | ADKストリーミングサービス（完全書き直し） |
| `backend/app/infrastructure/adk/agents/orchestrator.py` | ADKオーケストレーター + チャートツール |
| `backend/app/infrastructure/adk/tools/chart_tools.py` | ADK用チャートツール（新規） |
| `backend/app/infrastructure/adk/mcp_manager.py` | ADK MCP管理 |
| `backend/app/infrastructure/marketing/agent_service.py` | `USE_ADK`切り替えロジック追加 |

**ADKイベント構造**:
```python
# ADKのイベントは content.parts[] に複数要素を含む
event.content.parts[i].text          # テキスト
event.content.parts[i].function_call # ツール呼び出し
event.content.parts[i].function_response # ツール結果
```

**サブエージェント名変換**:
```
ZohoCRMAgent → zoho_crm
AnalyticsAgent → analytics
SEOAgent → seo
AdPlatformAgent → ad_platform
WordPressAgent → wordpress
CandidateInsightAgent → candidate_insight
```

**技術的知見**:
- ADK `Runner.run_async()` は async generator を返す（awaitableではない）
- ADK `InMemorySessionService.create_session()` は async メソッド
- ADK メッセージは `types.Content(role="user", parts=[types.Part(text=...)])` 形式
- ADKツールは plain Python function を自動ラップ（`@function_tool`不要）
- `AgentTool(agent=sub_agent)` でサブエージェントをツール化
- モデルID: `gemini-3-flash-preview` (Gemini 3 Flash)
- **ストリーミング**: デフォルトは `StreamingMode.NONE` (stream: False) → 明示的に `RunConfig(streaming_mode=StreamingMode.SSE)` を渡す必要あり
  ```python
  from google.adk.agents.run_config import StreamingMode
  from google.adk.runners import RunConfig

  run_config = RunConfig(streaming_mode=StreamingMode.SSE)
  async for event in runner.run_async(..., run_config=run_config):
      ...
  ```

**コスト比較**:
| モデル | 入力 | 出力 | 削減率 |
|--------|------|------|--------|
| GPT-5.2 + GPT-5-mini | $3-5/クエリ | - | - |
| Gemini 3 Flash | ~$0.50-1/クエリ | - | **~80%** |

**情報ソース**:
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [google/adk-python GitHub](https://github.com/google/adk-python)
- ADK Source: `google/adk/agents/`, `google/adk/runners/`

### 30. ADK テキスト重複バグ修正 (2026-02-05)

**問題**: フロントエンドで同じメッセージが2回表示される

**根本原因**: ADK SSEストリーミングのイベント構造
```
Event 1: partial=True, text="こんにちは..." (ストリーミングチャンク)
Event 2: partial=True, no text
Event 3: partial=False, text="こんにちは..." (完了イベント、同じテキスト)
```

`_process_adk_event()` で `partial` フラグをチェックせずに全イベントのテキストを送信していたため、同じテキストが2回（partial=TrueとFalse）送信されていた。

**修正内容** (`agent_service.py`):

1. `event.partial` フラグを確認して重複防止:
   ```python
   is_partial = getattr(event, "partial", None)

   # テキスト処理
   if is_partial is True:
       # ストリーミングチャンク → 送信
       results.append({"type": "text_delta", "content": part.text})
   elif is_partial is False:
       # 完了イベント → スキップ（既にpartial=Trueで送信済み）
       logger.debug("Skipping final text...")
   elif is_partial is None:
       # 非ストリーミング（サブエージェント等）→ 送信
       results.append({"type": "text_delta", "content": part.text})
   ```

2. 条件を `if` → `elif` に変更（排他的条件化）:
   - 同じ `part` から複数のSSEイベントが生成されない
   - 優先順位: function_response > function_call > text

**ADK SSEイベントフロー**:
| partial値 | 意味 | アクション |
|-----------|------|-----------|
| `True` | ストリーミングチャンク | **送信** |
| `False` | 完了イベント（全テキスト含む）| **スキップ** |
| `None` | 非ストリーミング | **送信** |

**技術的知見**:
- ADK の `StreamingMode.SSE` では、`partial=True` でチャンクが到着し、`partial=False` で完全なテキストが到着
- サブエージェント（`stream: False`）では `partial=None`
- `Event.partial` は `Optional[bool]` 型

### 31. ADK MCPツールセット配布アーキテクチャ修正 (2026-02-05)

**問題**: サブエージェントへのMCPツール配布が正しく動作しない（Analytics, SEO, AdPlatform, WordPressが0ツール）

**根本原因**:
1. `McpToolset`クラスには`name`属性が存在しない
2. 各サブエージェントファクトリが `getattr(server, "name", "")` でフィルタリングしようとしていた
3. 結果: `name`が空文字列となりフィルタに一致せず、ツールが0になる

**修正内容**:

1. **`orchestrator.py`** - MCPツールセットのドメイン別配布:
   ```python
   def build_agent(self, ..., mcp_toolsets: ADKMCPToolsets | None = None):
       mcp_mapping = {
           "analytics": [],      # GA4 + GSC
           "ad_platform": [],    # Meta Ads
           "seo": [],            # Ahrefs
           "wordpress": [],      # WordPress x2
       }
       if mcp_toolsets:
           if mcp_toolsets.ga4:
               mcp_mapping["analytics"].append(mcp_toolsets.ga4)
           if mcp_toolsets.gsc:
               mcp_mapping["analytics"].append(mcp_toolsets.gsc)
           # ... etc

       for name, factory in self._sub_factories.items():
           domain_mcp = mcp_mapping.get(name, [])
           sub_agent = factory.build_agent(mcp_servers=domain_mcp, asset=asset)
   ```

2. **サブエージェントファクトリの簡素化**:
   ```python
   # Before (バグ)
   for server in mcp_servers:
       if getattr(server, "name", "") in ("ga4", "gsc"):
           tools.append(server)

   # After (修正)
   if mcp_servers:
       return list(mcp_servers)  # オーケストレーターが事前フィルタ済み
   ```

3. **`agent_service.py`** - `ADKMCPToolsets`オブジェクトを直接渡す:
   ```python
   mcp_toolsets = await self._mcp_manager.create_toolsets()
   orchestrator = self._orchestrator_factory.build_agent(mcp_toolsets=mcp_toolsets)
   ```

**修正後のサブエージェントツール数**:
| エージェント | ツール数 | ソース |
|-------------|---------|--------|
| AnalyticsAgent | 2 | GA4 + GSC MCPToolset |
| AdPlatformAgent | 1 | Meta Ads MCPToolset |
| SEOAgent | 0 | Ahrefs MCPToolset未設定 |
| WordPressAgent | 0 | WordPress MCPToolset未設定 |
| ZohoCRMAgent | 10 | Function tools |
| CandidateInsightAgent | 4 | Function tools |

**技術的知見**:
- `McpToolset`には`name`属性がない - フィルタリングは呼び出し元で行う
- ADKの`McpToolset`はSTDIO/SSE接続パラメータのみを保持
- ドメイン別のツール配布はオーケストレーターファクトリで集中管理

### 32. ADK会話履歴・セッション管理実装 & 二重化修正 (2026-02-05)

**背景**: 大規模調査（6並列エージェント）の結果、ADK実装は会話履歴永続化が~40%しか完了していないことが判明

**調査結果 - 主要な問題点**:
1. `_context_items`イベントが空の`[]`を返していた（コンテキスト継続不可）
2. チャートイベントが`activity_items`に蓄積されていなかった（UI復元不可）
3. `InMemorySessionService`のみ使用（セッション間永続化なし）

**修正内容**:

1. **`adk/agent_service.py`** - Context Items構築:
   ```python
   # After streaming completes, build context_items from session history
   updated_session = await self._session_service.get_session(
       app_name="marketing_ai",
       user_id="default",
       session_id=session_id,
   )
   if updated_session and hasattr(updated_session, "events"):
       for event in updated_session.events:
           # Convert ADK events to serializable context items
           if hasattr(event, "content") and event.content:
               role = getattr(event.content, "role", "assistant")
               parts_data = []
               for part in event.content.parts:
                   if hasattr(part, "text") and part.text:
                       parts_data.append({"text": part.text})
                   elif hasattr(part, "function_call") and part.function_call:
                       parts_data.append({"function_call": {...}})
                   elif hasattr(part, "function_response") and part.function_response:
                       parts_data.append({"function_response": {...}})
               if parts_data:
                   context_items.append({"role": role, "parts": parts_data})

   yield {"type": "_context_items", "items": context_items}
   ```

2. **`marketing.py`** - チャートイベント蓄積:
   ```python
   elif event_type == "chart":
       activity_items.append({
           "kind": "chart",
           "sequence": seq,
           "id": str(uuid.uuid4()),
           "spec": event.get("spec"),
       })
       seq += 1
   ```

**ADK Session構造**:
| 属性 | 型 | 用途 |
|------|-----|------|
| `id` | `str` | セッションID |
| `events` | `list[Event]` | 会話イベント履歴 |
| `state` | `dict[str, Any]` | カスタム状態 |
| `last_update_time` | `float` | 最終更新時刻 |

**ADK Event.content構造**:
| 属性 | 型 | 内容 |
|------|-----|------|
| `role` | `Optional[str]` | "user" / "model" |
| `parts` | `list[Part]` | コンテンツパーツ |

**ADK Part構造**:
| 属性 | 型 | 内容 |
|------|-----|------|
| `text` | `Optional[str]` | テキストコンテンツ |
| `function_call` | `Optional[FunctionCall]` | ツール呼び出し |
| `function_response` | `Optional[FunctionResponse]` | ツール結果 |
| `thought` | `Optional[bool]` | 思考過程フラグ |

**データフロー（修正後）**:
```
1. ストリーミング中
   ADK events → _process_adk_event() → SSE events → Frontend

2. ストリーミング完了後
   Session.events → context_items構築 → _context_items event → DB保存 & Frontend

3. 次のターン
   marketing_conversations.metadata.context_items → stream_chat(context_items=...) → ADK Session
```

**永続化パターン（OpenAI SDK互換）**:
| 項目 | 保存先 | 目的 |
|------|--------|------|
| context_items | `marketing_conversations.metadata` | 次ターンコンテキスト継続 |
| activity_items | `marketing_messages.content` | UI復元用 |
| full_text | `marketing_messages.plain_text` | 検索用 |

**期待効果**:
- マルチターン会話でコンテキストが継続される
- ページリロード後もチャートが復元される
- 会話ダッシュボードに正しく表示される

**技術的知見**:
- ADK `InMemorySessionService`はプロセス内メモリのみ（再起動で消失）
- `DatabaseSessionService`は将来の永続化オプション
- `session.events`はストリーミング完了後にアクセス可能
- `Event.content.role`は"user"または"model"（OpenAI SDKの"assistant"と異なる）

### 32-2. ADKマルチターンでのテキスト二重化修正 (2026-02-05)

**問題**: 中間報告テキストが二重に表示される
```
GSCのデータが取得できました。続いて、...
GSCのデータが取得できました。続いて、...  ← 重複！
```

**根本原因**:
ADKのマルチターン実行では各ターンで:
1. `partial=True` でテキストをストリーミング
2. `partial=False` でそのターンの完全なテキストを送信

旧ロジックでは`partial=False`のテキストを`sent_text_tracker`と比較して重複排除していたが、各ターンの`partial=False`テキストには前のターンのテキストが含まれないため、不一致と判断され再送信されていた。

**修正** (`adk/agent_service.py`):
```python
# Before: 複雑な重複排除ロジック
if is_partial is False and sent_text_tracker is not None:
    # ... 28行の重複排除コード
    # 問題: マルチターンで不一致と判断され再送信

# After: シンプルにスキップ
if is_partial is False:
    for part in event.content.parts:
        if hasattr(part, "text") and part.text:
            # Skip - already sent via partial=True streaming
            logger.debug(f"[ADK] Skipping final text (partial=False): {len(part.text)} chars")
            continue
        # Process non-text parts only
        part_result = self._process_non_text_part(part, sub_agent_states)
```

**ADK partial イベントフロー（修正後）**:
| イベント | partial | アクション |
|---------|---------|-----------|
| ストリーミングチャンク | `True` | **送信** |
| ターン完了テキスト | `False` | **スキップ** (既に送信済み) |
| サブエージェント出力 | `None` | **送信** |

### 32-3. Activity Items 順序保持修正 (2026-02-05)

**問題**: テキスト→ツール→テキストの順序がDB保存・UI復元で崩れる

**根本原因** (`marketing.py`):
`tool_call`, `chart`, `sub_agent_event` の後に `current_text_id` がリセットされていなかったため、ツール呼び出し後のテキストが前のテキストブロックに追記されていた。

**修正** (`marketing.py`):
```python
elif event_type == "tool_call":
    current_text_id = None  # ← 追加: 新しいテキストブロックを開始
    activity_items.append({...})

elif event_type == "chart":
    current_text_id = None  # ← 追加
    activity_items.append({...})

elif event_type == "sub_agent_event":
    current_text_id = None  # ← 追加
    activity_items.append({...})
```

**修正** (`use-marketing-chat.ts`):
```typescript
// Restore activity items with new IDs, sorted by sequence
const activityItems = (msg.activity_items || [])
  .map((item, idx) => ({ ...item, sequence: item.sequence ?? idx }))
  .sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0));  // ← 追加
```

**正しいActivity Items順序**:
```
[
  {kind: "text", sequence: 0, content: "SEOを確認します。"},
  {kind: "sub_agent", sequence: 1, agent: "analytics"},
  {kind: "text", sequence: 2, content: "GSCデータが取得できました。"},
  {kind: "sub_agent", sequence: 3, agent: "seo"},
  {kind: "chart", sequence: 4, spec: {...}},
  {kind: "text", sequence: 5, content: "分析結果をまとめます。"}
]
```

---

> ## **【最重要・再掲】記憶の更新は絶対に忘れるな**
> **このファイルの冒頭にも書いたが、改めて念押しする。**
> 作業が完了したら、コミットする前に、必ずこのファイルに変更内容を記録せよ。
> 新しいファイルを作成した、既存ファイルを変更した、設計を変更した、バグを見つけた、知見を得た — すべて記録対象。
> **「後で更新しよう」は禁止。今すぐ更新せよ。**
