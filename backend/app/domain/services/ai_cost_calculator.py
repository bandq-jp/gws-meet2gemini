"""
AIコスト計算サービス

Gemini 2.5 Proの料金体系に基づいてトークン使用量をコストに変換する。
ドメインサービスとしてビジネスルール（料金計算）を担当する。
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class TokenCost:
    """トークンコスト計算結果"""
    prompt_tokens: int
    output_tokens: int  # candidates + thoughts tokens
    cached_tokens: int
    input_cost: Decimal
    output_cost: Decimal
    cache_cost: Decimal
    total_cost: Decimal
    pricing_tier: str  # "standard" or "high_volume"


@dataclass
class MeetingCostSummary:
    """会議別コスト集計"""
    meeting_id: str
    meeting_title: Optional[str]
    total_prompt_tokens: int
    total_output_tokens: int
    total_cached_tokens: int
    total_input_cost: Decimal
    total_output_cost: Decimal
    total_cache_cost: Decimal
    total_cost: Decimal
    api_calls_count: int
    created_at: str


class GeminiCostCalculator:
    """Gemini 2.5 Pro コスト計算サービス"""
    
    # Gemini 2.5 Pro料金（per 1M tokens USD）
    # 20万トークン以下
    STANDARD_INPUT_RATE = Decimal("1.25")
    STANDARD_OUTPUT_RATE = Decimal("10.00")
    STANDARD_CACHE_RATE = Decimal("0.31")
    
    # 20万トークン超
    HIGH_VOLUME_INPUT_RATE = Decimal("2.50")
    HIGH_VOLUME_OUTPUT_RATE = Decimal("15.00")
    HIGH_VOLUME_CACHE_RATE = Decimal("0.625")
    
    # コンテキストキャッシュストレージ（per 1M tokens per hour）
    CACHE_STORAGE_RATE = Decimal("4.50")
    
    # 料金体系切り替え閾値
    HIGH_VOLUME_THRESHOLD = 200_000  # 20万トークン
    
    @classmethod
    def calculate_single_usage(
        self,
        prompt_tokens: int,
        candidates_tokens: int,
        thoughts_tokens: Optional[int] = None,
        cached_tokens: Optional[int] = None
    ) -> TokenCost:
        """単一のAPI呼び出しのコストを計算
        
        Args:
            prompt_tokens: 入力トークン数
            candidates_tokens: 候補出力トークン数
            thoughts_tokens: 思考トークン数
            cached_tokens: キャッシュトークン数
            
        Returns:
            TokenCost: 計算されたコスト情報
        """
        prompt_tokens = prompt_tokens or 0
        candidates_tokens = candidates_tokens or 0
        thoughts_tokens = thoughts_tokens or 0
        cached_tokens = cached_tokens or 0
        
        # 出力トークン = 候補 + 思考
        total_output_tokens = candidates_tokens + thoughts_tokens
        
        # 料金体系の決定（プロンプトトークン数で判定）
        is_high_volume = prompt_tokens > self.HIGH_VOLUME_THRESHOLD
        pricing_tier = "high_volume" if is_high_volume else "standard"
        
        # 料金レート選択
        input_rate = self.HIGH_VOLUME_INPUT_RATE if is_high_volume else self.STANDARD_INPUT_RATE
        output_rate = self.HIGH_VOLUME_OUTPUT_RATE if is_high_volume else self.STANDARD_OUTPUT_RATE
        cache_rate = self.HIGH_VOLUME_CACHE_RATE if is_high_volume else self.STANDARD_CACHE_RATE
        
        # コスト計算（per 1M tokens）
        input_cost = (Decimal(prompt_tokens) / Decimal("1000000")) * input_rate
        output_cost = (Decimal(total_output_tokens) / Decimal("1000000")) * output_rate
        cache_cost = (Decimal(cached_tokens) / Decimal("1000000")) * cache_rate
        
        # 小数点以下6桁で四捨五入
        input_cost = input_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        output_cost = output_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        cache_cost = cache_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        
        total_cost = input_cost + output_cost + cache_cost
        
        return TokenCost(
            prompt_tokens=prompt_tokens,
            output_tokens=total_output_tokens,
            cached_tokens=cached_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            cache_cost=cache_cost,
            total_cost=total_cost,
            pricing_tier=pricing_tier
        )
    
    @classmethod
    def calculate_meeting_costs(
        self,
        usage_logs: List[Dict[str, Any]],
        meeting_title: Optional[str] = None
    ) -> MeetingCostSummary:
        """会議単位でのコスト集計
        
        Args:
            usage_logs: ai_usage_logsテーブルのレコードリスト
            meeting_title: 会議タイトル（任意）
            
        Returns:
            MeetingCostSummary: 会議別コスト集計
        """
        if not usage_logs:
            return MeetingCostSummary(
                meeting_id="",
                meeting_title=meeting_title,
                total_prompt_tokens=0,
                total_output_tokens=0,
                total_cached_tokens=0,
                total_input_cost=Decimal("0"),
                total_output_cost=Decimal("0"),
                total_cache_cost=Decimal("0"),
                total_cost=Decimal("0"),
                api_calls_count=0,
                created_at=""
            )
        
        meeting_id = usage_logs[0].get("meeting_id", "")
        created_at = usage_logs[0].get("created_at", "")
        
        # 各API呼び出しのコストを計算して集計
        total_input_cost = Decimal("0")
        total_output_cost = Decimal("0")
        total_cache_cost = Decimal("0")
        total_prompt_tokens = 0
        total_output_tokens = 0
        total_cached_tokens = 0
        
        for log in usage_logs:
            cost = self.calculate_single_usage(
                prompt_tokens=log.get("prompt_token_count", 0),
                candidates_tokens=log.get("candidates_token_count", 0),
                thoughts_tokens=log.get("thoughts_token_count", 0),
                cached_tokens=log.get("cached_content_token_count", 0)
            )
            
            total_input_cost += cost.input_cost
            total_output_cost += cost.output_cost
            total_cache_cost += cost.cache_cost
            total_prompt_tokens += cost.prompt_tokens
            total_output_tokens += cost.output_tokens
            total_cached_tokens += cost.cached_tokens
        
        return MeetingCostSummary(
            meeting_id=meeting_id,
            meeting_title=meeting_title,
            total_prompt_tokens=total_prompt_tokens,
            total_output_tokens=total_output_tokens,
            total_cached_tokens=total_cached_tokens,
            total_input_cost=total_input_cost,
            total_output_cost=total_output_cost,
            total_cache_cost=total_cache_cost,
            total_cost=total_input_cost + total_output_cost + total_cache_cost,
            api_calls_count=len(usage_logs),
            created_at=created_at
        )
    
    @classmethod
    def calculate_total_costs(
        self,
        all_usage_logs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """全体のコスト統計を計算
        
        Args:
            all_usage_logs: すべてのusage_logsレコード
            
        Returns:
            全体統計辞書
        """
        if not all_usage_logs:
            return {
                "total_cost": "0.000000",
                "total_prompt_tokens": 0,
                "total_output_tokens": 0,
                "total_cached_tokens": 0,
                "total_api_calls": 0,
                "average_cost_per_call": "0.000000",
                "meetings_count": 0
            }
        
        # 全体集計
        total_cost = Decimal("0")
        total_prompt_tokens = 0
        total_output_tokens = 0
        total_cached_tokens = 0
        meetings = set()
        
        for log in all_usage_logs:
            cost = self.calculate_single_usage(
                prompt_tokens=log.get("prompt_token_count", 0),
                candidates_tokens=log.get("candidates_token_count", 0),
                thoughts_tokens=log.get("thoughts_token_count", 0),
                cached_tokens=log.get("cached_content_token_count", 0)
            )
            
            total_cost += cost.total_cost
            total_prompt_tokens += cost.prompt_tokens
            total_output_tokens += cost.output_tokens
            total_cached_tokens += cost.cached_tokens
            
            if log.get("meeting_id"):
                meetings.add(log["meeting_id"])
        
        avg_cost = total_cost / len(all_usage_logs) if all_usage_logs else Decimal("0")
        
        return {
            "total_cost": str(total_cost),
            "total_input_cost": str(sum(
                self.calculate_single_usage(
                    log.get("prompt_token_count", 0),
                    log.get("candidates_token_count", 0),
                    log.get("thoughts_token_count", 0),
                    log.get("cached_content_token_count", 0)
                ).input_cost for log in all_usage_logs
            )),
            "total_output_cost": str(sum(
                self.calculate_single_usage(
                    log.get("prompt_token_count", 0),
                    log.get("candidates_token_count", 0),
                    log.get("thoughts_token_count", 0),
                    log.get("cached_content_token_count", 0)
                ).output_cost for log in all_usage_logs
            )),
            "total_cache_cost": str(sum(
                self.calculate_single_usage(
                    log.get("prompt_token_count", 0),
                    log.get("candidates_token_count", 0),
                    log.get("thoughts_token_count", 0),
                    log.get("cached_content_token_count", 0)
                ).cache_cost for log in all_usage_logs
            )),
            "total_prompt_tokens": total_prompt_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cached_tokens": total_cached_tokens,
            "total_api_calls": len(all_usage_logs),
            "average_cost_per_call": str(avg_cost),
            "meetings_count": len(meetings)
        }