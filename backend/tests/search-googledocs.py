#!/usr/bin/env python3
"""
* ドメインワイド・デリゲーションで複数ユーザーを偽装  
* Drive で “Meet Recordings” フォルダを探す  
* フォルダ内の Google ドキュメントの
    - ファイルメタデータ
    - プレーンテキスト（Drive export）
    - JSON 構造（Docs API）
  を取得して表示
"""
from __future__ import annotations
import sys, re, json, textwrap
from pathlib import Path
from typing import Dict, Optional, List

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ───────────────────────── 設 定 ──────────────────────────
SERVICE_ACCOUNT_FILE = Path("service_account.json")
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]

USER_EMAILS = [
    "ito.t@bandq.jp",
]

TARGET_KEYWORD = "Meet Recordings"
CASE_SENSITIVE = False
EXPORT_MIME = "text/plain"                     # Drive export で取得する MIME
MAX_TEXT_PREVIEW = 600                         # コンソールに出す本文プレビューの長さ
# ─────────────────────────────────────────────────────────

def get_services(subject: Optional[str]):
    """Drive / Docs 両方の service を返す"""
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=subject
    )
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    docs  = build("docs",  "v1", credentials=creds, cache_discovery=False)
    return drive, docs


# ---------- Drive ヘルパ ---------- #
def list_all_folders(drive) -> Dict[str, Dict]:
    folders: Dict[str, Dict] = {}
    page_token = None
    while True:
        resp = (
            drive.files()
            .list(
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="nextPageToken, files(id,name,parents)",
                pageSize=1000,
                corpora="allDrives",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageToken=page_token,
            )
            .execute()
        )
        for f in resp.get("files", []):
            folders[f["id"]] = {"name": f["name"], "parents": f.get("parents", [])}
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return folders


def build_path(folder_id: str, folders: Dict[str, Dict]) -> List[str]:
    parts: List[str] = []
    cur = folder_id
    while cur:
        node = folders.get(cur)
        if not node:
            break
        parts.append(node["name"])
        cur = node["parents"][0] if node.get("parents") else None
    return list(reversed(parts))


def list_files_in_folder(drive, folder_id: str):
    files = []
    page_token = None
    while True:
        resp = (
            drive.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields=(
                    "nextPageToken, "
                    "files(id,name,mimeType,createdTime,modifiedTime,owners,webViewLink)"
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
    return files


def export_doc_as_text(drive, file_id: str, mime: str = EXPORT_MIME) -> str:
    """Drive export を使って Google ドキュメントをプレーンテキスト取得"""
    data = drive.files().export(fileId=file_id, mimeType=mime).execute()
    return data.decode("utf-8")


# ---------- Docs API ヘルパ ---------- #
def get_doc_structure(docs, doc_id: str) -> dict:
    """Google Docs API documents.get"""
    return docs.documents().get(documentId=doc_id).execute()


# ---------- (オプション) 会議情報抽出 ---------- #
MEETING_RE = re.compile(
    r"^(?P<title>.+?)\s*-\s*(?P<date>\d{4}/\d{2}/\d{2})\s*(?P<time>\d{1,2}:\d{2})"
)

def parse_meeting_info(filename: str) -> dict:
    """
    ドキュメント名から
    'タイトル', '日付', '時刻' を推定（Gemini メモの典型的な命名規則用）
    """
    m = MEETING_RE.search(filename)
    if not m:
        return {}
    return m.groupdict()


# ────────────────────────── main ──────────────────────────
def main() -> None:
    try:
        for user in USER_EMAILS:
            print("=" * 70)
            print(f"🔍  USER: {user}")

            drive, docs = get_services(user)
            folders = list_all_folders(drive)

            match = (
                (lambda n: n == TARGET_KEYWORD)
                if CASE_SENSITIVE
                else (lambda n: n.lower() == TARGET_KEYWORD.lower())
            )
            meet_folders = [fid for fid, meta in folders.items() if match(meta["name"])]

            if not meet_folders:
                print("  ❌ Meet Recordings folder not found.")
                continue

            for fid in meet_folders:
                path = build_path(fid, folders)
                print(f"\n📂  {' / '.join(path)} (id: {fid})")

                for f in list_files_in_folder(drive, fid):
                    if f["mimeType"] != "application/vnd.google-apps.document":
                        continue  # Google ドキュメント以外はスキップ

                    meta_json = json.dumps(f, ensure_ascii=False, indent=2)
                    body_text = export_doc_as_text(drive, f["id"])

                    print(f"\n📝  {f['name']} (id: {f['id']})")
                    print(f"    ├─ updated : {f['modifiedTime']}")
                    print(f"    ├─ webView : {f['webViewLink']}")
                    meet_info = parse_meeting_info(f["name"])
                    if meet_info:
                        print(
                            f"    └─ meeting : "
                            f"{meet_info.get('title')} "
                            f"@ {meet_info.get('date')} {meet_info.get('time')}"
                        )

                    # 本文プレビュー
                    preview = textwrap.shorten(body_text, width=MAX_TEXT_PREVIEW)
                    print(f"\n----- TEXT PREVIEW -----\n{preview}\n------------------------")

                    # JSON 構造が欲しい場合は Docs API を呼び出す
                    # doc_struct = get_doc_structure(docs, f["id"])
                    # with open(f"{f['id']}.json", "w", encoding="utf-8") as fp:
                    #     json.dump(doc_struct, fp, ensure_ascii=False, indent=2)

    except HttpError as e:
        print(f"Drive / Docs API error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
