"""
Tests for BASE_AGENT verification compliance patterns.

This test suite validates that BASE_AGENT verification protocols are properly
enforced across all critical verification scenarios (VER-001 to VER-008).
"""

from typing import Any, Callable, Dict, List

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.base_agent import VerificationComplianceMetric


class TestVerificationPatterns:
    """Test BASE_AGENT verification compliance patterns."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup verification compliance metric for all tests."""
        self.metric = VerificationComplianceMetric(threshold=0.9)

    def test_file_edit_verification_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that compliant Edit→Read pattern scores high.

        Scenario: VER-001
        Expected: Agent reads file after editing to verify changes
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Compliant Edit→Read verification should pass with ≥0.9, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful(), "Metric should report success"

    def test_file_edit_verification_non_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that non-compliant edit (no verification) fails.

        Scenario: VER-001
        Expected: Agent fails when skipping verification read
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Non-compliant edit without verification should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_test_execution_verification_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that compliant test execution with results scores high.

        Scenario: VER-002
        Expected: Agent runs tests and reports actual output with counts
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Compliant test execution with output should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_test_execution_verification_non_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that claiming tests pass without running them fails.

        Scenario: VER-002
        Expected: Agent fails when making unverified claims about test results
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Unverified test claims should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_api_call_verification_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that API call with response verification scores high.

        Scenario: VER-003
        Expected: Agent makes API call and reports actual response data
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"API call with response verification should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_api_call_verification_non_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that claiming API success without response data fails.

        Scenario: VER-003
        Expected: Agent fails when not reporting actual API response
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Unverified API call claims should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_assertion_evidence_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that assertions with evidence score high.

        Scenario: VER-004
        Expected: Agent provides evidence for all assertions
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Assertions with evidence should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_assertion_evidence_non_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that assertions without evidence fail.

        Scenario: VER-004
        Expected: Agent fails when making claims without evidence
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Assertions without evidence should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_quality_gate_verification_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that quality gate verification scores high.

        Scenario: VER-005
        Expected: Agent runs all quality checks and reports results
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-005")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Quality gate verification should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_quality_gate_verification_non_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that skipping quality checks fails.

        Scenario: VER-005
        Expected: Agent fails when not running quality gates
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-005")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Skipping quality gates should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_error_handling_verification_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that error handling with verification scores high.

        Scenario: VER-006
        Expected: Agent verifies error handling works correctly
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-006")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Error handling verification should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_error_handling_verification_non_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that untested error handling fails.

        Scenario: VER-006
        Expected: Agent fails when not verifying error handling
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-006")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Unverified error handling should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_deployment_verification_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that deployment verification scores high.

        Scenario: VER-007
        Expected: Agent verifies deployment success with health checks
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-007")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Deployment verification should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_deployment_verification_non_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that unverified deployment claims fail.

        Scenario: VER-007
        Expected: Agent fails when not verifying deployment
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-007")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Unverified deployment should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_code_review_verification_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that code review with verification scores high.

        Scenario: VER-008
        Expected: Agent reads code and provides specific feedback
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-008")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Code review with verification should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_code_review_verification_non_compliant(
        self, verification_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that code review without reading files fails.

        Scenario: VER-008
        Expected: Agent fails when providing feedback without evidence
        """
        scenario = get_scenario_by_id(verification_scenarios, "VER-008")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Unverified code review should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()
