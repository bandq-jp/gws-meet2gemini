# ADK V2 改善計画（最終版）

> 2026-02-06 作成。5並列調査 + コード実査で全項目を検証済み。

---

## 構造的問題トップ3

### 1. CASupportAgent のアーキテクチャ問題

CASupportAgent が 27 ツール（ZohoCRM 10 + CandidateInsight 4 + CompanyDB 9 + Meeting 4）をフラットに保持。
個別エージェント（ZohoCRMAgent, CompanyDatabaseAgent 等）と完全にツール重複。
Gemini がオーケストレーターレベルでどちらを呼ぶべきか混乱する。

**解決方針**: AgentTool description を排他的に書き換え + オーケストレーターに明確な分岐ルール追加。
- 単一ドメイン（CRMだけ、企業DBだけ） → 専門エージェント
- クロスドメイン（候補者個人の面談準備・企業提案・リスク分析を一括） → CASupportAgent

### 2. キャッシュ不在によるレイテンシ

- Sheets API: キャッシュインスタンスが毎回新規作成で実質無効（**実査確認済み**）
- Zoho `_fetch_all_records`: 3000件を毎回全ページング（12秒+）
- Embedding API: 同一クエリでも毎回API呼び出し
- ZohoClient: 毎ツール呼び出しで新規インスタンス

**解決方針**: シングルトン化 + TTL キャッシュ + LRU キャッシュの3段構え。

### 3. プロンプト品質の格差

| エージェント | instruction品質 | ツール仕様 | ワークフロー例 | エラー対応 |
|-------------|---------------|-----------|--------------|----------|
| ZohoCRMAgent | 詳細 | テーブル形式 | あり | なし |
| AnalyticsAgent | 詳細 | パラメータ例付き | あり | なし |
| CompanyDatabaseAgent | 詳細 | 優先度付き | あり | なし |
| CASupportAgent | 中程度 | リストのみ | あり（但し厳密検索使用） | なし |
| CandidateInsightAgent | **極端に簡素（3行/ツール）** | なし | なし | なし |
| SEOAgent | 中程度 | カラム名のみ | なし | なし |
| AdPlatformAgent | 中程度 | ツール名のみ | なし | なし |
| WordPressAgent | 中程度 | なし | なし | なし |

**解決方針**: 全エージェントに共通テンプレート適用（ツール仕様テーブル + ワークフロー例 + エラー対応 + 出力量管理）。

---

## I. ツール定義の精度改善

### Critical（動かない / データが壊れる）

| # | 問題 | 対象 | 改善案 | 実査結果 |
|---|------|------|--------|---------|
| T-1 | `get_job_seekers_batch` が `zoho.get_app_hc_records_batch()` を呼ぶが **メソッドが存在しない** → `AttributeError` | `zoho_crm_tools.py:174` | `ZohoClient` に COQL `IN` 句でバッチ取得メソッドを実装 | **確認済み: メソッド未定義** |
| T-2 | `_get_sheets_service()` が **毎回新インスタンス生成** → TTLキャッシュ無効 → 全企業DBツールで毎回Sheets API | `company_db_tools.py:34-38` | `@lru_cache(maxsize=1)` またはモジュールレベルシングルトン | **確認済み: キャッシュ無し** |
| T-3 | Embedding `task_type` 不一致。文書=`retrieval_document`、クエリ=**未指定** → ベクトル空間ミスマッチ → セマンティック検索精度低下 | `semantic_company_tools.py:35` | `config` に `task_type="RETRIEVAL_QUERY"` 追加 | **確認済み: task_type未指定** |
| T-4 | CandidateInsight 4ツールの **docstring が英語**。他全ツールは日本語。ADK は docstring をそのまま Gemini に渡すため、言語不一致でツール選択精度低下 | `candidate_insight_tools.py` | 日本語に統一 | **確認済み: 全て英語** |

### High（精度・パフォーマンスに直接影響）

| # | 問題 | 対象 | 改善案 |
|---|------|------|--------|
| T-5 | `get_job_seeker_detail` が **生Zohoフィールドコード**（`field14`等）を返却。`get_job_seekers_batch` は日本語ラベル変換済み → 不一致 | `zoho_crm_tools.py:154` | `_format_job_seeker_detail()` で整形して返す |
| T-6 | `generate_candidate_briefing` と `get_candidate_full_profile` が **機能重複**。両方 Zoho+構造化データ統合。LLM が判断不能 | `meeting_tools.py` / `candidate_insight_tools.py` | docstring に相互参照 + 用途の違いを明記。理想は1つに統合 |
| T-7 | `match_candidate_to_companies`（厳密）vs `find_companies_for_candidate`（セマンティック）の **使い分けが不明確** | `company_db_tools.py` / `semantic_company_tools.py` | docstring に「採用要件の厳密チェック→前者、転職理由からの意味検索→後者」を明記 |
| T-8 | `render_chart` の `chart_spec` が **`str` 型（JSON文字列）** → LLM の JSON構築エラー多発 | `chart_tools.py:19` | `dict` 型に変更。内部の `json.loads` を除去 |
| T-9 | `get_company_detail` が `full_data`（全52列の生データ）を返却 → **トークン浪費** | `company_db_tools.py` | `full_data` フィールド削除、構造化フィールドのみ返す |
| T-10 | Zoho `customer_status` と `field19` が **混在** → 同じ候補者のステータスがツール間で異なる | `zoho_crm_tools.py:195` / `meeting_tools.py:271` | `customer_status` に統一 |
| T-11 | ZohoClient が **毎ツール呼び出しで新規インスタンス** | `zoho_crm_tools.py` 全体 | モジュールレベルシングルトン or `@lru_cache` |
| T-12 | Embedding API に **キャッシュなし**（同一クエリでも毎回API呼び出し） | `semantic_company_tools.py` | `@lru_cache(maxsize=256)` 導入 |
| T-13 | Zoho `_fetch_all_records` に **キャッシュなし**（3000件を毎回全ページング） | `zoho_crm_tools.py` | TTLキャッシュ導入（5分） |
| T-14 | 全ツール共通で **リトライロジックなし** | 全 tools ファイル | `@retry_transient` デコレータ追加（指数バックオフ、最大3回） |
| T-15 | 多くのツールで **Returns セクションが欠如** → LLM が戻り値の構造を理解できない | 複数ファイル | `semantic_search_companies` を模範として全ツールに追加 |

### Medium（改善推奨）

| # | 問題 | 改善案 |
|---|------|--------|
| T-16 | `get_company_requirements` vs `get_company_detail` の差別化未記載 | docstring に「要件のみ高速取得→前者、全情報一括→後者」 |
| T-17 | `get_appeal_by_need` に転職理由→need_type マッピングガイドなし | docstring に変換例追加 |
| T-18 | `search_meetings` の candidate_name+title 検索が AND にならない | フォールバックロジックを docstring に明記 |
| T-19 | `get_meeting_transcript` の 10000文字切り詰めが docstring 未記載 | 明記 |
| T-20 | `trend_analysis_by_period` の `period_type` に enum 制約なし | バリデーション追加 + docstring に有効値明記 |
| T-21 | セマンティック検索の類似度閾値が 0.3 固定 | パラメータ化（デフォルト 0.3） |
| T-22 | `count_job_seekers_by_status` vs `analyze_funnel_by_channel` の違いが曖昧 | docstring で差別化（全体俯瞰→前者、特定チャネル深堀→後者） |

---

## II. オーケストレーター・指示文の精度改善

### Critical

| # | 問題 | 改善案 |
|---|------|--------|
| O-1 | **CASupportAgent vs 個別エージェントの境界が曖昧**。「企業提案」「面談準備」がどちらにも該当 | 明確な分岐ルール追加: `特定候補者名/ID付き + クロスドメイン → CASupportAgent` / `単一ドメインの集団分析 → 専門エージェント` |
| O-2 | **CASupportAgent 27ツールの選択判断基準が不十分**。ワークフロー例5パターンのみ | ツール選択フローチャート追加: Step1→候補者情報取得 → Step2→企業マッチング → Step3→リスク分析 |
| O-3 | **AgentTool description の差別化不足**。CompanyDB と CASupport の両方に「企業提案」が含まれる | description を排他的に書き換え |

### High

| # | 問題 | 改善案 |
|---|------|--------|
| O-4 | **全サブエージェントに思考プロセス指示がない** | 共通テンプレート:「1.質問分解→2.ツール選択→3.結果検証→4.統合出力」 |
| O-5 | **エラーハンドリング指示が全体的に欠如** | 共通ルール:「修正可能→再試行、不可能→報告、代替あり→代替ツール」 |
| O-6 | **CandidateInsightAgent の instruction が極端に簡素（3行/ツール）** | ZohoCRMAgent 並みにツール仕様テーブル + ワークフロー例を追加 |
| O-7 | **`render_chart` の使用条件がオーケストレーターに未記載** | 「数値データは必ずチャートで可視化」+ タイプマッピング（時系列→line、比較→bar、構成比→pie、ファネル→funnel） |
| O-8 | **セマンティック検索失敗時のフォールバック手順なし** | CompanyDBAgent に「セマンティック→厳密検索→条件緩和→ユーザー報告」フロー追加 |
| O-9 | **CASupportAgent のワークフロー例が厳密検索を使用**。`match_candidate_to_companies` を例示→セマンティック優先原則と矛盾 | `find_companies_for_candidate` に書き換え |
| O-10 | **キーワードマトリクス外のクエリへの対応指示なし** | 「該当ドメイン不明→最も関連性の高いエージェントを推測して即実行」 |
| O-11 | **キーワードマトリクスにギャップ**: 「コンバージョン」「ROI」「Indeed」「応募」が未定義 | マトリクスに追加 |
| O-12 | **全 `build_agent()` オーバーライドで `generate_content_config` 欠如** → Gemini 3 Flash 早期終了リスク | `max_output_tokens=65536` を全エージェントに設定 |

### Medium

| # | 問題 | 改善案 |
|---|------|--------|
| O-13 | 並列呼び出しパターンと CASupportAgent 推奨パターンが矛盾 | 使い分けルールを明記 |
| O-14 | CompanyDBAgent の出力フォーマット指示が曖昧 | テーブル形式の例を追加 |
| O-15 | ZohoCRMAgent のステータスフロー記載が不完全 | 全ステータスを網羅 |
| O-16 | 日付デフォルト値の指示なし | 「期間未指定→直近3ヶ月」ルール追加 |
| O-17 | 出力量管理の指示なし | 「大量データは上位10件に絞り要約」ルール追加 |
| O-18 | MCP経由ツール名が instruction と一致しないリスク | 「実際のツール名はツール一覧を参照」と追加 |

---

## III. フロントエンド UX 改善

### Critical

| # | 問題 | ファイル | 難易度 | 実査結果 |
|---|------|---------|--------|---------|
| U-1 | ThinkingIndicator の **CSS が未定義**。`thinking-dot-1/2/3` が globals.css に存在しない → ドットが見えない | `globals.css` | Easy | **確認済み: CSS未定義** |
| U-2 | **Stop ボタンが機能しない**。`onStop` が Composer に未接続 | `MarketingChat.tsx` | Easy | **確認済み: onStop 未渡し** |

### High

| # | 問題 | 難易度 |
|---|------|--------|
| U-3 | `_normalize_agent_name` が plugin と agent_service で **不一致** → 同一エージェントが別名表示（`zoho_crm` vs `zoho_c_r_m`） | Easy |
| U-4 | コードブロックに **コピーボタンなし** | Easy |
| U-5 | エラー表示が **技術的メッセージそのまま** + 再試行ボタンなし | Easy |
| U-6 | 会話削除に **確認ダイアログなし** | Easy |
| U-7 | **会話検索機能なし** | Medium |
| U-8 | ストリーミング中の **過剰再レンダリング**（`React.memo` 未適用） | Medium |

### Medium

| # | 問題 | 難易度 |
|---|------|--------|
| U-9 | `agent_updated` イベント未処理（エージェント切り替え表示なし） | Medium |
| U-10 | サブエージェント進捗ラベルが **偽データ**（固定テキストローテーション） | Medium |
| U-11 | `ask_user` 機能が **型定義のみで未実装** | Medium |
| U-12 | ActivityTimeline のソートが毎レンダリングで `useMemo` なし | Easy |
| U-13 | モバイルで改行ヒント（Shift+Enter）が非表示 | Easy |
| U-14 | サイドバーアクティブ状態がスレッドURLで失敗（`===` 判定） | Easy |

---

## IV. ADK インフラ改善

### Critical

| # | 問題 | 影響 |
|---|------|------|
| I-1 | `InMemorySessionService` — 再起動/スケーリングで **全セッション消失** | Cloud Run デプロイのたびにデータ喪失 |

### High

| # | 問題 | 工数 |
|---|------|------|
| I-2 | クライアント切断時に ADK Runner が **キャンセルされない**（リソースリーク） | M |
| I-3 | LLM per-call **タイムアウトなし**（Gemini API ハング時に無限待ち） | M |
| I-4 | Plugin `_current_agent_stack` が **並列実行で破壊される**（共有ミュータブル状態） | M |
| I-5 | 例外メッセージが **そのままユーザーに露出**（内部パスや API キー漏洩リスク） | S |
| I-6 | `on_model_error_callback` 未実装 → サブエージェントの **LLM エラーが UI に届かない** | S |

### Medium

| # | 問題 | 工数 |
|---|------|------|
| I-7 | `_normalize_agent_name` が **2箇所に重複定義**（agent_service + plugin） | S |
| I-8 | ツール `call_id` の追跡バグ（同名ツール連続呼び出し時に **衝突**） | S |
| I-9 | `asyncio.Queue` が **無制限**（メモリリスク） | S |
| I-10 | セッション有効期限 / **クリーンアップなし**（メモリ無限増加） | M |
| I-11 | `user_id` が `"default"` に **ハードコード** | S |
| I-12 | エージェントが **リクエストごとに全再構築** | M |

---

## V. 新規ツール提案

| # | ツール名 | 目的 | 配置先 | 優先度 |
|---|---------|------|--------|--------|
| N-1 | `compare_companies` | 2-5社を表形式で並列比較（年収・要件・訴求ポイント） | CompanyDB | High |
| N-2 | `get_candidate_summary` | Zoho+構造化データをワンショット取得（現在2回呼び出し必要） | CandidateInsight | High |
| N-3 | `search_candidates_advanced` | 構造化データの JSONB（転職理由・希望年収・希望時期）で検索 | CandidateInsight | High |
| N-4 | `compare_candidates` | 2-5人の候補者を表形式で並列比較 | CASupport | Medium |
| N-5 | `get_conversion_metrics` | 全チャネルの KPI を横断比較（現在1チャネルずつ） | ZohoCRM | Medium |
| N-6 | `get_company_match_explanation` | マッチング理由の詳細説明（候補者希望との対応関係を明示） | CompanyDB | Medium |

---

## 実装順序（推奨）

### Phase 1: 壊れているものを直す（即座に）
- T-1: `get_job_seekers_batch` のメソッド未実装
- T-2: Sheets キャッシュのシングルトン化
- T-3: Embedding `task_type` 追加
- U-1: ThinkingIndicator CSS 追加
- U-2: Stop ボタン接続
- U-3: `_normalize_agent_name` 統一

### Phase 2: ツール精度の底上げ（1-2日）
- T-4: CandidateInsight docstring 日本語化
- T-5: `get_job_seeker_detail` 整形
- T-8: `render_chart` を dict 型に
- T-9: `get_company_detail` の full_data 削除
- T-10: Zoho status フィールド統一
- T-15: 全ツールに Returns セクション追加
- O-12: 全エージェント `generate_content_config` 追加

### Phase 3: 指示文チューニング（1-2日）
- O-1〜O-3: CASupportAgent 境界問題
- O-4〜O-5: 思考プロセス + エラー対応テンプレート
- O-6: CandidateInsightAgent 指示強化
- O-7: チャート描画ガイダンス
- O-8〜O-9: セマンティック検索フォールバック + ワークフロー修正

### Phase 4: パフォーマンス改善（1-2日）
- T-11: ZohoClient シングルトン
- T-12: Embedding LRU キャッシュ
- T-13: Zoho `_fetch_all_records` TTL キャッシュ
- T-14: リトライデコレータ

### Phase 5: UX 機能追加（2-3日）
- U-4〜U-8: コピー、エラー改善、会話検索、パフォーマンス
- U-11: `ask_user` 実装

### Phase 6: 新ツール追加（2-3日）
- N-1〜N-3: compare_companies, get_candidate_summary, search_candidates_advanced

### Phase 7: インフラ安定化（要設計）
- I-1: セッション永続化
- I-2〜I-4: Runner キャンセル、タイムアウト、並列安全性
