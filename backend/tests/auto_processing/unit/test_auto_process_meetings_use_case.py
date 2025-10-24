"""
Unit tests for AutoProcessMeetingsUseCase
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from concurrent.futures import Future

from app.application.use_cases.auto_process_meetings import AutoProcessMeetingsUseCase, ProcessingCandidate, ProcessingResult


class TestAutoProcessMeetingsUseCase:
    """Test cases for AutoProcessMeetingsUseCase"""
    
    @pytest.fixture
    def use_case(self):
        """Create use case instance for testing"""
        return AutoProcessMeetingsUseCase()
    
    @pytest.fixture
    def mock_dependencies(self, mock_settings, mock_meeting_repository, mock_zoho_client, 
                         mock_candidate_title_matcher, mock_process_structured_use_case, mock_job_tracker):
        """Mock all dependencies"""
        with patch('app.application.use_cases.auto_process_meetings.get_settings', return_value=mock_settings), \
             patch('app.application.use_cases.auto_process_meetings.MeetingRepositoryImpl', return_value=mock_meeting_repository), \
             patch('app.application.use_cases.auto_process_meetings.ZohoClient', return_value=mock_zoho_client), \
             patch('app.application.use_cases.auto_process_meetings.CandidateTitleMatcher', return_value=mock_candidate_title_matcher), \
             patch('app.application.use_cases.auto_process_meetings.ProcessStructuredDataUseCase', return_value=mock_process_structured_use_case), \
             patch('app.application.use_cases.auto_process_meetings.JobTracker', mock_job_tracker):
            yield {
                'settings': mock_settings,
                'meeting_repo': mock_meeting_repository,
                'zoho_client': mock_zoho_client,
                'title_matcher': mock_candidate_title_matcher,
                'process_use_case': mock_process_structured_use_case,
                'job_tracker': mock_job_tracker
            }

    @pytest.mark.asyncio
    async def test_execute_basic_flow(self, use_case, mock_dependencies):
        """Test basic execution flow"""
        # Setup
        deps = mock_dependencies
        
        # Mock collect_processing_candidates to return empty list
        with patch.object(use_case, '_collect_processing_candidates', return_value=[]):
            result = await use_case.execute(
                accounts=["test@example.com"],
                max_items=5,
                dry_run=True
            )
        
        # Assertions
        assert result is not None
        assert "total_candidates" in result
        assert "processed" in result
        assert "execution_time_seconds" in result
        assert result["dry_run"] is True
        assert result["max_items"] == 5

    @pytest.mark.asyncio
    async def test_execute_with_candidates(self, use_case, mock_dependencies, sample_processing_candidates):
        """Test execution with actual candidates"""
        deps = mock_dependencies
        
        # Mock collect_processing_candidates to return sample candidates
        with patch.object(use_case, '_collect_processing_candidates', return_value=sample_processing_candidates[:3]):
            result = await use_case.execute(
                accounts=["test@example.com"],
                max_items=10,
                dry_run=True
            )
        
        # Assertions
        assert result["processed"] == 3
        assert len(result["results"]) == 3
        assert result["dry_run"] is True
        
        # Check result structure
        for result_item in result["results"]:
            assert "meeting_id" in result_item
            assert "candidate_name" in result_item
            assert "status" in result_item
            assert result_item["status"] == "would_process"

    @pytest.mark.asyncio
    async def test_execute_with_parallel_processing(self, use_case, mock_dependencies, sample_processing_candidates):
        """Test execution with parallel processing (not dry run)"""
        deps = mock_dependencies
        
        # Mock process_candidates_parallel
        mock_results = [
            ProcessingResult(
                meeting_id="meeting-1",
                title="初回面談 - テスト候補者1",
                candidate_name="テスト候補者1",
                zoho_record_id="zoho-1",
                status="success",
                processing_time=2.5
            )
        ]
        
        with patch.object(use_case, '_collect_processing_candidates', return_value=sample_processing_candidates[:1]), \
             patch.object(use_case, '_process_candidates_parallel', return_value=(1, 0, mock_results)):
            
            result = await use_case.execute(
                accounts=["test@example.com"],
                max_items=5,
                dry_run=False,
                parallel_workers=3,
                batch_size=5
            )
        
        # Assertions
        assert result["processed"] == 1
        assert result["errors"] == 0
        assert result["dry_run"] is False
        assert result["parallel_workers"] == 3
        assert result["batch_size"] == 5
        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "success"

    def test_calculate_priority_score(self, use_case):
        """Test priority score calculation"""
        meeting_data = {
            "title": "初回面談 - 田中太郎さん",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "text_content": "A" * 10000  # 10k characters
        }
        
        score = use_case._calculate_priority_score(meeting_data, "田中太郎")
        
        # Should have base score (10) + recent bonus (~5) + text length bonus (3) + name occurrence bonus
        assert score >= 15.0
        assert score <= 20.0

    def test_calculate_priority_score_no_first_meeting(self, use_case):
        """Test priority score for non-first meeting"""
        meeting_data = {
            "title": "二回目面談 - 田中太郎さん",  # No "初回"
            "created_at": datetime.now(timezone.utc).isoformat(),
            "text_content": "A" * 5000
        }
        
        score = use_case._calculate_priority_score(meeting_data, "田中太郎")
        
        # Should not have base "初回" bonus
        assert score < 10.0

    def test_calculate_priority_score_free_consultation(self, use_case):
        """無料キャリア相談でも優先度ボーナスが付与されること"""
        meeting_data = {
            "title": "無料キャリア相談 - 田中太郎さん",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "text_content": "A" * 8000
        }

        score = use_case._calculate_priority_score(meeting_data, "田中太郎")

        assert score >= 10.0

    def test_calculate_priority_score_old_meeting(self, use_case):
        """Test priority score for old meeting"""
        old_date = datetime.now(timezone.utc).replace(month=1).isoformat()  # Old date
        meeting_data = {
            "title": "初回面談 - 田中太郎さん",
            "created_at": old_date,
            "text_content": "A" * 5000
        }
        
        score = use_case._calculate_priority_score(meeting_data, "田中太郎")
        
        # Should have reduced score due to age
        assert score >= 10.0  # Base score
        assert score <= 15.0  # Reduced due to age

    @pytest.mark.asyncio
    async def test_collect_processing_candidates(self, use_case, mock_dependencies, sample_meeting_data, sample_zoho_match):
        """Test candidate collection logic"""
        deps = mock_dependencies
        
        # Setup mocks
        deps['meeting_repo'].list_meetings_paginated.return_value = {
            "items": [{"id": "meeting-123", "title": "初回面談 - 田中太郎"}],
            "has_next": False
        }
        deps['meeting_repo'].get_meeting_core.return_value = sample_meeting_data
        deps['title_matcher'].extract_from_title.return_value = "田中太郎"
        deps['zoho_client'].search_app_hc_by_exact_name.return_value = [sample_zoho_match]
        deps['title_matcher'].is_exact_match.return_value = True
        
        # Execute
        candidates = await use_case._collect_processing_candidates(
            deps['meeting_repo'], 
            deps['title_matcher'], 
            ["test@example.com"], 
            5, 
            None
        )
        
        # Assertions
        assert len(candidates) == 1
        assert candidates[0].meeting_id == "meeting-123"
        assert candidates[0].candidate_name == "田中太郎"
        assert candidates[0].title == "初回面談 - 田中太郎さん"
        assert candidates[0].priority_score > 0

    @pytest.mark.asyncio
    async def test_collect_processing_candidates_accepts_free_career_consultation(self, use_case, mock_dependencies, sample_meeting_data, sample_zoho_match):
        """Meetings titled with 無料キャリア相談 should also be processed"""
        deps = mock_dependencies

        free_meeting = {**sample_meeting_data, "id": "meeting-free", "title": "無料キャリア相談 - 田中太郎さん"}

        deps['meeting_repo'].list_meetings_paginated.return_value = {
            "items": [{"id": "meeting-free", "title": "無料キャリア相談 - 田中太郎さん"}],
            "has_next": False
        }
        deps['meeting_repo'].get_meeting_core.return_value = free_meeting
        deps['title_matcher'].extract_from_title.return_value = "田中太郎"
        deps['zoho_client'].search_app_hc_by_exact_name.return_value = [sample_zoho_match]
        deps['title_matcher'].is_exact_match.return_value = True

        candidates = await use_case._collect_processing_candidates(
            deps['meeting_repo'],
            deps['title_matcher'],
            ["test@example.com"],
            5,
            None
        )

        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.meeting_id == "meeting-free"
        assert "無料キャリア相談" in candidate.title

    @pytest.mark.asyncio
    async def test_collect_processing_candidates_filtering(self, use_case, mock_dependencies, sample_meeting_data):
        """Test candidate collection with filtering"""
        deps = mock_dependencies
        
        # Setup mock data - one valid, one invalid
        meeting_without_text = {**sample_meeting_data, "text_content": ""}
        meeting_without_first = {**sample_meeting_data, "title": "二回目面談 - 田中太郎さん"}
        
        deps['meeting_repo'].list_meetings_paginated.return_value = {
            "items": [
                {"id": "meeting-1", "title": "初回面談 - 田中太郎"},
                {"id": "meeting-2", "title": "二回目面談 - 田中太郎"}
            ],
            "has_next": False
        }
        
        def get_meeting_side_effect(meeting_id):
            if meeting_id == "meeting-1":
                return sample_meeting_data
            elif meeting_id == "meeting-2":
                return meeting_without_first
            return None
        
        deps['meeting_repo'].get_meeting_core.side_effect = get_meeting_side_effect
        deps['title_matcher'].extract_from_title.return_value = "田中太郎"
        deps['zoho_client'].search_app_hc_by_exact_name.return_value = [{"record_id": "zoho-1", "candidate_name": "田中太郎"}]
        deps['title_matcher'].is_exact_match.return_value = True
        
        # Execute
        candidates = await use_case._collect_processing_candidates(
            deps['meeting_repo'], 
            deps['title_matcher'], 
            None, 
            10, 
            None
        )
        
        # Should only include the meeting with "初回" as a valid candidate
        valid_candidates = [c for c in candidates if isinstance(c, ProcessingCandidate)]
        assert len(valid_candidates) == 1
        assert valid_candidates[0].meeting_id == "meeting-1"

        skip_candidates = [c for c in candidates if hasattr(c, 'skip_reason')]
        assert skip_candidates
        assert all(getattr(c, 'skip_reason', None) == 'not_first' for c in skip_candidates)

    @pytest.mark.asyncio
    async def test_process_candidates_parallel(self, use_case, sample_processing_candidates):
        """Test parallel processing of candidates"""
        candidates = sample_processing_candidates[:3]
        
        # Mock _process_single_candidate to return successful results
        def mock_process_single(candidate):
            return ProcessingResult(
                meeting_id=candidate.meeting_id,
                title=candidate.title,
                candidate_name=candidate.candidate_name,
                zoho_record_id=candidate.zoho_match["record_id"],
                status="success",
                processing_time=1.5
            )
        
        with patch.object(use_case, '_process_single_candidate', side_effect=mock_process_single):
            processed, errors, results = await use_case._process_candidates_parallel(
                candidates, parallel_workers=2, batch_size=5, job_id=None
            )
        
        # Assertions
        assert processed == 3
        assert errors == 0
        assert len(results) == 3
        
        for result in results:
            assert result.status == "success"
            assert result.processing_time == 1.5

    def test_process_single_candidate_success(self, use_case, sample_processing_candidates):
        """Test single candidate processing - success case"""
        candidate = sample_processing_candidates[0]
        
        # Mock ProcessStructuredDataUseCase
        mock_orchestrator = Mock()
        mock_orchestrator.execute.return_value = {
            "meeting_id": candidate.meeting_id,
            "zoho_write_result": {"status": "success"}
        }
        
        with patch('app.application.use_cases.auto_process_meetings.ProcessStructuredDataUseCase', return_value=mock_orchestrator):
            result = use_case._process_single_candidate(candidate)
        
        # Assertions
        assert result.meeting_id == candidate.meeting_id
        assert result.status == "success"
        assert result.processing_time > 0
        assert result.error_message is None

    def test_process_single_candidate_error(self, use_case, sample_processing_candidates):
        """Test single candidate processing - error case"""
        candidate = sample_processing_candidates[0]
        
        # Mock ProcessStructuredDataUseCase to raise exception
        mock_orchestrator = Mock()
        mock_orchestrator.execute.side_effect = Exception("Test error")
        
        with patch('app.application.use_cases.auto_process_meetings.ProcessStructuredDataUseCase', return_value=mock_orchestrator):
            result = use_case._process_single_candidate(candidate)
        
        # Assertions
        assert result.meeting_id == candidate.meeting_id
        assert result.status == "error"
        assert result.error_message == "Test error"
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_execute_with_job_tracking(self, use_case, mock_dependencies):
        """Test execution with job tracking"""
        deps = mock_dependencies
        
        with patch.object(use_case, '_collect_processing_candidates', return_value=[]):
            result = await use_case.execute(
                accounts=["test@example.com"],
                job_id="test-job-123"
            )
        
        # Verify job tracker calls
        deps['job_tracker'].mark_running.assert_called()
        deps['job_tracker'].mark_success.assert_called()

    @pytest.mark.asyncio
    async def test_execute_parameters_validation(self, use_case, mock_dependencies):
        """Test parameter validation and defaults"""
        deps = mock_dependencies
        deps['settings'].autoproc_max_items = 15
        deps['settings'].autoproc_parallel_workers = 3
        deps['settings'].autoproc_batch_size = 8
        
        with patch.object(use_case, '_collect_processing_candidates', return_value=[]):
            result = await use_case.execute()  # No parameters
        
        # Should use defaults from settings
        assert result["max_items"] == 15
        assert result["parallel_workers"] == 3
        assert result["batch_size"] == 8

    @pytest.mark.asyncio
    async def test_execute_override_parameters(self, use_case, mock_dependencies):
        """Test parameter override"""
        deps = mock_dependencies
        
        with patch.object(use_case, '_collect_processing_candidates', return_value=[]):
            result = await use_case.execute(
                max_items=25,
                parallel_workers=7,
                batch_size=12
            )
        
        # Should use overridden values
        assert result["max_items"] == 25
        assert result["parallel_workers"] == 7
        assert result["batch_size"] == 12

    def test_safe_int_helper(self, use_case):
        """Test _safe_int helper method"""
        assert use_case._safe_int(None) == 20
        assert use_case._safe_int("", 10) == 10
        assert use_case._safe_int("15") == 15
        assert use_case._safe_int(25) == 25
        assert use_case._safe_int("invalid", 30) == 30

    @pytest.mark.asyncio
    async def test_performance_metrics_calculation(self, use_case, mock_dependencies, sample_processing_candidates):
        """Test performance metrics are calculated correctly"""
        deps = mock_dependencies
        
        # Mock results with processing times
        mock_results = [
            ProcessingResult(
                meeting_id="meeting-1",
                title="Test",
                candidate_name="Test",
                zoho_record_id="zoho-1",
                status="success",
                processing_time=2.0,
                tokens_used=1500
            ),
            ProcessingResult(
                meeting_id="meeting-2", 
                title="Test2",
                candidate_name="Test2",
                zoho_record_id="zoho-2",
                status="success",
                processing_time=3.0,
                tokens_used=2000
            )
        ]
        
        with patch.object(use_case, '_collect_processing_candidates', return_value=sample_processing_candidates[:2]), \
             patch.object(use_case, '_process_candidates_parallel', return_value=(2, 0, mock_results)):
            
            result = await use_case.execute(dry_run=False)
        
        # Check performance metrics
        assert result["avg_processing_time_seconds"] == 2.5  # (2.0 + 3.0) / 2
        assert result["total_tokens_used"] == 3500  # 1500 + 2000
        assert result["processing_rate"] > 0  # Should be calculated
        assert result["success_rate"] == 1.0  # 2 success, 0 errors
