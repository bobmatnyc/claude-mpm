#!/usr/bin/env python3
"""
Tests for AgentMetricsCollector Service
======================================

Comprehensive test suite for the extracted AgentMetricsCollector service.
Tests all metrics collection, tracking, and reporting functionality.
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_metrics_collector import (
    AgentMetricsCollector,
)


class TestAgentMetricsCollector:
    """Test suite for AgentMetricsCollector."""

    @pytest.fixture
    def metrics_collector(self):
        """Create AgentMetricsCollector instance."""
        return AgentMetricsCollector()

    def test_initialization(self, metrics_collector):
        """Test AgentMetricsCollector initialization."""
        assert hasattr(metrics_collector, "logger")
        assert hasattr(metrics_collector, "_deployment_metrics")

        # Check initial metrics state
        metrics = metrics_collector.get_deployment_metrics()
        assert metrics["total_deployments"] == 0
        assert metrics["successful_deployments"] == 0
        assert metrics["success_rate_percent"] == 0.0

    def test_update_deployment_metrics_success(self, metrics_collector):
        """Test updating metrics with successful deployment."""
        results = {"deployed": ["test-agent", "qa-agent"], "errors": [], "migrated": []}

        metrics_collector.update_deployment_metrics(150.5, results)

        metrics = metrics_collector.get_deployment_metrics()
        assert metrics["total_deployments"] == 1
        assert metrics["successful_deployments"] == 1
        assert metrics["failed_deployments"] == 0
        assert metrics["success_rate_percent"] == 100.0
        assert metrics["average_deployment_time_ms"] == 150.5

        # Check agent type tracking
        assert "qa" in metrics["agent_type_distribution"]
        assert metrics["agent_type_distribution"]["qa"] == 2  # Both agents counted

    def test_update_deployment_metrics_failure(self, metrics_collector):
        """Test updating metrics with failed deployment."""
        results = {
            "deployed": [],
            "errors": ["Template parsing failed", "File not found"],
            "migrated": [],
        }

        metrics_collector.update_deployment_metrics(75.0, results)

        metrics = metrics_collector.get_deployment_metrics()
        assert metrics["total_deployments"] == 1
        assert metrics["successful_deployments"] == 0
        assert metrics["failed_deployments"] == 1
        assert metrics["success_rate_percent"] == 0.0

        # Check error tracking
        assert len(metrics["error_distribution"]) > 0

    def test_update_deployment_metrics_with_migrations(self, metrics_collector):
        """Test updating metrics with migrations."""
        results = {
            "deployed": ["security-agent"],
            "errors": [],
            "migrated": ["old-agent", "legacy-agent"],
        }

        metrics_collector.update_deployment_metrics(200.0, results)

        metrics = metrics_collector.get_deployment_metrics()
        assert metrics["migrations_performed"] == 2
        assert metrics["version_migrations"] == 2

    def test_rolling_average_calculation(self, metrics_collector):
        """Test rolling average calculation for deployment times."""
        # Add multiple deployments
        for i in range(5):
            results = {"deployed": [f"agent-{i}"], "errors": [], "migrated": []}
            metrics_collector.update_deployment_metrics(100.0 + i * 10, results)

        metrics = metrics_collector.get_deployment_metrics()
        expected_avg = (100 + 110 + 120 + 130 + 140) / 5
        assert metrics["average_deployment_time_ms"] == expected_avg

    def test_deployment_times_limit(self, metrics_collector):
        """Test that deployment times are limited to last 100 entries."""
        # Add more than 100 deployments
        for i in range(105):
            results = {"deployed": [f"agent-{i}"], "errors": [], "migrated": []}
            metrics_collector.update_deployment_metrics(float(i), results)

        # Check that only last 100 are kept
        assert len(metrics_collector._deployment_metrics["deployment_times"]) == 100

        # Check that the oldest entries were removed
        deployment_times = metrics_collector._deployment_metrics["deployment_times"]
        assert min(deployment_times) == 5.0  # Should start from 5, not 0

    def test_agent_type_categorization(self, metrics_collector):
        """Test agent type categorization."""
        test_cases = [
            ("security-scanner", "security"),
            ("qa-validator", "qa"),
            ("test-runner", "qa"),
            ("doc-generator", "documentation"),
            ("data-processor", "data"),
            ("ops-monitor", "operations"),
            ("research-analyzer", "research"),
            ("general-helper", "general"),
        ]

        for agent_name, expected_type in test_cases:
            actual_type = metrics_collector._extract_agent_type(agent_name)
            assert actual_type == expected_type, f"Failed for {agent_name}"

    def test_error_categorization(self, metrics_collector):
        """Test error message categorization."""
        test_cases = [
            ("JSON parsing failed", "parsing_error"),
            ("Invalid JSON format", "parsing_error"),
            ("File not found", "file_error"),
            ("Path does not exist", "file_error"),
            ("Version mismatch", "version_error"),
            ("Template validation failed", "template_error"),
            ("Validation error occurred", "validation_error"),
            ("Unknown error", "other_error"),
        ]

        for error_msg, expected_category in test_cases:
            actual_category = metrics_collector._categorize_error(error_msg)
            assert actual_category == expected_category, f"Failed for {error_msg}"

    def test_get_deployment_status(self, metrics_collector):
        """Test getting deployment status."""
        status = metrics_collector.get_deployment_status()

        assert "deployment_metrics" in status
        assert "last_updated" in status
        assert "metrics_collection_active" in status
        assert status["metrics_collection_active"] is True

    def test_reset_metrics(self, metrics_collector):
        """Test resetting metrics."""
        # Add some data first
        results = {"deployed": ["test-agent"], "errors": [], "migrated": []}
        metrics_collector.update_deployment_metrics(100.0, results)

        # Verify data exists
        metrics = metrics_collector.get_deployment_metrics()
        assert metrics["total_deployments"] == 1

        # Reset metrics
        metrics_collector.reset_metrics()

        # Verify reset
        metrics = metrics_collector.get_deployment_metrics()
        assert metrics["total_deployments"] == 0
        assert metrics["successful_deployments"] == 0
        assert metrics["average_deployment_time_ms"] == 0.0
        assert len(metrics["agent_type_distribution"]) == 0

    def test_track_validation_time(self, metrics_collector):
        """Test tracking validation times."""
        metrics_collector.track_validation_time("test-agent", 25.5)
        metrics_collector.track_validation_time("qa-agent", 30.0)

        # Validation times are stored internally
        validation_times = metrics_collector._deployment_metrics[
            "template_validation_times"
        ]
        assert validation_times["test-agent"] == 25.5
        assert validation_times["qa-agent"] == 30.0

    def test_get_performance_summary(self, metrics_collector):
        """Test getting performance summary."""
        # Add some test data
        results = {"deployed": ["test-agent"], "errors": [], "migrated": []}
        metrics_collector.update_deployment_metrics(150.0, results)

        results = {"deployed": ["qa-agent"], "errors": ["Error"], "migrated": []}
        metrics_collector.update_deployment_metrics(200.0, results)

        summary = metrics_collector.get_performance_summary()

        assert "total_deployments" in summary
        assert "success_rate" in summary
        assert "average_time_ms" in summary
        assert "fastest_deployment_ms" in summary
        assert "slowest_deployment_ms" in summary
        assert "error_rate_percent" in summary

        assert summary["total_deployments"] == 2
        assert summary["fastest_deployment_ms"] == 150.0
        assert summary["slowest_deployment_ms"] == 200.0

    def test_most_common_agent_type(self, metrics_collector):
        """Test getting most common agent type."""
        # Add agents of different types
        test_data = [
            (["security-agent"], "security"),
            (["security-scanner"], "security"),
            (["qa-agent"], "qa"),
            (["doc-agent"], "documentation"),
        ]

        for agents, _ in test_data:
            results = {"deployed": agents, "errors": [], "migrated": []}
            metrics_collector.update_deployment_metrics(100.0, results)

        most_common = metrics_collector._get_most_common_agent_type()
        assert most_common == "security"  # Should be most frequent

    def test_error_rate_calculation(self, metrics_collector):
        """Test error rate calculation."""
        # Add successful deployment
        results = {"deployed": ["agent1"], "errors": [], "migrated": []}
        metrics_collector.update_deployment_metrics(100.0, results)

        # Add failed deployment
        results = {"deployed": [], "errors": ["Error"], "migrated": []}
        metrics_collector.update_deployment_metrics(100.0, results)

        error_rate = metrics_collector._calculate_error_rate()
        assert error_rate == 50.0  # 1 failure out of 2 total = 50%

    def test_mixed_success_failure_metrics(self, metrics_collector):
        """Test metrics with mixed success and failure scenarios."""
        # Successful deployment
        results = {"deployed": ["agent1"], "errors": [], "migrated": ["old-agent"]}
        metrics_collector.update_deployment_metrics(120.0, results)

        # Failed deployment
        results = {"deployed": [], "errors": ["Parse error"], "migrated": []}
        metrics_collector.update_deployment_metrics(80.0, results)

        # Partially successful deployment
        results = {"deployed": ["agent2"], "errors": ["Warning"], "migrated": []}
        metrics_collector.update_deployment_metrics(150.0, results)

        metrics = metrics_collector.get_deployment_metrics()

        assert metrics["total_deployments"] == 3
        assert metrics["successful_deployments"] == 1  # Only first (no errors)
        assert metrics["failed_deployments"] == 2  # Second and third (both have errors)
        assert metrics["migrations_performed"] == 1
        assert abs(metrics["success_rate_percent"] - 33.33) < 0.01  # 1/3 * 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
