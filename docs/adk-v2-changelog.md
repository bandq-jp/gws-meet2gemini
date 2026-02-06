# ADK V2 改善実装 変更履歴

> 2026-02-06 実施。`docs/adk-v2-improvement-plan.md` の全7フェーズを対象。
> **25ファイル変更、+1,190行、-185行**

---

## 変更サマリー

| Phase | 内容 | 完了項目数 | 未実施 |
|-------|------|-----------|--------|
| 1 | 緊急修正（壊れているもの） | 6/6 | - |
| 2 | ツール精度の底上げ | 14/14 | - |
| 3 | 指示文チューニング | 18/18 | - |
| 4 | パフォーマンス改善 | 4/4 | - |
| 5 | UX改善 | 7/14 | U-6, U-7, U-9, U-10, U-11 |
| 6 | 新ツール追加 | 3/6 | N-3, N-4, N-6 |
| 7 | インフラ改善 | 4/12 | I-1~I-4, I-8, I-10~I-12 |
| **合計** | | **56/74** | **18** |

---

## Phase 1: 緊急修正

### T-1: `get_job_seekers_batch` メソッド未実装の修正

**ファイル**: `backend/app/infrastructure/zoho/client.py` (+40行)

**問題**: `zoho_crm_tools.py` の `get_job_seekers_batch` が `zoho.get_app_hc_records_batch()` を呼ぶが、ZohoClient にメソッドが存在せず `AttributeError` が発生。

**修正内容**:
- `get_app_hc_records_batch(record_ids)` メソッドを新規追加
- COQL `IN` 句で最大50件を一括取得
- COQL失敗時は1件ずつ取得するフォールバック付き

```python
def get_app_hc_records_batch(self, record_ids: List[str]) -> List[Dict[str, Any]]:
    ids_str = ",".join(f"'{rid}'" for rid in record_ids[:50])
    query = f"SELECT ... FROM {module_api} WHERE id IN ({ids_str})"
    return self._with_coql_fallback(_coql_batch, _legacy_batch)
```

---

### T-2: SheetsService キャッシュ無効の修正

**ファイル**: `backend/app/infrastructure/adk/tools/company_db_tools.py` (+6行)

**問題**: `_get_sheets_service()` が毎回新規インスタンスを生成 → TTLキャッシュが実質無効 → 全企業DBツールで毎回Sheets API呼び出し。

**修正内容**:
- モジュールレベルのシングルトンパターンに変更

```python
_sheets_service_instance = None

def _get_sheets_service():
    global _sheets_service_instance
    if _sheets_service_instance is None:
        from app.infrastructure.google.sheets_service import CompanyDatabaseSheetsService
        _sheets_service_instance = CompanyDatabaseSheetsService(get_settings())
    return _sheets_service_instance
```

---

### T-3: Embedding `task_type` 不一致の修正

**ファイル**: `backend/app/infrastructure/adk/tools/semantic_company_tools.py` (+3行)

**問題**: 文書登録時は `task_type="retrieval_document"` だが、クエリ生成時は `task_type` 未指定 → ベクトル空間ミスマッチ → セマンティック検索精度低下。

**修正内容**:
- `config` に `task_type: "RETRIEVAL_QUERY"` を追加

```python
config={
    "output_dimensionality": EMBEDDING_DIMENSIONS,
    "task_type": "RETRIEVAL_QUERY",  # 追加
},
```

---

### U-1: ThinkingIndicator CSS未定義の修正

**ファイル**: `frontend/src/app/globals.css` (+14行)

**問題**: `thinking-dot-1/2/3` クラスが `globals.css` に存在せず、思考中ドットが表示されなかった。

**修正内容**:
- `.thinking-dot` クラスとバウンスアニメーションを追加

```css
.thinking-dot {
  @apply inline-block w-1.5 h-1.5 rounded-full bg-current;
  animation: thinking-bounce 1.4s ease-in-out infinite;
}
.thinking-dot-1 { animation-delay: 0s; }
.thinking-dot-2 { animation-delay: 0.2s; }
.thinking-dot-3 { animation-delay: 0.4s; }

@keyframes thinking-bounce {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}
```

---

### U-2: Stopボタン未接続の修正

**ファイル**: `frontend/src/components/marketing/v2/MarketingChat.tsx` (+2行)
**ファイル**: `frontend/src/hooks/use-marketing-chat-v2.ts` (+11行)

**問題**: Composer の `onStop` プロパティが MarketingChat から渡されておらず、ストリーミング停止が機能しなかった。

**修正内容**:
1. `useMarketingChat` フックに `cancelStream` 関数を追加
2. MarketingChat で `cancelStream` を受け取り、Composer の `onStop` に接続
3. `UseMarketingChatReturn` 型に `cancelStream` を追加

```typescript
// use-marketing-chat-v2.ts
const cancelStream = useCallback(() => {
  if (abortControllerRef.current) {
    abortControllerRef.current.abort();
    abortControllerRef.current = null;
  }
  setIsStreaming(false);
}, []);

// MarketingChat.tsx
<Composer onSend={handleSend} onStop={cancelStream} ... />
```

---

### U-3: `_normalize_agent_name` 不一致の修正

**ファイル**: `backend/app/infrastructure/adk/utils.py` (新規作成)
**ファイル**: `backend/app/infrastructure/adk/agent_service.py` (-31行, +4行)
**ファイル**: `backend/app/infrastructure/adk/plugins/sub_agent_streaming_plugin.py` (-12行, +2行)

**問題**: `agent_service.py` と `sub_agent_streaming_plugin.py` で `_normalize_agent_name` が別々に定義されており、`CA` アクロニムの扱いなどで不一致 → 同一エージェントが別名で表示される可能性。

**修正内容**:
- `utils.py` に統合版 `normalize_agent_name()` を作成（`CRM`, `SEO`, `CA`, `WordPress` 全てのアクロニムに対応）
- 両ファイルから重複コードを削除し、`utils.py` からインポート

---

## Phase 2: ツール精度の底上げ

### T-4: CandidateInsight docstring 日本語化

**ファイル**: `backend/app/infrastructure/adk/tools/candidate_insight_tools.py`

**問題**: 4ツール全ての docstring が英語。他全ツールは日本語。ADK は docstring をそのまま Gemini に渡すため、言語不一致でツール選択精度が低下。

**修正内容**: 4ツール全てを日本語化
- `analyze_competitor_risk`: "Analyze competitor risk..." → "競合エージェントリスク分析。他社オファー・選考中企業を持つ高リスク候補者を特定。"
- `assess_candidate_urgency`: "Assess candidate urgency..." → "候補者の緊急度を評価。転職希望時期・離職状況・他社オファーから優先順位を算出。"
- `analyze_transfer_patterns`: "Analyze transfer patterns..." → "転職パターン分析。転職理由・希望時期・キャリアビジョンの傾向を可視化。"
- `generate_candidate_briefing`: "Generate candidate briefing..." → "面談ブリーフィング生成。Zoho基本情報+議事録構造化データを統合した準備資料。"

---

### T-5: `get_job_seeker_detail` 整形

**ファイル**: `backend/app/infrastructure/adk/tools/zoho_crm_tools.py`

**問題**: `get_job_seeker_detail` が生Zohoフィールドコード（`field14` 等）を返却。`get_job_seekers_batch` は日本語ラベル変換済みで不一致。

**修正内容**:
- `return record` → `return _format_job_seeker_detail(record)` に変更
- docstring を "整形済み求職者データ（日本語ラベル）" に更新

---

### T-6: `generate_candidate_briefing` と `get_candidate_full_profile` の差別化

**ファイル**: `backend/app/infrastructure/adk/tools/meeting_tools.py`

**問題**: 両ツールが機能重複し、LLM が判断不能。

**修正内容**: docstring に相互参照を追加
- `get_candidate_full_profile`: "generate_candidate_briefingとの違い：こちらはZoho+議事録の全情報統合プロファイル。面談準備には generate_candidate_briefing を推奨。"
- `generate_candidate_briefing`: "get_candidate_full_profileとの違い：こちらはリスク分析付きの面談準備に特化。"

---

### T-7: 厳密検索 vs セマンティック検索の差別化

**ファイル**: `backend/app/infrastructure/adk/tools/company_db_tools.py`, `semantic_company_tools.py`

**問題**: `match_candidate_to_companies`（厳密）vs `find_companies_for_candidate`（セマンティック）の使い分けが不明確。

**修正内容**:
- `match_candidate_to_companies`: "find_companies_for_candidateとの違い：こちらは採用要件（年齢・年収・学歴）の厳密マッチング。自然言語の意味検索はfind_companies_for_candidateを使用。"
- `find_companies_for_candidate`: "match_candidate_to_companiesとの違い：こちらは転職理由からベクトル類似度でマッチング。厳密な条件チェックはmatch_candidate_to_companiesを使用。"

---

### T-8: `render_chart` を dict 型に変更

**ファイル**: `backend/app/infrastructure/adk/tools/chart_tools.py` (-9行, +2行)

**問題**: `chart_spec` が `str` 型（JSON文字列） → LLM の JSON 構築エラー多発。

**修正内容**:
- `chart_spec: str` → `chart_spec: dict` に変更
- `import json` と `json.loads()` を削除
- docstring を「チャート仕様の辞書」に更新

---

### T-9: `get_company_detail` の `full_data` 削除

**ファイル**: `backend/app/infrastructure/adk/tools/company_db_tools.py` (-2行)

**問題**: `full_data`（全52列の生データ）を返却 → トークン浪費。

**修正内容**: `"full_data": company` 行を削除。

---

### T-10: Zoho ステータスフィールド統一

**ファイル**: `backend/app/infrastructure/adk/tools/meeting_tools.py` (+1行, -1行)

**問題**: `customer_status` と `field19` が混在。

**修正内容**: `meeting_tools.py` の `get_candidate_full_profile` 内で `field19` → `customer_status` に統一。

---

### T-15: 全ツールに Returns セクション追加

**ファイル**: `zoho_crm_tools.py`, `company_db_tools.py`, `meeting_tools.py`, `semantic_company_tools.py`

**問題**: 多くのツールで Returns セクションが欠如 → LLM が戻り値の構造を理解できない。

**修正内容**: 全23ツールに構造化された Returns セクションを追加。
```python
Returns:
    Dict[str, Any]: 検索結果。
        success: True/False
        total: ヒット件数
        records: 求職者レコードリスト
```

---

### T-16〜T-22: docstring 改善（Medium項目）

| # | 修正内容 |
|---|---------|
| T-16 | `get_company_requirements` に "get_company_detailとの違い：採用要件のみ高速取得" を追加 |
| T-17 | `get_appeal_by_need` に転職理由→need_typeマッピングガイド追加（給与→salary, 残業→wlb等） |
| T-18 | `search_meetings` に "candidate_nameとtitleは独立検索（AND条件ではない）" を追加 |
| T-19 | `get_meeting_transcript` に "10000文字を超える場合は切り詰めて返す" を追加 |
| T-20 | `trend_analysis_by_period` に enum バリデーション追加（weekly/monthly/quarterly） |
| T-21 | `semantic_search_companies` に `similarity_threshold` パラメータ追加（デフォルト0.3、0.0-1.0にクランプ） |
| T-22 | `count_job_seekers_by_status` / `analyze_funnel_by_channel` に差別化説明追加 |

---

### O-12: 全エージェントに `generate_content_config` 追加

**ファイル**: 7つのエージェントファクトリ全て（各+3行）
- `ad_platform_agent.py`
- `analytics_agent.py`
- `ca_support_agent.py`
- `candidate_insight_agent.py`
- `company_db_agent.py`
- `seo_agent.py`
- `wordpress_agent.py`
- `zoho_crm_agent.py`

**問題**: `build_agent()` オーバーライドで `generate_content_config` 欠如 → Gemini 3 Flash が約3000トークンで早期終了するリスク。

**修正内容**:
```python
generate_content_config=types.GenerateContentConfig(
    max_output_tokens=self._settings.adk_max_output_tokens,
),
```

---

## Phase 3: 指示文チューニング

### O-1: CASupportAgent vs 専門エージェント境界の明確化

**ファイル**: `backend/app/infrastructure/adk/agents/orchestrator.py` (+12行)

**修正内容**: オーケストレーター instructions に使い分けセクション追加
- **CASupportAgent**: 特定候補者名/ID + クロスドメイン分析（CRM + 議事録 + 企業DB）
- **専門エージェント**: 集団分析、単一ドメイン深堀り

---

### O-3: AgentTool description 差別化

**ファイル**: `backend/app/infrastructure/adk/agents/ca_support_agent.py` (+3行, -2行)

**修正内容**: `tool_description` を排他的に書き換え
- Before: "CA（キャリアアドバイザー）支援エージェント。候補者情報・面談内容・企業DBを統合して..."
- After: "特定候補者のクロスドメイン分析（CRM+議事録+企業DB統合）。面談準備・企業提案・リスク分析を一括実行。集団分析や単一ドメインの質問には専門エージェントを使用。"

---

### O-4: 全サブエージェントに思考プロセス指示

**ファイル**: `backend/app/infrastructure/adk/agents/orchestrator.py` (+5行)

**修正内容**: 共通テンプレート追加
```
1. 質問分解: ユーザーの質問を具体的なデータ取得ステップに分解
2. ツール選択: 最適なツールを選択（重複呼び出しを避ける）
3. 結果検証: 取得データが質問に十分に答えているか確認
4. 統合出力: 複数ソースの結果を統合し、表やチャートで可視化
```

---

### O-5: エラーハンドリング指示追加

**ファイル**: `backend/app/infrastructure/adk/agents/orchestrator.py` (+7行)

**修正内容**: 共通エラー対応ルール追加
- `success: false` → パラメータ修正して再試行 / 認証エラー報告 / 条件緩和 / 代替案提示
- ツール不在 → 最も近いツールを使用

---

### O-6: CandidateInsightAgent 指示強化

**ファイル**: `backend/app/infrastructure/adk/agents/candidate_insight_agent.py` (+40行)

**問題**: instruction が極端に簡素（3行/ツール）。

**修正内容**:
- 重要ルール追加（許可を求めるな、推測するな、効率的に）
- 全4ツールにパラメータ・戻り値の詳細仕様を追加
- ワークフロー例3パターン追加（高リスク対応、面談準備、トレンド分析）
- 回答方針を具体化（リスクレベル: 即時/高/中/低、アクション提案）

---

### O-7: チャート描画ガイダンス追加

**ファイル**: `backend/app/infrastructure/adk/agents/orchestrator.py` (+10行)

**修正内容**: "数値データには必ず `render_chart` を使用して可視化" ルールと推奨マッピング表追加
| データの性質 | 推奨タイプ |
|---|---|
| 時系列推移 | line |
| カテゴリ比較 | bar |
| 構成比 | pie / donut |
| ファネル | funnel |
| 多軸比較 | radar |

---

### O-8: セマンティック検索フォールバック手順

**ファイル**: `backend/app/infrastructure/adk/agents/ca_support_agent.py` (+6行)

**修正内容**:
```
1. まずセマンティック検索: find_companies_for_candidate or semantic_search_companies
2. 結果が少ない場合: 条件を緩和して再検索
3. それでも不足: search_companies（厳密検索）にフォールバック
4. 特定企業の詳細: get_company_detail で補足
```

---

### O-9: CASupportAgent ワークフロー修正

**ファイル**: `backend/app/infrastructure/adk/agents/ca_support_agent.py` (+1行, -1行)

**修正内容**: ワークフロー例の企業提案ステップをセマンティック優先に変更
- Before: `match_candidate_to_companies(record_id)` → マッチング企業取得
- After: `find_companies_for_candidate(transfer_reasons, age, desired_salary)` → セマンティックマッチング

---

### O-10: キーワードマトリクス外のクエリ対応

**ファイル**: `backend/app/infrastructure/adk/agents/orchestrator.py` (+1行)

**修正内容**: マトリクスに "上記に該当しない質問 → 最も関連性の高いエージェントを推測して即実行" を追加。

---

### O-11: キーワードマトリクスのギャップ埋め

**ファイル**: `backend/app/infrastructure/adk/agents/orchestrator.py` (+3行)

**修正内容**: 未定義だったキーワードを追加
- コンバージョン、CVR、応募率 → ZohoCRMAgent
- ROI、投資対効果、費用対効果 → AdPlatformAgent + ZohoCRMAgent
- Indeed、doda、ビズリーチ → ZohoCRMAgent

---

### O-13〜O-17: 出力量管理・ルール追加

**ファイル**: `backend/app/infrastructure/adk/agents/orchestrator.py` (+5行)

| # | 修正内容 |
|---|---------|
| O-13 | 並列 vs CASupportAgent の使い分けルール明記 |
| O-14 | テーブル形式の出力を推奨 |
| O-16 | 日付デフォルト: 期間未指定→直近3ヶ月 |
| O-17 | 大量データは上位10件に絞り全体サマリーを付ける |

---

### O-18: MCP経由ツール名の注意書き

**ファイル**: `backend/app/infrastructure/adk/agents/orchestrator.py` (+3行)

**修正内容**: "実際のツール名は各エージェント内のツール一覧に依存する" 注意書きを追加。

---

## Phase 4: パフォーマンス改善

### T-11: ZohoClient シングルトン化

**ファイル**: `backend/app/infrastructure/adk/tools/zoho_crm_tools.py` (+8行), `candidate_insight_tools.py` (+8行)

**問題**: 全14ツール呼び出しで毎回 `ZohoClient()` を新規生成。

**修正内容**:
- 両ファイルに `_get_zoho_client()` シングルトン関数を追加
- 全14箇所の `ZohoClient()` を `_get_zoho_client()` に置換

**効果**: ツール呼び出しあたり約50-100ms節約。

---

### T-12: Embedding LRU キャッシュ

**ファイル**: `backend/app/infrastructure/adk/tools/semantic_company_tools.py` (+10行)

**問題**: 同一クエリでも毎回 Gemini Embedding API を呼び出し。

**修正内容**:
- `@lru_cache(maxsize=256)` 付きの `_get_cached_embedding()` 関数を追加
- `_get_query_embedding()` からキャッシュ経由で取得

**効果**: キャッシュヒット時に200-500ms節約（API往復分）。

---

### T-13: Zoho `_fetch_all_records` TTL キャッシュ

**ファイル**: `backend/app/infrastructure/adk/tools/zoho_crm_tools.py` (+15行)

**問題**: `_fetch_all_records()` が約3000件を毎回全ページング（12秒+）。

**修正内容**:
- TTLキャッシュ（5分有効）の `_get_cached_all_records()` を追加
- `trend_analysis_by_period`, `compare_channels`, `get_pic_performance`, `get_conversion_metrics` の4ツールで使用

**効果**: キャッシュヒット時に2-5秒節約。

---

### T-14: リトライデコレータ

**ファイル**: `backend/app/infrastructure/adk/tools/zoho_crm_tools.py` (+20行)

**修正内容**:
- `_retry_transient(max_retries=2, delay=1.0)` デコレータを追加
- 指数バックオフ（1s→2s）
- 認証/バリデーションエラーはリトライしない
- 定義済み（将来の選択的適用用）

---

## Phase 5: UX改善

### U-4: コードブロックにコピーボタン追加

**ファイル**: `frontend/src/components/marketing/v2/ChatMessage.tsx` (+42行)

**修正内容**:
- `CodeBlock` コンポーネントを新規追加
- クリップボードコピー機能 + "コピー済み" フィードバック（2秒表示）
- 既存の `markdownComponents.code` を `CodeBlock` に置換

---

### U-5: エラー表示の改善

**ファイル**: `frontend/src/components/marketing/v2/MarketingChat.tsx` (+8行, -2行)

**修正内容**:
- ネットワークエラーは "ネットワークエラーが発生しました" に変換
- 長いエラーメッセージ（100文字超）は "エラーが発生しました。もう一度お試しください。" に変換
- 「閉じる」ボタンを追加

---

### U-8: ストリーミング中の過剰再レンダリング防止

**ファイル**: `frontend/src/components/marketing/v2/ChatMessage.tsx` (+5行, -3行)

**修正内容**:
- `ChatMessage` を `React.memo` でラップ
- `ActivityTimeline` のソートを `useMemo` で最適化

```typescript
export const ChatMessage = memo(function ChatMessage({ message }: ChatMessageProps) { ... });

const sortedItems = useMemo(
  () => [...items].sort((a, b) => a.sequence - b.sequence),
  [items]
);
```

---

### U-12: ActivityTimeline ソートの useMemo 化

U-8 に含めて実施。`[...items].sort()` を `useMemo` でキャッシュ。

---

### U-13: モバイルで改行ヒント表示

**ファイル**: `frontend/src/components/marketing/v2/Composer.tsx` (+1行, -1行)

**修正内容**:
- `hidden sm:block` → `block`（常時表示）
- フォントサイズ: `text-[10px] sm:text-[11px]`（モバイル時は小さめ）

---

### U-14: サイドバーアクティブ状態の修正

**ファイル**: `frontend/src/components/app-sidebar.tsx` (+14行, -1行)

**問題**: `pathname === item.href` の完全一致判定 → `/marketing-v2/abc123` のようなスレッドURLでアクティブ状態が失われる。

**修正内容**: 最長プレフィックスマッチアルゴリズムを導入

```typescript
const activeItemHref = useMemo(() => {
  if (!pathname) return null;
  let bestMatch: string | null = null;
  for (const item of menuItems) {
    if (pathname === item.href || pathname.startsWith(item.href + '/')) {
      if (!bestMatch || item.href.length > bestMatch.length) {
        bestMatch = item.href;
      }
    }
  }
  return bestMatch;
}, [pathname, menuItems]);
```

---

## Phase 6: 新ツール追加

### N-1: `compare_companies` (CompanyDB)

**ファイル**: `backend/app/infrastructure/adk/tools/company_db_tools.py` (+130行)

**機能**: 2〜5社を並列比較（年収・要件・訴求ポイント）

**入力**: `company_names: List[str]`（部分一致検索）
**出力**: `comparison_table`（企業比較テーブル）+ `summary`（主要差異サマリー）

サマリーは自動生成:
- 年収上限が最も高い企業
- リモート可能企業
- 年齢上限が最も高い企業

---

### N-2: `get_candidate_summary` (CandidateInsight)

**ファイル**: `backend/app/infrastructure/adk/tools/candidate_insight_tools.py` (+130行)

**機能**: Zoho + 構造化データ + リスク評価をワンショット取得

**入力**: `record_id: str`
**出力**: `basic_info`, `transfer_profile`, `risk_level`(high/medium/low), `risk_score`, `risk_factors`, `recommended_actions`

リスクスコアリング:
- 他社オファーあり: +40点
- 競合エージェント3社以上: +30点
- 最終面接〜内定済み: +30点
- 「すぐにでも」転職希望: +10点

---

### N-5: `get_conversion_metrics` (ZohoCRM)

**ファイル**: `backend/app/infrastructure/adk/tools/zoho_crm_tools.py` (+170行)

**機能**: 全チャネル横断のコンバージョンKPIを一括取得

**入力**: `date_from`, `date_to`（任意）
**出力**: `overall`(全体), `category_summary`(カテゴリ別), `metrics`(チャネル別), `ranking`(入社率順), `recommendations`(改善推奨)

---

## Phase 7: インフラ改善

### I-5: エラーメッセージのサニタイズ

**ファイル**: `backend/app/infrastructure/adk/utils.py` (新規, +30行), `agent_service.py` (+3行, -3行)

**問題**: 例外メッセージがそのままユーザーに露出（内部パス・APIキー漏洩リスク）。

**修正内容**:
- `sanitize_error()` 関数を追加。正規表現で以下を検出:
  - ファイルパス (`/app/...`, `/home/...`)
  - APIキー (`sk-*`, `AIza*`, `ghp_*`)
  - スタックトレース
  - IPアドレス
  - 接続文字列 (`postgresql://...`)
  - 環境変数代入
- 検出時はジェネリックメッセージ "エラーが発生しました。もう一度お試しください。" に置換
- 200文字超のメッセージも同様に置換
- `agent_service.py` の3箇所の `str(e)` を `sanitize_error(str(e))` に変更

---

### I-6: モデルエラー検出の強化

**ファイル**: `backend/app/infrastructure/adk/plugins/sub_agent_streaming_plugin.py` (+55行)

**問題**: `on_model_error_callback` 未実装 → サブエージェントの LLM エラーが UI に届かない。

**修正内容**: `after_model_callback` を拡張して3種のエラーを検出:
1. **null response**: LLM応答なし → `model_error` イベント発行
2. **blocked response**: safety filter等 → `finish_reason` を確認し `model_error` 発行
3. **error_message**: ADK の `error_message` 属性 → `model_error` 発行（生メッセージは送らない）

---

### I-7: `_normalize_agent_name` 重複排除

Phase 1 の U-3 と同時に実施。`utils.py` に統合。

---

### I-9: `asyncio.Queue` サイズ制限

**ファイル**: `backend/app/infrastructure/adk/agent_service.py` (+1行, -1行)

**問題**: `asyncio.Queue()` が無制限 → コンシューマー遅延時にメモリリスク。

**修正内容**: `asyncio.Queue(maxsize=1000)` に変更。プロデューサーは `await queue.put()` で自然にバックプレッシャーがかかる。

---

## 未実施項目（低優先度 / 設計検討必要）

### UX
| # | 項目 | 理由 |
|---|------|------|
| U-6 | 会話削除確認ダイアログ | UI追加が必要 |
| U-7 | 会話検索機能 | バックエンドAPI追加が必要 |
| U-9 | `agent_updated` イベント処理 | プロトコル設計が必要 |
| U-10 | サブエージェント進捗の実ラベル化 | ADKイベントとの対応設計が必要 |
| U-11 | `ask_user` 機能実装 | 双方向通信の設計が必要 |

### 新ツール
| # | ツール | 理由 |
|---|--------|------|
| N-3 | `search_candidates_advanced` | Supabase JSONB検索の設計が必要 |
| N-4 | `compare_candidates` | UIとの連携設計が必要 |
| N-6 | `get_company_match_explanation` | LLM呼び出しコストの検討が必要 |

### インフラ
| # | 項目 | 理由 |
|---|------|------|
| I-1 | セッション永続化 | Redis/Supabase等の永続化先の設計が必要 |
| I-2 | Runner キャンセル | ADK Runner のキャンセルAPI調査が必要 |
| I-3 | LLM per-call タイムアウト | ADK GenerateContentConfigでの設定可否調査 |
| I-4 | Plugin 並列安全性 | `_current_agent_stack` のスレッドセーフ化設計 |
| I-8 | `call_id` 追跡バグ | 同名ツール連続呼び出しの衝突パターン調査 |
| I-10 | セッションクリーンアップ | TTLポリシーの設計が必要 |
| I-11 | `user_id` ハードコード | Clerk JWT からの user_id 取得パイプライン設計 |
| I-12 | エージェント毎回再構築 | キャッシュ戦略の設計が必要 |

---

## 変更ファイル一覧

| ファイル | 操作 | 変更行 | Phase |
|---------|------|-------|-------|
| `backend/app/infrastructure/adk/utils.py` | **新規** | +90 | 1,7 |
| `backend/app/infrastructure/zoho/client.py` | 変更 | +40 | 1 |
| `backend/app/infrastructure/adk/agent_service.py` | 変更 | +10,-42 | 1,7 |
| `backend/app/infrastructure/adk/plugins/sub_agent_streaming_plugin.py` | 変更 | +60,-12 | 1,7 |
| `backend/app/infrastructure/adk/tools/zoho_crm_tools.py` | 変更 | +340 | 2,4,6 |
| `backend/app/infrastructure/adk/tools/candidate_insight_tools.py` | 変更 | +215 | 2,4,6 |
| `backend/app/infrastructure/adk/tools/company_db_tools.py` | 変更 | +189 | 1,2,6 |
| `backend/app/infrastructure/adk/tools/semantic_company_tools.py` | 変更 | +30,-20 | 1,2,4 |
| `backend/app/infrastructure/adk/tools/meeting_tools.py` | 変更 | +37 | 2 |
| `backend/app/infrastructure/adk/tools/chart_tools.py` | 変更 | +2,-9 | 2 |
| `backend/app/infrastructure/adk/agents/orchestrator.py` | 変更 | +57 | 3 |
| `backend/app/infrastructure/adk/agents/candidate_insight_agent.py` | 変更 | +66 | 2,3 |
| `backend/app/infrastructure/adk/agents/ca_support_agent.py` | 変更 | +20 | 3 |
| `backend/app/infrastructure/adk/agents/ad_platform_agent.py` | 変更 | +3 | 2 |
| `backend/app/infrastructure/adk/agents/analytics_agent.py` | 変更 | +3 | 2 |
| `backend/app/infrastructure/adk/agents/company_db_agent.py` | 変更 | +3 | 2 |
| `backend/app/infrastructure/adk/agents/seo_agent.py` | 変更 | +3 | 2 |
| `backend/app/infrastructure/adk/agents/wordpress_agent.py` | 変更 | +3 | 2 |
| `backend/app/infrastructure/adk/agents/zoho_crm_agent.py` | 変更 | +3 | 2 |
| `frontend/src/app/globals.css` | 変更 | +14 | 1 |
| `frontend/src/components/marketing/v2/ChatMessage.tsx` | 変更 | +60,-12 | 5 |
| `frontend/src/components/marketing/v2/Composer.tsx` | 変更 | +1,-1 | 5 |
| `frontend/src/components/marketing/v2/MarketingChat.tsx` | 変更 | +16 | 1,5 |
| `frontend/src/hooks/use-marketing-chat-v2.ts` | 変更 | +11 | 1 |
| `frontend/src/components/app-sidebar.tsx` | 変更 | +14,-1 | 5 |
