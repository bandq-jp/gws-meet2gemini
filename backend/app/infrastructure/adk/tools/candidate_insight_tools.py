"""
Candidate Insight Tools for Google ADK.

ADK-native tool definitions for candidate analysis.
These are plain Python functions that ADK will automatically wrap.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from collections import Counter

from google.adk.tools.tool_context import ToolContext

from app.infrastructure.zoho.client import ZohoClient, ZohoAuthError
from app.infrastructure.supabase.client import get_supabase

logger = logging.getLogger(__name__)

# ZohoClient singleton
_zoho_client_instance = None


def _get_zoho_client():
    """ZohoClient シングルトン取得。"""
    global _zoho_client_instance
    if _zoho_client_instance is None:
        _zoho_client_instance = ZohoClient()
    return _zoho_client_instance


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
    競合エージェントリスク分析。他社オファー・選考中企業を持つ高リスク候補者を特定。

    Args:
        channel: チャネル指定 (paid_meta, sco_bizreach等)
        date_from: 開始日 (YYYY-MM-DD)
        date_to: 終了日 (YYYY-MM-DD)
        limit: 分析対象最大件数

    Returns:
        Dict[str, Any]: 分析結果。high_risk_candidates（高リスク候補者リスト）、
                       competitor_agents（競合エージェント出現頻度）、
                       popular_companies（選考中企業出現頻度）を含む
    """
    logger.info(f"[ADK] analyze_competitor_risk: channel={channel}")

    try:
        zoho = _get_zoho_client()
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
    候補者の緊急度を評価。転職希望時期・離職状況・他社オファーから優先順位を算出。

    Args:
        channel: チャネル指定
        status: ステータス指定
        date_from: 開始日 (YYYY-MM-DD)
        date_to: 終了日 (YYYY-MM-DD)
        limit: 分析対象最大件数

    Returns:
        Dict[str, Any]: 緊急度評価結果。urgency_distribution（緊急度分布）、
                       priority_queue（スコア順優先候補者リスト）を含む
    """
    logger.info(f"[ADK] assess_candidate_urgency: channel={channel}")

    try:
        zoho = _get_zoho_client()
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
    転職パターン分析。転職理由・希望時期・キャリアビジョンの傾向を可視化。

    Args:
        channel: チャネル指定
        group_by: 集計軸 ("reason": 転職理由, "timing": 希望時期, "vision": キャリアビジョン)

    Returns:
        Dict[str, Any]: パターン分析結果。group_by（集計軸）、total_analyzed（分析件数）、
                       distribution（パターン分布）を含む
    """
    logger.info(f"[ADK] analyze_transfer_patterns: group_by={group_by}")

    try:
        all_structured = _get_all_structured_data_with_sync(limit=500)

        if channel:
            zoho = _get_zoho_client()
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


def generate_candidate_briefing(record_id: str, tool_context: ToolContext = None) -> Dict[str, Any]:
    """
    面談ブリーフィング生成。Zoho基本情報+議事録構造化データを統合した準備資料。get_candidate_full_profileとの違い：こちらはリスク分析付きの面談準備に特化。

    Args:
        record_id: ZohoレコードID

    Returns:
        Dict[str, Any]: 面談準備資料。basic_info（基本情報）、transfer_profile（転職プロフィール）、
                       conditions（条件）、competition_status（競合状況）を含む
    """
    logger.info(f"[ADK] generate_candidate_briefing: record_id={record_id}")

    if not record_id:
        return {"success": False, "error": "record_idを指定してください"}

    try:
        zoho = _get_zoho_client()
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

        # Track briefed candidates in user state
        if tool_context:
            try:
                briefed = tool_context.state.get("user:briefed_candidates", [])
                name = briefing.get("basic_info", {}).get("name", "不明")
                entry = {"record_id": record_id, "name": name}
                existing_ids = {b.get("record_id") for b in briefed if isinstance(b, dict)}
                if record_id not in existing_ids:
                    briefed = briefed + [entry]
                    if len(briefed) > 20:
                        briefed = briefed[-20:]
                    tool_context.state["user:briefed_candidates"] = briefed
            except Exception:
                pass

        return {
            "success": True,
            "record_id": record_id,
            "briefing": briefing,
        }

    except ZohoAuthError:
        return {"success": False, "error": "Zoho認証エラー"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_candidate_summary(
    record_id: str,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """候補者サマリーをワンショット取得。Zoho基本情報+構造化データ+リスク評価を統合。

    generate_candidate_briefingとget_candidate_full_profileの簡易版。
    1回の呼び出しで候補者の全体像を高速取得。

    Args:
        record_id: ZohoレコードID

    Returns:
        Dict[str, Any]: 統合サマリー。
            success: True/False
            basic_info: 基本情報（名前、年齢、チャネル、ステータス）
            transfer_profile: 転職プロファイル（理由、希望条件）
            risk_level: リスクレベル（high/medium/low）
            recommended_actions: 推奨アクション
    """
    logger.info(f"[ADK] get_candidate_summary: record_id={record_id}")

    if not record_id:
        return {"success": False, "error": "record_idを指定してください"}

    try:
        # 1. Zoho基本情報取得
        zoho = _get_zoho_client()
        zoho_record = zoho.get_app_hc_record(record_id)
        if not zoho_record:
            return {"success": False, "error": f"レコードが見つかりません: {record_id}"}

        owner = zoho_record.get("Owner")
        pic_name = owner.get("name") if isinstance(owner, dict) else str(owner) if owner else "未割当"

        basic_info = {
            "name": zoho_record.get("Name", "不明"),
            "age": zoho_record.get("field15"),
            "gender": zoho_record.get("field16"),
            "channel": zoho_record.get("field14"),
            "status": zoho_record.get("customer_status"),
            "pic": pic_name,
            "registered_at": zoho_record.get("field18"),
            "current_salary": zoho_record.get("field17"),
            "desired_salary": zoho_record.get("field20"),
        }

        # 2. 構造化データ取得
        structured = _get_structured_data_by_zoho_record(record_id)
        data = structured.get("data", {}) if structured else {}

        transfer_profile = {
            "activity_status": _extract_field(data, "transfer_activity_status"),
            "desired_timing": _extract_field(data, "desired_timing"),
            "transfer_reasons": _extract_field(data, "transfer_reasons"),
            "career_vision": _extract_field(data, "career_vision"),
            "current_job_status": _extract_field(data, "current_job_status"),
            "desired_first_year_salary": _extract_field(data, "desired_first_year_salary"),
            "desired_industries": _extract_field(data, "desired_industries"),
            "desired_positions": _extract_field(data, "desired_positions"),
        }

        # 3. リスク評価
        risk_score = 0
        risk_factors = []

        # 他社オファーの有無
        other_offer = _extract_field(data, "other_offer_salary")
        if other_offer:
            risk_score += 40
            risk_factors.append(f"他社オファーあり: {other_offer}")

        # 競合エージェント
        current_agents = _extract_field(data, "current_agents")
        if current_agents:
            agents_str = str(current_agents)
            agent_count = len([a.strip() for a in agents_str.replace("、", ",").split(",") if a.strip()])
            if agent_count >= 3:
                risk_score += 30
                risk_factors.append(f"競合エージェント{agent_count}社")
            elif agent_count >= 1:
                risk_score += 15
                risk_factors.append(f"競合エージェント{agent_count}社")

        # 転職活動状況
        activity_status = _extract_field(data, "transfer_activity_status")
        if activity_status in ["最終面接待ち ~ 内定済み"]:
            risk_score += 30
            risk_factors.append(f"活動状況: {activity_status}")
        elif activity_status in ["企業打診済み ~ 一次選考フェーズ"]:
            risk_score += 15
            risk_factors.append(f"活動状況: {activity_status}")

        # 希望時期の緊急度
        timing = _extract_field(data, "desired_timing")
        if timing == "すぐにでも":
            risk_score += 10
            risk_factors.append("転職希望: すぐにでも")

        # リスクレベル判定
        if risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 20:
            risk_level = "medium"
        else:
            risk_level = "low"

        # 4. 推奨アクション
        recommended_actions = []

        if risk_level == "high":
            recommended_actions.append("早急に面談・企業提案を実施し、他社に先行する")
            if other_offer:
                recommended_actions.append("他社オファー条件をヒアリングし、上回る提案を準備")
        elif risk_level == "medium":
            recommended_actions.append("定期的なフォローアップで関係性を維持")
            if current_agents:
                recommended_actions.append("差別化ポイントを明確にした企業提案を実施")
        else:
            recommended_actions.append("ヒアリングを深め、転職軸を明確化")

        job_status = _extract_field(data, "current_job_status")
        if job_status == "離職中":
            recommended_actions.append("離職中のため、早期入社可能な求人を優先提案")

        if timing == "すぐにでも":
            recommended_actions.append("即時対応可能な求人を優先的にマッチング")

        # Track analyzed candidates in user state
        if tool_context:
            try:
                analyzed = tool_context.state.get("user:analyzed_candidates", [])
                entry = {
                    "record_id": record_id,
                    "name": basic_info.get("name", "不明"),
                    "risk_level": risk_level,
                }
                existing_ids = {a.get("record_id") for a in analyzed if isinstance(a, dict)}
                if record_id not in existing_ids:
                    analyzed = analyzed + [entry]
                    if len(analyzed) > 30:
                        analyzed = analyzed[-30:]
                    tool_context.state["user:analyzed_candidates"] = analyzed
            except Exception:
                pass

        return {
            "success": True,
            "record_id": record_id,
            "basic_info": basic_info,
            "transfer_profile": transfer_profile,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "recommended_actions": recommended_actions,
            "competition_status": {
                "current_agents": current_agents,
                "other_offer_salary": other_offer,
                "companies_in_selection": _extract_field(data, "companies_in_selection"),
            },
        }

    except ZohoAuthError:
        return {"success": False, "error": "Zoho認証エラー"}
    except Exception as e:
        logger.error(f"[ADK] get_candidate_summary error: {e}")
        return {"success": False, "error": str(e)}


# List of ADK-compatible tools
ADK_CANDIDATE_INSIGHT_TOOLS = [
    analyze_competitor_risk,
    assess_candidate_urgency,
    analyze_transfer_patterns,
    generate_candidate_briefing,
    get_candidate_summary,
]
