from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any

from app.infrastructure.config.settings import get_settings
from app.infrastructure.background.job_tracker import JobTracker
from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl
from app.infrastructure.zoho.client import ZohoClient
from app.domain.services.candidate_title_matcher import CandidateTitleMatcher
from app.application.use_cases.process_structured_data import ProcessStructuredDataUseCase


logger = logging.getLogger(__name__)


class AutoProcessMeetingsUseCase:
    """Auto-process meetings if Docs title strictly matches Zoho candidate name.

    Behavior:
    - Skip items without text_content (no transcription yet).
    - Use a configurable regex to extract candidate name from the title. If not provided, the entire title is used.
    - Search Zoho APP-hc by strict equality. Only proceed when exactly one record matches.
    - For matched records, run ProcessStructuredDataUseCase to extract and write to Zoho.
    - Stop after processing up to max_items.
    """

    async def execute(
        self,
        accounts: Optional[List[str]] = None,
        max_items: Optional[int] = None,
        dry_run: bool = False,
        title_regex_override: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        settings = get_settings()
        max_items = max_items or self._safe_int(settings.autoproc_max_items, default=20)
        title_regex = title_regex_override or settings.candidate_title_regex
        matcher = CandidateTitleMatcher(title_regex)

        logger.info(
            "[auto] start: accounts=%s max_items=%s dry_run=%s title_regex=%s",
            accounts, max_items, dry_run, (title_regex or "<none>")
        )

        repo = MeetingRepositoryImpl()

        processed = 0
        skipped_no_text = 0
        skipped_no_title_match = 0
        skipped_zoho_not_exact = 0
        skipped_not_first = 0
        errors = 0

        # We'll page through unstructured meetings to avoid large queries (prevents 414).
        page = 1
        page_size = 40
        seen_count = 0

        if job_id:
            JobTracker.mark_running(job_id, message="Auto process started")

        results: List[Dict[str, Any]] = []
        zoho = ZohoClient()
        orchestrator = ProcessStructuredDataUseCase()

        while True:
            logger.info("[auto] paging: page=%s page_size=%s structured=false", page, page_size)
            page_result = repo.list_meetings_paginated(
                page=page,
                page_size=page_size,
                accounts=accounts,
                structured=False,  # only unstructured
            )

            items = page_result.get("items", [])
            logger.info("[auto] page loaded: items=%s has_next=%s", len(items), page_result.get("has_next"))
            if not items:
                break
            for item in items:
                if processed >= max_items:
                    break
                try:
                    # Fetch full meeting to check text_content
                    full = repo.get_meeting(str(item.get("id")))
                    if not full or not full.get("text_content"):
                        logger.info("[auto] skip(no_text): id=%s title=%s", item.get("id"), (item.get("title") or ""))
                        skipped_no_text += 1
                        continue

                    title = full.get("title") or item.get("title")
                    # Only process meetings whose title contains "初回"
                    if not title or ("初回" not in title):
                        logger.info("[auto] skip(not_first): id=%s title=%s", item.get("id"), title)
                        skipped_not_first += 1
                        continue
                    extracted = matcher.extract_from_title(title)
                    logger.info("[auto] extracted: id=%s title=%s candidate_extracted=%s", item.get("id"), title, extracted)
                    if not extracted:
                        logger.info("[auto] skip(no_title_match): id=%s title=%s", item.get("id"), title)
                        skipped_no_title_match += 1
                        continue

                    # Strict equality search on Zoho
                    logger.info("[auto] zoho search(exact): name=%s", extracted)
                    matches = zoho.search_app_hc_by_exact_name(extracted, limit=5)
                    logger.info("[auto] zoho search results: count=%s", len(matches))
                    if len(matches) != 1:
                        logger.info("[auto] skip(zoho_not_exact): id=%s reason=count=%s", item.get("id"), len(matches))
                        skipped_zoho_not_exact += 1
                        continue

                    match = matches[0]
                    # Final defensive check: strict match after normalization
                    if not matcher.is_exact_match(extracted, match.get("candidate_name")):
                        logger.info("[auto] skip(zoho_norm_not_equal): id=%s extracted=%s zoho=%s", item.get("id"), extracted, match.get("candidate_name"))
                        skipped_zoho_not_exact += 1
                        continue

                    if dry_run:
                        logger.info("[auto] would_process: id=%s zoho_record=%s name=%s", item.get("id"), match.get("record_id"), match.get("candidate_name"))
                        results.append({
                            "meeting_id": item.get("id"),
                            "title": title,
                            "candidate_name": match.get("candidate_name"),
                            "zoho_record_id": match.get("record_id"),
                            "action": "would_process"
                        })
                        processed += 1
                        continue

                    # Run the main structured processing (extract + save + Zoho write)
                    logger.info("[auto] processing: id=%s zoho_record=%s", item.get("id"), match.get("record_id"))
                    response = orchestrator.execute(
                        meeting_id=str(item.get("id")),
                        zoho_candidate_id=match.get("candidate_id"),
                        zoho_record_id=match.get("record_id"),
                        zoho_candidate_name=match.get("candidate_name"),
                        zoho_candidate_email=None,
                    )
                    logger.info("[auto] processed: id=%s zoho_status=%s", item.get("id"), (response.get("zoho_write_result", {}) if isinstance(response, dict) else {}))

                    results.append({
                        "meeting_id": item.get("id"),
                        "title": title,
                        "candidate_name": match.get("candidate_name"),
                        "zoho_record_id": match.get("record_id"),
                        "status": response.get("zoho_write_result", {}).get("status") if isinstance(response, dict) else "unknown",
                    })
                    processed += 1
                    if job_id:
                        JobTracker.update(job_id, stored=processed)

                except Exception as e:
                    logger.exception("auto-process failed: meeting_id=%s error=%s", item.get("id"), e)
                    errors += 1

            seen_count += len(items)
            if job_id:
                JobTracker.update(job_id, collected=seen_count)
            if processed >= max_items:
                break
            if not page_result.get("has_next"):
                break
            page += 1

        summary = {
            "total_candidates": seen_count,
            "processed": processed,
            "skipped_no_text": skipped_no_text,
            "skipped_no_title_match": skipped_no_title_match,
            "skipped_zoho_not_exact": skipped_zoho_not_exact,
            "skipped_not_first": skipped_not_first,
            "errors": errors,
            "max_items": max_items,
            "dry_run": dry_run,
            "results": results,
        }
        logger.info(
            "[auto] finished: processed=%s skipped={no_text:%s no_title:%s zoho_mismatch:%s not_first:%s} errors=%s",
            processed, skipped_no_text, skipped_no_title_match, skipped_zoho_not_exact, skipped_not_first, errors
        )
        if job_id:
            JobTracker.mark_success(
                job_id,
                message="Auto process finished",
                stored=processed,
                skipped=skipped_no_text + skipped_no_title_match + skipped_zoho_not_exact + skipped_not_first,
                collected=processed + skipped_no_text + skipped_no_title_match + skipped_zoho_not_exact + skipped_not_first,
            )

        return summary

    @staticmethod
    def _safe_int(val: Optional[str | int], default: int = 20) -> int:
        try:
            return int(val) if val is not None else default
        except Exception:
            return default
