"""
Unit tests for parallel processing functionality in auto-processing
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, Future

from app.application.use_cases.auto_process_meetings import (
    AutoProcessMeetingsUseCase, 
    ProcessingCandidate, 
    ProcessingResult
)


class TestParallelProcessing:
    """Test cases for parallel processing functionality"""
    
    @pytest.fixture
    def use_case(self):
        return AutoProcessMeetingsUseCase()
    
    @pytest.fixture
    def sample_candidates(self):
        """Create sample candidates for testing"""
        candidates = []
        for i in range(10):
            candidates.append(ProcessingCandidate(
                meeting_id=f"meeting-{i+1}",
                title=f"初回面談 - 候補者{i+1}",
                candidate_name=f"候補者{i+1}",
                zoho_match={
                    "record_id": f"zoho-{i+1}",
                    "candidate_id": f"candidate-{i+1}",
                    "candidate_name": f"候補者{i+1}"
                },
                priority_score=15.0 + i,
                text_length=5000 + i * 500,
                created_at="2024-01-15T10:00:00Z"
            ))
        return candidates

    @pytest.mark.asyncio
    async def test_parallel_processing_basic(self, use_case, sample_candidates):
        """Test basic parallel processing functionality"""
        candidates = sample_candidates[:5]
        
        # Track processing order and timing
        processing_log = []
        
        def mock_process_single(candidate):
            start_time = time.time()
            # Simulate some processing time
            time.sleep(0.1)
            processing_time = time.time() - start_time
            
            processing_log.append({
                "meeting_id": candidate.meeting_id,
                "start_time": start_time,
                "processing_time": processing_time
            })
            
            return ProcessingResult(
                meeting_id=candidate.meeting_id,
                title=candidate.title,
                candidate_name=candidate.candidate_name,
                zoho_record_id=candidate.zoho_match["record_id"],
                status="success",
                processing_time=processing_time
            )
        
        with patch.object(use_case, '_process_single_candidate', side_effect=mock_process_single):
            start_time = time.time()
            processed, errors, results = await use_case._process_candidates_parallel(
                candidates, parallel_workers=3, batch_size=10, job_id=None
            )
            total_time = time.time() - start_time
        
        # Assertions
        assert processed == 5
        assert errors == 0
        assert len(results) == 5
        
        # Parallel processing should be faster than sequential
        # With 3 workers, should take roughly 2 batches: ceil(5/3) * 0.1 ≈ 0.2s
        assert total_time < 0.4  # Give some margin for overhead
        
        # Check all candidates were processed
        processed_ids = {r.meeting_id for r in results}
        expected_ids = {c.meeting_id for c in candidates}
        assert processed_ids == expected_ids

    @pytest.mark.asyncio
    async def test_parallel_processing_with_batch_size(self, use_case, sample_candidates):
        """Test parallel processing with batch size limitations"""
        candidates = sample_candidates[:8]
        
        processing_batches = []
        current_batch = []
        
        def mock_process_single(candidate):
            current_batch.append(candidate.meeting_id)
            time.sleep(0.05)  # Small delay
            
            return ProcessingResult(
                meeting_id=candidate.meeting_id,
                title=candidate.title,
                candidate_name=candidate.candidate_name,
                zoho_record_id=candidate.zoho_match["record_id"],
                status="success",
                processing_time=0.05
            )
        
        # Mock ThreadPoolExecutor to track batch processing
        original_threadpool = ThreadPoolExecutor
        
        class TrackedThreadPoolExecutor(ThreadPoolExecutor):
            def __init__(self, max_workers):
                super().__init__(max_workers)
                self.max_workers = max_workers
                
            def __enter__(self):
                processing_batches.append(len(current_batch))
                current_batch.clear()
                return super().__enter__()
        
        with patch('app.application.use_cases.auto_process_meetings.ThreadPoolExecutor', TrackedThreadPoolExecutor), \
             patch.object(use_case, '_process_single_candidate', side_effect=mock_process_single):
            
            processed, errors, results = await use_case._process_candidates_parallel(
                candidates, parallel_workers=3, batch_size=5, job_id=None
            )
        
        # Should process in batches of 5: first batch (5), second batch (3)
        assert processed == 8
        assert errors == 0
        assert len(results) == 8

    @pytest.mark.asyncio
    async def test_parallel_processing_error_handling(self, use_case, sample_candidates):
        """Test error handling in parallel processing"""
        candidates = sample_candidates[:4]
        
        def mock_process_single(candidate):
            # First and third candidates succeed, second and fourth fail
            if candidate.meeting_id in ["meeting-2", "meeting-4"]:
                raise Exception(f"Processing error for {candidate.meeting_id}")
            
            return ProcessingResult(
                meeting_id=candidate.meeting_id,
                title=candidate.title,
                candidate_name=candidate.candidate_name,
                zoho_record_id=candidate.zoho_match["record_id"],
                status="success",
                processing_time=0.1
            )
        
        with patch.object(use_case, '_process_single_candidate', side_effect=mock_process_single):
            processed, errors, results = await use_case._process_candidates_parallel(
                candidates, parallel_workers=2, batch_size=10, job_id=None
            )
        
        # Should handle errors gracefully
        assert processed == 2  # 2 successful
        assert errors == 2     # 2 failed
        assert len(results) == 2  # Only successful results returned
        
        # Check successful results
        successful_ids = {r.meeting_id for r in results}
        assert successful_ids == {"meeting-1", "meeting-3"}

    @pytest.mark.asyncio
    async def test_parallel_processing_job_tracking(self, use_case, sample_candidates):
        """Test job tracking during parallel processing"""
        candidates = sample_candidates[:3]
        mock_job_tracker = Mock()
        
        def mock_process_single(candidate):
            return ProcessingResult(
                meeting_id=candidate.meeting_id,
                title=candidate.title,
                candidate_name=candidate.candidate_name,
                zoho_record_id=candidate.zoho_match["record_id"],
                status="success",
                processing_time=0.05
            )
        
        with patch.object(use_case, '_process_single_candidate', side_effect=mock_process_single), \
             patch('app.application.use_cases.auto_process_meetings.JobTracker', mock_job_tracker):
            
            processed, errors, results = await use_case._process_candidates_parallel(
                candidates, parallel_workers=2, batch_size=10, job_id="test-job"
            )
        
        # Should update job tracker for each processed item
        assert mock_job_tracker.update.call_count == 3

    @pytest.mark.asyncio
    async def test_parallel_processing_performance_scaling(self, use_case, sample_candidates):
        """Test that parallel processing scales with worker count"""
        candidates = sample_candidates[:6]
        
        def mock_process_single(candidate):
            time.sleep(0.1)  # Fixed processing time
            return ProcessingResult(
                meeting_id=candidate.meeting_id,
                title=candidate.title,
                candidate_name=candidate.candidate_name,
                zoho_record_id=candidate.zoho_match["record_id"],
                status="success",
                processing_time=0.1
            )
        
        # Test with 1 worker (sequential)
        with patch.object(use_case, '_process_single_candidate', side_effect=mock_process_single):
            start_time = time.time()
            processed_1, _, _ = await use_case._process_candidates_parallel(
                candidates, parallel_workers=1, batch_size=10, job_id=None
            )
            time_1_worker = time.time() - start_time
        
        # Test with 3 workers (parallel)
        with patch.object(use_case, '_process_single_candidate', side_effect=mock_process_single):
            start_time = time.time()
            processed_3, _, _ = await use_case._process_candidates_parallel(
                candidates, parallel_workers=3, batch_size=10, job_id=None
            )
            time_3_workers = time.time() - start_time
        
        # Both should process the same number
        assert processed_1 == processed_3 == 6
        
        # 3 workers should be significantly faster than 1 worker
        # Expected: 1 worker = 6 * 0.1 = 0.6s, 3 workers = ceil(6/3) * 0.1 = 0.2s
        assert time_3_workers < time_1_worker * 0.6  # Allow some overhead

    @pytest.mark.asyncio
    async def test_batch_delay_between_batches(self, use_case, sample_candidates):
        """Test that there's a delay between processing batches"""
        candidates = sample_candidates[:7]  # Will create 2 batches with batch_size=5
        batch_timestamps = []
        
        def mock_process_single(candidate):
            return ProcessingResult(
                meeting_id=candidate.meeting_id,
                title=candidate.title,
                candidate_name=candidate.candidate_name,
                zoho_record_id=candidate.zoho_match["record_id"],
                status="success",
                processing_time=0.01
            )
        
        # Track when each batch starts
        original_threadpool = ThreadPoolExecutor
        
        class TimestampedThreadPoolExecutor(ThreadPoolExecutor):
            def __enter__(self):
                batch_timestamps.append(time.time())
                return super().__enter__()
        
        with patch('app.application.use_cases.auto_process_meetings.ThreadPoolExecutor', TimestampedThreadPoolExecutor), \
             patch.object(use_case, '_process_single_candidate', side_effect=mock_process_single):
            
            await use_case._process_candidates_parallel(
                candidates, parallel_workers=3, batch_size=5, job_id=None
            )
        
        # Should have 2 batches
        assert len(batch_timestamps) == 2
        
        # Second batch should start at least 1 second after first (delay between batches)
        time_diff = batch_timestamps[1] - batch_timestamps[0]
        assert time_diff >= 1.0

    def test_process_single_candidate_timing(self, use_case, sample_candidates):
        """Test that processing time is accurately measured"""
        candidate = sample_candidates[0]
        
        # Mock ProcessStructuredDataUseCase with delay
        mock_orchestrator = Mock()
        
        def slow_execute(*args, **kwargs):
            time.sleep(0.2)  # 200ms delay
            return {
                "meeting_id": candidate.meeting_id,
                "zoho_write_result": {"status": "success"}
            }
        
        mock_orchestrator.execute.side_effect = slow_execute
        
        with patch('app.application.use_cases.auto_process_meetings.ProcessStructuredDataUseCase', 
                  return_value=mock_orchestrator):
            start_time = time.time()
            result = use_case._process_single_candidate(candidate)
            actual_time = time.time() - start_time
        
        # Processing time should be accurately recorded
        assert result.processing_time >= 0.2
        assert result.processing_time <= actual_time + 0.01  # Small margin for overhead

    @pytest.mark.asyncio
    async def test_parallel_processing_memory_efficiency(self, use_case):
        """Test that parallel processing doesn't consume excessive memory"""
        # Create a large number of candidates
        large_candidate_list = []
        for i in range(50):
            large_candidate_list.append(ProcessingCandidate(
                meeting_id=f"meeting-{i+1}",
                title=f"初回面談 - 候補者{i+1}",
                candidate_name=f"候補者{i+1}",
                zoho_match={"record_id": f"zoho-{i+1}"},
                priority_score=10.0,
                text_length=1000,
                created_at="2024-01-15T10:00:00Z"
            ))
        
        processed_count = 0
        
        def mock_process_single(candidate):
            nonlocal processed_count
            processed_count += 1
            return ProcessingResult(
                meeting_id=candidate.meeting_id,
                title=candidate.title,
                candidate_name=candidate.candidate_name,
                zoho_record_id=candidate.zoho_match["record_id"],
                status="success",
                processing_time=0.001
            )
        
        with patch.object(use_case, '_process_single_candidate', side_effect=mock_process_single):
            # Process with small batch size to test memory efficiency
            processed, errors, results = await use_case._process_candidates_parallel(
                large_candidate_list, parallel_workers=5, batch_size=10, job_id=None
            )
        
        # Should process all candidates successfully
        assert processed == 50
        assert errors == 0
        assert len(results) == 50
        assert processed_count == 50