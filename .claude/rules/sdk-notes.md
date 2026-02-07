# SDK バージョン & 技術的知見

## ChatKit Python SDK v1.6.0
- **ソース**: `backend/.venv/lib/python3.12/site-packages/chatkit/`
- **SSEキープアライブ**: なし — SDK側にはキープアライブ機能が存在しない。カスタム `keepalive.py` が必要
- **ProgressUpdateEvent**: 型は `chatkit/types.py` に定義済み。複数回安全に送信可能
- **推論表示**: `chatkit/agents.py` の `stream_agent_response()` が `response.reasoning_summary_text.delta/done` を自動処理
- **キャンセル対応**: v1.6.0 で `handle_stream_cancelled()` が改善

## ChatKit Frontend SDK v1.5.0 / React v1.4.3
- **ソース**: `frontend/node_modules/@openai/chatkit/`, `@openai/chatkit-react/`
- **SSEキープアライブ**: なし — フロントエンド側にもタイムアウト対策は存在しない

## OpenAI Agents SDK v0.7.0
- **ソース**: `backend/.venv/lib/python3.12/site-packages/agents/`
- `nest_handoff_history` デフォルトが `True`→`False` に変更 (v0.7.0)
- GPT-5.1/5.2 のデフォルト reasoning effort が `'none'` に変更

## OpenAI Responses API (SSE)
- **キープアライブ**: なし — OpenAI APIもSSEキープアライブを送信しない
- **Background mode** (`"background": true`): 長時間推論タスクの公式ワークアラウンド
- **情報ソース**:
  - https://platform.openai.com/docs/api-reference/responses-streaming
  - https://platform.openai.com/docs/guides/streaming-responses
  - https://openai.github.io/openai-agents-python/streaming/

## Google ADK (Agent Development Kit)
- **ソース**: `backend/.venv/lib/python3.12/site-packages/google/adk/`
- **公式ドキュメント**: https://google.github.io/adk-docs/
- **GitHub**: https://github.com/google/adk-python

### ADK 制限設定

| 制限タイプ | パラメータ | デフォルト | 無制限設定 | 設定場所 |
|-----------|-----------|-----------|-----------|---------|
| LLM呼び出し回数 | `max_llm_calls` | 500 | `≤0` | `RunConfig` |
| ループ反復 | `max_iterations` | None(無制限) | None | `LoopAgent`のみ |
| 出力トークン | `max_output_tokens` | モデル依存 | - | `GenerateContentConfig` |
| ツール呼び出し | **存在しない** | - | - | - |
| ターン数 | **存在しない** | - | - | - |

### ADK RunConfig 設定
```python
from google.adk.runners import RunConfig
from google.adk.agents.run_config import StreamingMode

run_config = RunConfig(
    streaming_mode=StreamingMode.SSE,  # SSEストリーミング有効
    max_llm_calls=0,  # 0 or 負数 = 無制限
)
```

### ADK GenerateContentConfig 設定
```python
from google.genai import types

agent = Agent(
    ...,
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=65536,  # Gemini 3 Flash最大
        temperature=1.0,
        top_p=0.95,
    ),
)
```

### ADK Plugin システム
サブエージェント内部のイベント（ツール呼び出し、推論、エラー）をキャプチャするための強力な仕組み。

**利用可能なコールバック** (`BasePlugin`):
| コールバック | タイミング | 用途 |
|-------------|----------|------|
| `before_tool_callback` | ツール呼び出し前 | サブエージェント内のツール開始を検知 |
| `after_tool_callback` | ツール呼び出し後 | サブエージェント内のツール完了を検知 |
| `after_model_callback` | LLMレスポンス後 | 推論/思考をキャプチャ |
| `on_tool_error_callback` | ツールエラー時 | エラーハンドリング |
| `before_agent_callback` | エージェント開始前 | エージェント切り替え追跡 |
| `after_agent_callback` | エージェント完了後 | エージェント切り替え追跡 |

**重要**: `AgentTool`はデフォルトで`include_plugins=True`なので、親のPluginがサブエージェントに継承される。

```python
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner

class SubAgentStreamingPlugin(BasePlugin):
    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        # サブエージェント内のツール呼び出しをキャプチャ
        pass

runner = Runner(
    agent=orchestrator,
    plugins=[SubAgentStreamingPlugin(emit_callback=queue.put)],
)
```

**実装**: `backend/app/infrastructure/adk/plugins/sub_agent_streaming_plugin.py`

### ADK Context Caching (@experimental, v1.22.1)
Gemini Explicit Cacheを活用し、毎LLMコールの入力トークンコストを**90%削減**。

**フロー**: `App.context_cache_config` → `Runner` → `InvocationContext` → `ContextCacheRequestProcessor` → `GeminiContextCacheManager`

**キャッシュライフサイクル**:
1. 初回: フィンガープリント生成（SHA256 of system_instruction + tools + contents）
2. 2回目: フィンガープリント一致 + トークン > min_tokens → CachedContent作成
3. 3回目+: キャッシュ再利用（system_instruction/tools/cached_contentsをリクエストから除去）

```python
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps.app import App

app = App(
    name="marketing_ai",
    root_agent=orchestrator,
    plugins=[...],
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,     # キャッシュ作成の最小トークン数
        ttl_seconds=1800,    # 30分有効
        cache_intervals=10,  # 10回の呼び出しで再作成
    ),
)
runner = Runner(app=app, session_service=..., memory_service=...)
```

**重要な注意点**:
- `App`オブジェクト必須（`Runner(agent=..., app_name=...)`では使えない）
- `App`使用時、pluginsは`App`に設定する（`Runner`ではなく）
- `static_instruction`はADK v1.22.1には存在しない
- ADKソース: `.venv/.../google/adk/models/gemini_context_cache_manager.py`

## Gemini 3 Flash (gemini-3-flash-preview)
- **モデルID**: `gemini-3-flash-preview`
- **最大入力トークン**: 1,048,576 (1M)
- **最大出力トークン**: 65,536 (64k)
- **デフォルト出力トークン**: 未明記（実測では~3-4kで自己終了する報告あり）
- **thinking_level**: `minimal`, `low`, `medium`, `high`（デフォルト: `high`）
- **価格**: $0.50/1M入力、$3/1M出力
- **知識カットオフ**: 2025年1月

### 既知の問題
- **出力トークンの早期終了**: `max_output_tokens=60000`設定でも~3000トークンで自己終了する報告あり
- `finishReason: STOP`で終了（`MAX_TOKENS`ではない）
- 参照: https://discuss.ai.google.dev/t/gemini-3-output-limited-to-4k-tokens-instead-of-65k/114011

### 情報ソース
- https://ai.google.dev/gemini-api/docs/gemini-3
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash
- https://openrouter.ai/google/gemini-3-flash-preview
