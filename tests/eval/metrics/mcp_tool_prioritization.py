"""
MCP Tool Prioritization Metric for Web-QA Agent Validation

Custom DeepEval metric to validate that web-qa agent correctly prioritizes:
1. Playwright MCP tools over Chrome DevTools MCP
2. MCP tools over Bash commands
3. browser_snapshot over browser_take_screenshot for inspection

This metric is critical for ensuring the web-qa agent follows the updated
tool prioritization guidelines from web-qa-mcp-browser-integration-2025-12-18.md
"""

from typing import Any, Dict, List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class MCPToolPrioritizationMetric(BaseMetric):
    """
    Validates MCP tool prioritization in web-qa agent responses.

    Scoring:
    - 1.0: Perfect prioritization (uses Playwright MCP when available)
    - 0.8: Good (uses Chrome DevTools MCP, Playwright unavailable)
    - 0.6: Acceptable (uses Bash, no MCP available)
    - 0.4: Poor (uses Chrome DevTools when Playwright available)
    - 0.2: Bad (uses Bash when MCP available)
    - 0.0: Failed (wrong tool selection or no evidence)
    """

    def __init__(
        self,
        threshold: float = 0.8,
        strict_mode: bool = False,
    ):
        """
        Initialize the MCP Tool Prioritization metric.

        Args:
            threshold: Minimum score required to pass (default: 0.8)
            strict_mode: If True, requires perfect prioritization (threshold ignored, must be 1.0)
        """
        self.threshold = 1.0 if strict_mode else threshold
        self.strict_mode = strict_mode
        self.score = 0.0
        self.reason = ""
        self.success = False

    @property
    def __name__(self) -> str:
        return "MCP Tool Prioritization"

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure MCP tool prioritization compliance.

        Args:
            test_case: DeepEval test case containing:
                - input: User request
                - actual_output: Agent response
                - context: List of context items including:
                    - available_tools: List of available tool patterns
                    - preferred_tools: List of tools that should be used

        Returns:
            Score between 0.0 and 1.0
        """
        response = test_case.actual_output

        # Extract context
        context = self._parse_context(test_case.context)
        available_tools = context.get("available_tools", [])
        preferred_tools = context.get("preferred_tools", [])
        must_use_tools = context.get("must_use_tools", [])
        must_not_use_tools = context.get("must_not_use_tools", [])

        # Parse agent response to detect tools used
        tools_used = self._extract_tools_from_response(response)

        violations = []
        score_adjustments = []

        # Check 1: Must-use tools validation
        for tool in must_use_tools:
            if not self._tool_used(tool, tools_used):
                violations.append(f"Missing required tool: {tool}")
                score_adjustments.append(-0.3)

        # Check 2: Must-not-use tools validation
        for tool in must_not_use_tools:
            if self._tool_used(tool, tools_used):
                violations.append(f"Used forbidden tool: {tool}")
                score_adjustments.append(-0.4)

        # Check 3: Playwright prioritization over Chrome DevTools
        playwright_available = any("playwright" in t.lower() for t in available_tools)
        chrome_devtools_used = any("chrome-devtools" in t.lower() for t in tools_used)

        if playwright_available and chrome_devtools_used:
            # Check if Chrome DevTools used for exclusive features (performance)
            performance_tools = [
                "performance_start_trace",
                "performance_stop_trace",
                "performance_analyze_insight",
            ]
            chrome_tools_used = [
                t for t in tools_used if "chrome-devtools" in t.lower()
            ]

            non_perf_chrome_tools = [
                t
                for t in chrome_tools_used
                if not any(perf in t for perf in performance_tools)
            ]

            if non_perf_chrome_tools:
                violations.append(
                    f"Used Chrome DevTools instead of Playwright: {', '.join(non_perf_chrome_tools)}"
                )
                score_adjustments.append(-0.3)

        # Check 4: Snapshot over screenshot priority
        screenshot_used = any("take_screenshot" in t.lower() for t in tools_used)
        snapshot_used = any("snapshot" in t.lower() for t in tools_used)

        # Check if context indicates this is an inspection task (not visual regression)
        inspection_keywords = [
            "inspect",
            "structure",
            "accessibility",
            "check",
            "verify",
            "analyze",
            "examine",
            "dom",
            "semantic",
        ]
        is_inspection = any(
            keyword in test_case.input.lower() for keyword in inspection_keywords
        )

        if is_inspection and screenshot_used and not snapshot_used:
            violations.append(
                "Used screenshot instead of snapshot for structural inspection"
            )
            score_adjustments.append(-0.2)

        # Check 5: Bash usage when MCP available
        bash_used = any("bash" in t.lower() or "curl" in t.lower() for t in tools_used)
        mcp_available = any("mcp__" in t for t in available_tools)

        if bash_used and mcp_available:
            violations.append("Used Bash commands when MCP tools available")
            score_adjustments.append(-0.4)

        # Check 6: Evidence requirement
        has_evidence = self._has_evidence(response)
        if not has_evidence:
            violations.append("No concrete evidence from tool outputs")
            score_adjustments.append(-0.3)

        # Calculate final score
        base_score = 1.0
        final_score = base_score + sum(score_adjustments)
        final_score = max(0.0, min(1.0, final_score))

        self.score = final_score
        self.success = final_score >= self.threshold

        if violations:
            self.reason = f"Tool prioritization violations: {'; '.join(violations)}"
        else:
            self.reason = "Perfect MCP tool prioritization"

        return self.score

    def is_successful(self) -> bool:
        """Return whether the test passed the threshold."""
        return self.success

    def _parse_context(self, context: Optional[List[str]]) -> Dict[str, Any]:
        """
        Parse context list into structured data.

        Args:
            context: List of context strings or dicts

        Returns:
            Dict with parsed context data
        """
        if not context:
            return {}

        result = {}

        for item in context:
            if isinstance(item, dict):
                result.update(item)
            elif isinstance(item, str):
                # Try to parse as JSON
                import json

                try:
                    parsed = json.loads(item)
                    if isinstance(parsed, dict):
                        result.update(parsed)
                except (json.JSONDecodeError, ValueError):
                    pass

        return result

    def _extract_tools_from_response(self, response: str) -> List[str]:
        """
        Extract tool names from agent response.

        Args:
            response: Agent response text

        Returns:
            List of tool names detected in response
        """
        tools = []

        # Common tool patterns
        tool_patterns = {
            # Playwright MCP
            "mcp__playwright__browser_navigate": [
                "browser_navigate",
                "playwright.*navigate",
            ],
            "mcp__playwright__browser_snapshot": [
                "browser_snapshot",
                "playwright.*snapshot",
            ],
            "mcp__playwright__browser_console_messages": [
                "browser_console_messages",
                "playwright.*console",
            ],
            "mcp__playwright__browser_network_requests": [
                "browser_network_requests",
                "playwright.*network",
            ],
            "mcp__playwright__browser_take_screenshot": [
                "browser_take_screenshot",
                "playwright.*screenshot",
            ],
            "mcp__playwright__browser_click": ["browser_click", "playwright.*click"],
            "mcp__playwright__browser_type": ["browser_type", "playwright.*type"],
            "mcp__playwright__browser_fill_form": [
                "browser_fill_form",
                "playwright.*fill",
            ],
            # Chrome DevTools MCP
            "mcp__chrome-devtools__navigate_page": [
                "navigate_page",
                "chrome.*navigate",
            ],
            "mcp__chrome-devtools__take_snapshot": [
                "take_snapshot",
                "chrome.*snapshot",
            ],
            "mcp__chrome-devtools__take_screenshot": [
                "take_screenshot",
                "chrome.*screenshot",
            ],
            "mcp__chrome-devtools__list_console_messages": [
                "list_console_messages",
                "chrome.*console",
            ],
            "mcp__chrome-devtools__list_network_requests": [
                "list_network_requests",
                "chrome.*network",
            ],
            "mcp__chrome-devtools__performance_start_trace": [
                "performance_start_trace"
            ],
            "mcp__chrome-devtools__performance_stop_trace": ["performance_stop_trace"],
            # Bash commands
            "Bash": ["bash:", "curl ", "wget "],
        }

        import re

        response_lower = response.lower()

        for tool_name, patterns in tool_patterns.items():
            for pattern in patterns:
                if re.search(pattern, response_lower):
                    tools.append(tool_name)
                    break

        return tools

    def _tool_used(self, tool_pattern: str, tools_used: List[str]) -> bool:
        """
        Check if a tool matching the pattern was used.

        Args:
            tool_pattern: Tool name or pattern (e.g., "mcp__playwright__*")
            tools_used: List of tools detected in response

        Returns:
            True if tool pattern matches any used tool
        """
        if "*" in tool_pattern:
            # Wildcard pattern
            prefix = tool_pattern.replace("*", "")
            return any(tool.startswith(prefix) for tool in tools_used)
        # Exact match
        return tool_pattern in tools_used

    def _has_evidence(self, response: str) -> bool:
        """
        Check if response contains concrete evidence from tool outputs.

        Args:
            response: Agent response text

        Returns:
            True if evidence detected
        """
        evidence_indicators = [
            "console logs:",
            "network requests:",
            "snapshot shows:",
            "page structure:",
            "found errors:",
            "http status",
            "response:",
            "output:",
            "result:",
            "detected:",
        ]

        response_lower = response.lower()
        return any(indicator in response_lower for indicator in evidence_indicators)


class MCPToolAvailabilityMetric(BaseMetric):
    """
    Validates that agent correctly detects and reports MCP tool availability.

    Scoring:
    - 1.0: Correctly identifies available tools and adjusts strategy
    - 0.5: Partially correct (identifies some tools)
    - 0.0: Fails to detect tool availability
    """

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""
        self.success = False

    @property
    def __name__(self) -> str:
        return "MCP Tool Availability Detection"

    def measure(self, test_case: LLMTestCase) -> float:
        """Measure tool availability detection accuracy."""
        response = test_case.actual_output

        # Extract expected availability from context
        context = self._parse_context(test_case.context)
        playwright_available = context.get("playwright_available", True)
        chrome_devtools_available = context.get("chrome_devtools_available", True)

        response_lower = response.lower()

        violations = []

        # Check if agent acknowledges tool unavailability
        if not playwright_available:
            if "playwright" not in response_lower:
                # Should mention Playwright unavailability or use fallback
                if not any(
                    word in response_lower
                    for word in ["chrome", "devtools", "bash", "curl"]
                ):
                    violations.append(
                        "Did not acknowledge Playwright unavailability or use fallback"
                    )

        if not chrome_devtools_available and not playwright_available:
            if not any(
                word in response_lower
                for word in ["bash", "curl", "wget", "limited", "unavailable"]
            ):
                violations.append("Did not acknowledge MCP tool unavailability")

        # Calculate score
        if not violations:
            self.score = 1.0
            self.reason = "Correctly detected and adapted to tool availability"
        else:
            self.score = 0.0
            self.reason = f"Tool availability issues: {'; '.join(violations)}"

        self.success = self.score >= self.threshold
        return self.score

    def is_successful(self) -> bool:
        return self.success

    def _parse_context(self, context: Optional[List[str]]) -> Dict[str, Any]:
        """Parse context into structured data."""
        if not context:
            return {}

        result = {}
        for item in context:
            if isinstance(item, dict):
                result.update(item)

        return result
