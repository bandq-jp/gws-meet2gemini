"""
Unit tests for GetAutoProcessStatsUseCase
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.application.use_cases.get_auto_process_stats import GetAutoProcessStatsUseCase


class TestGetAutoProcessStatsUseCase:
    """Test cases for GetAutoProcessStatsUseCase"""
    
    @pytest.fixture
    def use_case(self):
        """Create use case instance for testing"""
        return GetAutoProcessStatsUseCase()
    
    @pytest.fixture
    def mock_repositories(self, mock_ai_usage_repository):
        """Mock all repository dependencies"""
        meeting_repo = Mock()
        structured_repo = Mock()
        
        return {
            'meeting_repo': meeting_repo,
            'structured_repo': structured_repo,
            'ai_usage_repo': mock_ai_usage_repository
        }
    
    @pytest.fixture
    def mock_dependencies(self, mock_repositories, mock_settings):
        """Mock all dependencies"""
        with patch('app.application.use_cases.get_auto_process_stats.MeetingRepositoryImpl', 
                  return_value=mock_repositories['meeting_repo']), \
             patch('app.application.use_cases.get_auto_process_stats.StructuredRepositoryImpl', 
                  return_value=mock_repositories['structured_repo']), \
             patch('app.application.use_cases.get_auto_process_stats.AiUsageRepositoryImpl', 
                  return_value=mock_repositories['ai_usage_repo']), \
             patch('app.application.use_cases.get_auto_process_stats.get_settings', 
                  return_value=mock_settings):
            yield mock_repositories
    
    def test_execute_basic(self, use_case, mock_dependencies):
        """Test basic stats execution"""
        result = use_case.execute(days_back=7, include_detailed_metrics=False)
        
        # Check basic structure
        assert "period" in result
        assert "basic_stats" in result
        assert "processing_stats" in result
        assert "performance_metrics" in result
        assert "cost_metrics" in result
        assert "error_analysis" in result
        assert "alerts" in result
        assert "settings" in result
        
        # Check period information
        period = result["period"]
        assert period["days"] == 7
        assert "start_date" in period
        assert "end_date" in period

    def test_execute_with_detailed_metrics(self, use_case, mock_dependencies):
        """Test execution with detailed metrics"""
        result = use_case.execute(days_back=7, include_detailed_metrics=True)
        
        # Should include additional detailed metrics
        assert "candidate_name_extraction_stats" in result
        assert "zoho_integration_stats" in result
        assert "gemini_api_stats" in result

    def test_execute_different_time_periods(self, use_case, mock_dependencies):
        """Test execution with different time periods"""
        # Test 1 day
        result_1d = use_case.execute(days_back=1)
        assert result_1d["period"]["days"] == 1
        
        # Test 30 days
        result_30d = use_case.execute(days_back=30)
        assert result_30d["period"]["days"] == 30

    def test_collect_basic_stats(self, use_case, mock_dependencies):
        """Test basic stats collection"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        stats = use_case._collect_basic_stats(start_date, end_date)
        
        # Check structure (currently returns mock data)
        assert "total_meetings" in stats
        assert "unstructured_meetings" in stats
        assert "structured_meetings" in stats
        assert "first_time_meetings" in stats
        assert "zoho_matchable_meetings" in stats

    def test_collect_processing_stats(self, use_case, mock_dependencies):
        """Test processing stats collection"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        stats = use_case._collect_processing_stats(start_date, end_date)
        
        # Check structure
        assert "total_processed" in stats
        assert "successful_processed" in stats
        assert "failed_processed" in stats
        assert "success_rate" in stats
        assert "daily_processing_rate" in stats

    def test_collect_performance_metrics(self, use_case, mock_dependencies):
        """Test performance metrics collection"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        metrics = use_case._collect_performance_metrics(start_date, end_date)
        
        # Check structure
        assert "avg_processing_time_seconds" in metrics
        assert "min_processing_time_seconds" in metrics
        assert "max_processing_time_seconds" in metrics
        assert "avg_items_per_minute" in metrics
        assert "parallel_efficiency" in metrics
        assert "timeout_incidents" in metrics
        assert "retry_incidents" in metrics

    def test_collect_cost_metrics_with_usage_data(self, use_case, mock_dependencies, sample_ai_usage_data):
        """Test cost metrics collection with AI usage data"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        # Mock AI usage data
        mock_dependencies['ai_usage_repo'].get_usage_summary.return_value = sample_ai_usage_data
        
        metrics = use_case._collect_cost_metrics(start_date, end_date)
        
        # Check structure
        assert "total_tokens_used" in metrics
        assert "total_api_calls" in metrics
        assert "estimated_cost_usd" in metrics
        assert "avg_tokens_per_meeting" in metrics
        assert "cost_per_meeting_usd" in metrics
        assert "model_usage_breakdown" in metrics
        assert "daily_cost_trend" in metrics

    def test_get_ai_usage_summary_calculation(self, use_case, mock_dependencies, sample_ai_usage_data):
        """Test AI usage summary calculation"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        # Mock the repository to return sample data
        mock_dependencies['ai_usage_repo'].get_usage_summary.return_value = sample_ai_usage_data
        
        summary = use_case._get_ai_usage_summary(start_date, end_date)
        
        # Check calculations
        expected_total_tokens = 1500 + 1100  # From sample data
        assert summary["total_tokens"] == expected_total_tokens
        assert summary["total_calls"] == 2
        assert summary["estimated_cost"] > 0
        assert summary["avg_tokens_per_meeting"] == expected_total_tokens / 2
        
        # Check model breakdown
        assert "gemini-2.5-pro" in summary["model_breakdown"]
        assert "gemini-2.5-flash" in summary["model_breakdown"]

    def test_get_ai_usage_summary_cost_estimation(self, use_case, mock_dependencies):
        """Test cost estimation for different models"""
        usage_data = [
            {
                "model": "gemini-2.5-pro",
                "total_token_count": 10000
            },
            {
                "model": "gemini-2.5-flash", 
                "total_token_count": 20000
            }
        ]
        
        mock_dependencies['ai_usage_repo'].get_usage_summary.return_value = usage_data
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        summary = use_case._get_ai_usage_summary(start_date, end_date)
        
        # Pro model should be more expensive than Flash
        model_breakdown = summary["model_breakdown"]
        pro_cost_per_token = model_breakdown["gemini-2.5-pro"]["tokens"] * 0.000003
        flash_cost_per_token = model_breakdown["gemini-2.5-flash"]["tokens"] * 0.000001
        
        assert summary["estimated_cost"] == pro_cost_per_token + flash_cost_per_token

    def test_collect_error_analysis(self, use_case, mock_dependencies):
        """Test error analysis collection"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        analysis = use_case._collect_error_analysis(start_date, end_date)
        
        # Check structure
        assert "total_errors" in analysis
        assert "error_rate" in analysis
        assert "error_types" in analysis
        assert "most_common_errors" in analysis
        assert "error_trend" in analysis

    def test_check_alert_conditions_success_rate_low(self, use_case, mock_settings):
        """Test alert for low success rate"""
        mock_settings.autoproc_success_rate_threshold = 0.9
        mock_settings.autoproc_error_rate_threshold = 0.05
        
        processing_stats = {"success_rate": 0.8, "total_processed": 100, "failed_processed": 20}
        performance_metrics = {"avg_processing_time_seconds": 30}
        cost_metrics = {"estimated_cost_usd": 5.0}
        
        alerts = use_case._check_alert_conditions(processing_stats, performance_metrics, cost_metrics)
        
        # Should have success rate alert
        success_rate_alerts = [a for a in alerts if a["type"] == "success_rate_low"]
        assert len(success_rate_alerts) == 1
        assert success_rate_alerts[0]["severity"] == "warning"

    def test_check_alert_conditions_error_rate_high(self, use_case, mock_settings):
        """Test alert for high error rate"""
        mock_settings.autoproc_success_rate_threshold = 0.9
        mock_settings.autoproc_error_rate_threshold = 0.05
        
        processing_stats = {"success_rate": 0.95, "total_processed": 100, "failed_processed": 10}
        performance_metrics = {"avg_processing_time_seconds": 30}
        cost_metrics = {"estimated_cost_usd": 5.0}
        
        alerts = use_case._check_alert_conditions(processing_stats, performance_metrics, cost_metrics)
        
        # Should have error rate alert (10/100 = 0.1 > 0.05)
        error_rate_alerts = [a for a in alerts if a["type"] == "error_rate_high"]
        assert len(error_rate_alerts) == 1
        assert error_rate_alerts[0]["severity"] == "critical"

    def test_check_alert_conditions_cost_high(self, use_case, mock_settings):
        """Test alert for high cost"""
        mock_settings.autoproc_success_rate_threshold = 0.9
        mock_settings.autoproc_error_rate_threshold = 0.05
        
        processing_stats = {"success_rate": 0.95, "total_processed": 100, "failed_processed": 2}
        performance_metrics = {"avg_processing_time_seconds": 30}
        cost_metrics = {"estimated_cost_usd": 10.0}  # $10/day = $300/month
        
        alerts = use_case._check_alert_conditions(processing_stats, performance_metrics, cost_metrics)
        
        # Should have cost alert (10 * 30 = 300 > 100)
        cost_alerts = [a for a in alerts if a["type"] == "cost_high"]
        assert len(cost_alerts) == 1
        assert cost_alerts[0]["severity"] == "warning"

    def test_check_alert_conditions_performance_slow(self, use_case, mock_settings):
        """Test alert for slow performance"""
        mock_settings.autoproc_success_rate_threshold = 0.9
        mock_settings.autoproc_error_rate_threshold = 0.05
        
        processing_stats = {"success_rate": 0.95, "total_processed": 100, "failed_processed": 2}
        performance_metrics = {"avg_processing_time_seconds": 90}  # 90 seconds > 60 seconds threshold
        cost_metrics = {"estimated_cost_usd": 5.0}
        
        alerts = use_case._check_alert_conditions(processing_stats, performance_metrics, cost_metrics)
        
        # Should have performance alert
        performance_alerts = [a for a in alerts if a["type"] == "performance_slow"]
        assert len(performance_alerts) == 1
        assert performance_alerts[0]["severity"] == "warning"

    def test_check_alert_conditions_multiple_alerts(self, use_case, mock_settings):
        """Test multiple alert conditions"""
        mock_settings.autoproc_success_rate_threshold = 0.9
        mock_settings.autoproc_error_rate_threshold = 0.05
        
        processing_stats = {"success_rate": 0.8, "total_processed": 100, "failed_processed": 10}  # Low success, high error
        performance_metrics = {"avg_processing_time_seconds": 90}  # Slow performance
        cost_metrics = {"estimated_cost_usd": 10.0}  # High cost
        
        alerts = use_case._check_alert_conditions(processing_stats, performance_metrics, cost_metrics)
        
        # Should have multiple alerts
        alert_types = {a["type"] for a in alerts}
        expected_types = {"success_rate_low", "error_rate_high", "performance_slow", "cost_high"}
        assert alert_types == expected_types

    def test_check_alert_conditions_no_alerts(self, use_case, mock_settings):
        """Test when no alert conditions are met"""
        mock_settings.autoproc_success_rate_threshold = 0.9
        mock_settings.autoproc_error_rate_threshold = 0.05
        
        processing_stats = {"success_rate": 0.98, "total_processed": 100, "failed_processed": 2}
        performance_metrics = {"avg_processing_time_seconds": 30}
        cost_metrics = {"estimated_cost_usd": 2.0}
        
        alerts = use_case._check_alert_conditions(processing_stats, performance_metrics, cost_metrics)
        
        # Should have no alerts
        assert len(alerts) == 0

    def test_check_alert_conditions_error_handling(self, use_case, mock_settings):
        """Test error handling in alert checking"""
        mock_settings.autoproc_success_rate_threshold = 0.9
        mock_settings.autoproc_error_rate_threshold = 0.05
        
        # Malformed data that could cause errors
        processing_stats = {}  # Missing required keys
        performance_metrics = {}
        cost_metrics = {}
        
        alerts = use_case._check_alert_conditions(processing_stats, performance_metrics, cost_metrics)
        
        # Should handle errors gracefully and possibly include an error alert
        assert isinstance(alerts, list)

    def test_settings_included_in_result(self, use_case, mock_dependencies, mock_settings):
        """Test that settings are included in the result"""
        mock_settings.autoproc_parallel_workers = 7
        mock_settings.autoproc_batch_size = 12
        mock_settings.autoproc_max_items = 25
        
        result = use_case.execute()
        
        settings = result["settings"]
        assert settings["parallel_workers"] == mock_settings.autoproc_parallel_workers  # 7
        assert settings["batch_size"] == mock_settings.autoproc_batch_size  # 12  
        assert settings["max_items"] == mock_settings.autoproc_max_items  # 25
        assert "success_rate_threshold" in settings
        assert "queue_alert_threshold" in settings
        assert "error_rate_threshold" in settings

    def test_collect_detailed_metrics_structure(self, use_case, mock_dependencies):
        """Test detailed metrics collection structure"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        detailed = use_case._collect_detailed_metrics(start_date, end_date)
        
        # Check candidate name extraction stats
        assert "candidate_name_extraction_stats" in detailed
        extraction_stats = detailed["candidate_name_extraction_stats"]
        assert "successful_extractions" in extraction_stats
        assert "failed_extractions" in extraction_stats
        assert "most_common_names" in extraction_stats
        
        # Check Zoho integration stats
        assert "zoho_integration_stats" in detailed
        zoho_stats = detailed["zoho_integration_stats"]
        assert "successful_lookups" in zoho_stats
        assert "failed_lookups" in zoho_stats
        assert "successful_writes" in zoho_stats
        assert "failed_writes" in zoho_stats
        assert "avg_lookup_time" in zoho_stats
        
        # Check Gemini API stats
        assert "gemini_api_stats" in detailed
        gemini_stats = detailed["gemini_api_stats"]
        assert "successful_calls" in gemini_stats
        assert "failed_calls" in gemini_stats
        assert "avg_response_time" in gemini_stats
        assert "rate_limit_hits" in gemini_stats

    def test_error_handling_in_collect_methods(self, use_case, mock_dependencies):
        """Test error handling in collection methods"""
        # Mock repositories to raise exceptions
        mock_dependencies['ai_usage_repo'].get_usage_summary.side_effect = Exception("Database error")
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        # Should not raise exceptions, but return empty/default data
        basic_stats = use_case._collect_basic_stats(start_date, end_date)
        assert isinstance(basic_stats, dict)
        
        processing_stats = use_case._collect_processing_stats(start_date, end_date)
        assert isinstance(processing_stats, dict)
        
        performance_metrics = use_case._collect_performance_metrics(start_date, end_date)
        assert isinstance(performance_metrics, dict)
        
        cost_metrics = use_case._collect_cost_metrics(start_date, end_date)
        assert isinstance(cost_metrics, dict)
        
        # Cost metrics should handle the error gracefully
        assert cost_metrics["total_tokens"] == 0
        assert cost_metrics["estimated_cost"] == 0.0