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
- **MCP Servers**: GA4, GSC, Ahrefs, Meta Ads, WordPress (オプション)

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
| `backend/app/infrastructure/chatkit/tool_events.py` | ToolUsageTracker: ツール実行のUI表示+DB保存 |
| `backend/app/infrastructure/chatkit/keepalive.py` | SSEキープアライブ (20秒間隔でProgressUpdateEvent) |
| `backend/app/infrastructure/chatkit/supabase_store.py` | ChatKit用Supabaseストア |
| `backend/app/infrastructure/chatkit/model_assets.py` | モデルプリセット管理 |
| `backend/app/infrastructure/chatkit/context.py` | リクエストコンテキスト |
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
