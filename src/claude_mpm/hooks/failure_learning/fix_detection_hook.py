#!/usr/bin/env python3
"""
Fix Detection Hook
==================

Detects when previously failed tasks succeed, indicating a fix has been applied.

WHY: Detecting fixes is the second step in the failure-learning cycle. When a
task that previously failed now succeeds, we know a fix was applied. Matching
fixes with failures creates the foundation for learning extraction.

DESIGN DECISION: This hook runs after failure detection (priority=87) to check
if successful tool executions resolve previous failures. Uses the FailureTracker
to match fixes with failures.

Integration points:
- Monitors successful tool executions (exit_code=0)
- Matches with previously detected failures by task type
- Marks failures as fixed in FailureTracker
- Triggers learning extraction for failure-fix pairs
"""

import logging
from typing import Any, Dict

from claude_mpm.hooks.base_hook import BaseHook, HookContext, HookResult, HookType
from claude_mpm.services.memory.failure_tracker import get_failure_tracker

logger = logging.getLogger(__name__)


class FixDetectionHook(BaseHook):
    """Hook that detects when failures are fixed.

    WHY: Automatically matches successful executions with previous failures.
    This enables automatic learning extraction without manual intervention.

    DESIGN DECISION: Priority 87 ensures this runs after failure detection
    but before learning extraction. The sequencing is critical:
    1. Failure detection (85)
    2. Fix detection (87)
    3. Learning extraction (89)
    """

    # Tools to monitor for fixes
    MONITORED_TOOLS = [
        "Bash",  # Command execution
        "NotebookEdit",  # Jupyter notebook execution
        "Task",  # Subagent delegation
    ]

    def __init__(self):
        """Initialize the fix detection hook."""
        super().__init__(
            name="fix_detection",
            priority=87,  # After failure detection, before learning extraction
        )
        self.tracker = get_failure_tracker()

    def execute(self, context: HookContext) -> HookResult:
        """Execute fix detection on successful tool execution.

        WHY: When a tool succeeds, check if it fixes a previous failure.
        This creates failure-fix pairs that can be used for learning extraction.

        Args:
            context: Hook context containing tool execution data

        Returns:
            HookResult with detection results
        """
        try:
            # Extract tool execution data
            tool_name = context.data.get("tool_name")
            exit_code = context.data.get("exit_code", 0)

            # Only process monitored tools
            if tool_name not in self.MONITORED_TOOLS:
                return HookResult(success=True, modified=False)

            # Only process successful executions
            if exit_code != 0:
                return HookResult(success=True, modified=False)

            # Check if there are any unfixed failures to potentially match
            unfixed_failures = self.tracker.get_unfixed_failures()
            if not unfixed_failures:
                # No failures to fix, skip
                return HookResult(success=True, modified=False)

            # Attempt to detect a fix
            tool_output = self._extract_tool_output(context.data)
            fix_context = self._build_fix_context(context)

            fix_result = self.tracker.detect_fix(
                tool_name=tool_name,
                tool_output=tool_output,
                exit_code=exit_code,
                context=fix_context,
            )

            if fix_result:
                fix_event, failure_event = fix_result
                logger.info(
                    f"Fix detected: {failure_event.task_type} - "
                    f"resolved failure {failure_event.task_id}"
                )

                # Store fix info in metadata for learning extraction hook
                return HookResult(
                    success=True,
                    modified=False,
                    metadata={
                        "fix_detected": True,
                        "failure_id": failure_event.task_id,
                        "fix_event": fix_event,
                        "failure_event": failure_event,
                    },
                )

            return HookResult(success=True, modified=False)

        except Exception as e:
            logger.error(f"Error in fix detection hook: {e}", exc_info=True)
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
        output = data.get("output") or data.get("result") or data.get("stdout") or ""

        # Handle nested result structures
        if isinstance(output, dict):
            output = output.get("output") or output.get("content") or str(output)

        return str(output) if output else ""

    def _build_fix_context(self, context: HookContext) -> Dict[str, str]:
        """Build context dictionary for fix event.

        Args:
            context: Hook context

        Returns:
            Context dictionary with agent, session, and other info
        """
        fix_context = {}

        # Extract relevant context fields
        if context.session_id:
            fix_context["session_id"] = context.session_id

        # Extract agent info
        agent_type = (
            context.data.get("agent_type")
            or context.data.get("subagent_type")
            or context.metadata.get("agent_type")
        )
        if agent_type:
            fix_context["agent_type"] = agent_type

        # Extract command/script info for Bash tool
        if context.data.get("tool_name") == "Bash":
            command = context.data.get("command") or context.data.get(
                "tool_input", {}
            ).get("command")
            if command:
                fix_context["command"] = command

        # Extract working directory
        working_dir = context.data.get("working_directory") or context.data.get("cwd")
        if working_dir:
            fix_context["working_dir"] = working_dir

        return fix_context


def get_fix_detection_hook() -> FixDetectionHook:
    """Factory function to create fix detection hook.

    WHY: Provides consistent hook creation pattern used throughout the framework.

    Returns:
        Configured FixDetectionHook instance
    """
    return FixDetectionHook()
