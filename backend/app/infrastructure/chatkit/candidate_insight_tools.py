"""
Candidate Insight Tools - 候補者インサイト分析ツール

Zoho CRMデータとSupabase構造化データ（議事録抽出）を組み合わせた
転職エージェント業務向けの高度な分析ツールを提供します。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from collections import Counter

from agents import function_tool, RunContextWrapper

from app.infrastructure.zoho.client import ZohoClient, ZohoAuthError
from app.infrastructure.supabase.client import get_supabase

logger = logging.getLogger(__name__)


# --- Supabaseデータアクセスヘルパー ---

def _get_structured_data_by_zoho_record(zoho_record_id: str) -> Optional[Dict[str, Any]]:
    """Zoho record_idから構造化データを取得"""
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
    """同期済み構造化データを一括取得（集計用）"""
    try:
        sb = get_supabase()
        res = sb.table("structured_outputs").select(
            "meeting_id, data, zoho_record_id, zoho_candidate_name, created_at"
        ).not_.is_("zoho_record_id", "null").limit(limit).execute()
        return res.data or []
    except Exception as e:
        logger.warning(f"Failed to get structured data: {e}")
        return []


def _extract_field(data: Dict[str, Any], field_name: str) -> Any:
    """構造化データから特定フィールドを安全に抽出"""
    if not data or not isinstance(data, dict):
        return None
    return data.get(field_name)


# --- ツール定義 ---

@function_tool(name_override="analyze_competitor_risk")
async def analyze_competitor_risk(
    ctx: RunContextWrapper[Any],
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    競合エージェント分析ツール。
    候補者が利用している他社エージェントと選考状況から、
    競合リスクを評価し、対応優先度を判定します。

    Args:
        channel: 流入経路でフィルタ（省略時は全体）
        date_from: 分析期間の開始日（YYYY-MM-DD形式）
        date_to: 分析期間の終了日（YYYY-MM-DD形式）
        limit: 分析対象件数（最大100）

    Returns:
        競合リスク分析結果:
        - high_risk_candidates: 即座に対応が必要な候補者
        - competitor_agents: 競合エージェント出現頻度
        - selection_in_progress: 選考中企業の傾向
        - recommendations: 対応提案

    使用例:
        - Meta広告経由候補者の競合状況を把握
        - 他社オファーがある候補者を優先対応
        - 競合エージェントの強み・弱みを分析
    """
    logger.info(
        "[candidate_insight_tools] analyze_competitor_risk: channel=%s, date_from=%s, date_to=%s",
        channel, date_from, date_to
    )

    try:
        zoho = ZohoClient()

        # Zohoから候補者リストを取得
        records = zoho.search_by_criteria(
            channel=channel,
            date_from=date_from,
            date_to=date_to,
            limit=min(limit, 100),
        )

        high_risk_candidates = []
        competitor_agents: Counter = Counter()
        companies_in_selection: Counter = Counter()
        other_offers = []

        for record in records:
            record_id = record.get("record_id")
            if not record_id:
                continue

            # Supabaseから構造化データを取得
            structured = _get_structured_data_by_zoho_record(record_id)
            if not structured:
                continue

            data = structured.get("data", {})

            # 競合エージェント分析
            current_agents = _extract_field(data, "current_agents")
            if current_agents:
                # カンマやスペースで分割して集計
                agents = [a.strip() for a in str(current_agents).replace("、", ",").split(",") if a.strip()]
                for agent in agents:
                    competitor_agents[agent] += 1

            # 選考中企業分析
            companies = _extract_field(data, "companies_in_selection") or []
            for company in companies if isinstance(companies, list) else []:
                if company:
                    companies_in_selection[str(company).split("（")[0].strip()] += 1

            # 他社オファー年収
            other_salary = _extract_field(data, "other_offer_salary")

            # 転職活動状況
            activity_status = _extract_field(data, "transfer_activity_status")

            # 高リスク判定（他社オファーありor最終面接段階）
            is_high_risk = False
            risk_reasons = []

            if other_salary:
                is_high_risk = True
                risk_reasons.append(f"他社オファー見込み: {other_salary}")

            if activity_status in ["最終面接待ち ~ 内定済み", "企業打診済み ~ 一次選考フェーズ"]:
                is_high_risk = True
                risk_reasons.append(f"活動状況: {activity_status}")

            if len(companies if isinstance(companies, list) else []) >= 3:
                is_high_risk = True
                risk_reasons.append(f"選考中企業: {len(companies)}社")

            if is_high_risk:
                high_risk_candidates.append({
                    "record_id": record_id,
                    "name": record.get("求職者名", "不明"),
                    "status": record.get("顧客ステータス"),
                    "channel": record.get("流入経路"),
                    "risk_reasons": risk_reasons,
                    "current_agents": current_agents,
                    "companies_in_selection": companies,
                    "other_offer_salary": other_salary,
                })

            if other_salary:
                other_offers.append({
                    "name": record.get("求職者名", "不明"),
                    "salary": other_salary,
                    "status": record.get("顧客ステータス"),
                })

        # 結果整理
        return {
            "success": True,
            "period": {
                "from": date_from or "全期間",
                "to": date_to or "現在",
            },
            "channel_filter": channel or "全体",
            "analyzed_count": len(records),
            "high_risk_count": len(high_risk_candidates),
            "high_risk_candidates": high_risk_candidates[:10],  # 上位10件
            "competitor_agents": dict(competitor_agents.most_common(10)),
            "popular_companies": dict(companies_in_selection.most_common(10)),
            "candidates_with_offers": other_offers[:5],
            "recommendations": _generate_competitor_recommendations(
                high_risk_candidates, competitor_agents
            ),
        }

    except ZohoAuthError as e:
        logger.error("[candidate_insight_tools] Zoho auth error: %s", e)
        return {"success": False, "error": "Zoho認証エラーが発生しました。"}
    except Exception as e:
        logger.error("[candidate_insight_tools] analyze_competitor_risk error: %s", e)
        return {"success": False, "error": f"競合分析中にエラーが発生しました: {str(e)}"}


def _generate_competitor_recommendations(
    high_risk: List[Dict], competitors: Counter
) -> List[str]:
    """競合分析に基づく推奨アクションを生成"""
    recommendations = []

    if high_risk:
        recommendations.append(
            f"⚠️ {len(high_risk)}名が高リスク（他社選考進行中）。"
            "即座のフォローアップを推奨します。"
        )

    top_competitors = competitors.most_common(3)
    if top_competitors:
        comp_names = "、".join([c[0] for c in top_competitors])
        recommendations.append(
            f"📊 主な競合エージェント: {comp_names}。"
            "差別化ポイントを明確にしてアプローチしましょう。"
        )

    return recommendations


@function_tool(name_override="assess_candidate_urgency")
async def assess_candidate_urgency(
    ctx: RunContextWrapper[Any],
    channel: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    候補者の緊急度を評価し、対応優先順位を付けます。
    転職希望時期、離職状況、選考進捗から緊急度スコアを算出します。

    Args:
        channel: 流入経路でフィルタ
        status: 顧客ステータスでフィルタ
        date_from: 分析期間の開始日（YYYY-MM-DD形式）
        date_to: 分析期間の終了日（YYYY-MM-DD形式）
        limit: 分析対象件数

    Returns:
        緊急度評価結果:
        - priority_queue: 優先度順の候補者リスト
        - urgency_distribution: 緊急度分布
        - immediate_action_required: 即座のアクションが必要な候補者

    使用例:
        - 本日対応すべき候補者を確認
        - 「すぐにでも転職したい」候補者を優先
        - 離職済み候補者をフォローアップ
    """
    logger.info(
        "[candidate_insight_tools] assess_candidate_urgency: channel=%s, status=%s",
        channel, status
    )

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

        for record in records:
            record_id = record.get("record_id")
            if not record_id:
                continue

            structured = _get_structured_data_by_zoho_record(record_id)
            if not structured:
                # 構造化データがない場合はスキップ or デフォルト
                continue

            data = structured.get("data", {})

            # 緊急度スコア計算
            score = 0
            factors = []

            # 1. 転職希望時期
            timing = _extract_field(data, "desired_timing")
            if timing == "すぐにでも":
                score += 40
                factors.append("希望時期: すぐにでも")
            elif timing == "3ヶ月以内":
                score += 30
                factors.append("希望時期: 3ヶ月以内")
            elif timing == "6ヶ月以内":
                score += 20
                factors.append("希望時期: 6ヶ月以内")

            # 2. 離職状況
            job_status = _extract_field(data, "current_job_status")
            if job_status == "離職中":
                score += 30
                factors.append("離職中")
            elif job_status == "離職確定":
                score += 20
                factors.append("離職確定")

            # 3. 転職活動状況
            activity = _extract_field(data, "transfer_activity_status")
            if activity == "最終面接待ち ~ 内定済み":
                score += 25
                factors.append("他社最終面接段階")
            elif activity == "企業打診済み ~ 一次選考フェーズ":
                score += 15
                factors.append("他社選考中")

            # 4. 他社オファー
            if _extract_field(data, "other_offer_salary"):
                score += 20
                factors.append("他社オファーあり")

            # 緊急度レベル判定
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
                "status": record.get("顧客ステータス"),
                "channel": record.get("流入経路"),
                "pic": record.get("PIC"),
                "urgency_score": score,
                "urgency_level": urgency,
                "factors": factors,
                "desired_timing": timing,
                "current_job_status": job_status,
            })

        # スコア順にソート
        urgency_scores.sort(key=lambda x: x["urgency_score"], reverse=True)

        # 即時アクション必要な候補者
        immediate = [c for c in urgency_scores if c["urgency_level"] == "即時"]

        return {
            "success": True,
            "period": {
                "from": date_from or "全期間",
                "to": date_to or "現在",
            },
            "filters": {
                "channel": channel or "全体",
                "status": status or "全体",
            },
            "analyzed_count": len(records),
            "urgency_distribution": urgency_distribution,
            "immediate_action_required": immediate[:10],
            "priority_queue": urgency_scores[:20],
            "recommendations": [
                f"🚨 {len(immediate)}名が即時対応必要です。" if immediate else "✅ 即時対応が必要な候補者はいません。",
                f"📋 本日の優先対応候補: {', '.join([c['name'] for c in urgency_scores[:3]])}" if urgency_scores else "",
            ],
        }

    except ZohoAuthError as e:
        logger.error("[candidate_insight_tools] Zoho auth error: %s", e)
        return {"success": False, "error": "Zoho認証エラーが発生しました。"}
    except Exception as e:
        logger.error("[candidate_insight_tools] assess_candidate_urgency error: %s", e)
        return {"success": False, "error": f"緊急度評価中にエラーが発生しました: {str(e)}"}


@function_tool(name_override="analyze_transfer_patterns")
async def analyze_transfer_patterns(
    ctx: RunContextWrapper[Any],
    channel: Optional[str] = None,
    group_by: str = "reason",
) -> Dict[str, Any]:
    """
    転職理由・動機のパターン分析を行います。
    マーケティング施策やコンテンツ企画の参考データを提供します。

    Args:
        channel: 特定チャネルで分析（省略時は全体）
        group_by: 集計軸 ("reason"=転職理由, "timing"=希望時期, "vision"=キャリアビジョン)

    Returns:
        パターン分析結果:
        - distribution: 集計結果
        - insights: インサイト
        - marketing_suggestions: マーケティング施策提案

    使用例:
        - Meta広告経由の候補者の転職理由傾向を分析
        - 「年収を上げたい」層の特徴を把握
        - コンテンツ企画のための動機分析
    """
    logger.info(
        "[candidate_insight_tools] analyze_transfer_patterns: channel=%s, group_by=%s",
        channel, group_by
    )

    try:
        # 構造化データを一括取得
        all_structured = _get_all_structured_data_with_sync(limit=500)

        if channel:
            # チャネルフィルタが必要な場合、Zohoから候補者を取得して紐付け
            zoho = ZohoClient()
            zoho_records = zoho.search_by_criteria(channel=channel, limit=200)
            valid_record_ids = {r.get("record_id") for r in zoho_records}
            all_structured = [
                s for s in all_structured
                if s.get("zoho_record_id") in valid_record_ids
            ]

        distribution: Counter = Counter()
        total_analyzed = 0

        for structured in all_structured:
            data = structured.get("data", {})
            if not data:
                continue

            total_analyzed += 1

            if group_by == "reason":
                # 転職理由（複数選択可）
                reasons = _extract_field(data, "transfer_reasons") or []
                for reason in (reasons if isinstance(reasons, list) else []):
                    distribution[reason] += 1

            elif group_by == "timing":
                # 希望時期
                timing = _extract_field(data, "desired_timing")
                if timing:
                    distribution[timing] += 1

            elif group_by == "vision":
                # キャリアビジョン（複数選択可）
                visions = _extract_field(data, "career_vision") or []
                for vision in (visions if isinstance(visions, list) else []):
                    distribution[vision] += 1

        # 結果整理
        sorted_dist = dict(distribution.most_common(20))
        total = sum(distribution.values())

        # パーセンテージ付きで整形
        distribution_with_pct = {
            k: {"count": v, "pct": f"{v / total * 100:.1f}%" if total > 0 else "0%"}
            for k, v in sorted_dist.items()
        }

        # インサイト生成
        insights = _generate_pattern_insights(group_by, distribution, channel)

        return {
            "success": True,
            "channel_filter": channel or "全体",
            "group_by": group_by,
            "total_analyzed": total_analyzed,
            "total_responses": total,
            "distribution": distribution_with_pct,
            "top_3": list(sorted_dist.keys())[:3],
            "insights": insights,
            "marketing_suggestions": _generate_marketing_suggestions(group_by, distribution),
        }

    except Exception as e:
        logger.error("[candidate_insight_tools] analyze_transfer_patterns error: %s", e)
        return {"success": False, "error": f"パターン分析中にエラーが発生しました: {str(e)}"}


def _generate_pattern_insights(group_by: str, dist: Counter, channel: Optional[str]) -> List[str]:
    """パターン分析のインサイトを生成"""
    insights = []
    top = dist.most_common(3)

    if group_by == "reason" and top:
        insights.append(f"最も多い転職理由: 「{top[0][0]}」({top[0][1]}件)")
        if len(top) >= 2:
            insights.append(f"2位: 「{top[1][0]}」、3位: 「{top[2][0] if len(top) >= 3 else 'N/A'}」")

    elif group_by == "timing" and top:
        urgent = sum(dist.get(t, 0) for t in ["すぐにでも", "3ヶ月以内"])
        total = sum(dist.values())
        if total > 0:
            insights.append(f"緊急性の高い層（すぐ〜3ヶ月以内）: {urgent}/{total}名 ({urgent/total*100:.0f}%)")

    elif group_by == "vision" and top:
        insights.append(f"最も多いキャリアビジョン: 「{top[0][0]}」")

    return insights


def _generate_marketing_suggestions(group_by: str, dist: Counter) -> List[str]:
    """マーケティング施策提案を生成"""
    suggestions = []
    top = dist.most_common(5)

    if group_by == "reason":
        reason_to_content = {
            "給与が低い・昇給が見込めない": "年収アップ事例・高年収求人特集",
            "昇進・キャリアアップが望めない": "キャリアアップ成功事例",
            "スキルアップしたい": "スキルアップ転職特集",
            "業界・会社の先行きが不安": "成長業界・安定企業特集",
            "働き方に柔軟性がない（リモートワーク不可など）": "リモート可求人特集",
        }
        for reason, _ in top[:3]:
            if reason in reason_to_content:
                suggestions.append(f"📝 コンテンツ提案: {reason_to_content[reason]}")

    elif group_by == "vision":
        suggestions.append("キャリアビジョン別の求人マッチングコンテンツを検討")

    return suggestions


@function_tool(name_override="generate_candidate_briefing")
async def generate_candidate_briefing(
    ctx: RunContextWrapper[Any],
    record_id: str,
) -> Dict[str, Any]:
    """
    面談前準備用の候補者ブリーフィングを生成します。
    Zoho CRM情報と議事録から抽出した詳細情報を統合して表示します。

    Args:
        record_id: Zoho CRMのレコードID

    Returns:
        候補者ブリーフィング:
        - basic_info: 基本情報（名前、流入経路、ステータス）
        - transfer_profile: 転職プロファイル（理由、希望時期、軸）
        - career_summary: キャリアサマリー（職歴、経験業界）
        - conditions: 希望条件（年収、業界、職種）
        - competition_status: 競合状況（他社エージェント、選考中企業）
        - talking_points: 面談時のポイント

    使用例:
        - 面談前に候補者の詳細情報を確認
        - 過去の議事録から抽出した情報を一覧
        - 効果的な面談準備
    """
    logger.info("[candidate_insight_tools] generate_candidate_briefing: record_id=%s", record_id)

    if not record_id:
        return {"success": False, "error": "record_idを指定してください"}

    try:
        zoho = ZohoClient()

        # Zohoから基本情報を取得
        zoho_record = zoho.get_app_hc_record(record_id)
        if not zoho_record:
            return {"success": False, "error": f"レコードが見つかりません: {record_id}"}

        # Supabaseから構造化データを取得
        structured = _get_structured_data_by_zoho_record(record_id)
        data = structured.get("data", {}) if structured else {}

        # ブリーフィング構築
        briefing = {
            "basic_info": {
                "name": zoho_record.get("Name", "不明"),
                "record_id": record_id,
                "channel": zoho_record.get("field14"),
                "status": zoho_record.get("customer_status"),
                "pic": zoho_record.get("Owner", {}).get("name") if isinstance(zoho_record.get("Owner"), dict) else None,
                "registered_at": zoho_record.get("field18"),
            },
            "transfer_profile": {
                "activity_status": _extract_field(data, "transfer_activity_status"),
                "desired_timing": _extract_field(data, "desired_timing"),
                "current_job_status": _extract_field(data, "current_job_status"),
                "transfer_reasons": _extract_field(data, "transfer_reasons"),
                "transfer_priorities": _extract_field(data, "transfer_priorities"),
                "transfer_trigger": _extract_field(data, "transfer_trigger"),
            },
            "career_summary": {
                "career_history": _extract_field(data, "career_history"),
                "current_duties": _extract_field(data, "current_duties"),
                "experience_industry": _extract_field(data, "experience_industry"),
                "enjoyed_work": _extract_field(data, "enjoyed_work"),
                "difficult_work": _extract_field(data, "difficult_work"),
            },
            "conditions": {
                "current_salary": _extract_field(data, "current_salary"),
                "desired_first_year_salary": _extract_field(data, "desired_first_year_salary"),
                "salary_breakdown": _extract_field(data, "salary_breakdown"),
                "desired_industry": _extract_field(data, "desired_industry"),
                "desired_position": _extract_field(data, "desired_position"),
                "business_vision": _extract_field(data, "business_vision"),
                "career_vision": _extract_field(data, "career_vision"),
            },
            "competition_status": {
                "agent_count": _extract_field(data, "agent_count"),
                "current_agents": _extract_field(data, "current_agents"),
                "companies_in_selection": _extract_field(data, "companies_in_selection"),
                "other_offer_salary": _extract_field(data, "other_offer_salary"),
                "other_company_intention": _extract_field(data, "other_company_intention"),
            },
        }

        # 面談ポイント生成
        talking_points = _generate_talking_points(briefing)

        return {
            "success": True,
            "record_id": record_id,
            "has_structured_data": bool(data),
            "briefing": briefing,
            "talking_points": talking_points,
            "last_synced": structured.get("zoho_synced_at") if structured else None,
        }

    except ZohoAuthError as e:
        logger.error("[candidate_insight_tools] Zoho auth error: %s", e)
        return {"success": False, "error": "Zoho認証エラーが発生しました。"}
    except Exception as e:
        logger.error("[candidate_insight_tools] generate_candidate_briefing error: %s", e)
        return {"success": False, "error": f"ブリーフィング生成中にエラーが発生しました: {str(e)}"}


def _generate_talking_points(briefing: Dict[str, Any]) -> List[str]:
    """面談時のポイントを生成"""
    points = []

    profile = briefing.get("transfer_profile", {})
    conditions = briefing.get("conditions", {})
    competition = briefing.get("competition_status", {})

    # 転職理由に基づくポイント
    reasons = profile.get("transfer_reasons") or []
    if "給与が低い・昇給が見込めない" in reasons:
        current = conditions.get("current_salary")
        desired = conditions.get("desired_first_year_salary")
        points.append(f"💰 年収重視: 現年収{current}万→希望{desired}万。具体的な年収レンジを提示。")

    if "スキルアップしたい" in reasons:
        points.append("📈 成長志向: 教育制度やキャリアパスを強調。")

    # 競合状況に基づくポイント
    if competition.get("current_agents"):
        points.append(f"⚠️ 競合あり: {competition['current_agents']}を利用中。差別化ポイントを明確に。")

    if competition.get("other_offer_salary"):
        points.append(f"🎯 他社オファー: {competition['other_offer_salary']}。条件面での競争力を確認。")

    if competition.get("companies_in_selection"):
        companies = competition["companies_in_selection"]
        if isinstance(companies, list) and len(companies) >= 2:
            points.append(f"📋 選考中企業あり: {len(companies)}社。スピード感を持って対応。")

    # 希望時期に基づくポイント
    timing = profile.get("desired_timing")
    if timing == "すぐにでも":
        points.append("🚨 緊急: 即転職希望。即日〜翌日でのフォローを推奨。")
    elif timing == "3ヶ月以内":
        points.append("⏰ 3ヶ月以内希望: 具体的な求人提案を早めに。")

    # キャリアビジョンに基づくポイント
    vision = conditions.get("career_vision") or []
    if "マネージャー/企画/事業責任者" in vision:
        points.append("🎯 マネジメント志向: 管理職ポジションや将来的な昇格パスを提案。")
    if "独立" in vision:
        points.append("🏢 独立志向: 将来的な独立につながる経験が積める環境を提案。")

    if not points:
        points.append("ℹ️ 詳細情報を面談で確認してください。")

    return points


# エクスポート用のツールリスト
CANDIDATE_INSIGHT_TOOLS = [
    analyze_competitor_risk,
    assess_candidate_urgency,
    analyze_transfer_patterns,
    generate_candidate_briefing,
]
