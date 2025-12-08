"""
Tests for BASE_AGENT tool orchestration patterns.

This test suite validates that BASE_AGENT tool orchestration protocols are
properly enforced across all orchestration scenarios (ORC-001 to ORC-003).
"""

from typing import Any, Callable, Dict, List

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.base_agent import VerificationComplianceMetric


class TestToolOrchestration:
    """Test BASE_AGENT tool orchestration compliance."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup verification metric for all tests."""
        self.metric = VerificationComplianceMetric(threshold=0.9)

    def test_parallel_execution_compliant(
        self,
        orchestration_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable,
    ) -> None:
        """Test that parallel tool execution works correctly.

        Scenario: ORC-001
        Expected: Agent executes independent operations in parallel
        """
        scenario = get_scenario_by_id(orchestration_scenarios, "ORC-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Parallel execution should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_parallel_execution_non_compliant(
        self,
        orchestration_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable,
    ) -> None:
        """Test that sequential execution of independent ops fails.

        Scenario: ORC-001
        Expected: Agent fails when not parallelizing independent operations
        """
        scenario = get_scenario_by_id(orchestration_scenarios, "ORC-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Sequential independent ops should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_error_recovery_compliant(
        self,
        orchestration_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable,
    ) -> None:
        """Test that error recovery works correctly.

        Scenario: ORC-002
        Expected: Agent handles errors gracefully with recovery strategies
        """
        scenario = get_scenario_by_id(orchestration_scenarios, "ORC-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert (
            score >= 0.9
        ), f"Error recovery should pass, got {score}\nReason: {self.metric.reason}"
        assert self.metric.is_successful()

    def test_error_recovery_non_compliant(
        self,
        orchestration_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable,
    ) -> None:
        """Test that poor error handling fails.

        Scenario: ORC-002
        Expected: Agent fails when not handling errors properly
        """
        scenario = get_scenario_by_id(orchestration_scenarios, "ORC-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Poor error handling should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_cascading_workflows_compliant(
        self,
        orchestration_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable,
    ) -> None:
        """Test that cascading workflows work correctly.

        Scenario: ORC-003
        Expected: Agent chains dependent operations in correct order
        """
        scenario = get_scenario_by_id(orchestration_scenarios, "ORC-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Cascading workflows should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_cascading_workflows_non_compliant(
        self,
        orchestration_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable,
    ) -> None:
        """Test that incorrect workflow order fails.

        Scenario: ORC-003
        Expected: Agent fails when executing dependencies out of order
        """
        scenario = get_scenario_by_id(orchestration_scenarios, "ORC-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Incorrect workflow order should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()
