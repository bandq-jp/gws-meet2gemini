"""
Semantic Search Tools for Company Database.

ADK-native tools for semantic search using pgvector embeddings.
Uses the same Gemini embedding model as agent memory for consistency.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from google import genai

from app.infrastructure.supabase.client import get_supabase
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

# Use same embedding model as agent memory
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768


@lru_cache(maxsize=256)
def _get_cached_embedding(query: str) -> tuple:
    """Embedding結果をキャッシュ（LRU、最大256件）。tupleで返すのはlru_cacheがhashableな戻り値を必要とするため。"""
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)

    result = client.models.embed_content(
        model=f"models/{EMBEDDING_MODEL}",
        contents=query,
        config={
            "output_dimensionality": EMBEDDING_DIMENSIONS,
            "task_type": "RETRIEVAL_QUERY",
        },
    )

    return tuple(result.embeddings[0].values)


def _get_query_embedding(query: str) -> List[float]:
    """
    Generate embedding for a search query.

    Uses Matryoshka truncation to match agent memory dimensions (768).
    """
    return list(_get_cached_embedding(query))


def semantic_search_companies(
    query: str,
    chunk_types: Optional[List[str]] = None,
    max_age: Optional[int] = None,
    min_salary: Optional[int] = None,
    locations: Optional[List[str]] = None,
    limit: int = 10,
    similarity_threshold: float = 0.3,
) -> Dict[str, Any]:
    """
    セマンティック検索で企業を探す。自然言語クエリで関連企業を検索。

    Args:
        query: 検索クエリ（自然言語）。例: "リモートワーク可能でワークライフバランス重視の企業"
        chunk_types: 検索対象チャンク種類。省略時は全種類。
            - overview: 企業概要
            - requirements: 採用要件
            - salary: 給与情報
            - growth: 成長・キャリア
            - wlb: ワークライフバランス
            - culture: 社風・カルチャー
        max_age: 候補者年齢（この年齢を受け入れる企業のみ）
        min_salary: 希望年収（この年収以上を提示可能な企業のみ）
        locations: 希望勤務地リスト（いずれかに該当する企業）
        limit: 取得件数（max 20）
        similarity_threshold: 類似度閾値（0.0-1.0、デフォルト0.3）。値を下げると結果が増え、上げると精度が上がる。

    Returns:
        Dict[str, Any]: セマンティック検索結果。
            success: True/False
            query: 検索クエリ
            total_found: マッチ件数
            results: 検索結果リスト（類似度スコア付き）
    """
    logger.info(f"[ADK Semantic] semantic_search_companies: query={query[:50]}...")

    if not query or len(query) < 3:
        return {"success": False, "error": "検索クエリは3文字以上必要です"}

    try:
        # Generate query embedding
        query_embedding = _get_query_embedding(query)

        # Build RPC parameters
        params: Dict[str, Any] = {
            "query_embedding": query_embedding,
            "match_count": min(limit, 20),
            "similarity_threshold": max(0.0, min(1.0, similarity_threshold)),
        }

        if chunk_types:
            params["match_chunk_types"] = chunk_types
        if max_age:
            params["filter_max_age"] = max_age
        if min_salary:
            params["filter_min_salary"] = min_salary
        if locations:
            params["filter_locations"] = locations

        # Execute semantic search via RPC
        sb = get_supabase()
        result = sb.rpc("search_company_chunks", params).execute()

        if not result.data:
            return {
                "success": True,
                "query": query,
                "total_found": 0,
                "results": [],
                "hint": "条件に合う企業が見つかりませんでした。条件を緩めてみてください。",
            }

        # Group by company and aggregate
        company_results: Dict[str, Dict[str, Any]] = {}
        for row in result.data:
            company_name = row["company_name"]
            if company_name not in company_results:
                company_results[company_name] = {
                    "company_name": company_name,
                    "max_similarity": row["similarity"],
                    "matched_chunks": [],
                    "metadata": row["metadata"],
                }

            company_results[company_name]["matched_chunks"].append({
                "chunk_type": row["chunk_type"],
                "similarity": round(row["similarity"], 3),
                "excerpt": row["chunk_text"][:200] + "..." if len(row["chunk_text"]) > 200 else row["chunk_text"],
            })

            # Keep highest similarity
            if row["similarity"] > company_results[company_name]["max_similarity"]:
                company_results[company_name]["max_similarity"] = row["similarity"]

        # Sort by max similarity
        sorted_results = sorted(
            company_results.values(),
            key=lambda x: x["max_similarity"],
            reverse=True,
        )

        # Format output
        formatted_results = []
        for r in sorted_results:
            formatted_results.append({
                "company_name": r["company_name"],
                "similarity_score": round(r["max_similarity"], 3),
                "matched_chunks": r["matched_chunks"],
                "age_limit": r["metadata"].get("age_limit"),
                "max_salary": r["metadata"].get("max_salary"),
                "locations": r["metadata"].get("locations"),
                "remote": r["metadata"].get("remote"),
            })

        return {
            "success": True,
            "query": query,
            "filters_applied": {
                "chunk_types": chunk_types,
                "max_age": max_age,
                "min_salary": min_salary,
                "locations": locations,
            },
            "total_found": len(formatted_results),
            "results": formatted_results,
        }

    except Exception as e:
        logger.error(f"[ADK Semantic] Error: {e}")
        return {"success": False, "error": str(e)}


def find_companies_for_candidate(
    transfer_reasons: str,
    age: Optional[int] = None,
    desired_salary: Optional[int] = None,
    desired_locations: Optional[List[str]] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    候補者の転職理由から最適な企業を検索（セマンティックマッチング）。

    match_candidate_to_companiesとの違い：こちらは転職理由からベクトル類似度でマッチング。
    厳密な条件チェックはmatch_candidate_to_companiesを使用。

    Args:
        transfer_reasons: 転職理由・希望（自然言語）。
            例: "給与を上げたい、リモートワークしたい、成長できる環境"
        age: 候補者年齢
        desired_salary: 希望年収（万円）
        desired_locations: 希望勤務地リスト
        limit: 取得件数

    Returns:
        Dict[str, Any]: セマンティック検索結果。
            success: True/False
            candidate_profile: 使用した候補者条件
            total_found: マッチ件数
            recommended_companies: 推薦企業リスト（訴求ポイント付き）
    """
    logger.info(f"[ADK Semantic] find_companies_for_candidate: reasons={transfer_reasons[:50]}...")

    if not transfer_reasons:
        return {"success": False, "error": "転職理由を指定してください"}

    try:
        # Determine which chunk types to search based on transfer reasons
        chunk_types = []
        reasons_lower = transfer_reasons.lower()

        if any(kw in reasons_lower for kw in ["給与", "年収", "お金", "収入"]):
            chunk_types.append("salary")
        if any(kw in reasons_lower for kw in ["成長", "キャリア", "スキル", "経験"]):
            chunk_types.append("growth")
        if any(kw in reasons_lower for kw in ["ワークライフ", "残業", "休み", "リモート", "在宅"]):
            chunk_types.append("wlb")
        if any(kw in reasons_lower for kw in ["雰囲気", "社風", "人間関係", "カルチャー"]):
            chunk_types.append("culture")

        # If no specific types detected, search all relevant types
        if not chunk_types:
            chunk_types = ["salary", "growth", "wlb", "culture"]

        # Build search query from transfer reasons
        search_query = f"転職理由: {transfer_reasons}"

        # Execute semantic search
        search_result = semantic_search_companies(
            query=search_query,
            chunk_types=chunk_types,
            max_age=age,
            min_salary=desired_salary,
            locations=desired_locations,
            limit=limit,
        )

        if not search_result.get("success"):
            return search_result

        # Enhance results with appeal points
        recommended = []
        for company in search_result.get("results", []):
            # Extract relevant appeal from matched chunks
            appeal_points = []
            for chunk in company.get("matched_chunks", []):
                if chunk["similarity"] >= 0.4:  # High relevance threshold
                    appeal_points.append(f"[{chunk['chunk_type']}] {chunk['excerpt'][:100]}")

            recommended.append({
                "company_name": company["company_name"],
                "match_score": company["similarity_score"],
                "age_limit": company.get("age_limit"),
                "max_salary": company.get("max_salary"),
                "locations": company.get("locations"),
                "remote": company.get("remote"),
                "appeal_points": appeal_points[:3],  # Top 3 appeal points
            })

        return {
            "success": True,
            "candidate_profile": {
                "transfer_reasons": transfer_reasons,
                "age": age,
                "desired_salary": desired_salary,
                "desired_locations": desired_locations,
            },
            "search_strategy": {
                "chunk_types_searched": chunk_types,
            },
            "total_found": len(recommended),
            "recommended_companies": recommended,
            "usage_hint": "match_scoreが高い企業から提案してください。appeal_pointsを候補者への説明に活用できます。",
        }

    except Exception as e:
        logger.error(f"[ADK Semantic] Error: {e}")
        return {"success": False, "error": str(e)}


# List of ADK-compatible semantic search tools
ADK_SEMANTIC_COMPANY_TOOLS = [
    semantic_search_companies,
    find_companies_for_candidate,
]
