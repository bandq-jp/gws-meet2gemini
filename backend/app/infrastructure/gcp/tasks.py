# backend/app/infrastructure/gcp/tasks.py
from __future__ import annotations
from typing import Any, Dict, Optional
import json
from google.cloud import tasks_v2
from google.cloud.tasks_v2.types import HttpMethod
from google.protobuf import duration_pb2
from app.infrastructure.config.settings import get_settings

def enqueue_collect_meetings_task(payload: Dict[str, Any], *, task_name: Optional[str] = None, dispatch_deadline_sec: int = 900) -> str:
    """
    Cloud Tasks に HTTP タスクを作成し、Cloud Run のワーカーURLへPOSTする。
    返り値: 作成したタスク名（フルパス）
    """
    settings = get_settings()
    
    # 必須設定の検証
    if not settings.tasks_autoproc_worker_url:
        raise RuntimeError("TASKS_AUTOPROC_WORKER_URL or TASKS_WORKER_URL is empty")
    if not settings.gcp_project or not settings.tasks_location or not settings.tasks_queue:
        raise RuntimeError("GCP_PROJECT / TASKS_LOCATION / TASKS_QUEUE must be set")
    
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

    # Durationオブジェクトを作成して設定
    deadline = duration_pb2.Duration(seconds=dispatch_deadline_sec)
    task = tasks_v2.Task(
        http_request=http_request,
        dispatch_deadline=deadline,
    )
    if task_name:
        task.name = client.task_path(
            settings.gcp_project, settings.tasks_location, settings.tasks_queue, task_name
        )

    created = client.create_task(request={"parent": parent, "task": task})
    return created.name


def enqueue_auto_process_task(payload: Dict[str, Any], *, task_name: Optional[str] = None, dispatch_deadline_sec: int = 900) -> str:
    """
    Cloud Tasks に自動処理タスクを作成し、Cloud Run のワーカーURLへPOSTする。
    返り値: 作成したタスク名（フルパス）
    """
    settings = get_settings()

    if not settings.tasks_worker_url:
        raise RuntimeError("TASKS_WORKER_URL is empty")
    if not settings.gcp_project or not settings.tasks_location or not settings.tasks_queue:
        raise RuntimeError("GCP_PROJECT / TASKS_LOCATION / TASKS_QUEUE must be set")

    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(settings.gcp_project, settings.tasks_location, settings.tasks_queue)

    # worker URL is the same base; the endpoint path is provided by caller payload and router
    http_request = tasks_v2.HttpRequest(
        http_method=HttpMethod.POST,
        url=settings.tasks_autoproc_worker_url,
        headers={
            "Content-Type": "application/json",
            "X-Requested-By": "cloud-tasks-enqueue",
        },
        body=json.dumps(payload).encode("utf-8"),
        oidc_token=tasks_v2.OidcToken(
            service_account_email=settings.tasks_oidc_service_account,
            audience=settings.tasks_autoproc_worker_url,
        ),
    )

    deadline = duration_pb2.Duration(seconds=dispatch_deadline_sec)
    task = tasks_v2.Task(
        http_request=http_request,
        dispatch_deadline=deadline,
    )
    if task_name:
        task.name = client.task_path(
            settings.gcp_project, settings.tasks_location, settings.tasks_queue, task_name
        )

    created = client.create_task(request={"parent": parent, "task": task})
    return created.name
