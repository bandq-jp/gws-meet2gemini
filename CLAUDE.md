# CLAUDE.md - 永続メモリ & 自己改善ログ

> ## **【最重要】記憶の更新は絶対に忘れるな**
> **作業の開始時・途中・完了時に必ずこのファイルを確認・更新せよ。**
> コード変更、設計変更、新しい知見、バグ修正、アーキテクチャ変更 — どんな小さな変更でも、発生したらその場で即座にこのファイルに記録すること。
> **ユーザーに「記憶を更新して」と言われる前に、自分から更新するのが当たり前。言われてからでは遅い。**
> これは最優先の義務であり、他のどんなタスクよりも優先される。

> **このファイルはClaude Codeの永続メモリであり、自己改善の記録である。**
> セッションをまたいで知識を保持し、過去の失敗・学び・判断を蓄積して次のセッションの自分をより賢くするためのファイルである。

## 運用ルール

1. **毎回の作業開始時**にこのファイルを読み込み、内容に従って行動する
2. **作業中に新しい知見・決定・変更が生じたら**、即座にこのファイルを更新する
3. **更新対象**: アーキテクチャ変更、新しい依存関係、デプロイ設定、踏んだ罠・解決策、環境差異、運用ルール
4. このファイルの情報が古くなった場合は削除・修正し、常に最新状態を維持する
5. **情報ソースも記録**: 公式ドキュメントURL・GitHubリポジトリ・SDKソースファイルパス
6. **自己改善**: ユーザーに指摘された間違い・非効率・判断ミスは「自己改善ログ」セクションに記録する

---

## Package Management (STRICT)

- **Backend (Python)**: `uv add <package>` — **Never use `pip install`**
- **Frontend (JS/TS)**: `bun add <package>` — **Never use `npm install` or `yarn add`**
- Backend lock: `uv sync`
- Frontend lock: `bun install`

---

## メモリ構成

詳細情報は `.claude/rules/` に分割配置（自動ロード）:

| ファイル | 内容 |
|---------|------|
| `project.md` | プロジェクト概要、主要機能 |
| `tech-stack.md` | Backend/Frontend/Infrastructure 技術スタック |
| `structure.md` | ディレクトリ構造 |
| `backend.md` | DDD/オニオンアーキテクチャ、APIエンドポイント |
| `chatkit.md` | ChatKit & マーケティングAI 詳細設計 |
| `sdk-notes.md` | SDK バージョン & 技術的知見 |
| `database.md` | Supabaseテーブル定義 |
| `frontend.md` | フロントエンドルート |
| `env-vars.md` | 環境変数 |
| `dev-commands.md` | 開発コマンド、Git Branching |

セッション変更履歴（詳細な実装ログ）:
- `docs/session-history/2026-02.md` — 2月全実装の詳細記録

---

## 現在のシステム状態 (2026-02-27更新)

### ADKエージェント構成
- **オーケストレーター**: Gemini 3 Flash Preview, Context Cache有効 (90%コスト削減)
- **サブエージェント (10個)**: AnalyticsAgent(GA4), SEOAgent(GSC), AdPlatformAgent(Meta Ads 20ツール), ZohoCRMAgent(3層12ツール), CompanyDatabaseAgent(20ツール: semantic+strict+Gmail+Slack), CASupportAgent(31ツール), WorkspaceAgent(Gmail+Calendar 8ツール), SlackAgent(7ツール), GoogleSearchAgent, CodeExecutionAgent
- **共通機能**: ask_user_clarification, マルチモーダルアップロード, State永続化, OTelテレメトリ(Phoenix)
- **State注入**: app:user_name/email/id, app:slack_*, app:current_date/time/day_of_week

### フィードバックシステム
- ThumbsUp/Down + テキストアノテーション (mark.js), AnnotationPanel
- FBレビューダッシュボード (/feedback), JSONL/CSVエクスポート
- DB: feedback_dimensions, feedback_tags, message_feedback, message_annotations

### トークン最適化
- MCPResponseOptimizerPlugin: GA4/Zoho/Meta Adsレスポンス圧縮 (60-80%削減)
- MCPツールフィルタ: GA4 6→2, GSC 9→7, Meta Ads 30→20
- before_model_callback: ツール説明文の自動圧縮
- 広告画像: after_tool→before_model 2段パイプラインでマルチモーダル注入

### エラー耐性
- サブエージェント503: on_tool_error_callbackでdict返却→re-raise回避
- オーケストレーター503: _pump_adk_events()で指数バックオフリトライ (2s→4s→8s, 最大3回)

### ADKフィードバック対応 (2026-02-27)
- **メモリ閾値修正**: `similarity_threshold` 0.3→0.55、`memory_max_results` 5→3（他会話のトピック混入対策）
- **オーケストレーター指示文強化**: ルール5修正（記憶の慎重な活用）、ルール6追加（定義の一貫性）、ルール7追加（データ出所の透明性）
- **ZohoCRM指示文強化**: チャネル別フィルタルール（org_hitocareer等）、ステータス厳守ルール（"12. 内定"のみが内定）
- **Slack指示文強化**: プライバシー制御ルール追加（人事・評価・給与情報の非表示、機密チャネル情報の省略）
- **AdPlatform指示文強化**: データなし時の正直な報告ルール追加
- **セッション復元**: `_restore_context_items()` でCloud Run再起動後も `context_items` をADKセッションに注入（テキスト部分のみ、function_call/responseは除外）
- **Zoho `get_conversion_metrics` 文字列比較バグ修正**: `interview_plus` がPython辞書順比較で `"12. 内定" < "4. 面談済み"` となり**常に0件**になっていた。`_status_number()` ヘルパーで先頭番号を数値抽出し正しく比較するよう修正
- **Slack DM除外**: 全検索クエリに `-is:dm` を追加。`_build_search_query`、`search_company_in_slack`、`search_candidate_in_slack`、`get_my_slack_activity` の全箇所

### 議事録一覧ページネーション
- `meeting_documents_enriched` VIEW: `is_structured`, `zoho_sync_status` を計算列で持つ
- 全タブ1クエリ: `count="exact"` + `.range()` でSQL側フィルタ+ページネーション
- マイグレーション: `0023_add_meeting_documents_enriched_view.sql`
- ブラウザバック対応: URL search params (`?tab=sync_failed&page=2`) + `replaceState`

### Zoho自動同期 名前マッチング (2026-02-11改善)
- **extract_from_title**: `_TIME_PREFIX_RE` でJP時間プレフィックス事前除去 (修正前56%→修正後74%正常抽出)
- **`~`→`[~〜～]`**: 全角チルダ`〜`/`～`もlookbehind対象に追加
- **ダブルスペース対応**: regex中の `[\s　]` → `[\s　]+` で複数スペース許容
- **CandidateTitleMatcher**: `_normalize_spaceless()` で全スペース除去比較を追加
- **is_exact_match**: 2段階比較 (1.標準正規化 → 2.スペース除去比較)
- **get_search_variations**: 名前バリエーション生成 (raw, normalized, spaceless)
- **search_app_hc_by_exact_name**: 多バリエーション×equals → starts_withフォールバック
- **auto_process**: 複数Zohoヒット時は正規化マッチで1件に絞り込み
- **実データ分析**: Zoho名はスペースあり/なし混在。`向井直也`(spaceless)で検索ヒット確認済み
- **全角括弧対応**: `（仮）石岡様` → regex除外+`_NOISE_PREFIX_RE`で`（仮）`除去。Zoho API 400を回避
- **残課題**: 姓のみタイトル (`田中様_初回面談`) は26%存在→データ制約で改善不可
- **残課題**: Zoho重複レコード（同名別ID: 向井直也×2, 大石周×2）→正しくスキップするが手動対応必要

### 画像生成スタジオ バグ修正 (2026-02-24)
- **BFFプロキシ gaxios問題**: 本番環境で `client.request()` (gaxios) が multipart/form-data の ArrayBuffer を `JSON.stringify()` → `{}` に変換していた。ファイルアップロード時は native `fetch()` + IDトークンヘッダーで転送するよう修正
- **handleGenerate Race Condition**: `handleNewSession()` 後の React State更新が非同期のため `currentSession` が null のまま `generateImage()` に渡されていた。`generateImage` に `sessionId` オプションを追加し、新規セッションIDを直接渡すよう修正
- **update_session({}) 空dict PATCH**: `image_gen.py` で `update_session(session_id, {})` が PostgREST に空body PATCH を送信していた。`{"updated_at": ...}` を明示的に渡すよう修正
- **教訓**: `google-auth-library` の `client.request()` (gaxios内部) は `ArrayBuffer` を `JSON.stringify()` してしまう。バイナリデータ転送には native `fetch()` + `getRequestHeaders()` でIDトークンだけ取得して使う

### 画像生成スタジオ 大規模修正 (2026-03-18)
- **Multi-turn会話対応**: `generate_image` がセッション内の過去メッセージをGemini APIに渡すよう修正。`client.chats.create()` + `chat.send_message()` でThought Signatureを自動管理。これにより「前の画像を修正して」等の文脈を維持した会話が可能に
- **system_instruction対応**: テンプレートのsystem_promptを `[System Context]` テキストとしてではなく、Gemini APIのネイティブ `system_instruction` パラメータで渡すよう修正
- **テンプレート選択の同期修正**: 履歴からセッションをロードした際に `selectedTemplateId` がセッションの `template_id` と同期されていなかった問題を修正。テンプレート選択変更時もバックエンドのセッションに反映
- **セッションPATCH APIエンドポイント追加**: `PATCH /sessions/{session_id}` でテンプレート変更を永続化
- **0.5Kサイズ削除**: UIとバックエンドから `0.5K` を削除。DB CHECK制約 `('1K', '2K', '4K')` に合わせる
- **google-genai SDK更新**: `>=1.65.0` → `>=1.66.0` に更新、uv.lockで `1.68.0` に解決
- **ConversationMessage dataclass追加**: 会話履歴の型安全な受け渡し用
- **_build_conversation_history()**: セッション内メッセージをGemini API形式に変換。assistant画像はStorageからダウンロードして含める
- **教訓**: Gemini画像生成はchat APIでThought Signatureを自動管理。`generate_content` 直接呼びではマルチターンの文脈が失われる
- **教訓**: Gemini画像生成の `system_instruction` は `GenerateContentConfig` のパラメータとして渡す（contentsに混ぜない）

### 画像生成 503 UNAVAILABLE 自動リトライ対応 (2026-04-17)
- **症状**: `gemini-3.1-flash-image-preview` が高負荷時に `503 UNAVAILABLE` を返し、画像生成が失敗。2026-04-10/04-11/04-17 と継続発生（refs=4, size=4K, ratio=auto で約33秒後に503、`"This model is currently experiencing high demand"`）
- **根本原因**: `genai.Client()` 初期化時にリトライ設定なし。SDKデフォルトは `stop_after_attempt(1)`（=リトライなし）
- **修正**: `image_generator.py` の Client 初期化で `HttpOptions(retry_options=HttpRetryOptions(...))` を指定。attempts=5, initial_delay=2s, max_delay=30s, exp_base=2, jitter=1, http_status_codes=[408,429,500,502,503,504]、HTTP timeout=300秒
- **SDK仕様**: `google-genai` v1.68.0 の `HttpRetryOptions` は tenacity ベース。Client レベルで設定すると `chat.send_message()` 経由でも同じリトライが有効（`_api_client.py` L758 `self._retry = tenacity.Retrying(**retry_kwargs)`）
- **検証**: モックで503×2を返すシミュレーション→3回目で成功。指数バックオフ+ジッタで ~2.6s → ~4.6s の遅延、SDKログに `"Retrying ... as it raised ServerError: 503"` が自動出力
- **教訓**: `genai.Client()` はデフォルトでリトライしない。503/429/504など一時的エラーが想定される本番APIコールでは `HttpRetryOptions` 必須。画像/動画など高負荷モデル呼び出しには特に重要

### Zoho CRM ファネル指標修正 (2026-03-30)
- **根本原因**: 面談実施数を `customer_status = "4. 面談済み"` で数えていたが、ステータスが先に進んだ人（提案中、内定、入社）やクローズされた人が漏れていた。修正前96人→修正後2,636人（27.5倍の差）
- **修正内容**: `field29`（面談日フィールド）が `NOT NULL` のレコードをカウントする方式に変更。クローズ（4,154件中2,113件が面談済み）も正確にカウントされる
- **影響範囲**: ChatKit `count_job_seekers_by_status`, `analyze_funnel_by_channel`, `compare_channels` / ADK `analyze_funnel_by_channel`, `compare_channels`, `get_pic_performance`, `get_conversion_metrics`
- **ZohoClient追加メソッド**: `count_interviewed()`, `count_interviewed_by_channel()` — `INTERVIEW_DATE_FIELD_API = "field29"` ベース
- **検証結果**: Zoho API面談数(2,636) > スプシRAWDATA面談数(1,718) — スプシは2025年末スナップショットのため差分は正常
- **関連発見**: cv-via-studioのrow 195/890がEmail不正で毎分リトライ失敗（zohoID既存だがスキップされてない）

### LP流入スプシ SSoT直読み (2026-04-03)
- **目的**: GAS/スプシ（responses02）をSSoT（Single Source of Truth）として直接読み取り、Zoho経由のデータ漏れ（19%）を解消
- **新規ファイル**:
  - `infrastructure/google/lp_sheets_service.py` — Sheets API読み取り + TTLキャッシュ(300s)
  - `infrastructure/google/lp_lead_evaluator.py` — 有効リード/TCV判定・チャネル分類（GAS数式と同等）
  - `infrastructure/adk/tools/lp_analytics_tools.py` — ADKツール5個
  - `infrastructure/chatkit/lp_analytics_tools.py` — ChatKitツール5個
- **ツール**: `get_lp_cv_summary`, `get_lp_cv_by_channel`, `get_lp_interview_bookings`, `get_lp_funnel`, `compare_lp_vs_zoho`
- **AnalyticsAgent統合**: ADK/ChatKit両方のAnalyticsAgentにLPツールを追加。エージェント指示文 + オーケストレーター指示文にLP CV優先ルーティングを明記
- **有効リード基準**: 年齢23-32歳 + 許可勤務地（東京都,神奈川県等10箇所）→ スプシ数式と100%一致検証済み
- **TCV基準**: 有効リード + 営業経験(salesexp="はい") → 同100%一致
- **チャネル分類**: parentPathベース（/meta*→meta, /media*→media, /cp_a*→ad等）— GAS identifySource_()と同等
- **検証結果**: ライブスプシ(946行) > xlsx(916行) — 30行の新規追加分。meta有効リード: API=382 vs xlsx=360（差22=新規行分）
- **環境変数**: `LP_SPREADSHEET_ID=12oRSU23GWBvJ5QD74QGNkRxlESQYmJM_U6YQsXeb7V8`
- **SAアクセス**: `bandq-dx@bandq-dx.iam.gserviceaccount.com` をスプシに閲覧者共有

### LP CVツール常時登録 + 範囲フィルタバグ修正 (2026-04-17)
- **症状**: マーケティングチャットで「CV値についてget_lpツールで教えて」と聞くと「このツールは使えません」と返答。Cloud Run の `LP_SPREADSHEET_ID` 環境変数が未設定で、3箇所のファクトリで `if self._settings.lp_spreadsheet_id:` ガードによりツール未登録だった
- **修正1 (ツール常時登録)**:
  - `settings.py` の `lp_spreadsheet_id` にデフォルト値 `12oRSU23GWBvJ5QD74QGNkRxlESQYmJM_U6YQsXeb7V8` を埋め込み
  - `seo_agent_factory.py` / `chatkit/agents/analytics_agent.py` / `adk/agents/analytics_agent.py` の条件分岐を削除し、LPツールは無条件に登録
- **修正2 (日付フィルタバグ)**: `_filter_by_period` と `get_lp_interview_bookings` で `timestamp[:10]` を文字列比較していたが、スプシのタイムスタンプは `2026/04/17 11:48:33` のスラッシュ区切りで、`date_from="2026-04-01"` と比較すると `"/" (0x2F) > "-" (0x2D)` により全件除外される重大バグ。`_normalize_date()` ヘルパで `/` → `-` に正規化してから比較
- **検証**: 2026-04-01〜04-17 の範囲で実スプシから 134件(test除外後)、meta 111件、有効リード109 (81.3%)、TCV 69 (51.5%)、面談予約 54 (40.3%) を正しく取得
- **教訓**: 業務重要ツールは環境変数ガードで無効化せず、必要な設定はコード側のデフォルト値で保証する（スプシIDはSA共有が前提なので公開でも問題なし）
- **教訓**: 日付フィルタは文字列比較する前に必ず区切り文字を正規化する。スプシ/GAS由来のタイムスタンプはスラッシュ区切りが多い

---

## 自己改善ログ（教訓集）

> 過去の失敗から抽出した再現性のあるルール。同じ過ちを繰り返さないための行動規範。

### SDK・外部ライブラリ
- **SDK機能を最初に徹底調査**: カスタム実装は最終手段。まずソースコードを全て読んで機能を把握してから設計
- **実データで検証してから設計**: ドキュメントだけでなく実際のAPIレスポンスを確認（Zoho v2/v7差異等は実測でしか発見不可）
- **モデル名・バージョンを確認してから調査**: 設定ファイルの実値を見ずに推測で実装しない
- **SDKのテンプレート/注入機能を最初に確認**: ADK State Injection `{app:key}` vs バッククォート `` `app:key` `` は全く別物

### ADK固有
- **State Injection**: `{app:key}` (波括弧) = 値を自動注入。バッククォートはただのテキスト
- **Plugin callback戻り値**: `None`=デフォルト動作、dict=オーバーライド（on_tool_error_callbackでdictを返せばre-raise回避）
- **google_search/BuiltInCodeExecutor**: 他ツールと同居不可→専用サブエージェント必須
- **App使用時**: pluginsはAppに設定（Runnerではなく）
- **MCP Image**: mcp_tool.pyがJSON dictにシリアライズ→before_model_callbackでPartsを直接注入が唯一の解
- **新エージェント追加時**: Plugin SUB_AGENT_NAMES + フロントエンドUI設定を必ず同時更新
- **InMemorySessionService揮発性**: Cloud Run再起動で全セッション消失。context_itemsをEventとして再注入すれば復元可能。`sessions`属性はpublicアクセス可
- **PreloadMemoryTool閾値**: similarity_threshold=0.3は低すぎて別会話のトピックが混入する。0.55以上を推奨。max_resultsも3程度に絞る
- **エージェント指示文にドメイン知識を**: Zohoチャネルフィルタ、ステータス値の厳密な定義、データなし時の報告義務など、業務知識を指示文に明記しないとAIが推測する
- **番号付きステータスの文字列比較は壊れる**: `"12. 内定" >= "4. 面談済み"` は辞書順で `False`（`"1" < "4"`）。番号抽出して数値比較が必要
- **ステータスベースのファネル計数は大幅に過少**: `customer_status = "4. 面談済み"` はスナップショット（その時点でそのステータスにいる人のみ）。CRMでは面談→提案→クローズと進むため、面談済みの人がステータス4から消える。正確な面談数は **面談日フィールド(field29) IS NOT NULL** で数える。検証: ステータスベース96人 vs field29ベース2,636人（27.5倍の差）
- **GA4 Thanks_All ≠ フォーム送信数**: Thanks_AllはサンクスページPVイベント。直接アクセス、リロード、bot等もカウントされるため、実際のCV数より大幅に多くなる（検証: GA4=998 vs スプシ=609）

### 設計判断
- **機能配置**: 別エージェントか既存統合かはユーザーに確認。同ドメインは原則同エージェント
- **参考プロジェクト**: 提示されたら全ファイルを徹底的に読む
- **段階的実装**: 勝手に段階を設けず、要件通りに一括実装
- **推測で実装するな**: 実測値を確認（MCP初期化<1msなのに1.2-1.7sと推測していた）

### エージェント指示文
- **日付は明示注入必須**: LLMは今日の日付を知らない。initial_stateで注入
- **実務者の指標名でデフォルト報告**: Meta Ads clicksとinline_link_clicksは別物。マーケター目線の指標を使う
- **mark.jsのoffsetはDOM textContentベース**: markdown原文とは異なる

### フロントエンド
- `opacity-0 group-hover:opacity-100` はモバイルで消える → `sm:` prefix必須
- Portal系の固定幅は `Math.min(desired, window.innerWidth - margin)` で動的計算
- `100vh` → `100dvh` でモバイルアドレスバー対応
- shadcn/ui SidebarのSheet mobileは `SidebarTrigger` 配置だけで動作
- **gaxios (google-auth-library) はバイナリ非対応**: `client.request({ data: ArrayBuffer })` は内部で `JSON.stringify()` → `{}` に化ける。multipart/form-data送信には `client.getRequestHeaders()` + native `fetch()` を使う
- **React State更新後の即時参照**: `setState()` 直後の値は古いclosureを参照。新しい値が必要な場合は関数の戻り値を直接使い、State経由の参照を避ける

### Gemini画像生成API
- **Multi-turn必須**: `client.chats.create()` + `chat.send_message()` を使う。`client.models.generate_content()` 直接呼びではThought Signatureが管理されず文脈が失われる
- **Thought Signature**: 暗号化された推論コンテキスト。chat API使用時はSDKが自動管理。手動で `generate_content` を使う場合は応答のsignatureを次ターンに含める必要あり（400エラー回避）
- **system_instruction**: `GenerateContentConfig(system_instruction=...)` で渡す。contentsに `[System Context]` テキストとして混ぜるのは非推奨
- **参照画像とSearchは排他**: reference_images使用時はGoogle Search/Image Searchを無効にする必要あり
- **image_size大文字必須**: `"1k"` は400エラー、`"1K"` が正しい
- **モデル**: `gemini-3.1-flash-image-preview` (Nano Banana 2)。Pro版は `gemini-3-pro-image-preview`

### API固有知見
- **Slack**: `search.messages`はUser Token(`xoxp-`)のみ。Bot Token(`xoxb-`)では`not_allowed_token_type`
- **Zoho COQL**: WHERE句必須、LIKE非サポート
- **Zoho Search API**: `equals`はスペース含む完全一致。日本語名は`equals`+`starts_with`フォールバック+名前バリエーション(spaceless等)で検索精度向上
- **Meta Ads**: `get_insights`のbreakdownは1つずつ、7d_view/28d_viewは2026年1月廃止、budgetはcents
- **PostgREST NOT IN**: 大量UUIDのNOT INフィルタはURL長制限で400エラー。VIEWで計算列を使うのが正解

---

> ## **【最重要・再掲】記憶の更新は絶対に忘れるな**
> 作業が完了したら、コミットする前に、必ずこのファイルに変更内容を記録せよ。
> **「後で更新しよう」は禁止。今すぐ更新せよ。**
