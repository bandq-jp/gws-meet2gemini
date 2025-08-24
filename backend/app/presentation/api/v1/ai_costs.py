"""
AIコスト関連API

トークン使用量とコスト情報を提供するAPIエンドポイント。
Gemini 2.5 Proの料金体系に基づいたコスト計算を行う。
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any

from app.application.use_cases.get_ai_costs import GetAiCostsUseCase

router = APIRouter()


@router.get("/summary", response_model=Dict[str, Any])
def get_cost_summary(
    limit: int = Query(1000, description="取得するusage_logsレコード数上限", ge=1, le=10000)
):
    """全体のAIコスト概要を取得
    
    Args:
        limit: 取得するレコード数上限
        
    Returns:
        全体統計、コスト内訳、最近の会議一覧
    """
    try:
        use_case = GetAiCostsUseCase()
        return use_case.get_overall_summary(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"コスト概要取得エラー: {str(e)}")


@router.get("/meeting/{meeting_id}", response_model=Dict[str, Any])
def get_meeting_cost_detail(meeting_id: str):
    """特定会議の詳細AIコスト情報を取得
    
    Args:
        meeting_id: 会議ID
        
    Returns:
        会議の詳細コスト情報とAPI呼び出し一覧
    """
    try:
        use_case = GetAiCostsUseCase()
        return use_case.get_meeting_detail(meeting_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"会議コスト詳細取得エラー: {str(e)}")


@router.get("/pricing-info", response_model=Dict[str, Any])
def get_pricing_info():
    """Gemini 2.5 Proの料金体系情報を取得
    
    Returns:
        料金体系の詳細情報
    """
    return {
        "model": "gemini-2.5-pro",
        "currency": "USD",
        "pricing_per_million_tokens": {
            "input": {
                "standard": "1.25",  # ≤200k tokens
                "high_volume": "2.50"  # >200k tokens
            },
            "output": {
                "standard": "10.00",  # includes thoughts tokens, prompt ≤200k
                "high_volume": "15.00"  # includes thoughts tokens, prompt >200k
            },
            "context_cache": {
                "standard": "0.31",  # ≤200k tokens
                "high_volume": "0.625"  # >200k tokens
            }
        },
        "thresholds": {
            "high_volume_threshold": 200000  # 20万トークン
        },
        "notes": [
            "Output料金には思考トークン(thoughts tokens)が含まれます",
            "料金体系はプロンプトトークン数で決まります",
            "コンテキストキャッシュストレージ料金: $4.50/百万トークン/時間"
        ],
        "calculation_example": {
            "description": "プロンプト15万トークン、出力5万トークンの場合",
            "input_cost": "0.1875",  # (150000/1000000) * 1.25
            "output_cost": "0.5000",  # (50000/1000000) * 10.00
            "total_cost": "0.6875"
        }
    }