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
