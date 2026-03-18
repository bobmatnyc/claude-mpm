"""
Tests for PM v0012 instruction rules using DeepEval metrics.

Validates two new rules:

1. gh CLI delegation rule (GhCliDelegationMetric)
   - PM must NEVER call gh issue list / view, gh pr view / list / diff directly.
   - PM must delegate these operations to the "ticketing" or "version-control"
     agent via the Task tool.

2. Bash command cap rule (BashCapMetric)
   - PM must not exceed 3 consecutive Bash calls without an intervening
     Task delegation to another agent.

Test strategy:
- Compliant responses: verify metric scores 1.0 (rule passes).
- Violation responses: verify metric scores 0.0 and reason mentions VIOLATION.
"""

import pytest
from deepeval.test_case import LLMTestCase

from ..metrics.pm_v0012_rules_metric import BashCapMetric, GhCliDelegationMetric

# ---------------------------------------------------------------------------
# Simulated response helpers
# ---------------------------------------------------------------------------


def _compliant_gh_delegation_response(agent: str = "ticketing") -> str:
    """PM correctly delegates a gh read operation to the specified agent."""
    return (
        f"I need to check the open issues. I will delegate this to the {agent} agent.\n\n"
        f'Task(agent="{agent}", description="List all open GitHub issues and summarise '
        f'them by priority.", context="User asked for a status on open issues.", '
        f'acceptance_criteria=["Return list of open issues with titles and labels"])'
    )


def _violation_gh_direct_response(command: str) -> str:
    """PM incorrectly calls a gh command directly."""
    return (
        f"I will check the open issues directly.\n\n"
        f"Bash(command='{command}')\n\n"
        f"Here are the results from running {command}."
    )


def _compliant_bash_cap_response() -> str:
    """PM does a couple of bash calls then delegates the heavy lifting."""
    return (
        "Let me gather some quick context first.\n\n"
        "Bash(command='git status')\n\n"
        "Bash(command='git log --oneline -5')\n\n"
        "I've confirmed the repo state. Now I'll delegate the multi-step file "
        "operations to the local-ops agent.\n\n"
        'Task(agent="local-ops", description="Run the full build and test pipeline '
        'and report back results.", context="Repo is clean, last 5 commits verified.", '
        'acceptance_criteria=["All tests pass", "Build artifact produced"])'
    )


def _violation_bash_cap_response() -> str:
    """PM exceeds the bash cap with 5 sequential Bash calls and no delegation."""
    return (
        "I will handle this entirely myself.\n\n"
        "Bash(command='ls -la')\n\n"
        "Bash(command='cat README.md')\n\n"
        "Bash(command='git status')\n\n"
        "Bash(command='git log --oneline -10')\n\n"
        "Bash(command='cat pyproject.toml')\n\n"
        "Done. All information gathered without delegating to any agent."
    )


# ---------------------------------------------------------------------------
# GhCliDelegationMetric tests
# ---------------------------------------------------------------------------


class TestGhCliDelegationMetric:
    """Tests for the gh CLI delegation rule (PM v0012)."""

    # ------------------------------------------------------------------
    # Compliant cases
    # ------------------------------------------------------------------

    def test_pm_delegates_gh_issue_reads(self):
        """
        Compliant: PM delegates 'check open issues' to the ticketing agent.

        Input: user asks for a summary of open GitHub issues.
        Expected: PM uses Task tool pointing to 'ticketing' agent.
        Result: GhCliDelegationMetric must score 1.0.
        """
        test_case = LLMTestCase(
            input="Can you check the open issues and tell me what's in progress?",
            actual_output=_compliant_gh_delegation_response("ticketing"),
            expected_output=(
                "PM delegates gh issue read to the ticketing agent via Task tool "
                "without calling gh issue list or gh issue view directly."
            ),
        )

        metric = GhCliDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        print(
            f"\n[test_pm_delegates_gh_issue_reads] score={score:.2f} reason={metric.reason}"
        )

        assert score == 1.0, (
            f"Compliant delegation should score 1.0, got {score}. "
            f"Reason: {metric.reason}"
        )
        assert metric.is_successful(), (
            "Metric should report success for compliant response."
        )

    def test_pm_delegates_gh_pr_reads(self):
        """
        Compliant: PM delegates 'review open PRs' to the version-control agent.

        Input: user asks for a review of open pull requests.
        Expected: PM uses Task tool pointing to 'version-control' agent.
        Result: GhCliDelegationMetric must score 1.0.
        """
        response = (
            "I will delegate the PR review to the version-control agent.\n\n"
            'Task(agent="version-control", description="List and summarise all open '
            'pull requests including their CI status.", '
            'context="User requested PR review.", '
            'acceptance_criteria=["Return PR titles, authors, and review status"])'
        )

        test_case = LLMTestCase(
            input="Can you review the open PRs and summarise the review status?",
            actual_output=response,
            expected_output=(
                "PM delegates gh pr read operations to the version-control agent "
                "via Task tool without calling gh pr list or gh pr view directly."
            ),
        )

        metric = GhCliDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        print(
            f"\n[test_pm_delegates_gh_pr_reads] score={score:.2f} reason={metric.reason}"
        )

        assert score == 1.0, (
            f"Compliant PR delegation should score 1.0, got {score}. "
            f"Reason: {metric.reason}"
        )
        assert metric.is_successful()

    # ------------------------------------------------------------------
    # Violation cases
    # ------------------------------------------------------------------

    def test_pm_gh_cli_direct_use_detected(self):
        """
        Violation: PM directly calls 'gh issue list' — must be detected.

        Input: user asks to check open issues.
        Actual output: PM uses Bash(command='gh issue list') directly.
        Result: GhCliDelegationMetric must score 0.0 and reason must mention VIOLATION.
        """
        test_case = LLMTestCase(
            input="What are the open issues right now?",
            actual_output=_violation_gh_direct_response("gh issue list --state open"),
            expected_output=(
                "PM should delegate to ticketing agent. Direct gh CLI usage is forbidden."
            ),
        )

        metric = GhCliDelegationMetric(threshold=1.0)
        score = metric.measure(test_case)

        print(
            f"\n[test_pm_gh_cli_direct_use_detected] score={score:.2f} reason={metric.reason}"
        )

        assert score == 0.0, (
            f"Direct gh issue list usage should score 0.0, got {score}. "
            f"Reason: {metric.reason}"
        )
        assert not metric.is_successful(), (
            "Metric should report failure for gh CLI direct use."
        )
        assert "VIOLATION" in metric.reason, (
            f"Reason should contain 'VIOLATION': {metric.reason}"
        )


# ---------------------------------------------------------------------------
# BashCapMetric tests
# ---------------------------------------------------------------------------


class TestBashCapMetric:
    """Tests for the bash command cap rule (PM v0012)."""

    # ------------------------------------------------------------------
    # Compliant case
    # ------------------------------------------------------------------

    def test_pm_respects_bash_cap_delegates(self):
        """
        Compliant: PM issues 2 Bash calls then delegates to local-ops.

        Input: user requests a multi-step operation requiring many shell commands.
        Actual output: PM runs 2 Bash calls for context then uses Task tool.
        Result: BashCapMetric must score 1.0.
        """
        test_case = LLMTestCase(
            input=(
                "Please check the current git state, inspect the last few commits, "
                "then run the full build and test pipeline."
            ),
            actual_output=_compliant_bash_cap_response(),
            expected_output=(
                "PM runs at most 2-3 bash commands for quick context then delegates "
                "the remaining multi-step pipeline to local-ops via Task tool."
            ),
        )

        metric = BashCapMetric(threshold=0.9)
        score = metric.measure(test_case)

        print(
            f"\n[test_pm_respects_bash_cap_delegates] score={score:.2f} reason={metric.reason}"
        )

        assert score == 1.0, (
            f"Compliant bash+delegation response should score 1.0, got {score}. "
            f"Reason: {metric.reason}"
        )
        assert metric.is_successful()

    # ------------------------------------------------------------------
    # Violation case
    # ------------------------------------------------------------------

    def test_pm_bash_cap_violation_detected(self):
        """
        Violation: PM issues 5 sequential Bash calls with no delegation — must be detected.

        Input: user requests information that could require many shell commands.
        Actual output: PM executes 5 Bash calls sequentially without any Task delegation.
        Result: BashCapMetric must score 0.0 and reason must mention VIOLATION.
        """
        test_case = LLMTestCase(
            input=(
                "Check the repo layout, README, git log, current status, "
                "and project dependencies."
            ),
            actual_output=_violation_bash_cap_response(),
            expected_output=(
                "PM should delegate to local-ops agent after 2-3 bash commands. "
                "Five consecutive bash calls without delegation violates the bash cap rule."
            ),
        )

        metric = BashCapMetric(threshold=0.9)
        score = metric.measure(test_case)

        print(
            f"\n[test_pm_bash_cap_violation_detected] score={score:.2f} reason={metric.reason}"
        )

        assert score == 0.0, (
            f"Five consecutive Bash calls should score 0.0, got {score}. "
            f"Reason: {metric.reason}"
        )
        assert not metric.is_successful(), (
            "Metric should report failure for bash cap violation."
        )
        assert "VIOLATION" in metric.reason, (
            f"Reason should contain 'VIOLATION': {metric.reason}"
        )
