#!/usr/bin/env python3
"""
Failure Tracker Service
=======================

Session-level state manager for tracking failures and their fixes to enable
automatic learning extraction.

WHY: When tasks fail and agents fix them, we need to track these failure-fix
pairs to extract learnings. This service provides in-memory session tracking
without requiring database or filesystem persistence.

DESIGN DECISION: Session-scoped tracking keeps the MVP simple. Failures are
tracked during a session, matched with fixes, and learnings are extracted
before session end. No persistent storage needed for MVP.

Architecture:
- Failure events: Captured from tool outputs (errors, exceptions, test failures)
- Fix events: Detected when same task type succeeds after failure
- Learning synthesis: Template-based extraction from failure-fix pairs
- Memory routing: Direct learnings to appropriate agent memory files

Example flow:
1. Bash tool returns error → FailureEvent created
2. User or agent makes changes
3. Bash tool succeeds → Fix detected, matched with failure
4. Learning extracted and written to agent memory
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FailureEvent:
    """Represents a detected task failure.

    Attributes:
        task_id: Unique identifier for this failure event
        task_type: Type of task that failed (bash, test, build, etc.)
        tool_name: Name of tool that failed (Bash, NotebookEdit, etc.)
        error_message: The actual error message
        context: Additional context (agent, session, working_dir, etc.)
        timestamp: When the failure occurred
        fixed: Whether this failure has been fixed
        fix_timestamp: When the fix occurred (if fixed)
    """

    task_id: str
    task_type: str
    tool_name: str
    error_message: str
    context: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fixed: bool = False
    fix_timestamp: Optional[datetime] = None

    def mark_fixed(self) -> None:
        """Mark this failure as fixed."""
        self.fixed = True
        self.fix_timestamp = datetime.now(timezone.utc)


@dataclass
class FixEvent:
    """Represents a detected fix for a previous failure.

    Attributes:
        task_type: Type of task that succeeded
        tool_name: Name of tool that succeeded
        success_message: Output from successful execution
        context: Additional context
        timestamp: When the fix occurred
        matched_failure: The failure event this fix resolves
    """

    task_type: str
    tool_name: str
    success_message: str
    context: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    matched_failure: Optional[FailureEvent] = None


@dataclass
class Learning:
    """Represents an extracted learning from a failure-fix pair.

    Attributes:
        category: Learning category (error-handling, testing, configuration, etc.)
        problem: Description of the original problem
        solution: Description of the solution
        context: Task context (tool, agent, etc.)
        target_agent: Which agent should receive this learning
        failure_event: The original failure
        fix_event: The fix that resolved it
        timestamp: When the learning was extracted
    """

    category: str
    problem: str
    solution: str
    context: Dict[str, str]
    target_agent: str
    failure_event: FailureEvent
    fix_event: FixEvent
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_markdown(self) -> str:
        """Format learning as markdown for memory file.

        Returns:
            Markdown-formatted learning entry
        """
        return (
            f"## {self.category}\n"
            f"- **Problem**: {self.problem}\n"
            f"- **Solution**: {self.solution}\n"
            f"- **Context**: {', '.join(f'{k}: {v}' for k, v in self.context.items())}\n"
            f"- **Date**: {self.timestamp.strftime('%Y-%m-%d')}\n"
        )


class FailureTracker:
    """Session-level tracker for failures, fixes, and learnings.

    WHY: Provides centralized state management for the failure-learning system.
    Hooks interact with this tracker to record failures, detect fixes, and
    extract learnings.

    DESIGN DECISION: In-memory session tracking is sufficient for MVP. Each
    session maintains its own failure history. When a fix is detected, we
    search for matching failures and create learning pairs.
    """

    # Failure detection patterns (ordered from most specific to least specific)
    ERROR_PATTERNS = [
        (r"SyntaxError: (.+)", "syntax-error"),
        (r"TypeError: (.+)", "type-error"),
        (r"ImportError: (.+)", "import-error"),
        (r"ModuleNotFoundError: (.+)", "module-not-found"),
        (r"FileNotFoundError: (.+)", "file-not-found"),
        (r"FAILED (.+)", "test-failure"),
        (r"✗ (.+) failed", "test-failure"),
        (r"(\d+) failed", "test-failure"),
        (r"Exception: (.+)", "exception"),
        (r"Command failed: (.+)", "command-error"),
        (r"Error: (.+)", "error"),  # Generic error - match last
    ]

    # Task type classification patterns
    TASK_TYPE_PATTERNS = {
        "test": [r"pytest", r"test", r"\.test\.py", r"tests/"],
        "build": [r"make", r"build", r"compile", r"setup\.py"],
        "lint": [r"lint", r"flake8", r"mypy", r"black", r"isort", r"ruff"],
        "git": [r"git ", r"commit", r"push", r"pull", r"merge"],
        "install": [r"pip install", r"npm install", r"yarn", r"poetry"],
        "script": [r"\.sh", r"\.py", r"\.js", r"script"],
    }

    def __init__(self):
        """Initialize the failure tracker."""
        self.failures: List[FailureEvent] = []
        self.fixes: List[FixEvent] = []
        self.learnings: List[Learning] = []
        self.session_id = datetime.now(timezone.utc).isoformat()

    def detect_failure(
        self, tool_name: str, tool_output: str, context: Optional[Dict[str, str]] = None
    ) -> Optional[FailureEvent]:
        """Detect if tool output contains a failure.

        WHY: Failures can occur in many forms (errors, exceptions, test failures).
        This method uses regex patterns to identify failures and extract relevant
        error messages.

        Args:
            tool_name: Name of the tool that executed
            tool_output: Output from the tool
            context: Additional context (agent, session, etc.)

        Returns:
            FailureEvent if failure detected, None otherwise
        """
        if not tool_output:
            return None

        context = context or {}

        # Check each error pattern
        for pattern, error_type in self.ERROR_PATTERNS:
            match = re.search(pattern, tool_output, re.MULTILINE | re.IGNORECASE)
            if match:
                error_message = match.group(1) if match.lastindex else match.group(0)

                # Classify task type
                task_type = self._classify_task_type(tool_output, context)

                # Create failure event
                task_id = f"{task_type}_{len(self.failures)}_{int(datetime.now(timezone.utc).timestamp())}"
                failure = FailureEvent(
                    task_id=task_id,
                    task_type=task_type,
                    tool_name=tool_name,
                    error_message=error_message.strip(),
                    context={
                        **context,
                        "error_type": error_type,
                        "output_preview": tool_output[:200],
                    },
                )

                self.failures.append(failure)
                logger.info(f"Detected failure: {task_type} - {error_message[:50]}...")
                return failure

        return None

    def detect_fix(
        self,
        tool_name: str,
        tool_output: str,
        exit_code: int = 0,
        context: Optional[Dict[str, str]] = None,
    ) -> Optional[Tuple[FixEvent, FailureEvent]]:
        """Detect if a successful execution fixes a previous failure.

        WHY: When a task succeeds, it might be fixing a previous failure of the
        same task type. This method matches successful executions with recent
        failures to detect fixes.

        Args:
            tool_name: Name of the tool that succeeded
            tool_output: Output from the tool
            exit_code: Exit code (0 = success)
            context: Additional context

        Returns:
            Tuple of (FixEvent, matched FailureEvent) if fix detected, None otherwise
        """
        # Only consider successful executions
        if exit_code != 0:
            return None

        context = context or {}
        task_type = self._classify_task_type(tool_output, context)

        # Find matching unfixed failure
        matching_failure = self._find_matching_failure(task_type, tool_name)
        if not matching_failure:
            return None

        # Create fix event
        fix = FixEvent(
            task_type=task_type,
            tool_name=tool_name,
            success_message=tool_output[:200] if tool_output else "Success",
            context=context,
            matched_failure=matching_failure,
        )

        # Mark failure as fixed
        matching_failure.mark_fixed()
        self.fixes.append(fix)

        logger.info(f"Detected fix for {task_type} failure: {matching_failure.task_id}")
        return (fix, matching_failure)

    def extract_learning(
        self,
        fix_event: FixEvent,
        failure_event: FailureEvent,
        target_agent: Optional[str] = None,
    ) -> Learning:
        """Extract learning from a failure-fix pair.

        WHY: When we have a failure and its fix, we can synthesize a learning
        that captures the problem-solution pair for future reference.

        DESIGN DECISION: MVP uses template-based extraction (no AI). The learning
        format is simple and actionable, ready for agent memory files.

        Args:
            fix_event: The fix that resolved the failure
            failure_event: The original failure
            target_agent: Which agent should receive this learning (auto-detected if None)

        Returns:
            Learning object with extracted knowledge
        """
        # Auto-detect target agent if not specified
        if not target_agent:
            target_agent = self._determine_target_agent(failure_event, fix_event)

        # Categorize the learning
        category = self._categorize_learning(failure_event)

        # Extract problem and solution descriptions
        problem = self._extract_problem_description(failure_event)
        solution = self._extract_solution_description(fix_event, failure_event)

        # Build context
        learning_context = {
            "task_type": failure_event.task_type,
            "tool": failure_event.tool_name,
            "error_type": failure_event.context.get("error_type", "unknown"),
        }

        # Add agent context if available
        if "agent_type" in failure_event.context:
            learning_context["agent"] = failure_event.context["agent_type"]

        learning = Learning(
            category=category,
            problem=problem,
            solution=solution,
            context=learning_context,
            target_agent=target_agent,
            failure_event=failure_event,
            fix_event=fix_event,
        )

        self.learnings.append(learning)
        logger.info(f"Extracted learning for {target_agent}: {category}")
        return learning

    def get_unfixed_failures(self) -> List[FailureEvent]:
        """Get all failures that haven't been fixed yet.

        Returns:
            List of unfixed failure events
        """
        return [f for f in self.failures if not f.fixed]

    def get_learnings_for_agent(self, agent_id: str) -> List[Learning]:
        """Get all learnings targeted for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of learnings for that agent
        """
        return [l for l in self.learnings if l.target_agent == agent_id]

    def get_session_stats(self) -> Dict[str, int]:
        """Get statistics for the current session.

        Returns:
            Dict with failure/fix/learning counts
        """
        return {
            "total_failures": len(self.failures),
            "fixed_failures": len([f for f in self.failures if f.fixed]),
            "unfixed_failures": len([f for f in self.failures if not f.fixed]),
            "total_fixes": len(self.fixes),
            "total_learnings": len(self.learnings),
        }

    def _classify_task_type(self, output: str, context: Dict[str, str]) -> str:
        """Classify the task type based on output and context.

        Args:
            output: Tool output
            context: Additional context

        Returns:
            Task type string (test, build, lint, etc.)
        """
        # Check context first
        if "command" in context:
            command = context["command"].lower()
            for task_type, patterns in self.TASK_TYPE_PATTERNS.items():
                if any(
                    re.search(pattern, command, re.IGNORECASE) for pattern in patterns
                ):
                    return task_type

        # Check output
        output_lower = output.lower()
        for task_type, patterns in self.TASK_TYPE_PATTERNS.items():
            if any(
                re.search(pattern, output_lower, re.IGNORECASE) for pattern in patterns
            ):
                return task_type

        # Default to general execution
        return "execution"

    def _find_matching_failure(
        self, task_type: str, tool_name: str
    ) -> Optional[FailureEvent]:
        """Find the most recent unfixed failure matching the task type.

        Args:
            task_type: Type of task
            tool_name: Tool name

        Returns:
            Matching FailureEvent or None
        """
        # Search in reverse chronological order
        for failure in reversed(self.failures):
            if (
                not failure.fixed
                and failure.task_type == task_type
                and failure.tool_name == tool_name
            ):
                return failure

        # If no exact match, try matching just tool_name for generic tasks
        if task_type == "execution":
            for failure in reversed(self.failures):
                if not failure.fixed and failure.tool_name == tool_name:
                    return failure

        return None

    def _determine_target_agent(
        self, failure_event: FailureEvent, fix_event: FixEvent
    ) -> str:
        """Determine which agent should receive the learning.

        Args:
            failure_event: The failure
            fix_event: The fix

        Returns:
            Agent identifier (PM, engineer, qa, etc.)
        """
        # Check if agent was involved in the context
        if "agent_type" in failure_event.context:
            return failure_event.context["agent_type"]

        if "agent_type" in fix_event.context:
            return fix_event.context["agent_type"]

        # Route by task type
        task_type = failure_event.task_type
        if task_type in ("test", "lint"):
            return "qa"
        if task_type in ("build", "install", "script") or task_type == "git":
            return "engineer"
        # Default to PM for general learnings
        return "PM"

    def _categorize_learning(self, failure_event: FailureEvent) -> str:
        """Categorize the learning based on failure type.

        Args:
            failure_event: The failure event

        Returns:
            Category string
        """
        error_type = failure_event.context.get("error_type", "unknown")
        task_type = failure_event.task_type

        # Map error types to categories
        category_map = {
            "test-failure": "Testing",
            "syntax-error": "Code Quality",
            "type-error": "Code Quality",
            "import-error": "Dependencies",
            "module-not-found": "Dependencies",
            "file-not-found": "File Management",
            "command-error": "Configuration",
            "error": "Error Handling",
            "exception": "Error Handling",
        }

        # Try error type first
        if error_type in category_map:
            return category_map[error_type]

        # Try task type
        task_category_map = {
            "test": "Testing",
            "build": "Build Process",
            "lint": "Code Quality",
            "git": "Version Control",
            "install": "Dependencies",
        }

        if task_type in task_category_map:
            return task_category_map[task_type]

        return "General"

    def _extract_problem_description(self, failure_event: FailureEvent) -> str:
        """Extract a concise problem description from the failure.

        Args:
            failure_event: The failure event

        Returns:
            Problem description string
        """
        error_msg = failure_event.error_message
        task_type = failure_event.task_type

        # Truncate long error messages
        if len(error_msg) > 100:
            error_msg = error_msg[:97] + "..."

        return f"{task_type.capitalize()} failed: {error_msg}"

    def _extract_solution_description(
        self, fix_event: FixEvent, failure_event: FailureEvent
    ) -> str:
        """Extract a solution description from the fix.

        WHY: We want to capture what changed between failure and fix.
        For MVP, we use a simple heuristic based on the time gap.

        Args:
            fix_event: The fix event
            failure_event: The failure event

        Returns:
            Solution description string
        """
        # Calculate time between failure and fix
        time_delta = fix_event.timestamp - failure_event.timestamp
        time_str = f"{int(time_delta.total_seconds())}s"

        # Generic solution description for MVP
        # In future versions, this could analyze git diff, file changes, etc.
        return f"Fixed after {time_str} - verified with successful {fix_event.task_type} execution"


# Singleton instance for session-level tracking
_tracker_instance: Optional[FailureTracker] = None
_tracker_lock = threading.Lock()


def get_failure_tracker() -> FailureTracker:
    """Get or create the singleton FailureTracker instance.

    WHY: Session-level tracking requires a singleton to maintain state
    across multiple hook invocations during the same session.

    Thread-safe implementation using double-checked locking pattern to
    prevent race conditions during concurrent initialization.

    Returns:
        The FailureTracker singleton instance
    """
    global _tracker_instance

    # Fast path - check without lock
    if _tracker_instance is not None:
        return _tracker_instance

    # Slow path - acquire lock and double-check
    with _tracker_lock:
        if _tracker_instance is None:
            _tracker_instance = FailureTracker()
        return _tracker_instance


def reset_failure_tracker() -> None:
    """Reset the failure tracker (for testing or session restart).

    WHY: Tests need to reset state between runs. Also useful for
    explicitly starting a new tracking session.

    Thread-safe implementation ensures proper cleanup.
    """
    global _tracker_instance
    with _tracker_lock:
        _tracker_instance = None
