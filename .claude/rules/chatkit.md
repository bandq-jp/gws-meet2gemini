# ChatKit & マーケティングAI 詳細設計

## アーキテクチャ
```
Frontend (ChatKit React) → Next.js API Route (SSE proxy) → FastAPI → ChatKitServer → Agents SDK → OpenAI API
```

## 主要ファイル
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

## SSEキープアライブ機構 (keepalive.py)
- **目的**: 長時間推論 (reasoning_effort: high/xhigh) 中のSSEタイムアウト防止
- **仕組み**: pump task + asyncio.Queue + wait_for(timeout=20s) パターン
- **イベント**: タイムアウト時に `ProgressUpdateEvent(text="考え中...")` を送信
- **適用箇所**: `marketing_server.py` の `respond()` メソッドでメイン・フォールバック両ストリームに適用

## ChatKit ネイティブ推論表示
- ChatKit agents.py L622-743 で `response.reasoning_summary_text.delta/done` を自動処理
- `WorkflowItem(type="reasoning")` + `ThoughtTask` でUI表示
- `seo_agent_factory.py` で `Reasoning(effort=..., summary="detailed")` を設定

## ToolUsageTracker の非同期DB書き込み
- `_fire_and_forget()` でDB保存を非ブロッキング化
- `_save_tool_call_as_context()`, `_save_tool_output_as_context()` が対象
- `close()` で未完了タスクを10秒タイムアウトで待機
