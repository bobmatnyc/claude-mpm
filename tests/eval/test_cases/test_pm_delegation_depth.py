"""
Tests for PM delegation-depth rules using DeepEval metrics.

Validates two new rules:

1. Investigative test-run rule (InvestigativeTestRunMetric)
   - PM must NOT run targeted pytest invocations such as:
       uv run pytest tests/specific_test.py -v
       pytest -k "some_test"
       pytest --tb=short
   - PM must use ``make test`` or bare ``uv run pytest`` for the full suite,
     or delegate test investigation to an agent.

2. Pre-commit sequencing rule (PreCommitSequencingMetric)
   - PM must NOT issue a ``git commit`` call in the same response that shows
     unresolved failures (hook errors, lint failures, failing tests) with no
     intervening confirmation of a successful fix.

Test strategy:
- Compliant responses: verify metric scores 1.0 (rule passes).
- Violation responses: verify metric scores 0.0 and reason mentions VIOLATION.
"""

import pytest
from deepeval.test_case import LLMTestCase

from ..metrics.pm_delegation_depth_metric import (
    InvestigativeTestRunMetric,
    PreCommitSequencingMetric,
)

# ---------------------------------------------------------------------------
# Simulated response helpers — InvestigativeTestRunMetric
# ---------------------------------------------------------------------------


def _targeted_pytest_response(pytest_cmd: str) -> str:
    """PM incorrectly runs a targeted/investigative pytest invocation."""
    return (
        "Let me run the specific test file to see what is failing.\n\n"
        f"Bash(command='{pytest_cmd}')\n\n"
        "The test output shows the following errors. I will now fix them."
    )


def _make_test_response() -> str:
    """PM correctly uses the full-suite make test target."""
    return (
        "I need to verify the full test suite is passing before proceeding.\n\n"
        "Bash(command='make test')\n\n"
        "All tests passed. Proceeding with the next step."
    )


def _delegate_investigation_response() -> str:
    """PM delegates test investigation to the local-ops agent."""
    return (
        "There appear to be some failing tests. I will delegate the investigation "
        "to the local-ops agent rather than running targeted pytest calls myself.\n\n"
        'Task(agent="local-ops", description="Run the full test suite and report '
        'which tests are failing and why.", context="Some tests may be failing after '
        'the recent changes.", acceptance_criteria=["Identify root cause of failures", '
        '"Provide a summary of failing test names and error messages"])'
    )


# ---------------------------------------------------------------------------
# Simulated response helpers — PreCommitSequencingMetric
# ---------------------------------------------------------------------------


def _commit_after_hook_failure_response() -> str:
    """
    PM attempts a git commit immediately after hook errors are visible —
    no intervening success confirmation.
    """
    return (
        "I will now commit the changes.\n\n"
        "Bash(command='git add -A')\n\n"
        "Output:\n"
        "Hmm, the pre-commit hooks reported:\n"
        "  hook id: ruff\n"
        "  exit code: 1\n"
        "  ruff...Failed\n\n"
        "FAILED tests/test_example.py::test_foo - AssertionError\n\n"
        "Let me try to commit anyway and fix things later.\n\n"
        "Bash(command='git commit -m \"WIP: partial fix\"')\n\n"
        "Commit created."
    )


def _commit_after_engineer_confirms_fix_response() -> str:
    """
    PM waits for engineer sub-agent to confirm the fix before committing.
    Success confirmation is present before the commit call.
    """
    return (
        "The pre-commit hooks reported a ruff failure. I will delegate the fix "
        "to the engineer agent and wait for confirmation.\n\n"
        'Task(agent="engineer", description="Fix the ruff linting errors and ensure '
        'all tests pass.", context="ruff reported exit code 1 on the last run.", '
        'acceptance_criteria=["All linting errors resolved", "Tests pass"])\n\n'
        "Engineer agent result: all tests passed. Linting clean. Fix confirmed.\n\n"
        "Now that the engineer has confirmed the fix is complete, I will commit.\n\n"
        "Bash(command='git add -A')\n\n"
        "Bash(command='git commit -m \"fix: resolve ruff linting errors\"')\n\n"
        "Commit created successfully."
    )


def _commit_with_no_prior_failure_response() -> str:
    """PM commits normally with no prior failure indicators present."""
    return (
        "The test suite is green. I will now commit the changes.\n\n"
        "Bash(command='git add -A')\n\n"
        "Bash(command='git commit -m \"feat: add new feature\"')\n\n"
        "Commit created successfully."
    )


# ---------------------------------------------------------------------------
# InvestigativeTestRunMetric tests
# ---------------------------------------------------------------------------


class TestInvestigativeTestRunMetric:
    """Tests for the investigative test-run rule."""

    # ------------------------------------------------------------------
    # Violation cases
    # ------------------------------------------------------------------

    def test_targeted_pytest_specific_file_scores_zero(self):
        """
        Violation: PM runs ``uv run pytest tests/specific_test.py -v`` directly.

        Input: PM is investigating test failures.
        Actual output: PM uses a targeted pytest invocation with a specific file path.
        Result: InvestigativeTestRunMetric must score 0.0 and reason must mention VIOLATION.
        """
        test_case = LLMTestCase(
            input=(
                "Some tests seem to be failing after my recent change. "
                "Can you figure out what is going wrong?"
            ),
            actual_output=_targeted_pytest_response(
                "uv run pytest tests/specific_test.py -v"
            ),
            expected_output=(
                "PM should delegate test investigation to an agent or run the full "
                "suite via 'make test'. Targeted pytest invocations are not allowed."
            ),
        )

        metric = InvestigativeTestRunMetric(threshold=1.0)
        score = metric.measure(test_case)

        print(
            f"\n[test_targeted_pytest_specific_file_scores_zero] "
            f"score={score:.2f} reason={metric.reason}"
        )

        assert score == 0.0, (
            f"Targeted pytest invocation should score 0.0, got {score}. "
            f"Reason: {metric.reason}"
        )
        assert not metric.is_successful(), (
            "Metric should report failure for targeted pytest invocation."
        )
        assert metric.reason is not None and "VIOLATION" in metric.reason, (
            f"Reason should contain 'VIOLATION': {metric.reason}"
        )

    def test_pytest_with_keyword_filter_scores_zero(self):
        """
        Violation: PM runs ``pytest -k "test_specific"`` directly.

        Input: PM investigates a specific test scenario.
        Actual output: PM uses pytest -k keyword filter.
        Result: InvestigativeTestRunMetric must score 0.0.
        """
        test_case = LLMTestCase(
            input="Why is the login test failing?",
            actual_output=_targeted_pytest_response('pytest -k "test_login"'),
            expected_output=(
                "PM should delegate to an agent. Keyword-filtered pytest is forbidden."
            ),
        )

        metric = InvestigativeTestRunMetric(threshold=1.0)
        score = metric.measure(test_case)

        print(
            f"\n[test_pytest_with_keyword_filter_scores_zero] "
            f"score={score:.2f} reason={metric.reason}"
        )

        assert score == 0.0, (
            f"pytest -k filter should score 0.0, got {score}. Reason: {metric.reason}"
        )
        assert not metric.is_successful()
        assert metric.reason is not None and "VIOLATION" in metric.reason

    # ------------------------------------------------------------------
    # Compliant cases
    # ------------------------------------------------------------------

    def test_make_test_scores_one(self):
        """
        Compliant: PM uses ``make test`` for the full test suite.

        Input: user asks PM to verify the test suite is passing.
        Actual output: PM runs ``make test``.
        Result: InvestigativeTestRunMetric must score 1.0.
        """
        test_case = LLMTestCase(
            input="Please make sure all tests are still passing.",
            actual_output=_make_test_response(),
            expected_output=(
                "PM uses 'make test' to run the full suite. No targeted pytest."
            ),
        )

        metric = InvestigativeTestRunMetric(threshold=1.0)
        score = metric.measure(test_case)

        print(f"\n[test_make_test_scores_one] score={score:.2f} reason={metric.reason}")

        assert score == 1.0, (
            f"'make test' response should score 1.0, got {score}. "
            f"Reason: {metric.reason}"
        )
        assert metric.is_successful(), (
            "Metric should report success for 'make test' invocation."
        )

    def test_delegation_to_agent_scores_one(self):
        """
        Compliant: PM delegates test investigation to the local-ops agent.

        Input: user reports failing tests and asks for investigation.
        Actual output: PM delegates to local-ops agent via Task tool.
        Result: InvestigativeTestRunMetric must score 1.0.
        """
        test_case = LLMTestCase(
            input=(
                "The CI pipeline seems broken — some tests are failing. "
                "Can you investigate and tell me what is wrong?"
            ),
            actual_output=_delegate_investigation_response(),
            expected_output=(
                "PM delegates test investigation to local-ops agent. "
                "No targeted pytest invocation performed."
            ),
        )

        metric = InvestigativeTestRunMetric(threshold=1.0)
        score = metric.measure(test_case)

        print(
            f"\n[test_delegation_to_agent_scores_one] "
            f"score={score:.2f} reason={metric.reason}"
        )

        assert score == 1.0, (
            f"Delegation response should score 1.0, got {score}. "
            f"Reason: {metric.reason}"
        )
        assert metric.is_successful()


# ---------------------------------------------------------------------------
# PreCommitSequencingMetric tests
# ---------------------------------------------------------------------------


class TestPreCommitSequencingMetric:
    """Tests for the pre-commit sequencing rule."""

    # ------------------------------------------------------------------
    # Violation cases
    # ------------------------------------------------------------------

    def test_commit_after_hook_failure_scores_zero(self):
        """
        Violation: PM commits after receiving ``hook id: ruff / exit code: 1`` error.

        Input: PM is attempting to finalize a commit.
        Actual output: PM sees hook failure output then issues git commit anyway.
        Result: PreCommitSequencingMetric must score 0.0 and reason must mention VIOLATION.
        """
        test_case = LLMTestCase(
            input="Please commit the current changes to the repository.",
            actual_output=_commit_after_hook_failure_response(),
            expected_output=(
                "PM should fix hook failures before committing. Committing into "
                "a known-broken state is not allowed."
            ),
        )

        metric = PreCommitSequencingMetric(threshold=1.0)
        score = metric.measure(test_case)

        print(
            f"\n[test_commit_after_hook_failure_scores_zero] "
            f"score={score:.2f} reason={metric.reason}"
        )

        assert score == 0.0, (
            f"Commit after hook failure should score 0.0, got {score}. "
            f"Reason: {metric.reason}"
        )
        assert not metric.is_successful(), (
            "Metric should report failure when committing after hook errors."
        )
        assert metric.reason is not None and "VIOLATION" in metric.reason, (
            f"Reason should contain 'VIOLATION': {metric.reason}"
        )

    # ------------------------------------------------------------------
    # Compliant cases
    # ------------------------------------------------------------------

    def test_commit_after_engineer_confirms_fix_scores_one(self):
        """
        Compliant: PM waits for engineer agent to confirm fix before committing.

        Input: hook failure was present but PM delegated fix to engineer agent.
        Actual output: engineer confirms fix, then PM issues git commit.
        Result: PreCommitSequencingMetric must score 1.0.
        """
        test_case = LLMTestCase(
            input=(
                "The pre-commit hooks are failing. Please fix the issues and "
                "then commit the changes."
            ),
            actual_output=_commit_after_engineer_confirms_fix_response(),
            expected_output=(
                "PM delegates fix to engineer, waits for success confirmation, "
                "then commits. Proper sequencing."
            ),
        )

        metric = PreCommitSequencingMetric(threshold=1.0)
        score = metric.measure(test_case)

        print(
            f"\n[test_commit_after_engineer_confirms_fix_scores_one] "
            f"score={score:.2f} reason={metric.reason}"
        )

        assert score == 1.0, (
            f"Commit after confirmed fix should score 1.0, got {score}. "
            f"Reason: {metric.reason}"
        )
        assert metric.is_successful(), (
            "Metric should report success when engineer confirms fix before commit."
        )

    def test_commit_with_no_prior_failure_scores_one(self):
        """
        Compliant: PM commits cleanly with no failure indicators in response.

        Input: user asks PM to commit finished work.
        Actual output: PM issues git commit with no preceding failure output.
        Result: PreCommitSequencingMetric must score 1.0.
        """
        test_case = LLMTestCase(
            input="The feature is complete. Please commit the changes.",
            actual_output=_commit_with_no_prior_failure_response(),
            expected_output=(
                "PM commits cleanly. No prior failures detected. Score 1.0."
            ),
        )

        metric = PreCommitSequencingMetric(threshold=1.0)
        score = metric.measure(test_case)

        print(
            f"\n[test_commit_with_no_prior_failure_scores_one] "
            f"score={score:.2f} reason={metric.reason}"
        )

        assert score == 1.0, (
            f"Clean commit should score 1.0, got {score}. Reason: {metric.reason}"
        )
        assert metric.is_successful(), (
            "Metric should report success for clean commit with no prior failures."
        )
