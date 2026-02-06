"""
Zoho CRM Tools for Google ADK.

ADK-native tool definitions for Zoho CRM operations.
These are plain Python functions that ADK will automatically wrap.

All tools from OpenAI Agents SDK version have been ported here.
"""

from __future__ import annotations

import functools
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.adk.tools.tool_context import ToolContext

from app.infrastructure.zoho.client import ZohoClient, ZohoAuthError

logger = logging.getLogger(__name__)

# ZohoClient singleton
_zoho_client_instance = None


def _get_zoho_client():
    """ZohoClient シングルトン取得。"""
    global _zoho_client_instance
    if _zoho_client_instance is None:
        _zoho_client_instance = ZohoClient()
    return _zoho_client_instance


# TTL cache for all records
_all_records_cache = None
_all_records_cache_time = 0
_ALL_RECORDS_CACHE_TTL = 300  # 5分


def _get_cached_all_records():
    """全レコードのTTLキャッシュ。5分間有効。"""
    global _all_records_cache, _all_records_cache_time
    now = time.time()
    if _all_records_cache is not None and (now - _all_records_cache_time) < _ALL_RECORDS_CACHE_TTL:
        return _all_records_cache
    zoho = _get_zoho_client()
    _all_records_cache = zoho._fetch_all_records()
    _all_records_cache_time = now
    return _all_records_cache


def _retry_transient(max_retries: int = 2, delay: float = 1.0):
    """一時的エラーの自動リトライデコレータ（指数バックオフ）。"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    # 認証エラーやバリデーションエラーはリトライしない
                    if any(kw in error_str for kw in ["auth", "invalid", "not found", "permission"]):
                        raise
                    if attempt < max_retries:
                        import time as _time
                        _time.sleep(delay * (2 ** attempt))
                        logger.warning(f"[zoho_crm_tools] Retry {attempt+1}/{max_retries} for {func.__name__}: {e}")
            raise last_error
        return wrapper
    return decorator


# Channel definitions
CHANNEL_DEFINITIONS = {
    # Scout channels
    "sco_bizreach": "BizReachスカウト経由で獲得したリード",
    "sco_dodaX": "dodaXスカウト経由で獲得したリード",
    "sco_ambi": "Ambiスカウト経由で獲得したリード",
    "sco_rikunavi": "リクナビスカウト経由で獲得したリード",
    "sco_nikkei": "日経転職版スカウト経由で獲得したリード",
    "sco_liiga": "外資就活ネクストスカウト経由で獲得したリード",
    "sco_openwork": "OpenWorkスカウト経由で獲得したリード",
    "sco_carinar": "Carinarスカウト経由で獲得したリード",
    "sco_dodaX_D&P": "dodaXダイヤモンド/プラチナスカウト経由で獲得したリード",
    # Paid advertising
    "paid_google": "Googleリスティング広告経由で獲得したリード",
    "paid_meta": "Meta広告（Facebook/Instagram）経由で獲得したリード",
    "paid_affiliate": "アフィリエイト広告経由で獲得したリード",
    # Organic
    "org_hitocareer": "SEOメディア（hitocareer）経由で獲得したリード",
    "org_jobs": "自社求人サイト経由で獲得したリード",
    # Others
    "feed_indeed": "Indeed経由で獲得したリード",
    "referral": "紹介経由で獲得したリード",
    "other": "その他",
}

# Status definitions
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


def get_channel_definitions() -> Dict[str, Any]:
    """流入経路(channel)とステータス(status)の定義一覧を取得。

    Returns:
        Dict[str, Any]: チャネル・ステータス定義。
            success: True/False
            channels: チャネル定義辞書
            statuses: ステータス定義辞書
    """
    return {
        "success": True,
        "channels": CHANNEL_DEFINITIONS,
        "statuses": STATUS_DEFINITIONS,
        "usage_hint": "search_job_seekers や aggregate_by_channel で使用できる流入経路コードの一覧です。",
    }


def search_job_seekers(
    channel: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """求職者を検索。channel/statusの定義はget_channel_definitionsで取得。

    Args:
        channel: 流入経路(paid_meta, sco_bizreach等)
        status: ステータス("1. リード"等)
        name: 名前(部分一致)
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)
        limit: 件数(max100)

    Returns:
        Dict[str, Any]: 検索結果。
            success: True/False
            total: ヒット件数
            records: 求職者レコードリスト
            filters_applied: 適用したフィルタ
    """
    logger.info(f"[ADK Zoho] search_job_seekers: channel={channel}, status={status}")

    try:
        zoho = _get_zoho_client()
        results = zoho.search_by_criteria(
            channel=channel,
            status=status,
            name=name,
            date_from=date_from,
            date_to=date_to,
            limit=min(limit, 100),
        )

        # Track candidate search patterns in user state
        if tool_context and results:
            try:
                searches = tool_context.state.get("user:recent_candidate_searches", [])
                search_record = {
                    "filters": {k: v for k, v in {
                        "channel": channel, "status": status, "name": name,
                    }.items() if v is not None},
                    "result_count": len(results),
                }
                searches = searches + [search_record]
                if len(searches) > 10:
                    searches = searches[-10:]
                tool_context.state["user:recent_candidate_searches"] = searches
            except Exception:
                pass

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
        logger.error(f"[ADK Zoho] Auth error: {e}")
        return {"success": False, "error": "認証エラー。管理者に連絡してください。"}
    except Exception as e:
        logger.error(f"[ADK Zoho] Error: {e}")
        return {"success": False, "error": str(e)}


def get_job_seeker_detail(record_id: str, tool_context: ToolContext = None) -> Dict[str, Any]:
    """特定求職者1名の詳細取得。日本語ラベル付き整形済みデータを返す。

    Args:
        record_id: Zoho CRMのレコードID

    Returns:
        success: True/False
        record_id: レコードID
        record: 整形済み求職者データ（日本語ラベル）
    """
    logger.info(f"[ADK Zoho] get_job_seeker_detail: record_id={record_id}")

    if not record_id:
        return {"success": False, "error": "record_idが指定されていません"}

    try:
        zoho = _get_zoho_client()
        record = zoho.get_app_hc_record(record_id)

        if not record:
            return {"success": False, "error": f"レコードが見つかりません: {record_id}"}

        # Track viewed candidates in user state
        if tool_context:
            try:
                viewed = tool_context.state.get("user:viewed_candidates", [])
                name = record.get("Name", record_id)
                entry = {"record_id": record_id, "name": name}
                # Avoid duplicates by record_id
                existing_ids = {v.get("record_id") for v in viewed if isinstance(v, dict)}
                if record_id not in existing_ids:
                    viewed = viewed + [entry]
                    if len(viewed) > 30:
                        viewed = viewed[-30:]
                    tool_context.state["user:viewed_candidates"] = viewed
            except Exception:
                pass

        return {
            "success": True,
            "record_id": record_id,
            "record": _format_job_seeker_detail(record),
        }
    except ZohoAuthError as e:
        return {"success": False, "error": "認証エラー"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_job_seekers_batch(record_ids: List[str]) -> Dict[str, Any]:
    """複数求職者の詳細を一括取得（COQLでIN句使用、最大50件）。

    Args:
        record_ids: 取得するrecord_idのリスト（最大50件）

    Returns:
        Dict[str, Any]: 一括取得結果。
            success: True/False
            total: 取得件数
            records: 求職者レコードリスト（整形済み）
    """
    logger.info(f"[ADK Zoho] get_job_seekers_batch: {len(record_ids)} records")

    if not record_ids:
        return {"success": False, "error": "record_idsが空です"}

    if len(record_ids) > 50:
        return {"success": False, "error": "最大50件まで指定可能です"}

    try:
        zoho = _get_zoho_client()
        records = zoho.get_app_hc_records_batch(record_ids)

        formatted = [_format_job_seeker_detail(r) for r in records]
        return {
            "success": True,
            "total": len(formatted),
            "records": formatted,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _format_job_seeker_detail(record: Dict[str, Any]) -> Dict[str, Any]:
    """Zohoレコードを読みやすい形式に整形"""
    owner = record.get("Owner")
    pic_name = owner.get("name") if isinstance(owner, dict) else str(owner) if owner else "未割当"

    return {
        "record_id": record.get("id"),
        "求職者名": record.get("Name"),
        "流入経路": record.get("field14"),
        "顧客ステータス": record.get("field19"),
        "PIC": pic_name,
        "登録日": record.get("field18"),
        "更新日": record.get("Modified_Time"),
        "年齢": record.get("field15"),
        "性別": record.get("field16"),
        "現年収": record.get("field17"),
        "希望年収": record.get("field20"),
        "経験業種": record.get("field21"),
        "経験職種": record.get("field22"),
        "希望業種": record.get("field23"),
        "希望職種": record.get("field24"),
        "転職希望時期": record.get("field66"),
        "現職状況": record.get("field67"),
        "職歴": record.get("field85"),
    }


def aggregate_by_channel(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """流入経路別の求職者数を集計。広告効果分析に使用。

    Args:
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)

    Returns:
        Dict[str, Any]: チャネル別集計。
            success: True/False
            period: 集計期間
            by_category: カテゴリ別集計（スカウト系・有料広告系等）
            category_totals: カテゴリ別合計
            total: 総数
    """
    logger.info(f"[ADK Zoho] aggregate_by_channel: {date_from} to {date_to}")

    try:
        zoho = _get_zoho_client()
        results = zoho.count_by_channel(date_from=date_from, date_to=date_to)

        # Categorize by channel type
        enriched: Dict[str, Any] = {
            "スカウト系": {},
            "有料広告系": {},
            "自然流入系": {},
            "その他": {},
        }

        for channel, count in results.items():
            item = {"count": count, "description": CHANNEL_DEFINITIONS.get(channel, "不明")}
            if channel.startswith("sco_"):
                enriched["スカウト系"][channel] = item
            elif channel.startswith("paid_"):
                enriched["有料広告系"][channel] = item
            elif channel.startswith("org_"):
                enriched["自然流入系"][channel] = item
            else:
                enriched["その他"][channel] = item

        category_totals = {
            category: sum(item["count"] for item in items.values())
            for category, items in enriched.items()
        }

        return {
            "success": True,
            "period": {"from": date_from or "全期間", "to": date_to or "現在"},
            "by_category": enriched,
            "category_totals": category_totals,
            "total": sum(results.values()),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def count_job_seekers_by_status(
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """ステータス別集計(ファネル分析用)。channelで絞込可。

    全チャネル横断のステータス分布。特定チャネルの深堀りはanalyze_funnel_by_channelを使用。

    Args:
        channel: 流入経路でフィルタ
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)

    Returns:
        Dict[str, Any]: ステータス別集計。
            success: True/False
            channel_filter: 適用したチャネル
            by_status: ステータス別カウント
            total: 総数
            funnel_analysis: ファネル分析（面談率・入社率等）
    """
    logger.info(f"[ADK Zoho] count_by_status: channel={channel}")

    try:
        zoho = _get_zoho_client()
        results = zoho.count_by_status(
            channel=channel, date_from=date_from, date_to=date_to
        )

        enriched = {
            status: {"count": count, "description": STATUS_DEFINITIONS.get(status, "不明")}
            for status, count in results.items()
        }

        total = sum(results.values())
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
            "period": {"from": date_from or "全期間", "to": date_to or "現在"},
            "by_status": enriched,
            "total": total,
            "funnel_analysis": funnel_analysis,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_funnel_by_channel(
    channel: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """特定channelのファネル分析。転換率とボトルネックを特定。

    特定チャネルの詳細ファネル分析。全体俯瞰はcount_job_seekers_by_statusを使用。

    Args:
        channel: 流入経路(必須)
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)

    Returns:
        Dict[str, Any]: ファネル分析結果。
            success: True/False
            channel: 分析対象チャネル
            funnel_data: ステージ別データ（転換率・離脱率）
            bottlenecks: ボトルネック箇所リスト
            kpis: KPI指標
    """
    logger.info(f"[ADK Zoho] analyze_funnel_by_channel: channel={channel}")

    if not channel:
        return {"success": False, "error": "流入経路（channel）を指定してください"}

    try:
        zoho = _get_zoho_client()
        status_counts = zoho.count_by_status(
            channel=channel, date_from=date_from, date_to=date_to
        )

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

        return {
            "success": True,
            "channel": channel,
            "channel_description": CHANNEL_DEFINITIONS.get(channel, "不明"),
            "period": {"from": date_from or "全期間", "to": date_to or "現在"},
            "funnel_data": funnel_data,
            "bottlenecks": bottlenecks,
            "kpis": kpis,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def trend_analysis_by_period(
    period_type: str = "monthly",
    months_back: int = 6,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """期間別トレンド分析。月次/週次の推移と前期比を確認。

    Args:
        period_type: "monthly" または "weekly" または "quarterly"。それ以外はエラー。
        months_back: 何ヶ月/週遡るか（max 12）
        channel: 流入経路でフィルタ

    Returns:
        Dict[str, Any]: トレンド分析結果。
            success: True/False
            period_type: 分析期間タイプ
            trend_data: 期間別データ（前期比・増減率）
            summary: 集計サマリ
    """
    logger.info(f"[ADK Zoho] trend_analysis_by_period: {period_type}, {months_back}ヶ月")

    # Validate period_type
    valid_periods = {"weekly", "monthly", "quarterly"}
    if period_type not in valid_periods:
        return {"success": False, "error": f"period_typeは {valid_periods} のいずれかを指定してください"}

    months_back = min(months_back, 12)

    try:
        zoho = _get_zoho_client()
        today = datetime.now()

        all_records = _get_cached_all_records()

        if channel:
            all_records = [r for r in all_records if r.get(zoho.CHANNEL_FIELD_API) == channel]

        periods = []
        for i in range(months_back - 1, -1, -1):
            if period_type == "monthly":
                year = today.year
                month = today.month - i
                while month <= 0:
                    month += 12
                    year -= 1

                period_start = datetime(year, month, 1)
                if month == 12:
                    period_end = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = datetime(year, month + 1, 1) - timedelta(days=1)
                period_label = f"{year}年{month}月"
            else:
                period_start = today - timedelta(weeks=i, days=today.weekday())
                period_end = period_start + timedelta(days=6)
                period_label = f"{period_start.strftime('%m/%d')}週"

            periods.append({
                "label": period_label,
                "start": period_start.strftime("%Y-%m-%d"),
                "end": period_end.strftime("%Y-%m-%d"),
            })

        trend_data = []
        for period in periods:
            date_from = period["start"]
            date_to = period["end"]

            count = 0
            for record in all_records:
                reg_date = record.get(zoho.DATE_FIELD_API)
                if reg_date:
                    if date_from and reg_date < date_from:
                        continue
                    if date_to and reg_date > date_to:
                        continue
                    count += 1

            trend_data.append({
                "period": period["label"],
                "date_from": date_from,
                "date_to": date_to,
                "count": count,
            })

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
    except Exception as e:
        return {"success": False, "error": str(e)}


def compare_channels(
    channels: List[str],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """複数チャネル(2-5個)の比較。獲得数・入社率をランキング。

    Args:
        channels: 比較するチャネルのリスト（2-5個）
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)

    Returns:
        Dict[str, Any]: チャネル比較結果。
            success: True/False
            period: 比較期間
            comparison: チャネル別データ（ランキング付き）
            best_by_hire_rate: 入社率トップチャネル
            best_by_volume: 獲得数トップチャネル
    """
    logger.info(f"[ADK Zoho] compare_channels: {channels}")

    if not channels or len(channels) < 2:
        return {"success": False, "error": "比較には2つ以上の流入経路を指定してください"}

    if len(channels) > 5:
        return {"success": False, "error": "比較は最大5チャネルまでです"}

    try:
        zoho = _get_zoho_client()

        all_records = _get_cached_all_records()
        filtered = zoho._filter_by_date(all_records, date_from, date_to)

        channel_stats: Dict[str, Dict[str, int]] = {ch: {} for ch in channels}

        for record in filtered:
            ch = record.get(zoho.CHANNEL_FIELD_API)
            if ch not in channels:
                continue

            status = record.get(zoho.STATUS_FIELD_API)
            if status:
                channel_stats[ch][status] = channel_stats[ch].get(status, 0) + 1

        comparison_data = []
        for channel in channels:
            status_counts = channel_stats.get(channel, {})
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

        ranked_by_hire_rate = sorted(
            comparison_data,
            key=lambda x: x["hired"] / x["total"] if x["total"] > 0 else 0,
            reverse=True,
        )
        for i, item in enumerate(ranked_by_hire_rate):
            item["hire_rate_rank"] = i + 1

        ranked_by_total = sorted(comparison_data, key=lambda x: x["total"], reverse=True)
        for i, item in enumerate(ranked_by_total):
            item["volume_rank"] = i + 1

        return {
            "success": True,
            "period": {"from": date_from or "全期間", "to": date_to or "現在"},
            "comparison": comparison_data,
            "best_by_hire_rate": ranked_by_hire_rate[0]["channel"] if ranked_by_hire_rate else None,
            "best_by_volume": ranked_by_total[0]["channel"] if ranked_by_total else None,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_pic_performance(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """担当者(PIC)別パフォーマンス。成約率ランキング。

    Args:
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)
        channel: 流入経路でフィルタ

    Returns:
        Dict[str, Any]: PIC別パフォーマンス。
            success: True/False
            period: 分析期間
            pic_count: PIC数
            performance_data: PIC別データ（ランキング付き）
            top_performer: トップPIC
    """
    logger.info(f"[ADK Zoho] get_pic_performance: channel={channel}")

    try:
        zoho = _get_zoho_client()

        all_records = _get_cached_all_records()
        filtered = zoho._filter_by_date(all_records, date_from, date_to)

        if channel:
            filtered = [r for r in filtered if r.get(zoho.CHANNEL_FIELD_API) == channel]

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

        performance_data.sort(
            key=lambda x: x["hired"] / x["total"] if x["total"] > 0 else 0,
            reverse=True,
        )

        for i, item in enumerate(performance_data):
            item["rank"] = i + 1

        return {
            "success": True,
            "period": {"from": date_from or "全期間", "to": date_to or "現在"},
            "channel_filter": channel or "全体",
            "pic_count": len(performance_data),
            "performance_data": performance_data,
            "top_performer": performance_data[0]["pic"] if performance_data else None,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_conversion_metrics(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """全チャネル横断のコンバージョン指標を一括取得。チャネル別の獲得数・面談率・内定率・入社率を比較。

    compare_channelsとの違い：こちらは全チャネルのKPIを自動計算。
    compare_channelsは特定チャネル同士の詳細比較。

    Args:
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)

    Returns:
        Dict[str, Any]: 全チャネルKPI。
            success: True/False
            period: 分析期間
            metrics: チャネル別KPI（獲得数、面談率、内定率、入社率、CPA推計）
            ranking: 入社率ランキング
            recommendations: 改善推奨
    """
    logger.info(f"[ADK Zoho] get_conversion_metrics: {date_from} to {date_to}")

    try:
        zoho = _get_zoho_client()
        all_records = _get_cached_all_records()
        filtered = zoho._filter_by_date(all_records, date_from, date_to)

        # Aggregate status counts per channel
        channel_stats: Dict[str, Dict[str, int]] = {}

        for record in filtered:
            ch = record.get(zoho.CHANNEL_FIELD_API)
            if not ch:
                continue

            if ch not in channel_stats:
                channel_stats[ch] = {}

            status = record.get(zoho.STATUS_FIELD_API)
            if status:
                channel_stats[ch][status] = channel_stats[ch].get(status, 0) + 1

        # Build metrics per channel
        metrics = []
        for ch, status_counts in channel_stats.items():
            total = sum(status_counts.values())
            if total == 0:
                continue

            interview_done = status_counts.get("4. 面談済み", 0)
            offer = status_counts.get("12. 内定", 0) + status_counts.get("13. 内定承諾", 0)
            hired = status_counts.get("14. 入社", 0)

            # Calculate cumulative counts (candidates who reached at least this stage)
            # For funnel: someone with "14. 入社" also passed through "4. 面談済み"
            # But since Zoho stores current status, we need cumulative counts
            interview_plus = sum(
                cnt for st, cnt in status_counts.items()
                if st >= "4. 面談済み" and st < "16. クローズ"
            )
            offer_plus = sum(
                cnt for st, cnt in status_counts.items()
                if st >= "12. 内定" and st <= "14. 入社"
            )
            hired_count = status_counts.get("14. 入社", 0)

            interview_rate = round((interview_plus / total) * 100, 1) if total > 0 else 0
            offer_rate = round((offer_plus / total) * 100, 1) if total > 0 else 0
            hire_rate = round((hired_count / total) * 100, 1) if total > 0 else 0

            # Category
            if ch.startswith("sco_"):
                category = "スカウト"
            elif ch.startswith("paid_"):
                category = "有料広告"
            elif ch.startswith("org_"):
                category = "自然流入"
            else:
                category = "その他"

            metrics.append({
                "channel": ch,
                "description": CHANNEL_DEFINITIONS.get(ch, "不明"),
                "category": category,
                "total": total,
                "interview_rate": f"{interview_rate}%",
                "offer_rate": f"{offer_rate}%",
                "hire_rate": f"{hire_rate}%",
                "hired_count": hired_count,
                "_hire_rate_num": hire_rate,  # for sorting
            })

        # Sort by hire rate descending for ranking
        metrics.sort(key=lambda x: x["_hire_rate_num"], reverse=True)

        ranking = []
        for i, m in enumerate(metrics):
            ranking.append({
                "rank": i + 1,
                "channel": m["channel"],
                "description": m["description"],
                "hire_rate": m["hire_rate"],
                "hired_count": m["hired_count"],
                "total": m["total"],
            })

        # Remove internal sort key
        for m in metrics:
            del m["_hire_rate_num"]

        # Generate recommendations
        recommendations = []

        if ranking:
            top = ranking[0]
            recommendations.append(
                f"入社率トップは{top['description']}（{top['hire_rate']}）。"
                f"このチャネルの成功パターンを他チャネルに横展開を推奨。"
            )

        # Find channels with high volume but low conversion
        high_vol_low_conv = [
            m for m in metrics
            if m["total"] >= 10 and float(m["hire_rate"].replace("%", "")) < 3.0
        ]
        if high_vol_low_conv:
            names = ", ".join(m["description"] for m in high_vol_low_conv[:3])
            recommendations.append(
                f"獲得数は多いが入社率が低いチャネル: {names}。ファネル改善を優先。"
            )

        # Category-level summary
        category_summary: Dict[str, Dict[str, Any]] = {}
        for m in metrics:
            cat = m["category"]
            if cat not in category_summary:
                category_summary[cat] = {"total": 0, "hired": 0, "channels": 0}
            category_summary[cat]["total"] += m["total"]
            category_summary[cat]["hired"] += m["hired_count"]
            category_summary[cat]["channels"] += 1

        for cat, data in category_summary.items():
            data["hire_rate"] = (
                f"{round((data['hired'] / data['total']) * 100, 1)}%"
                if data["total"] > 0 else "N/A"
            )

        overall_total = sum(m["total"] for m in metrics)
        overall_hired = sum(m["hired_count"] for m in metrics)

        return {
            "success": True,
            "period": {"from": date_from or "全期間", "to": date_to or "現在"},
            "overall": {
                "total": overall_total,
                "hired": overall_hired,
                "hire_rate": f"{round((overall_hired / overall_total) * 100, 1)}%" if overall_total > 0 else "N/A",
            },
            "category_summary": category_summary,
            "metrics": metrics,
            "ranking": ranking[:10],
            "recommendations": recommendations,
        }

    except Exception as e:
        logger.error(f"[ADK Zoho] get_conversion_metrics error: {e}")
        return {"success": False, "error": str(e)}


# List of ADK-compatible tools - ALL tools from OpenAI SDK version
ADK_ZOHO_CRM_TOOLS = [
    # Basic search and retrieval
    get_channel_definitions,
    search_job_seekers,
    get_job_seeker_detail,
    get_job_seekers_batch,
    # Aggregation and analysis (COQL optimized)
    aggregate_by_channel,
    count_job_seekers_by_status,
    # Advanced analysis tools
    analyze_funnel_by_channel,
    trend_analysis_by_period,
    compare_channels,
    get_pic_performance,
    get_conversion_metrics,
]
