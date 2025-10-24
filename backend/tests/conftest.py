"""
Pytest configuration and shared fixtures for auto-processing tests
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from app.infrastructure.config.settings import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    settings = Mock()
    settings.autoproc_parallel_workers = 5
    settings.autoproc_batch_size = 10
    settings.autoproc_max_items = 20
    settings.autoproc_success_rate_threshold = 0.9
    settings.autoproc_queue_alert_threshold = 50
    settings.autoproc_error_rate_threshold = 0.05
    settings.candidate_title_regex = None
    settings.autoproc_gemini_model_small_threshold = 5000
    settings.autoproc_gemini_model_large_threshold = 15000
    return settings


@pytest.fixture
def sample_meeting_data():
    """Sample meeting data for testing"""
    return {
        "id": "meeting-123",
        "doc_id": "doc-abc-123",
        "title": "初回面談 - 田中太郎さん",
        "meeting_datetime": "2024-01-15T10:00:00Z",
        "organizer_email": "agent@bandq.jp",
        "organizer_name": "エージェント田中",
        "document_url": "https://docs.google.com/document/d/doc-abc-123",
        "text_content": "本日は初回面談にお越しいただき、ありがとうございます。田中太郎さんのご経歴について...",
        "created_at": "2024-01-15T09:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }


@pytest.fixture
def sample_zoho_match():
    """Sample Zoho match data for testing"""
    return {
        "record_id": "zoho-record-456",
        "candidate_id": "candidate-789",
        "candidate_name": "田中太郎",
        "candidate_email": "tanaka@example.com"
    }


@pytest.fixture
def sample_processing_candidates():
    """Sample processing candidates for testing"""
    from app.application.use_cases.auto_process_meetings import ProcessingCandidate
    
    candidates = []
    for i in range(5):
        candidates.append(ProcessingCandidate(
            meeting_id=f"meeting-{i+1}",
            title=f"初回面談 - テスト候補者{i+1}",
            candidate_name=f"テスト候補者{i+1}",
            zoho_match={
                "record_id": f"zoho-{i+1}",
                "candidate_id": f"candidate-{i+1}",
                "candidate_name": f"テスト候補者{i+1}"
            },
            priority_score=10.0 + i,
            text_length=5000 + i * 1000,
            created_at="2024-01-15T10:00:00Z",
            meeting_data={
                "id": f"meeting-{i+1}",
                "title": f"初回面談 - テスト候補者{i+1}",
                "text_content": "A" * (5000 + i * 1000),
                "created_at": "2024-01-15T10:00:00Z",
                "organizer_name": "テストエージェント"
            }
        ))
    return candidates


@pytest.fixture
def mock_meeting_repository():
    """Mock meeting repository"""
    repo = Mock()
    
    # Mock list_meetings_paginated
    repo.list_meetings_paginated.return_value = {
        "items": [],
        "has_next": False
    }
    
    # Mock get_meeting
    repo.get_meeting.return_value = None
    repo.get_meeting_core.return_value = None
    
    return repo


@pytest.fixture
def mock_zoho_client():
    """Mock Zoho client"""
    client = Mock()
    
    # Mock search methods
    client.search_app_hc_by_exact_name.return_value = []
    
    return client


@pytest.fixture
def mock_candidate_title_matcher():
    """Mock candidate title matcher"""
    matcher = Mock()
    
    # Mock extraction methods
    matcher.extract_from_title.return_value = "テスト候補者"
    matcher.is_exact_match.return_value = True
    
    return matcher


@pytest.fixture
def mock_process_structured_use_case():
    """Mock ProcessStructuredDataUseCase"""
    use_case = Mock()
    
    # Mock execute method
    use_case.execute.return_value = {
        "meeting_id": "meeting-123",
        "data": {"test": "data"},
        "zoho_write_result": {"status": "success"}
    }
    
    return use_case


@pytest.fixture
def mock_job_tracker():
    """Mock JobTracker"""
    tracker = Mock()
    
    # Mock methods
    tracker.create_job.return_value = "job-123"
    tracker.mark_running.return_value = None
    tracker.update.return_value = None
    tracker.mark_success.return_value = None
    tracker.mark_failed.return_value = None
    
    return tracker


@pytest.fixture
def sample_ai_usage_data():
    """Sample AI usage data for testing"""
    return [
        {
            "id": "usage-1",
            "meeting_id": "meeting-123",
            "group_name": "基本情報",
            "model": "gemini-2.5-pro",
            "prompt_token_count": 1000,
            "candidates_token_count": 500,
            "total_token_count": 1500,
            "finish_reason": "STOP",
            "response_chars": 800,
            "latency_ms": 2500,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "usage-2",
            "meeting_id": "meeting-456",
            "group_name": "転職活動状況",
            "model": "gemini-2.5-flash",
            "prompt_token_count": 800,
            "candidates_token_count": 300,
            "total_token_count": 1100,
            "finish_reason": "STOP",
            "response_chars": 600,
            "latency_ms": 1800,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]


@pytest.fixture
def mock_ai_usage_repository():
    """Mock AI usage repository"""
    repo = Mock()
    
    # Mock get_usage_summary
    repo.get_usage_summary.return_value = []
    
    return repo


class AsyncIterator:
    """Helper class for async iteration in tests"""
    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


def create_async_mock(*args, **kwargs):
    """Helper to create async mock functions"""
    mock = AsyncMock(*args, **kwargs)
    return mock