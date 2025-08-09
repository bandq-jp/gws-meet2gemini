from __future__ import annotations
from typing import List, Optional, Dict, Any
import re
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
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

    async def collect_meeting_docs(self, accounts: Optional[List[str]] = None, include_structure: bool = False) -> List[MeetingDocument]:
        subjects = accounts or self.settings.impersonate_subjects
        results: List[MeetingDocument] = []
        for subject in subjects:
            drive = self._build_drive(subject)
            docs = self._build_docs(subject)
            folders = self._list_all_folders(drive)
            meet_folders = [fid for fid, meta in folders.items() if meta.get("name", "").lower() == "meet recordings".lower()]
            for fid in meet_folders:
                for f in self._list_files_in_folder(drive, fid):
                    if f.get("mimeType") != "application/vnd.google-apps.document":
                        continue
                    text = self._export_doc_as_text(drive, f["id"]) or ""
                    invited = self._get_invited_emails(drive, f["id"]) or []
                    organizer_name = None
                    if isinstance(f.get("owners"), list) and f["owners"]:
                        owner = f["owners"][0]
                        organizer_name = owner.get("displayName")
                    title = f.get("name")
                    meeting_dt = self._parse_meeting_datetime(title) or f.get("modifiedTime")
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
        return results

    def _build_drive(self, subject: Optional[str]):
        if os.path.exists(self.settings.service_account_json):
            creds = Credentials.from_service_account_file(self.settings.service_account_json, scopes=SCOPES, subject=subject)
        else:
            # Cloud Run: use attached service account (no subject impersonation)
            creds, _ = google.auth.default(scopes=SCOPES)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def _build_docs(self, subject: Optional[str]):
        if os.path.exists(self.settings.service_account_json):
            creds = Credentials.from_service_account_file(self.settings.service_account_json, scopes=SCOPES, subject=subject)
        else:
            creds, _ = google.auth.default(scopes=SCOPES)
        return build("docs", "v1", credentials=creds, cache_discovery=False)

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
        data = drive.files().export(fileId=file_id, mimeType="text/plain").execute()
        return data.decode("utf-8")

    def _get_invited_emails(self, drive, file_id: str) -> list[str]:
        try:
            perms = drive.permissions().list(fileId=file_id, fields="permissions(emailAddress)" ,supportsAllDrives=True).execute()
            emails = [p.get("emailAddress") for p in perms.get("permissions", []) if p.get("emailAddress")]
            return list(sorted(set(emails)))
        except Exception:
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
