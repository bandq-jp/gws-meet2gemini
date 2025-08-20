from __future__ import annotations
from typing import List, Optional, Dict, Any
import re
import os
import json
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
import google.auth

from app.infrastructure.config.settings import get_settings
from app.domain.entities.meeting_document import MeetingDocument
MEETING_RE = re.compile(r"^(?P<title>.+?)\s*-\s*(?P<date>\d{4}/\d{2}/\d{2})\s*(?P<time>\d{1,2}:\d{2})")

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]

class DriveDocsCollector:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)

    async def collect_meeting_docs(self, accounts: Optional[List[str]] = None, include_structure: bool = False) -> List[MeetingDocument]:
        subjects = accounts or self.settings.impersonate_subjects
        self.logger.debug("collect_meeting_docs: subjects=%s include_structure=%s", subjects, include_structure)
        results: List[MeetingDocument] = []
        skipped_accounts: List[str] = []
        for subject in subjects:
            self.logger.debug("Start collecting for subject=%s", subject)
            try:
                drive = self._build_drive(subject)
                docs = self._build_docs(subject)
                folders = self._list_all_folders(drive)
                self.logger.debug("Total folders found=%d", len(folders))
                meet_folders = [fid for fid, meta in folders.items() if meta.get("name", "").lower() == "meet recordings".lower()]
                if not meet_folders:
                    self.logger.warning("No 'Meet Recordings' folder found for subject=%s", subject)
                for fid in meet_folders:
                    self.logger.debug("Scanning folder id=%s name=%s", fid, folders.get(fid, {}).get("name"))
                    files = self._list_files_in_folder(drive, fid)
                    self.logger.debug("Files in folder=%d", len(files))
                    for f in files:
                        mime = f.get("mimeType")
                        self.logger.debug("File id=%s name=%s mime=%s", f.get("id"), f.get("name"), mime)
                        if mime != "application/vnd.google-apps.document":
                            self.logger.debug("Skip non-Google Doc id=%s", f.get("id"))
                            continue
                        text = self._export_doc_as_text(drive, f["id"]) or ""
                        self.logger.debug("Exported text length id=%s len=%d", f.get("id"), len(text))
                        invited = self._get_invited_emails(drive, f["id"]) or []
                        self.logger.debug("Invited emails count id=%s count=%d", f.get("id"), len(invited))
                        organizer_name = None
                        if isinstance(f.get("owners"), list) and f["owners"]:
                            owner = f["owners"][0]
                            organizer_name = owner.get("displayName")
                        title = f.get("name")
                        meeting_dt = self._parse_meeting_datetime(title) or f.get("modifiedTime")
                        if meeting_dt == f.get("modifiedTime"):
                            self.logger.debug("Datetime parsed from modifiedTime id=%s", f.get("id"))
                        else:
                            self.logger.debug("Datetime parsed from title id=%s", f.get("id"))
                        meeting = MeetingDocument(
                            id=None,
                            doc_id=f["id"],
                            title=title,
                            meeting_datetime=meeting_dt,
                            organizer_email=subject,
                            organizer_name=organizer_name,
                            document_url=f.get("webViewLink"),
                            invited_emails=invited,
                            text_content=text,
                            metadata=f,
                        )
                        results.append(meeting)
                self.logger.debug("Accumulated results for subject=%s count=%d", subject, len(results))
            except (RefreshError, HttpError) as e:
                self.logger.warning("Skip subject due to auth/API error: subject=%s error=%s", subject, e)
                skipped_accounts.append(subject)
                continue
            except Exception as e:
                self.logger.error("Skip subject due to unexpected error: subject=%s error=%s", subject, e)
                skipped_accounts.append(subject)
                continue

        if skipped_accounts:
            self.logger.warning("Skipped accounts: %s", ", ".join(skipped_accounts))
        return results

    def _build_drive(self, subject: Optional[str]):
        creds = self._build_credentials(subject)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def _build_docs(self, subject: Optional[str]):
        creds = self._build_credentials(subject)
        return build("docs", "v1", credentials=creds, cache_discovery=False)

    def _build_credentials(self, subject: Optional[str]):
        val = (self.settings.service_account_json or "").strip()
        if not val:
            raise RuntimeError("SERVICE_ACCOUNT_JSON is not set. Must provide service account JSON (file path or JSON content).")
        # Prefer explicit service account key. Do not fall back to default credentials.
        # 1) If path exists, load from file. 2) Otherwise try to parse as JSON content from env/secret.
        if os.path.exists(val):
            self.logger.debug("Using service account key file path: %s", val)
            return Credentials.from_service_account_file(val, scopes=SCOPES, subject=subject)
        try:
            info = json.loads(val)
            if not isinstance(info, dict):
                raise ValueError("SERVICE_ACCOUNT_JSON did not parse into an object")
            self.logger.debug("Using service account JSON from environment secret content")
            return Credentials.from_service_account_info(info, scopes=SCOPES, subject=subject)
        except Exception as e:
            self.logger.error("Failed to load service account credentials from SERVICE_ACCOUNT_JSON. Provide a valid file path or JSON. Error: %s", e)
            raise

    def _list_all_folders(self, drive) -> Dict[str, Dict[str, Any]]:
        folders: Dict[str, Dict[str, Any]] = {}
        page_token = None
        while True:
            resp = (
                drive.files().list(
                    q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                    fields="nextPageToken, files(id,name,parents)",
                    pageSize=1000,
                    corpora="allDrives",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    pageToken=page_token,
                ).execute()
            )
            for f in resp.get("files", []):
                folders[f["id"]] = {"name": f["name"], "parents": f.get("parents", [])}
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return folders

    def _list_files_in_folder(self, drive, folder_id: str):
        files: list[Dict[str, Any]] = []
        page_token = None
        while True:
            resp = (
                drive.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields=("nextPageToken, files(id,name,mimeType,createdTime,modifiedTime,owners(emailAddress,displayName),webViewLink)"),
                    pageSize=1000,
                    corpora="allDrives",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    pageToken=page_token,
                ).execute()
            )
            files.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return files

    def _export_doc_as_text(self, drive, file_id: str) -> str:
        try:
            data = drive.files().export(fileId=file_id, mimeType="text/plain").execute()
            return data.decode("utf-8")
        except Exception as e:
            self.logger.error("Failed to export doc as text id=%s error=%s", file_id, e)
            return ""

    def _get_invited_emails(self, drive, file_id: str) -> list[str]:
        try:
            perms = drive.permissions().list(fileId=file_id, fields="permissions(emailAddress)" ,supportsAllDrives=True).execute()
            emails = [p.get("emailAddress") for p in perms.get("permissions", []) if p.get("emailAddress")]
            return list(sorted(set(emails)))
        except Exception as e:
            self.logger.debug("Failed to fetch permissions id=%s error=%s", file_id, e)
            return []

    def _parse_meeting_datetime(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        m = MEETING_RE.search(name)
        if not m:
            return None
        info = m.groupdict()
        # Convert to RFC3339 style 'YYYY-MM-DDTHH:MM:00Z' naive (no TZ); leave as 'YYYY/MM/DD HH:MM'
        return f"{info['date']} {info['time']}"
