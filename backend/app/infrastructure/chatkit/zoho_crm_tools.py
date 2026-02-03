"""
Zoho CRM Function Tools for Marketing ChatKit

求職者（APP-hc / jobSeeker）の検索・集計ツールを提供します。
Meta Ads MCP / GA4 MCPと組み合わせた横断分析に使用されます。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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
    "5. 提案中": "求人提案中",
    "6. 応募意思獲得": "応募意思獲得",
    "7. 打診済み": "企業へ打診済み",
    "8. 一次面接待ち": "一次面接待ち",
    "9. 一次面接済み": "一次面接済み",
    "10. 最終面接待ち": "最終面接待ち",
    "11. 最終面接済み": "最終面接済み",
    "12. 内定": "内定獲得",
    "13. 内定承諾": "内定承諾",
    "14. 入社": "入社決定",
    "15. 入社後退職（入社前退職含む）": "入社後退職",
    "16. クローズ": "案件終了",
    "17. 連絡禁止": "連絡禁止",
    "18. 中長期対応": "中長期対応",
    "19. 他社送客": "他社送客",
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
    求職者を検索。channel/statusの定義はget_channel_definitionsで取得。

    Args:
        channel: 流入経路(paid_meta, sco_bizreach等)
        status: ステータス("1. リード"等、番号+スペース+名前)
        name: 名前(部分一致)
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)
        limit: 件数(max100)
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
    """特定求職者の詳細取得。record_idはsearch_job_seekersで取得。"""
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
    """流入経路別の求職者数を集計。広告効果分析に使用。"""
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
    """ステータス別集計(ファネル分析用)。channelで絞込可。"""
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
            lead_count = results.get("1. リード", 0)
            interview_count = results.get("4. 面談済み", 0)
            hired_count = results.get("14. 入社", 0)

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
    """流入経路(channel)とステータス(status)の定義一覧を取得。"""
    return {
        "success": True,
        "channels": CHANNEL_DEFINITIONS,
        "statuses": STATUS_DEFINITIONS,
        "usage_hint": "search_job_seekers や aggregate_by_channel で使用できる流入経路コードの一覧です。",
    }


# --- 新規分析ツール (2026-02-03追加) ---

@function_tool(name_override="analyze_funnel_by_channel")
async def analyze_funnel_by_channel(
    ctx: RunContextWrapper[Any],
    channel: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """特定channelのファネル分析。転換率とボトルネックを特定。"""
    logger.info(
        "[zoho_crm_tools] analyze_funnel_by_channel: channel=%s, date_from=%s, date_to=%s",
        channel, date_from, date_to
    )

    if not channel:
        return {
            "success": False,
            "error": "流入経路（channel）を指定してください",
        }

    try:
        zoho = ZohoClient()
        status_counts = zoho.count_by_status(
            channel=channel,
            date_from=date_from,
            date_to=date_to,
        )

        # ファネルステージ定義（順序重要）
        funnel_stages = [
            ("1. リード", "初期獲得"),
            ("2. コンタクト", "連絡済み"),
            ("3. 面談待ち", "面談予約"),
            ("4. 面談済み", "面談完了"),
            ("5. 提案中", "求人提案"),
            ("6. 応募意思獲得", "応募意思"),
            ("7. 打診済み", "企業打診"),
            ("8. 一次面接待ち", "一次面接待ち"),
            ("9. 一次面接済み", "一次面接完了"),
            ("10. 最終面接待ち", "最終面接待ち"),
            ("11. 最終面接済み", "最終面接完了"),
            ("12. 内定", "内定"),
            ("13. 内定承諾", "内定承諾"),
            ("14. 入社", "入社決定"),
        ]

        # ファネル分析
        funnel_data = []
        prev_count = None
        bottlenecks = []

        for status, label in funnel_stages:
            count = status_counts.get(status, 0)
            conversion_rate = None
            drop_rate = None

            if prev_count is not None and prev_count > 0:
                conversion_rate = round((count / prev_count) * 100, 1)
                drop_rate = round(100 - conversion_rate, 1)

                # ボトルネック判定: 転換率50%未満
                if conversion_rate < 50 and count < prev_count:
                    bottlenecks.append({
                        "stage": label,
                        "from_status": funnel_data[-1]["status"] if funnel_data else None,
                        "to_status": status,
                        "conversion_rate": conversion_rate,
                        "drop_count": prev_count - count,
                    })

            funnel_data.append({
                "status": status,
                "label": label,
                "count": count,
                "conversion_rate_from_prev": f"{conversion_rate}%" if conversion_rate is not None else "N/A",
                "drop_rate": f"{drop_rate}%" if drop_rate is not None else "N/A",
            })

            prev_count = count

        # 全体KPI
        total = sum(status_counts.values())
        lead_count = status_counts.get("1. リード", 0)
        hired_count = status_counts.get("14. 入社", 0)
        interview_count = status_counts.get("4. 面談済み", 0)

        kpis = {
            "総数": total,
            "リード数": lead_count,
            "面談済み数": interview_count,
            "入社数": hired_count,
            "全体入社率": f"{(hired_count / lead_count * 100):.1f}%" if lead_count > 0 else "N/A",
            "面談率": f"{(interview_count / lead_count * 100):.1f}%" if lead_count > 0 else "N/A",
        }

        # 改善提案を生成
        recommendations = _generate_funnel_recommendations(bottlenecks)

        return {
            "success": True,
            "channel": channel,
            "channel_description": CHANNEL_DEFINITIONS.get(channel, "不明"),
            "period": {
                "from": date_from or "全期間",
                "to": date_to or "現在",
            },
            "funnel_data": funnel_data,
            "bottlenecks": bottlenecks,
            "kpis": kpis,
            "recommendations": recommendations,
        }

    except ZohoAuthError as e:
        logger.error("[zoho_crm_tools] Zoho auth error: %s", e)
        return {
            "success": False,
            "error": "Zoho認証エラーが発生しました。",
            "error_detail": str(e),
        }
    except Exception as e:
        logger.error("[zoho_crm_tools] analyze_funnel_by_channel error: %s", e)
        return {
            "success": False,
            "error": f"ファネル分析中にエラーが発生しました: {str(e)}",
        }


def _generate_funnel_recommendations(bottlenecks: list) -> list:
    """ボトルネックに基づく改善提案を生成"""
    recommendations = []

    for bn in bottlenecks:
        stage = bn["stage"]
        drop_count = bn["drop_count"]
        conversion_rate = bn["conversion_rate"]

        if "面談" in stage:
            recommendations.append(
                f"【{stage}】転換率{conversion_rate}%: "
                f"面談設定プロセスの効率化や、リマインド強化を検討してください。"
                f"（{drop_count}名離脱）"
            )
        elif "面接" in stage:
            recommendations.append(
                f"【{stage}】転換率{conversion_rate}%: "
                f"面接対策サポートの充実や、企業とのマッチング精度向上を検討してください。"
                f"（{drop_count}名離脱）"
            )
        elif "内定" in stage:
            recommendations.append(
                f"【{stage}】転換率{conversion_rate}%: "
                f"内定後フォローアップの強化や、条件交渉サポートを検討してください。"
                f"（{drop_count}名離脱）"
            )
        else:
            recommendations.append(
                f"【{stage}】転換率{conversion_rate}%: "
                f"このステップでの離脱原因を分析し、プロセス改善を検討してください。"
                f"（{drop_count}名離脱）"
            )

    return recommendations


@function_tool(name_override="trend_analysis_by_period")
async def trend_analysis_by_period(
    ctx: RunContextWrapper[Any],
    period_type: str = "monthly",
    months_back: int = 6,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """期間別トレンド分析。月次/週次の推移と前期比を確認。"""
    from datetime import datetime, timedelta

    logger.info(
        "[zoho_crm_tools] trend_analysis_by_period: period_type=%s, months_back=%s, channel=%s",
        period_type, months_back, channel
    )

    # パラメータ制限
    months_back = min(months_back, 12)

    try:
        zoho = ZohoClient()
        today = datetime.now()
        trend_data = []

        for i in range(months_back - 1, -1, -1):
            if period_type == "monthly":
                # 月初〜月末
                year = today.year
                month = today.month - i
                while month <= 0:
                    month += 12
                    year -= 1

                period_start = datetime(year, month, 1)
                # 次月の1日 - 1日 = 月末
                if month == 12:
                    period_end = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = datetime(year, month + 1, 1) - timedelta(days=1)
                period_label = f"{year}年{month}月"
            else:  # weekly
                period_start = today - timedelta(weeks=i, days=today.weekday())
                period_end = period_start + timedelta(days=6)
                period_label = f"{period_start.strftime('%m/%d')}週"

            date_from = period_start.strftime("%Y-%m-%d")
            date_to = period_end.strftime("%Y-%m-%d")

            # 流入経路別件数を取得
            if channel:
                results = zoho.search_by_criteria(
                    channel=channel,
                    date_from=date_from,
                    date_to=date_to,
                    limit=200,
                )
                count = len(results)
            else:
                channel_counts = zoho.count_by_channel(
                    date_from=date_from,
                    date_to=date_to,
                )
                count = sum(channel_counts.values())

            trend_data.append({
                "period": period_label,
                "date_from": date_from,
                "date_to": date_to,
                "count": count,
            })

        # 前期比計算
        for i, data in enumerate(trend_data):
            if i == 0:
                data["change"] = None
                data["change_pct"] = None
                data["trend"] = "基準"
            else:
                prev_count = trend_data[i - 1]["count"]
                change = data["count"] - prev_count
                change_pct = round((change / prev_count) * 100, 1) if prev_count > 0 else None

                data["change"] = change
                data["change_pct"] = f"{change_pct:+.1f}%" if change_pct is not None else "N/A"

                if change_pct is not None:
                    if change_pct > 10:
                        data["trend"] = "上昇↑"
                    elif change_pct < -10:
                        data["trend"] = "下降↓"
                    else:
                        data["trend"] = "横ばい→"
                else:
                    data["trend"] = "N/A"

        total_count = sum(d["count"] for d in trend_data)
        avg_count = round(total_count / len(trend_data), 1) if trend_data else 0

        return {
            "success": True,
            "period_type": period_type,
            "channel_filter": channel or "全体",
            "channel_description": CHANNEL_DEFINITIONS.get(channel) if channel else None,
            "trend_data": trend_data,
            "summary": {
                "total_periods": len(trend_data),
                "total_count": total_count,
                "avg_count": avg_count,
            },
        }

    except ZohoAuthError as e:
        logger.error("[zoho_crm_tools] Zoho auth error: %s", e)
        return {
            "success": False,
            "error": "Zoho認証エラーが発生しました。",
        }
    except Exception as e:
        logger.error("[zoho_crm_tools] trend_analysis_by_period error: %s", e)
        return {
            "success": False,
            "error": f"トレンド分析中にエラーが発生しました: {str(e)}",
        }


@function_tool(name_override="compare_channels")
async def compare_channels(
    ctx: RunContextWrapper[Any],
    channels: List[str],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """複数チャネル(2-5個)の比較。獲得数・入社率をランキング。"""
    logger.info(
        "[zoho_crm_tools] compare_channels: channels=%s, date_from=%s, date_to=%s",
        channels, date_from, date_to
    )

    if not channels or len(channels) < 2:
        return {
            "success": False,
            "error": "比較には2つ以上の流入経路を指定してください",
        }

    if len(channels) > 5:
        return {
            "success": False,
            "error": "比較は最大5チャネルまでです",
        }

    try:
        zoho = ZohoClient()
        comparison_data = []

        for channel in channels:
            # ステータス別件数を取得
            status_counts = zoho.count_by_status(
                channel=channel,
                date_from=date_from,
                date_to=date_to,
            )

            total = sum(status_counts.values())
            hired = status_counts.get("14. 入社", 0)
            interview_done = status_counts.get("4. 面談済み", 0)

            comparison_data.append({
                "channel": channel,
                "description": CHANNEL_DEFINITIONS.get(channel, "不明"),
                "total": total,
                "hired": hired,
                "interview_done": interview_done,
                "hire_rate": f"{(hired / total * 100):.1f}%" if total > 0 else "N/A",
                "interview_rate": f"{(interview_done / total * 100):.1f}%" if total > 0 else "N/A",
            })

        # ランキング作成（入社率順）
        ranked_by_hire_rate = sorted(
            comparison_data,
            key=lambda x: x["hired"] / x["total"] if x["total"] > 0 else 0,
            reverse=True,
        )
        for i, item in enumerate(ranked_by_hire_rate):
            item["hire_rate_rank"] = i + 1

        # ランキング（総数順）
        ranked_by_total = sorted(comparison_data, key=lambda x: x["total"], reverse=True)
        for i, item in enumerate(ranked_by_total):
            item["volume_rank"] = i + 1

        return {
            "success": True,
            "period": {
                "from": date_from or "全期間",
                "to": date_to or "現在",
            },
            "comparison": comparison_data,
            "best_by_hire_rate": ranked_by_hire_rate[0]["channel"] if ranked_by_hire_rate else None,
            "best_by_volume": ranked_by_total[0]["channel"] if ranked_by_total else None,
            "insight": _generate_channel_comparison_insight(comparison_data),
        }

    except ZohoAuthError as e:
        logger.error("[zoho_crm_tools] Zoho auth error: %s", e)
        return {"success": False, "error": "Zoho認証エラーが発生しました。"}
    except Exception as e:
        logger.error("[zoho_crm_tools] compare_channels error: %s", e)
        return {"success": False, "error": f"チャネル比較中にエラーが発生しました: {str(e)}"}


def _generate_channel_comparison_insight(data: list) -> str:
    """チャネル比較のインサイトを生成"""
    if not data:
        return "データなし"

    best_hire = max(data, key=lambda x: x["hired"] / x["total"] if x["total"] > 0 else 0)
    best_volume = max(data, key=lambda x: x["total"])

    insights = []
    insights.append(f"入社率が最も高いのは「{best_hire['description']}」({best_hire['hire_rate']})")
    insights.append(f"獲得数が最も多いのは「{best_volume['description']}」({best_volume['total']}件)")

    return " / ".join(insights)


@function_tool(name_override="get_pic_performance")
async def get_pic_performance(
    ctx: RunContextWrapper[Any],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """担当者(PIC)別パフォーマンス。成約率ランキング。"""
    logger.info(
        "[zoho_crm_tools] get_pic_performance: date_from=%s, date_to=%s, channel=%s",
        date_from, date_to, channel
    )

    try:
        zoho = ZohoClient()

        # 全レコードを取得（PICでGROUP BYはCOQLで難しい場合があるため）
        all_records = zoho._fetch_all_records(max_pages=15)
        filtered = zoho._filter_by_date(all_records, date_from, date_to)

        if channel:
            filtered = [r for r in filtered if r.get(zoho.CHANNEL_FIELD_API) == channel]

        # PIC別に集計
        pic_stats: Dict[str, Dict[str, int]] = {}

        for record in filtered:
            owner = record.get("Owner")
            pic_name = owner.get("name") if isinstance(owner, dict) else str(owner) if owner else "未割当"
            status = record.get(zoho.STATUS_FIELD_API)

            if pic_name not in pic_stats:
                pic_stats[pic_name] = {"total": 0, "hired": 0, "interview_done": 0}

            pic_stats[pic_name]["total"] += 1
            if status == "14. 入社":
                pic_stats[pic_name]["hired"] += 1
            if status == "4. 面談済み":
                pic_stats[pic_name]["interview_done"] += 1

        # パフォーマンスデータ作成
        performance_data = []
        for pic_name, stats in pic_stats.items():
            performance_data.append({
                "pic": pic_name,
                "total": stats["total"],
                "hired": stats["hired"],
                "interview_done": stats["interview_done"],
                "hire_rate": f"{(stats['hired'] / stats['total'] * 100):.1f}%" if stats["total"] > 0 else "N/A",
                "interview_rate": f"{(stats['interview_done'] / stats['total'] * 100):.1f}%" if stats["total"] > 0 else "N/A",
            })

        # 入社率でソート
        performance_data.sort(
            key=lambda x: x["hired"] / x["total"] if x["total"] > 0 else 0,
            reverse=True,
        )

        # ランク付け
        for i, item in enumerate(performance_data):
            item["rank"] = i + 1

        return {
            "success": True,
            "period": {
                "from": date_from or "全期間",
                "to": date_to or "現在",
            },
            "channel_filter": channel or "全体",
            "pic_count": len(performance_data),
            "performance_data": performance_data,
            "top_performer": performance_data[0]["pic"] if performance_data else None,
        }

    except ZohoAuthError as e:
        logger.error("[zoho_crm_tools] Zoho auth error: %s", e)
        return {"success": False, "error": "Zoho認証エラーが発生しました。"}
    except Exception as e:
        logger.error("[zoho_crm_tools] get_pic_performance error: %s", e)
        return {"success": False, "error": f"PICパフォーマンス集計中にエラーが発生しました: {str(e)}"}


# エクスポート用のツールリスト
ZOHO_CRM_TOOLS = [
    # 基本検索・取得
    search_job_seekers,
    get_job_seeker_detail,
    get_channel_definitions,
    # 集計・分析（COQL最適化済み）
    aggregate_by_channel,
    count_job_seekers_by_status,
    # 高度な分析ツール（2026-02-03追加）
    analyze_funnel_by_channel,
    trend_analysis_by_period,
    compare_channels,
    get_pic_performance,
]
