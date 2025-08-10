#!/usr/bin/env python3
"""
Watch 設定スクリプト - Cloud Run Job あるいは Cloud Scheduler＋Pub/Sub から定期実行
Google Drive の changes.watch を使用してフォルダの変更を監視
"""
import uuid, json, datetime, os, logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.cloud import firestore

# 設定
SERVICE_ACCOUNT = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "drive_watch")

# Firestore client
db = firestore.Client()
COL = db.collection(FIRESTORE_COLLECTION)

# ユーザーと Meet Recordings フォルダ ID のマッピング
USERS = {
    "masuda.g@bandq.jp": "1nMb9rtbhmrZoA9A-kf_tBy43eVLnp3BT",
    "narita.k@bandq.jp": "1Vw8W8tciWESV5rsSaj9mcsFJwGsp5iFD",  # 実際のフォルダIDに要変更
}

# Webhook URL (実際のデプロイ先に要変更)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://REGION-PROJECT.cloudfunctions.net/drive_webhook")
TTL_SEC = 7 * 24 * 3600  # 7 days (最大)

logging.basicConfig(level=logging.INFO)

def create_drive_service(user: str):
    """指定ユーザーでドメインワイドデリゲーションを使用してDrive serviceを作成"""
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT, scopes=SCOPES, subject=user
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def stop_existing_watch(user: str):
    """既存のwatch subscription があれば停止"""
    try:
        doc = COL.document(user).get()
        if doc.exists:
            data = doc.to_dict()
            channel_id = data.get("channelId")
            resource_id = data.get("resourceId")
            
            if channel_id and resource_id:
                service = create_drive_service(user)
                service.channels().stop(body={
                    "id": channel_id,
                    "resourceId": resource_id
                }).execute()
                logging.info(f"Stopped existing watch for {user}: {channel_id}")
    except Exception as e:
        logging.warning(f"Failed to stop existing watch for {user}: {e}")

def subscribe_to_changes(user: str, folder_id: str):
    """指定ユーザーのフォルダの変更を監視するwatch subscriptionを作成"""
    try:
        # 既存の subscription を停止
        stop_existing_watch(user)
        
        service = create_drive_service(user)
        
        # 現在の startPageToken を取得
        start_response = service.changes().getStartPageToken(
            supportsAllDrives=True
        ).execute()
        start_page_token = start_response["startPageToken"]
        
        # Watch subscription body を作成
        watch_body = {
            "id": str(uuid.uuid4()),
            "type": "web_hook",
            "address": WEBHOOK_URL,
            "token": json.dumps({"user": user, "folder": folder_id}),
            "expiration": str(
                int((datetime.datetime.utcnow() + datetime.timedelta(seconds=TTL_SEC))
                    .timestamp() * 1000)
            ),
        }

        # changes.watch を実行
        watch_response = service.changes().watch(
            pageToken=start_page_token,
            body=watch_body,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        # Firestore に情報を保存
        COL.document(user).set({
            "pageToken": start_page_token,
            "channelId": watch_response["id"],
            "resourceId": watch_response["resourceId"],
            "expiration": watch_response["expiration"],
            "folderId": folder_id,
            "createdAt": datetime.datetime.utcnow(),
        })
        
        # 期限を人間が読める形式に変換
        expiration_datetime = datetime.datetime.fromtimestamp(
            int(watch_response["expiration"]) / 1000
        )
        
        logging.info(
            f"Watch set for {user} - Channel: {watch_response['id']}, "
            f"Expires: {expiration_datetime.isoformat()}"
        )
        
        return True
        
    except Exception as e:
        logging.error(f"Failed to create watch subscription for {user}: {e}")
        return False

def verify_folder_access(user: str, folder_id: str):
    """フォルダへのアクセス権限を確認"""
    try:
        service = create_drive_service(user)
        folder_info = service.files().get(
            fileId=folder_id,
            fields="id,name,parents",
            supportsAllDrives=True
        ).execute()
        
        logging.info(f"Verified access to folder '{folder_info['name']}' for {user}")
        return True
        
    except Exception as e:
        logging.error(f"Cannot access folder {folder_id} for {user}: {e}")
        return False

def main():
    """メイン処理 - 全ユーザーの watch subscription を設定"""
    logging.info("Starting watch setup process...")
    
    success_count = 0
    total_count = len(USERS)
    
    for user, folder_id in USERS.items():
        logging.info(f"Processing user: {user}")
        
        # フォルダアクセス確認
        if not verify_folder_access(user, folder_id):
            logging.error(f"Skipping {user} due to access issues")
            continue
        
        # Watch subscription 作成
        if subscribe_to_changes(user, folder_id):
            success_count += 1
            logging.info(f"Successfully set up watch for {user}")
        else:
            logging.error(f"Failed to set up watch for {user}")
    
    logging.info(f"Watch setup completed: {success_count}/{total_count} successful")
    
    if success_count < total_count:
        exit(1)  # 一部失敗した場合は非0で終了

def stop_all_watches():
    """全ユーザーの watch subscription を停止（メンテナンス用）"""
    logging.info("Stopping all watch subscriptions...")
    
    for user in USERS.keys():
        stop_existing_watch(user)
        # Firestore からも削除
        try:
            COL.document(user).delete()
            logging.info(f"Deleted Firestore document for {user}")
        except Exception as e:
            logging.warning(f"Failed to delete Firestore document for {user}: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--stop":
        stop_all_watches()
    else:
        main()