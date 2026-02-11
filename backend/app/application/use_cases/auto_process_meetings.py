from __future__ import annotations
import logging
import asyncio
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from app.infrastructure.config.settings import get_settings
from app.infrastructure.background.job_tracker import JobTracker
from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl
from app.infrastructure.zoho.client import ZohoClient
from app.domain.services.candidate_title_matcher import CandidateTitleMatcher
from app.application.use_cases.process_structured_data import ProcessStructuredDataUseCase


logger = logging.getLogger(__name__)

AUTO_PROCESS_KEYWORDS: Tuple[str, ...] = ("初回", "無料キャリア相談")


@dataclass
class ProcessingCandidate:
    """処理対象の会議候補データ"""
    meeting_id: str
    title: str
    candidate_name: str
    zoho_match: Dict[str, Any]
    priority_score: float
    text_length: int
    created_at: str
    meeting_data: Optional[Dict[str, Any]] = None


@dataclass
class ProcessingResult:
    """処理結果データ"""
    meeting_id: str
    title: str
    candidate_name: str
    zoho_record_id: str
    status: str
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    tokens_used: Optional[int] = None


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
        parallel_workers: Optional[int] = None,
        batch_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        settings = get_settings()
        max_items = max_items or self._safe_int(settings.autoproc_max_items, default=20)
        parallel_workers = parallel_workers or settings.autoproc_parallel_workers
        batch_size = batch_size or settings.autoproc_batch_size
        title_regex = title_regex_override or settings.candidate_title_regex
        matcher = CandidateTitleMatcher(title_regex)

        logger.info(
            "[auto] start: accounts=%s max_items=%s parallel_workers=%s batch_size=%s dry_run=%s title_regex=%s",
            accounts, max_items, parallel_workers, batch_size, dry_run, (title_regex or "<none>")
        )

        start_time = time.time()
        repo = MeetingRepositoryImpl()
        
        # Initialize counters
        processed = 0
        skipped_no_text = 0
        skipped_no_title_match = 0
        skipped_zoho_not_exact = 0
        skipped_not_first = 0
        errors = 0
        seen_count = 0

        if job_id:
            JobTracker.mark_running(job_id, message="Auto process started - collecting candidates")

        # Step 1: Collect processing candidates with priority scoring
        logger.info("[auto] collecting candidates...")
        candidates = await self._collect_processing_candidates(
            repo, matcher, accounts, max_items, title_regex
        )
        
        logger.info("[auto] candidates collected: total=%s", len(candidates))
        
        # Update statistics based on candidate collection
        seen_count = len(candidates)
        skipped_no_text = sum(1 for c in candidates if hasattr(c, 'skip_reason') and c.skip_reason == 'no_text')
        skipped_not_first = sum(1 for c in candidates if hasattr(c, 'skip_reason') and c.skip_reason == 'not_first')
        skipped_no_title_match = sum(1 for c in candidates if hasattr(c, 'skip_reason') and c.skip_reason == 'no_title_match')
        skipped_zoho_not_exact = sum(1 for c in candidates if hasattr(c, 'skip_reason') and c.skip_reason == 'zoho_not_exact')
        skipped_already_structured = sum(1 for c in candidates if hasattr(c, 'skip_reason') and c.skip_reason == 'already_structured')
        
        # Filter out skipped candidates to get actual processing candidates
        valid_candidates = [c for c in candidates if isinstance(c, ProcessingCandidate)]
        approx_text_chars = sum(c.text_length for c in valid_candidates)
        logger.info("[auto] valid candidates for processing: %s", len(valid_candidates))

        if job_id:
            JobTracker.update(job_id, collected=seen_count, message="Starting parallel processing")

        results: List[ProcessingResult] = []

        # Step 2: Process candidates in parallel batches
        if valid_candidates and not dry_run:
            logger.info("[auto] starting parallel processing with %s workers", parallel_workers)
            processed, errors, batch_results = await self._process_candidates_parallel(
                valid_candidates, parallel_workers, batch_size, job_id
            )
            results.extend(batch_results)
        elif valid_candidates and dry_run:
            # Dry run mode - just create mock results
            logger.info("[auto] dry run mode - creating mock results")
            for candidate in valid_candidates[:max_items]:
                results.append(ProcessingResult(
                    meeting_id=candidate.meeting_id,
                    title=candidate.title,
                    candidate_name=candidate.candidate_name,
                    zoho_record_id=candidate.zoho_match.get("record_id", ""),
                    status="would_process"
                ))
            processed = len(results)

        # Calculate execution time and performance metrics
        execution_time = time.time() - start_time
        avg_processing_time = sum(r.processing_time or 0 for r in results) / max(len(results), 1)
        total_tokens = sum(r.tokens_used or 0 for r in results)
        
        # Create enhanced summary with performance metrics
        summary = {
            "total_candidates": seen_count,
            "processed": processed,
            "skipped_no_text": skipped_no_text,
            "skipped_no_title_match": skipped_no_title_match,
            "skipped_zoho_not_exact": skipped_zoho_not_exact,
            "skipped_not_first": skipped_not_first,
            "skipped_already_structured": skipped_already_structured,
            "errors": errors,
            "max_items": max_items,
            "dry_run": dry_run,
            "parallel_workers": parallel_workers,
            "batch_size": batch_size,
            "execution_time_seconds": round(execution_time, 2),
            "avg_processing_time_seconds": round(avg_processing_time, 2),
            "total_tokens_used": total_tokens,
            "processing_rate": round(processed / max(execution_time, 1), 2),  # items per second
            "success_rate": round(processed / max(processed + errors, 1), 3),
            "approx_text_chars": approx_text_chars,
            "results": [
                {
                    "meeting_id": r.meeting_id,
                    "title": r.title,
                    "candidate_name": r.candidate_name,
                    "zoho_record_id": r.zoho_record_id,
                    "status": r.status,
                    "error_message": r.error_message,
                    "processing_time": r.processing_time,
                    "tokens_used": r.tokens_used
                } for r in results
            ],
        }
        
        logger.info(
            "[auto] finished: processed=%s skipped={no_text:%s no_title:%s zoho_mismatch:%s not_first:%s already_structured:%s} errors=%s execution_time=%.2fs rate=%.2f/s",
            processed, skipped_no_text, skipped_no_title_match, skipped_zoho_not_exact, skipped_not_first, skipped_already_structured, errors, execution_time, summary["processing_rate"]
        )
        
        if job_id:
            JobTracker.mark_success(
                job_id,
                message=f"Auto process finished - {processed} processed in {execution_time:.1f}s",
                stored=processed,
                skipped=skipped_no_text + skipped_no_title_match + skipped_zoho_not_exact + skipped_not_first + skipped_already_structured,
                collected=seen_count,
            )

        return summary

    async def _collect_processing_candidates(
        self,
        repo: MeetingRepositoryImpl,
        matcher: CandidateTitleMatcher,
        accounts: Optional[List[str]],
        max_items: int,
        title_regex: Optional[str]
    ) -> List[ProcessingCandidate]:
        """候補会議を収集し、優先度スコアを計算する"""
        candidates = []
        zoho = ZohoClient()
        
        # Page through meetings to collect candidates
        page = 1
        page_size = 40
        total_seen = 0
        
        # Collect candidates with a reasonable limit to balance thoroughness and performance
        max_pages = min(50, max(10, max_items * 5))  # Scale with max_items but cap at 50 pages
        
        while page <= max_pages:
            logger.info("[auto] collecting page=%s page_size=%s (max_pages=%s)", page, page_size, max_pages)
            
            # Early stopping if we have found plenty of valid candidates
            valid_candidates_so_far = sum(1 for c in candidates if isinstance(c, ProcessingCandidate))
            if valid_candidates_so_far >= max_items * 3:  # 3x buffer for good selection
                logger.info("[auto] early stopping: found %s candidates (target: %s)", valid_candidates_so_far, max_items)
                break
            
            page_result = repo.list_meetings_paginated(
                page=page,
                page_size=page_size,
                accounts=accounts,
                structured=False,  # only unstructured
            )
            
            items = page_result.get("items", [])
            if not items:
                break
                

            for item in items:
                total_seen += 1
                try:
                    meeting_id = str(item.get("id") or "")
                    if not meeting_id:
                        continue

                    title = (item.get("title") or "").strip()

                    if not title or not self._has_auto_process_keyword(title):
                        mock_candidate = type('SkippedCandidate', (), {
                            'skip_reason': 'not_first',
                            'meeting_id': meeting_id,
                            'title': title
                        })()
                        candidates.append(mock_candidate)
                        continue

                    if item.get("is_structured"):
                        mock_candidate = type('SkippedCandidate', (), {
                            'skip_reason': 'already_structured',
                            'meeting_id': meeting_id,
                            'title': title
                        })()
                        candidates.append(mock_candidate)
                        continue

                    # タイトルマッチをtext_content取得の前に実行（不要なDB取得を回避）
                    extracted = matcher.extract_from_title(title)
                    if not extracted:
                        mock_candidate = type('SkippedCandidate', (), {
                            'skip_reason': 'no_title_match',
                            'meeting_id': meeting_id,
                            'title': title
                        })()
                        candidates.append(mock_candidate)
                        continue

                    # Zoho検索: 名前バリエーション（スペース有無等）で複数パターン検索
                    variations = matcher.get_search_variations(extracted)
                    matches = zoho.search_app_hc_by_exact_name(extracted, limit=5, name_variations=variations)

                    if not matches:
                        mock_candidate = type('SkippedCandidate', (), {
                            'skip_reason': 'zoho_not_exact',
                            'meeting_id': meeting_id,
                            'title': title
                        })()
                        candidates.append(mock_candidate)
                        continue

                    # 複数ヒット時: 正規化マッチで絞り込み
                    if len(matches) > 1:
                        verified = [m for m in matches if matcher.is_exact_match(extracted, m.get("candidate_name", ""), pre_extracted=True)]
                        if len(verified) != 1:
                            mock_candidate = type('SkippedCandidate', (), {
                                'skip_reason': 'zoho_not_exact',
                                'meeting_id': meeting_id,
                                'title': title
                            })()
                            candidates.append(mock_candidate)
                            continue
                        match = verified[0]
                    else:
                        match = matches[0]
                        if not matcher.is_exact_match(extracted, match.get("candidate_name", ""), pre_extracted=True):
                            mock_candidate = type('SkippedCandidate', (), {
                                'skip_reason': 'zoho_not_exact',
                                'meeting_id': meeting_id,
                                'title': title
                            })()
                            candidates.append(mock_candidate)
                            continue

                    # Zohoマッチ確定後にのみtext_contentを取得
                    full = repo.get_meeting_core(meeting_id)
                    if not full or not full.get("text_content"):
                        mock_candidate = type('SkippedCandidate', (), {
                            'skip_reason': 'no_text',
                            'meeting_id': meeting_id,
                            'title': title
                        })()
                        candidates.append(mock_candidate)
                        continue

                    priority_score = self._calculate_priority_score(full, extracted)
                    text_len = len(full.get("text_content", ""))

                    candidate = ProcessingCandidate(
                        meeting_id=meeting_id,
                        title=title,
                        candidate_name=extracted,
                        zoho_match=match,
                        priority_score=priority_score,
                        text_length=text_len,
                        created_at=full.get("created_at", ""),
                        meeting_data=full
                    )

                    candidates.append(candidate)
                    logger.debug("[auto] candidate added: id=%s name=%s priority=%.2f",
                                 candidate.meeting_id, candidate.candidate_name, priority_score)

                except Exception as e:
                    logger.warning("[auto] error collecting candidate %s: %s", item.get("id"), e)
                    continue

            if not page_result.get("has_next"):
                break
            page += 1
            
        # Sort only valid ProcessingCandidate objects by priority score (highest first) and limit to max_items
        valid_candidates = [c for c in candidates if isinstance(c, ProcessingCandidate)]
        valid_candidates.sort(key=lambda c: c.priority_score, reverse=True)
        
        # Keep all candidates for statistics but return only max_items valid candidates
        limited_valid_candidates = valid_candidates[:max_items]
        
        # Combine limited valid candidates with all skip candidates for statistics
        skip_candidates = [c for c in candidates if not isinstance(c, ProcessingCandidate)]
        result_candidates = limited_valid_candidates + skip_candidates
        
        logger.info("[auto] candidates collected: total_seen=%s candidates=%s max_items=%s", 
                   total_seen, len(result_candidates), max_items)
        
        return result_candidates
    
    def _calculate_priority_score(self, meeting_data: Dict[str, Any], candidate_name: str) -> float:
        """会議の優先度スコアを計算する"""
        score = 0.0
        
        # Base score for having any auto-process keyword in title
        title = meeting_data.get("title", "")
        if self._has_auto_process_keyword(title):
            score += 10.0
            
        # Boost score based on how recent the meeting is
        created_at = meeting_data.get("created_at", "")
        if created_at:
            try:
                from datetime import datetime, timezone
                created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                days_old = (now - created).days
                # More recent meetings get higher score
                score += max(0, 5.0 - (days_old * 0.1))
            except Exception:
                pass
                
        # Score based on text length (medium length preferred)
        text_length = len(meeting_data.get("text_content", ""))
        if 2000 <= text_length <= 20000:
            score += 3.0
        elif text_length > 20000:
            score += 1.0  # Long documents are still valuable but might be harder to process
            
        # Boost score if candidate name appears multiple times in title
        name_occurrences = title.lower().count(candidate_name.lower())
        score += min(2.0, name_occurrences * 0.5)
        
        return round(score, 2)

    @staticmethod
    def _has_auto_process_keyword(title: Optional[str]) -> bool:
        """Return True when the meeting title contains an auto-process trigger keyword."""
        if not title:
            return False
        return any(keyword in title for keyword in AUTO_PROCESS_KEYWORDS)

    async def _process_candidates_parallel(
        self,
        candidates: List[ProcessingCandidate],
        parallel_workers: int,
        batch_size: int,
        job_id: Optional[str]
    ) -> Tuple[int, int, List[ProcessingResult]]:
        """並列処理で候補を処理する"""
        processed = 0
        errors = 0
        all_results = []
        
        # Process candidates in batches to respect batch_size limit
        for batch_start in range(0, len(candidates), batch_size):
            batch_candidates = candidates[batch_start:batch_start + batch_size]
            batch_num = (batch_start // batch_size) + 1
            
            logger.info("[auto] processing batch %s: candidates=%s workers=%s", 
                       batch_num, len(batch_candidates), parallel_workers)
            
            # Run batch processing in thread pool
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
                # Submit all candidates in current batch
                futures = []
                for candidate in batch_candidates:
                    future = executor.submit(self._process_single_candidate, candidate)
                    futures.append(future)
                
                # Collect results as they complete
                batch_results = []
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result.status == "success":
                            processed += 1
                        elif result.error_message:
                            errors += 1
                        batch_results.append(result)
                        
                        # Update job progress
                        if job_id:
                            JobTracker.update(job_id, stored=processed)
                            
                    except Exception as e:
                        logger.exception("[auto] parallel processing error: %s", e)
                        errors += 1
                
                all_results.extend(batch_results)
                logger.info("[auto] batch %s completed: processed=%s errors=%s", 
                           batch_num, len([r for r in batch_results if r.status == "success"]),
                           len([r for r in batch_results if r.error_message]))
                
                # Small delay between batches to prevent overwhelming APIs
                if batch_start + batch_size < len(candidates):
                    await asyncio.sleep(1)
        
        return processed, errors, all_results

    def _process_single_candidate(self, candidate: ProcessingCandidate) -> ProcessingResult:
        """単一候補の構造化処理を実行する"""
        start_time = time.time()
        
        try:
            logger.info("[auto] processing candidate: id=%s name=%s", 
                       candidate.meeting_id, candidate.candidate_name)
            
            # Run the structured data processing
            orchestrator = ProcessStructuredDataUseCase()
            response = orchestrator.execute(
                meeting_id=candidate.meeting_id,
                zoho_candidate_id=candidate.zoho_match.get("candidate_id"),
                zoho_record_id=candidate.zoho_match.get("record_id"),
                zoho_candidate_name=candidate.candidate_name,
                zoho_candidate_email=candidate.zoho_match.get("candidate_email"),
                meeting_data=candidate.meeting_data,
            )
            
            processing_time = time.time() - start_time
            
            # Extract status and tokens from response
            status = "success"
            tokens_used = None
            
            if isinstance(response, dict):
                zoho_result = response.get("zoho_write_result", {})
                if isinstance(zoho_result, dict):
                    status = zoho_result.get("status", "success")
                # TODO: Extract token usage from AI usage logs if available
                
            logger.info("[auto] candidate processed: id=%s status=%s time=%.2fs", 
                       candidate.meeting_id, status, processing_time)
            
            return ProcessingResult(
                meeting_id=candidate.meeting_id,
                title=candidate.title,
                candidate_name=candidate.candidate_name,
                zoho_record_id=candidate.zoho_match.get("record_id", ""),
                status=status,
                processing_time=processing_time,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error("[auto] candidate processing failed: id=%s error=%s time=%.2fs", 
                        candidate.meeting_id, error_msg, processing_time)
            
            return ProcessingResult(
                meeting_id=candidate.meeting_id,
                title=candidate.title,
                candidate_name=candidate.candidate_name,
                zoho_record_id=candidate.zoho_match.get("record_id", ""),
                status="error",
                error_message=error_msg,
                processing_time=processing_time
            )

    @staticmethod
    def _safe_int(val: Optional[str | int], default: int = 20) -> int:
        try:
            return int(val) if val is not None else default
        except Exception:
            return default
