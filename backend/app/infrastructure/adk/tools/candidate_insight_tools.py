"""
Candidate Insight Tools for Google ADK.

ADK-native tool definitions for candidate analysis.
These are plain Python functions that ADK will automatically wrap.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from collections import Counter

from app.infrastructure.zoho.client import ZohoClient, ZohoAuthError
from app.infrastructure.supabase.client import get_supabase

logger = logging.getLogger(__name__)


# --- Helper functions ---

def _get_structured_data_by_zoho_record(zoho_record_id: str) -> Optional[Dict[str, Any]]:
    """Get structured data by Zoho record ID."""
    try:
        sb = get_supabase()
        res = sb.table("structured_outputs").select(
            "meeting_id, data, zoho_record_id, zoho_candidate_name, zoho_sync_status"
        ).eq("zoho_record_id", zoho_record_id).maybe_single().execute()
        return res.data
    except Exception as e:
        logger.warning(f"Failed to get structured data for zoho_record_id={zoho_record_id}: {e}")
        return None


def _get_all_structured_data_with_sync(limit: int = 500) -> List[Dict[str, Any]]:
    """Get all synced structured data for analysis."""
    try:
        sb = get_supabase()
        res = sb.table("structured_outputs").select(
            "meeting_id, data, zoho_record_id, zoho_candidate_name, created_at"
        ).not_.is_("zoho_record_id", "null").limit(limit).execute()
        return res.data or []
    except Exception as e:
        logger.warning(f"Failed to get structured data: {e}")
        return []


def _get_all_structured_data_by_zoho_ids(zoho_record_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Batch get structured data by multiple Zoho record IDs."""
    if not zoho_record_ids:
        return {}

    try:
        sb = get_supabase()
        res = sb.table("structured_outputs").select(
            "meeting_id, data, zoho_record_id, zoho_candidate_name, zoho_sync_status"
        ).in_("zoho_record_id", zoho_record_ids[:100]).execute()

        return {row["zoho_record_id"]: row for row in (res.data or [])}
    except Exception as e:
        logger.warning(f"Failed to batch get structured data: {e}")
        return {}


def _extract_field(data: Dict[str, Any], field_name: str) -> Any:
    """Safely extract field from structured data."""
    if not data or not isinstance(data, dict):
        return None
    return data.get(field_name)


# --- ADK-compatible tool functions ---

def analyze_competitor_risk(
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Analyze competitor risk - identify high-risk candidates with other agent offers.

    Args:
        channel: Filter by channel (paid_meta, sco_bizreach, etc.)
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        limit: Max candidates to analyze

    Returns:
        Analysis with high_risk_candidates, competitor_agents, recommendations
    """
    logger.info(f"[ADK] analyze_competitor_risk: channel={channel}")

    try:
        zoho = ZohoClient()
        records = zoho.search_by_criteria(
            channel=channel,
            date_from=date_from,
            date_to=date_to,
            limit=min(limit, 100),
        )

        high_risk_candidates = []
        competitor_agents: Counter = Counter()
        companies_in_selection: Counter = Counter()

        record_ids = [r.get("record_id") for r in records if r.get("record_id")]
        structured_map = _get_all_structured_data_by_zoho_ids(record_ids)

        for record in records:
            record_id = record.get("record_id")
            if not record_id:
                continue

            structured = structured_map.get(record_id)
            if not structured:
                continue

            data = structured.get("data", {})

            current_agents = _extract_field(data, "current_agents")
            if current_agents:
                agents = [a.strip() for a in str(current_agents).replace("、", ",").split(",") if a.strip()]
                for agent in agents:
                    competitor_agents[agent] += 1

            companies = _extract_field(data, "companies_in_selection") or []
            for company in (companies if isinstance(companies, list) else []):
                if company:
                    companies_in_selection[str(company).split("（")[0].strip()] += 1

            other_salary = _extract_field(data, "other_offer_salary")
            activity_status = _extract_field(data, "transfer_activity_status")

            is_high_risk = False
            risk_reasons = []

            if other_salary:
                is_high_risk = True
                risk_reasons.append(f"他社オファー: {other_salary}")

            if activity_status in ["最終面接待ち ~ 内定済み", "企業打診済み ~ 一次選考フェーズ"]:
                is_high_risk = True
                risk_reasons.append(f"活動状況: {activity_status}")

            if is_high_risk:
                high_risk_candidates.append({
                    "record_id": record_id,
                    "name": record.get("求職者名", "不明"),
                    "risk_reasons": risk_reasons,
                })

        return {
            "success": True,
            "analyzed_count": len(records),
            "high_risk_count": len(high_risk_candidates),
            "high_risk_candidates": high_risk_candidates[:10],
            "competitor_agents": dict(competitor_agents.most_common(10)),
            "popular_companies": dict(companies_in_selection.most_common(10)),
        }

    except ZohoAuthError:
        return {"success": False, "error": "Zoho認証エラー"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def assess_candidate_urgency(
    channel: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Assess candidate urgency based on timing, job status, and activity.

    Args:
        channel: Filter by channel
        status: Filter by status
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        limit: Max candidates to analyze

    Returns:
        Urgency assessment with priority queue
    """
    logger.info(f"[ADK] assess_candidate_urgency: channel={channel}")

    try:
        zoho = ZohoClient()
        records = zoho.search_by_criteria(
            channel=channel,
            status=status,
            date_from=date_from,
            date_to=date_to,
            limit=min(limit, 100),
        )

        urgency_scores = []
        urgency_distribution = {"即時": 0, "高": 0, "中": 0, "低": 0}

        record_ids = [r.get("record_id") for r in records if r.get("record_id")]
        structured_map = _get_all_structured_data_by_zoho_ids(record_ids)

        for record in records:
            record_id = record.get("record_id")
            if not record_id:
                continue

            structured = structured_map.get(record_id)
            if not structured:
                continue

            data = structured.get("data", {})
            score = 0
            factors = []

            timing = _extract_field(data, "desired_timing")
            if timing == "すぐにでも":
                score += 40
                factors.append("すぐにでも")
            elif timing == "3ヶ月以内":
                score += 30
                factors.append("3ヶ月以内")

            job_status = _extract_field(data, "current_job_status")
            if job_status == "離職中":
                score += 30
                factors.append("離職中")

            if _extract_field(data, "other_offer_salary"):
                score += 20
                factors.append("他社オファーあり")

            if score >= 70:
                urgency = "即時"
            elif score >= 50:
                urgency = "高"
            elif score >= 30:
                urgency = "中"
            else:
                urgency = "低"

            urgency_distribution[urgency] += 1

            urgency_scores.append({
                "record_id": record_id,
                "name": record.get("求職者名", "不明"),
                "urgency_score": score,
                "urgency_level": urgency,
                "factors": factors,
            })

        urgency_scores.sort(key=lambda x: x["urgency_score"], reverse=True)

        return {
            "success": True,
            "analyzed_count": len(records),
            "urgency_distribution": urgency_distribution,
            "priority_queue": urgency_scores[:20],
        }

    except ZohoAuthError:
        return {"success": False, "error": "Zoho認証エラー"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_transfer_patterns(
    channel: Optional[str] = None,
    group_by: str = "reason",
) -> Dict[str, Any]:
    """
    Analyze transfer patterns grouped by reason, timing, or vision.

    Args:
        channel: Filter by channel
        group_by: Group by "reason", "timing", or "vision"

    Returns:
        Pattern distribution and insights
    """
    logger.info(f"[ADK] analyze_transfer_patterns: group_by={group_by}")

    try:
        all_structured = _get_all_structured_data_with_sync(limit=500)

        if channel:
            zoho = ZohoClient()
            zoho_records = zoho.search_by_criteria(channel=channel, limit=200)
            valid_record_ids = {r.get("record_id") for r in zoho_records}
            all_structured = [
                s for s in all_structured
                if s.get("zoho_record_id") in valid_record_ids
            ]

        distribution: Counter = Counter()

        for structured in all_structured:
            data = structured.get("data", {})
            if not data:
                continue

            if group_by == "reason":
                reasons = _extract_field(data, "transfer_reasons") or []
                for reason in (reasons if isinstance(reasons, list) else []):
                    distribution[reason] += 1
            elif group_by == "timing":
                timing = _extract_field(data, "desired_timing")
                if timing:
                    distribution[timing] += 1
            elif group_by == "vision":
                visions = _extract_field(data, "career_vision") or []
                for vision in (visions if isinstance(visions, list) else []):
                    distribution[vision] += 1

        return {
            "success": True,
            "group_by": group_by,
            "total_analyzed": len(all_structured),
            "distribution": dict(distribution.most_common(20)),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_candidate_briefing(record_id: str) -> Dict[str, Any]:
    """
    Generate candidate briefing for interview preparation.

    Args:
        record_id: Zoho record ID

    Returns:
        Comprehensive briefing with Zoho + structured data
    """
    logger.info(f"[ADK] generate_candidate_briefing: record_id={record_id}")

    if not record_id:
        return {"success": False, "error": "record_idを指定してください"}

    try:
        zoho = ZohoClient()
        zoho_record = zoho.get_app_hc_record(record_id)
        if not zoho_record:
            return {"success": False, "error": f"レコードが見つかりません"}

        structured = _get_structured_data_by_zoho_record(record_id)
        data = structured.get("data", {}) if structured else {}

        briefing = {
            "basic_info": {
                "name": zoho_record.get("Name", "不明"),
                "channel": zoho_record.get("field14"),
                "status": zoho_record.get("customer_status"),
            },
            "transfer_profile": {
                "activity_status": _extract_field(data, "transfer_activity_status"),
                "desired_timing": _extract_field(data, "desired_timing"),
                "transfer_reasons": _extract_field(data, "transfer_reasons"),
            },
            "conditions": {
                "current_salary": _extract_field(data, "current_salary"),
                "desired_first_year_salary": _extract_field(data, "desired_first_year_salary"),
            },
            "competition_status": {
                "current_agents": _extract_field(data, "current_agents"),
                "other_offer_salary": _extract_field(data, "other_offer_salary"),
            },
        }

        return {
            "success": True,
            "record_id": record_id,
            "briefing": briefing,
        }

    except ZohoAuthError:
        return {"success": False, "error": "Zoho認証エラー"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# List of ADK-compatible tools
ADK_CANDIDATE_INSIGHT_TOOLS = [
    analyze_competitor_risk,
    assess_candidate_urgency,
    analyze_transfer_patterns,
    generate_candidate_briefing,
]
