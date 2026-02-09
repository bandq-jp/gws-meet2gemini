"""
Google Drive Service - Per-user Drive API access (read-only).

Provides read-only access to Google Drive files (including Docs, Sheets, Slides)
via service account domain-wide delegation with drive.readonly scope.

File exports:
  - Google Docs → text/plain
  - Google Sheets → text/csv (per sheet)
  - Google Slides → text/plain
  - Other files → direct download (text-based only)

Authentication: SERVICE_ACCOUNT_JSON (file path or JSON string)
Scope: drive.readonly
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]

# Google Workspace MIME types and their export formats
GOOGLE_MIME_EXPORTS = {
    "application/vnd.google-apps.document": {
        "export_mime": "text/plain",
        "label": "Google Docs",
    },
    "application/vnd.google-apps.spreadsheet": {
        "export_mime": "text/csv",
        "label": "Google Sheets",
    },
    "application/vnd.google-apps.presentation": {
        "export_mime": "text/plain",
        "label": "Google Slides",
    },
    "application/vnd.google-apps.drawing": {
        "export_mime": "text/plain",
        "label": "Google Drawings",
    },
}

# File MIME types that can be read as text
TEXT_READABLE_MIMES = {
    "text/plain",
    "text/csv",
    "text/html",
    "text/xml",
    "application/json",
    "application/xml",
    "text/markdown",
    "text/tab-separated-values",
}

# Max file size for direct download (5MB)
MAX_DOWNLOAD_SIZE = 5 * 1024 * 1024


class GoogleDriveService:
    """
    Per-user Google Drive API service with credential caching.

    Maintains separate API service instances per user because
    domain-wide delegation requires a different `subject` for each user.

    Service entries are cached with a 50-minute TTL (before the default
    1-hour OAuth2 token expiry).
    """

    _instance: Optional["GoogleDriveService"] = None
    _lock = threading.Lock()

    def __init__(self, settings: "Settings"):
        self._settings = settings
        # (drive_service, created_at) per user_email
        self._services: Dict[str, Tuple[Any, datetime]] = {}
        self._ttl = timedelta(minutes=50)

    @classmethod
    def get_instance(cls, settings: "Settings") -> "GoogleDriveService":
        """Thread-safe singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(settings)
        return cls._instance

    def _build_credentials(self, user_email: str) -> Credentials:
        """Build delegated credentials for a specific user."""
        val = (self._settings.service_account_json or "").strip()
        if not val:
            raise RuntimeError(
                "SERVICE_ACCOUNT_JSON is not set. "
                "Must provide service account JSON (file path or JSON content)."
            )

        if os.path.exists(val):
            logger.debug("Using service account key file path: %s", val)
            return Credentials.from_service_account_file(
                val, scopes=SCOPES, subject=user_email
            )

        try:
            info = json.loads(val)
            if not isinstance(info, dict):
                raise ValueError("SERVICE_ACCOUNT_JSON did not parse into an object")
            logger.debug("Using service account JSON from environment secret content")
            return Credentials.from_service_account_info(
                info, scopes=SCOPES, subject=user_email
            )
        except Exception as e:
            logger.error("Failed to load service account credentials: %s", e)
            raise

    def get_drive(self, user_email: str) -> Any:
        """Get or create Drive API service for a user."""
        now = datetime.now()

        if user_email in self._services:
            drive, created = self._services[user_email]
            if now - created < self._ttl:
                return drive
            logger.debug("[DriveService] Service expired for %s", user_email)

        creds = self._build_credentials(user_email)
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        self._services[user_email] = (drive, now)
        logger.info("[DriveService] Created service for %s", user_email)
        return drive
