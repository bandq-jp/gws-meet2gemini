from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query, Body, Request, Response, status
import logging
from datetime import datetime, timezone

from app.application.use_cases.process_structured_data import ProcessStructuredDataUseCase
from app.application.use_cases.extract_structured_data_only import ExtractStructuredDataOnlyUseCase
from app.application.use_cases.sync_structured_data_to_zoho import SyncStructuredDataToZohoUseCase
from app.application.use_cases.get_structured_data import GetStructuredDataUseCase
from app.application.use_cases.get_auto_process_stats import GetAutoProcessStatsUseCase
from app.presentation.schemas.structured import (
    StructuredOut, StructuredProcessRequest,
    ExtractOnlyRequest, ExtractOnlyOut,
    SyncToZohoRequest, SyncToZohoOut
)
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.infrastructure.background.job_tracker import JobTracker
from app.application.use_cases.auto_process_meetings import AutoProcessMeetingsUseCase
from app.infrastructure.gcp.tasks import enqueue_auto_process_task
from app.infrastructure.config.settings import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/process/{meeting_id}", response_model=StructuredOut)
def process_structured(meeting_id: str, request: StructuredProcessRequest):
    try:
        use_case = ProcessStructuredDataUseCase()
        return use_case.execute(
            meeting_id=meeting_id,
            zoho_candidate_id=request.zoho_candidate_id,
            zoho_record_id=request.zoho_record_id,
            zoho_candidate_name=request.zoho_candidate_name,
            zoho_candidate_email=request.zoho_candidate_email,
            custom_schema_id=request.custom_schema_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/extract-only/{meeting_id}", response_model=ExtractOnlyOut)
def extract_structured_only(meeting_id: str, request: ExtractOnlyRequest):
    """構造化出力のみを実行（Zoho書き込みは行わない）"""
    try:
        use_case = ExtractStructuredDataOnlyUseCase()
        return use_case.execute(
            meeting_id=meeting_id,
            custom_schema_id=request.custom_schema_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sync-to-zoho/{meeting_id}", response_model=SyncToZohoOut)
def sync_structured_to_zoho(meeting_id: str, request: SyncToZohoRequest):
    """既存の構造化データをZoho CRMに手動で同期"""
    try:
        use_case = SyncStructuredDataToZohoUseCase()
        return use_case.execute(
            meeting_id=meeting_id,
            zoho_candidate_id=request.zoho_candidate_id,
            zoho_record_id=request.zoho_record_id,
            zoho_candidate_name=request.zoho_candidate_name,
            zoho_candidate_email=request.zoho_candidate_email
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{meeting_id}", response_model=StructuredOut)
async def get_structured(meeting_id: str):
    use_case = GetStructuredDataUseCase()
    return await use_case.execute(meeting_id)


# --- Auto process endpoints ---

class AutoProcessIn(BaseModel):
    accounts: Optional[List[str]] = None
    max_items: Optional[int] = None
    dry_run: bool = False
    title_regex: Optional[str] = None
    sync: bool = False
    parallel_workers: Optional[int] = None
    batch_size: Optional[int] = None


@router.post("/auto-process", response_model=Dict[str, Any])
async def auto_process(
    body: AutoProcessIn = Body(default=AutoProcessIn()),
):
    """Run auto-processing. Use sync=true for inline execution (returns summary)."""
    use_case = AutoProcessMeetingsUseCase()
    try:
        logger.info("[api] auto_process request: sync=%s dry_run=%s max_items=%s parallel_workers=%s batch_size=%s accounts=%s title_regex=%s",
                    body.sync, body.dry_run, body.max_items, body.parallel_workers, body.batch_size, (body.accounts or []), (body.title_regex or "<none>"))
        # Synchronous mode for local testing
        if body.sync:
            summary = await use_case.execute(
                accounts=body.accounts,
                max_items=body.max_items,
                dry_run=body.dry_run,
                title_regex_override=body.title_regex,
                parallel_workers=body.parallel_workers,
                batch_size=body.batch_size,
                job_id=None,
            )
            logger.info("[api] auto_process sync finished: processed=%s errors=%s",
                        summary.get("processed"), summary.get("errors"))
            return summary

        job_id = JobTracker.create_job(
            name="auto_process",
            params=body.model_dump(),
        )
        JobTracker.mark_running(job_id, message="Auto-processing queued")

        import asyncio

        async def _run():
            try:
                logger.info("[api] auto_process background started: job_id=%s", job_id)
                await use_case.execute(
                    accounts=body.accounts,
                    max_items=body.max_items,
                    dry_run=body.dry_run,
                    title_regex_override=body.title_regex,
                    parallel_workers=body.parallel_workers,
                    batch_size=body.batch_size,
                    job_id=job_id,
                )
                logger.info("[api] auto_process background finished: job_id=%s", job_id)
            except Exception as e:
                JobTracker.mark_failed(job_id, error=str(e))
                logger.exception("[api] auto_process background failed: job_id=%s error=%s", job_id, e)

        asyncio.create_task(_run())
        return {
            "message": "Auto-processing started (background).",
            "job_id": job_id,
            "status_url": f"/api/v1/meetings/collect/status/{job_id}",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auto-process-task", response_model=Dict[str, Any], status_code=202)
async def enqueue_auto_process(
    body: AutoProcessIn = Body(default=AutoProcessIn()),
):
    """Enqueue auto-processing to Cloud Tasks and return immediately."""
    job_id = JobTracker.create_job(name="auto_process(tasks)", params=body.model_dump())
    JobTracker.mark_running(job_id, message="Queued to Cloud Tasks")

    payload = {
        "job_id": job_id,
        **body.model_dump(),
    }

    try:
        task_fullname = enqueue_auto_process_task(payload)
    except Exception as e:
        JobTracker.mark_failed(job_id, error=f"enqueue failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cloud Tasks enqueue failed: {e}")

    return {
        "message": "Enqueued to Cloud Tasks.",
        "job_id": job_id,
        "task_name": task_fullname,
        "status_url": f"/api/v1/meetings/collect/status/{job_id}",
    }


class AutoWorkerIn(AutoProcessIn):
    job_id: str


@router.post("/auto-process/worker", status_code=204)
async def auto_process_worker(request: Request, body: AutoWorkerIn = Body(...)):
    """Cloud Tasks worker endpoint for auto-processing."""
    settings = get_settings()

    # Basic verification similar to collect worker
    qhdr = request.headers.get("X-Cloud-Tasks-QueueName")
    if not qhdr and request.headers.get("X-Requested-By") != "cloud-tasks-enqueue":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if settings.expected_queue_name and qhdr and qhdr != settings.expected_queue_name:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid queue")

    use_case = AutoProcessMeetingsUseCase()
    try:
        await use_case.execute(
            accounts=body.accounts,
            max_items=body.max_items,
            dry_run=body.dry_run,
            title_regex_override=body.title_regex,
            parallel_workers=body.parallel_workers,
            batch_size=body.batch_size,
            job_id=body.job_id,
        )
        return Response(status_code=204)
    except Exception as e:
        JobTracker.mark_failed(body.job_id, error=str(e))
        raise


# --- Statistics and monitoring endpoints ---

@router.get("/auto-process/stats", response_model=Dict[str, Any])
async def get_auto_process_stats(
    days_back: int = Query(default=7, ge=1, le=30, description="Number of days to look back for statistics"),
    detailed: bool = Query(default=False, description="Include detailed metrics")
):
    """Get auto-processing statistics and performance metrics."""
    try:
        use_case = GetAutoProcessStatsUseCase()
        stats = use_case.execute(days_back=days_back, include_detailed_metrics=detailed)
        
        logger.info("[api] auto_process stats requested: days_back=%s detailed=%s", days_back, detailed)
        return stats
        
    except Exception as e:
        logger.error("[api] error getting auto_process stats: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/auto-process/health", response_model=Dict[str, Any])
async def get_auto_process_health():
    """Get current health status of auto-processing system."""
    try:
        settings = get_settings()
        use_case = GetAutoProcessStatsUseCase()
        
        # Get recent stats (last 24 hours)
        stats = use_case.execute(days_back=1, include_detailed_metrics=False)
        
        # Extract key health metrics
        processing_stats = stats.get("processing_stats", {})
        alerts = stats.get("alerts", [])
        
        success_rate = processing_stats.get("success_rate", 0.0)
        error_rate = 1.0 - success_rate if success_rate > 0 else 0.0
        
        # Determine overall health status
        health_status = "healthy"
        if error_rate > settings.autoproc_error_rate_threshold:
            health_status = "unhealthy"
        elif success_rate < settings.autoproc_success_rate_threshold:
            health_status = "degraded"
        elif len([a for a in alerts if a.get("severity") == "critical"]) > 0:
            health_status = "critical"
        elif len(alerts) > 0:
            health_status = "warning"
        
        health_data = {
            "status": health_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "success_rate": success_rate,
                "error_rate": error_rate,
                "total_processed_24h": processing_stats.get("total_processed", 0),
                "active_alerts": len(alerts)
            },
            "settings": {
                "parallel_workers": settings.autoproc_parallel_workers,
                "batch_size": settings.autoproc_batch_size,
                "max_items": settings.autoproc_max_items
            },
            "alerts": alerts[:5],  # Only show first 5 alerts
            "checks": {
                "success_rate_ok": success_rate >= settings.autoproc_success_rate_threshold,
                "error_rate_ok": error_rate <= settings.autoproc_error_rate_threshold,
                "no_critical_alerts": len([a for a in alerts if a.get("severity") == "critical"]) == 0
            }
        }
        
        logger.info("[api] auto_process health check: status=%s alerts=%s", health_status, len(alerts))
        return health_data
        
    except Exception as e:
        logger.error("[api] error getting auto_process health: %s", e)
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "metrics": {},
            "alerts": [{"type": "health_check_error", "severity": "error", "message": f"Health check failed: {str(e)}"}]
        }
