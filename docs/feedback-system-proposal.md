# b&q Agent Feedback & Annotation System 設計提案書

> **目的**: b&qエージェントの品質改善のための、社員向けフィードバック収集 + 管理者向けレビュー + エクスポートシステム
> **作成日**: 2026-02-07
> **ステータス**: 提案（未実装）

---

## 1. システム全体像

```
┌─────────────────────────────────────────────────────────────────────┐
│                    b&q Agent Chat Page (/marketing-v2)              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────────────────────────────────┐ │
│  │              │  │  通常モード                                   │ │
│  │  Message     │  │  ┌─────┐ ┌─────┐                             │ │
│  │  List        │  │  │ 👍  │ │ 👎  │  ← メッセージごとに表示    │ │
│  │              │  │  └─────┘ └─────┘                             │ │
│  │              │  ├──────────────────────────────────────────────┤ │
│  │              │  │  FBモード (トグルで切替)                     │ │
│  │              │  │  ┌──────────────────────────┐                │ │
│  │              │  │  │ テキスト選択 → コメント  │                │ │
│  │              │  │  │ ツール選択 → 評価        │                │ │
│  │              │  │  │ 多次元レーティング        │                │ │
│  │              │  │  │ タグ付け                  │                │ │
│  │              │  │  │ 修正案入力                │                │ │
│  │              │  │  └──────────────────────────┘                │ │
│  └──────────────┘  └──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Feedback Review Page (/feedback)                    │
│                                                                     │
│  ┌────────────────────┐  ┌──────────────────────────────────────┐  │
│  │ フィルタ・集計      │  │ チャット再現ビュー                   │  │
│  │ ・日別トレンド      │  │ ・実際のチャット画面を再現           │  │
│  │ ・タグ別集計        │  │ ・アノテーション箇所をハイライト     │  │
│  │ ・ツール別問題      │  │ ・コメント表示                       │  │
│  │ ・レビューキュー    │  │ ・レビューステータス更新             │  │
│  └────────────────────┘  └──────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ エクスポート: JSONL / CSV / HTML（アノテーション付き）        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. UX設計

### 2.1 通常モード（常時表示）

各アシスタントメッセージの下部に、最小限のフィードバックUI:

```
┌─────────────────────────────────────────────────┐
│ [Assistant Message Content]                      │
│ ...                                              │
│                                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │  👍  👎  │  📝 詳細FB  │  ← hover時に表示   │ │
│ └──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**👍 クリック時**: 即座に保存。オプションでポップオーバー展開:
- 「何が良かった？」タグ選択（優れた洞察 / 適切なツール活用 / 包括的 / 実用的）
- 一行コメント入力欄

**👎 クリック時**: ポップオーバー展開（必須）:
- 「何が問題？」タグ選択（ハルシネーション / ツール選択ミス / 回答不完全 / データエラー / 冗長 / フォーマット不適切）
- コメント入力欄
- 修正案入力欄（任意）

**デザイン参考**: ChatGPTの👎→カテゴリ選択モーダル + Braintrustのキーボードショートカット

### 2.2 FBモード（詳細アノテーション）

ヘッダーにトグルボタンを配置。ONにすると、チャット画面がアノテーションモードに:

```
┌─────────────────────────────────────────────────────────┐
│  b&q エージェント   [通常モード ○ | ● FBモード]  [Export]│
├─────────────────────────────────────────────────────────┤
│                                                         │
│  User: 「MyVisionの企業情報を教えて」                    │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Assistant:                                         │  │
│  │                                                    │  │
│  │  ▶ CompanyDatabaseAgent  ✓ 3ツール実行             │  │
│  │    ├ search_companies "MyVision" ✓     [📝]       │  │
│  │    ├ get_company_detail ✓              [📝]       │  │
│  │    └ get_appeal_points ✓               [📝]       │  │
│  │                                                    │  │
│  │  ████████████████████████████████████████████████  │  │
│  │  │MyVisionは人材紹介会社で、│主にIT/コンサル領    │  │
│  │  │域を中心に...            │← テキスト選択で     │  │
│  │  │                         │  ポップオーバー表示  │  │
│  │  ████████████████████████████████████████████████  │  │
│  │                                                    │  │
│  │  ┌── 多次元評価 ─────────────────────────────┐    │  │
│  │  │ 正確性:     ★★★★☆                        │    │  │
│  │  │ 関連性:     ★★★★★                        │    │  │
│  │  │ 完全性:     ★★★☆☆                        │    │  │
│  │  │ ツール活用: ★★★★★                        │    │  │
│  │  │ 有用性:     ★★★★☆                        │    │  │
│  │  └─────────────────────────────────────────────┘   │  │
│  │                                                    │  │
│  │  タグ: [ハルシネーション] [+追加]                   │  │
│  │  コメント: [________________]                      │  │
│  │                                                    │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### テキスト選択アノテーション

FBモードでテキストを選択すると、ポップオーバーが表示:

```
              ┌────────────────────────────────────┐
              │ この部分について                     │
              │ ┌──────────────────────────────────┐│
              │ │コメント:                          ││
              │ │[この数値は実際と異なる。正しくは  ]││
              │ │[年収上限は800万円ではなく900万円   ]││
              │ └──────────────────────────────────┘│
              │                                      │
              │ 深刻度: ⚠ 重大  ○ 軽微  ○ 情報     │
              │                                      │
              │ タグ: [ハルシネーション ×] [+]        │
              │                                      │
              │ 修正案:                               │
              │ [年収上限は900万円（2026年度実績）  ] │
              │                                      │
              │         [キャンセル] [保存]            │
              └────────────────────────────────────┘
```

#### ツール/サブエージェント アノテーション

各ツール実行バッジの横にある `[📝]` をクリックすると:

```
┌────────────────────────────────────────┐
│ search_companies "MyVision"            │
│                                        │
│ ツール選択: ○ 適切  ● 不適切          │
│ 引数:       ● 適切  ○ 不適切          │
│ 結果:       ● 正確  ○ 不正確          │
│                                        │
│ コメント:                              │
│ [semantic_searchを使うべきだった      ] │
│                                        │
│         [キャンセル] [保存]            │
└────────────────────────────────────────┘
```

### 2.3 テキスト選択のアンカリング戦略

**推奨方式: W3C Web Annotation Model (Hypothesis方式)**

レンダリング済みMarkdown内のテキスト選択を、2つのセレクタで永続化:

```typescript
interface TextSpanSelector {
  type: "text_span";
  // 位置ベース（高速・正確だが脆い）
  position: { start: number; end: number };
  // 引用ベース（位置ずれに強い）
  quote: {
    prefix: string;  // 選択箇所の直前20文字
    exact: string;   // 選択テキスト
    suffix: string;  // 選択箇所の直後20文字
  };
}
```

**実装アプローチ**:
1. `window.getSelection()` で選択範囲を取得
2. メッセージのプレーンテキスト（`plain_text`フィールド）内での位置を計算
3. `position` + `quote` の両方を保存
4. 再表示時: `position`で高速マッチ → 失敗時は`quote`でファジーマッチ
5. メッセージの`content_hash`が変わった場合、`is_stale`フラグを立てる

**ライブラリ不使用**: 既存のshadcn/ui Popoverで十分。外部ライブラリ（react-highlight-menu等）は星数が少なく保守リスクが高い。

### 2.4 暗黙的フィードバック（将来拡張）

明示的フィードバックに加え、以下のシグナルも収集可能:
- **コピー操作**: ユーザーがレスポンスをコピーした = 有用性のシグナル
- **再生成**: 同じ質問の再送信 = 不満足のシグナル
- **滞在時間**: メッセージの読了時間
- **後続質問**: フォローアップの有無（完全性のシグナル）

---

## 3. Feedback Review Page (`/feedback`)

### 3.1 ページ構成

```
/feedback
├── 概要ダッシュボード（KPIカード + トレンド）
├── フィードバック一覧（テーブル + フィルタ）
├── チャット再現ビュー（Sheet/Modal）
└── エクスポート機能
```

### 3.2 概要ダッシュボード

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Total FB │ │  Good %  │ │  Bad %   │ │ 未レビュー│
│   142    │ │  68.3%   │ │  31.7%   │ │    23    │
└──────────┘ └──────────┘ └──────────┘ └──────────┘

┌────────────────────────────────────────────────────┐
│ 日別トレンド (recharts AreaChart)                   │
│ ▬ Good  ▬ Bad                                      │
│ ┌──────────────────────────────────────────────┐   │
│ │    ╱‾‾╲                                      │   │
│ │   ╱    ╲___╱‾‾‾‾╲                            │   │
│ │  ╱                ╲___                        │   │
│ └──────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘

┌────────────────────────┐ ┌────────────────────────┐
│ タグ別問題頻度          │ │ ツール別問題            │
│ (recharts BarChart)     │ │ (recharts BarChart)     │
│                         │ │                         │
│ ハルシネーション ████ 12│ │ search_companies ██ 8   │
│ ツール選択ミス  ███  9 │ │ get_module_schema █ 5   │
│ 回答不完全     ██   6 │ │ query_crm_records █ 4   │
│ データエラー   █    3 │ │                         │
└────────────────────────┘ └────────────────────────┘
```

### 3.3 フィードバック一覧テーブル

```
┌────────────────────────────────────────────────────────────────────┐
│ フィルタ: [期間 ▼] [評価 ▼] [タグ ▼] [ステータス ▼] [検索...]   │
├──────┬──────────┬────────┬──────────┬──────────┬────────┬────────┤
│ 評価 │ 日時     │ ユーザ │ メッセージ│ タグ     │ステータス│ 操作 │
├──────┼──────────┼────────┼──────────┼──────────┼────────┼────────┤
│  👎  │ 02/07    │ sato@  │ MyVision │ ハルシ   │ 🟡 新規│ [詳細]│
│      │ 14:30    │        │ の企業... │ ネーション│        │       │
├──────┼──────────┼────────┼──────────┼──────────┼────────┼────────┤
│  👍  │ 02/07    │ tanaka@│ GA4の    │ 優れた   │ ✅ 済  │ [詳細]│
│      │ 13:15    │        │ 分析結果 │ 洞察     │        │       │
├──────┼──────────┼────────┼──────────┼──────────┼────────┼────────┤
│  👎  │ 02/06    │ yamada@│ 候補者   │ ツール   │ 🔵 対応│ [詳細]│
│      │ 16:45    │        │ のリスク │ 選択ミス │  済    │       │
└──────┴──────────┴────────┴──────────┴──────────┴────────┴────────┘
                                            [前へ] 1/5 [次へ]
```

### 3.4 チャット再現ビュー（Sheet）

テーブルの「詳細」をクリックすると、右からSheetが開く:

```
┌──────────────────────────────────────────────────────────┐
│ ← 戻る   会話詳細   [レビュー済み ▼] [エクスポート]      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  User: 「MyVisionの企業情報を教えて」                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Assistant:                                          │  │
│  │                                                     │  │
│  │  ▶ CompanyDatabaseAgent ✓                           │  │
│  │                                                     │  │
│  │  MyVisionは人材紹介会社で、主にIT/コンサル領域      │  │
│  │  を中心に████████████████████████████              │  │
│  │  ← ハイライト箇所（黄色背景）                       │  │
│  │                                                     │  │
│  │  年収上限は800万円程度です。                         │  │
│  │  ← ハイライト箇所（赤背景 = critical）              │  │
│  │                                                     │  │
│  │  ┌─ アノテーション ─────────────────────────────┐   │  │
│  │  │ 📍 "年収上限は800万円"                       │   │  │
│  │  │ 🏷 ハルシネーション | ⚠ 重大                 │   │  │
│  │  │ 💬 正しくは900万円。Sheetsの最新データと不一致│   │  │
│  │  │ ✏️ 修正案: 「年収上限は900万円（2026年度）」  │   │  │
│  │  │                                              │   │  │
│  │  │ ステータス: [新規 ▼]                          │   │  │
│  │  │ レビューメモ: [________________]              │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  │                                                     │  │
│  │  ── メッセージ評価 ──                               │  │
│  │  評価: 👎  タグ: [ハルシネーション]                  │  │
│  │  コメント: 「年収データが古い」                      │  │
│  │  多次元: 正確性 2/5, 関連性 4/5, 完全性 3/5         │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  User: 「他の類似企業も教えて」                           │
│  ...                                                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**ポイント**:
- 実際のチャットUIと**ほぼ同じレンダリング**（ChatMessage.tsxのコンポーネントを再利用）
- アノテーション箇所がハイライトされ、横にコメントが表示
- レビュー担当がステータスを更新できる
- 会話全体の文脈を見ながらレビューできる

### 3.5 レビューワークフロー

```
🟡 新規 (new)
   │
   ▼ レビュー担当がレビュー
🔵 レビュー済み (reviewed)
   │
   ├─▶ 対応済み (actioned) ← 改善を実施
   │
   └─▶ 却下 (dismissed) ← 対応不要と判断
```

---

## 4. データベーススキーマ

### 4.1 テーブル設計

既存の`marketing_messages`/`marketing_conversations`テーブルとの関係:

```
marketing_conversations (既存)
  │ 1:N
  ▼
marketing_messages (既存)
  │ 1:1                    1:N
  ├──────────────────┐ ┌──────────────────┐
  ▼                  ▼ ▼                  │
message_feedback     message_annotations  │
(メッセージ単位)     (セグメント単位)     │
                                          │
feedback_dimensions ◄─────────────────────┘
(評価軸マスタ)       参照

feedback_tags
(タグマスタ)         参照
```

### 4.2 message_feedback（メッセージ単位フィードバック）

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | UUID PK | フィードバックID |
| `message_id` | TEXT FK → marketing_messages | 対象メッセージ |
| `conversation_id` | TEXT FK → marketing_conversations | 対象会話 |
| `user_email` | TEXT | フィードバック者 |
| `rating` | TEXT | 'good' / 'bad' |
| `comment` | TEXT | 自由記述コメント |
| `correction` | TEXT | 修正案（RLHF用） |
| `dimension_scores` | JSONB | `{"accuracy": 4, "relevance": 5}` |
| `tags` | TEXT[] | `["hallucination", "wrong_tool"]` |
| `review_status` | TEXT | 'new' / 'reviewed' / 'actioned' / 'dismissed' |
| `reviewed_by` | TEXT | レビュー者 |
| `review_notes` | TEXT | レビューメモ |
| `content_hash` | TEXT | メッセージ内容のSHA-256 |
| `trace_id` | TEXT | OTelトレースID（Phoenix連携） |

**制約**: `UNIQUE(message_id, user_email)` — 1ユーザー1メッセージに1件のみ

### 4.3 message_annotations（セグメント単位アノテーション）

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | UUID PK | アノテーションID |
| `message_id` | TEXT FK | 対象メッセージ |
| `conversation_id` | TEXT FK | 対象会話 |
| `user_email` | TEXT | アノテーター |
| `selector` | JSONB | アンカー情報（後述） |
| `comment` | TEXT | コメント |
| `tags` | TEXT[] | タグ |
| `severity` | TEXT | 'critical' / 'major' / 'minor' / 'info' / 'positive' |
| `correction` | TEXT | この部分の修正案 |
| `review_status` | TEXT | レビューステータス |
| `content_hash` | TEXT | 作成時のメッセージハッシュ |
| `is_stale` | BOOLEAN | 内容変更で無効化されたか |

**制約**: 1メッセージに複数アノテーション可

### 4.4 selector JSONBの型

```typescript
// テキスト選択
{
  "type": "text_span",
  "position": { "start": 142, "end": 287 },
  "quote": { "prefix": "...", "exact": "選択テキスト", "suffix": "..." }
}

// ツール呼び出し
{
  "type": "activity_item",
  "activity_item_kind": "tool",
  "tool_name": "search_companies",
  "call_id": "call_abc123"
}

// サブエージェント出力
{
  "type": "sub_agent_output",
  "agent_name": "CompanyDatabaseAgent"
}

// メッセージ全体
{
  "type": "full_message"
}
```

### 4.5 マスタテーブル

**feedback_dimensions**: 評価軸の定義
```
| key          | display_name | data_type | min | max |
|-------------|-------------|-----------|-----|-----|
| accuracy     | 正確性       | numeric   | 1   | 5   |
| relevance    | 関連性       | numeric   | 1   | 5   |
| completeness | 完全性       | numeric   | 1   | 5   |
| tool_usage   | ツール活用   | numeric   | 1   | 5   |
| helpfulness  | 有用性       | numeric   | 1   | 5   |
| tone         | トーン       | numeric   | 1   | 5   |
```

**feedback_tags**: タグの定義
```
| key            | display_name       | sentiment |
|---------------|-------------------|-----------|
| hallucination  | ハルシネーション    | negative  |
| wrong_tool     | ツール選択ミス      | negative  |
| incomplete     | 回答不完全         | negative  |
| wrong_agent    | エージェント選択ミス | negative  |
| data_error     | データ取得エラー    | negative  |
| format_issue   | フォーマット不適切  | negative  |
| too_verbose    | 冗長すぎる         | negative  |
| stale_data     | 古いデータ         | negative  |
| great_insight  | 優れた洞察         | positive  |
| good_tool_use  | 適切なツール活用    | positive  |
| comprehensive  | 包括的な回答       | positive  |
| actionable     | 実用的な提案       | positive  |
```

### 4.6 集計ビュー

- `feedback_conversation_summary`: 会話別の評価サマリー
- `feedback_tag_frequency`: タグ別の出現頻度（問題パターン特定用）
- `feedback_daily_trend`: 日別のGood/Bad推移
- `feedback_by_tool`: ツール別の問題報告数

---

## 5. エクスポート機能

### 5.1 エクスポート形式

| 形式 | 用途 | 対象者 |
|------|------|--------|
| **JSONL** | RLHF/DPO学習データ | データサイエンティスト |
| **CSV** | スプレッドシート分析 | 非技術者・管理者 |
| **HTML** | アノテーション付き会話閲覧 | レビュー担当者 |

### 5.2 JSONL エクスポート（RLHF/DPO用）

```jsonl
{
  "feedback_id": "uuid",
  "conversation_id": "conv-123",
  "message_id": "msg-456",
  "rating": "bad",
  "tags": ["hallucination"],
  "dimension_scores": {"accuracy": 2, "relevance": 4},
  "comment": "年収データが古い",
  "correction": "年収上限は900万円（2026年度）",
  "message": {
    "role": "assistant",
    "content": {"text": "...", "activity_items": [...]},
    "plain_text": "MyVisionは人材紹介会社で...",
    "model": "gemini-3-flash-preview"
  },
  "conversation_context": [
    {"role": "user", "plain_text": "MyVisionの企業情報を教えて"},
    ...
  ],
  "annotations": [
    {
      "selector": {"type": "text_span", "quote": {"exact": "年収上限は800万円"}},
      "comment": "正しくは900万円",
      "severity": "critical",
      "tags": ["hallucination"]
    }
  ]
}
```

### 5.3 CSV エクスポート

```csv
conversation_id,message_id,日時,ユーザー,メッセージ抜粋,評価,タグ,正確性,関連性,完全性,コメント,ステータス
conv-123,msg-456,2026-02-07,sato@bandq.jp,MyVisionは人材紹介会社...,bad,ハルシネーション,2,4,3,年収データが古い,新規
```

### 5.4 HTML エクスポート（アノテーション付き）

実際のチャット画面を忠実に再現したHTMLファイル:
- メッセージの全文表示
- アノテーション箇所のハイライト（黄色=info, 赤=critical）
- コメントがサイドバーに表示
- 評価・タグ・多次元スコアが表示
- スタンドアロン（CSSインライン、外部依存なし）

### 5.5 エクスポートフィルタ

- 期間（開始日〜終了日）
- 評価（Good / Bad / 全て）
- タグ（複数選択）
- レビューステータス（新規 / レビュー済み / 対応済み / 却下）
- ユーザー

---

## 6. 技術設計

### 6.1 フロントエンド構成

```
frontend/src/
├── app/
│   └── feedback/
│       └── page.tsx                    # レビューダッシュボード
├── components/
│   └── feedback/
│       ├── FeedbackBar.tsx             # 👍👎 + 詳細FBボタン（通常モード）
│       ├── FeedbackPopover.tsx         # 👎クリック時のポップオーバー
│       ├── FeedbackModeToggle.tsx      # FBモードトグル
│       ├── AnnotationLayer.tsx         # テキスト選択ハイライト + ポップオーバー
│       ├── ToolAnnotation.tsx          # ツール/サブエージェント評価ポップオーバー
│       ├── DimensionRating.tsx         # 多次元レーティング（★5段階）
│       ├── TagSelector.tsx             # タグ選択チップ
│       ├── FeedbackDashboard.tsx       # レビューページ: KPI + トレンド
│       ├── FeedbackTable.tsx           # レビューページ: フィードバック一覧
│       ├── ChatReplaySheet.tsx         # レビューページ: チャット再現Sheet
│       ├── AnnotationHighlight.tsx     # 再現ビューでのハイライト表示
│       └── ExportDialog.tsx            # エクスポート設定ダイアログ
├── hooks/
│   ├── use-feedback.ts                 # フィードバック送信・取得
│   ├── use-annotations.ts             # アノテーション操作
│   └── use-feedback-dashboard.ts      # ダッシュボード集計データ
└── lib/
    └── feedback/
        ├── types.ts                    # 型定義
        ├── text-selector.ts            # テキスト選択→セレクタ変換ユーティリティ
        └── export.ts                   # クライアントサイドエクスポート
```

### 6.2 ライブラリ選定

| 用途 | 推奨 | 理由 |
|------|------|------|
| テキスト選択ポップオーバー | **カスタム実装** (Selection API + shadcn Popover) | 既存UI統一、外部ライブラリ不要 |
| フィードバックUI全般 | **shadcn/ui** (Button, Popover, RadioGroup, Textarea, Slider) | プロジェクト既存、一貫したデザイン |
| グラフ | **recharts** (既存) | プロジェクト既存 |
| テーブル | **shadcn/ui Table** + **@tanstack/react-table** | プロジェクト既存 |
| アイコン | **lucide-react** (既存) | ThumbsUp, ThumbsDown, MessageSquare, Tag, Download, Filter等 |

**新規ライブラリ追加: 不要** — 全てプロジェクト既存のUIライブラリで実現可能

### 6.3 バックエンドAPI

```
POST   /api/v1/feedback/messages/{message_id}         # メッセージFB送信/更新
GET    /api/v1/feedback/messages/{message_id}         # メッセージFB取得
POST   /api/v1/feedback/annotations                   # アノテーション作成
GET    /api/v1/feedback/annotations/{message_id}      # メッセージのアノテーション一覧
PUT    /api/v1/feedback/annotations/{id}              # アノテーション更新
DELETE /api/v1/feedback/annotations/{id}              # アノテーション削除
GET    /api/v1/feedback/overview                      # ダッシュボード概要
GET    /api/v1/feedback/list                          # フィードバック一覧（ページネーション）
PUT    /api/v1/feedback/{id}/review                   # レビューステータス更新
POST   /api/v1/feedback/export                        # エクスポート実行
GET    /api/v1/feedback/tags                          # タグマスタ取得
GET    /api/v1/feedback/dimensions                    # 評価軸マスタ取得
```

### 6.4 Next.js APIプロキシ

既存パターンに準拠:
```
frontend/src/app/api/feedback/
├── messages/[id]/route.ts              # FB送信/取得プロキシ
├── annotations/route.ts               # アノテーションCRUDプロキシ
├── annotations/[id]/route.ts          # 個別アノテーション操作
├── overview/route.ts                  # ダッシュボードデータ
├── list/route.ts                      # 一覧データ
├── [id]/review/route.ts              # レビュー更新
├── export/route.ts                   # エクスポート
├── tags/route.ts                     # タグマスタ
└── dimensions/route.ts              # 評価軸マスタ
```

### 6.5 データフロー

```
通常モード:
  User clicks 👍/👎 → FeedbackBar → use-feedback hook
    → POST /api/feedback/messages/{id} → FastAPI → Supabase

FBモード テキスト選択:
  User selects text → window.getSelection() → text-selector.ts
    → AnnotationLayer → Popover → use-annotations hook
    → POST /api/feedback/annotations → FastAPI → Supabase

FBモード ツール評価:
  User clicks 📝 on tool badge → ToolAnnotation → use-annotations hook
    → POST /api/feedback/annotations → FastAPI → Supabase

レビューページ:
  Load → use-feedback-dashboard → GET /api/feedback/overview + list
  Click 詳細 → ChatReplaySheet → GET /api/v1/marketing-v2/threads/{id}
    + GET /api/feedback/messages/{id} + annotations/{id}
  Update review → PUT /api/feedback/{id}/review
```

---

## 7. 実装優先順位

### Phase 1: 基本フィードバック（MVP）
1. DBマイグレーション（`message_feedback`テーブル + タグマスタ）
2. バックエンドAPI（メッセージFB送信/取得）
3. `FeedbackBar` コンポーネント（👍👎 + ポップオーバー）
4. `ChatMessage.tsx` への統合
5. Next.js APIプロキシ

**価値**: 最小限のFB収集が可能に。全メッセージでGood/Bad + タグ + コメント

### Phase 2: セグメントアノテーション
1. `message_annotations`テーブル追加
2. FBモードトグル + `AnnotationLayer`
3. テキスト選択 → セレクタ変換 → 保存
4. ツール/サブエージェント評価UI
5. 多次元レーティング

**価値**: 細粒度のFB収集。どの部分が問題かを特定可能

### Phase 3: レビューダッシュボード
1. `/feedback` ページ
2. KPIカード + トレンドチャート
3. フィードバック一覧テーブル
4. チャット再現ビュー（Sheet）
5. レビューワークフロー

**価値**: 管理者がFBを効率的にレビュー・対応

### Phase 4: エクスポート
1. JSONL エクスポート
2. CSV エクスポート
3. HTML エクスポート（アノテーション付き）
4. フィルタ機能

**価値**: データを外部ツールやLLM改善パイプラインに活用

---

## 8. 設計上の重要な判断

### 8.1 なぜ `message_feedback` と `message_annotations` を分離するか

| 観点 | 1テーブル統合 | 2テーブル分離（推奨） |
|------|-------------|---------------------|
| UX | 簡易FBとアノテーションが混在 | 簡易FB（👍👎）は気軽、アノテーションは詳細 |
| クエリ | 集計が複雑 | それぞれ最適化可能 |
| カーディナリティ | 1メッセージにN件 | feedback: 1ユーザー1件、annotations: N件 |
| LangSmithとの対比 | LangSmith方式 | Argilla + Langfuse方式 |

### 8.2 なぜ外部ライブラリを使わないか

- **react-text-annotate** (137 stars, 2023年以降メンテなし): plain textのみ対応、Markdown不可
- **react-highlight-menu** (26 stars): 低採用率、保守リスク
- **Tiptap Comments** (有料): ライセンスコスト、読み取り専用コンテンツにはオーバースペック
- **assistant-ui** (8,385 stars): 良いライブラリだが、既存のChatMessage.tsxを全面書き換えが必要

**結論**: `window.getSelection()` + shadcn/ui Popover の組み合わせが最もリスクが低く、既存UIとの統一性も保てる

### 8.3 なぜPhoenix/Langfuseと別システムにするか

| 観点 | Phoenix/Langfuse統合 | 独自システム（推奨） |
|------|---------------------|---------------------|
| UX | 技術者向けUI | 社員向けにカスタマイズ可能 |
| アクセス | 別ツールに移動が必要 | チャットページ内で完結 |
| カスタマイズ | 制約あり | 完全自由 |
| データ連携 | trace_idで紐付け | trace_idで紐付け（同じ） |
| 運用コスト | 追加なし | 追加開発・保守 |

**結論**: 社員が日常的にFBを提供するUIは独自で作り、データ分析はPhoenixのtrace_idで連携する

### 8.4 Phoenix連携ポイント

```
message_feedback.trace_id → Phoenix trace_id
```

これにより:
- FBの「ハルシネーション」タグがついたメッセージのトレースをPhoenixで深掘り
- どのLLMコール・ツール呼び出しが問題を引き起こしたかをスパンレベルで分析
- 問題パターンをPhoenixのevalと組み合わせて自動検知

---

## 9. 参考情報源

| リソース | URL | 要点 |
|----------|-----|------|
| LangSmith Feedback | https://docs.langchain.com/langsmith/feedback-data-format | run_id + key + score モデル |
| Langfuse Scores | https://langfuse.com/docs/evaluation/evaluation-methods/data-model | 3種類のスコア型（numeric/categorical/boolean） |
| Argilla SpanQuestion | https://docs.argilla.io/latest/how_to_guides/annotate/ | テキストスパンアノテーション |
| W3C Web Annotation | https://www.w3.org/TR/annotation-model/ | TextPositionSelector + TextQuoteSelector |
| Hypothesis Fuzzy Anchoring | https://web.hypothes.is/blog/fuzzy-anchoring/ | ファジーマッチングによるアンカー復元 |
| Fine-Grained RLHF | https://finegrainedrlhf.github.io/ | サブ文/文/文書レベルの3段階フィードバック |
| Braintrust Human Review | https://www.braintrust.dev/docs/core/human-review | アノテーションキュー + キーボードショートカット |
| Phoenix Annotations | https://arize.com/docs/phoenix/tracing/concepts-tracing/annotations-concepts | span-level annotation + 3 annotator kinds |
| OpenAI DPO Format | https://cookbook.openai.com/examples/fine_tuning_direct_preference_optimization_guide | preference fine-tuning データ形式 |
| ChatGPT Sycophancy Fix | https://openai.com/index/expanding-on-sycophancy/ | 短期的positive FBの罠 |
| assistant-ui FeedbackAdapter | https://github.com/assistant-ui/assistant-ui | React AI chat + 組み込みFB |

---

## 10. 想定工数（参考）

| Phase | 内容 | 推定規模 |
|-------|------|---------|
| Phase 1 | 基本FB（👍👎 + タグ） | ~15ファイル新規/変更 |
| Phase 2 | セグメントアノテーション | ~10ファイル新規/変更 |
| Phase 3 | レビューダッシュボード | ~12ファイル新規 |
| Phase 4 | エクスポート | ~5ファイル新規/変更 |
| **合計** | | **~42ファイル** |
