# feat/new-meta-agent ブランチ変更一覧

> ベースブランチ: `main`
> コミット数: 4
> 変更規模: +1,737行 / -89行（24ファイル）

---

## コミット一覧

| # | コミットハッシュ | タイトル | 変更ファイル数 | 行数 |
|---|----------------|---------|-------------|------|
| 1 | `f4b6048` | feat(meta-ads): implement extensive improvements for Meta Ads analysis | 7 | +724/-52 |
| 2 | `8d1381e` | feat(ad-images): implement persistent ad image storage and frontend display enhancements | 4 | +112/-20 |
| 3 | `dcad5dd` | feat(ask-user-clarification): implement interactive user choice UI for ambiguous queries | 10 | +540/-6 |
| 4 | `fa1a17e` | feat(user-personalization): implement user context and Slack integration for personalized responses | 10 | +379/-21 |

---

## 1. Meta Ads (AdPlatformAgent) 大規模改善

**コミット**: `f4b6048`
**目的**: Meta広告分析の精度・深さ・トークン効率を大幅向上。プロの運用知識をエージェントに注入。

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/infrastructure/adk/agents/ad_platform_agent.py` | 指示文全面書き換え（50行→200+行） |
| `backend/app/infrastructure/adk/agents/orchestrator.py` | AdPlatformAgent説明・キーワードマトリクス更新 |
| `backend/app/infrastructure/adk/mcp_manager.py` | META_ADS_TOOL_FILTER追加 |
| `backend/app/infrastructure/adk/plugins/mcp_response_optimizer.py` | Meta Ads対応（圧縮説明+レスポンス圧縮） |
| `backend/pyproject.toml` | Pillow依存追加 |
| `backend/uv.lock` | ロックファイル更新 |

### 変更詳細

#### MCPツールフィルタ追加（`mcp_manager.py`）
- `META_ADS_TOOL_FILTER` 定義（20 read-onlyツールのみ許可）
- write系ツール（`create_campaign`, `update_*`, `upload_*`, `create_budget_schedule`, `get_login_link`）を除外
- `create_meta_ads_toolset()` に `tool_filter=META_ADS_TOOL_FILTER` 適用

#### AdPlatformAgent指示文全面書き換え（`ad_platform_agent.py`）
- 旧: 50行（存在しないツール名を参照、基本KPIのみ）
- 新: 200+行のプロレベル指示文
- `get_insights` 完全仕様: パラメータ、返却メトリクス（ベンチマーク付き）、breakdown一覧（行数目安付き）
- 分析フレームワーク7つ:
  1. パフォーマンス概要
  2. CPC要因分解（CPM vs CTR）
  3. クリエイティブ疲弊検知
  4. フリークエンシー管理（閾値テーブル: 認知3-5、検討2-4、CV4-7、リタゲ~10）
  5. 配置別分析（Feed/Stories/Reels特性）
  6. ファネル分析（Imp→Click→LP→CV）
  7. 動画分析（Hook Rate/Hold Rate）
- 効率的クエリパターン5例
- エラー対応ルール
- ツール一覧20個の正確な名称・パラメータ・出力

#### MCPResponseOptimizerPlugin Meta Ads対応（`mcp_response_optimizer.py`）
- `_COMPRESSED_DESCRIPTIONS` に Meta Ads 20ツールの圧縮説明を追加
- `META_ADS_VERBOSE_TOOLS` (`get_insights`, `get_campaigns`, `get_adsets`, `get_ads`) 定義
- `_compress_meta_ads_response()` 新規メソッド:
  - 冗長なネストJSON → パイプ区切りcompact table変換
  - 重要KPI（spend, impressions, clicks, cpc, cpm, ctr, conversions, cost_per_conversion, roas）を抽出
  - その他フィールドは `other_fields` としてまとめ
  - 200行上限、圧縮率ログ出力
- `_handle_ad_image()` 新規メソッド:
  - MCP `get_ad_image` の base64画像レスポンスを処理
  - PIL で ~Full HD にリサイズ
  - `types.Part.from_bytes()` で Gemini コンテキストに画像を注入
  - `before_model_callback` で `llm_request.contents` に画像を差し込み
  - テキスト結果のみ返却（画像はLLMコンテキストに直接注入）
- `_extract_image_from_mcp_result()`: base64画像データの抽出ヘルパー

#### オーケストレーター更新（`orchestrator.py`）
- AdPlatformAgent説明文を「Meta広告のパフォーマンス分析、クリエイティブ評価、ターゲティング提案」に更新
- キーワードマトリクスに広告関連ワードを拡充（広告画像、クリエイティブ、配置、リタゲ等）

---

## 2. 広告画像の永続保存 + フロントエンド表示

**コミット**: `8d1381e`
**目的**: `get_ad_image` で取得した広告画像をSupabase Storageに永続保存し、フロントエンドでmarkdown画像として表示。

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/infrastructure/adk/plugins/mcp_response_optimizer.py` | Supabase Storageアップロード追加 |
| `backend/app/infrastructure/adk/agents/ad_platform_agent.py` | 指示文にURL使用ガイダンス追加 |
| `frontend/src/components/marketing/v2/ChatMessage.tsx` | `img` markdownコンポーネント追加 |

### 変更詳細

#### Supabase Storage画像アップロード（`mcp_response_optimizer.py`）
- `_handle_ad_image()` に Supabase Storage アップロードステップを追加
- `_upload_ad_image_to_storage()` 新メソッド:
  - 保存先: `marketing-attachments/ad-images/ad_{ad_id}_{timestamp}.jpg`
  - 署名付きURL生成（7日間有効）
  - エラー時はURLなしで画像分析のみ続行（フォールバック安全）
- 返却テキストに永続公開URLを含め、エージェントが `![広告画像](URL)` でmarkdownに埋め込み可能に

#### Agent指示文更新（`ad_platform_agent.py`）
- `get_ad_image` 結果の Image URL を `![広告画像](URL)` で回答に含める指示
- `get_ad_creatives` の thumbnail_url（64x64）は使用しない旨を明記

#### Frontend `img` コンポーネント追加（`ChatMessage.tsx`）
- `markdownComponents` に `img` を追加
- スタイリング: `max-w-full`, `max-h-[500px]`, `rounded-lg`, `shadow-sm`, `border`
- `onError` で壊れた画像のフォールバック（`ImageIcon` プレースホルダー表示）
- クリックで原寸表示（`<a target="_blank">` ラップ）
- `loading="lazy"` でパフォーマンス最適化
- `useState` で画像エラー状態管理

---

## 3. ユーザー確認・選択肢UI（ask_user_clarification）

**コミット**: `dcad5dd`
**目的**: エージェントがユーザーの意図が曖昧な場合に、Claude Code風のインタラクティブ選択UIを表示して確認を取る機能。

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/infrastructure/adk/tools/ask_user_tools.py` | **新規** — ask_user_clarification ツール |
| `frontend/src/components/marketing/v2/AskUserPrompt.tsx` | **新規** — 選択肢UIコンポーネント（302行） |
| `backend/app/infrastructure/adk/agent_service.py` | ask_user検知ロジック追加 |
| `backend/app/infrastructure/adk/agents/orchestrator.py` | ツール登録 + 指示文ガイドライン追加 |
| `backend/app/presentation/api/v1/marketing_v2.py` | `ask_user` SSEイベント蓄積 |
| `frontend/src/hooks/use-marketing-chat-v2.ts` | `processEvent` に `ask_user` ケース追加 |
| `frontend/src/components/marketing/v2/ChatMessage.tsx` | ActivityTimelineに `ask_user` レンダリング追加 |
| `frontend/src/components/marketing/v2/MessageList.tsx` | `onSendMessage` prop追加・パススルー |
| `frontend/src/components/marketing/v2/MarketingChat.tsx` | `handleSend` を `onSendMessage` として渡す |

### アーキテクチャ

ADKネイティブ `LongRunningFunctionTool` + カスタムSSEイベント + フロントエンド選択UI

### フロー

```
1. オーケストレーターが ask_user_clarification(questions=[...]) を呼び出し
2. ツールは None を返す（LongRunningFunctionTool: skip_summarization=True）
3. agent_service._process_adk_event が function_call を検知 → ask_user SSEイベント生成
4. フロントエンドが選択肢ボタンUIを表示（AskUserPrompt コンポーネント）
5. ユーザーがクリック → 選択結果を新しいメッセージとして自動送信
6. エージェントが次のターンで選択結果を受け取り続行
```

### 変更詳細

#### ask_user_clarification ツール（`ask_user_tools.py`）
- `LongRunningFunctionTool` でラップ（再呼び出し防止）
- `skip_summarization=True` で LLM が None 応答を要約しない
- パラメータ: `questions: list[dict]`（question, header, options, multiSelect）
- 「その他」選択肢はシステムが自動追加するため、LLM生成に含めない指示

#### AskUserPrompt コンポーネント（`AskUserPrompt.tsx`）
- 302行の新規コンポーネント
- シングルセレクト: ラジオトグル（再クリックで解除）
- マルチセレクト: チェックボックストグル
- 全質問にシステムが自動で「その他（自由入力）」を追加
- 「送信」「スキップ」ボタン（即送信ではなく明示的な送信操作）
- 回答済み状態: 選択結果をハイライト表示、操作不可

#### agent_service.py
- `_process_non_text_part()`（partial=Falseパス）: `ask_user_clarification` は `pass`（重複防止）
- partial=True/None パスのみで1回処理（function_call 検知 → `ask_user` イベント生成）

#### orchestrator.py
- `ADK_ASK_USER_TOOLS` をオーケストレーターツールに追加
- 指示文に「ユーザーへの確認・選択肢提示」セクション追加:
  - 使うべき場面 / 使わない場面
  - 形式の例（question, header, options, multiSelect）
  - 注意事項: 選択肢提示後はテキスト出力を止めてユーザーの選択を待つ

#### marketing_v2.py
- `ask_user` イベントを `activity_items` リストに蓄積（DB保存対応）
- フィールド: `kind: "ask_user"`, `groupId`, `questions`, `answered: false`

#### use-marketing-chat-v2.ts
- `processEvent` に `ask_user` ケース追加
- `AskUserActivityItem` 型の import

#### ChatMessage.tsx
- ActivityTimeline に `ask_user` レンダリング追加
- `onSendMessage` prop チェーン追加

### ADK知見
- `LongRunningFunctionTool` はツール説明に自動で「NOTE: This is a long-running operation...」を付加
- ADKには `get_user_choice_tool`（組み込み）も存在するが、options が string[] のみで description 不可のため独自実装

---

## 4. ユーザーパーソナライズ基盤

**コミット**: `fa1a17e`
**目的**: Clerk認証情報を全エージェントに注入し、パーソナライズされた応答を実現。「自分のメール」「自分のSlack」「自分の担当」といった表現を正しく解釈可能に。

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/presentation/api/v1/marketing_v2.py` | initial_state拡充 + Slack ID解決 |
| `backend/app/infrastructure/slack/slack_service.py` | `lookup_user_by_email()` 追加 |
| `backend/app/infrastructure/adk/tools/slack_tools.py` | `get_my_slack_activity` 新ツール追加 |
| `backend/app/infrastructure/adk/agents/slack_agent.py` | 指示文パーソナライズ |
| `backend/app/infrastructure/adk/agents/orchestrator.py` | ユーザー情報 + ルーティング追加 |
| `backend/app/infrastructure/adk/agents/workspace_agent.py` | ユーザー情報セクション追加 |
| `backend/app/infrastructure/adk/agents/ca_support_agent.py` | 担当CA情報追加 |
| `frontend/src/components/marketing/v2/ChatMessage.tsx` | ツールUI設定追加 |
| `.claude/rules/sdk-notes.md` | ADK State Injection構文ドキュメント追加 |

### 変更詳細

#### Phase 1: ユーザーコンテキスト拡充（`marketing_v2.py`）
- `initial_state` に以下を追加注入:
  - `app:user_name` — Clerk認証からのユーザー名
  - `app:user_id` — ClerkユーザーID
  - `app:slack_user_id` — Slack API で自動解決
  - `app:slack_username` — Slackハンドル名
  - `app:slack_display_name` — Slack表示名
- Slack ID解決: `SlackService.lookup_user_by_email()` 呼び出し（非ブロッキング、失敗しても続行）

#### Phase 2: Slackメール→ユーザーID解決（`slack_service.py`）
- `lookup_user_by_email(email)` 新メソッド
- Slack API `users.lookupByEmail` 使用（`users:read.email` scope必要）
- 24時間TTLキャッシュ（pipe-separated compact format）
- 未発見も `__not_found__` でネガティブキャッシュ
- 返却: `user_id`, `username`, `display_name`, `real_name`

#### Phase 3: get_my_slack_activity 新ツール（`slack_tools.py`）
- 自分の投稿 + 自分へのメンションを一括取得
- パラメータ:
  - `activity_type`: `"all"` / `"my_posts"` / `"mentions"`（デフォルト: `"all"`）
  - `days_back`: 遡る日数（1-30、デフォルト7）
  - `max_results`: 取得件数（1-50、デフォルト30）
- stateから `app:slack_user_id` を自動取得して `from:<@USER_ID>` / `<@USER_ID>` で検索
- ADK_SLACK_TOOLS: 6→7ツール

#### Phase 4: 全エージェント指示文パーソナライズ

**orchestrator.py:**
- 「現在のユーザー」セクション追加
- ADK State Injection構文で値を直接注入: `{app:user_name}`, `{app:user_email}`, `{app:slack_display_name?}`, `{app:slack_username?}`
- パーソナライズルール: 氏名で呼びかけ
- 「自分の〜」表現の解釈マトリクス追加:
  - 「自分のメール」→ GoogleWorkspaceAgent
  - 「自分の予定」→ GoogleWorkspaceAgent
  - 「自分のSlack」→ SlackAgent
  - 「自分の担当候補者」→ ZohoCRMAgent / CASupportAgent

**slack_agent.py:**
- 「現在のユーザー情報」セクション追加（氏名、メール、SlackユーザーID、ハンドル名、表示名）
- `get_my_slack_activity` のツール説明・ワークフロー例追加
- 「自分の」「私の」リクエストの解釈ルール追加
- 回答方針: ユーザー名で呼びかけ、自分の投稿は「あなたの投稿」と表現

**workspace_agent.py:**
- 「現在のユーザー」セクション追加（氏名、メール）
- 回答時はそのままの名前で呼びかけ指示

**ca_support_agent.py:**
- 「現在のユーザー（担当CA）」セクション追加
- 「自分の担当候補者」→ Zoho Owner/PICフィールドで検索指示
- 「自分の面談」→ 議事録ツールでユーザー名検索指示

#### フロントエンド（`ChatMessage.tsx`）
- `get_my_slack_activity` のアイコン（User）・ラベル（自分のSlack活動）追加

### ADK State Injection 知見
- `{app:user_name}` 構文（波括弧）で指示文にstate値を自動注入
- `{app:key?}` — `?` サフィックスでオプショナル（未設定時にKeyError回避）
- バッククォート `` `app:key` `` は単なるテキスト — モデルは値にアクセスできない
- `instruction` が文字列の場合のみ自動注入（`InstructionProvider` callableの場合はバイパス）
- ADKソース: `.venv/.../google/adk/utils/instructions_utils.py` L30-124

---

## 全体の変更ファイル一覧

```
 .claude/rules/sdk-notes.md                                        |  +20
 CLAUDE.md                                                         | +187
 README.md                                                         |   +1/-1
 backend/app/infrastructure/adk/agent_service.py                   |  +16/-1
 backend/app/infrastructure/adk/agents/ad_platform_agent.py        | +202 (大幅書き換え)
 backend/app/infrastructure/adk/agents/ca_support_agent.py         |   +7
 backend/app/infrastructure/adk/agents/orchestrator.py             |  +81 (4コミット累積)
 backend/app/infrastructure/adk/agents/slack_agent.py              |  +59/-21
 backend/app/infrastructure/adk/agents/workspace_agent.py          |   +5
 backend/app/infrastructure/adk/mcp_manager.py                     |  +34/-1
 backend/app/infrastructure/adk/plugins/mcp_response_optimizer.py  | +508 (大幅拡張)
 backend/app/infrastructure/adk/tools/ask_user_tools.py            |  +54 (新規)
 backend/app/infrastructure/adk/tools/slack_tools.py               | +108
 backend/app/infrastructure/chatkit/attachment_store.py             |   +8/-8
 backend/app/infrastructure/slack/slack_service.py                  |  +79
 backend/app/presentation/api/v1/marketing_v2.py                   |  +31/-2
 backend/pyproject.toml                                            |   +1
 backend/uv.lock                                                   |   +2
 frontend/src/components/marketing/v2/AskUserPrompt.tsx            | +302 (新規)
 frontend/src/components/marketing/v2/ChatMessage.tsx              |  +58/-3
 frontend/src/components/marketing/v2/MarketingChat.tsx            |   +1
 frontend/src/components/marketing/v2/MessageList.tsx              |   +4
 frontend/src/hooks/use-marketing-chat-v2.ts                       |  +53/-1
 frontend/src/hooks/use-marketing-chatkit.ts                       |   -4
```
