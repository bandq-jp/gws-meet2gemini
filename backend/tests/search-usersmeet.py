#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, Optional, List

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ===== 設定 =====
SERVICE_ACCOUNT_FILE = Path("service_account.json")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# 検索対象ユーザー（ドメインワイドデリゲーション前提）
USER_EMAILS = [
    "masuda.g@bandq.jp",
    "narita.k@bandq.jp",
    # 追加可能
]

TARGET_KEYWORD = "Meet Recordings"
CASE_SENSITIVE = False

# =================

def get_service(subject: Optional[str]):
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
        subject=subject
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_all_folders(service) -> Dict[str, Dict]:
    folders: Dict[str, Dict] = {}
    page_token = None
    while True:
        response = service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="nextPageToken, files(id, name, parents)",
            pageSize=1000,
            corpora="allDrives",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            pageToken=page_token
        ).execute()

        for f in response.get("files", []):
            folders[f["id"]] = {"name": f["name"], "parents": f.get("parents", [])}

        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return folders


def build_path(folder_id: str, folders: Dict[str, Dict]) -> List[str]:
    parts = []
    current = folder_id
    while current:
        node = folders.get(current)
        if not node:
            break
        parts.append(node["name"])
        current = node["parents"][0] if node.get("parents") else None
    return list(reversed(parts))


def list_files_in_folder(service, folder_id: str):
    """フォルダ内のファイルを列挙"""
    files = []
    page_token = None
    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
            pageSize=1000,
            corpora="allDrives",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            pageToken=page_token
        ).execute()

        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return files


def main():
    try:
        for user_email in USER_EMAILS:
            print("="*60)
            print(f"🔍 Searching for user: {user_email}")
            service = get_service(user_email)
            folders = list_all_folders(service)

            def match(name: str) -> bool:
                return (
                    name == TARGET_KEYWORD
                    if CASE_SENSITIVE
                    else name.lower() == TARGET_KEYWORD.lower()
                )

            hits = [fid for fid, meta in folders.items() if match(meta["name"])]

            if not hits:
                print("  ❌ No 'Meet Recordings' folder found.")
                continue

            for fid in hits:
                path = build_path(fid, folders)
                print(f"\n📂 Found folder: {' / '.join(path)} (id: {fid})")
                files = list_files_in_folder(service, fid)
                if not files:
                    print("   (No files in this folder)")
                else:
                    print("   Files:")
                    for f in files:
                        print(f"     - {f['name']} (id: {f['id']}, updated: {f['modifiedTime']})")

    except HttpError as err:
        print(f"Drive API error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
