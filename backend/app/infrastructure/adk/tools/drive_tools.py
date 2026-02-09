"""
Google Drive Tools (ADK version) - Drive read-only access.

Provides per-user access to Google Drive files via service account
domain-wide delegation (drive.readonly scope). User email is read
from tool_context.state["app:user_email"].

Exports Google Docs as text, Sheets as CSV, Slides as text.
No documents.readonly or spreadsheets.readonly scope required.

Tools:
  search_drive_files, list_folder_contents, get_file_metadata,
  read_google_doc, read_spreadsheet, read_file_content
"""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Lazy singleton for drive service
_drive_service = None


def _get_drive_service():
    """Get GoogleDriveService singleton (lazy init)."""
    global _drive_service
    if _drive_service is None:
        from app.infrastructure.google.drive_service import GoogleDriveService
        from app.infrastructure.config.settings import get_settings
        _drive_service = GoogleDriveService.get_instance(get_settings())
    return _drive_service


def _get_user_email(tool_context) -> Optional[str]:
    """Extract user email from tool context state."""
    if tool_context is None:
        return None
    return tool_context.state.get("app:user_email")


# MIME type labels for display
_MIME_LABELS = {
    "application/vnd.google-apps.document": "Google Docs",
    "application/vnd.google-apps.spreadsheet": "Google Sheets",
    "application/vnd.google-apps.presentation": "Google Slides",
    "application/vnd.google-apps.folder": "フォルダ",
    "application/vnd.google-apps.form": "Google Forms",
    "application/vnd.google-apps.drawing": "Google Drawings",
    "application/pdf": "PDF",
    "text/plain": "テキスト",
    "text/csv": "CSV",
    "image/png": "PNG画像",
    "image/jpeg": "JPEG画像",
}


def _format_file(f: Dict) -> Dict[str, Any]:
    """Format a Drive file for AI consumption."""
    mime = f.get("mimeType", "")
    return {
        "id": f.get("id", ""),
        "name": f.get("name", ""),
        "type": _MIME_LABELS.get(mime, mime),
        "mimeType": mime,
        "modifiedTime": f.get("modifiedTime", ""),
        "size": f.get("size", ""),
        "owners": [o.get("displayName", o.get("emailAddress", ""))
                    for o in f.get("owners", [])],
        "webViewLink": f.get("webViewLink", ""),
        "starred": f.get("starred", False),
    }


def _human_size(size_str: str) -> str:
    """Convert bytes string to human-readable size."""
    if not size_str:
        return ""
    try:
        size = int(size_str)
    except (ValueError, TypeError):
        return size_str
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{size}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


# ============================================================
# Drive Tools
# ============================================================


def search_drive_files(
    query: str,
    file_type: Optional[str] = None,
    max_results: int = 15,
    tool_context=None,
) -> Dict[str, Any]:
    """Google Driveでファイルを検索。ファイル名・内容・種類で絞り込み。

    Drive検索構文をサポート:
    - ファイル名: name contains '報告書'
    - 全文検索: fullText contains '売上'
    - フォルダ内: 'FOLDER_ID' in parents
    - 更新日: modifiedTime > '2025-01-01'
    - スター付き: starred = true
    - 組み合わせ可能（AND結合）

    Args:
        query: 検索キーワード（自然言語。Drive検索クエリに自動変換）
        file_type: ファイル種別フィルタ（docs/sheets/slides/pdf/folder/all）。未指定=all
        max_results: 取得件数（1-30、デフォルト15）

    Returns:
        success: 成功/失敗
        query: 使用した検索クエリ
        count: ヒット件数
        files: ファイルリスト（id, name, type, modifiedTime, owners, webViewLink）
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    max_results = max(1, min(30, max_results))

    # Build Drive API query
    q_parts = []

    # File type filter
    mime_map = {
        "docs": "application/vnd.google-apps.document",
        "sheets": "application/vnd.google-apps.spreadsheet",
        "slides": "application/vnd.google-apps.presentation",
        "pdf": "application/pdf",
        "folder": "application/vnd.google-apps.folder",
    }
    if file_type and file_type.lower() in mime_map:
        q_parts.append(f"mimeType = '{mime_map[file_type.lower()]}'")

    # If query looks like a raw Drive API query, use as-is
    if any(op in query for op in ["contains", "in parents", "mimeType", "modifiedTime", "starred"]):
        q_parts.append(query)
    else:
        # Natural language → fullText search + name search
        q_parts.append(f"(name contains '{query}' or fullText contains '{query}')")

    # Exclude trashed files
    q_parts.append("trashed = false")

    q = " and ".join(q_parts)

    try:
        svc = _get_drive_service()
        drive = svc.get_drive(user_email)

        result = drive.files().list(
            q=q,
            pageSize=max_results,
            fields="files(id,name,mimeType,modifiedTime,size,owners,webViewLink,starred)",
            orderBy="modifiedTime desc",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files = [_format_file(f) for f in result.get("files", [])]

        # State tracking
        if tool_context:
            try:
                searches = tool_context.state.get("user:drive_searches", [])
                searches = searches + [{"query": query, "count": len(files)}]
                if len(searches) > 20:
                    searches = searches[-20:]
                tool_context.state["user:drive_searches"] = searches
            except Exception:
                pass

        return {
            "success": True,
            "query": q,
            "count": len(files),
            "files": files,
        }

    except Exception as e:
        logger.error("[search_drive_files] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"Drive検索に失敗しました: {type(e).__name__}"}


def list_folder_contents(
    folder_id: Optional[str] = None,
    max_results: int = 20,
    tool_context=None,
) -> Dict[str, Any]:
    """フォルダ内のファイル一覧を取得。

    Args:
        folder_id: フォルダID。未指定=マイドライブのルート
        max_results: 取得件数（1-50、デフォルト20）

    Returns:
        success: 成功/失敗
        folder_id: フォルダID
        count: ファイル数
        files: ファイルリスト（サブフォルダ含む）
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    max_results = max(1, min(50, max_results))
    parent = folder_id or "root"

    try:
        svc = _get_drive_service()
        drive = svc.get_drive(user_email)

        result = drive.files().list(
            q=f"'{parent}' in parents and trashed = false",
            pageSize=max_results,
            fields="files(id,name,mimeType,modifiedTime,size,owners,webViewLink,starred)",
            orderBy="folder,name",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files = [_format_file(f) for f in result.get("files", [])]

        return {
            "success": True,
            "folder_id": parent,
            "count": len(files),
            "files": files,
        }

    except Exception as e:
        logger.error("[list_folder_contents] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"フォルダ一覧の取得に失敗しました: {type(e).__name__}"}


def get_file_metadata(
    file_id: str,
    tool_context=None,
) -> Dict[str, Any]:
    """ファイルの詳細メタデータを取得。

    Args:
        file_id: ファイルID（search_drive_filesまたはlist_folder_contentsの結果から取得）

    Returns:
        success: 成功/失敗
        id: ファイルID
        name: ファイル名
        type: ファイル種別
        mimeType: MIMEタイプ
        size: ファイルサイズ
        createdTime: 作成日時
        modifiedTime: 更新日時
        owners: オーナー
        lastModifyingUser: 最終更新者
        shared: 共有状態
        webViewLink: 閲覧URL
        parents: 親フォルダID
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    try:
        svc = _get_drive_service()
        drive = svc.get_drive(user_email)

        f = drive.files().get(
            fileId=file_id,
            fields=(
                "id,name,mimeType,size,createdTime,modifiedTime,"
                "owners,lastModifyingUser,shared,sharingUser,"
                "webViewLink,webContentLink,parents,starred,description"
            ),
            supportsAllDrives=True,
        ).execute()

        mime = f.get("mimeType", "")
        last_mod = f.get("lastModifyingUser", {})

        return {
            "success": True,
            "id": f.get("id", ""),
            "name": f.get("name", ""),
            "type": _MIME_LABELS.get(mime, mime),
            "mimeType": mime,
            "size": _human_size(f.get("size", "")),
            "description": f.get("description", ""),
            "createdTime": f.get("createdTime", ""),
            "modifiedTime": f.get("modifiedTime", ""),
            "owners": [
                {"name": o.get("displayName", ""), "email": o.get("emailAddress", "")}
                for o in f.get("owners", [])
            ],
            "lastModifyingUser": {
                "name": last_mod.get("displayName", ""),
                "email": last_mod.get("emailAddress", ""),
            },
            "shared": f.get("shared", False),
            "starred": f.get("starred", False),
            "webViewLink": f.get("webViewLink", ""),
            "parents": f.get("parents", []),
        }

    except Exception as e:
        logger.error("[get_file_metadata] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"ファイル情報の取得に失敗しました: {type(e).__name__}"}


def read_google_doc(
    file_id: str,
    max_chars: int = 5000,
    tool_context=None,
) -> Dict[str, Any]:
    """Google Docsの本文をテキストとして取得。

    Drive APIのexport機能でtext/plainとしてエクスポート。
    documents.readonlyスコープ不要。

    Args:
        file_id: DocsファイルID
        max_chars: 最大文字数（500-20000、デフォルト5000）

    Returns:
        success: 成功/失敗
        file_id: ファイルID
        name: ファイル名
        content: テキスト本文（max_chars文字で切り詰め）
        char_count: 総文字数
        truncated: 切り詰めたかどうか
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    max_chars = max(500, min(20000, max_chars))

    try:
        svc = _get_drive_service()
        drive = svc.get_drive(user_email)

        # Get file name
        meta = drive.files().get(
            fileId=file_id,
            fields="name,mimeType",
            supportsAllDrives=True,
        ).execute()

        mime = meta.get("mimeType", "")
        if mime != "application/vnd.google-apps.document":
            return {
                "success": False,
                "error": f"このファイルはGoogle Docsではありません（{_MIME_LABELS.get(mime, mime)}）。"
                         f"read_spreadsheetまたはread_file_contentを使用してください。",
            }

        # Export as text/plain
        content_bytes = drive.files().export(
            fileId=file_id,
            mimeType="text/plain",
        ).execute()

        content = content_bytes.decode("utf-8", errors="replace") if isinstance(content_bytes, bytes) else str(content_bytes)
        char_count = len(content)
        truncated = char_count > max_chars

        if truncated:
            content = content[:max_chars] + f"\n\n...(以下省略、全{char_count:,}文字中{max_chars:,}文字を表示)"

        return {
            "success": True,
            "file_id": file_id,
            "name": meta.get("name", ""),
            "content": content,
            "char_count": char_count,
            "truncated": truncated,
        }

    except Exception as e:
        logger.error("[read_google_doc] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"Docsの読み取りに失敗しました: {type(e).__name__}"}


def read_spreadsheet(
    file_id: str,
    sheet_name: Optional[str] = None,
    max_chars: int = 8000,
    tool_context=None,
) -> Dict[str, Any]:
    """Google Sheetsの内容をCSV形式で取得。

    Drive APIのexport機能でtext/csvとしてエクスポート。
    spreadsheets.readonlyスコープ不要。

    注意: Drive API exportは最初のシートのみをCSV出力する。
    特定シートを指定する場合はsheet_nameパラメータを使用（gid指定）。

    Args:
        file_id: SheetsファイルID
        sheet_name: シート名（未指定=最初のシート）。Drive APIでは直接シート名指定不可のため、
                    全シートエクスポート後にフィルタする
        max_chars: 最大文字数（500-30000、デフォルト8000）

    Returns:
        success: 成功/失敗
        file_id: ファイルID
        name: ファイル名
        content: CSV形式のテキスト
        char_count: 総文字数
        truncated: 切り詰めたかどうか
        note: エクスポートに関する注意事項
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    max_chars = max(500, min(30000, max_chars))

    try:
        svc = _get_drive_service()
        drive = svc.get_drive(user_email)

        # Get file name and verify type
        meta = drive.files().get(
            fileId=file_id,
            fields="name,mimeType",
            supportsAllDrives=True,
        ).execute()

        mime = meta.get("mimeType", "")
        if mime != "application/vnd.google-apps.spreadsheet":
            return {
                "success": False,
                "error": f"このファイルはGoogle Sheetsではありません（{_MIME_LABELS.get(mime, mime)}）。"
                         f"read_google_docまたはread_file_contentを使用してください。",
            }

        # Export as CSV (first sheet only via Drive API)
        content_bytes = drive.files().export(
            fileId=file_id,
            mimeType="text/csv",
        ).execute()

        content = content_bytes.decode("utf-8", errors="replace") if isinstance(content_bytes, bytes) else str(content_bytes)
        char_count = len(content)
        truncated = char_count > max_chars

        if truncated:
            # Truncate at line boundary
            lines = content[:max_chars].rsplit("\n", 1)
            content = lines[0] + f"\n\n...(以下省略、全{char_count:,}文字中表示)"

        note = "Drive APIのCSVエクスポートは最初のシートのみを出力します。"
        if sheet_name:
            note += f" シート'{sheet_name}'の指定は、spreadsheets.readonlyスコープが必要なため現在は非対応です。"

        return {
            "success": True,
            "file_id": file_id,
            "name": meta.get("name", ""),
            "content": content,
            "char_count": char_count,
            "truncated": truncated,
            "note": note,
        }

    except Exception as e:
        logger.error("[read_spreadsheet] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"Sheetsの読み取りに失敗しました: {type(e).__name__}"}


def read_file_content(
    file_id: str,
    max_chars: int = 5000,
    tool_context=None,
) -> Dict[str, Any]:
    """Google Drive上のファイル内容を読み取り。

    Google Workspace形式（Docs/Sheets/Slides）はテキストとしてエクスポート。
    テキスト系ファイル（.txt, .csv, .json, .md等）は直接ダウンロード。
    バイナリファイル（画像、動画等）はメタデータのみ返却。

    Args:
        file_id: ファイルID
        max_chars: 最大文字数（500-20000、デフォルト5000）

    Returns:
        success: 成功/失敗
        file_id: ファイルID
        name: ファイル名
        type: ファイル種別
        content: テキスト内容（対応形式のみ）
        char_count: 文字数
    """
    user_email = _get_user_email(tool_context)
    if not user_email:
        return {"success": False, "error": "ユーザーメールが取得できません。ログイン状態を確認してください。"}

    max_chars = max(500, min(20000, max_chars))

    try:
        svc = _get_drive_service()
        drive = svc.get_drive(user_email)

        # Get file metadata
        meta = drive.files().get(
            fileId=file_id,
            fields="id,name,mimeType,size",
            supportsAllDrives=True,
        ).execute()

        mime = meta.get("mimeType", "")
        name = meta.get("name", "")
        file_size = meta.get("size", "")

        # Google Workspace format → export
        from app.infrastructure.google.drive_service import GOOGLE_MIME_EXPORTS
        if mime in GOOGLE_MIME_EXPORTS:
            export_info = GOOGLE_MIME_EXPORTS[mime]
            content_bytes = drive.files().export(
                fileId=file_id,
                mimeType=export_info["export_mime"],
            ).execute()

            content = content_bytes.decode("utf-8", errors="replace") if isinstance(content_bytes, bytes) else str(content_bytes)
            char_count = len(content)
            truncated = char_count > max_chars

            if truncated:
                content = content[:max_chars] + f"\n\n...(以下省略、全{char_count:,}文字)"

            return {
                "success": True,
                "file_id": file_id,
                "name": name,
                "type": export_info["label"],
                "content": content,
                "char_count": char_count,
                "truncated": truncated,
            }

        # Text-based files → direct download
        from app.infrastructure.google.drive_service import TEXT_READABLE_MIMES, MAX_DOWNLOAD_SIZE
        if mime in TEXT_READABLE_MIMES or name.endswith((".txt", ".csv", ".json", ".md", ".xml", ".yml", ".yaml", ".log", ".tsv")):
            # Check size
            if file_size and int(file_size) > MAX_DOWNLOAD_SIZE:
                return {
                    "success": True,
                    "file_id": file_id,
                    "name": name,
                    "type": _MIME_LABELS.get(mime, mime),
                    "content": None,
                    "message": f"ファイルが大きすぎます（{_human_size(file_size)}）。5MB以下のファイルのみ読み取り可能です。",
                }

            content_bytes = drive.files().get_media(
                fileId=file_id,
            ).execute()

            content = content_bytes.decode("utf-8", errors="replace") if isinstance(content_bytes, bytes) else str(content_bytes)
            char_count = len(content)
            truncated = char_count > max_chars

            if truncated:
                content = content[:max_chars] + f"\n\n...(以下省略、全{char_count:,}文字)"

            return {
                "success": True,
                "file_id": file_id,
                "name": name,
                "type": _MIME_LABELS.get(mime, mime),
                "content": content,
                "char_count": char_count,
                "truncated": truncated,
            }

        # Binary files → metadata only
        return {
            "success": True,
            "file_id": file_id,
            "name": name,
            "type": _MIME_LABELS.get(mime, mime),
            "mimeType": mime,
            "size": _human_size(file_size),
            "content": None,
            "message": f"バイナリファイル（{_MIME_LABELS.get(mime, mime)}）のため内容は読み取れません。メタデータのみ返却します。",
        }

    except Exception as e:
        logger.error("[read_file_content] Error: %s", e, exc_info=True)
        return {"success": False, "error": f"ファイル読み取りに失敗しました: {type(e).__name__}"}


# ============================================================
# Tool Export List
# ============================================================

ADK_DRIVE_TOOLS = [
    search_drive_files,
    list_folder_contents,
    get_file_metadata,
    read_google_doc,
    read_spreadsheet,
    read_file_content,
]
