"""
AI使用量リポジトリ実装

Gemini API呼び出しのトークン使用量をSupabaseに永続化する。
DDD/オニオンアーキテクチャに従い、インフラ層でのデータ永続化責任を担う。
"""
from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional
from app.infrastructure.supabase.client import get_supabase

logger = logging.getLogger(__name__)


class AiUsageRepositoryImpl:
    """AI使用量リポジトリ実装"""
    
    TABLE = "ai_usage_logs"
    
    def insert_many(self, meeting_id: str, events: List[Dict[str, Any]]) -> None:
        """使用量イベントを一括挿入する
        
        Args:
            meeting_id: 会議ID
            events: 使用量イベントのリスト（UsageEvent.to_dict()の結果）
        """
        if not events:
            logger.debug("No usage events to insert")
            return
            
        try:
            sb = get_supabase()
            
            # meeting_idを各イベントに追加
            payload = [
                {**event, "meeting_id": meeting_id}
                for event in events
            ]
            
            # 大量データの場合は分割挿入を考慮（現在はシンプルな実装）
            result = sb.table(self.TABLE).insert(payload).execute()
            
            logger.info(
                f"AI使用量ログを挿入完了: meeting_id={meeting_id}, "
                f"events_count={len(events)}, "
                f"inserted_rows={len(result.data) if result.data else 0}"
            )
            
        except Exception as e:
            logger.error(
                f"AI使用量ログ挿入エラー: meeting_id={meeting_id}, "
                f"events_count={len(events)}, error={str(e)}"
            )
            # エラーが発生しても構造化データ処理は継続させるため、例外を再発生させない
    
    def get_usage_by_meeting(self, meeting_id: str) -> List[Dict[str, Any]]:
        """指定された会議IDの使用量ログを取得する
        
        Args:
            meeting_id: 会議ID
            
        Returns:
            使用量ログのリスト
        """
        try:
            sb = get_supabase()
            result = sb.table(self.TABLE).select("*").eq("meeting_id", meeting_id).order("created_at").execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(
                f"AI使用量ログ取得エラー: meeting_id={meeting_id}, error={str(e)}"
            )
            return []
    
    def get_usage_summary(self, limit: int = 100) -> Dict[str, Any]:
        """使用量の要約統計を取得する
        
        Args:
            limit: 取得件数制限
            
        Returns:
            使用量の要約統計
        """
        try:
            sb = get_supabase()
            
            # 最新の使用量データを取得
            result = sb.table(self.TABLE).select(
                "id, meeting_id, model, group_name, prompt_token_count, candidates_token_count, "
                "cached_content_token_count, total_token_count, latency_ms, created_at"
            ).order("created_at", desc=True).limit(limit).execute()
            
            if not result.data:
                return {"total_records": 0, "usage_logs": []}
            
            # 基本統計を計算
            usage_logs = result.data
            total_prompt_tokens = sum(
                log.get("prompt_token_count", 0) or 0 for log in usage_logs
            )
            total_candidates_tokens = sum(
                log.get("candidates_token_count", 0) or 0 for log in usage_logs
            )
            total_cached_tokens = sum(
                log.get("cached_content_token_count", 0) or 0 for log in usage_logs
            )
            avg_latency = sum(
                log.get("latency_ms", 0) or 0 for log in usage_logs
            ) / len(usage_logs) if usage_logs else 0
            
            return {
                "total_records": len(usage_logs),
                "total_prompt_tokens": total_prompt_tokens,
                "total_candidates_tokens": total_candidates_tokens,
                "total_cached_tokens": total_cached_tokens,
                "average_latency_ms": round(avg_latency, 2),
                "usage_logs": usage_logs
            }
            
        except Exception as e:
            logger.error(f"AI使用量要約取得エラー: error={str(e)}")
            return {"total_records": 0, "usage_logs": [], "error": str(e)}