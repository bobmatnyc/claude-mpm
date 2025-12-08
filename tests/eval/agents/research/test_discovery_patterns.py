"""
Tests for Research Agent discovery pattern compliance.

This test suite validates that Research Agent discovery protocols are
properly enforced across all discovery scenarios (DSC-R-001 to DSC-R-005).
"""

from typing import Any, Callable, Dict, List

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.research import SamplingStrategyMetric


class TestDiscoveryPatterns:
    """Test Research Agent discovery pattern compliance."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup sampling strategy metric for all tests."""
        self.metric = SamplingStrategyMetric(threshold=0.85)

    def test_grep_glob_discovery_compliant(
        self, discovery_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that grep/glob usage scores high.

        Scenario: DSC-R-001
        Expected: Agent uses grep/glob for file discovery
        """
        scenario = get_scenario_by_id(discovery_scenarios, "DSC-R-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.85, (
            f"Grep/glob discovery should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_grep_glob_discovery_non_compliant(
        self, discovery_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that sequential file reading fails.

        Scenario: DSC-R-001
        Expected: Agent fails when not using discovery tools
        """
        scenario = get_scenario_by_id(discovery_scenarios, "DSC-R-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.85, (
            f"Sequential reads should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_pattern_extraction_compliant(
        self, discovery_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that pattern extraction scores high.

        Scenario: DSC-R-002
        Expected: Agent extracts patterns from samples
        """
        scenario = get_scenario_by_id(discovery_scenarios, "DSC-R-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.85, (
            f"Pattern extraction should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_pattern_extraction_non_compliant(
        self, discovery_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that raw enumeration fails.

        Scenario: DSC-R-002
        Expected: Agent fails when not extracting patterns
        """
        scenario = get_scenario_by_id(discovery_scenarios, "DSC-R-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.85, (
            f"Raw enumeration should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_findings_synthesis_compliant(
        self, discovery_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that findings synthesis scores high.

        Scenario: DSC-R-003
        Expected: Agent synthesizes findings into coherent insights
        """
        scenario = get_scenario_by_id(discovery_scenarios, "DSC-R-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.85, (
            f"Findings synthesis should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_findings_synthesis_non_compliant(
        self, discovery_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that raw observations fail.

        Scenario: DSC-R-003
        Expected: Agent fails when only listing observations
        """
        scenario = get_scenario_by_id(discovery_scenarios, "DSC-R-003")

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

    def test_executive_summary_compliant(
        self, discovery_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that executive summary scores high.

        Scenario: DSC-R-004
        Expected: Agent provides executive summary upfront
        """
        scenario = get_scenario_by_id(discovery_scenarios, "DSC-R-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.85, (
            f"Executive summary should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_executive_summary_non_compliant(
        self, discovery_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that missing summary fails.

        Scenario: DSC-R-004
        Expected: Agent fails when no executive summary provided
        """
        scenario = get_scenario_by_id(discovery_scenarios, "DSC-R-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.85, (
            f"Missing summary should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_code_examples_compliant(
        self, discovery_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that code examples score high.

        Scenario: DSC-R-005
        Expected: Agent includes representative code examples
        """
        scenario = get_scenario_by_id(discovery_scenarios, "DSC-R-005")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.85, (
            f"Code examples should pass, got {score}\nReason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_code_examples_non_compliant(
        self, discovery_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that vague descriptions fail.

        Scenario: DSC-R-005
        Expected: Agent fails when no code examples provided
        """
        scenario = get_scenario_by_id(discovery_scenarios, "DSC-R-005")

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
