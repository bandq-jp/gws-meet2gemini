"""
AIコスト取得UseCase

ai_usage_logsテーブルからデータを取得してコスト計算し、
フロントエンド向けに整理したデータを返す。
"""
from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from app.infrastructure.supabase.repositories.ai_usage_repository_impl import AiUsageRepositoryImpl
from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl
from app.domain.services.ai_cost_calculator import GeminiCostCalculator

logger = logging.getLogger(__name__)


class GetAiCostsUseCase:
    """AIコスト取得UseCase"""
    
    def __init__(self):
        self.usage_repo = AiUsageRepositoryImpl()
        self.meeting_repo = MeetingRepositoryImpl()
        self.cost_calculator = GeminiCostCalculator()
    
    def get_overall_summary(self, limit: int = 1000) -> Dict[str, Any]:
        """全体のコスト概要を取得
        
        Args:
            limit: 取得するレコード数上限
            
        Returns:
            全体統計とコスト情報
        """
        try:
            # 最新のusage_logsを取得
            usage_summary = self.usage_repo.get_usage_summary(limit=limit)
            usage_logs = usage_summary.get("usage_logs", [])
            
            if not usage_logs:
                return {
                    "summary": {
                        "total_cost_usd": "0.000000",
                        "total_meetings": 0,
                        "total_api_calls": 0,
                        "total_tokens": 0
                    },
                    "recent_meetings": [],
                    "cost_breakdown": {
                        "input_cost": "0.000000",
                        "output_cost": "0.000000",
                        "cache_cost": "0.000000"
                    }
                }
            
            # 全体コスト計算
            total_stats = self.cost_calculator.calculate_total_costs(usage_logs)
            
            # 会議別コスト集計
            meeting_costs = self._get_meetings_with_costs(limit=20)
            
            return {
                "summary": {
                    "total_cost_usd": total_stats["total_cost"],
                    "total_meetings": total_stats["meetings_count"],
                    "total_api_calls": total_stats["total_api_calls"],
                    "total_tokens": total_stats["total_prompt_tokens"] + total_stats["total_output_tokens"],
                    "total_prompt_tokens": total_stats["total_prompt_tokens"],
                    "total_output_tokens": total_stats["total_output_tokens"],
                    "average_cost_per_call": total_stats["average_cost_per_call"]
                },
                "cost_breakdown": {
                    "input_cost": total_stats["total_input_cost"],
                    "output_cost": total_stats["total_output_cost"],
                    "cache_cost": total_stats["total_cache_cost"]
                },
                "recent_meetings": meeting_costs,
                "last_updated": usage_logs[0].get("created_at") if usage_logs else None
            }
            
        except Exception as e:
            logger.error(f"全体コスト概要取得エラー: {e}")
            raise
    
    def get_meeting_detail(self, meeting_id: str) -> Dict[str, Any]:
        """特定会議の詳細コスト情報を取得
        
        Args:
            meeting_id: 会議ID
            
        Returns:
            会議の詳細コスト情報
        """
        try:
            # 使用量ログを取得
            usage_logs = self.usage_repo.get_usage_by_meeting(meeting_id)
            
            if not usage_logs:
                return {
                    "meeting_id": meeting_id,
                    "meeting_title": "不明",
                    "error": "使用量データが見つかりません"
                }
            
            # 会議情報を取得
            meeting = self.meeting_repo.get_meeting(meeting_id)
            meeting_title = meeting.get("title", "タイトル不明") if meeting else "会議情報なし"
            
            # コスト計算
            cost_summary = self.cost_calculator.calculate_meeting_costs(
                usage_logs, meeting_title
            )
            
            # API呼び出し詳細
            call_details = []
            for log in usage_logs:
                cost = self.cost_calculator.calculate_single_usage(
                    prompt_tokens=log.get("prompt_token_count", 0),
                    candidates_tokens=log.get("candidates_token_count", 0),
                    thoughts_tokens=0,  # DBスキーマには存在しないため0で設定
                    cached_tokens=log.get("cached_content_token_count", 0)
                )
                
                call_details.append({
                    "id": log.get("id"),
                    "group_name": log.get("group_name"),
                    "model": log.get("model"),
                    "prompt_tokens": cost.prompt_tokens,
                    "output_tokens": cost.output_tokens,
                    "cached_tokens": cost.cached_tokens,
                    "input_cost": str(cost.input_cost),
                    "output_cost": str(cost.output_cost),
                    "cache_cost": str(cost.cache_cost),
                    "total_cost": str(cost.total_cost),
                    "pricing_tier": cost.pricing_tier,
                    "latency_ms": log.get("latency_ms"),
                    "created_at": log.get("created_at")
                })
            
            return {
                "meeting_id": meeting_id,
                "meeting_title": meeting_title,
                "summary": {
                    "total_cost": str(cost_summary.total_cost),
                    "total_prompt_tokens": cost_summary.total_prompt_tokens,
                    "total_output_tokens": cost_summary.total_output_tokens,
                    "total_cached_tokens": cost_summary.total_cached_tokens,
                    "api_calls_count": cost_summary.api_calls_count,
                    "input_cost": str(cost_summary.total_input_cost),
                    "output_cost": str(cost_summary.total_output_cost),
                    "cache_cost": str(cost_summary.total_cache_cost)
                },
                "call_details": call_details,
                "created_at": cost_summary.created_at
            }
            
        except Exception as e:
            logger.error(f"会議詳細コスト取得エラー: meeting_id={meeting_id}, error={e}")
            raise
    
    def _get_meetings_with_costs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """AI使用量ログがある会議のみのコスト情報一覧を取得
        
        Args:
            limit: 取得する会議数上限
            
        Returns:
            AI処理済み会議のコスト情報リスト（usage_logsがある会議のみ）
        """
        try:
            # ai_usage_logsから会議IDを取得してから、該当する会議情報を取得する方針に変更
            usage_summary = self.usage_repo.get_usage_summary(limit=limit * 3)  # 余裕を持って取得
            all_usage_logs = usage_summary.get("usage_logs", [])
            
            if not all_usage_logs:
                return []
            
            # 会議IDごとにusage_logsをグループ化
            meeting_usage_map = {}
            for log in all_usage_logs:
                meeting_id = log.get("meeting_id")
                if meeting_id:
                    if meeting_id not in meeting_usage_map:
                        meeting_usage_map[meeting_id] = []
                    meeting_usage_map[meeting_id].append(log)
            
            # 各会議の詳細情報を取得してコスト計算
            meeting_costs = []
            processed_count = 0
            
            for meeting_id, usage_logs in meeting_usage_map.items():
                if processed_count >= limit:
                    break
                    
                # 会議詳細情報を取得
                meeting = self.meeting_repo.get_meeting(meeting_id)
                if not meeting:
                    continue  # 会議が見つからない場合はスキップ
                
                # コスト計算
                cost_summary = self.cost_calculator.calculate_meeting_costs(
                    usage_logs, meeting.get("title")
                )
                
                meeting_costs.append({
                    "meeting_id": meeting_id,
                    "meeting_title": meeting.get("title", "タイトル不明"),
                    "total_cost": str(cost_summary.total_cost),
                    "total_tokens": cost_summary.total_prompt_tokens + cost_summary.total_output_tokens,
                    "api_calls_count": cost_summary.api_calls_count,
                    "created_at": meeting.get("created_at")
                })
                
                processed_count += 1
            
            # 作成日時の降順でソート
            meeting_costs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            return meeting_costs[:limit]  # 最終的に指定された件数に制限
            
        except Exception as e:
            logger.error(f"会議別コスト一覧取得エラー: {e}")
            return []