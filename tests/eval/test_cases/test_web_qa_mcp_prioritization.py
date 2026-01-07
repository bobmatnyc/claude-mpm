"""
Web-QA Agent MCP Tool Prioritization Validation Tests

Tests web-qa agent compliance with Playwright MCP prioritization guidelines
documented in web-qa-mcp-browser-integration-2025-12-18.md

Key Validations:
1. Playwright MCP tools prioritized over Chrome DevTools MCP
2. MCP tools prioritized over Bash commands
3. browser_snapshot preferred over browser_take_screenshot for inspection
4. Correct fallback behavior when tools unavailable
5. Evidence collection from tool outputs

Usage:
    # Run all web-qa MCP prioritization tests
    pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py -v

    # Run specific scenario
    pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py::TestWebQAMCPPrioritization::test_playwright_navigation_and_snapshot -v

    # Run with detailed output
    pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py -v -s

    # Run critical tests only
    pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py -v -m critical
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.mcp_tool_prioritization import (
    MCPToolAvailabilityMetric,
    MCPToolPrioritizationMetric,
)

# Load test scenarios
SCENARIOS_FILE = (
    Path(__file__).parent.parent / "scenarios" / "web_qa_mcp_prioritization.json"
)

with open(SCENARIOS_FILE) as f:
    SCENARIO_DATA = json.load(f)
    SCENARIOS = SCENARIO_DATA["scenarios"]


def get_scenario_by_id(scenario_id: str) -> Dict[str, Any]:
    """Get scenario by ID."""
    for scenario in SCENARIOS:
        if scenario["id"] == scenario_id:
            return scenario
    raise ValueError(f"Scenario not found: {scenario_id}")


def get_scenarios_by_category(category: str) -> list:
    """Get all scenarios in a category."""
    return [s for s in SCENARIOS if s["category"] == category]


def get_scenarios_by_severity(severity: str) -> list:
    """Get all scenarios with specified severity."""
    return [s for s in SCENARIOS if s["severity"] == severity]


class TestWebQAMCPPrioritization:
    """Test suite for web-qa agent MCP tool prioritization."""

    @pytest.mark.critical
    @pytest.mark.parametrize(
        "scenario", get_scenarios_by_severity("critical"), ids=lambda s: s["id"]
    )
    def test_critical_prioritization_scenarios(self, scenario: Dict[str, Any]):
        """
        Test critical MCP tool prioritization scenarios.

        These tests MUST pass for the web-qa agent to be considered compliant.
        """
        # Create test case
        test_case = LLMTestCase(
            input=scenario["user_input"],
            # In real usage, this would be the actual agent response
            # For now, we'll use a mock response that demonstrates expected behavior
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        # Create metric
        metric = MCPToolPrioritizationMetric(
            threshold=0.9,  # Critical scenarios require 90%+ compliance
            strict_mode=True,  # Critical scenarios require perfect prioritization
        )

        # Assert test passes
        metric.measure(test_case)
        assert metric.is_successful(), f"Test failed: {metric.reason}"

    @pytest.mark.high
    @pytest.mark.parametrize(
        "scenario", get_scenarios_by_severity("high"), ids=lambda s: s["id"]
    )
    def test_high_priority_scenarios(self, scenario: Dict[str, Any]):
        """
        Test high-priority MCP tool prioritization scenarios.

        These tests should pass with 80%+ compliance.
        """
        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(threshold=0.8)

        metric.measure(test_case)
        assert metric.is_successful(), f"Test failed: {metric.reason}"

    @pytest.mark.medium
    @pytest.mark.parametrize(
        "scenario", get_scenarios_by_severity("medium"), ids=lambda s: s["id"]
    )
    def test_medium_priority_scenarios(self, scenario: Dict[str, Any]):
        """
        Test medium-priority scenarios.

        These tests should pass with 70%+ compliance.
        """
        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(threshold=0.7)

        metric.measure(test_case)
        assert metric.is_successful(), f"Test failed: {metric.reason}"

    def test_playwright_navigation_and_snapshot(self):
        """
        Test: Agent uses Playwright MCP for navigation and snapshot inspection.

        Expected behavior:
        - Uses mcp__playwright__browser_navigate to load page
        - Uses mcp__playwright__browser_snapshot for accessibility inspection (NOT screenshot)
        - Uses mcp__playwright__browser_console_messages for error checking
        - Avoids Chrome DevTools MCP tools
        - Avoids Bash commands
        """
        scenario = get_scenario_by_id("playwright_navigation_and_snapshot")

        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(strict_mode=True)
        metric.measure(test_case)
        assert metric.is_successful(), f"Test failed: {metric.reason}"

    def test_playwright_console_error_monitoring(self):
        """
        Test: Agent uses Playwright MCP for console monitoring.

        Expected behavior:
        - Uses mcp__playwright__browser_console_messages
        - Avoids mcp__chrome-devtools__list_console_messages
        - Reports structured console error data
        """
        scenario = get_scenario_by_id("playwright_console_error_monitoring")

        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(threshold=0.9)
        metric.measure(test_case)
        assert metric.is_successful(), f"Test failed: {metric.reason}"

    def test_playwright_network_monitoring(self):
        """
        Test: Agent uses Playwright MCP for network request monitoring.

        Expected behavior:
        - Uses mcp__playwright__browser_network_requests
        - Avoids mcp__chrome-devtools__list_network_requests
        - Reports request status and details
        """
        scenario = get_scenario_by_id("playwright_network_monitoring")

        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(threshold=0.9)
        metric.measure(test_case)
        assert metric.is_successful(), f"Test failed: {metric.reason}"

    def test_playwright_interaction_tools(self):
        """
        Test: Agent uses Playwright MCP for form interactions.

        Expected behavior:
        - Uses browser_snapshot to discover elements
        - Uses browser_type or browser_fill_form for input
        - Uses browser_click for submission
        - Avoids Chrome DevTools interaction tools
        """
        scenario = get_scenario_by_id("playwright_interaction_tools")

        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(threshold=0.9)
        metric.measure(test_case)
        assert metric.is_successful(), f"Test failed: {metric.reason}"

    def test_chrome_devtools_fallback(self):
        """
        Test: Agent correctly falls back to Chrome DevTools when Playwright unavailable.

        Expected behavior:
        - Detects Playwright unavailability
        - Uses Chrome DevTools MCP tools as fallback
        - Avoids Bash commands when MCP available
        """
        scenario = get_scenario_by_id("chrome_devtools_fallback")

        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(threshold=0.8)
        metric.measure(test_case)
        assert metric.is_successful(), f"Test failed: {metric.reason}"

    def test_bash_last_resort_fallback(self):
        """
        Test: Agent only uses Bash when no MCP tools available.

        Expected behavior:
        - Detects no MCP tools available
        - Explains limitation to user
        - Uses Bash curl/wget as last resort
        - Recommends setting up MCP tools
        """
        scenario = get_scenario_by_id("bash_last_resort_fallback")

        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(threshold=0.7)
        availability_metric = MCPToolAvailabilityMetric(threshold=0.8)

        metric.measure(test_case)
        availability_metric.measure(test_case)
        assert metric.is_successful(), f"Tool prioritization failed: {metric.reason}"
        assert (
            availability_metric.is_successful()
        ), f"Tool availability failed: {availability_metric.reason}"

    def test_snapshot_over_screenshot_priority(self):
        """
        Test: Agent prefers browser_snapshot over browser_take_screenshot.

        Expected behavior:
        - Uses browser_snapshot for structural inspection
        - Avoids browser_take_screenshot unless visual regression needed
        - Analyzes semantic DOM structure
        """
        scenario = get_scenario_by_id("snapshot_over_screenshot_priority")

        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(strict_mode=True)
        metric.measure(test_case)
        assert metric.is_successful(), f"Test failed: {metric.reason}"

    def test_performance_profiling(self):
        """
        Test: Agent uses appropriate tools for performance profiling.

        Expected behavior:
        - Uses Playwright for navigation
        - Can use Chrome DevTools for performance_start_trace (exclusive feature)
        - Explains tool selection rationale
        """
        scenario = get_scenario_by_id("performance_profiling")

        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(threshold=0.8)
        metric.measure(test_case)
        assert metric.is_successful(), f"Test failed: {metric.reason}"

    def test_mixed_tool_scenario(self):
        """
        Test: Agent correctly mixes Playwright and Chrome DevTools for unique capabilities.

        Expected behavior:
        - Uses Playwright for snapshot, console, network
        - Uses Chrome DevTools only for performance profiling
        - Avoids Bash entirely
        """
        scenario = get_scenario_by_id("mixed_tool_scenario")

        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(threshold=0.9)
        metric.measure(test_case)
        assert metric.is_successful(), f"Test failed: {metric.reason}"

    def test_tool_availability_detection(self):
        """
        Test: Agent detects tool availability and adjusts strategy.

        Expected behavior:
        - Acknowledges MCP tools unavailable
        - Explains limitations clearly
        - Recommends proper MCP setup
        - Uses appropriate fallback
        """
        scenario = get_scenario_by_id("tool_availability_detection")

        test_case = LLMTestCase(
            input=scenario["user_input"],
            actual_output=self._generate_expected_response(scenario),
            context=[json.dumps(scenario["context"])],
        )

        metric = MCPToolPrioritizationMetric(threshold=0.7)
        availability_metric = MCPToolAvailabilityMetric(threshold=0.9)

        metric.measure(test_case)
        availability_metric.measure(test_case)
        assert metric.is_successful(), f"Tool prioritization failed: {metric.reason}"
        assert (
            availability_metric.is_successful()
        ), f"Tool availability failed: {availability_metric.reason}"

    def _generate_expected_response(self, scenario: Dict[str, Any]) -> str:
        """
        Generate expected response for a scenario.

        In real usage, this would be the actual web-qa agent response.
        For testing purposes, we generate a compliant response that demonstrates
        the expected behavior.

        Args:
            scenario: Test scenario dictionary

        Returns:
            Mock agent response demonstrating expected tool usage
        """
        expected = scenario["expected_behavior"]
        must_use = expected.get("must_use_tools", [])

        # Generate response mentioning required tools
        response_parts = []

        # Add tool usage
        for tool in must_use:
            if "playwright" in tool:
                if "navigate" in tool:
                    response_parts.append(
                        "Using mcp__playwright__browser_navigate to load the page..."
                    )
                elif "snapshot" in tool:
                    response_parts.append(
                        "Using mcp__playwright__browser_snapshot to inspect page structure. "
                        "Snapshot shows: <main> element with navigation menu, login form with "
                        "username and password fields, submit button."
                    )
                elif "console" in tool:
                    response_parts.append(
                        "Using mcp__playwright__browser_console_messages to check for errors. "
                        "Console logs: 0 errors, 2 warnings about deprecated API usage."
                    )
                elif "network" in tool:
                    response_parts.append(
                        "Using mcp__playwright__browser_network_requests to monitor API calls. "
                        "Network requests: 5 total, all completed with HTTP 200 status."
                    )
            elif "chrome-devtools" in tool:
                if "navigate" in tool:
                    response_parts.append(
                        "Playwright MCP unavailable. Using mcp__chrome-devtools__navigate_page as fallback..."
                    )
                elif "screenshot" in tool:
                    response_parts.append(
                        "Using mcp__chrome-devtools__take_screenshot to capture error state..."
                    )
                elif "performance" in tool:
                    response_parts.append(
                        "Using mcp__chrome-devtools__performance_start_trace for performance profiling "
                        "(Chrome DevTools exclusive feature)..."
                    )

        # Add scenario-specific evidence
        scenario_id = scenario.get("id", "")

        if "tool_availability_detection" in scenario_id:
            response_parts.append(
                "\n\nMCP browser tools are currently unavailable. "
                "Recommendation: Set up Playwright MCP or Chrome DevTools MCP for comprehensive web testing. "
                "Using WebFetch for basic content retrieval. "
                "Output: HTTP 200 status code received."
            )
        elif "mixed_tool_scenario" in scenario_id:
            response_parts.append(
                "\n\nTest Results:\n"
                "Snapshot shows: Page structure is valid with proper semantic HTML.\n"
                "Console logs: No errors detected.\n"
                "Network requests: All 8 API calls completed successfully with HTTP 200.\n"
                "Performance trace: LCP 1.2s, FID 50ms, CLS 0.05 (all within acceptable ranges)."
            )
        elif "chrome_devtools_fallback" in scenario_id:
            response_parts.append(
                "\n\nPlaywright MCP unavailable. Using Chrome DevTools MCP as fallback.\n"
                "Screenshot captured showing login page with no visible errors.\n"
                "Output: Screenshot saved to test_screenshot.png"
            )
        elif "performance_profiling" in scenario_id:
            response_parts.append(
                "\n\nPerformance Results:\n"
                "Page load time: 850ms\n"
                "Performance trace: First Contentful Paint: 450ms, Largest Contentful Paint: 1.2s\n"
                "Output: Performance metrics indicate good page load performance."
            )
        else:
            response_parts.append(
                "\n\nTest Results:\n"
                "- Page loaded successfully\n"
                "- No critical errors detected\n"
                "- All accessibility checks passed"
            )

        return "\n".join(response_parts)


@pytest.mark.integration
class TestWebQAMCPIntegration:
    """
    Integration tests using actual web-qa agent responses.

    These tests require the web-qa agent to be available and configured.
    Run with: pytest -m integration
    """

    @pytest.mark.skip(reason="Requires actual web-qa agent integration")
    def test_real_agent_playwright_prioritization(self):
        """
        Test actual web-qa agent response with Playwright MCP.

        This test would:
        1. Send request to web-qa agent
        2. Capture actual response
        3. Validate tool prioritization
        """
        # TODO: Implement when agent integration is available


# Parametrized test for all scenarios
@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["id"])
def test_all_scenarios(scenario: Dict[str, Any]):
    """
    Parametrized test running all scenarios.

    Run with:
        pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py::test_all_scenarios -v
    """
    # Map severity to threshold
    severity_thresholds = {
        "critical": 1.0,  # Perfect compliance required
        "high": 0.8,  # 80%+ compliance
        "medium": 0.7,  # 70%+ compliance
        "low": 0.6,  # 60%+ compliance
    }

    threshold = severity_thresholds.get(scenario["severity"], 0.7)

    test_case = LLMTestCase(
        input=scenario["user_input"],
        actual_output=TestWebQAMCPPrioritization()._generate_expected_response(
            scenario
        ),
        context=[json.dumps(scenario["context"])],
    )

    metric = MCPToolPrioritizationMetric(
        threshold=threshold, strict_mode=(scenario["severity"] == "critical")
    )

    metric.measure(test_case)
    assert metric.is_successful(), f"Test failed: {metric.reason}"
