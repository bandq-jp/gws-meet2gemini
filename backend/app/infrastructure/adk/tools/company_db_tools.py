"""
Company Database Tools for Google ADK.

ADK-native tool definitions for company information operations.
These are plain Python functions that ADK will automatically wrap.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Need type definitions
NEED_TYPES = {
    "salary": "給与・年収重視",
    "growth": "成長・キャリアアップ重視",
    "wlb": "ワークライフバランス重視",
    "atmosphere": "社風・雰囲気重視",
    "future": "将来性・安定性重視",
}

# Need type to column name mapping
NEED_COLUMN_MAP = {
    "salary": "給与訴求",
    "growth": "成長訴求",
    "wlb": "WLB訴求",
    "atmosphere": "雰囲気訴求",
    "future": "将来性訴求",
}


_sheets_service_instance = None


def _get_sheets_service():
    """Get SheetsService singleton (lazy import to avoid circular deps)."""
    global _sheets_service_instance
    if _sheets_service_instance is None:
        from app.infrastructure.google.sheets_service import CompanyDatabaseSheetsService
        from app.infrastructure.config.settings import get_settings
        _sheets_service_instance = CompanyDatabaseSheetsService(get_settings())
    return _sheets_service_instance


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    if value is None or value == "":
        return default
    try:
        # Handle strings like "35歳" -> 35
        if isinstance(value, str):
            value = value.replace("歳", "").replace("万", "").replace(",", "").strip()
        return int(value)
    except (ValueError, TypeError):
        return default


def get_company_definitions() -> Dict[str, Any]:
    """
    企業DBのマスタ定義一覧を取得。業種・勤務地・ニーズタイプ・担当者一覧を返す。

    Returns:
        success: True/False
        industries: 業種リスト
        locations: 勤務地リスト
        need_types: ニーズタイプ定義
        available_pics: 利用可能な担当者名一覧
        total_companies: 企業総数
    """
    logger.info("[ADK CompanyDB] get_company_definitions")

    try:
        service = _get_sheets_service()
        all_companies = service.get_all_companies()

        # Extract unique values
        industries = sorted(set(
            c.get("業種", "") for c in all_companies if c.get("業種")
        ))
        locations = sorted(set(
            c.get("勤務地", "") for c in all_companies if c.get("勤務地")
        ))
        pic_names = service.list_pic_sheets()

        return {
            "success": True,
            "industries": industries,
            "locations": locations,
            "need_types": NEED_TYPES,
            "available_pics": pic_names,
            "total_companies": len(all_companies),
        }
    except Exception as e:
        logger.error(f"[ADK CompanyDB] get_company_definitions error: {e}")
        return {"success": False, "error": str(e)}


def search_companies(
    industry: Optional[str] = None,
    location: Optional[str] = None,
    min_salary: Optional[int] = None,
    max_age: Optional[int] = None,
    education: Optional[str] = None,
    remote_ok: Optional[bool] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    企業検索。条件でフィルタリングして企業リストを返す。

    Args:
        industry: 業種（部分一致、例: IT/コンサル/メーカー）
        location: 勤務地（部分一致、例: 東京/大阪/リモート）
        min_salary: 最低年収（万円）。この年収以上を提示可能な企業
        max_age: 候補者の年齢。この年齢以下を受け入れる企業
        education: 学歴要件（部分一致）
        remote_ok: リモートワーク可能か
        limit: 取得件数（max 50）

    Returns:
        success: True/False
        filters_applied: 適用したフィルタ
        total_found: マッチ件数
        companies: 企業リスト（簡易情報）
    """
    logger.info(f"[ADK CompanyDB] search_companies: industry={industry}, location={location}")

    try:
        service = _get_sheets_service()
        all_companies = service.get_all_companies()

        filtered = []
        for company in all_companies:
            # Industry filter (partial match)
            if industry and industry not in company.get("業種", ""):
                continue

            # Location filter (partial match)
            if location and location not in company.get("勤務地", ""):
                continue

            # Salary filter
            if min_salary:
                company_max = _safe_int(company.get("想定年収上限"), 0)
                if company_max < min_salary:
                    continue

            # Age filter
            if max_age:
                age_limit = _safe_int(company.get("年齢上限"), 99)
                if age_limit < max_age:
                    continue

            # Education filter (partial match)
            if education and education not in company.get("学歴要件", ""):
                continue

            # Remote filter
            if remote_ok is not None:
                remote_policy = company.get("リモートワーク", "")
                is_remote = "可" in remote_policy or "フル" in remote_policy or "相談" in remote_policy
                if remote_ok and not is_remote:
                    continue

            # Build summary record
            filtered.append({
                "企業名": company.get("企業名"),
                "業種": company.get("業種"),
                "勤務地": company.get("勤務地"),
                "想定年収": f"{company.get('想定年収下限', '?')}〜{company.get('想定年収上限', '?')}万",
                "年齢上限": company.get("年齢上限"),
                "学歴要件": company.get("学歴要件"),
                "リモート": company.get("リモートワーク"),
            })

        return {
            "success": True,
            "filters_applied": {
                "industry": industry,
                "location": location,
                "min_salary": min_salary,
                "max_age": max_age,
                "education": education,
                "remote_ok": remote_ok,
            },
            "total_found": len(filtered),
            "companies": filtered[:min(limit, 50)],
        }
    except Exception as e:
        logger.error(f"[ADK CompanyDB] search_companies error: {e}")
        return {"success": False, "error": str(e)}


def get_company_detail(company_name: str) -> Dict[str, Any]:
    """
    企業詳細取得。全データ+訴求ポイントを返す。

    Args:
        company_name: 企業名（部分一致検索）

    Returns:
        success: True/False
        company_name: 企業名
        basic_info: 基本情報
        requirements: 採用要件
        conditions: 条件
        appeal_points: ニーズ別訴求ポイント
    """
    logger.info(f"[ADK CompanyDB] get_company_detail: company_name={company_name}")

    if not company_name:
        return {"success": False, "error": "company_nameを指定してください"}

    try:
        service = _get_sheets_service()
        all_companies = service.get_all_companies()

        # Partial match search
        matches = [c for c in all_companies if company_name in c.get("企業名", "")]

        if not matches:
            return {"success": False, "error": f"企業が見つかりません: {company_name}"}

        if len(matches) > 1:
            return {
                "success": False,
                "error": "複数の企業がマッチしました。より具体的な企業名を指定してください。",
                "matches": [m.get("企業名") for m in matches[:5]],
            }

        company = matches[0]

        # Get appeal points
        appeal_data = service.get_appeal_points()
        appeal = appeal_data.get(company.get("企業名"), {})

        return {
            "success": True,
            "company_name": company.get("企業名"),
            "basic_info": {
                "業種": company.get("業種"),
                "勤務地": company.get("勤務地"),
                "設立年": company.get("設立年"),
                "従業員数": company.get("従業員数"),
                "上場区分": company.get("上場区分"),
            },
            "requirements": {
                "年齢上限": company.get("年齢上限"),
                "学歴要件": company.get("学歴要件"),
                "経験社数上限": company.get("経験社数上限"),
                "必須経験": company.get("必須経験"),
                "歓迎経験": company.get("歓迎経験"),
            },
            "conditions": {
                "想定年収": f"{company.get('想定年収下限')}〜{company.get('想定年収上限')}万",
                "リモートワーク": company.get("リモートワーク"),
                "平均残業時間": company.get("平均残業時間"),
                "有給取得率": company.get("有給取得率"),
            },
            "appeal_points": appeal,
        }
    except Exception as e:
        logger.error(f"[ADK CompanyDB] get_company_detail error: {e}")
        return {"success": False, "error": str(e)}


def get_company_requirements(company_name: str) -> Dict[str, Any]:
    """
    企業の採用要件を取得。年齢・学歴・経験社数などの要件を返す。

    get_company_detailとの違い：採用要件のみ高速取得。全情報不要な場合はこちらが効率的。

    Args:
        company_name: 企業名（部分一致検索）

    Returns:
        Dict[str, Any]: 採用要件。
            success: True/False
            company_name: 企業名
            requirements: 採用要件詳細
    """
    logger.info(f"[ADK CompanyDB] get_company_requirements: company_name={company_name}")

    if not company_name:
        return {"success": False, "error": "company_nameを指定してください"}

    try:
        service = _get_sheets_service()
        all_companies = service.get_all_companies()

        matches = [c for c in all_companies if company_name in c.get("企業名", "")]

        if not matches:
            return {"success": False, "error": f"企業が見つかりません: {company_name}"}

        if len(matches) > 1:
            return {
                "success": False,
                "error": "複数の企業がマッチ",
                "matches": [m.get("企業名") for m in matches[:5]],
            }

        company = matches[0]

        return {
            "success": True,
            "company_name": company.get("企業名"),
            "requirements": {
                "年齢上限": company.get("年齢上限"),
                "学歴要件": company.get("学歴要件"),
                "経験社数上限": company.get("経験社数上限"),
                "必須スキル": company.get("必須スキル"),
                "必須経験": company.get("必須経験"),
                "歓迎スキル": company.get("歓迎スキル"),
                "歓迎経験": company.get("歓迎経験"),
                "求める人物像": company.get("求める人物像"),
            },
        }
    except Exception as e:
        logger.error(f"[ADK CompanyDB] get_company_requirements error: {e}")
        return {"success": False, "error": str(e)}


def get_appeal_by_need(
    company_name: str,
    need_type: str,
) -> Dict[str, Any]:
    """
    ニーズ別訴求ポイント取得。候補者の転職理由に合わせた訴求文言を返す。

    転職理由→need_type変換ガイド:
    - 給与が低い → salary
    - スキルアップしたい → growth
    - 残業多い → wlb
    - 人間関係 → atmosphere
    - 会社の将来が不安 → future

    Args:
        company_name: 企業名
        need_type: ニーズタイプ（salary/growth/wlb/atmosphere/future）

    Returns:
        Dict[str, Any]: 訴求ポイント。
            success: True/False
            company_name: 企業名
            need_type: ニーズタイプ
            need_label: ニーズの日本語ラベル
            appeal_point: 訴求文言
    """
    logger.info(f"[ADK CompanyDB] get_appeal_by_need: company={company_name}, need={need_type}")

    if not company_name:
        return {"success": False, "error": "company_nameを指定してください"}

    if need_type not in NEED_TYPES:
        return {
            "success": False,
            "error": f"無効なニーズタイプ: {need_type}",
            "valid_types": NEED_TYPES,
        }

    try:
        service = _get_sheets_service()
        appeal_data = service.get_appeal_points()

        # Try exact match first, then partial match
        company_appeal = appeal_data.get(company_name)
        if not company_appeal:
            # Partial match
            for name, data in appeal_data.items():
                if company_name in name:
                    company_appeal = data
                    company_name = name
                    break

        if not company_appeal:
            return {"success": False, "error": f"企業の訴求データが見つかりません: {company_name}"}

        column = NEED_COLUMN_MAP.get(need_type, "")
        appeal_text = company_appeal.get(column, "")

        return {
            "success": True,
            "company_name": company_name,
            "need_type": need_type,
            "need_label": NEED_TYPES[need_type],
            "appeal_point": appeal_text,
            "usage_hint": "この訴求ポイントを候補者への提案時に活用してください。",
        }
    except Exception as e:
        logger.error(f"[ADK CompanyDB] get_appeal_by_need error: {e}")
        return {"success": False, "error": str(e)}


def match_candidate_to_companies(
    record_id: Optional[str] = None,
    age: Optional[int] = None,
    current_salary: Optional[int] = None,
    desired_salary: Optional[int] = None,
    education: Optional[str] = None,
    experience_count: Optional[int] = None,
    transfer_reasons: Optional[List[str]] = None,
    location: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    候補者に合う企業をマッチング。Zoho record_idまたは条件を指定してスコア付きで企業を推薦。

    find_companies_for_candidateとの違い：こちらは採用要件（年齢・年収・学歴）の厳密マッチング。
    自然言語の意味検索はfind_companies_for_candidateを使用。

    Args:
        record_id: Zoho候補者record_id（指定すると自動でZoho+Supabaseからデータ取得）
        age: 年齢
        current_salary: 現年収（万円）
        desired_salary: 希望年収（万円）
        education: 学歴
        experience_count: 経験社数
        transfer_reasons: 転職理由リスト
        location: 希望勤務地
        limit: 取得件数（max 20）

    Returns:
        Dict[str, Any]: マッチング結果。
            success: True/False
            candidate_info: 使用した候補者情報
            total_matched: マッチ件数
            recommended_companies: スコア付き推奨企業リスト
    """
    logger.info(f"[ADK CompanyDB] match_candidate_to_companies: record_id={record_id}")

    try:
        candidate_info: Dict[str, Any] = {}

        # If record_id provided, fetch from Zoho + Supabase
        if record_id:
            try:
                from app.infrastructure.zoho.client import ZohoClient
                from app.infrastructure.adk.tools.candidate_insight_tools import (
                    _get_structured_data_by_zoho_record,
                )

                zoho = ZohoClient()
                zoho_record = zoho.get_app_hc_record(record_id)

                if zoho_record:
                    candidate_info["name"] = zoho_record.get("Name", "不明")
                    candidate_info["channel"] = zoho_record.get("field14")
                    candidate_info["age"] = _safe_int(zoho_record.get("field15"))
                    candidate_info["current_salary"] = _safe_int(zoho_record.get("field17"))
                    candidate_info["desired_salary"] = _safe_int(zoho_record.get("field20"))

                structured = _get_structured_data_by_zoho_record(record_id)
                if structured and structured.get("data"):
                    data = structured["data"]
                    candidate_info["transfer_reasons"] = data.get("transfer_reasons", [])
                    if data.get("desired_first_year_salary"):
                        candidate_info["desired_salary"] = _safe_int(
                            data.get("desired_first_year_salary")
                        )
            except Exception as e:
                logger.warning(f"[ADK CompanyDB] Failed to fetch Zoho/Supabase data: {e}")

        # Override with manual values
        if age:
            candidate_info["age"] = age
        if current_salary:
            candidate_info["current_salary"] = current_salary
        if desired_salary:
            candidate_info["desired_salary"] = desired_salary
        if education:
            candidate_info["education"] = education
        if experience_count:
            candidate_info["experience_count"] = experience_count
        if transfer_reasons:
            candidate_info["transfer_reasons"] = transfer_reasons
        if location:
            candidate_info["location"] = location

        # Get company data
        service = _get_sheets_service()
        all_companies = service.get_all_companies()
        appeal_data = service.get_appeal_points()

        # Calculate match scores
        scored_companies = []
        for company in all_companies:
            score = 0
            match_reasons = []
            disqualified = False

            # Age match (critical)
            if candidate_info.get("age"):
                age_limit = _safe_int(company.get("年齢上限"), 99)
                if candidate_info["age"] <= age_limit:
                    score += 20
                    match_reasons.append("年齢適合")
                else:
                    disqualified = True
                    continue  # Age over limit = skip

            # Location match
            if candidate_info.get("location"):
                company_location = company.get("勤務地", "")
                if candidate_info["location"] in company_location:
                    score += 15
                    match_reasons.append("勤務地適合")

            # Salary match
            if candidate_info.get("desired_salary"):
                company_max = _safe_int(company.get("想定年収上限"), 0)
                company_min = _safe_int(company.get("想定年収下限"), 0)
                desired = candidate_info["desired_salary"]

                if company_min <= desired <= company_max:
                    score += 30
                    match_reasons.append("希望年収レンジ内")
                elif desired < company_max:
                    score += 15
                    match_reasons.append("年収上限内")

            # Experience count match
            if candidate_info.get("experience_count"):
                exp_limit = _safe_int(company.get("経験社数上限"), 99)
                if candidate_info["experience_count"] <= exp_limit:
                    score += 10
                    match_reasons.append("経験社数適合")

            # Transfer reason -> appeal point match
            reasons = candidate_info.get("transfer_reasons", [])
            company_appeal = appeal_data.get(company.get("企業名"), {})
            reasons_str = " ".join(str(r) for r in reasons) if reasons else ""

            if ("給与" in reasons_str or "年収" in reasons_str) and company_appeal.get("給与訴求"):
                score += 15
                match_reasons.append("給与訴求可")
            if ("成長" in reasons_str or "スキル" in reasons_str or "キャリア" in reasons_str) and company_appeal.get("成長訴求"):
                score += 15
                match_reasons.append("成長訴求可")
            if ("ワークライフ" in reasons_str or "残業" in reasons_str or "休み" in reasons_str) and company_appeal.get("WLB訴求"):
                score += 15
                match_reasons.append("WLB訴求可")
            if ("雰囲気" in reasons_str or "人間関係" in reasons_str or "社風" in reasons_str) and company_appeal.get("雰囲気訴求"):
                score += 10
                match_reasons.append("雰囲気訴求可")

            if score > 0 and not disqualified:
                scored_companies.append({
                    "企業名": company.get("企業名"),
                    "業種": company.get("業種"),
                    "勤務地": company.get("勤務地"),
                    "想定年収": f"{company.get('想定年収下限')}〜{company.get('想定年収上限')}万",
                    "年齢上限": company.get("年齢上限"),
                    "match_score": score,
                    "match_reasons": match_reasons,
                })

        # Sort by score
        scored_companies.sort(key=lambda x: x["match_score"], reverse=True)

        return {
            "success": True,
            "candidate_info": candidate_info,
            "total_matched": len(scored_companies),
            "recommended_companies": scored_companies[:min(limit, 20)],
            "usage_hint": "match_scoreが高い企業から優先的に提案してください。",
        }
    except Exception as e:
        logger.error(f"[ADK CompanyDB] match_candidate_to_companies error: {e}")
        return {"success": False, "error": str(e)}


def get_pic_recommended_companies(pic_name: str) -> Dict[str, Any]:
    """
    担当者別推奨企業リストを取得（X シートから）。

    Args:
        pic_name: 担当者名（"X " プレフィックスなし）

    Returns:
        success: True/False
        pic_name: 担当者名
        total_companies: 企業数
        rankings: 企業ランキングリスト
    """
    logger.info(f"[ADK CompanyDB] get_pic_recommended_companies: pic_name={pic_name}")

    if not pic_name:
        return {"success": False, "error": "pic_nameを指定してください"}

    try:
        service = _get_sheets_service()
        rankings = service.get_pic_ranking(pic_name)

        if not rankings:
            available_pics = service.list_pic_sheets()
            return {
                "success": False,
                "error": f"担当者「{pic_name}」のシートが見つかりません",
                "available_pics": available_pics,
            }

        return {
            "success": True,
            "pic_name": pic_name,
            "total_companies": len(rankings),
            "rankings": rankings[:20],
        }
    except Exception as e:
        logger.error(f"[ADK CompanyDB] get_pic_recommended_companies error: {e}")
        return {"success": False, "error": str(e)}


def compare_companies(
    company_names: List[str],
) -> Dict[str, Any]:
    """複数企業の比較表を生成（2-5社）。年収・要件・訴求ポイントを並列比較。

    Args:
        company_names: 比較する企業名リスト（2-5社）

    Returns:
        Dict[str, Any]: 比較結果。
            success: True/False
            comparison_table: 企業比較テーブル
            summary: 主要な違いのサマリー
    """
    logger.info(f"[ADK CompanyDB] compare_companies: {company_names}")

    if not company_names or len(company_names) < 2:
        return {"success": False, "error": "比較には2社以上を指定してください"}

    if len(company_names) > 5:
        return {"success": False, "error": "比較は最大5社までです"}

    try:
        service = _get_sheets_service()
        all_companies = service.get_all_companies()
        appeal_data = service.get_appeal_points()

        # Build lookup by name (partial match)
        comparison_table = []
        not_found = []

        for target_name in company_names:
            matches = [c for c in all_companies if target_name in c.get("企業名", "")]

            if not matches:
                not_found.append(target_name)
                continue

            company = matches[0]
            name = company.get("企業名", target_name)
            appeal = appeal_data.get(name, {})

            # Salary range
            salary_min = company.get("想定年収下限", "?")
            salary_max = company.get("想定年収上限", "?")

            comparison_table.append({
                "企業名": name,
                "業種": company.get("業種"),
                "勤務地": company.get("勤務地"),
                "想定年収": f"{salary_min}〜{salary_max}万",
                "想定年収下限": _safe_int(salary_min, 0),
                "想定年収上限": _safe_int(salary_max, 0),
                "年齢上限": company.get("年齢上限"),
                "学歴要件": company.get("学歴要件"),
                "経験社数上限": company.get("経験社数上限"),
                "必須経験": company.get("必須経験"),
                "リモートワーク": company.get("リモートワーク"),
                "平均残業時間": company.get("平均残業時間"),
                "有給取得率": company.get("有給取得率"),
                "設立年": company.get("設立年"),
                "従業員数": company.get("従業員数"),
                "上場区分": company.get("上場区分"),
                "訴求ポイント": {
                    "給与訴求": appeal.get("給与訴求", ""),
                    "成長訴求": appeal.get("成長訴求", ""),
                    "WLB訴求": appeal.get("WLB訴求", ""),
                    "雰囲気訴求": appeal.get("雰囲気訴求", ""),
                    "将来性訴求": appeal.get("将来性訴求", ""),
                },
            })

        if not comparison_table:
            return {
                "success": False,
                "error": "指定された企業がいずれも見つかりません",
                "not_found": not_found,
            }

        # Generate summary of key differences
        summary_points = []

        # Salary comparison
        salary_items = [
            (c["企業名"], c["想定年収上限"])
            for c in comparison_table if c["想定年収上限"] > 0
        ]
        if salary_items:
            best_salary = max(salary_items, key=lambda x: x[1])
            summary_points.append(f"年収上限が最も高いのは{best_salary[0]}（{best_salary[1]}万円）")

        # Remote comparison
        remote_companies = [
            c["企業名"] for c in comparison_table
            if c.get("リモートワーク") and (
                "可" in str(c["リモートワーク"]) or
                "フル" in str(c["リモートワーク"])
            )
        ]
        if remote_companies:
            summary_points.append(f"リモート可能: {', '.join(remote_companies)}")

        # Age limit comparison
        age_items = [
            (c["企業名"], _safe_int(c.get("年齢上限"), 0))
            for c in comparison_table if _safe_int(c.get("年齢上限"), 0) > 0
        ]
        if age_items:
            most_flexible = max(age_items, key=lambda x: x[1])
            summary_points.append(f"年齢上限が最も高いのは{most_flexible[0]}（{most_flexible[1]}歳）")

        # Remove internal-only fields from output
        for entry in comparison_table:
            del entry["想定年収下限"]
            del entry["想定年収上限"]

        result: Dict[str, Any] = {
            "success": True,
            "compared_count": len(comparison_table),
            "comparison_table": comparison_table,
            "summary": summary_points,
        }

        if not_found:
            result["not_found"] = not_found

        return result

    except Exception as e:
        logger.error(f"[ADK CompanyDB] compare_companies error: {e}")
        return {"success": False, "error": str(e)}


# List of ADK-compatible tools
ADK_COMPANY_DB_TOOLS = [
    get_company_definitions,
    search_companies,
    get_company_detail,
    get_company_requirements,
    get_appeal_by_need,
    match_candidate_to_companies,
    get_pic_recommended_companies,
    compare_companies,
]
