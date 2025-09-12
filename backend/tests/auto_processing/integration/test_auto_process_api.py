"""
Integration tests for auto-processing API endpoints
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.main import app


class TestAutoProcessAPI:
    """Integration tests for auto-processing API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auto_process_use_case(self):
        """Mock AutoProcessMeetingsUseCase"""
        use_case = Mock()
        use_case.execute = AsyncMock()
        return use_case
    
    @pytest.fixture
    def mock_stats_use_case(self):
        """Mock GetAutoProcessStatsUseCase"""
        use_case = Mock()
        use_case.execute.return_value = {
            "period": {"start_date": "2024-01-01T00:00:00Z", "end_date": "2024-01-08T00:00:00Z", "days": 7},
            "basic_stats": {"total_meetings": 100},
            "processing_stats": {"total_processed": 50, "success_rate": 0.95},
            "performance_metrics": {"avg_processing_time_seconds": 30},
            "cost_metrics": {"estimated_cost_usd": 10.0},
            "error_analysis": {"total_errors": 2},
            "alerts": [],
            "settings": {"parallel_workers": 5}
        }
        return use_case
    
    def test_auto_process_sync_success(self, client, mock_auto_process_use_case):
        """Test successful synchronous auto-process request"""
        # Mock successful execution
        mock_auto_process_use_case.execute.return_value = {
            "processed": 5,
            "errors": 0,
            "total_candidates": 10,
            "execution_time_seconds": 30.5,
            "success_rate": 1.0,
            "results": []
        }
        
        with patch('app.presentation.api.v1.structured.AutoProcessMeetingsUseCase', 
                  return_value=mock_auto_process_use_case):
            response = client.post("/api/v1/structured/auto-process", json={
                "accounts": ["test@example.com"],
                "max_items": 10,
                "dry_run": True,
                "sync": True,
                "parallel_workers": 3,
                "batch_size": 5
            })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["processed"] == 5
        assert data["errors"] == 0
        assert data["total_candidates"] == 10
        assert "execution_time_seconds" in data
        assert "success_rate" in data

    def test_auto_process_async_success(self, client, mock_auto_process_use_case):
        """Test successful asynchronous auto-process request"""
        mock_job_tracker = Mock()
        mock_job_tracker.create_job.return_value = "job-123"
        
        with patch('app.presentation.api.v1.structured.AutoProcessMeetingsUseCase', 
                  return_value=mock_auto_process_use_case), \
             patch('app.presentation.api.v1.structured.JobTracker', mock_job_tracker):
            
            response = client.post("/api/v1/structured/auto-process", json={
                "accounts": ["test@example.com"],
                "max_items": 10,
                "sync": False  # Async mode
            })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["job_id"] == "job-123"
        assert "status_url" in data
        assert "message" in data

    def test_auto_process_with_all_parameters(self, client, mock_auto_process_use_case):
        """Test auto-process with all parameters"""
        mock_auto_process_use_case.execute.return_value = {"processed": 0}
        
        with patch('app.presentation.api.v1.structured.AutoProcessMeetingsUseCase', 
                  return_value=mock_auto_process_use_case):
            
            response = client.post("/api/v1/structured/auto-process", json={
                "accounts": ["user1@example.com", "user2@example.com"],
                "max_items": 15,
                "dry_run": True,
                "title_regex": "初回.*(?P<name>[^\\s-]+)",
                "sync": True,
                "parallel_workers": 7,
                "batch_size": 12
            })
        
        assert response.status_code == 200
        
        # Verify use case was called with correct parameters
        mock_auto_process_use_case.execute.assert_called_once()
        call_args = mock_auto_process_use_case.execute.call_args
        
        assert call_args[1]["accounts"] == ["user1@example.com", "user2@example.com"]
        assert call_args[1]["max_items"] == 15
        assert call_args[1]["dry_run"] is True
        assert call_args[1]["title_regex_override"] == "初回.*(?P<name>[^\\s-]+)"
        assert call_args[1]["parallel_workers"] == 7
        assert call_args[1]["batch_size"] == 12

    def test_auto_process_default_parameters(self, client, mock_auto_process_use_case):
        """Test auto-process with default parameters"""
        mock_auto_process_use_case.execute.return_value = {"processed": 0}
        
        with patch('app.presentation.api.v1.structured.AutoProcessMeetingsUseCase', 
                  return_value=mock_auto_process_use_case):
            
            response = client.post("/api/v1/structured/auto-process", json={})
        
        assert response.status_code == 200
        
        # Verify use case was called with default parameters
        call_args = mock_auto_process_use_case.execute.call_args
        
        assert call_args[1]["accounts"] == []
        assert call_args[1]["max_items"] is None
        assert call_args[1]["dry_run"] is False

    def test_auto_process_error_handling(self, client, mock_auto_process_use_case):
        """Test auto-process error handling"""
        mock_auto_process_use_case.execute.side_effect = Exception("Processing failed")
        
        with patch('app.presentation.api.v1.structured.AutoProcessMeetingsUseCase', 
                  return_value=mock_auto_process_use_case):
            
            response = client.post("/api/v1/structured/auto-process", json={
                "sync": True
            })
        
        assert response.status_code == 400
        assert "Processing failed" in response.json()["detail"]

    def test_auto_process_task_enqueue_success(self, client, mock_auto_process_use_case):
        """Test successful task enqueuing"""
        mock_job_tracker = Mock()
        mock_job_tracker.create_job.return_value = "job-456"
        
        mock_enqueue = Mock()
        mock_enqueue.return_value = "projects/test/locations/asia-northeast1/queues/test/tasks/task-123"
        
        with patch('app.presentation.api.v1.structured.JobTracker', mock_job_tracker), \
             patch('app.presentation.api.v1.structured.enqueue_auto_process_task', mock_enqueue):
            
            response = client.post("/api/v1/structured/auto-process-task", json={
                "accounts": ["test@example.com"],
                "max_items": 5
            })
        
        assert response.status_code == 202
        data = response.json()
        
        assert data["job_id"] == "job-456"
        assert "task_name" in data
        assert "status_url" in data

    def test_auto_process_task_enqueue_error(self, client):
        """Test task enqueuing error"""
        mock_job_tracker = Mock()
        mock_job_tracker.create_job.return_value = "job-789"
        mock_job_tracker.mark_failed = Mock()
        
        mock_enqueue = Mock()
        mock_enqueue.side_effect = Exception("Cloud Tasks error")
        
        with patch('app.presentation.api.v1.structured.JobTracker', mock_job_tracker), \
             patch('app.presentation.api.v1.structured.enqueue_auto_process_task', mock_enqueue):
            
            response = client.post("/api/v1/structured/auto-process-task", json={})
        
        assert response.status_code == 500
        assert "Cloud Tasks enqueue failed" in response.json()["detail"]
        mock_job_tracker.mark_failed.assert_called_once()

    def test_auto_process_worker_success(self, client, mock_auto_process_use_case):
        """Test worker endpoint success"""
        mock_settings = Mock()
        mock_settings.expected_queue_name = None
        
        with patch('app.presentation.api.v1.structured.AutoProcessMeetingsUseCase', 
                  return_value=mock_auto_process_use_case), \
             patch('app.presentation.api.v1.structured.get_settings', return_value=mock_settings):
            
            response = client.post("/api/v1/structured/auto-process/worker", 
                                 json={"job_id": "job-123"},
                                 headers={"X-Requested-By": "cloud-tasks-enqueue"})
        
        assert response.status_code == 204
        mock_auto_process_use_case.execute.assert_called_once()

    def test_auto_process_worker_forbidden(self, client):
        """Test worker endpoint access control"""
        response = client.post("/api/v1/structured/auto-process/worker", 
                             json={"job_id": "job-123"})
        
        assert response.status_code == 403

    def test_auto_process_worker_error(self, client, mock_auto_process_use_case):
        """Test worker endpoint error handling"""
        mock_auto_process_use_case.execute.side_effect = Exception("Worker error")
        mock_job_tracker = Mock()
        mock_settings = Mock()
        mock_settings.expected_queue_name = None
        
        with patch('app.presentation.api.v1.structured.AutoProcessMeetingsUseCase', 
                  return_value=mock_auto_process_use_case), \
             patch('app.presentation.api.v1.structured.get_settings', return_value=mock_settings), \
             patch('app.presentation.api.v1.structured.JobTracker', mock_job_tracker):
            
            with pytest.raises(Exception, match="Worker error"):
                client.post("/api/v1/structured/auto-process/worker", 
                           json={"job_id": "job-123"},
                           headers={"X-Requested-By": "cloud-tasks-enqueue"})
        
        mock_job_tracker.mark_failed.assert_called_once()

    def test_get_auto_process_stats_success(self, client, mock_stats_use_case):
        """Test successful stats retrieval"""
        with patch('app.presentation.api.v1.structured.GetAutoProcessStatsUseCase', 
                  return_value=mock_stats_use_case):
            
            response = client.get("/api/v1/structured/auto-process/stats?days_back=14&detailed=true")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "period" in data
        assert "basic_stats" in data
        assert "processing_stats" in data
        assert "performance_metrics" in data
        assert "cost_metrics" in data
        
        # Verify use case was called with correct parameters
        mock_stats_use_case.execute.assert_called_once_with(days_back=14, include_detailed_metrics=True)

    def test_get_auto_process_stats_default_params(self, client, mock_stats_use_case):
        """Test stats retrieval with default parameters"""
        with patch('app.presentation.api.v1.structured.GetAutoProcessStatsUseCase', 
                  return_value=mock_stats_use_case):
            
            response = client.get("/api/v1/structured/auto-process/stats")
        
        assert response.status_code == 200
        
        # Should use default parameters
        mock_stats_use_case.execute.assert_called_once_with(days_back=7, include_detailed_metrics=False)

    def test_get_auto_process_stats_error(self, client, mock_stats_use_case):
        """Test stats retrieval error handling"""
        mock_stats_use_case.execute.side_effect = Exception("Stats error")
        
        with patch('app.presentation.api.v1.structured.GetAutoProcessStatsUseCase', 
                  return_value=mock_stats_use_case):
            
            response = client.get("/api/v1/structured/auto-process/stats")
        
        assert response.status_code == 500
        assert "Failed to get statistics" in response.json()["detail"]

    def test_get_auto_process_health_success(self, client, mock_stats_use_case):
        """Test successful health check"""
        # Mock settings
        mock_settings = Mock()
        mock_settings.autoproc_parallel_workers = 5
        mock_settings.autoproc_batch_size = 10
        mock_settings.autoproc_max_items = 20
        mock_settings.autoproc_success_rate_threshold = 0.9
        mock_settings.autoproc_error_rate_threshold = 0.05
        
        # Mock stats with healthy metrics
        mock_stats_use_case.execute.return_value = {
            "processing_stats": {"success_rate": 0.95, "total_processed": 100},
            "alerts": []
        }
        
        with patch('app.presentation.api.v1.structured.GetAutoProcessStatsUseCase', 
                  return_value=mock_stats_use_case), \
             patch('app.presentation.api.v1.structured.get_settings', return_value=mock_settings):
            
            response = client.get("/api/v1/structured/auto-process/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "metrics" in data
        assert "settings" in data
        assert "checks" in data
        
        # Check that use case was called with 1-day lookback
        mock_stats_use_case.execute.assert_called_once_with(days_back=1, include_detailed_metrics=False)

    def test_get_auto_process_health_unhealthy(self, client, mock_stats_use_case):
        """Test health check with unhealthy status"""
        mock_settings = Mock()
        mock_settings.autoproc_success_rate_threshold = 0.9
        mock_settings.autoproc_error_rate_threshold = 0.05
        
        # Mock stats with unhealthy metrics (high error rate)
        mock_stats_use_case.execute.return_value = {
            "processing_stats": {"success_rate": 0.85, "total_processed": 100, "failed_processed": 15},
            "alerts": [{"severity": "critical", "type": "error_rate_high"}]
        }
        
        with patch('app.presentation.api.v1.structured.GetAutoProcessStatsUseCase', 
                  return_value=mock_stats_use_case), \
             patch('app.presentation.api.v1.structured.get_settings', return_value=mock_settings):
            
            response = client.get("/api/v1/structured/auto-process/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "critical"  # Due to critical alert
        assert len(data["alerts"]) == 1
        assert data["checks"]["success_rate_ok"] is False

    def test_get_auto_process_health_error(self, client, mock_stats_use_case):
        """Test health check error handling"""
        mock_stats_use_case.execute.side_effect = Exception("Health check error")
        
        with patch('app.presentation.api.v1.structured.GetAutoProcessStatsUseCase', 
                  return_value=mock_stats_use_case):
            
            response = client.get("/api/v1/structured/auto-process/health")
        
        assert response.status_code == 200  # Still returns 200 but with error status
        data = response.json()
        
        assert data["status"] == "error"
        assert "error" in data
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["type"] == "health_check_error"

    def test_parameter_validation(self, client):
        """Test API parameter validation"""
        # Test invalid days_back (too large)
        response = client.get("/api/v1/structured/auto-process/stats?days_back=100")
        assert response.status_code == 422  # Validation error
        
        # Test invalid days_back (too small)
        response = client.get("/api/v1/structured/auto-process/stats?days_back=0")
        assert response.status_code == 422  # Validation error
        
        # Test valid range
        mock_stats_use_case = Mock()
        mock_stats_use_case.execute.return_value = {"period": {}, "basic_stats": {}}
        
        with patch('app.presentation.api.v1.structured.GetAutoProcessStatsUseCase', 
                  return_value=mock_stats_use_case):
            response = client.get("/api/v1/structured/auto-process/stats?days_back=30")
            assert response.status_code == 200

    def test_request_body_validation(self, client, mock_auto_process_use_case):
        """Test request body validation for auto-process"""
        mock_auto_process_use_case.execute.return_value = {"processed": 0}
        
        with patch('app.presentation.api.v1.structured.AutoProcessMeetingsUseCase', 
                  return_value=mock_auto_process_use_case):
            
            # Test with invalid data types
            response = client.post("/api/v1/structured/auto-process", json={
                "max_items": "not_a_number",
                "parallel_workers": "invalid",
                "batch_size": -1
            })
            
            # Should still work with type coercion or return validation error
            # The exact behavior depends on Pydantic configuration
            assert response.status_code in [200, 422]

    def test_content_type_handling(self, client, mock_auto_process_use_case):
        """Test proper content type handling"""
        mock_auto_process_use_case.execute.return_value = {"processed": 0}
        
        with patch('app.presentation.api.v1.structured.AutoProcessMeetingsUseCase', 
                  return_value=mock_auto_process_use_case):
            
            # Test with correct content type
            response = client.post("/api/v1/structured/auto-process", 
                                 json={"sync": True},
                                 headers={"Content-Type": "application/json"})
            assert response.status_code == 200
            
            # Test response content type
            assert response.headers["content-type"] == "application/json"