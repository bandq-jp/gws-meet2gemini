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
- **Chat**: @openai/chatkit 1.5.0, @openai/chatkit-react 1.4.3
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

### 12. Google ADK移行可能性調査 (2026-02-05)

**背景**: マーケティングAIチャットのOpenAI Agents SDKをGoogle ADK (Agent Development Kit)に移行できるか調査

**調査結果**: **移行は技術的に可能だが、現時点では非推奨**

**Google ADK概要** (v1.23.0, 2026-01-22リリース):
- **公式**: [google.github.io/adk-docs](https://google.github.io/adk-docs/)
- **GitHub**: [google/adk-python](https://github.com/google/adk-python)
- **PyPI**: [google-adk](https://pypi.org/project/google-adk/)
- Gemini最適化だが、LiteLLM経由でOpenAI/Claude等もサポート

**機能比較**:

| 機能 | OpenAI Agents SDK | Google ADK | 互換性 |
|------|-------------------|------------|--------|
| Agent定義 | `Agent(name, model, tools)` | `LlmAgent(name, model, tools)` | ✅ 類似 |
| カスタムツール | `@function_tool` | `FunctionTool` | ✅ 類似 |
| MCP STDIO | `MCPServerStdio` | `MCPToolset + StdioConnectionParams` | ✅ 対応 |
| MCP HTTP | `HostedMCPTool` | `MCPToolset + StreamableHTTPConnectionParams` | ✅ 対応 |
| ストリーミング | `Runner.run_streamed()` | `runner.run_live()` | ✅ 対応 |
| セッション管理 | ChatKit Store | `SessionService` | ⚠️ 要実装 |
| 会話UI | ChatKit React | AG-UI + CopilotKit | ❌ 大幅変更 |
| Reasoning | ネイティブ | `BuiltInPlanner` (Geminiのみ) | ⚠️ GPT非対応 |

**移行しない理由**:

1. **ChatKitの代替構築コストが大きい**
   - ADKには`adk web`開発UIはあるがプロダクション非対応
   - [AG-UIプロトコル](https://github.com/ag-ui-protocol/ag-ui) + CopilotKitが推奨だがChatKit程成熟していない
   - フロントエンド全面書き換え（推定3-4週間）

2. **GPT-5.x継続ならメリット薄い**
   - ADKはGemini最適化
   - LiteLLM経由GPTは構造化出力・Reasoning表示で問題報告あり ([Issue #217](https://github.com/google/adk-python/issues/217), [Issue #2982](https://github.com/google/adk-python/issues/2982))

3. **現在の実装が安定稼働中**
   - SSEキープアライブ実装済み
   - MCP統合（ローカル/リモート）完備
   - ChatKitネイティブReasoning表示対応

**移行工数見積り**:
- バックエンド: 2-3週間 (Agent書き換え、MCP移行、セッション実装)
- フロントエンド: 3-4週間 (ChatKit削除、AG-UI導入、UI再実装)
- **合計: 5-7週間**

**将来的な移行検討条件**:
1. Gemini 3.0等でGPT-5.xを大幅に上回る性能が出た場合
2. AG-UI/CopilotKitがChatKit並みに成熟した場合
3. OpenAI Agents SDKのサポート終了が発表された場合

**ADK MCP統合例** (参考):
```python
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='analytics-mcp',
            env={"GOOGLE_APPLICATION_CREDENTIALS": sa_path}
        )
    ),
    tool_filter=['get_ga4_report', 'list_properties']  # ツールフィルタ
)
```

**結論**: **現状維持 (OpenAI Agents SDK + ChatKit) を推奨**

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

---

> ## **【最重要・再掲】記憶の更新は絶対に忘れるな**
> **このファイルの冒頭にも書いたが、改めて念押しする。**
> 作業が完了したら、コミットする前に、必ずこのファイルに変更内容を記録せよ。
> 新しいファイルを作成した、既存ファイルを変更した、設計を変更した、バグを見つけた、知見を得た — すべて記録対象。
> **「後で更新しよう」は禁止。今すぐ更新せよ。**
