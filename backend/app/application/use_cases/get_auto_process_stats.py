from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl
from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl
from app.infrastructure.supabase.repositories.ai_usage_repository_impl import AiUsageRepositoryImpl
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class GetAutoProcessStatsUseCase:
    """自動処理の統計情報を取得するためのユースケース"""
    
    def __init__(self):
        self._meeting_repo = None
        self._structured_repo = None
        self._ai_usage_repo = None
        self.settings = get_settings()
    
    @property
    def meeting_repo(self) -> MeetingRepositoryImpl:
        if self._meeting_repo is None:
            self._meeting_repo = MeetingRepositoryImpl()
        return self._meeting_repo

    @meeting_repo.setter
    def meeting_repo(self, value: MeetingRepositoryImpl) -> None:
        self._meeting_repo = value

    @property
    def structured_repo(self) -> StructuredRepositoryImpl:
        if self._structured_repo is None:
            self._structured_repo = StructuredRepositoryImpl()
        return self._structured_repo

    @structured_repo.setter
    def structured_repo(self, value: StructuredRepositoryImpl) -> None:
        self._structured_repo = value

    @property
    def ai_usage_repo(self) -> AiUsageRepositoryImpl:
        if self._ai_usage_repo is None:
            self._ai_usage_repo = AiUsageRepositoryImpl()
        return self._ai_usage_repo

    @ai_usage_repo.setter
    def ai_usage_repo(self, value: AiUsageRepositoryImpl) -> None:
        self._ai_usage_repo = value

    def execute(
        self, 
        days_back: int = 7,
        include_detailed_metrics: bool = True
    ) -> Dict[str, Any]:
        """
        自動処理の統計情報を取得する
        
        Args:
            days_back: 何日前からの統計を取得するか
            include_detailed_metrics: 詳細メトリクスを含めるか
            
        Returns:
            統計情報の辞書
        """
        logger.info(f"[stats] collecting auto-process stats for last {days_back} days")

        # Refresh settings to pick up latest configuration
        self.settings = get_settings()
        settings = self.settings
        
        # 期間の設定
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)
        
        # 基本統計を収集
        basic_stats = self._collect_basic_stats(start_date, end_date)
        
        # 処理統計を収集
        processing_stats = self._collect_processing_stats(start_date, end_date)
        
        # パフォーマンスメトリクスを収集
        performance_metrics = self._collect_performance_metrics(start_date, end_date)
        
        # コスト統計を収集
        cost_metrics = self._collect_cost_metrics(start_date, end_date)
        
        # エラー分析
        error_analysis = self._collect_error_analysis(start_date, end_date)
        
        # 詳細メトリクスを含める場合
        detailed_metrics = {}
        if include_detailed_metrics:
            detailed_metrics = self._collect_detailed_metrics(start_date, end_date)
        
        # アラート状況をチェック
        alerts = self._check_alert_conditions(processing_stats, performance_metrics, cost_metrics)
        
        stats = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days_back
            },
            "basic_stats": basic_stats,
            "processing_stats": processing_stats,
            "performance_metrics": performance_metrics,
            "cost_metrics": cost_metrics,
            "error_analysis": error_analysis,
            "alerts": alerts,
            "settings": {
                "parallel_workers": settings.autoproc_parallel_workers,
                "batch_size": settings.autoproc_batch_size,
                "max_items": settings.autoproc_max_items,
                "success_rate_threshold": settings.autoproc_success_rate_threshold,
                "queue_alert_threshold": settings.autoproc_queue_alert_threshold,
                "error_rate_threshold": settings.autoproc_error_rate_threshold
            },
            **detailed_metrics
        }
        
        logger.info(f"[stats] collected stats: processed={processing_stats.get('total_processed', 0)} errors={error_analysis.get('total_errors', 0)}")
        
        return stats
    
    def _collect_basic_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """基本統計情報を収集"""
        try:
            # TODO: Implement database queries for basic stats
            # For now, return mock data structure
            return {
                "total_meetings": 0,  # Total meetings in database
                "unstructured_meetings": 0,  # Meetings without structured output
                "structured_meetings": 0,  # Meetings with structured output
                "first_time_meetings": 0,  # Meetings with "初回" in title
                "zoho_matchable_meetings": 0,  # Meetings that could match Zoho candidates
            }
        except Exception as e:
            logger.error(f"[stats] error collecting basic stats: {e}")
            return {}
    
    def _collect_processing_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """処理統計情報を収集"""
        try:
            # TODO: Implement processing stats collection
            return {
                "total_processed": 0,
                "successful_processed": 0,
                "failed_processed": 0,
                "skipped_no_text": 0,
                "skipped_not_first": 0,
                "skipped_no_title_match": 0,
                "skipped_zoho_not_exact": 0,
                "success_rate": 0.0,
                "daily_processing_rate": 0.0
            }
        except Exception as e:
            logger.error(f"[stats] error collecting processing stats: {e}")
            return {}
    
    def _collect_performance_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """パフォーマンスメトリクスを収集"""
        try:
            # TODO: Collect performance data from AI usage logs
            return {
                "avg_processing_time_seconds": 0.0,
                "min_processing_time_seconds": 0.0,
                "max_processing_time_seconds": 0.0,
                "avg_items_per_minute": 0.0,
                "parallel_efficiency": 0.0,  # How well parallel processing is working
                "timeout_incidents": 0,
                "retry_incidents": 0
            }
        except Exception as e:
            logger.error(f"[stats] error collecting performance metrics: {e}")
            return {}
    
    def _collect_cost_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """コストメトリクスを収集"""
        try:
            # Collect AI usage data
            usage_data = self._get_ai_usage_summary(start_date, end_date)
            
            return {
                "total_tokens_used": usage_data.get("total_tokens", 0),
                "total_tokens": usage_data.get("total_tokens", 0),
                "total_api_calls": usage_data.get("total_calls", 0),
                "estimated_cost_usd": usage_data.get("estimated_cost", 0.0),
                "estimated_cost": usage_data.get("estimated_cost", 0.0),
                "avg_tokens_per_meeting": usage_data.get("avg_tokens_per_meeting", 0),
                "cost_per_meeting_usd": usage_data.get("cost_per_meeting", 0.0),
                "model_usage_breakdown": usage_data.get("model_breakdown", {}),
                "daily_cost_trend": usage_data.get("daily_trend", [])
            }
        except Exception as e:
            logger.error(f"[stats] error collecting cost metrics: {e}")
            return {
                "total_tokens_used": 0,
                "total_tokens": 0,
                "total_api_calls": 0,
                "estimated_cost_usd": 0.0,
                "estimated_cost": 0.0,
                "avg_tokens_per_meeting": 0,
                "cost_per_meeting_usd": 0.0,
                "model_usage_breakdown": {},
                "daily_cost_trend": []
            }
    
    def _collect_error_analysis(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """エラー分析を収集"""
        try:
            # TODO: Analyze error patterns from logs
            return {
                "total_errors": 0,
                "error_rate": 0.0,
                "error_types": {},  # Dict of error type -> count
                "most_common_errors": [],  # List of most frequent errors
                "error_trend": []  # Daily error counts
            }
        except Exception as e:
            logger.error(f"[stats] error collecting error analysis: {e}")
            return {}
    
    def _collect_detailed_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """詳細メトリクスを収集"""
        try:
            return {
                "candidate_name_extraction_stats": {
                    "successful_extractions": 0,
                    "failed_extractions": 0,
                    "most_common_names": []
                },
                "zoho_integration_stats": {
                    "successful_lookups": 0,
                    "failed_lookups": 0,
                    "successful_writes": 0,
                    "failed_writes": 0,
                    "avg_lookup_time": 0.0
                },
                "gemini_api_stats": {
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "avg_response_time": 0.0,
                    "rate_limit_hits": 0
                }
            }
        except Exception as e:
            logger.error(f"[stats] error collecting detailed metrics: {e}")
            return {}
    
    def _get_ai_usage_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """AI使用量の要約を取得"""
        try:
            # Get AI usage data from the database
            raw_usage = self.ai_usage_repo.get_usage_summary()
            if isinstance(raw_usage, dict):
                usage_logs = raw_usage.get("usage_logs", [])
            else:
                usage_logs = raw_usage or []

            total_tokens = 0
            total_calls = 0
            model_breakdown = {}
            daily_trend = []
            
            for log in usage_logs:
                # Ensure log is a dictionary
                if not isinstance(log, dict):
                    continue
                tokens = log.get("total_token_count", 0) or 0
                total_tokens += tokens
                total_calls += 1
                
                model = log.get("model", "unknown")
                if model not in model_breakdown:
                    model_breakdown[model] = {"calls": 0, "tokens": 0}
                model_breakdown[model]["calls"] += 1
                model_breakdown[model]["tokens"] += tokens
            
            # Estimate cost (rough calculation for Gemini pricing)
            # These rates are approximate and should be updated based on actual pricing
            estimated_cost = 0.0
            for model, data in model_breakdown.items():
                if "flash" in model.lower():
                    # Flash model is cheaper
                    estimated_cost += data["tokens"] * 0.000001  # $0.000001 per token estimate
                elif "pro" in model.lower():
                    # Pro model is more expensive
                    estimated_cost += data["tokens"] * 0.000003  # $0.000003 per token estimate
            
            avg_tokens_per_meeting = total_tokens / max(total_calls, 1)
            cost_per_meeting = estimated_cost / max(total_calls, 1)
            
            return {
                "total_tokens": total_tokens,
                "total_calls": total_calls,
                "estimated_cost": round(estimated_cost, 4),
                "avg_tokens_per_meeting": round(avg_tokens_per_meeting, 0),
                "cost_per_meeting": round(cost_per_meeting, 4),
                "model_breakdown": model_breakdown,
                "daily_trend": daily_trend
            }
            
        except Exception as e:
            logger.error(f"[stats] error getting AI usage summary: {e}")
            return {
                "total_tokens": 0,
                "total_calls": 0,
                "estimated_cost": 0.0,
                "avg_tokens_per_meeting": 0,
                "cost_per_meeting": 0.0,
                "model_breakdown": {},
                "daily_trend": []
            }
    
    def _check_alert_conditions(
        self, 
        processing_stats: Dict[str, Any], 
        performance_metrics: Dict[str, Any], 
        cost_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """アラート条件をチェック"""
        alerts = []
        
        try:
            # Success rate alert
            success_rate = processing_stats.get("success_rate", 1.0)
            if success_rate < self.settings.autoproc_success_rate_threshold:
                alerts.append({
                    "type": "success_rate_low",
                    "severity": "warning",
                    "message": f"Success rate ({success_rate:.1%}) is below threshold ({self.settings.autoproc_success_rate_threshold:.1%})",
                    "value": success_rate,
                    "threshold": self.settings.autoproc_success_rate_threshold
                })
            
            # Error rate alert
            error_rate = processing_stats.get("failed_processed", 0) / max(processing_stats.get("total_processed", 1), 1)
            if error_rate > self.settings.autoproc_error_rate_threshold:
                alerts.append({
                    "type": "error_rate_high",
                    "severity": "critical",
                    "message": f"Error rate ({error_rate:.1%}) is above threshold ({self.settings.autoproc_error_rate_threshold:.1%})",
                    "value": error_rate,
                    "threshold": self.settings.autoproc_error_rate_threshold
                })
            
            # Cost alert (example: monthly cost projection > $100)
            daily_cost = cost_metrics.get("estimated_cost_usd", 0)
            monthly_projection = daily_cost * 30
            if monthly_projection > 100:
                alerts.append({
                    "type": "cost_high",
                    "severity": "warning",
                    "message": f"Monthly cost projection (${monthly_projection:.2f}) exceeds budget limit",
                    "value": monthly_projection,
                    "threshold": 100
                })
            
            # Performance alert
            avg_processing_time = performance_metrics.get("avg_processing_time_seconds", 0)
            if avg_processing_time > 60:  # More than 1 minute per item
                alerts.append({
                    "type": "performance_slow",
                    "severity": "warning",
                    "message": f"Average processing time ({avg_processing_time:.1f}s) is unusually high",
                    "value": avg_processing_time,
                    "threshold": 60
                })
                
        except Exception as e:
            logger.error(f"[stats] error checking alert conditions: {e}")
            alerts.append({
                "type": "stats_error",
                "severity": "error",
                "message": f"Error checking alert conditions: {str(e)}"
            })
        
        return alerts