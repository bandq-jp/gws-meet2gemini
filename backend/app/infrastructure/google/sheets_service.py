"""
Google Sheets Service for Company Database.

Provides read-only access to the company information spreadsheet
with in-memory caching for performance.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


class SheetsDataCache:
    """TTL-based in-memory cache for spreadsheet data."""

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache.

        Args:
            ttl_seconds: Cache TTL in seconds (default 5 minutes).
        """
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                logger.debug(f"[SheetsCache] Cache hit: {key}")
                return data
            del self._cache[key]
            logger.debug(f"[SheetsCache] Cache expired: {key}")
        return None

    def set(self, key: str, value: Any) -> None:
        """Set cache value with current timestamp."""
        self._cache[key] = (value, datetime.now())
        logger.debug(f"[SheetsCache] Cache set: {key}")

    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate specific key or all cache."""
        if key:
            self._cache.pop(key, None)
            logger.debug(f"[SheetsCache] Cache invalidated: {key}")
        else:
            self._cache.clear()
            logger.debug("[SheetsCache] All cache invalidated")


class CompanyDatabaseSheetsService:
    """
    Read-only Google Sheets service for company database.

    Provides access to:
    - DB sheet: Company master data (52 columns x ~99 companies)
    - Import sheet: Need-based appeal points
    - PIC sheets: Per-advisor company rankings
    """

    # Sheet name constants
    SHEET_DB = "DB"
    SHEET_IMPORT = "新_インポート用"
    PIC_SHEETS_PREFIX = "X "  # Format: "X 担当者名"

    def __init__(self, settings: "Settings"):
        """
        Initialize the service.

        Args:
            settings: Application settings with SERVICE_ACCOUNT_JSON and spreadsheet config.
        """
        self._settings = settings
        self._cache = SheetsDataCache(ttl_seconds=settings.company_db_cache_ttl)
        self._sheets = None
        self._spreadsheet_id = settings.company_db_spreadsheet_id

        if not self._spreadsheet_id:
            logger.warning("[SheetsService] COMPANY_DB_SPREADSHEET_ID is not set")

    def _build_credentials(self) -> Credentials:
        """
        Build service account credentials.

        Uses the same pattern as drive_docs_collector.py.
        Supports both file path and JSON string from environment variable.

        Returns:
            Configured Credentials object.

        Raises:
            RuntimeError: If SERVICE_ACCOUNT_JSON is not set or invalid.
        """
        val = (self._settings.service_account_json or "").strip()
        if not val:
            raise RuntimeError(
                "SERVICE_ACCOUNT_JSON is not set. "
                "Must provide service account JSON (file path or JSON content)."
            )

        # Path 1: Load from file
        if os.path.exists(val):
            logger.debug(f"[SheetsService] Using service account key file: {val}")
            return Credentials.from_service_account_file(val, scopes=SCOPES)

        # Path 2: Parse from environment variable as JSON string
        try:
            info = json.loads(val)
            if not isinstance(info, dict):
                raise ValueError("SERVICE_ACCOUNT_JSON did not parse into an object")
            logger.debug("[SheetsService] Using service account JSON from environment")
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            logger.error(
                f"[SheetsService] Failed to load service account credentials: {e}"
            )
            raise

    def _build_service(self):
        """Build or return cached Sheets API service."""
        if self._sheets:
            return self._sheets

        creds = self._build_credentials()
        self._sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        logger.info("[SheetsService] Sheets API service initialized")
        return self._sheets

    def _parse_sheet_to_dicts(
        self, rows: List[List[str]], skip_empty: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Parse sheet rows into list of dictionaries.

        Args:
            rows: Raw rows from Sheets API (first row is headers).
            skip_empty: Skip rows where the first column is empty.

        Returns:
            List of dictionaries with header keys.
        """
        if len(rows) < 2:
            return []

        headers = rows[0]
        results = []

        for row in rows[1:]:
            # Skip empty rows
            if skip_empty and (not row or not row[0].strip()):
                continue

            record = {}
            for i, header in enumerate(headers):
                if header:  # Skip empty headers
                    record[header] = row[i] if i < len(row) else ""
            results.append(record)

        return results

    def get_all_companies(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get all companies from DB sheet.

        Args:
            force_refresh: Bypass cache and fetch fresh data.

        Returns:
            List of company dictionaries with all 52+ columns.
        """
        if not self._spreadsheet_id:
            logger.error("[SheetsService] Spreadsheet ID not configured")
            return []

        cache_key = "db_all_companies"
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            sheets = self._build_service()
            result = (
                sheets.spreadsheets()
                .values()
                .get(
                    spreadsheetId=self._spreadsheet_id,
                    range=f"'{self.SHEET_DB}'!A:BZ",  # Cover all 52+ columns
                )
                .execute()
            )

            rows = result.get("values", [])
            companies = self._parse_sheet_to_dicts(rows)

            logger.info(f"[SheetsService] Loaded {len(companies)} companies from DB sheet")
            self._cache.set(cache_key, companies)
            return companies

        except Exception as e:
            logger.error(f"[SheetsService] Failed to fetch companies: {e}")
            return []

    def get_appeal_points(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get need-based appeal points from import sheet.

        Args:
            force_refresh: Bypass cache and fetch fresh data.

        Returns:
            Dictionary mapping company name to appeal points by need type.
        """
        if not self._spreadsheet_id:
            return {}

        cache_key = "appeal_points"
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            sheets = self._build_service()
            result = (
                sheets.spreadsheets()
                .values()
                .get(
                    spreadsheetId=self._spreadsheet_id,
                    range=f"'{self.SHEET_IMPORT}'!A:Z",
                )
                .execute()
            )

            rows = result.get("values", [])
            if len(rows) < 2:
                return {}

            headers = rows[0]
            appeal_data: Dict[str, Dict[str, Any]] = {}

            for row in rows[1:]:
                if not row or not row[0].strip():
                    continue

                company_name = row[0].strip()
                appeal_data[company_name] = {}

                for i, header in enumerate(headers[1:], start=1):
                    if header:
                        appeal_data[company_name][header] = row[i] if i < len(row) else ""

            logger.info(
                f"[SheetsService] Loaded appeal points for {len(appeal_data)} companies"
            )
            self._cache.set(cache_key, appeal_data)
            return appeal_data

        except Exception as e:
            logger.error(f"[SheetsService] Failed to fetch appeal points: {e}")
            return {}

    def get_pic_ranking(
        self, pic_name: str, force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get company rankings for a specific PIC (advisor).

        Args:
            pic_name: Advisor name (without "X " prefix).
            force_refresh: Bypass cache and fetch fresh data.

        Returns:
            List of company rankings with match scores.
        """
        if not self._spreadsheet_id:
            return []

        sheet_name = f"{self.PIC_SHEETS_PREFIX}{pic_name}"
        cache_key = f"pic_ranking_{pic_name}"

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            sheets = self._build_service()
            result = (
                sheets.spreadsheets()
                .values()
                .get(
                    spreadsheetId=self._spreadsheet_id,
                    range=f"'{sheet_name}'!A:Z",
                )
                .execute()
            )

            rows = result.get("values", [])
            rankings = self._parse_sheet_to_dicts(rows)

            logger.info(
                f"[SheetsService] Loaded {len(rankings)} rankings for PIC: {pic_name}"
            )
            self._cache.set(cache_key, rankings)
            return rankings

        except Exception as e:
            logger.warning(f"[SheetsService] PIC sheet not found: {sheet_name}, error: {e}")
            return []

    def list_pic_sheets(self) -> List[str]:
        """
        List all available PIC (advisor) names with sheets.

        Returns:
            List of advisor names (without "X " prefix).
        """
        if not self._spreadsheet_id:
            return []

        cache_key = "pic_sheets_list"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            sheets = self._build_service()
            metadata = (
                sheets.spreadsheets()
                .get(
                    spreadsheetId=self._spreadsheet_id,
                    fields="sheets.properties.title",
                )
                .execute()
            )

            pic_names = []
            for sheet in metadata.get("sheets", []):
                title = sheet["properties"]["title"]
                if title.startswith(self.PIC_SHEETS_PREFIX):
                    pic_name = title[len(self.PIC_SHEETS_PREFIX) :]
                    pic_names.append(pic_name)

            logger.info(f"[SheetsService] Found {len(pic_names)} PIC sheets")
            self._cache.set(cache_key, pic_names)
            return pic_names

        except Exception as e:
            logger.error(f"[SheetsService] Failed to list PIC sheets: {e}")
            return []

    def invalidate_cache(self, key: Optional[str] = None) -> None:
        """
        Invalidate cache.

        Args:
            key: Specific cache key to invalidate, or None for all.
        """
        self._cache.invalidate(key)
