"""
Tests for Research Agent memory efficiency protocol compliance.

This test suite validates that Research Agent memory management protocols are
properly enforced across all memory scenarios (MEM-R-001 to MEM-R-006).
"""

from typing import Any, Callable, Dict, List

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.research import MemoryEfficiencyMetric


class TestMemoryProtocol:
    """Test Research Agent memory efficiency protocol compliance."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup memory efficiency metric for all tests."""
        self.metric = MemoryEfficiencyMetric(threshold=0.9)

    def test_file_size_check_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that compliant file size checking scores high.

        Scenario: MEM-R-001
        Expected: Agent checks file size before reading large files
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Compliant file size check should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_file_size_check_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that missing file size check fails.

        Scenario: MEM-R-001
        Expected: Agent fails when not checking file size
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Missing file size check should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_summarizer_usage_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that document summarizer usage scores high.

        Scenario: MEM-R-002
        Expected: Agent uses summarizer for files >20KB
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Summarizer usage should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_summarizer_usage_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that missing summarizer usage fails.

        Scenario: MEM-R-002
        Expected: Agent fails when not using summarizer for large files
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Missing summarizer should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_file_read_limit_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that 3-5 file limit compliance scores high.

        Scenario: MEM-R-003
        Expected: Agent reads 3-5 files max, uses sampling
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.8, (
            f"File limit compliance should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )

    def test_file_read_limit_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that excessive file reads fail.

        Scenario: MEM-R-003
        Expected: Agent fails when reading too many files
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.8, (
            f"Excessive file reads should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )

    def test_line_sampling_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that strategic line sampling scores high.

        Scenario: MEM-R-004
        Expected: Agent samples 100-200 lines per file
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert (
            score >= 0.85
        ), f"Line sampling should pass, got {score}\nReason: {self.metric.reason}"

    def test_line_sampling_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that full file reads fail.

        Scenario: MEM-R-004
        Expected: Agent fails when reading entire files
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.85, (
            f"Full file reads should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )

    def test_no_full_codebase_reads_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that discovery-based approach scores high.

        Scenario: MEM-R-005
        Expected: Agent uses discovery tools, not brute force
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-005")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.95, (
            f"Discovery-based approach should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_no_full_codebase_reads_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that brute force reads fail.

        Scenario: MEM-R-005
        Expected: Agent fails when reading entire codebase
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-005")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.95, (
            f"Brute force reads should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_strategic_sampling_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that strategic sampling scores high.

        Scenario: MEM-R-006
        Expected: Agent uses pattern extraction, not exhaustive analysis
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-006")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Strategic sampling should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_strategic_sampling_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that exhaustive analysis fails.

        Scenario: MEM-R-006
        Expected: Agent fails when using brute force enumeration
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-R-006")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Exhaustive analysis should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()
