from __future__ import annotations

from typing import List, Optional, Dict, Any
import io
import json
import logging
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.infrastructure.config.settings import get_settings
from app.domain.entities.meeting_document import MeetingDocument
from app.infrastructure.notta.xlsx_parser import NottaXlsxParser


SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_SHEET_MIME = "application/vnd.google-apps.spreadsheet"


class NottaDriveXlsxCollector:
    """Collect Notta Excel transcripts from a shared Drive folder."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.parser = NottaXlsxParser()

    async def collect_meeting_docs(
        self,
        accounts: Optional[List[str]] = None,
        include_structure: bool = False,
        skip_failed_exports: bool = False,
    ) -> List[MeetingDocument]:
        subject = self._resolve_subject(accounts)
        if not subject:
            raise RuntimeError("No impersonation subject available for Notta collection")

        import asyncio

        return await asyncio.to_thread(self._collect_for_subject_sync, subject, skip_failed_exports)

    def list_shared_drives(self) -> List[Dict[str, Any]]:
        subject = self._resolve_subject(None)
        if not subject:
            raise RuntimeError("No impersonation subject available for Notta drive listing")
        drive = self._build_drive(subject)
        drives: List[Dict[str, Any]] = []
        page_token = None
        while True:
            resp = drive.drives().list(pageSize=100, pageToken=page_token).execute()
            drives.extend(resp.get("drives", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return drives

    def list_folders(
        self,
        drive_id: Optional[str] = None,
        name: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        subject = self._resolve_subject(None)
        if not subject:
            raise RuntimeError("No impersonation subject available for Notta folder listing")
        drive = self._build_drive(subject)

        q = ["mimeType='application/vnd.google-apps.folder'", "trashed=false"]
        if name:
            q.append(f"name='{name}'")
        query = " and ".join(q)

        folders: List[Dict[str, Any]] = []
        page_token = None
        while True:
            params = {
                "q": query,
                "fields": "nextPageToken, files(id,name,parents,driveId)",
                "pageSize": min(max(limit, 1), 1000),
                "corpora": "drive" if drive_id else "allDrives",
                "includeItemsFromAllDrives": True,
                "supportsAllDrives": True,
                "pageToken": page_token,
            }
            if drive_id:
                params["driveId"] = drive_id
            resp = drive.files().list(**params).execute()
            folders.extend(resp.get("files", []))
            if len(folders) >= limit:
                return folders[:limit]
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return folders

    def _collect_for_subject_sync(self, subject: str, skip_failed_exports: bool) -> List[MeetingDocument]:
        self.logger.debug("Start Notta collection subject=%s", subject)
        drive = self._build_drive(subject)

        folder_id = self.settings.notta_folder_id
        if not folder_id and self.settings.notta_folder_name:
            matches = self._find_folder_by_name(
                drive,
                name=self.settings.notta_folder_name,
                drive_id=self.settings.notta_drive_id or None,
                limit=50,
            )
            if len(matches) == 1:
                folder_id = matches[0]["id"]
            elif not matches:
                raise RuntimeError(
                    f"NOTTA_FOLDER_NAME not found: {self.settings.notta_folder_name}"
                )
            else:
                ids = ", ".join([f"{m.get('name')}:{m.get('id')}" for m in matches])
                raise RuntimeError(
                    f"NOTTA_FOLDER_NAME matched multiple folders. Set NOTTA_FOLDER_ID explicitly. Matches: {ids}"
                )

        if not folder_id:
            raise RuntimeError(
                "NOTTA_FOLDER_ID is not set. Use /api/v1/meetings/notta/drives and /api/v1/meetings/notta/folders to discover."
            )

        files = self._list_xlsx_files(drive, folder_id)
        results: List[MeetingDocument] = []
        for f in files:
            try:
                data = self._download_xlsx(drive, f)
                parsed = self.parser.parse(data, f.get("name"))
                meeting = MeetingDocument(
                    id=None,
                    doc_id=f["id"],
                    title=parsed.title or f.get("name"),
                    meeting_datetime=parsed.meeting_datetime or f.get("modifiedTime"),
                    organizer_email=self.settings.notta_organizer_email,
                    organizer_name=None,
                    document_url=f.get("webViewLink"),
                    invited_emails=[],
                    text_content=parsed.text_content,
                    metadata=self._build_metadata(f, parsed),
                )
                results.append(meeting)
            except Exception as e:
                self.logger.error("Failed to parse Notta xlsx id=%s name=%s error=%s", f.get("id"), f.get("name"), e)
                if skip_failed_exports:
                    continue
                raise
        self.logger.debug("Finished Notta collection total=%d", len(results))
        return results

    def _find_folder_by_name(
        self,
        drive,
        name: str,
        drive_id: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        q = f"mimeType='application/vnd.google-apps.folder' and trashed=false and name='{name}'"
        folders: List[Dict[str, Any]] = []
        page_token = None
        while True:
            params = {
                "q": q,
                "fields": "nextPageToken, files(id,name,parents,driveId)",
                "pageSize": min(max(limit, 1), 1000),
                "corpora": "drive" if drive_id else "allDrives",
                "includeItemsFromAllDrives": True,
                "supportsAllDrives": True,
                "pageToken": page_token,
            }
            if drive_id:
                params["driveId"] = drive_id
            resp = drive.files().list(**params).execute()
            folders.extend(resp.get("files", []))
            if len(folders) >= limit:
                return folders[:limit]
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return folders

    def _list_xlsx_files(self, drive, folder_id: str) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        page_token = None
        query = (
            f"'{folder_id}' in parents and trashed=false and "
            f"(mimeType='{_XLSX_MIME}' or mimeType='{_SHEET_MIME}')"
        )
        while True:
            resp = (
                drive.files()
                .list(
                    q=query,
                    fields=(
                        "nextPageToken, files(id,name,mimeType,createdTime,modifiedTime,"
                        "owners(emailAddress,displayName),webViewLink,size,driveId)"
                    ),
                    pageSize=1000,
                    corpora="allDrives",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    pageToken=page_token,
                )
                .execute()
            )
            files.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        self.logger.info("Notta folder files=%d", len(files))
        return files

    def _download_xlsx(self, drive, file_meta: Dict[str, Any]) -> bytes:
        file_id = file_meta["id"]
        mime = file_meta.get("mimeType")
        if mime == _SHEET_MIME:
            request = drive.files().export(fileId=file_id, mimeType=_XLSX_MIME)
        else:
            request = drive.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return fh.getvalue()

    def _build_metadata(self, file_meta: Dict[str, Any], parsed) -> Dict[str, Any]:
        metadata = dict(file_meta)
        metadata.update(
            {
                "transcript_provider": "notta",
                "transcript_source": "notta_xlsx",
                "duration_mins": parsed.duration_mins,
                "notta_raw_title": parsed.title,
                "notta_meta_line": parsed.meta_line,
                "notta_sheet_name": parsed.sheet_name,
                "speaker_stats": parsed.speaker_stats,
                "row_count": parsed.row_count,
            }
        )
        return metadata

    def _resolve_subject(self, accounts: Optional[List[str]]) -> Optional[str]:
        if self.settings.notta_impersonate_subject:
            return self.settings.notta_impersonate_subject
        if accounts:
            return accounts[0]
        if self.settings.impersonate_subjects:
            return self.settings.impersonate_subjects[0]
        return None

    def _build_drive(self, subject: Optional[str]):
        creds = self._build_credentials(subject)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def _build_credentials(self, subject: Optional[str]):
        val = (self.settings.service_account_json or "").strip()
        if not val:
            raise RuntimeError("SERVICE_ACCOUNT_JSON is not set. Must provide service account JSON (file path or JSON content).")
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
            self.logger.error(
                "Failed to load service account credentials from SERVICE_ACCOUNT_JSON. Provide a valid file path or JSON. Error: %s",
                e,
            )
            raise
