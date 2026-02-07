"""
Zoho CRM Tools for Google ADK.

3層アーキテクチャ:
  Tier 1 (メタデータ発見): list_crm_modules, get_module_schema, get_module_layout
  Tier 2 (汎用クエリ): query_crm_records, aggregate_crm_data, get_record_detail, get_related_records
  Tier 3 (専門分析): analyze_funnel_by_channel, trend_analysis_by_period, compare_channels,
                     get_pic_performance, get_conversion_metrics

Tier 1/2: 全CRMモジュールに動的アクセス（フィールドやモジュールをハードコードしない）
Tier 3: jobSeekerモジュール専用の高度なビジネス分析（ファネル・トレンド・チャネル比較）
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


# TTL cache for all jobSeeker records (Tier 3 specialized tools用)
_all_records_cache = None
_all_records_cache_time = 0
_ALL_RECORDS_CACHE_TTL = 300  # 5分


def _get_cached_all_records():
    """全jobSeekerレコードのTTLキャッシュ。5分間有効。"""
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
                    if any(kw in error_str for kw in ["auth", "invalid", "not found", "permission"]):
                        raise
                    if attempt < max_retries:
                        import time as _time
                        _time.sleep(delay * (2 ** attempt))
                        logger.warning(f"[zoho_crm_tools] Retry {attempt+1}/{max_retries} for {func.__name__}: {e}")
            raise last_error
        return wrapper
    return decorator


# チャネルカテゴリ定義（Tier 3内部用）
_CHANNEL_CATEGORIES = {
    "sco_": "スカウト",
    "paid_": "有料広告",
    "org_": "自然流入",
    "feed_": "求人フィード",
}


def _categorize_channel(channel: str) -> str:
    """チャネルコードからカテゴリを判定。"""
    if not channel:
        return "不明"
    for prefix, category in _CHANNEL_CATEGORIES.items():
        if channel.startswith(prefix):
            return category
    if channel == "referral":
        return "紹介"
    return "その他"


# ファネルステージ定義（ビジネスロジック、Tier 3用）
_FUNNEL_STAGES = [
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


def _clean_lookup_fields(record: Dict[str, Any], strip_empty: bool = False) -> Dict[str, Any]:
    """ルックアップフィールドを展開し、$系システムフィールドを除去。

    Args:
        record: Zohoレコード
        strip_empty: Trueの場合、null/空文字/空リストのフィールドも除去（トークン節約）
    """
    cleaned = {}
    for k, v in record.items():
        if k.startswith("$"):
            continue
        # Strip empty values when requested
        if strip_empty and (v is None or v == "" or v == [] or v == {}):
            continue
        if isinstance(v, dict) and "name" in v and "id" in v and len(v) <= 3:
            cleaned[k] = v.get("name")
            cleaned[f"{k}_id"] = v.get("id")
        else:
            cleaned[k] = v
    return cleaned


# ============================================================
# Tier 1: メタデータ発見ツール
# ============================================================

def list_crm_modules(
    include_record_counts: bool = False,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """Zoho CRMの全モジュール（タブ）一覧を取得。

    どのモジュールが利用可能か、どんなデータが入っているかを確認する起点ツール。
    初めてCRMを探索するときに最初に呼ぶこと。

    Args:
        include_record_counts: Trueにすると各モジュールのレコード件数も取得（やや遅い）

    Returns:
        success: True/False
        modules: モジュール一覧（api_name, label, type）
        total_modules: モジュール総数
        hint: 次に使うべきツールのヒント
    """
    logger.info(f"[ADK Zoho] list_crm_modules: counts={include_record_counts}")

    try:
        zoho = _get_zoho_client()
        modules = zoho.list_modules()

        # API対応モジュールのみ
        api_modules = [m for m in modules if m.get("api_supported")]

        result_modules = []
        for m in api_modules:
            entry = {
                "api_name": m["api_name"],
                "label": m.get("label") or m.get("singular_label"),
                "type": m.get("generated_type"),
            }
            if include_record_counts:
                try:
                    count_result = zoho._coql_query(
                        f"SELECT COUNT(id) FROM {m['api_name']} WHERE id is not null"
                    )
                    data = count_result.get("data") or []
                    entry["record_count"] = data[0].get("COUNT(id)", 0) if data else 0
                except Exception:
                    entry["record_count"] = "取得不可"
            result_modules.append(entry)

        return {
            "success": True,
            "modules": result_modules,
            "total_modules": len(result_modules),
            "hint": "get_module_schemaでフィールド構造を確認し、query_crm_recordsでデータを取得できます。",
        }
    except ZohoAuthError:
        return {"success": False, "error": "認証エラー。管理者に連絡してください。"}
    except Exception as e:
        logger.error(f"[ADK Zoho] list_crm_modules error: {e}")
        return {"success": False, "error": str(e)}


# Picklist compression settings
_MAX_PICKLIST_VALUES = 20  # Max picklist values per field (reduces ~500→20)


def _deduplicate_picklist_values(values: list) -> list:
    """Deduplicate composite picklist values like '「X」×「Y」'.

    Zoho picklists often contain cross-product duplicates:
    - '「マイナビ転職」×「マイナビ転職」' → just keep 'マイナビ転職'
    - Both '有料_meta_lead' and '有料_meta_lead×スカウト' → keep unique base values
    """
    if not values:
        return values

    seen = set()
    unique = []
    for v in values:
        if not isinstance(v, str):
            unique.append(v)
            continue
        # Extract base value from composite format: '「A」×「B」' or 'A×B'
        # For cross-product values, keep only unique base parts
        base = v.split("×")[0].strip().strip("「」")
        if base and base not in seen:
            seen.add(base)
            unique.append(v.split("×")[0].strip() if "×" in v else v)
        elif not base:
            unique.append(v)
    return unique


def get_module_schema(
    module_api_name: str,
    include_picklist_values: bool = True,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """モジュールのフィールド構造（スキーマ）を取得。

    各フィールドのAPI名、表示名、データ型、ピックリスト選択肢、ルックアップ先を返す。
    query_crm_recordsでSELECT/WHERE句に使うフィールド名を確認するために必須。

    Args:
        module_api_name: モジュールAPI名（例: "jobSeeker", "JOB", "HRBP", "Contacts"）
        include_picklist_values: ピックリストの選択肢一覧も含めるか

    Returns:
        success: True/False
        module: モジュール名
        total_fields: フィールド総数
        fields: フィールド一覧（api_name, display_label, data_type, pick_list_values, lookup_module）
        picklist_summary: ピックリストフィールドの要約
        lookup_summary: ルックアップフィールドの要約
    """
    logger.info(f"[ADK Zoho] get_module_schema: module={module_api_name}")

    if not module_api_name:
        return {"success": False, "error": "module_api_nameを指定してください"}

    try:
        zoho = _get_zoho_client()
        fields = zoho.list_fields_rich(module_api_name)

        output_fields = []
        picklist_fields = []
        lookup_fields = []

        for f in fields:
            entry = {
                "api_name": f["api_name"],
                "display_label": f.get("display_label"),
                "data_type": f.get("data_type"),
            }

            dt = f.get("data_type", "")
            if dt in ("picklist", "multiselectpicklist") and include_picklist_values:
                raw_vals = f.get("pick_list_values", [])
                # Deduplicate composite values then cap at _MAX_PICKLIST_VALUES
                deduped = _deduplicate_picklist_values(raw_vals)
                capped = deduped[:_MAX_PICKLIST_VALUES]
                entry["pick_list_values"] = capped
                if len(deduped) > _MAX_PICKLIST_VALUES:
                    entry["pick_list_total"] = len(raw_vals)
                picklist_fields.append({
                    "api_name": f["api_name"],
                    "display_label": f.get("display_label"),
                    "value_count": len(raw_vals),
                    "values": capped,
                })
            elif dt == "lookup":
                lk_module = f.get("lookup_module")
                entry["lookup_module"] = lk_module
                lookup_fields.append({
                    "api_name": f["api_name"],
                    "display_label": f.get("display_label"),
                    "lookup_module": lk_module,
                })

            output_fields.append(entry)

        return {
            "success": True,
            "module": module_api_name,
            "total_fields": len(output_fields),
            "fields": output_fields,
            "picklist_summary": picklist_fields if picklist_fields else None,
            "lookup_summary": lookup_fields if lookup_fields else None,
        }
    except ZohoAuthError:
        return {"success": False, "error": "認証エラー。管理者に連絡してください。"}
    except Exception as e:
        logger.error(f"[ADK Zoho] get_module_schema error: {e}")
        return {"success": False, "error": str(e)}


def get_module_layout(
    module_api_name: str,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """モジュールのレイアウト（セクション構造・フィールド配置）を取得。

    UIでどのフィールドがどのセクションにグループ化されているかを確認。
    フィールドの論理的なまとまり（基本情報、ステータス、面談内容、企業提案検索等）を理解するのに便利。

    Args:
        module_api_name: モジュールAPI名（例: "jobSeeker", "JOB"）

    Returns:
        success: True/False
        module: モジュール名
        layouts: レイアウト一覧（name, sections[{display_label, field_count, fields}]）
    """
    logger.info(f"[ADK Zoho] get_module_layout: module={module_api_name}")

    if not module_api_name:
        return {"success": False, "error": "module_api_nameを指定してください"}

    try:
        zoho = _get_zoho_client()
        layouts = zoho.get_layouts(module_api_name)

        return {
            "success": True,
            "module": module_api_name,
            "layouts": layouts,
        }
    except ZohoAuthError:
        return {"success": False, "error": "認証エラー。管理者に連絡してください。"}
    except Exception as e:
        logger.error(f"[ADK Zoho] get_module_layout error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# Tier 2: 汎用クエリツール
# ============================================================

@_retry_transient(max_retries=2)
def query_crm_records(
    module: str,
    fields: str,
    where: Optional[str] = None,
    order_by: Optional[str] = None,
    limit: int = 50,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """任意モジュールのレコードをCOQL（SQL風クエリ）で検索・取得。

    フィールド名はget_module_schemaで確認してから使用すること。
    ピックリスト値はget_module_schemaのpick_list_valuesから確認可能。

    COQL仕様:
    - WHERE句: =, !=, >, <, >=, <=, like '%値%', in ('a','b'), is null, is not null
    - ORDER BY: ASC/DESC
    - LIMIT: 最大2000
    - ルックアップJOIN: Owner.name, field64.Account_Name のようにドット記法で参照可能

    Args:
        module: モジュールAPI名（例: "jobSeeker", "JOB", "HRBP", "Contacts"）
        fields: カンマ区切りのフィールドAPI名（例: "id, Name, customer_status, field14"）
        where: WHERE条件（例: "customer_status = '4. 面談済み' AND field14 = 'sco_bizreach'"）
        order_by: ソート（例: "Modified_Time DESC"）
        limit: 取得件数（1-2000、デフォルト50）

    Returns:
        success: True/False
        module: 対象モジュール
        total: 取得件数
        records: レコードリスト
        has_more: さらにデータがあるか
        query: 実行したCOQLクエリ（デバッグ用）
    """
    logger.info(f"[ADK Zoho] query_crm_records: module={module}, fields={fields[:80] if fields else ''}")

    if not module:
        return {"success": False, "error": "moduleを指定してください"}
    if not fields:
        return {"success": False, "error": "fieldsを指定してください（例: 'id, Name, Modified_Time'）"}

    try:
        zoho = _get_zoho_client()
        effective_limit = max(1, min(limit, 2000))

        # COQL構築
        query = f"SELECT {fields} FROM {module}"
        if where:
            query += f" WHERE {where}"
        else:
            query += " WHERE id is not null"
        if order_by:
            query += f" ORDER BY {order_by}"
        query += f" LIMIT {effective_limit}"

        result = zoho.generic_coql_query(query, limit=effective_limit)
        data = result.get("data") or []
        info = result.get("info") or {}

        cleaned_records = [_clean_lookup_fields(rec) for rec in data]

        # State tracking
        if tool_context:
            try:
                queries = tool_context.state.get("user:recent_crm_queries", [])
                queries = queries + [{"module": module, "where": where, "count": len(data)}]
                if len(queries) > 20:
                    queries = queries[-20:]
                tool_context.state["user:recent_crm_queries"] = queries
            except Exception:
                pass

        return {
            "success": True,
            "module": module,
            "total": len(cleaned_records),
            "records": cleaned_records,
            "has_more": info.get("more_records", False),
            "query": query,
        }
    except ZohoAuthError:
        return {"success": False, "error": "認証エラー。管理者に連絡してください。"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"[ADK Zoho] query_crm_records error: {e}")
        return {"success": False, "error": str(e)}


@_retry_transient(max_retries=2)
def aggregate_crm_data(
    module: str,
    group_by: str,
    aggregate: str = "COUNT(id)",
    where: Optional[str] = None,
    order_by: Optional[str] = None,
    limit: int = 200,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """任意モジュールの集計をCOQL GROUP BYで実行。

    チャネル別・ステータス別・担当者別などの件数・集計を高速に取得。
    クロス集計も最大4フィールドまでGROUP BY可能。

    COQL GROUP BY仕様:
    - 集計関数: COUNT(id), SUM(field), MAX(field), MIN(field)
    - GROUP BY: 最大4フィールド
    - WHERE条件併用可

    Args:
        module: モジュールAPI名（例: "jobSeeker"）
        group_by: GROUP BYフィールド（カンマ区切り、例: "customer_status" or "field14, customer_status"）
        aggregate: 集計式（デフォルト: "COUNT(id)"。"SUM(field17)"など数値フィールドも可）
        where: WHERE条件（例: "field14 = 'sco_bizreach'"）
        order_by: ソート（例: "customer_status ASC"）
        limit: 最大行数（デフォルト200）

    Returns:
        success: True/False
        module: 対象モジュール
        total_groups: グループ数
        data: 集計結果リスト
        query: 実行したCOQLクエリ
    """
    logger.info(f"[ADK Zoho] aggregate_crm_data: module={module}, group_by={group_by}")

    if not module:
        return {"success": False, "error": "moduleを指定してください"}
    if not group_by:
        return {"success": False, "error": "group_byを指定してください（例: 'customer_status'）"}

    try:
        zoho = _get_zoho_client()
        effective_limit = max(1, min(limit, 2000))

        query = f"SELECT {aggregate}, {group_by} FROM {module}"
        if where:
            query += f" WHERE {where}"
        else:
            query += " WHERE id is not null"
        query += f" GROUP BY {group_by}"
        if order_by:
            query += f" ORDER BY {order_by}"
        query += f" LIMIT {effective_limit}"

        result = zoho.generic_coql_query(query, limit=effective_limit)
        data = result.get("data") or []

        return {
            "success": True,
            "module": module,
            "total_groups": len(data),
            "data": data,
            "query": query,
        }
    except ZohoAuthError:
        return {"success": False, "error": "認証エラー。管理者に連絡してください。"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"[ADK Zoho] aggregate_crm_data error: {e}")
        return {"success": False, "error": str(e)}


@_retry_transient(max_retries=2)
def get_record_detail(
    module: str,
    record_id: str,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """任意モジュールの1レコードを全フィールド取得。

    レコードIDはquery_crm_recordsで取得したidを使用。
    全フィールドが返るため、特定フィールドだけ必要ならquery_crm_recordsでfieldsを絞ること。

    Args:
        module: モジュールAPI名（例: "jobSeeker", "JOB"）
        record_id: ZohoのレコードID

    Returns:
        success: True/False
        module: モジュール名
        record_id: レコードID
        record: 全フィールドデータ（ルックアップはname展開済み）
        field_count: 返却フィールド数
    """
    logger.info(f"[ADK Zoho] get_record_detail: module={module}, id={record_id}")

    if not module:
        return {"success": False, "error": "moduleを指定してください"}
    if not record_id:
        return {"success": False, "error": "record_idを指定してください"}

    try:
        zoho = _get_zoho_client()
        record = zoho.get_record(module, record_id)

        if not record:
            return {"success": False, "error": f"レコードが見つかりません: {module}/{record_id}"}

        cleaned = _clean_lookup_fields(record, strip_empty=True)

        # State tracking
        if tool_context:
            try:
                viewed = tool_context.state.get("user:viewed_records", [])
                entry = {"module": module, "record_id": record_id, "name": record.get("Name", record_id)}
                existing_ids = {v.get("record_id") for v in viewed if isinstance(v, dict)}
                if record_id not in existing_ids:
                    viewed = viewed + [entry]
                    if len(viewed) > 30:
                        viewed = viewed[-30:]
                    tool_context.state["user:viewed_records"] = viewed
            except Exception:
                pass

        return {
            "success": True,
            "module": module,
            "record_id": record_id,
            "record": cleaned,
            "field_count": len(cleaned),
        }
    except ZohoAuthError:
        return {"success": False, "error": "認証エラー。管理者に連絡してください。"}
    except Exception as e:
        logger.error(f"[ADK Zoho] get_record_detail error: {e}")
        return {"success": False, "error": str(e)}


@_retry_transient(max_retries=2)
def get_related_records(
    module: str,
    record_id: str,
    related_list: str,
    limit: int = 200,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """レコードの関連リスト（サブフォーム・子レコード）を取得。

    関連リスト名はZohoのUI上のタブ名、またはAPIドキュメントで確認。
    例: jobSeekerの選考サブフォーム（relatedlist2）、推薦企業（CLT_hc10）等。

    Args:
        module: 親モジュールAPI名（例: "jobSeeker"）
        record_id: 親レコードのID
        related_list: 関連リストAPI名（例: "relatedlist2", "CLT_hc10", "Notes"）
        limit: 最大取得件数（デフォルト200）

    Returns:
        success: True/False
        module: 親モジュール名
        record_id: 親レコードID
        related_list: 関連リスト名
        total: 取得件数
        records: 関連レコードリスト
    """
    logger.info(f"[ADK Zoho] get_related_records: {module}/{record_id}/{related_list}")

    if not module or not record_id or not related_list:
        return {"success": False, "error": "module, record_id, related_listをすべて指定してください"}

    try:
        zoho = _get_zoho_client()
        records = zoho.get_related_records(module, record_id, related_list, limit=min(limit, 200))

        return {
            "success": True,
            "module": module,
            "record_id": record_id,
            "related_list": related_list,
            "total": len(records),
            "records": records,
        }
    except ZohoAuthError:
        return {"success": False, "error": "認証エラー。管理者に連絡してください。"}
    except Exception as e:
        logger.error(f"[ADK Zoho] get_related_records error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# Tier 3: jobSeeker専門分析ツール
# ============================================================

def analyze_funnel_by_channel(
    channel: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """特定チャネルのファネル分析。各ステージの転換率とボトルネックを自動特定。

    チャネルコードはget_module_schemaでjobSeekerのfield14ピックリスト値を確認。
    全チャネル横断で見たい場合はaggregate_crm_dataでGROUP BYを使用。

    Args:
        channel: 流入経路コード（必須。例: "sco_bizreach", "paid_meta", "org_hitocareer"）
        date_from: 開始日(YYYY-MM-DD)
        date_to: 終了日(YYYY-MM-DD)

    Returns:
        success: True/False
        channel: 分析対象チャネル
        category: チャネルカテゴリ（スカウト/有料広告等）
        funnel_data: ステージ別データ（count, conversion_rate, drop_rate）
        bottlenecks: ボトルネック箇所リスト（転換率50%未満）
        kpis: KPI指標（リード数、面談率、入社率等）
    """
    logger.info(f"[ADK Zoho] analyze_funnel_by_channel: channel={channel}")

    if not channel:
        return {"success": False, "error": "チャネルコードを指定してください（例: sco_bizreach）"}

    try:
        zoho = _get_zoho_client()
        status_counts = zoho.count_by_status(
            channel=channel, date_from=date_from, date_to=date_to
        )

        funnel_data = []
        prev_count = None
        bottlenecks = []

        for status, label in _FUNNEL_STAGES:
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
            "category": _categorize_channel(channel),
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
        channel: 流入経路でフィルタ（省略時は全チャネル）

    Returns:
        success: True/False
        period_type: 分析期間タイプ
        trend_data: 期間別データ（count, change, change_pct, trend）
        summary: 集計サマリ（total_count, avg_count）
    """
    logger.info(f"[ADK Zoho] trend_analysis_by_period: {period_type}, {months_back}ヶ月")

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
                        data["trend"] = "上昇"
                    elif change_pct < -10:
                        data["trend"] = "下降"
                    else:
                        data["trend"] = "横ばい"
                else:
                    data["trend"] = "N/A"

        total_count = sum(d["count"] for d in trend_data)
        avg_count = round(total_count / len(trend_data), 1) if trend_data else 0

        return {
            "success": True,
            "period_type": period_type,
            "channel_filter": channel or "全体",
            "category": _categorize_channel(channel) if channel else None,
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
        success: True/False
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
        for ch in channels:
            status_counts = channel_stats.get(ch, {})
            total = sum(status_counts.values())
            hired = status_counts.get("14. 入社", 0)
            interview_done = status_counts.get("4. 面談済み", 0)

            comparison_data.append({
                "channel": ch,
                "category": _categorize_channel(ch),
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
        success: True/False
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
        success: True/False
        overall: 全体KPI
        category_summary: カテゴリ別サマリ
        metrics: チャネル別KPI
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

            # Cumulative counts (candidates who reached at least this stage)
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

            category = _categorize_channel(ch)

            metrics.append({
                "channel": ch,
                "category": category,
                "total": total,
                "interview_rate": f"{interview_rate}%",
                "offer_rate": f"{offer_rate}%",
                "hire_rate": f"{hire_rate}%",
                "hired_count": hired_count,
                "_hire_rate_num": hire_rate,
            })

        # Sort by hire rate
        metrics.sort(key=lambda x: x["_hire_rate_num"], reverse=True)

        ranking = []
        for i, m in enumerate(metrics):
            ranking.append({
                "rank": i + 1,
                "channel": m["channel"],
                "category": m["category"],
                "hire_rate": m["hire_rate"],
                "hired_count": m["hired_count"],
                "total": m["total"],
            })

        # Remove internal sort key
        for m in metrics:
            del m["_hire_rate_num"]

        # Recommendations
        recommendations = []
        if ranking:
            top = ranking[0]
            recommendations.append(
                f"入社率トップは{top['channel']}（{top['category']}、{top['hire_rate']}）。"
                f"このチャネルの成功パターンを横展開推奨。"
            )

        high_vol_low_conv = [
            m for m in metrics
            if m["total"] >= 10 and float(m["hire_rate"].replace("%", "")) < 3.0
        ]
        if high_vol_low_conv:
            names = ", ".join(m["channel"] for m in high_vol_low_conv[:3])
            recommendations.append(
                f"獲得数は多いが入社率が低いチャネル: {names}。ファネル改善を優先。"
            )

        # Category summary
        category_summary: Dict[str, Dict[str, Any]] = {}
        for m in metrics:
            cat = m["category"]
            if cat not in category_summary:
                category_summary[cat] = {"total": 0, "hired": 0, "channels": 0}
            category_summary[cat]["total"] += m["total"]
            category_summary[cat]["hired"] += m["hired_count"]
            category_summary[cat]["channels"] += 1

        for data in category_summary.values():
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


# ============================================================
# ツールリスト
# ============================================================

ADK_ZOHO_CRM_TOOLS = [
    # Tier 1: メタデータ発見
    list_crm_modules,
    get_module_schema,
    get_module_layout,
    # Tier 2: 汎用クエリ
    query_crm_records,
    aggregate_crm_data,
    get_record_detail,
    get_related_records,
    # Tier 3: jobSeeker専門分析
    analyze_funnel_by_channel,
    trend_analysis_by_period,
    compare_channels,
    get_pic_performance,
    get_conversion_metrics,
]
