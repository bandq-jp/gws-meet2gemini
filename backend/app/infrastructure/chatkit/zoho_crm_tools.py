"""
Zoho CRM Function Tools for Marketing ChatKit

求職者（APP-hc / jobSeeker）の検索・集計ツールを提供します。
Meta Ads MCP / GA4 MCPと組み合わせた横断分析に使用されます。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from agents import function_tool, RunContextWrapper

from app.infrastructure.zoho.client import ZohoClient, ZohoAuthError

logger = logging.getLogger(__name__)

# 流入経路の定義（AIエージェントの参照用）
CHANNEL_DEFINITIONS = {
    # スカウト系
    "sco_bizreach": "BizReachスカウト経由で獲得したリード",
    "sco_dodaX": "dodaXスカウト経由で獲得したリード",
    "sco_ambi": "Ambiスカウト経由で獲得したリード",
    "sco_rikunavi": "リクナビスカウト経由で獲得したリード",
    "sco_nikkei": "日経転職版スカウト経由で獲得したリード",
    "sco_liiga": "外資就活ネクストスカウト経由で獲得したリード",
    "sco_openwork": "OpenWorkスカウト経由で獲得したリード",
    "sco_carinar": "Carinarスカウト経由で獲得したリード",
    "sco_dodaX_D&P": "dodaXダイヤモンド/プラチナスカウト経由で獲得したリード",
    # 有料広告系
    "paid_google": "Googleリスティング広告経由で獲得したリード",
    "paid_meta": "Meta広告（Facebook/Instagram）経由で獲得したリード",
    "paid_affiliate": "アフィリエイト広告経由で獲得したリード",
    # 自然流入系
    "org_hitocareer": "SEOメディア（hitocareer）経由で獲得したリード",
    "org_jobs": "自社求人サイト経由で獲得したリード",
    # その他
    "feed_indeed": "Indeed経由で獲得したリード",
    "referral": "紹介経由で獲得したリード",
    "other": "その他",
}

# ステータスの定義（AIエージェントの参照用）
# 注意: Zohoでは番号とステータスの間にスペースがある（例: "1. リード"）
STATUS_DEFINITIONS = {
    "1. リード": "初期獲得状態",
    "2. コンタクト": "連絡済み",
    "3. 面談待ち": "面談予約済み",
    "4. 面談済み": "面談完了",
    "5. 選考中": "企業選考中",
    "6. 内定": "内定獲得",
    "7. 入社": "入社決定",
    "16. クローズ": "案件終了",
}


@function_tool(name_override="search_job_seekers")
async def search_job_seekers(
    ctx: RunContextWrapper[Any],
    channel: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Zoho CRM APP-hc（求職者）を検索します。
    流入経路やステータスでフィルタリングして、顧客情報を取得できます。

    Args:
        channel: 流入経路でフィルタ。選択肢:
            - paid_meta: Meta広告経由
            - paid_google: Googleリスティング広告経由
            - paid_affiliate: アフィリエイト広告経由
            - sco_bizreach: BizReachスカウト経由
            - sco_dodaX: dodaXスカウト経由
            - sco_ambi: Ambiスカウト経由
            - sco_rikunavi: リクナビスカウト経由
            - sco_nikkei: 日経転職版スカウト経由
            - sco_liiga: 外資就活ネクストスカウト経由
            - sco_openwork: OpenWorkスカウト経由
            - sco_carinar: Carinarスカウト経由
            - sco_dodaX_D&P: dodaXダイヤモンド/プラチナスカウト経由
            - org_hitocareer: SEOメディア経由
            - org_jobs: 自社求人サイト経由
            - feed_indeed: Indeed経由
            - referral: 紹介経由
            - other: その他
        status: 顧客ステータスでフィルタ（番号とステータスの間にスペースあり）。選択肢:
            - "1. リード", "2. コンタクト", "3. 面談待ち", "4. 面談済み"
            - "5. 選考中", "6. 内定", "7. 入社", "16. クローズ"
        name: 求職者名（部分一致）
        date_from: 登録日の開始日（YYYY-MM-DD形式）
        date_to: 登録日の終了日（YYYY-MM-DD形式）
        limit: 取得件数（最大100、デフォルト20）

    Returns:
        検索結果（record_id, 求職者名, 流入経路, 顧客ステータス, PIC, 登録日）
    """
    logger.info(
        "[zoho_crm_tools] search_job_seekers called: channel=%s, status=%s, name=%s, date_from=%s, date_to=%s",
        channel, status, name, date_from, date_to
    )

    try:
        zoho = ZohoClient()
        results = zoho.search_by_criteria(
            channel=channel,
            status=status,
            name=name,
            date_from=date_from,
            date_to=date_to,
            limit=min(limit, 100),
        )

        return {
            "success": True,
            "total": len(results),
            "records": results,
            "filters_applied": {
                "channel": channel,
                "channel_description": CHANNEL_DEFINITIONS.get(channel) if channel else None,
                "status": status,
                "name": name,
                "date_range": f"{date_from or '*'} ~ {date_to or '*'}",
            },
        }

    except ZohoAuthError as e:
        logger.error("[zoho_crm_tools] Zoho auth error: %s", e)
        return {
            "success": False,
            "error": "Zoho認証エラーが発生しました。管理者に連絡してください。",
            "error_detail": str(e),
        }
    except Exception as e:
        logger.error("[zoho_crm_tools] search_job_seekers error: %s", e)
        return {
            "success": False,
            "error": f"検索中にエラーが発生しました: {str(e)}",
        }


@function_tool(name_override="get_job_seeker_detail")
async def get_job_seeker_detail(
    ctx: RunContextWrapper[Any],
    record_id: str,
) -> Dict[str, Any]:
    """
    特定の求職者の詳細情報を取得します。
    search_job_seekersで取得したrecord_idを指定してください。

    Args:
        record_id: Zoho CRMのレコードID

    Returns:
        求職者の全フィールド情報
    """
    logger.info("[zoho_crm_tools] get_job_seeker_detail called: record_id=%s", record_id)

    if not record_id:
        return {
            "success": False,
            "error": "record_idが指定されていません",
        }

    try:
        zoho = ZohoClient()
        record = zoho.get_app_hc_record(record_id)

        if not record:
            return {
                "success": False,
                "error": f"レコードが見つかりません: {record_id}",
                "record": None,
            }

        return {
            "success": True,
            "record_id": record_id,
            "record": record,
        }

    except ZohoAuthError as e:
        logger.error("[zoho_crm_tools] Zoho auth error: %s", e)
        return {
            "success": False,
            "error": "Zoho認証エラーが発生しました。管理者に連絡してください。",
            "error_detail": str(e),
        }
    except Exception as e:
        logger.error("[zoho_crm_tools] get_job_seeker_detail error: %s", e)
        return {
            "success": False,
            "error": f"詳細取得中にエラーが発生しました: {str(e)}",
        }


@function_tool(name_override="aggregate_by_channel")
async def aggregate_by_channel(
    ctx: RunContextWrapper[Any],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    流入経路ごとの求職者数を集計します。
    Meta広告やGA4のデータと組み合わせて、広告効果の分析に使用できます。

    Args:
        date_from: 集計期間の開始日（YYYY-MM-DD形式）
        date_to: 集計期間の終了日（YYYY-MM-DD形式）

    Returns:
        流入経路ごとの件数と説明

    使用例:
        - 今月の流入経路別リード数を確認
        - Meta広告経由の成約率をGA4/Meta Ads MCPと比較
        - スカウト系 vs 広告系の効果比較
    """
    logger.info(
        "[zoho_crm_tools] aggregate_by_channel called: date_from=%s, date_to=%s",
        date_from, date_to
    )

    try:
        zoho = ZohoClient()
        results = zoho.count_by_channel(date_from=date_from, date_to=date_to)

        # 日本語説明を追加してカテゴリ分類
        enriched: Dict[str, Any] = {
            "スカウト系": {},
            "有料広告系": {},
            "自然流入系": {},
            "その他": {},
        }

        for channel, count in results.items():
            item = {
                "count": count,
                "description": CHANNEL_DEFINITIONS.get(channel, "不明"),
            }

            if channel.startswith("sco_"):
                enriched["スカウト系"][channel] = item
            elif channel.startswith("paid_"):
                enriched["有料広告系"][channel] = item
            elif channel.startswith("org_"):
                enriched["自然流入系"][channel] = item
            else:
                enriched["その他"][channel] = item

        # カテゴリ別小計
        category_totals = {
            category: sum(item["count"] for item in items.values())
            for category, items in enriched.items()
        }

        return {
            "success": True,
            "period": {
                "from": date_from or "全期間",
                "to": date_to or "現在",
            },
            "by_category": enriched,
            "category_totals": category_totals,
            "total": sum(results.values()),
        }

    except ZohoAuthError as e:
        logger.error("[zoho_crm_tools] Zoho auth error: %s", e)
        return {
            "success": False,
            "error": "Zoho認証エラーが発生しました。管理者に連絡してください。",
            "error_detail": str(e),
        }
    except Exception as e:
        logger.error("[zoho_crm_tools] aggregate_by_channel error: %s", e)
        return {
            "success": False,
            "error": f"集計中にエラーが発生しました: {str(e)}",
        }


@function_tool(name_override="count_job_seekers_by_status")
async def count_job_seekers_by_status(
    ctx: RunContextWrapper[Any],
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    ステータスごとの求職者数を集計します（ファネル分析用）。
    特定の流入経路に絞った分析も可能です。

    Args:
        channel: 流入経路でフィルタ（省略時は全体）
            選択肢: paid_meta, paid_google, sco_bizreach, org_hitocareer など
        date_from: 集計期間の開始日（YYYY-MM-DD形式）
        date_to: 集計期間の終了日（YYYY-MM-DD形式）

    Returns:
        ステータスごとの件数（ファネル分析用）

    使用例:
        - Meta広告経由のリードがどこまで進んでいるかを確認
        - 流入経路別の成約率（入社/リード）を比較
        - ボトルネックの特定（どのステータスで離脱が多いか）
    """
    logger.info(
        "[zoho_crm_tools] count_job_seekers_by_status called: channel=%s, date_from=%s, date_to=%s",
        channel, date_from, date_to
    )

    try:
        zoho = ZohoClient()
        results = zoho.count_by_status(
            channel=channel,
            date_from=date_from,
            date_to=date_to,
        )

        # ステータスの説明を追加
        enriched = {}
        for status, count in results.items():
            enriched[status] = {
                "count": count,
                "description": STATUS_DEFINITIONS.get(status, "不明"),
            }

        total = sum(results.values())

        # 簡易ファネル分析
        funnel_analysis = None
        if total > 0:
            lead_count = results.get("1.リード", 0)
            interview_count = results.get("4.面談済み", 0)
            hired_count = results.get("7.入社", 0)

            funnel_analysis = {
                "面談率": f"{(interview_count / total * 100):.1f}%" if total > 0 else "N/A",
                "入社率": f"{(hired_count / total * 100):.1f}%" if total > 0 else "N/A",
                "リード→面談転換率": f"{(interview_count / lead_count * 100):.1f}%" if lead_count > 0 else "N/A",
                "面談→入社転換率": f"{(hired_count / interview_count * 100):.1f}%" if interview_count > 0 else "N/A",
            }

        return {
            "success": True,
            "channel_filter": channel or "全体",
            "channel_description": CHANNEL_DEFINITIONS.get(channel) if channel else None,
            "period": {
                "from": date_from or "全期間",
                "to": date_to or "現在",
            },
            "by_status": enriched,
            "total": total,
            "funnel_analysis": funnel_analysis,
        }

    except ZohoAuthError as e:
        logger.error("[zoho_crm_tools] Zoho auth error: %s", e)
        return {
            "success": False,
            "error": "Zoho認証エラーが発生しました。管理者に連絡してください。",
            "error_detail": str(e),
        }
    except Exception as e:
        logger.error("[zoho_crm_tools] count_job_seekers_by_status error: %s", e)
        return {
            "success": False,
            "error": f"集計中にエラーが発生しました: {str(e)}",
        }


@function_tool(name_override="get_channel_definitions")
async def get_channel_definitions(
    ctx: RunContextWrapper[Any],
) -> Dict[str, Any]:
    """
    流入経路の定義一覧を取得します。
    どの流入経路が何を意味するかを確認したいときに使用します。

    Returns:
        流入経路コードと説明の一覧
    """
    return {
        "success": True,
        "channels": CHANNEL_DEFINITIONS,
        "statuses": STATUS_DEFINITIONS,
        "usage_hint": "search_job_seekers や aggregate_by_channel で使用できる流入経路コードの一覧です。",
    }


# エクスポート用のツールリスト
ZOHO_CRM_TOOLS = [
    search_job_seekers,
    get_job_seeker_detail,
    aggregate_by_channel,
    count_job_seekers_by_status,
    get_channel_definitions,
]
