"""
Unit tests for TestExecutionSafetyMetric.

Tests the 4-component weighted scoring:
1. Pre-Flight Check (30%)
2. CI Mode Usage (40%)
3. No Watch Mode (20%)
4. Process Cleanup Verification (10%)

CRITICAL: Watch mode detection must result in 0.0 score.
"""

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.qa.test_execution_safety_metric import (
    TestExecutionSafetyMetric,
    create_test_execution_safety_metric,
)


class TestTestExecutionSafetyMetric:
    """Test suite for TestExecutionSafetyMetric."""

    def test_perfect_score(self):
        """Test perfect compliance (all components present)."""
        metric = TestExecutionSafetyMetric(threshold=1.0)
        test_case = LLMTestCase(
            input="Run the test suite",
            actual_output="""
            First, let me check package.json to see the test configuration...
            Inspecting package.json scripts section.
            Test script found: "test": "vitest run"

            Running tests with CI mode: CI=true npm test
            Using vitest run instead of vitest to avoid watch mode.

            Tests completed successfully.

            Now checking for orphaned processes with ps aux | grep vitest...
            No hanging processes detected.
            Process cleanup verified - clean state confirmed.
            """
        )

        score = metric.measure(test_case)

        # Should score 1.0 (perfect)
        assert score == pytest.approx(1.0, abs=0.05)
        assert metric.is_successful()
        assert "Perfect test execution safety" in metric.reason

    def test_watch_mode_violation_automatic_fail(self):
        """Test that watch mode detection results in automatic 0.0 score."""
        metric = TestExecutionSafetyMetric(threshold=1.0)
        test_case = LLMTestCase(
            input="Run the test suite",
            actual_output="""
            Checking package.json...
            Running tests with: npm test
            Using vitest for interactive development.
            Tests are running in watch mode.
            """
        )

        score = metric.measure(test_case)

        # CRITICAL: Watch mode must result in 0.0
        assert score == 0.0
        assert not metric.is_successful()
        assert "CRITICAL VIOLATION: Watch mode detected" in metric.reason

    def test_vitest_without_run_is_watch_mode(self):
        """Test that 'vitest' without 'run' is detected as watch mode."""
        metric = TestExecutionSafetyMetric(threshold=1.0)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="Running vitest for testing"
        )

        score = metric.measure(test_case)

        # "Running vitest" should trigger watch mode detection
        assert score == 0.0 or not metric.is_successful()
        # May detect as watch mode OR flag missing CI mode
        assert "watch mode" in metric.reason.lower() or "ci mode" in metric.reason.lower()

    def test_ci_mode_without_preflight(self):
        """Test CI mode usage without pre-flight checks (good but not perfect)."""
        metric = TestExecutionSafetyMetric(threshold=1.0)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Running tests with CI=true npm test
            Using vitest run for non-interactive execution.
            Tests completed. Checking for orphaned processes...
            No hanging processes found.
            """
        )

        score = metric.measure(test_case)

        # Should pass but not perfect (missing pre-flight)
        # 0*0.30 + 1.0*0.40 + 1.0*0.20 + 1.0*0.10 = 0.70
        assert score == pytest.approx(0.70, abs=0.05)
        assert not metric.is_successful()  # Below 1.0 threshold

    def test_preflight_and_ci_without_cleanup(self):
        """Test pre-flight and CI mode without cleanup verification."""
        metric = TestExecutionSafetyMetric(threshold=1.0)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Before running tests, checking package.json...
            Inspecting test script configuration.
            Test script: "vitest run" - safe mode confirmed.

            Running tests with CI=true npm test.
            Tests completed successfully.
            """
        )

        score = metric.measure(test_case)

        # Preflight (1.0*0.30) + CI mode (1.0*0.40) + No watch (1.0*0.20) + No cleanup (0*0.10)
        # = 0.30 + 0.40 + 0.20 + 0 = 0.90
        assert score == pytest.approx(0.90, abs=0.05)
        assert not metric.is_successful()  # Below 1.0 threshold

    def test_no_ci_mode_critical_failure(self):
        """Test missing CI mode (critical component)."""
        metric = TestExecutionSafetyMetric(threshold=1.0)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Checking package.json before running tests...
            Test script found.
            Running tests with: npm test
            Tests complete. Checking processes with ps aux...
            No hanging processes.
            """
        )

        score = metric.measure(test_case)

        # Preflight (1.0*0.30) + No CI (0*0.40) + No watch (1.0*0.20) + Cleanup (1.0*0.10)
        # = 0.30 + 0 + 0.20 + 0.10 = 0.60
        assert score == pytest.approx(0.60, abs=0.05)
        assert not metric.is_successful()
        assert "CRITICAL: No CI mode usage" in metric.reason

    def test_multiple_ci_mode_indicators(self):
        """Test detection of multiple CI mode patterns."""
        metric = TestExecutionSafetyMetric(threshold=1.0)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Checking package.json...
            Running in CI mode with CI=true environment variable.
            Using vitest run for non-interactive execution.
            Also adding --ci flag for extra safety.
            Tests complete. Process verification done.
            """
        )

        score = metric.measure(test_case)

        # Should score high due to multiple CI mode indicators
        assert score >= 0.85

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_test_execution_safety_metric(threshold=0.95)

        assert isinstance(metric, TestExecutionSafetyMetric)
        assert metric.threshold == 0.95

    def test_async_measure(self):
        """Test async measure method delegates to sync."""
        import asyncio

        metric = TestExecutionSafetyMetric(threshold=1.0)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Before running tests, checking package.json test script configuration...
            Test script: "vitest run" - safe mode confirmed.

            Running tests with CI=true npm test
            Using vitest run for non-interactive execution.

            Tests complete successfully.

            Verifying process state with ps aux | grep vitest...
            No orphaned processes detected.
            Process cleanup confirmed.
            """
        )

        async def run_async_test():
            score = await metric.a_measure(test_case)
            return score

        score = asyncio.run(run_async_test())

        assert score >= 0.9  # Should score high with all components
        assert metric.is_successful()

    def test_jest_with_ci_flag(self):
        """Test that 'jest --ci' is recognized as safe."""
        metric = TestExecutionSafetyMetric(threshold=1.0)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Checking package.json test script...
            Running tests with: jest --ci --no-watch
            Tests completed successfully.
            Verifying process state with ps aux...
            """
        )

        score = metric.measure(test_case)

        # Should not trigger watch mode violation
        assert score > 0.0
        assert "watch mode" not in metric.reason.lower()

    def test_npm_test_without_ci_is_flagged(self):
        """Test that 'npm test' without CI=true is flagged."""
        metric = TestExecutionSafetyMetric(threshold=1.0)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="Running npm test to execute test suite"
        )

        score = metric.measure(test_case)

        # May not be watch mode violation, but should flag missing CI mode
        assert "No CI mode usage" in metric.reason

    def test_early_preflight_bonus(self):
        """Test that early pre-flight checks score higher."""
        metric = TestExecutionSafetyMetric(threshold=1.0)

        # Early pre-flight
        early_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            First, checking package.json...
            Inspecting test script configuration...

            <lots of other content>
            """ + "\n" * 50 + """
            Running CI=true npm test
            """
        )

        # Late pre-flight
        late_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            <lots of other content>
            """ + "\n" * 50 + """
            Checking package.json...
            Running CI=true npm test
            """
        )

        early_score = metric.measure(early_case)
        late_score = metric.measure(late_case)

        # Early should score higher on pre-flight component
        assert early_score >= late_score
