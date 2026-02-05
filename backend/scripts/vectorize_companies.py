#!/usr/bin/env python3
"""
Company Data Vectorization Script.

Reads company data from Google Sheets and creates vector embeddings
for semantic search using Gemini Embedding API.

Usage:
    cd backend
    uv run python scripts/vectorize_companies.py

Requirements:
    - COMPANY_DB_SPREADSHEET_ID set in .env
    - GEMINI_API_KEY set in .env
    - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set in .env
    - Supabase migration 0020_add_company_embeddings.sql applied
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import dotenv
dotenv.load_dotenv()

import google.generativeai as genai
from supabase import create_client, Client

from app.infrastructure.google.sheets_service import CompanyDatabaseSheetsService
from app.infrastructure.config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Gemini Embedding Model (same as agent memory for consistency)
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768

# Chunk types for semantic search
CHUNK_TYPES = [
    "overview",      # Company overview
    "requirements",  # Hiring requirements
    "salary",        # Salary information
    "growth",        # Growth/career appeal
    "wlb",           # Work-life balance appeal
    "culture",       # Atmosphere/culture appeal
]

# Need type to column mapping (same as company_db_tools.py)
NEED_COLUMN_MAP = {
    "salary": "給与訴求",
    "growth": "成長訴求",
    "wlb": "WLB訴求",
    "atmosphere": "雰囲気訴求",
    "future": "将来性訴求",
}

# Spreadsheet column name mapping (actual column names in the spreadsheet)
COLUMN_MAP = {
    "企業名": "クライアント名",
    "業種": "紹介領域",
    "勤務地": "勤務地",
    "年齢上限": "上限年齢（数字）",
    "学歴要件": "最終学歴",
    "経験社数上限": "経験社数",
    "想定年収上限": "初年度上限年収（基本給+固定残業）",
    "想定年収下限": "初年度オファー年収",  # Using as lower bound estimate
    "リモートワーク": "リモート",
    "リモート詳細": "リモート詳細",
    "平均残業時間": "勤務時間・平均残業時間",
    "従業員数": "従業員数",
    "設立年": "設立年",
    "社風": "カルチャー",
    "事業内容": "会社の特色（ひとこと）",
    "必須経験": "経験職種",
    "求める人物像": "求人条件詳細",
    "紹介推奨": "紹介推奨度",
    "レイヤー": "紹介レイヤー",
    "フレックス": "フレックス",
    "昇給制度": "昇給",
    "キャリアパス": "横のキャリアパス",
    "研修制度": "オンボーディング方法・期間",
}


def _safe_str(value: Any, default: str = "") -> str:
    """Safely convert value to string."""
    if value is None:
        return default
    return str(value).strip()


def _get_col(company: Dict[str, Any], key: str) -> str:
    """Get column value using the column mapping."""
    actual_col = COLUMN_MAP.get(key, key)
    return _safe_str(company.get(actual_col))


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    if value is None or value == "":
        return default
    try:
        if isinstance(value, str):
            value = value.replace("歳", "").replace("万", "").replace(",", "").strip()
        return int(value)
    except (ValueError, TypeError):
        return default


def generate_chunk_text(
    company: Dict[str, Any],
    appeal_data: Dict[str, Any],
    chunk_type: str,
) -> str:
    """
    Generate text content for a specific chunk type.

    Args:
        company: Company data from DB sheet
        appeal_data: Appeal points from import sheet
        chunk_type: Type of chunk to generate

    Returns:
        Text content for embedding
    """
    name = _get_col(company, "企業名")

    if chunk_type == "overview":
        # Company basic overview
        parts = [
            f"企業名: {name}",
            f"業種: {_get_col(company, '業種')}",
            f"勤務地: {_get_col(company, '勤務地')}",
            f"設立年: {_get_col(company, '設立年')}",
            f"従業員数: {_get_col(company, '従業員数')}",
            f"事業内容: {_get_col(company, '事業内容')}",
        ]
        return "\n".join(p for p in parts if not p.endswith(": "))

    elif chunk_type == "requirements":
        # Hiring requirements
        parts = [
            f"企業名: {name}",
            f"年齢上限: {_get_col(company, '年齢上限')}歳",
            f"学歴要件: {_get_col(company, '学歴要件')}",
            f"経験社数上限: {_get_col(company, '経験社数上限')}",
            f"必須経験: {_get_col(company, '必須経験')}",
            f"求める人物像: {_get_col(company, '求める人物像')}",
        ]
        return "\n".join(p for p in parts if not p.endswith(": ") and not p.endswith(": 歳"))

    elif chunk_type == "salary":
        # Salary information + salary appeal
        appeal = appeal_data.get(name, {})
        parts = [
            f"企業名: {name}",
            f"初年度オファー年収: {_get_col(company, '想定年収下限')}万円",
            f"初年度上限年収: {_get_col(company, '想定年収上限')}万円",
            f"昇給制度: {_get_col(company, '昇給制度')}",
            f"インセンティブ: {_safe_str(company.get('インセンティブ'))}",
            f"給与訴求ポイント: {_safe_str(appeal.get(NEED_COLUMN_MAP['salary']))}",
        ]
        return "\n".join(p for p in parts if not p.endswith(": ") and not p.endswith(": 万円"))

    elif chunk_type == "growth":
        # Growth/career appeal
        appeal = appeal_data.get(name, {})
        parts = [
            f"企業名: {name}",
            f"オンボーディング: {_get_col(company, '研修制度')}",
            f"キャリアパス: {_get_col(company, 'キャリアパス')}",
            f"昇格: {_safe_str(company.get('昇格'))}",
            f"成長訴求ポイント: {_safe_str(appeal.get(NEED_COLUMN_MAP['growth']))}",
        ]
        return "\n".join(p for p in parts if not p.endswith(": "))

    elif chunk_type == "wlb":
        # Work-life balance appeal
        appeal = appeal_data.get(name, {})
        parts = [
            f"企業名: {name}",
            f"勤務時間・残業: {_get_col(company, '平均残業時間')}",
            f"リモートワーク: {_get_col(company, 'リモートワーク')}",
            f"リモート詳細: {_get_col(company, 'リモート詳細')}",
            f"フレックス: {_get_col(company, 'フレックス')}",
            f"副業可否: {_safe_str(company.get('副業可否'))}",
            f"WLB訴求ポイント: {_safe_str(appeal.get(NEED_COLUMN_MAP['wlb']))}",
        ]
        return "\n".join(p for p in parts if not p.endswith(": "))

    elif chunk_type == "culture":
        # Atmosphere/culture appeal
        appeal = appeal_data.get(name, {})
        parts = [
            f"企業名: {name}",
            f"カルチャー: {_get_col(company, '社風')}",
            f"メンバーの特徴: {_safe_str(company.get('メンバーの特徴'))}",
            f"チーム編成: {_safe_str(company.get('チーム編成'))}",
            f"女性の働きやすさ: {_safe_str(company.get('女性の働きやすさ'))}",
            f"雰囲気訴求ポイント: {_safe_str(appeal.get(NEED_COLUMN_MAP['atmosphere']))}",
            f"将来性訴求ポイント: {_safe_str(appeal.get(NEED_COLUMN_MAP['future']))}",
        ]
        return "\n".join(p for p in parts if not p.endswith(": "))

    return ""


def extract_metadata(company: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metadata for filtering.

    Args:
        company: Company data from DB sheet

    Returns:
        Metadata dictionary for JSONB storage
    """
    # Parse locations into array
    location_str = _get_col(company, "勤務地")
    locations = [loc.strip() for loc in location_str.split("/") if loc.strip()]
    if not locations and location_str:
        locations = [location_str]

    # Parse remote option
    remote_str = _get_col(company, "リモートワーク")

    # Determine recommendation status
    recommendation = _get_col(company, "紹介推奨")

    # Layer (レイヤー)
    layer = _get_col(company, "レイヤー")

    return {
        "age_limit": _safe_int(company.get(COLUMN_MAP.get("年齢上限", "年齢上限"))) or None,
        "min_salary": _safe_int(company.get(COLUMN_MAP.get("想定年収下限", "想定年収下限"))) or None,
        "max_salary": _safe_int(company.get(COLUMN_MAP.get("想定年収上限", "想定年収上限"))) or None,
        "locations": locations if locations else None,
        "remote": remote_str if remote_str else None,
        "industry": _get_col(company, "業種") or None,
        "recommendation": recommendation if recommendation else None,
        "layer": layer if layer else None,
    }


def compute_content_hash(text: str) -> str:
    """Compute hash for change detection."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def get_embedding(text: str, model: str = EMBEDDING_MODEL) -> List[float]:
    """
    Get embedding vector from Gemini API.

    Uses Matryoshka truncation to get 768 dimensions (same as agent memory).

    Args:
        text: Text to embed
        model: Embedding model name

    Returns:
        List of floats (768 dimensions)
    """
    result = genai.embed_content(
        model=model,
        content=text,
        task_type="retrieval_document",
        output_dimensionality=EMBEDDING_DIMENSIONS,  # Matryoshka truncation to 768
    )
    return result["embedding"]


def upsert_chunk(
    supabase: Client,
    company_name: str,
    chunk_type: str,
    chunk_text: str,
    embedding: List[float],
    metadata: Dict[str, Any],
    content_hash: str,
) -> bool:
    """
    Upsert a chunk into Supabase.

    Args:
        supabase: Supabase client
        company_name: Company name
        chunk_type: Chunk type
        chunk_text: Text content
        embedding: Vector embedding
        metadata: Metadata for filtering
        content_hash: Hash for change detection

    Returns:
        True if successful
    """
    try:
        # Check if chunk exists and has same hash
        existing = supabase.table("company_chunks").select(
            "id, content_hash"
        ).eq("company_name", company_name).eq("chunk_type", chunk_type).execute()

        if existing.data and existing.data[0].get("content_hash") == content_hash:
            logger.debug(f"  Skipping {company_name}/{chunk_type} (unchanged)")
            return True

        # Upsert the chunk
        data = {
            "company_name": company_name,
            "chunk_type": chunk_type,
            "chunk_text": chunk_text,
            "embedding": embedding,
            "metadata": metadata,
            "content_hash": content_hash,
            "source_sheet": "DB",
        }

        supabase.table("company_chunks").upsert(
            data,
            on_conflict="company_name,chunk_type",
        ).execute()

        return True

    except Exception as e:
        logger.error(f"  Error upserting {company_name}/{chunk_type}: {e}")
        return False


def main():
    """Main vectorization function."""
    logger.info("=" * 60)
    logger.info("Company Data Vectorization Script")
    logger.info("=" * 60)

    # Initialize settings
    settings = get_settings()

    # Check required settings
    if not settings.company_db_spreadsheet_id:
        logger.error("COMPANY_DB_SPREADSHEET_ID not set!")
        sys.exit(1)

    if not settings.gemini_api_key:
        logger.error("GEMINI_API_KEY not set!")
        sys.exit(1)

    if not settings.supabase_url or not settings.supabase_key:
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set!")
        sys.exit(1)

    # Initialize Gemini
    genai.configure(api_key=settings.gemini_api_key)
    logger.info(f"Gemini configured with model: {EMBEDDING_MODEL}")

    # Initialize Supabase
    supabase = create_client(settings.supabase_url, settings.supabase_key)
    logger.info("Supabase client initialized")

    # Initialize Sheets service
    sheets_service = CompanyDatabaseSheetsService(settings)

    # Load company data
    logger.info("Loading companies from Google Sheets...")
    companies = sheets_service.get_all_companies(force_refresh=True)
    logger.info(f"Loaded {len(companies)} companies")

    # Load appeal points
    logger.info("Loading appeal points...")
    appeal_data = sheets_service.get_appeal_points(force_refresh=True)
    logger.info(f"Loaded appeal points for {len(appeal_data)} companies")

    # Process each company
    total_chunks = 0
    success_chunks = 0
    skipped_chunks = 0
    error_chunks = 0

    start_time = time.time()

    for i, company in enumerate(companies, 1):
        company_name = _get_col(company, "企業名")
        if not company_name:
            logger.warning(f"Skipping company #{i}: no name")
            continue

        logger.info(f"[{i}/{len(companies)}] Processing: {company_name}")

        # Extract metadata (shared across all chunks)
        metadata = extract_metadata(company)

        # Generate and vectorize each chunk
        for chunk_type in CHUNK_TYPES:
            total_chunks += 1

            # Generate chunk text
            chunk_text = generate_chunk_text(company, appeal_data, chunk_type)
            if not chunk_text or len(chunk_text) < 20:
                logger.debug(f"  Skipping {chunk_type}: insufficient content")
                skipped_chunks += 1
                continue

            # Compute content hash
            content_hash = compute_content_hash(chunk_text)

            try:
                # Get embedding
                embedding = get_embedding(chunk_text)

                # Upsert to Supabase
                if upsert_chunk(
                    supabase,
                    company_name,
                    chunk_type,
                    chunk_text,
                    embedding,
                    metadata,
                    content_hash,
                ):
                    success_chunks += 1
                    logger.debug(f"  {chunk_type}: OK ({len(chunk_text)} chars)")
                else:
                    error_chunks += 1

                # Rate limiting (Gemini free tier: 1500 RPM)
                time.sleep(0.05)

            except Exception as e:
                logger.error(f"  Error processing {chunk_type}: {e}")
                error_chunks += 1
                # Back off on error
                time.sleep(1)

        # Progress checkpoint
        if i % 50 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed * 60
            logger.info(f"Progress: {i}/{len(companies)} ({rate:.1f} companies/min)")

    # Summary
    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("Vectorization Complete!")
    logger.info(f"Time elapsed: {elapsed:.1f} seconds")
    logger.info(f"Companies processed: {len(companies)}")
    logger.info(f"Total chunks: {total_chunks}")
    logger.info(f"  Success: {success_chunks}")
    logger.info(f"  Skipped: {skipped_chunks}")
    logger.info(f"  Errors: {error_chunks}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
