# マーケティングAI UX改善提案書

> **調査日**: 2026-02-05
> **調査方法**: 6並列エージェントによる大規模調査
> **データソース**: Supabase会話履歴 (314会話, 6311メッセージ), 参照プロジェクト, Web検索

---

## エグゼクティブサマリー

| カテゴリ | 健全性スコア | 状態 |
|---------|-------------|------|
| ツール完了判定 | 94% | ✅ Good |
| サブエージェント完了判定 | 0% | ❌ **CRITICAL** |
| Activity Items 永続化 | 7% | ❌ **CRITICAL** |
| エラーハンドリング | 94% | ✅ Good |
| ユーザー行動追跡 | 73% | ⚠️ Fair |
| **総合** | **54%** | **要改善** |

---

## 1. 重大な問題（即時対応必要）

### 1.1 サブエージェント `is_running` フィールド未設定

**発見**: 215件のサブエージェントアイテムすべてで `is_running: None`

**分布**:
| サブエージェント | 件数 | 割合 |
|-----------------|------|------|
| SEOAgent | 55 | 25.6% |
| ZohoCRMAgent | 53 | 24.7% |
| AnalyticsAgent | 47 | 21.9% |
| AdPlatformAgent | 32 | 14.9% |
| WordPressAgent | 21 | 9.8% |
| CandidateInsightAgent | 7 | 3.3% |

**根本原因**:
1. `agent_service.py` の `_process_sub_agent_event()` が `is_running` を返していない
2. `marketing.py` のDB保存時に `is_running` フィールドを含めていない

**影響**:
- UIでサブエージェントが永久に「実行中」表示
- 会話履歴復元時に完了状態が不明
- パフォーマンス分析が不可能

**修正コード**:
```python
# agent_service.py _process_sub_agent_event()
# 各イベントタイプで is_running を設定
- started → is_running: True
- tool_called → is_running: True
- tool_output → is_running: True
- reasoning → is_running: True
- message_output → is_running: False  # 完了マーカー

# marketing.py line 829
# DB保存時に is_running を含める
"is_running": event.get("is_running")
```

---

### 1.2 Activity Items 永続化バグ

**発見**: 635件のアシスタントメッセージのうち **93.5%** が空の `activity_items`

**正常に保存されている41件の内訳**:
| タイプ | 件数 |
|--------|------|
| sub_agent | 656 |
| tool | 62 |
| text | 55 |
| reasoning | 6 |

**影響**:
- 会話履歴の詳細が失われている
- ツール使用パターンの分析不可
- 監査証跡の欠落

**推定原因**:
- Native SSE実装移行時のDB永続化が不完全
- ストリーム終了前に `activity_items` がシリアライズされていない可能性

---

### 1.3 HostedMCPTool 互換性エラー

**発見**: 4件のツール呼び出し失敗（6.5%）

**エラーメッセージ**:
```
"Hosted tools are not supported with the ChatCompletions API.
Got tool type: <class 'agents.mcp.tool.HostedMCPTool'>"
```

**影響を受けるサブエージェント**:
- SEOAgent (Ahrefs)
- AnalyticsAgent (GA4/GSC)
- AdPlatformAgent (Meta Ads)
- WordPressAgent

**根本原因**:
- LiteLLM/ChatCompletions API では HostedMCPTool が明示的に拒否される
- OpenAI Responses API のみがサポート

**対策**:
- サブエージェントモデルは `gpt-5-mini` (OpenAI) を維持
- 将来的には `MCPServerStdio` に完全移行

---

## 2. UI/UX改善点

### 2.1 reasoningContent の Markdown 破壊

**問題コード** (`use-marketing-chat.ts` L358):
```typescript
reasoningContent: (subItem.reasoningContent || "") + " " + reasoningContent,
```

**修正**:
```typescript
reasoningContent: (subItem.reasoningContent || "") + "\n\n" + reasoningContent,
```

---

### 2.2 SubAgentBadge 自動折りたたみ欠如

**問題**: 完了後もすべてのサブエージェントが展開状態

**修正** (`ChatMessage.tsx`):
```typescript
useEffect(() => {
  if (item.isRunning && hasDetails) {
    setIsExpanded(true);
  } else if (!item.isRunning) {
    // 完了時に1秒後自動折りたたみ
    const timer = setTimeout(() => setIsExpanded(false), 1000);
    return () => clearTimeout(timer);
  }
}, [item.isRunning, hasDetails]);
```

---

### 2.3 参照プロジェクトとの比較結果

| 機能 | 参照プロジェクト | 本プロジェクト | 状態 |
|------|-----------------|----------------|------|
| ツール完了判定 (output有無) | ✅ | ✅ | OK |
| 逆順検索 (最新から) | ✅ | ✅ | OK |
| done時の安全弁 | ✅ | ✅ | OK |
| サブエージェント対応 | ❌ | ✅ | 本プロジェクト優位 |
| InterleavedTimeline | ✅ | ✅ | OK |
| 完了後の自動折りたたみ | ✅ | ❌ | 要修正 |
| React setState-during-render対策 | ❌ | ✅ | 本プロジェクト優位 |

---

## 3. ユーザー行動分析

### 3.1 利用パターン

| 指標 | 値 |
|------|-----|
| 総会話数 | 314 |
| 総メッセージ数 | 6,311 |
| 平均ターン数/会話 | 2.01 |
| シングルターン会話 | 59.8% |
| マルチターン会話 | 40.2% |

### 3.2 クエリ分布

| トピック | 割合 |
|---------|------|
| SEO (Ahrefs, GA4, GSC) | 29.4% |
| コンテンツ (WordPress) | 16.6% |
| 広告 (Meta) | 6.2% |
| CRM (Zoho) | 0.9% |
| その他 | 53.6% |

### 3.3 ユーザー集中度

| ユーザー | 会話数 | 割合 |
|---------|--------|------|
| masuda.g@bandq.jp | 186 | 59.2% |
| Top 3 users | 273 | 86.9% |

**リスク**: 単一パワーユーザーへの過度な最適化

### 3.4 繰り返しクエリ（テンプレート化候補）

| クエリパターン | 回数 |
|---------------|------|
| BtoB SaaS記事作成 | 29 |
| エンジニア転職記事 | 19 |
| SEOパフォーマンス確認 | 12 |

---

## 4. 推奨アクション

### 即時対応（今日中）

| # | タスク | ファイル | 工数 |
|---|--------|---------|------|
| 1 | サブエージェント `is_running` 設定 | `agent_service.py`, `marketing.py` | 30分 |
| 2 | reasoningContent Markdown修正 | `use-marketing-chat.ts` | 5分 |
| 3 | SubAgentBadge自動折りたたみ | `ChatMessage.tsx` | 15分 |

### 短期（1週間以内）

| # | タスク | 詳細 |
|---|--------|------|
| 4 | Activity Items永続化調査 | 93.5%空の原因特定 |
| 5 | CRM利用促進 | 現在0.9%→10%目標 |
| 6 | テンプレート機能 | 繰り返しクエリをプリセット化 |

### 中期（1ヶ月以内）

| # | タスク | 詳細 |
|---|--------|------|
| 7 | MCPServerStdio完全移行 | HostedMCPTool依存脱却 |
| 8 | ユーザーオンボーディング | パワーユーザー集中リスク軽減 |
| 9 | 分析ダッシュボード | ツール成功率、応答時間追跡 |

---

## 5. UXベストプラクティス（Web調査結果）

### 5.1 ツール実行UIフィードバック

- **実行中**: ローディングスピナー + 進捗テキスト
- **完了**: チェックマーク + 結果プレビュー
- **エラー**: インラインアラート + リトライオプション

### 5.2 マルチエージェントUI設計原則

1. **検証性 (Verification)**: ユーザーが意思決定を確認できる
2. **透明性 (Transparency)**: エージェント動作を可視化
3. **ハンドオフ (Handoffs)**: エージェント間の委譲を明確に
4. **エージェントバッジ**: 色分けによる視覚的区別

### 5.3 ストリーミングチャットUX

- トークン生成と同時にリアルタイム表示
- ストリーミング中は入力を無効化
- 同時送信メッセージはグループ化

---

## 6. 実装健全性スコア詳細

| 項目 | スコア | 詳細 |
|------|--------|------|
| ツール完了判定 | 9/10 | output有無で判定、安全弁あり |
| サブエージェント完了判定 | 2/10 | is_running未設定が致命的 |
| 順序保持 | 10/10 | Sequenceベースで完全保持 |
| 推論表示 | 8/10 | Markdown破壊問題あり |
| エラーハンドリング | 9/10 | 94%成功率 |
| DB永続化 | 3/10 | 93.5%がactivity_items空 |
| **総合** | **6.8/10** | **改善余地大** |

---

## 7. 調査方法論

### 7.1 並列エージェント構成

| エージェント | 調査対象 | トークン使用量 |
|-------------|---------|---------------|
| Agent 1 | ツール完了判定分析 | 76,086 |
| Agent 2 | 参照プロジェクト比較 | 120,408 |
| Agent 3 | エラーパターン分析 | 60,029 |
| Agent 4 | ユーザー行動分析 | 67,002 |
| Agent 5 | Web検索: UXベストプラクティス | 52,207 |
| Agent 6 | サブエージェントUI分析 | 84,195 |
| **合計** | | **459,927 tokens** |

### 7.2 データソース

- Supabase `marketing_conversations`: 314件
- Supabase `marketing_messages`: 6,311件
- 参照プロジェクト: `/home/als0028/study/shintairiku/ga4-oauth-aiagent`
- Web検索: AIチャットUI/UXベストプラクティス 2025

---

## 8. 結論

**現在のシステムは基本機能は動作しているが、サブエージェント完了判定とDB永続化に重大なバグがある。**

**即時対応が必要な2つの問題**:
1. `is_running` フィールド未設定 → サブエージェントが永久に「実行中」表示
2. `activity_items` 永続化バグ → 会話履歴の93.5%が詳細情報なし

**これらを修正することで、総合健全性スコアを 6.8/10 → 8.5/10 に向上できる見込み。**

---

*Generated by Claude Code with 6 parallel exploration agents*
*Date: 2026-02-05*
