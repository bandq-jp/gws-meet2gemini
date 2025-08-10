"""
Cloud Functions 2nd gen - Google Drive Webhook Handler
Environment variables:
  SERVICE_ACCOUNT_JSON : service_account.json path
  FIRESTORE_COLLECTION : drive_watch (Firestore collection name)
"""
from __future__ import annotations
import base64, json, os, logging
from pathlib import Path

from flask import Flask, request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.cloud import firestore

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "drive_watch")
SERVICE_ACCOUNT_JSON = os.environ.get("SERVICE_ACCOUNT_JSON", "service_account.json")

# Firestore client
db = firestore.Client()
COL = db.collection(FIRESTORE_COLLECTION)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def drive_service(user: str):
    """Create Drive service with domain-wide delegation"""
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_JSON, scopes=SCOPES, subject=user
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def save_token(user: str, token: str):
    """Save pageToken to Firestore"""
    COL.document(user).set({"pageToken": token})
    logging.info(f"Saved pageToken for {user}")

def load_token(user: str) -> str | None:
    """Load pageToken from Firestore"""
    doc = COL.document(user).get()
    return doc.to_dict().get("pageToken") if doc.exists else None

def process_document(drive, file_info: dict, user: str):
    """Process newly added Google Document"""
    try:
        # Export document as plain text
        text = drive.files().export(
            fileId=file_info["id"], 
            mimeType="text/plain"
        ).execute().decode("utf-8")

        logging.info(
            "Doc added: %s (%s) by %s – %d chars",
            file_info["name"], file_info["id"], user, len(text)
        )
        
        # Here you can add processing results to Cloud Storage / Pub/Sub
        # Example: Cloud Storage save
        # storage_client = storage.Client()
        # bucket = storage_client.bucket("your-bucket")
        # blob = bucket.blob(f"meeting-docs/{file_info['id']}.txt")
        # blob.upload_from_string(text)
        
        # Example: Pub/Sub publish
        # publisher = pubsub_v1.PublisherClient()
        # topic_path = publisher.topic_path("your-project", "meeting-docs")
        # message_data = json.dumps({
        #     "file_id": file_info["id"],
        #     "file_name": file_info["name"],
        #     "user": user,
        #     "text_content": text,
        #     "modified_time": file_info["modifiedTime"]
        # })
        # publisher.publish(topic_path, message_data.encode("utf-8"))
        
        return True
    except Exception as e:
        logging.error(f"Error processing document {file_info['id']}: {e}")
        return False

@app.route("/", methods=["POST"])
def drive_webhook():
    """Handle Drive webhook notifications"""
    # Ignore initial sync notification
    if request.headers.get("X-Goog-Resource-State") == "sync":
        logging.info("Ignoring sync notification")
        return ("", 204)

    # Get user info and folder ID from channel token
    try:
        payload = json.loads(request.headers.get("X-Goog-Channel-Token", "{}"))
        user = payload["user"]
        folder_id = payload["folder"]
        logging.info(f"Processing webhook for user: {user}, folder: {folder_id}")
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Invalid channel token: {e}")
        return ("", 400)

    # Get pageToken
    page_token = load_token(user)
    if not page_token:
        logging.warning(f"No pageToken for {user} – resync needed")
        return ("", 204)

    # Create Drive service
    try:
        drv = drive_service(user)
    except Exception as e:
        logging.error(f"Failed to create Drive service for {user}: {e}")
        return ("", 500)

    # Get changes using changes.list
    while page_token:
        try:
            resp = drv.changes().list(
                pageToken=page_token,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields=(
                    "nextPageToken,newStartPageToken,"
                    "changes(file(id,name,mimeType,parents,modifiedTime))"
                ),
            ).execute()

            # Check changed files
            for change in resp.get("changes", []):
                file_info = change.get("file")
                if not file_info:  # deleted files etc.
                    continue
                    
                # Check if file is in target folder
                if folder_id not in file_info.get("parents", []):
                    continue
                    
                # Check if it's a Google Document
                if file_info["mimeType"] != "application/vnd.google-apps.document":
                    continue

                # Process the document
                process_document(drv, file_info, user)

            # Process next page token
            page_token = resp.get("nextPageToken")
            if not page_token:
                # Save new startPageToken
                new_start_token = resp.get("newStartPageToken")
                if new_start_token:
                    save_token(user, new_start_token)

        except Exception as e:
            logging.error(f"Error processing changes for {user}: {e}")
            break

    return ("", 204)

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}, 200

if __name__ == "__main__":
    # For local development
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))