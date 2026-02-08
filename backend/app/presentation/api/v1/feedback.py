"""
Feedback & Annotation API

Endpoints for collecting, reviewing, and exporting feedback on agent messages.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.infrastructure.chatkit.context import MarketingRequestContext
from app.infrastructure.config.settings import get_settings
from app.infrastructure.security.marketing_token_service import (
    MarketingTokenError,
    MarketingTokenService,
)
from app.infrastructure.supabase.client import get_supabase

router = APIRouter(prefix="/feedback", tags=["feedback"])
logger = logging.getLogger(__name__)


# ============================================================
# Auth (reuse marketing token)
# ============================================================

def _token_service() -> MarketingTokenService:
    settings = get_settings()
    return MarketingTokenService(settings.marketing_chatkit_token_secret)


async def require_feedback_context(
    authorization: Annotated[str | None, Header(convert_underscores=False)] = None,
    marketing_client_secret: Annotated[
        str | None, Header(alias="x-marketing-client-secret", convert_underscores=False)
    ] = None,
) -> MarketingRequestContext:
    token: str | None = None
    if marketing_client_secret:
        token = marketing_client_secret.strip()
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    try:
        claims = _token_service().verify(token)
    except MarketingTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return MarketingRequestContext(
        user_id=claims.sub, user_email=claims.email, user_name=claims.name
    )


# ============================================================
# Schemas
# ============================================================

class FeedbackCreate(BaseModel):
    rating: str | None = Field(None, pattern="^(good|bad)$")
    comment: str | None = None
    correction: str | None = None
    dimension_scores: dict | None = None
    tags: list[str] | None = None


class AnnotationCreate(BaseModel):
    message_id: str
    conversation_id: str
    selector: dict
    comment: str | None = None
    tags: list[str] | None = None
    severity: str = Field("info", pattern="^(critical|major|minor|info|positive)$")
    correction: str | None = None
    content_hash: str | None = None


class AnnotationUpdate(BaseModel):
    comment: str | None = None
    tags: list[str] | None = None
    severity: str | None = None
    correction: str | None = None


class ReviewUpdate(BaseModel):
    review_status: str = Field(..., pattern="^(new|reviewed|actioned|dismissed)$")
    review_notes: str | None = None


# ============================================================
# Helper
# ============================================================

def _content_hash(content: str | dict | None) -> str:
    raw = json.dumps(content, sort_keys=True, ensure_ascii=False) if isinstance(content, dict) else (content or "")
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _ensure_shared(sb, conversation_id: str, ctx: MarketingRequestContext) -> None:
    """Auto-enable sharing on conversations that receive feedback."""
    try:
        conv = (
            sb.table("marketing_conversations")
            .select("is_shared")
            .eq("id", conversation_id)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if conv.data and not conv.data.get("is_shared"):
            sb.table("marketing_conversations").update({
                "is_shared": True,
                "shared_at": datetime.now(timezone.utc).isoformat(),
                "shared_by_email": ctx.user_email,
                "shared_by_clerk_id": ctx.user_id,
            }).eq("id", conversation_id).execute()
            logger.info("Auto-shared conversation %s (feedback by %s)", conversation_id, ctx.user_email)
    except Exception:
        logger.warning("Failed to auto-share conversation %s", conversation_id, exc_info=True)


# ============================================================
# Message Feedback
# ============================================================

@router.post("/messages/{message_id}")
async def upsert_message_feedback(
    message_id: str,
    body: FeedbackCreate,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    sb = get_supabase()
    # fetch message to get conversation_id and content_hash
    msg = sb.table("marketing_messages").select("conversation_id, content").eq("id", message_id).maybe_single().execute()
    if not msg.data:
        raise HTTPException(status_code=404, detail="Message not found")

    row = {
        "message_id": message_id,
        "conversation_id": msg.data["conversation_id"],
        "user_email": ctx.user_email,
        "user_id": ctx.user_id,
        "rating": body.rating,
        "comment": body.comment,
        "correction": body.correction,
        "dimension_scores": body.dimension_scores or {},
        "tags": body.tags or [],
        "content_hash": _content_hash(msg.data.get("content")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    result = (
        sb.table("message_feedback")
        .upsert(row, on_conflict="message_id,user_email")
        .execute()
    )

    # Auto-enable sharing for conversations with feedback
    _ensure_shared(sb, msg.data["conversation_id"], ctx)

    return result.data[0] if result.data else row


@router.get("/messages/{message_id}")
async def get_message_feedback(
    message_id: str,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    sb = get_supabase()
    result = (
        sb.table("message_feedback")
        .select("*")
        .eq("message_id", message_id)
        .execute()
    )
    return result.data


# ============================================================
# Annotations
# ============================================================

@router.post("/annotations")
async def create_annotation(
    body: AnnotationCreate,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    sb = get_supabase()
    row = {
        "message_id": body.message_id,
        "conversation_id": body.conversation_id,
        "user_email": ctx.user_email,
        "user_id": ctx.user_id,
        "selector": body.selector,
        "comment": body.comment,
        "tags": body.tags or [],
        "severity": body.severity,
        "correction": body.correction,
        "content_hash": body.content_hash,
    }
    try:
        result = sb.table("message_annotations").insert(row).execute()
    except Exception as e:
        err_msg = str(e)
        if "23503" in err_msg or "foreign key" in err_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="メッセージがまだ保存されていません。ページを再読み込みしてください。",
            )
        raise

    # Auto-enable sharing for conversations with annotations
    _ensure_shared(sb, body.conversation_id, ctx)

    return result.data[0] if result.data else row


@router.get("/annotations/{message_id}")
async def get_message_annotations(
    message_id: str,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    sb = get_supabase()
    result = (
        sb.table("message_annotations")
        .select("*")
        .eq("message_id", message_id)
        .order("created_at")
        .execute()
    )
    return result.data


@router.put("/annotations/{annotation_id}")
async def update_annotation(
    annotation_id: str,
    body: AnnotationUpdate,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    sb = get_supabase()
    updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if body.comment is not None:
        updates["comment"] = body.comment
    if body.tags is not None:
        updates["tags"] = body.tags
    if body.severity is not None:
        updates["severity"] = body.severity
    if body.correction is not None:
        updates["correction"] = body.correction

    result = (
        sb.table("message_annotations")
        .update(updates)
        .eq("id", annotation_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return result.data[0]


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(
    annotation_id: str,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    sb = get_supabase()
    sb.table("message_annotations").delete().eq("id", annotation_id).execute()
    return {"ok": True}


# ============================================================
# Review
# ============================================================

@router.put("/{feedback_id}/review")
async def update_review_status(
    feedback_id: str,
    body: ReviewUpdate,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    sb = get_supabase()
    updates = {
        "review_status": body.review_status,
        "reviewed_by": ctx.user_email,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.review_notes is not None:
        updates["review_notes"] = body.review_notes

    result = sb.table("message_feedback").update(updates).eq("id", feedback_id).execute()
    if not result.data:
        # try annotations table
        result = sb.table("message_annotations").update(updates).eq("id", feedback_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Not found")
    return result.data[0]


# ============================================================
# Dashboard / List
# ============================================================

@router.get("/overview")
async def get_overview(
    days: int = Query(30, ge=1, le=365),
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    sb = get_supabase()
    all_fb = sb.table("message_feedback").select("id, rating, review_status, tags, created_at").execute()
    rows = all_fb.data or []

    total = len(rows)
    good = sum(1 for r in rows if r.get("rating") == "good")
    bad = sum(1 for r in rows if r.get("rating") == "bad")
    unreviewed = sum(1 for r in rows if r.get("review_status") == "new")

    # tag frequency
    tag_counts: dict[str, int] = {}
    for r in rows:
        for t in (r.get("tags") or []):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:10]

    # daily trend (last N days)
    from collections import defaultdict
    daily: dict[str, dict] = defaultdict(lambda: {"good": 0, "bad": 0, "total": 0})
    for r in rows:
        day = (r.get("created_at") or "")[:10]
        if day:
            daily[day]["total"] += 1
            if r.get("rating") == "good":
                daily[day]["good"] += 1
            elif r.get("rating") == "bad":
                daily[day]["bad"] += 1
    trend = [{"day": k, **v} for k, v in sorted(daily.items(), reverse=True)[:days]]

    return {
        "total": total,
        "good": good,
        "bad": bad,
        "unreviewed": unreviewed,
        "good_pct": round(100 * good / total, 1) if total else 0,
        "bad_pct": round(100 * bad / total, 1) if total else 0,
        "top_tags": [{"tag": t, "count": c} for t, c in top_tags],
        "trend": trend,
    }


@router.get("/list")
async def list_feedback(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    rating: str | None = None,
    review_status: str | None = None,
    tag: str | None = None,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    sb = get_supabase()
    q = sb.table("message_feedback").select(
        "*, marketing_messages!inner(plain_text, role, created_at), marketing_conversations!inner(title)"
    )

    if rating:
        q = q.eq("rating", rating)
    if review_status:
        q = q.eq("review_status", review_status)
    if tag:
        q = q.contains("tags", [tag])

    offset = (page - 1) * per_page
    q = q.order("created_at", desc=True).range(offset, offset + per_page - 1)
    result = q.execute()

    # count
    count_q = sb.table("message_feedback").select("id", count="exact")
    if rating:
        count_q = count_q.eq("rating", rating)
    if review_status:
        count_q = count_q.eq("review_status", review_status)
    if tag:
        count_q = count_q.contains("tags", [tag])
    count_result = count_q.execute()
    total_count = count_result.count if count_result.count is not None else len(result.data or [])

    return {
        "items": result.data or [],
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": (total_count + per_page - 1) // per_page if total_count else 0,
    }


# ============================================================
# Master data
# ============================================================

@router.get("/tags")
async def get_tags(ctx: MarketingRequestContext = Depends(require_feedback_context)):
    sb = get_supabase()
    result = sb.table("feedback_tags").select("*").eq("is_active", True).order("sort_order").execute()
    return result.data


@router.get("/dimensions")
async def get_dimensions(ctx: MarketingRequestContext = Depends(require_feedback_context)):
    sb = get_supabase()
    result = sb.table("feedback_dimensions").select("*").eq("is_active", True).order("sort_order").execute()
    return result.data


# ============================================================
# Export
# ============================================================

def _flatten_activity_items(activity_items: list | None) -> list[dict]:
    """Flatten activity_items into export-friendly rows."""
    if not activity_items:
        return []
    rows = []
    for item in sorted(activity_items, key=lambda x: x.get("sequence", 0)):
        kind = item.get("kind", "")
        base = {"kind": kind, "sequence": item.get("sequence", 0)}

        if kind == "text":
            base["content"] = (item.get("content") or "")[:500]
        elif kind == "tool":
            base["tool_name"] = item.get("name", "")
            base["tool_arguments"] = item.get("arguments", "")
            base["tool_output"] = (item.get("output") or "")[:1000]
        elif kind == "sub_agent":
            base["agent_name"] = item.get("agent", "")
            base["event_type"] = item.get("event_type", "")
            data = item.get("data") or {}
            base["tool_name"] = data.get("tool_name", "")
            base["tool_arguments"] = data.get("arguments", "")
            base["tool_output"] = (data.get("output_preview") or data.get("content") or "")[:1000]
            base["error"] = data.get("error", "")
            # Flatten nested toolCalls if present
            for tc in item.get("toolCalls") or []:
                rows.append({
                    "kind": "sub_agent_tool",
                    "sequence": base["sequence"],
                    "agent_name": base["agent_name"],
                    "tool_name": tc.get("toolName", ""),
                    "tool_arguments": tc.get("arguments", ""),
                    "tool_output": "",
                    "is_complete": tc.get("isComplete", False),
                    "error": tc.get("error", ""),
                })
            if item.get("reasoningContent"):
                rows.append({
                    "kind": "sub_agent_reasoning",
                    "sequence": base["sequence"],
                    "agent_name": base["agent_name"],
                    "content": (item["reasoningContent"] or "")[:500],
                })
        elif kind == "reasoning":
            base["content"] = (item.get("content") or "")[:500]
        elif kind == "chart":
            spec = item.get("spec") or {}
            base["chart_type"] = spec.get("type", "")
            base["chart_title"] = spec.get("title", "")
            base["chart_data_rows"] = len(spec.get("data") or [])
        elif kind == "code_execution":
            base["code"] = (item.get("code") or "")[:1000]
            base["language"] = item.get("language", "")
        elif kind == "code_result":
            base["output"] = (item.get("output") or "")[:1000]
            base["outcome"] = item.get("outcome", "")

        rows.append(base)
    return rows


@router.get("/export")
async def export_feedback(
    format: str = Query("jsonl", pattern="^(jsonl|csv)$"),
    rating: str | None = None,
    review_status: str | None = None,
    tag: str | None = None,
    user_email: str | None = None,
    conversation_id: str | None = None,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    sb = get_supabase()

    # ── Feedback query ──
    fb_q = sb.table("message_feedback").select("*")
    if rating:
        fb_q = fb_q.eq("rating", rating)
    if review_status:
        fb_q = fb_q.eq("review_status", review_status)
    if tag:
        fb_q = fb_q.contains("tags", [tag])
    if user_email:
        fb_q = fb_q.eq("user_email", user_email)
    if conversation_id:
        fb_q = fb_q.eq("conversation_id", conversation_id)
    fb_q = fb_q.order("created_at", desc=True)
    fb_items = (fb_q.execute()).data or []

    # ── Annotations query ──
    ann_q = sb.table("message_annotations").select("*")
    if user_email:
        ann_q = ann_q.eq("user_email", user_email)
    if conversation_id:
        ann_q = ann_q.eq("conversation_id", conversation_id)
    ann_q = ann_q.order("created_at", desc=True)
    all_annotations = (ann_q.execute()).data or []

    # ── Conversation IDs with feedback/annotations ──
    conv_ids = set()
    for r in fb_items:
        conv_ids.add(r["conversation_id"])
    for r in all_annotations:
        conv_ids.add(r["conversation_id"])

    # ── Load full conversation messages with activity_items ──
    conv_meta: dict[str, dict] = {}
    messages_by_conv: dict[str, list] = {}
    for cid in conv_ids:
        # Conversation metadata
        meta_r = (
            sb.table("marketing_conversations")
            .select("id, title, owner_email, created_at, metadata")
            .eq("id", cid)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if meta_r.data:
            conv_meta[cid] = meta_r.data

        # All messages in conversation (full content with activity_items)
        msgs_r = (
            sb.table("marketing_messages")
            .select("id, conversation_id, role, content, plain_text, created_at")
            .eq("conversation_id", cid)
            .order("created_at", desc=False)
            .limit(500)
            .execute()
        )
        messages_by_conv[cid] = msgs_r.data or []

    # ── Group feedback/annotations by message ──
    fb_by_msg: dict[str, list] = {}
    for fb in fb_items:
        fb_by_msg.setdefault(fb["message_id"], []).append(fb)
    ann_by_msg: dict[str, list] = {}
    for ann in all_annotations:
        ann_by_msg.setdefault(ann["message_id"], []).append(ann)

    if format == "jsonl":
        def generate():
            for cid in sorted(conv_ids):
                meta = conv_meta.get(cid, {})
                msgs = messages_by_conv.get(cid, [])

                # 1. Conversation header
                yield json.dumps({
                    "type": "conversation",
                    "conversation_id": cid,
                    "title": meta.get("title", ""),
                    "owner_email": meta.get("owner_email", ""),
                    "created_at": meta.get("created_at", ""),
                }, ensure_ascii=False, default=str) + "\n"

                # 2. All messages with activity_items + attached feedback/annotations
                for msg in msgs:
                    content = msg.get("content") or {}
                    activity_items = content.get("activity_items") or []
                    text = content.get("text") or msg.get("plain_text") or ""

                    row: dict = {
                        "type": "message",
                        "message_id": msg["id"],
                        "conversation_id": cid,
                        "role": msg["role"],
                        "text": text,
                        "created_at": msg.get("created_at", ""),
                        "activity_items": activity_items,
                    }

                    # Attach feedback for this message
                    msg_fb = fb_by_msg.get(msg["id"])
                    if msg_fb:
                        row["feedback"] = [
                            {
                                "id": fb["id"],
                                "user_email": fb.get("user_email"),
                                "rating": fb.get("rating"),
                                "comment": fb.get("comment"),
                                "correction": fb.get("correction"),
                                "tags": fb.get("tags"),
                                "review_status": fb.get("review_status"),
                                "created_at": fb.get("created_at"),
                            }
                            for fb in msg_fb
                        ]

                    # Attach annotations for this message
                    msg_ann = ann_by_msg.get(msg["id"])
                    if msg_ann:
                        row["annotations"] = [
                            {
                                "id": ann["id"],
                                "user_email": ann.get("user_email"),
                                "severity": ann.get("severity"),
                                "comment": ann.get("comment"),
                                "correction": ann.get("correction"),
                                "tags": ann.get("tags"),
                                "selector": ann.get("selector"),
                                "review_status": ann.get("review_status"),
                                "created_at": ann.get("created_at"),
                            }
                            for ann in msg_ann
                        ]

                    yield json.dumps(row, ensure_ascii=False, default=str) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f"attachment; filename=feedback_{datetime.now().strftime('%Y%m%d')}.jsonl"},
        )
    else:
        # CSV: flat rows with type column
        buf = io.StringIO()
        writer = csv.writer(buf)

        writer.writerow([
            "type", "conversation_id", "conversation_title", "message_id",
            "role", "sequence", "kind", "agent_name", "tool_name",
            "tool_arguments", "tool_output", "text_content",
            "rating", "severity", "tags", "comment", "correction",
            "review_status", "user_email", "created_at",
        ])

        for cid in sorted(conv_ids):
            meta = conv_meta.get(cid, {})
            title = meta.get("title", "")
            msgs = messages_by_conv.get(cid, [])

            for msg in msgs:
                mid = msg["id"]
                role = msg["role"]
                content = msg.get("content") or {}
                text = content.get("text") or msg.get("plain_text") or ""
                activity_items = content.get("activity_items") or []
                created_at = msg.get("created_at", "")

                # Message row (text content)
                writer.writerow([
                    "message", cid, title, mid,
                    role, "", "", "", "",
                    "", "", text[:500],
                    "", "", "", "", "",
                    "", "", created_at,
                ])

                # Activity item rows (tools, sub-agents, reasoning, charts, code)
                for ai in _flatten_activity_items(activity_items):
                    kind = ai.get("kind", "")
                    writer.writerow([
                        f"activity:{kind}", cid, title, mid,
                        role, ai.get("sequence", ""), kind,
                        ai.get("agent_name", ""), ai.get("tool_name", ""),
                        (ai.get("tool_arguments") or "")[:500],
                        (ai.get("tool_output") or ai.get("output") or "")[:500],
                        (ai.get("content") or ai.get("code") or "")[:500],
                        "", "", "", "", "",
                        "", "", created_at,
                    ])

                # Feedback rows for this message
                for fb in fb_by_msg.get(mid, []):
                    writer.writerow([
                        "feedback", cid, title, mid,
                        "", "", "", "", "",
                        "", "", "",
                        fb.get("rating", ""), "",
                        ", ".join(fb.get("tags") or []),
                        fb.get("comment", ""), fb.get("correction", ""),
                        fb.get("review_status", ""), fb.get("user_email", ""),
                        fb.get("created_at", ""),
                    ])

                # Annotation rows for this message
                for ann in ann_by_msg.get(mid, []):
                    sel = ann.get("selector") or {}
                    quote = sel.get("quote", {}).get("exact", "")[:200] if isinstance(sel, dict) else ""
                    writer.writerow([
                        "annotation", cid, title, mid,
                        "", "", "", "", "",
                        "", "", quote,
                        "", ann.get("severity", ""),
                        ", ".join(ann.get("tags") or []),
                        ann.get("comment", ""), ann.get("correction", ""),
                        ann.get("review_status", ""), ann.get("user_email", ""),
                        ann.get("created_at", ""),
                    ])

        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=feedback_{datetime.now().strftime('%Y%m%d')}.csv"},
        )


# ============================================================
# Conversations list (for feedback review dashboard)
# ============================================================

@router.get("/conversations")
async def list_conversations_with_feedback(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    rating: str | None = None,
    user_email: str | None = None,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    """List conversations that have feedback, with summary stats."""
    sb = get_supabase()

    # 1. Get conversation IDs that have feedback (with optional filters)
    fb_q = sb.table("message_feedback").select("conversation_id, rating, review_status, user_email, created_at")
    if rating:
        fb_q = fb_q.eq("rating", rating)
    if user_email:
        fb_q = fb_q.eq("user_email", user_email)
    fb_result = fb_q.execute()
    fb_rows = fb_result.data or []

    # 2. Get conversations that have annotations
    ann_q = sb.table("message_annotations").select("conversation_id, severity, review_status, user_email, created_at")
    if user_email:
        ann_q = ann_q.eq("user_email", user_email)
    ann_result = ann_q.execute()
    ann_rows = ann_result.data or []

    # 3. Aggregate per conversation
    conv_ids: set[str] = set()
    conv_stats: dict[str, dict] = {}

    for r in fb_rows:
        cid = r["conversation_id"]
        conv_ids.add(cid)
        if cid not in conv_stats:
            conv_stats[cid] = {
                "total_feedback": 0, "good_count": 0, "bad_count": 0,
                "unreviewed_count": 0, "annotation_count": 0,
                "unique_users": set(), "latest_at": "",
            }
        s = conv_stats[cid]
        s["total_feedback"] += 1
        if r.get("rating") == "good":
            s["good_count"] += 1
        elif r.get("rating") == "bad":
            s["bad_count"] += 1
        if r.get("review_status") == "new":
            s["unreviewed_count"] += 1
        s["unique_users"].add(r.get("user_email", ""))
        ts = r.get("created_at", "")
        if ts > s["latest_at"]:
            s["latest_at"] = ts

    for r in ann_rows:
        cid = r["conversation_id"]
        conv_ids.add(cid)
        if cid not in conv_stats:
            conv_stats[cid] = {
                "total_feedback": 0, "good_count": 0, "bad_count": 0,
                "unreviewed_count": 0, "annotation_count": 0,
                "unique_users": set(), "latest_at": "",
            }
        s = conv_stats[cid]
        s["annotation_count"] += 1
        if r.get("review_status") == "new":
            s["unreviewed_count"] += 1
        s["unique_users"].add(r.get("user_email", ""))
        ts = r.get("created_at", "")
        if ts > s["latest_at"]:
            s["latest_at"] = ts

    if not conv_ids:
        return {"items": [], "total": 0, "page": page, "per_page": per_page, "total_pages": 0}

    # 4. Sort by latest_at descending
    sorted_ids = sorted(conv_ids, key=lambda cid: conv_stats[cid]["latest_at"], reverse=True)
    total_count = len(sorted_ids)
    total_pages = (total_count + per_page - 1) // per_page
    offset = (page - 1) * per_page
    page_ids = sorted_ids[offset:offset + per_page]

    # 5. Fetch conversation metadata
    conv_meta: dict[str, dict] = {}
    if page_ids:
        for batch_start in range(0, len(page_ids), 50):
            batch = page_ids[batch_start:batch_start + 50]
            meta_result = (
                sb.table("marketing_conversations")
                .select("id, title, owner_email, created_at")
                .in_("id", batch)
                .execute()
            )
            for m in meta_result.data or []:
                conv_meta[m["id"]] = m

    # 6. Build response
    items = []
    for cid in page_ids:
        s = conv_stats[cid]
        meta = conv_meta.get(cid, {})
        items.append({
            "conversation_id": cid,
            "title": meta.get("title", ""),
            "owner_email": meta.get("owner_email", ""),
            "created_at": meta.get("created_at", ""),
            "total_feedback": s["total_feedback"],
            "good_count": s["good_count"],
            "bad_count": s["bad_count"],
            "annotation_count": s["annotation_count"],
            "unreviewed_count": s["unreviewed_count"],
            "unique_users": len(s["unique_users"] - {""}),
            "latest_feedback_at": s["latest_at"],
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.get("/conversations/{conversation_id}/users")
async def get_conversation_feedback_users(
    conversation_id: str,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    """Get unique users who gave feedback/annotations on a conversation."""
    sb = get_supabase()
    fb = sb.table("message_feedback").select("user_email").eq("conversation_id", conversation_id).execute()
    ann = sb.table("message_annotations").select("user_email").eq("conversation_id", conversation_id).execute()
    users = set()
    for r in (fb.data or []):
        if r.get("user_email"):
            users.add(r["user_email"])
    for r in (ann.data or []):
        if r.get("user_email"):
            users.add(r["user_email"])
    return sorted(users)


# ============================================================
# Conversation feedback detail (for chat page & review page)
# ============================================================

@router.get("/conversation/{conversation_id}")
async def get_conversation_feedback(
    conversation_id: str,
    user_email: str | None = None,
    ctx: MarketingRequestContext = Depends(require_feedback_context),
):
    sb = get_supabase()
    fb_q = sb.table("message_feedback").select("*").eq("conversation_id", conversation_id)
    ann_q = sb.table("message_annotations").select("*").eq("conversation_id", conversation_id)
    if user_email:
        fb_q = fb_q.eq("user_email", user_email)
        ann_q = ann_q.eq("user_email", user_email)
    fb = fb_q.order("created_at").execute()
    ann = ann_q.order("created_at").execute()
    return {
        "feedback": fb.data or [],
        "annotations": ann.data or [],
    }
