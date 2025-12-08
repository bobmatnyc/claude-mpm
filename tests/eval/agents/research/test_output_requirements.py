"""
Tests for Research Agent output requirements compliance.

This test suite validates that Research Agent output formatting is
properly enforced across all output scenarios (OUT-R-001 to OUT-R-004).
"""

from typing import Any, Callable, Dict, List

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.research import SamplingStrategyMetric


class TestOutputRequirements:
    """Test Research Agent output requirements compliance."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup sampling strategy metric for all tests."""
        self.metric = SamplingStrategyMetric(threshold=0.85)

    def test_file_list_inclusion_compliant(
        self, output_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that file list inclusion scores high.

        Scenario: OUT-R-001
        Expected: Agent includes complete file list
        """
        scenario = get_scenario_by_id(output_scenarios, "OUT-R-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.85, (
            f"File list inclusion should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_file_list_inclusion_non_compliant(
        self, output_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that missing file list fails.

        Scenario: OUT-R-001
        Expected: Agent fails when file list omitted
        """
        scenario = get_scenario_by_id(output_scenarios, "OUT-R-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.85, (
            f"Missing file list should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_pattern_analysis_compliant(
        self, output_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that pattern analysis scores high.

        Scenario: OUT-R-002
        Expected: Agent provides pattern analysis with insights
        """
        scenario = get_scenario_by_id(output_scenarios, "OUT-R-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.85, (
            f"Pattern analysis should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_pattern_analysis_non_compliant(
        self, output_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that raw observations fail.

        Scenario: OUT-R-002
        Expected: Agent fails when no pattern analysis provided
        """
        scenario = get_scenario_by_id(output_scenarios, "OUT-R-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.85, (
            f"Raw observations should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_representative_samples_compliant(
        self, output_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that representative samples score high.

        Scenario: OUT-R-003
        Expected: Agent includes code samples in output
        """
        scenario = get_scenario_by_id(output_scenarios, "OUT-R-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.85, (
            f"Representative samples should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_representative_samples_non_compliant(
        self, output_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that vague descriptions fail.

        Scenario: OUT-R-003
        Expected: Agent fails when no code samples provided
        """
        scenario = get_scenario_by_id(output_scenarios, "OUT-R-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.85, (
            f"Vague descriptions should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_actionable_recommendations_compliant(
        self, output_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that actionable recommendations score high.

        Scenario: OUT-R-004
        Expected: Agent provides specific, actionable recommendations
        """
        scenario = get_scenario_by_id(output_scenarios, "OUT-R-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.85, (
            f"Actionable recommendations should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_actionable_recommendations_non_compliant(
        self, output_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that vague suggestions fail.

        Scenario: OUT-R-004
        Expected: Agent fails when recommendations are vague
        """
        scenario = get_scenario_by_id(output_scenarios, "OUT-R-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.85, (
            f"Vague suggestions should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()
