"""
LP流入スプレッドシート読み取りサービス.

responses02（全LP申込）、面談予約、有効リードTCV要件、UTMマッピングを
Google Sheets APIで直接読み取る。Zohoを経由しないSSoTアクセス。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .sheets_service import SheetsDataCache

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class LPSheetsService:
    """LP流入スプレッドシートの読み取り専用サービス."""

    # responses02 の列インデックス (0-based)
    COL_TIMESTAMP = 0
    COL_SALESEXP = 1
    COL_INCOME = 2
    COL_LOCATION = 3
    COL_EXP_COMPANIES = 4
    COL_EDUCATION = 5
    COL_BIRTHDATE = 6
    COL_FULLNAME = 7
    COL_EMAIL = 8
    COL_PHONE = 9
    COL_PARENT_URL = 10
    COL_PARENT_PATH = 11
    COL_PAGE_URL = 12
    COL_REFERRER_URL = 13
    COL_PREFERENCE = 14
    COL_INTERVIEW_DATE = 17  # R: 面談予約
    COL_ASSIGNEE = 19        # T: slackID
    COL_CLASSIFICATION = 21  # V: 流入経路
    COL_ZOHO_ID = 23         # X: zohoID
    COL_CALL_STATUS = 26     # AA: 架電

    def __init__(self, settings: "Settings"):
        self._settings = settings
        self._cache = SheetsDataCache(ttl_seconds=settings.lp_cache_ttl)
        self._sheets = None
        self._spreadsheet_id = settings.lp_spreadsheet_id

        if not self._spreadsheet_id:
            logger.warning("[LPSheets] LP_SPREADSHEET_ID is not set")

    def _build_service(self):
        """Build or return cached Sheets API service."""
        if self._sheets:
            return self._sheets

        import json
        import os

        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        val = (self._settings.service_account_json or "").strip()
        if not val:
            raise RuntimeError("SERVICE_ACCOUNT_JSON is not set")

        if os.path.exists(val):
            creds = Credentials.from_service_account_file(val, scopes=scopes)
        else:
            info = json.loads(val)
            creds = Credentials.from_service_account_info(info, scopes=scopes)

        self._sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return self._sheets

    def _read_sheet(self, sheet_name: str) -> List[List[Any]]:
        """指定シートの全データを取得（キャッシュ付き）."""
        cached = self._cache.get(sheet_name)
        if cached is not None:
            return cached

        service = self._build_service()
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=self._spreadsheet_id, range=f"'{sheet_name}'")
            .execute()
        )
        rows = result.get("values", [])
        logger.info("[LPSheets] Read '%s': %d rows", sheet_name, len(rows))
        self._cache.set(sheet_name, rows)
        return rows

    def _safe_get(self, row: List[Any], idx: int) -> str:
        """行から安全に値を取得."""
        if idx < len(row):
            val = row[idx]
            return str(val).strip() if val is not None else ""
        return ""

    def get_responses02(self) -> List[Dict[str, Any]]:
        """responses02シートの全行を辞書リストで返す（ヘッダー行除外）."""
        rows = self._read_sheet(self._settings.lp_sheet_responses02)
        if len(rows) < 2:
            return []

        result = []
        for row in rows[1:]:
            if not row or not row[0]:
                continue
            result.append({
                "timestamp": self._safe_get(row, self.COL_TIMESTAMP),
                "salesexp": self._safe_get(row, self.COL_SALESEXP),
                "income": self._safe_get(row, self.COL_INCOME),
                "location": self._safe_get(row, self.COL_LOCATION),
                "exp_companies": self._safe_get(row, self.COL_EXP_COMPANIES),
                "education": self._safe_get(row, self.COL_EDUCATION),
                "birthdate": self._safe_get(row, self.COL_BIRTHDATE),
                "fullname": self._safe_get(row, self.COL_FULLNAME),
                "email": self._safe_get(row, self.COL_EMAIL),
                "phone": self._safe_get(row, self.COL_PHONE),
                "parent_url": self._safe_get(row, self.COL_PARENT_URL),
                "parent_path": self._safe_get(row, self.COL_PARENT_PATH),
                "page_url": self._safe_get(row, self.COL_PAGE_URL),
                "referrer_url": self._safe_get(row, self.COL_REFERRER_URL),
                "interview_date": self._safe_get(row, self.COL_INTERVIEW_DATE),
                "assignee": self._safe_get(row, self.COL_ASSIGNEE),
                "classification": self._safe_get(row, self.COL_CLASSIFICATION),
                "zoho_id": self._safe_get(row, self.COL_ZOHO_ID),
                "call_status": self._safe_get(row, self.COL_CALL_STATUS),
            })
        return result

    def get_interview_bookings(self) -> List[Dict[str, Any]]:
        """面談予約シートの全行を辞書リストで返す."""
        rows = self._read_sheet(self._settings.lp_sheet_interview)
        if len(rows) < 2:
            return []

        result = []
        for row in rows[1:]:
            if not row or not row[0]:
                continue
            result.append({
                "name": self._safe_get(row, 0),
                "email": self._safe_get(row, 1),
                "datetime": self._safe_get(row, 2),
                "created_at": self._safe_get(row, 3),
                "meet_url": self._safe_get(row, 4) if len(row) > 4 else "",
                "source": self._safe_get(row, 5) if len(row) > 5 else "",
            })
        return result

    def get_valid_lead_criteria(self) -> Dict[str, Any]:
        """有効リードTCV要件シートから判定基準を取得."""
        rows = self._read_sheet("有効リード/TCV要件")

        criteria = {
            "valid_lead": {"min_age": 23, "max_age": 32, "locations": [], "experience": None},
            "tcv": {"min_age": 23, "max_age": 32, "locations": [], "experience": "営業ないし人材業界経験"},
        }

        for row in rows:
            if not row:
                continue
            label = str(row[0]).strip() if row[0] else ""

            if label == "年齢" and len(row) >= 5:
                try:
                    min_age = int(row[1])
                    max_age = int(row[3])
                    criteria["valid_lead"]["min_age"] = min_age
                    criteria["valid_lead"]["max_age"] = max_age
                    criteria["tcv"]["min_age"] = min_age
                    criteria["tcv"]["max_age"] = max_age
                except (ValueError, TypeError):
                    pass

            if label == "希望勤務地":
                locs = [str(v).strip() for v in row[1:] if v]
                if locs:
                    if not criteria["valid_lead"]["locations"]:
                        criteria["valid_lead"]["locations"] = locs
                    criteria["tcv"]["locations"] = locs

            if label == "経験" and len(row) >= 2 and row[1]:
                criteria["tcv"]["experience"] = str(row[1]).strip()

        return criteria

    def get_utm_mapping(self) -> Dict[str, Dict[str, str]]:
        """URLパラメータマッピングシートからUTM ID→名前マッピングを取得."""
        rows = self._read_sheet("URLパラメータマッピング")

        mapping = {"campaign": {}, "adset": {}, "content": {}}

        for row in rows[2:]:  # skip 2 header rows
            if not row:
                continue
            # Columns A-B: campaign, D-E: adset, G-H: content
            if len(row) > 1 and row[0] and row[1]:
                mapping["campaign"][str(row[0]).strip()] = str(row[1]).strip()
            if len(row) > 4 and row[3] and row[4]:
                mapping["adset"][str(row[3]).strip()] = str(row[4]).strip()
            if len(row) > 7 and row[6] and row[7]:
                mapping["content"][str(row[6]).strip()] = str(row[7]).strip()

        return mapping

    def invalidate_cache(self) -> None:
        """全キャッシュを無効化."""
        self._cache.invalidate()
