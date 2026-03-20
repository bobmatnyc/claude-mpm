"""
PM v0012 Rules Metrics for DeepEval.

Two new metrics enforcing PM instruction rules introduced in v0012:

1. GhCliDelegationMetric
   Enforces the absolute prohibition on PM calling gh CLI commands directly.
   Any of:  gh issue list, gh issue view, gh pr view, gh pr list, gh pr diff
   must be delegated to the "ticketing" or "version-control" agent via the
   Task tool.  Threshold 1.0 (zero tolerance).

2. BashCapMetric
   Enforces the bash-command cap: PM must not execute more than 3 Bash tool
   invocations in a single response without an intervening Task delegation.
   Threshold 0.9.
"""

import re
from typing import Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

# ---------------------------------------------------------------------------
# GhCliDelegationMetric
# ---------------------------------------------------------------------------

# gh subcommands the PM is absolutely forbidden to call directly
_GH_FORBIDDEN_PATTERNS = [
    r"\bgh\s+issue\s+list\b",
    r"\bgh\s+issue\s+view\b",
    r"\bgh\s+pr\s+view\b",
    r"\bgh\s+pr\s+list\b",
    r"\bgh\s+pr\s+diff\b",
]

# Task tool delegation to an acceptable agent
_TASK_DELEGATION_PATTERN = re.compile(
    r'Task\s*\(\s*agent\s*=\s*[\'"](?:ticketing|version-control)[\'"]',
    re.IGNORECASE,
)


class GhCliDelegationMetric(BaseMetric):
    """
    DeepEval metric enforcing the gh-CLI delegation rule from PM v0012.

    PM MUST NOT use gh issue list / view, gh pr view / list / diff as direct
    tool calls.  Any such operation must be performed by delegating to the
    "ticketing" or "version-control" agent via the Task tool.

    Scoring:
    - 1.0: No forbidden gh calls detected in the response.
    - 0.0: One or more forbidden gh calls detected (zero tolerance).

    Threshold: 1.0
    """

    def __init__(self, threshold: float = 1.0) -> None:
        self.threshold = threshold
        self.score: float = 0.0
        self.reason: str = ""
        self.success: bool = False

    @property
    def __name__(self) -> str:
        return "GH CLI Delegation"

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Check actual_output for forbidden gh CLI direct calls.

        Returns:
            1.0 if no violation detected, 0.0 on first violation found.
        """
        output = test_case.actual_output or ""

        # Check for any forbidden gh CLI pattern
        for pattern in _GH_FORBIDDEN_PATTERNS:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                self.score = 0.0
                self.reason = (
                    f"VIOLATION: PM called '{match.group().strip()}' directly. "
                    "gh CLI read commands must be delegated to the ticketing or "
                    "version-control agent via the Task tool."
                )
                self.success = False
                return 0.0

        # No forbidden pattern found
        self.score = 1.0
        self.reason = "No forbidden gh CLI direct calls detected."
        self.success = True
        return 1.0

    def is_successful(self) -> bool:
        return self.success

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)


# ---------------------------------------------------------------------------
# BashCapMetric
# ---------------------------------------------------------------------------

# Matches a single Bash tool invocation opening
_BASH_CALL_PATTERN = re.compile(r"\bBash\s*\(", re.IGNORECASE)

# Task tool delegation to any agent (resets the counter)
_ANY_TASK_DELEGATION = re.compile(
    r'Task\s*\(\s*agent\s*=\s*[\'"](\w[\w-]*)[\'"]',
    re.IGNORECASE,
)

# Maximum consecutive bash calls allowed before a Task delegation is required
_BASH_CAP = 3


class BashCapMetric(BaseMetric):
    """
    DeepEval metric enforcing the bash-command cap rule from PM v0012.

    PM must not issue more than 3 consecutive Bash tool invocations without
    an intervening Task delegation to another agent.  After hitting the 2-3
    bash limit the PM should hand off to "local-ops" or another relevant agent.

    Scoring:
    - 1.0: Consecutive bash run never exceeds the cap.
    - 0.0: Consecutive bash count exceeds the cap without an intervening
           Task delegation.

    Threshold: 0.9
    """

    def __init__(self, threshold: float = 0.9) -> None:
        self.threshold = threshold
        self.score: float = 0.0
        self.reason: str = ""
        self.success: bool = False

    @property
    def __name__(self) -> str:
        return "Bash Command Cap"

    def _count_max_consecutive_bash(self, output: str) -> tuple[int, int]:
        """
        Walk through the output tracking consecutive Bash calls.

        A Task(agent=...) invocation resets the consecutive counter.

        Returns:
            (max_consecutive, total_bash_calls)
        """
        # Build a positional event list: (position, type)
        events: list[tuple[int, str]] = []

        for m in _BASH_CALL_PATTERN.finditer(output):
            events.append((m.start(), "bash"))

        for m in _ANY_TASK_DELEGATION.finditer(output):
            events.append((m.start(), "task"))

        # Sort by position in the output
        events.sort(key=lambda e: e[0])

        consecutive = 0
        max_consecutive = 0
        total_bash = 0

        for _, event_type in events:
            if event_type == "bash":
                consecutive += 1
                total_bash += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:  # task delegation resets streak
                consecutive = 0

        return max_consecutive, total_bash

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Evaluate whether PM exceeded the consecutive bash call cap.

        Returns:
            1.0 if bash cap is respected, 0.0 if exceeded.
        """
        output = test_case.actual_output or ""

        max_consecutive, total_bash = self._count_max_consecutive_bash(output)

        if max_consecutive > _BASH_CAP:
            self.score = 0.0
            self.reason = (
                f"VIOLATION: PM issued {max_consecutive} consecutive Bash calls "
                f"(cap is {_BASH_CAP}).  After reaching the bash limit the PM must "
                "delegate to an agent (e.g. local-ops) via the Task tool."
            )
            self.success = False
            return 0.0

        self.score = 1.0
        self.reason = (
            f"Bash cap respected: max consecutive Bash calls = {max_consecutive} "
            f"(total = {total_bash}, cap = {_BASH_CAP})."
        )
        self.success = True
        return 1.0

    def is_successful(self) -> bool:
        return self.success

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)
