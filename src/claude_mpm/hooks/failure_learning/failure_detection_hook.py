#!/usr/bin/env python3
"""
Failure Detection Hook
======================

Detects task failures from tool outputs and registers them with the FailureTracker.

WHY: Failures are the first step in the failure-learning cycle. By detecting
failures early, we can match them with fixes later and extract valuable learnings.

DESIGN DECISION: This hook runs after tool execution (priority=85) to inspect
tool outputs for failure patterns. It integrates with the PostDelegationHook
lifecycle to access tool execution results.

Integration points:
- Monitors post_tool events for Bash, NotebookEdit, and other execution tools
- Extracts error messages, exceptions, and test failures
- Registers failures with FailureTracker for fix matching
"""

import logging
from typing import Any, Dict

from claude_mpm.hooks.base_hook import BaseHook, HookContext, HookResult, HookType
from claude_mpm.services.memory.failure_tracker import get_failure_tracker

logger = logging.getLogger(__name__)


class FailureDetectionHook(BaseHook):
    """Hook that detects and tracks task failures.

    WHY: Automatically captures failures without requiring manual tracking.
    Runs after tool execution to inspect outputs and detect error patterns.

    DESIGN DECISION: Priority 85 ensures this runs after tool execution but
    before fix detection and learning extraction. This ordering is critical
    for the failure-learning cycle.
    """

    # Tools to monitor for failures
    MONITORED_TOOLS = [
        "Bash",  # Command execution
        "NotebookEdit",  # Jupyter notebook execution
        "Task",  # Subagent delegation
    ]

    def __init__(self):
        """Initialize the failure detection hook."""
        super().__init__(
            name="failure_detection",
            priority=85,  # After tool execution, before fix detection
        )
        self.tracker = get_failure_tracker()

    def execute(self, context: HookContext) -> HookResult:
        """Execute failure detection on tool output.

        WHY: Inspects tool execution results to identify failures. When a failure
        is detected, it's registered with the FailureTracker for later matching
        with fixes.

        Args:
            context: Hook context containing tool execution data

        Returns:
            HookResult with detection results
        """
        try:
            # Extract tool execution data
            tool_name = context.data.get("tool_name")
            tool_output = self._extract_tool_output(context.data)
            exit_code = context.data.get("exit_code", 0)

            # Only process monitored tools
            if tool_name not in self.MONITORED_TOOLS:
                return HookResult(success=True, modified=False)

            # Skip if tool succeeded
            if exit_code == 0 and not self._contains_failure_indicators(tool_output):
                return HookResult(success=True, modified=False)

            # Detect failure
            failure_context = self._build_failure_context(context)
            failure = self.tracker.detect_failure(
                tool_name=tool_name, tool_output=tool_output, context=failure_context
            )

            if failure:
                logger.info(
                    f"Failure detected: {failure.task_type} - "
                    f"{failure.error_message[:50]}..."
                )
                return HookResult(
                    success=True,
                    modified=False,
                    metadata={"failure_detected": True, "failure_id": failure.task_id},
                )

            return HookResult(success=True, modified=False)

        except Exception as e:
            logger.error(f"Error in failure detection hook: {e}", exc_info=True)
            return HookResult(success=False, error=str(e), modified=False)

    def validate(self, context: HookContext) -> bool:
        """Validate if this hook should run for the given context.

        Args:
            context: Hook context to validate

        Returns:
            True if hook should execute
        """
        if not super().validate(context):
            return False

        # Run for POST_DELEGATION events (after tool execution)
        if context.hook_type != HookType.POST_DELEGATION:
            return False

        # Must have tool execution data
        return "tool_name" in context.data

    def _extract_tool_output(self, data: Dict[str, Any]) -> str:
        """Extract tool output from event data.

        Args:
            data: Event data dictionary

        Returns:
            Tool output string
        """
        # Try various output fields
        output = (
            data.get("output")
            or data.get("result")
            or data.get("error_output")
            or data.get("stderr")
            or ""
        )

        # Handle nested result structures
        if isinstance(output, dict):
            output = (
                output.get("output")
                or output.get("content")
                or output.get("error")
                or str(output)
            )

        return str(output) if output else ""

    def _contains_failure_indicators(self, output: str) -> bool:
        """Check if output contains failure indicators even if exit_code is 0.

        WHY: Some tools return 0 exit code but still report failures in output
        (e.g., test runners that catch exceptions).

        Args:
            output: Tool output

        Returns:
            True if failure indicators found
        """
        if not output:
            return False

        failure_keywords = [
            "error:",
            "exception:",
            "failed",
            "failure",
            "traceback",
            "✗",
            "❌",
        ]

        output_lower = output.lower()
        return any(keyword in output_lower for keyword in failure_keywords)

    def _build_failure_context(self, context: HookContext) -> Dict[str, str]:
        """Build context dictionary for failure event.

        Args:
            context: Hook context

        Returns:
            Context dictionary with agent, session, and other info
        """
        failure_context = {}

        # Extract relevant context fields
        if context.session_id:
            failure_context["session_id"] = context.session_id

        # Extract agent info from data or metadata
        agent_type = (
            context.data.get("agent_type")
            or context.data.get("subagent_type")
            or context.metadata.get("agent_type")
        )
        if agent_type:
            failure_context["agent_type"] = agent_type

        # Extract command/script info for Bash tool
        if context.data.get("tool_name") == "Bash":
            command = context.data.get("command") or context.data.get(
                "tool_input", {}
            ).get("command")
            if command:
                failure_context["command"] = command

        # Extract working directory
        working_dir = context.data.get("working_directory") or context.data.get("cwd")
        if working_dir:
            failure_context["working_dir"] = working_dir

        return failure_context


def get_failure_detection_hook() -> FailureDetectionHook:
    """Factory function to create failure detection hook.

    WHY: Provides consistent hook creation pattern used throughout the framework.

    Returns:
        Configured FailureDetectionHook instance
    """
    return FailureDetectionHook()
