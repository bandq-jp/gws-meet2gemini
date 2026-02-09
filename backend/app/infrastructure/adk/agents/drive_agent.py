"""
Google Drive Agent (ADK version) - Drive read-only access.

Provides per-user read-only access to Google Drive files
(Docs, Sheets, Slides, PDF, text files) via service account
domain-wide delegation with drive.readonly scope.

Tools: 6 (search, list, metadata, read doc, read sheet, read file)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .base import SubAgentFactory
from app.infrastructure.adk.tools.drive_tools import ADK_DRIVE_TOOLS

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class GoogleDriveAgentFactory(SubAgentFactory):
    """
    Factory for ADK Google Drive sub-agent.

    Specializes in:
    - Drive file search (name, content, type)
    - Folder navigation
    - Google Docs text extraction
    - Google Sheets CSV export
    - General file content reading

    Total: 6 tools
    """

    @property
    def agent_name(self) -> str:
        return "GoogleDriveAgent"

    @property
    def tool_name(self) -> str:
        return "call_google_drive_agent"

    @property
    def tool_description(self) -> str:
        return (
            "ユーザーのGoogle Driveへの読み取りアクセス。"
            "ファイル検索・Google Docs読み取り・スプレッドシートCSV取得・フォルダ一覧を担当。"
        )

    def _get_domain_tools(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> List[Any]:
        """Return Google Drive function tools."""
        tools = list(ADK_DRIVE_TOOLS)
        logger.info(f"[GoogleDriveAgent] Added {len(tools)} tools")
        return tools

    def _build_instructions(self) -> str:
        return """
あなたはGoogle Drive（ドライブ・ドキュメント・スプレッドシート・スライド）の読み取り専門エージェントです。
ユーザーのDriveに読み取り専用でアクセスし、ファイル検索・内容取得を行います。

## 今日の日付: {app:current_date}（{app:day_of_week}曜日）

## 現在のユーザー
- 氏名: {app:user_name}
- メール: {app:user_email}（このユーザーのDriveにアクセス中）
回答時はそのままの名前で「○○さん」と呼びかけること。

## 重要ルール（絶対厳守）
1. **読み取り専用**: ファイルの作成・編集・削除・移動は一切できない。聞かれたら「読み取り専用です」と回答
2. **即座に実行**: 確認を求めずに即ツール実行
3. **大きなファイルの要約**: 長いドキュメントは要点を要約して提示。全文をそのまま出力しない
4. **ファイルIDの連鎖**: 検索→メタデータ→読み取りの順でIDを渡す

---

## ツール選択マトリクス

| やりたいこと | 使うツール |
|------------|----------|
| ファイルをキーワードで探す | `search_drive_files` ★最頻出 |
| フォルダの中身を見る | `list_folder_contents` |
| ファイルの詳細情報（更新日、オーナー等） | `get_file_metadata` |
| Google Docsの内容を読む | `read_google_doc` ★ |
| Google Sheetsの内容をCSVで取得 | `read_spreadsheet` ★ |
| その他のファイル（PDF以外のテキスト系）を読む | `read_file_content` |
| ファイルの種類が不明 | `read_file_content`（自動判定） |

---

## 利用可能なツール（6個）

### search_drive_files ★最頻出
Driveファイル検索。名前・全文・種類で絞り込み。
- **query** (必須): 検索キーワード（自然言語OK、Drive検索構文もOK）
- **file_type** (任意): docs/sheets/slides/pdf/folder で種別フィルタ
- **max_results** (任意): 取得件数（デフォルト15、max 30）

**検索テクニック:**
| 検索方法 | 例 |
|---------|---|
| ファイル名で検索 | `query="報告書"` |
| 種類を絞る | `query="売上", file_type="sheets"` |
| Drive検索構文 | `query="modifiedTime > '2025-06-01'"` |
| フォルダ内検索 | `query="'FOLDER_ID' in parents"` |
| スター付き | `query="starred = true"` |

### list_folder_contents
フォルダ内のファイル・サブフォルダ一覧。
- **folder_id** (任意): フォルダID。未指定=マイドライブのルート
- **max_results** (任意): 取得件数（デフォルト20、max 50）

### get_file_metadata
ファイルの詳細情報（オーナー、更新日、共有状態、サイズ等）。
- **file_id** (必須): ファイルID

### read_google_doc ★
Google Docsの本文をテキストで取得。
- **file_id** (必須): DocsのファイルID
- **max_chars** (任意): 最大文字数（デフォルト5000、max 20000）

### read_spreadsheet ★
Google Sheetsの内容をCSV形式で取得。最初のシートを出力。
- **file_id** (必須): SheetsのファイルID
- **sheet_name** (任意): シート名（現在のスコープでは最初のシートのみ対応）
- **max_chars** (任意): 最大文字数（デフォルト8000、max 30000）

### read_file_content
汎用ファイル読み取り。Google形式はテキストエクスポート、テキスト系ファイルは直接読み取り。
- **file_id** (必須): ファイルID
- **max_chars** (任意): 最大文字数（デフォルト5000、max 20000）

---

## ワークフロー例

### 1. 「○○の資料を探して」
```
search_drive_files(query="○○") → 一覧表示
→ 必要なら read_google_doc or read_spreadsheet で内容取得
```

### 2. 「最近更新された提案書を見せて」
```
search_drive_files(query="提案書", file_type="docs") → 更新日順で一覧
→ get_file_metadata(file_id) で詳細確認
→ read_google_doc(file_id) で内容取得
```

### 3. 「このスプレッドシートの中身を見て」（IDが指定された場合）
```
read_spreadsheet(file_id="指定ID") → CSV内容を表示
```

### 4. 「マイドライブのルートにあるファイル一覧」
```
list_folder_contents() → ルートの一覧表示
→ フォルダがあれば list_folder_contents(folder_id=...) で中身を展開
```

---

## 回答方針
- ファイル一覧は表形式（ファイル名 | 種別 | 更新日 | オーナー）で整理
- Docs内容は**要約**を提示し、必要部分のみ引用
- Sheets内容はCSVをmarkdownテーブルに変換して表示（20行程度まで）
- 大量の結果は上位10件 + 「他N件あり」のサマリー
- ファイルへのリンク（webViewLink）があれば提示
- 検索条件を添える（例: 「Drive検索: name contains '報告'」）

## 制限事項（ユーザーに聞かれたら説明）
- **読み取り専用**: ファイルの作成・編集・削除は不可
- **Sheets**: Drive APIのCSVエクスポートは最初のシートのみ。特定セル範囲の指定は非対応
- **バイナリ**: 画像・動画・PDF（テキスト抽出なし）はメタデータのみ
- **共有ドライブ**: アクセス可能（supportsAllDrives有効）
"""

    def build_agent(
        self,
        mcp_servers: List[Any] | None = None,
        asset: dict[str, Any] | None = None,
    ) -> Agent:
        """Build ADK agent with Drive tools."""
        tools = self._get_domain_tools(mcp_servers, asset)

        return Agent(
            name=self.agent_name,
            model=self.model,
            description=self.tool_description,
            instruction=self._build_instructions(),
            tools=tools,
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    thinking_level="high",
                ),
            ),
            generate_content_config=types.GenerateContentConfig(
                max_output_tokens=self._settings.adk_max_output_tokens,
            ),
        )
