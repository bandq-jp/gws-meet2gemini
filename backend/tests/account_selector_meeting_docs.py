#!/usr/bin/env python3
"""
統合された議事録Google ドキュメント取得プログラム
- アカウント選択機能
- Google Docsの議事録取得
- ローカルデータ保存
"""

from __future__ import annotations
import sys
import re
import json
import textwrap
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ===== 設定 =====
SERVICE_ACCOUNT_FILE = Path("service_account.json")
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]

# 登録されているアカウントリスト
AVAILABLE_ACCOUNTS = [
    "masuda.g@bandq.jp",
    "narita.k@bandq.jp", 
    "ito.t@bandq.jp",
]

TARGET_KEYWORD = "Meet Recordings"
CASE_SENSITIVE = False
EXPORT_MIME = "text/plain"
MAX_TEXT_PREVIEW = 600
OUTPUT_DIR = Path("tests/meet-txt/downloaded_meeting_docs")

# 会議情報の正規表現
MEETING_RE = re.compile(
    r"^(?P<title>.+?)\s*-\s*(?P<date>\d{4}/\d{2}/\d{2})\s*(?P<time>\d{1,2}:\d{2})"
)

def get_services(subject: Optional[str]):
    """Drive / Docs 両方の service を返す"""
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=subject
    )
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    docs = build("docs", "v1", credentials=creds, cache_discovery=False)
    return drive, docs

def list_all_folders(drive) -> Dict[str, Dict]:
    """全フォルダを取得"""
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
    """フォルダパスを構築"""
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
    """フォルダ内のファイルを列挙"""
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

def get_doc_structure(docs, doc_id: str) -> dict:
    """Google Docs API documents.get"""
    return docs.documents().get(documentId=doc_id).execute()

def parse_meeting_info(filename: str) -> dict:
    """
    ドキュメント名から
    'タイトル', '日付', '時刻' を推定（Gemini メモの典型的な命名規則用）
    """
    m = MEETING_RE.search(filename)
    if not m:
        return {}
    return m.groupdict()

def select_accounts() -> List[str]:
    """アカウント選択インターフェース"""
    print("利用可能なアカウント:")
    for i, account in enumerate(AVAILABLE_ACCOUNTS, 1):
        print(f"  {i}. {account}")
    print(f"  {len(AVAILABLE_ACCOUNTS) + 1}. すべて選択")
    
    while True:
        try:
            choice = input("\n選択してください (例: 1,3 または all): ").strip()
            
            if choice.lower() in ['all', 'すべて', str(len(AVAILABLE_ACCOUNTS) + 1)]:
                return AVAILABLE_ACCOUNTS[:]
            
            if ',' in choice:
                # 複数選択
                indices = [int(x.strip()) for x in choice.split(',')]
                selected = []
                for idx in indices:
                    if 1 <= idx <= len(AVAILABLE_ACCOUNTS):
                        selected.append(AVAILABLE_ACCOUNTS[idx - 1])
                    else:
                        print(f"無効な番号: {idx}")
                        break
                else:
                    return selected
            else:
                # 単一選択
                idx = int(choice)
                if 1 <= idx <= len(AVAILABLE_ACCOUNTS):
                    return [AVAILABLE_ACCOUNTS[idx - 1]]
                else:
                    print(f"1-{len(AVAILABLE_ACCOUNTS)}の範囲で選択してください")
        except ValueError:
            print("有効な番号を入力してください")

def ensure_output_dir():
    """出力ディレクトリの作成"""
    OUTPUT_DIR.mkdir(exist_ok=True)

def check_existing_document(user_email: str, doc_id: str) -> Optional[Path]:
    """既存の同一文書をチェック"""
    user_dir = OUTPUT_DIR / user_email.replace('@', '_at_').replace('.', '_')
    if not user_dir.exists():
        return None
    
    # 同じdoc_idを含むファイルを検索
    for existing_file in user_dir.glob(f"*{doc_id}*.json"):
        return existing_file
    return None

def save_document_data(user_email: str, doc_info: dict, text_content: str, doc_structure: Optional[dict] = None, force_update: bool = False):
    """ドキュメントデータをローカルに保存"""
    user_dir = OUTPUT_DIR / user_email.replace('@', '_at_').replace('.', '_')
    user_dir.mkdir(exist_ok=True)
    
    # 重複チェック
    existing_file = check_existing_document(user_email, doc_info['id'])
    if existing_file and not force_update:
        # 既存ファイルの更新日時をチェック
        try:
            with open(existing_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_modified = existing_data['metadata']['modifiedTime']
                current_modified = doc_info['modifiedTime']
                
                if existing_modified == current_modified:
                    print(f"    ⏭️  スキップ: {existing_file.name} (変更なし)")
                    return existing_file
                else:
                    print(f"    🔄 更新: {existing_file.name} (文書が更新されています)")
        except (json.JSONDecodeError, KeyError):
            print(f"    ⚠️  既存ファイル読み込みエラー、新規作成します")
    
    # ファイル名の安全化
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', doc_info['name'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # メタデータとテキストを保存
    if existing_file and force_update:
        # 既存ファイルを更新
        data_file = existing_file
    else:
        # 新規ファイル作成
        data_file = user_dir / f"{safe_filename}_{doc_info['id']}_{timestamp}.json"
    
    save_data = {
        "metadata": doc_info,
        "text_content": text_content,
        "meeting_info": parse_meeting_info(doc_info['name']),
        "downloaded_at": datetime.now().isoformat(),
        "doc_structure": doc_structure
    }
    
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    if existing_file and force_update:
        print(f"    💾 更新: {data_file}")
    else:
        print(f"    💾 保存: {data_file}")
    return data_file

def main() -> None:
    try:
        # 出力ディレクトリの準備
        ensure_output_dir()
        
        # アカウント選択
        selected_accounts = select_accounts()
        print(f"\n選択されたアカウント: {', '.join(selected_accounts)}")
        
        # 保存するドキュメントの確認
        save_docs = input("\nドキュメントをローカルに保存しますか? (y/N): ").strip().lower() in ['y', 'yes']
        include_structure = False
        force_update = False
        if save_docs:
            include_structure = input("Docs API構造も含めて保存しますか? (y/N): ").strip().lower() in ['y', 'yes']
            force_update = input("既存ファイルを強制更新しますか? (y/N): ").strip().lower() in ['y', 'yes']
            if include_structure:
                print("⚠️  注意: Docs APIが無効の場合は構造の取得に失敗します")
                print("    有効化: https://console.developers.google.com/apis/api/docs.googleapis.com/overview")
        
        total_docs_found = 0
        total_docs_saved = 0
        
        for user in selected_accounts:
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

                    total_docs_found += 1
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

                    # ローカル保存
                    if save_docs:
                        doc_structure = None
                        if include_structure:
                            try:
                                doc_structure = get_doc_structure(docs, f["id"])
                            except HttpError as e:
                                print(f"    ⚠️  Docs API構造の取得に失敗: {e}")
                        
                        save_document_data(user, f, body_text, doc_structure, force_update)
                        total_docs_saved += 1

        print("\n" + "=" * 70)
        print(f"📊 サマリー:")
        print(f"   検索対象アカウント: {len(selected_accounts)}")
        print(f"   発見されたドキュメント: {total_docs_found}")
        if save_docs:
            print(f"   保存されたドキュメント: {total_docs_saved}")
            print(f"   保存先ディレクトリ: {OUTPUT_DIR.absolute()}")

    except HttpError as e:
        print(f"Drive / Docs API error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(0)

if __name__ == "__main__":
    main()