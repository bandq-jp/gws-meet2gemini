# backend/app/infrastructure/gcp/tasks.py
from __future__ import annotations
from typing import Any, Dict, Optional
import json
from google.cloud import tasks_v2
from google.cloud.tasks_v2.types import HttpMethod
from app.infrastructure.config.settings import get_settings

def enqueue_collect_meetings_task(payload: Dict[str, Any], *, task_name: Optional[str] = None, dispatch_deadline_sec: int = 900) -> str:
    """
    Cloud Tasks に HTTP タスクを作成し、Cloud Run のワーカーURLへPOSTする。
    返り値: 作成したタスク名（フルパス）
    """
    settings = get_settings()
    client = tasks_v2.CloudTasksClient()

    parent = client.queue_path(settings.gcp_project, settings.tasks_location, settings.tasks_queue)

    # HTTP リクエスト設定
    http_request = tasks_v2.HttpRequest(
        http_method=HttpMethod.POST,
        url=settings.tasks_worker_url,
        headers={
            "Content-Type": "application/json",
            # ヘッダでQueue名を伝えておく（ワーカー側でX-Cloud-Tasks-QueueNameが来るが、補助用途）
            "X-Requested-By": "cloud-tasks-enqueue",
        },
        body=json.dumps(payload).encode("utf-8"),
        # OIDC 署名（Cloud Run 側を認証必須にする前提）
        oidc_token=tasks_v2.OidcToken(
            service_account_email=settings.tasks_oidc_service_account,
            audience=settings.tasks_worker_url,  # Cloud Run の Audience はURLでOK
        ),
    )

    task = tasks_v2.Task(http_request=http_request)
    if task_name:
        task.name = client.task_path(settings.gcp_project, settings.tasks_location, settings.tasks_queue, task_name)

    task.dispatch_deadline.seconds = dispatch_deadline_sec  # 最大15分

    created = client.create_task(request={"parent": parent, "task": task})
    return created.name