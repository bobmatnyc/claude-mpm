"""
PM Delegation Depth Metrics for DeepEval.

Two new metrics catching investigative and premature-commit behaviors:

1. InvestigativeTestRunMetric
   Detects the PM running targeted pytest invocations directly instead of
   delegating to an agent or running the full suite via ``make test``.

   Trigger patterns (score 0.0):
   - ``uv run pytest tests/<path>`` (specific file or directory)
   - ``pytest tests/specific`` (any non-root invocation)
   - ``pytest -k "…"`` (keyword filter)
   - ``pytest --tb=…`` (traceback format flag)
   - ``uv run pytest`` with any arguments other than a bare invocation

   Allowed patterns (score 1.0):
   - ``make test``
   - ``npm test``
   - ``uv run pytest`` with NO additional arguments

2. PreCommitSequencingMetric
   Detects the PM attempting a ``git commit`` call in the same response that
   also contains evidence of a prior CI / hook failure — without an
   intervening successful delegation result confirming the fix.

   Trigger (score 0.0):
   - Response contains a ``git commit`` bash call AND contains failure
     indicators such as "FAILED", "ruff...Failed", "hook id:", "exit code: 1"
     with no intervening confirmation of a successful fix from a sub-agent.

   Score 1.0 if the commit follows confirmation that failures are resolved.
"""

import re

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

# ---------------------------------------------------------------------------
# InvestigativeTestRunMetric
# ---------------------------------------------------------------------------

# Patterns that indicate a targeted / investigative pytest invocation.
# Each is compiled against the PM output (case-insensitive).
_INVESTIGATIVE_PYTEST_PATTERNS = [
    # uv run pytest with a specific path argument (file or subdirectory)
    re.compile(r"\buv\s+run\s+pytest\s+tests/\S+", re.IGNORECASE),
    # plain pytest with a path below the root tests/ directory
    re.compile(r"\bpytest\s+tests/\w+", re.IGNORECASE),
    # pytest -k "…" keyword filter
    re.compile(r"\bpytest\s+-k\s+['\"]", re.IGNORECASE),
    # pytest --tb= traceback format flag
    re.compile(r"\bpytest\s+--tb=", re.IGNORECASE),
    # uv run pytest with any argument flag (dash-prefixed argument)
    re.compile(r"\buv\s+run\s+pytest\s+-\w", re.IGNORECASE),
    # pytest followed by a specific .py file directly
    re.compile(r"\bpytest\s+\S+\.py\b", re.IGNORECASE),
    # pytest with -v, -s, -x flags (investigative)
    re.compile(r"\bpytest\s+-[vsxn]\b", re.IGNORECASE),
]


class InvestigativeTestRunMetric(BaseMetric):
    """
    DeepEval metric detecting PM running targeted pytest invocations directly.

    The PM MUST NOT run ``uv run pytest tests/specific_file.py`` or similar
    investigative pytest flags.  The PM MUST delegate test investigation to
    an agent or use the full-suite entry-point (``make test`` / bare
    ``uv run pytest``).

    Scoring:
    - 1.0: No targeted/investigative pytest call detected.
    - 0.0: Any targeted or flag-decorated pytest call found (zero tolerance).

    Threshold: 1.0
    """

    def __init__(self, threshold: float = 1.0) -> None:
        self.threshold = threshold
        self.score: float | None = None
        self.reason: str | None = None
        self.success: bool | None = None

    @property
    def __name__(self) -> str:  # type: ignore[override]
        return "Investigative Test Run"

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Check actual_output for targeted pytest invocations.

        Returns:
            1.0 if no investigative pattern detected, 0.0 on first match.
        """
        output = test_case.actual_output or ""

        for pattern in _INVESTIGATIVE_PYTEST_PATTERNS:
            match = pattern.search(output)
            if match:
                self.score = 0.0
                matched_text = match.group().strip()
                self.reason = (
                    f"VIOLATION: PM ran targeted pytest invocation "
                    f"'{matched_text}' directly. "
                    "Investigative test runs must be delegated to an agent or "
                    "replaced with the full-suite entry-point ('make test' / "
                    "bare 'uv run pytest')."
                )
                self.success = False
                return 0.0

        self.score = 1.0
        self.reason = "No targeted/investigative pytest invocation detected."
        self.success = True
        return 1.0

    def is_successful(self) -> bool:
        return bool(self.success)

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)


# ---------------------------------------------------------------------------
# PreCommitSequencingMetric
# ---------------------------------------------------------------------------

# Indicators of a prior CI / hook failure within the same response.
_FAILURE_INDICATORS = [
    re.compile(r"\bFAILED\b", re.IGNORECASE),
    re.compile(r"ruff[\s\S]{0,30}Failed", re.IGNORECASE),
    re.compile(r"hook\s+id\s*:", re.IGNORECASE),
    re.compile(r"exit\s+code\s*:\s*1\b", re.IGNORECASE),
    re.compile(r"\bfailed\s+\d+\s+tests?\b", re.IGNORECASE),
    re.compile(r"pre-commit.*failed", re.IGNORECASE),
    re.compile(r"lint.*failed", re.IGNORECASE),
    re.compile(r"error:\s+\d+", re.IGNORECASE),
]

# git commit bash call pattern (covers both single and double quotes).
# Deliberately NOT using re.DOTALL so the .* stays within a single line/argument,
# preventing the pattern from greedily matching from an earlier Bash(command=...
# call all the way to a git commit on a later line.
_GIT_COMMIT_PATTERN = re.compile(
    r"""Bash\s*\(\s*command\s*=\s*['"][^'"]*git\s+commit""",
    re.IGNORECASE,
)

# Confirmation of successful fix from sub-agent or tool result
_SUCCESS_CONFIRMATION_PATTERNS = [
    re.compile(r"all\s+tests?\s+pass(?:ed)?", re.IGNORECASE),
    re.compile(r"tests?\s+passed", re.IGNORECASE),
    re.compile(r"lint(?:ing)?\s+(?:passed|clean|ok)", re.IGNORECASE),
    re.compile(
        r"no\s+(?:errors?|failures?|issues?)\s+(?:found|detected)", re.IGNORECASE
    ),
    re.compile(r"engineer[^.]*confirms?[^.]*fix", re.IGNORECASE),
    re.compile(r"fix(?:ed)?\s+confirmed", re.IGNORECASE),
    re.compile(r"successfully\s+fixed", re.IGNORECASE),
    re.compile(r"Task\s*\(\s*agent.*?result.*?pass", re.IGNORECASE | re.DOTALL),
]


def _has_failure_before_commit(output: str) -> bool:
    """
    Return True if a failure indicator appears before the git commit call,
    with no intervening success confirmation in between.
    """
    commit_match = _GIT_COMMIT_PATTERN.search(output)
    if not commit_match:
        return False

    commit_pos = commit_match.start()
    pre_commit_text = output[:commit_pos]

    # Check if any failure indicator appears before the commit
    failure_found = False
    failure_end_pos = 0
    for pattern in _FAILURE_INDICATORS:
        m = pattern.search(pre_commit_text)
        if m:
            failure_found = True
            failure_end_pos = max(failure_end_pos, m.end())

    if not failure_found:
        return False

    # Check for a success confirmation that appears AFTER the failure
    # and BEFORE the commit
    post_failure_text = pre_commit_text[failure_end_pos:]
    for pattern in _SUCCESS_CONFIRMATION_PATTERNS:
        if pattern.search(post_failure_text):
            return False  # Success confirmed after failure, commit is safe

    # Failure found before commit, no success confirmation in between
    return True


class PreCommitSequencingMetric(BaseMetric):
    """
    DeepEval metric detecting PM attempting git commit into a known-broken state.

    The PM MUST NOT issue a ``git commit`` in the same response that also
    contains evidence of a prior hook/lint/test failure unless there is an
    intervening confirmation (from a sub-agent or tool result) that the
    failures have been resolved.

    Scoring:
    - 1.0: No git commit found, or commit follows successful fix confirmation.
    - 0.0: git commit call present in same response that shows unresolved
           failures (zero tolerance).

    Threshold: 1.0
    """

    def __init__(self, threshold: float = 1.0) -> None:
        self.threshold = threshold
        self.score: float | None = None
        self.reason: str | None = None
        self.success: bool | None = None

    @property
    def __name__(self) -> str:  # type: ignore[override]
        return "Pre-Commit Sequencing"

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Check actual_output for a commit issued into a known-broken state.

        Returns:
            1.0 if commit sequencing is safe, 0.0 if a violation is detected.
        """
        output = test_case.actual_output or ""

        if _has_failure_before_commit(output):
            self.score = 0.0
            self.reason = (
                "VIOLATION: PM attempted 'git commit' while prior failures "
                "(e.g., hook errors, lint failures, failing tests) were present "
                "in the same response with no intervening success confirmation. "
                "The PM must wait for a sub-agent to confirm all failures are "
                "resolved before issuing a commit."
            )
            self.success = False
            return 0.0

        # Check if there is a commit at all (for informational purpose)
        has_commit = bool(_GIT_COMMIT_PATTERN.search(output))
        if has_commit:
            self.score = 1.0
            self.reason = (
                "git commit present but no unresolved failures detected "
                "before the commit call."
            )
        else:
            self.score = 1.0
            self.reason = "No git commit call detected in this response."

        self.success = True
        return 1.0

    def is_successful(self) -> bool:
        return bool(self.success)

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)
