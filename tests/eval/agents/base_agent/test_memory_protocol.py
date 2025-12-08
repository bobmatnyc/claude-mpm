"""
Tests for BASE_AGENT memory protocol compliance.

This test suite validates that BASE_AGENT memory management protocols are
properly enforced across all memory scenarios (MEM-001 to MEM-006).
"""

from typing import Any, Callable, Dict, List

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.base_agent import MemoryProtocolMetric


class TestMemoryProtocol:
    """Test BASE_AGENT memory protocol compliance."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup memory protocol metric for all tests."""
        self.metric = MemoryProtocolMetric(threshold=0.9)

    def test_json_response_format_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that compliant JSON response format scores high.

        Scenario: MEM-001
        Expected: Agent uses JSON response block with memory-update field
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Compliant JSON memory format should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_json_response_format_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that missing JSON response format fails.

        Scenario: MEM-001
        Expected: Agent fails when not using JSON response block
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Missing JSON memory format should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_memory_trigger_detection_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that memory trigger detection works correctly.

        Scenario: MEM-002
        Expected: Agent detects memory triggers and stores appropriately
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Memory trigger detection should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_memory_trigger_detection_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that missing memory trigger detection fails.

        Scenario: MEM-002
        Expected: Agent fails when not detecting memory triggers
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Missing memory triggers should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_memory_avoidance_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that obvious facts are not stored in memory.

        Scenario: MEM-003
        Expected: Agent avoids storing common knowledge
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Avoiding obvious facts should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_memory_avoidance_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that storing obvious facts fails.

        Scenario: MEM-003
        Expected: Agent fails when storing common knowledge
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Storing obvious facts should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_memory_consolidation_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that memory consolidation works correctly.

        Scenario: MEM-004
        Expected: Agent consolidates related memories into coherent entries
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Memory consolidation should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_memory_consolidation_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that fragmented memories fail.

        Scenario: MEM-004
        Expected: Agent fails when creating duplicate/fragmented memories
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Fragmented memories should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_memory_update_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that memory updates work correctly.

        Scenario: MEM-005
        Expected: Agent updates existing memories appropriately
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-005")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Memory update should pass, got {score}\nReason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_memory_update_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that creating duplicates instead of updating fails.

        Scenario: MEM-005
        Expected: Agent fails when duplicating instead of updating
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-005")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Duplicate memories should fail, got {score}\nReason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()

    def test_memory_size_limits_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that memory size limits are respected.

        Scenario: MEM-006
        Expected: Agent keeps memory entries concise and focused
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-006")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Concise memory entries should pass, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert self.metric.is_successful()

    def test_memory_size_limits_non_compliant(
        self, memory_scenarios: List[Dict[str, Any]], get_scenario_by_id: Callable
    ) -> None:
        """Test that overly verbose memories fail.

        Scenario: MEM-006
        Expected: Agent fails when creating verbose/unfocused memories
        """
        scenario = get_scenario_by_id(memory_scenarios, "MEM-006")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"],
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Verbose memory entries should fail, got {score}\n"
            f"Reason: {self.metric.reason}"
        )
        assert not self.metric.is_successful()
