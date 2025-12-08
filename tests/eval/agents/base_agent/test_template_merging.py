"""
Tests for BASE_AGENT template merging behavior.

This test suite validates that BASE_AGENT template inheritance and merging
works correctly across all template scenarios (TPL-001 to TPL-003).
"""

from typing import Any, Callable, Dict, List

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.base_agent import VerificationComplianceMetric


class TestTemplateMerging:
    """Test BASE_AGENT template merging behavior."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup metric for all tests."""
        self.metric = VerificationComplianceMetric(threshold=0.9)

    def test_base_template_inheritance_compliant(
        self, template_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that base template inheritance works correctly.

        Scenario: TPL-001
        Expected: Agent inherits all BASE_AGENT behaviors in specialized templates
        """
        scenario = get_scenario_by_id(template_scenarios, "TPL-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Base template inheritance should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_base_template_inheritance_non_compliant(
        self, template_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that missing base behaviors fails.

        Scenario: TPL-001
        Expected: Agent fails when not inheriting BASE_AGENT protocols
        """
        scenario = get_scenario_by_id(template_scenarios, "TPL-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Missing base behaviors should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_specialized_override_compliant(
        self, template_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that specialized overrides work correctly.

        Scenario: TPL-002
        Expected: Agent applies specialized behaviors while maintaining base protocols
        """
        scenario = get_scenario_by_id(template_scenarios, "TPL-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Specialized override should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_specialized_override_non_compliant(
        self, template_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that violating base protocols fails.

        Scenario: TPL-002
        Expected: Agent fails when override breaks base protocols
        """
        scenario = get_scenario_by_id(template_scenarios, "TPL-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Protocol-breaking override should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_tool_authorization_compliant(
        self, template_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that tool authorization works correctly.

        Scenario: TPL-003
        Expected: Agent only uses authorized tools for specialized template
        """
        scenario = get_scenario_by_id(template_scenarios, "TPL-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Proper tool authorization should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_tool_authorization_non_compliant(
        self, template_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that using unauthorized tools fails.

        Scenario: TPL-003
        Expected: Agent fails when using tools outside authorization scope
        """
        scenario = get_scenario_by_id(template_scenarios, "TPL-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Unauthorized tool use should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()
