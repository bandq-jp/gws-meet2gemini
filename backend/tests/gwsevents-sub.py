#!/usr/bin/env python3
# tests/gwsevents-sub.py
import datetime as dt
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

PROJECT_ID   = "bandq-dx"
TOPIC_NAME   = "drive-events"  # 既に作成済み
FOLDER_ID    = "1nMb9rtbhmrZoA9A-kf_tBy43eVLnp3BT"  # Meet Recordings のフォルダID
SUBJECT_USER = "masuda.g@bandq.jp"                  # DWD の偽装対象ユーザー

# Drive イベントの作成/編集等を購読する場合に許可されるスコープ
SCOPES = [
    # Events API は“対象アプリのスコープ”を使います（Drive）
    # まずは読み取り最小でOK。必要に応じて drive.metadata などへ。
    "https://www.googleapis.com/auth/drive.readonly",
]

def main():
    creds = Credentials.from_service_account_file(
        "service_account.json", scopes=SCOPES, subject=SUBJECT_USER
    )
    # v1 を使用
    events = build("workspaceevents", "v1", credentials=creds, cache_discovery=False)

    body = {
        "targetResource": f"//googleapis.com/drive/v3/files/{FOLDER_ID}",
        # フォルダに“ファイルが追加された”イベント（=ファイル作成扱い）
        "eventTypes": ["google.workspace.drive.file.v3.created"],
        "notificationEndpoint": {
            "pubsubTopic": f"projects/{PROJECT_ID}/topics/{TOPIC_NAME}"
        },
        # まずは payload を最小で（file.id 等は届きます）
        # payloadOptions は省略（必要になったら fieldMask を追加）
        # 期限は TTL で指定（resource を含めないと最長 7d）
        "ttl": "604800s"  # 7日
    }

    op = events.subscriptions().create(body=body).execute()
    print(json.dumps(op, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
