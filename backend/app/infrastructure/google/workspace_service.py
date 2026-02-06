"""
Google Workspace Service - Per-user Gmail and Calendar API access.

Provides read-only access to Gmail and Google Calendar via service account
domain-wide delegation. Each user gets their own API service instances
because the `subject` parameter differs per user.

Authentication: SERVICE_ACCOUNT_JSON (file path or JSON string)
Scopes: gmail.readonly, calendar.readonly
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
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


class GoogleWorkspaceService:
    """
    Per-user Google Workspace API service with credential caching.

    Unlike CompanyDatabaseSheetsService (global singleton for a shared spreadsheet),
    this service maintains separate API service instances per user because
    domain-wide delegation requires a different `subject` for each user.

    Service entries are cached with a 50-minute TTL (before the default
    1-hour OAuth2 token expiry).
    """

    _instance: Optional["GoogleWorkspaceService"] = None
    _lock = threading.Lock()

    def __init__(self, settings: "Settings"):
        self._settings = settings
        # (gmail_service, calendar_service, created_at) per user_email
        self._services: Dict[str, Tuple[Any, Any, datetime]] = {}
        self._ttl = timedelta(minutes=50)

    @classmethod
    def get_instance(cls, settings: "Settings") -> "GoogleWorkspaceService":
        """Thread-safe singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(settings)
        return cls._instance

    def _build_credentials(self, user_email: str) -> Credentials:
        """Build delegated credentials for a specific user.

        Follows the same pattern as drive_docs_collector.py:
        1. If SERVICE_ACCOUNT_JSON is a file path → load from file
        2. Otherwise → parse as JSON string from env variable
        """
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
            logger.error(
                "Failed to load service account credentials: %s", e
            )
            raise

    def _get_services(self, user_email: str) -> Tuple[Any, Any]:
        """Get or create Gmail and Calendar services for a user."""
        now = datetime.now()

        if user_email in self._services:
            gmail, calendar, created = self._services[user_email]
            if now - created < self._ttl:
                return gmail, calendar
            logger.debug("[WorkspaceService] Service expired for %s", user_email)

        creds = self._build_credentials(user_email)
        gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
        calendar = build("calendar", "v3", credentials=creds, cache_discovery=False)
        self._services[user_email] = (gmail, calendar, now)
        logger.info("[WorkspaceService] Created services for %s", user_email)
        return gmail, calendar

    def get_gmail(self, user_email: str) -> Any:
        """Get Gmail API service for a specific user."""
        gmail, _ = self._get_services(user_email)
        return gmail

    def get_calendar(self, user_email: str) -> Any:
        """Get Calendar API service for a specific user."""
        _, calendar = self._get_services(user_email)
        return calendar
