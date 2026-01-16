# Zoho CRM 顧客検索ツール 要件定義書

## 1. 概要

### 1.1 目的
AIエージェント（Marketing ChatKit）に Zoho CRM の顧客（求職者）データへのアクセス機能を追加し、Meta Ads MCP / GA4 MCP と組み合わせた横断分析を可能にする。

### 1.2 ビジネス目標
- 「どの広告（流入経路）から来た顧客が成約に至ったか」を分析
- 広告費対効果（ROAS）の顧客レベルでの可視化
- マーケティング施策の最適化支援

### 1.3 対象モジュール
- **Zoho CRM モジュール**: `CustomModule1`（表示名: APP-hc / jobSeeker）
- **主要フィールド**: 流入経路、顧客ステータス、求職者名、登録日、PIC（担当者）

---

## 2. 実装方式

### 2.1 選定方式
**Function Tool として既存バックエンドに統合**

### 2.2 選定理由
| 観点 | 詳細 |
|------|------|
| 既存資産 | `ZohoClient` のトークン管理・COQL対応を再利用 |
| セキュリティ | 個人情報を含むため外部MCP化は非推奨 |
| 運用コスト | 追加インフラ不要 |
| 統合性 | Meta Ads / GA4 MCPと同一Agent内で併用可能 |

### 2.3 代替案（将来検討）
- 他プロジェクトで再利用が必要になった場合、Function Toolのロジックを切り出してMCPサーバー化

---

## 3. 機能要件

### 3.1 ツール一覧

| ツール名 | 説明 | 主要パラメータ |
|---------|------|---------------|
| `search_job_seekers` | 流入経路・ステータス等で顧客検索 | channel, status, name, date_from, date_to, limit |
| `get_job_seeker_detail` | 特定顧客の詳細情報取得 | record_id |
| `aggregate_by_channel` | 流入経路別の集計 | date_from, date_to |
| `count_job_seekers_by_status` | ステータス別の件数集計 | channel, date_from, date_to |

### 3.2 流入経路マスタ

```
スカウト系:
- sco_bizreach      : BizReachスカウト経由
- sco_dodaX         : dodaXスカウト経由
- sco_dodaX_D&P     : dodaXダイヤモンド/プラチナスカウト経由
- sco_ambi          : Ambiスカウト経由
- sco_rikunavi      : リクナビスカウト経由
- sco_nikkei        : 日経転職版スカウト経由
- sco_liiga         : 外資就活ネクストスカウト経由
- sco_openwork      : OpenWorkスカウト経由
- sco_carinar       : Carinarスカウト経由

有料広告系:
- paid_google       : Googleリスティング広告経由
- paid_meta         : Meta広告経由
- paid_affiliate    : アフィリエイト広告経由

自然流入系:
- org_hitocareer    : SEOメディア（hitocareer）経由
- org_jobs          : 自社求人サイト経由

その他:
- feed_indeed       : Indeed経由
- referral          : 紹介経由
- other             : その他
```

### 3.3 顧客ステータス（想定）

```
1.リード
2.コンタクト
3.面談待ち
4.面談済み
5.選考中
...
16.クローズ
```

※ 実際のステータス値は Zoho CRM のフィールド定義を確認して決定

---

## 4. 技術設計

### 4.1 ファイル構成

```
backend/app/infrastructure/
├── zoho/
│   ├── client.py              # 既存: トークン管理、API呼び出し
│   └── search_tools.py        # 新規: 検索用ツール実装
├── chatkit/
│   ├── seo_agent_factory.py   # 既存: ツール追加
│   ├── seo_article_tools.py   # 既存: 参考パターン
│   └── zoho_crm_tools.py      # 新規: Function Tool定義
└── config/
    └── settings.py            # 既存: 環境変数
```

### 4.2 ZohoClient 拡張

既存の `ZohoClient` に以下のメソッドを追加:

```python
class ZohoClient:
    # 既存メソッド
    # - search_app_hc_by_name()
    # - get_app_hc_record()

    # 新規追加
    def query_coql(self, query: str) -> list[dict]:
        """COQL クエリを実行"""

    def search_by_criteria(
        self,
        channel: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 20
    ) -> list[dict]:
        """条件指定で顧客検索"""

    def count_by_channel(
        self,
        date_from: str | None = None,
        date_to: str | None = None
    ) -> dict[str, int]:
        """流入経路別の件数集計"""
```

### 4.3 Function Tool 実装

```python
# backend/app/infrastructure/chatkit/zoho_crm_tools.py

from agents import function_tool, RunContextWrapper
from app.infrastructure.zoho.client import ZohoClient
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

CHANNEL_DEFINITIONS = {
    "sco_bizreach": "BizReachスカウト経由",
    "sco_dodaX": "dodaXスカウト経由",
    "paid_meta": "Meta広告経由",
    "paid_google": "Googleリスティング広告経由",
    "org_hitocareer": "SEOメディア経由",
    # ... 他の流入経路
}


@function_tool(name_override="search_job_seekers")
async def search_job_seekers(
    ctx: RunContextWrapper,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """
    Zoho CRM APP-hc（求職者）を検索します。

    Args:
        channel: 流入経路（例: paid_meta, sco_bizreach, org_hitocareer）
        status: 顧客ステータス（例: 1.リード, 3.面談待ち, 16.クローズ）
        name: 求職者名（部分一致）
        date_from: 登録日開始（YYYY-MM-DD）
        date_to: 登録日終了（YYYY-MM-DD）
        limit: 取得件数（最大100）

    Returns:
        検索結果リスト（record_id, 求職者名, 流入経路, ステータス等）

    流入経路の選択肢:
        - paid_meta: Meta広告経由
        - paid_google: Googleリスティング広告経由
        - sco_bizreach: BizReachスカウト経由
        - sco_dodaX: dodaXスカウト経由
        - org_hitocareer: SEOメディア経由
        - その他（定義一覧参照）
    """
    zoho = ZohoClient()
    results = zoho.search_by_criteria(
        channel=channel,
        status=status,
        name=name,
        date_from=date_from,
        date_to=date_to,
        limit=min(limit, 100)
    )

    return {
        "total": len(results),
        "records": results,
        "filters_applied": {
            "channel": channel,
            "status": status,
            "name": name,
            "date_range": f"{date_from or '*'} ~ {date_to or '*'}"
        }
    }


@function_tool(name_override="get_job_seeker_detail")
async def get_job_seeker_detail(
    ctx: RunContextWrapper,
    record_id: str,
) -> dict:
    """
    特定の求職者の詳細情報を取得します。

    Args:
        record_id: Zoho CRMのレコードID

    Returns:
        求職者の全フィールド情報
    """
    zoho = ZohoClient()
    record = zoho.get_app_hc_record(record_id)

    if not record:
        return {"error": f"Record {record_id} not found", "record": None}

    return {
        "record_id": record_id,
        "record": record
    }


@function_tool(name_override="aggregate_by_channel")
async def aggregate_by_channel(
    ctx: RunContextWrapper,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """
    流入経路ごとの求職者数を集計します。
    Meta広告やGA4のデータと組み合わせて、広告効果の分析に使用できます。

    Args:
        date_from: 集計期間開始（YYYY-MM-DD）
        date_to: 集計期間終了（YYYY-MM-DD）

    Returns:
        流入経路ごとの件数
    """
    zoho = ZohoClient()
    results = zoho.count_by_channel(date_from=date_from, date_to=date_to)

    # 日本語説明を追加
    enriched = {}
    for channel, count in results.items():
        enriched[channel] = {
            "count": count,
            "description": CHANNEL_DEFINITIONS.get(channel, "その他")
        }

    return {
        "period": {
            "from": date_from or "all",
            "to": date_to or "all"
        },
        "by_channel": enriched,
        "total": sum(results.values())
    }


@function_tool(name_override="count_job_seekers_by_status")
async def count_job_seekers_by_status(
    ctx: RunContextWrapper,
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """
    ステータスごとの求職者数を集計します。
    特定の流入経路に絞った分析も可能です。

    Args:
        channel: 流入経路でフィルタ（省略時は全体）
        date_from: 集計期間開始（YYYY-MM-DD）
        date_to: 集計期間終了（YYYY-MM-DD）

    Returns:
        ステータスごとの件数（ファネル分析用）
    """
    zoho = ZohoClient()
    results = zoho.count_by_status(
        channel=channel,
        date_from=date_from,
        date_to=date_to
    )

    return {
        "channel_filter": channel or "all",
        "period": {
            "from": date_from or "all",
            "to": date_to or "all"
        },
        "by_status": results,
        "total": sum(results.values())
    }
```

### 4.4 Agent Factory への統合

```python
# backend/app/infrastructure/chatkit/seo_agent_factory.py に追加

from app.infrastructure.chatkit.zoho_crm_tools import (
    search_job_seekers,
    get_job_seeker_detail,
    aggregate_by_channel,
    count_job_seekers_by_status,
)

ZOHO_CRM_TOOLS = [
    search_job_seekers,
    get_job_seeker_detail,
    aggregate_by_channel,
    count_job_seekers_by_status,
]

class MarketingAgentFactory:
    def build_agent(self, asset: dict[str, Any] | None = None, ...):
        tools: List[Any] = []

        # ... 既存のツール設定 ...

        # Zoho CRM ツールを追加
        enable_zoho_crm = asset is None or asset.get("enable_zoho_crm", True)
        if enable_zoho_crm and self._settings.zoho_refresh_token:
            tools.extend(ZOHO_CRM_TOOLS)

        # ... 残りの設定 ...
```

### 4.5 System Prompt 更新

```python
# Marketing Agent の system prompt に追加

ZOHO_CRM_INSTRUCTIONS = """
## Zoho CRM（APP-hc: 求職者データ）利用ガイド

### 利用可能なツール
- `search_job_seekers`: 流入経路・ステータス等で顧客検索
- `get_job_seeker_detail`: 特定顧客の詳細取得
- `aggregate_by_channel`: 流入経路別の集計
- `count_job_seekers_by_status`: ステータス別の集計

### 流入経路の種類
**有料広告系**:
- `paid_meta`: Meta広告経由（Facebook/Instagram）
- `paid_google`: Googleリスティング広告経由
- `paid_affiliate`: アフィリエイト広告経由

**スカウト系**:
- `sco_bizreach`: BizReachスカウト
- `sco_dodaX`: dodaXスカウト
- `sco_ambi`: Ambiスカウト
- その他多数...

**自然流入系**:
- `org_hitocareer`: SEOメディア（hitocareer）経由
- `org_jobs`: 自社求人サイト経由

### 横断分析の例
1. Meta広告のパフォーマンス → `paid_meta` で流入した顧客のステータス分布
2. 流入経路別の成約率比較
3. 広告費 vs 成約数の相関分析（Meta Ads MCPと組み合わせ）
"""
```

---

## 5. データベース変更

### 5.1 marketing_model_assets テーブル

```sql
-- enable_zoho_crm フラグを追加
ALTER TABLE public.marketing_model_assets
  ADD COLUMN IF NOT EXISTS enable_zoho_crm boolean NOT NULL DEFAULT true;
```

---

## 6. 横断分析ユースケース

### 6.1 広告効果分析

**ユーザーの質問例**:
> 「今月のMeta広告からの流入顧客で、面談まで進んだ人は何人？」

**AIの処理フロー**:
1. `search_job_seekers(channel="paid_meta", status="4.面談済み", date_from="2026-01-01")`
2. 結果を整理して回答

### 6.2 ROAS分析

**ユーザーの質問例**:
> 「先月のMeta広告費に対して、何人成約した？」

**AIの処理フロー**:
1. Meta Ads MCP → 先月の広告費取得
2. `count_job_seekers_by_status(channel="paid_meta", date_from="2025-12-01", date_to="2025-12-31")`
3. 成約ステータスの件数を抽出
4. 広告費 ÷ 成約数 = CPA を算出

### 6.3 流入経路比較

**ユーザーの質問例**:
> 「スカウト経由と広告経由、どちらの成約率が高い？」

**AIの処理フロー**:
1. `aggregate_by_channel()` で全体像を取得
2. スカウト系（sco_*）と広告系（paid_*）をグループ化
3. 各グループの成約率を算出・比較

---

## 7. セキュリティ考慮事項

### 7.1 データアクセス制御
- Function Tool は Marketing ChatKit のトークン認証を通過したユーザーのみ利用可能
- 個人情報（求職者名、連絡先等）の取り扱いに注意

### 7.2 ログ記録
- ツール呼び出しは既存の `ToolUsageTracker` で記録
- 監査ログとして誰がいつどのデータにアクセスしたか追跡可能

### 7.3 レート制限
- Zoho API のレート制限（10 req/10 min）に注意
- 大量検索時はバッチ処理を検討

---

## 8. テスト計画

### 8.1 単体テスト
- `ZohoClient.search_by_criteria()` の各条件パターン
- `ZohoClient.count_by_channel()` の集計ロジック
- Function Tool の入力バリデーション

### 8.2 統合テスト
- Marketing Agent で Zoho CRM ツールが呼び出せること
- Meta Ads MCP と組み合わせた横断クエリ
- エラーハンドリング（Zoho API エラー時の挙動）

### 8.3 E2Eテスト
- ChatKit UI から「Meta広告からの流入顧客を検索」と入力
- 正しく検索結果が返ること

---

## 9. 実装スケジュール（タスク順序）

### Phase 1: 基盤実装
- [ ] `ZohoClient` に `query_coql()`, `search_by_criteria()`, `count_by_channel()` 追加
- [ ] Zoho CRM のフィールド名確認（流入経路、顧客ステータス等）

### Phase 2: Function Tool 実装
- [ ] `zoho_crm_tools.py` 作成
- [ ] `seo_agent_factory.py` にツール統合
- [ ] System Prompt 更新

### Phase 3: テスト・調整
- [ ] 単体テスト作成・実行
- [ ] ChatKit UI での動作確認
- [ ] 横断分析のユースケース検証

### Phase 4: 本番デプロイ
- [ ] DBマイグレーション実行
- [ ] Cloud Run デプロイ
- [ ] 本番動作確認

---

## 10. 将来の拡張案

### 10.1 書き込み機能
- AIエージェントが顧客ステータスを更新
- 自動タグ付け（広告経由の顧客に自動でタグ追加）

### 10.2 リモートMCP化
- 他プロジェクトで再利用が必要になった場合
- 認証サービスの共有化と合わせて検討

### 10.3 リアルタイム通知
- 新規リード獲得時のSlack通知連携
- ステータス変更時のアラート

---

## 付録: 環境変数

既存の設定をそのまま使用:

```bash
# Zoho OAuth（既存）
ZOHO_CLIENT_ID=xxx
ZOHO_CLIENT_SECRET=xxx
ZOHO_REFRESH_TOKEN=xxx
ZOHO_API_BASE_URL=https://www.zohoapis.jp
ZOHO_ACCOUNTS_BASE_URL=https://accounts.zoho.jp
ZOHO_APP_HC_MODULE=CustomModule1
```

新規追加不要。
