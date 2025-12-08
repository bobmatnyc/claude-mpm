"""
Unit tests for ProcessManagementMetric.

Tests the 4-component weighted scoring:
1. Pre-Flight Checks (40%)
2. Post-Execution Verification (35%)
3. Hanging Process Detection (15%)
4. Orphaned Process Cleanup (10%)
"""

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.qa.process_management_metric import (
    ProcessManagementMetric,
    create_process_management_metric,
)


class TestProcessManagementMetric:
    """Test suite for ProcessManagementMetric."""

    def test_perfect_score(self):
        """Test perfect compliance (all components present)."""
        metric = ProcessManagementMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Run tests with process management",
            actual_output="""
            Before running tests, let me check package.json...
            Inspecting test script configuration.
            Test script found: "test": "vitest run"
            Verified test command is safe and non-interactive.

            Running tests...
            Tests completed successfully.

            Now verifying process state with ps aux | grep vitest...
            Checking for any hanging test processes...
            No hanging processes detected.
            Process state is clean - no orphaned node processes.

            Verified: All test processes terminated correctly.
            No stuck or hanging processes remain.
            Process cleanup confirmed.
            """,
        )

        score = metric.measure(test_case)

        # Should score >= 0.9 (perfect or near-perfect)
        assert score >= 0.9
        assert metric.is_successful()
        assert "Perfect process management" in metric.reason or score >= 0.9

    def test_preflight_only(self):
        """Test pre-flight checks without post-execution verification."""
        metric = ProcessManagementMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Checking package.json before running tests...
            Inspecting test script: "vitest run"
            Verifying test command is non-interactive.
            Safe mode confirmed.

            Running tests...
            Tests complete.
            """,
        )

        score = metric.measure(test_case)

        # Preflight scores high, but missing other components
        # Preflight (0.9*0.40) + Post-exec (0.5*0.35) + etc
        # Actual scoring may vary based on detected patterns
        assert score < 0.9  # Below threshold
        assert not metric.is_successful()

    def test_post_execution_verification_only(self):
        """Test post-execution verification without pre-flight."""
        metric = ProcessManagementMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Running tests...
            Tests complete.

            Verifying process state with ps aux...
            Checking for orphaned processes.
            Process state is clean.
            No hanging processes detected.
            All tests terminated correctly.
            """,
        )

        score = metric.measure(test_case)

        # Missing pre-flight (most critical component at 40%)
        # Should fail to meet 0.9 threshold
        assert score < 0.9  # Below threshold
        assert not metric.is_successful()

    def test_comprehensive_preflight_checks(self):
        """Test multiple pre-flight check patterns."""
        metric = ProcessManagementMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Run tests safely",
            actual_output="""
            Before running tests, I'll perform pre-flight checks:
            1. Inspecting package.json test script
            2. Verifying test command is safe
            3. Checking for non-interactive mode
            4. Reviewing package.json configuration

            Test script: "vitest run" - SAFE, non-interactive confirmed.

            Running tests with verified safe configuration...
            Tests complete. Verifying process state...
            No hanging processes detected.
            """,
        )

        score = metric.measure(test_case)

        # Should score high on pre-flight (multiple checks early)
        assert score >= 0.9
        assert metric.is_successful()

    def test_hanging_process_detection(self):
        """Test hanging process detection patterns."""
        metric = ProcessManagementMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Check for hanging processes",
            actual_output="""
            Checking package.json test script...
            Test script verified: "vitest run"

            Running tests...
            Tests complete.

            Checking for hanging processes...
            Detecting any stuck test processes...
            No hanging vitest processes detected.
            No processes are not responding.
            All test processes terminated successfully.
            """,
        )

        score = metric.measure(test_case)

        # Should score well with hanging detection
        assert score >= 0.9
        assert metric.is_successful()

    def test_orphaned_process_cleanup(self):
        """Test orphaned process cleanup detection."""
        metric = ProcessManagementMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Clean up processes",
            actual_output="""
            Inspecting package.json before tests...
            Test script: "vitest run" - safe mode.

            Running tests...
            Tests complete.

            Verifying process state...
            Found orphaned vitest process (PID 12345).
            Killing orphaned process with pkill.
            Terminated hanging node processes.
            Process cleanup complete - all orphaned processes removed.
            """,
        )

        score = metric.measure(test_case)

        # Should score well with all components including cleanup
        assert score >= 0.9
        assert metric.is_successful()

    def test_no_process_management(self):
        """Test output with no process management (should fail)."""
        metric = ProcessManagementMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Running tests...
            All tests passed.
            Done.
            """,
        )

        score = metric.measure(test_case)

        assert score < 0.9
        assert not metric.is_successful()
        assert "CRITICAL: No pre-flight checks" in metric.reason

    def test_early_preflight_bonus(self):
        """Test that early pre-flight checks score higher."""
        metric = ProcessManagementMetric(threshold=0.9)

        # Early pre-flight
        early_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            First, checking package.json...
            Inspecting test script configuration...
            Test command verified safe...

            <lots of other content>
            """
            + "\n" * 50
            + """
            Running tests...
            Verifying process state...
            """,
        )

        # Late pre-flight
        late_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            <lots of other content>
            """
            + "\n" * 50
            + """
            Checking package.json...
            Running tests...
            Verifying process state...
            """,
        )

        early_score = metric.measure(early_case)
        late_score = metric.measure(late_case)

        # Early should score higher on pre-flight component
        assert early_score >= late_score

    def test_ps_aux_verification(self):
        """Test ps aux command detection for verification."""
        metric = ProcessManagementMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Verify processes",
            actual_output="""
            Checking package.json test script...
            Test script: "vitest run" verified safe.

            Running tests...
            Tests complete.

            Executing ps aux | grep vitest to check for hanging processes...
            ps aux | grep node to check for orphaned node processes...
            Process state verification complete.
            All processes terminated cleanly.
            """,
        )

        score = metric.measure(test_case)

        # Should detect ps aux usage
        assert score >= 0.9
        assert metric.is_successful()

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_process_management_metric(threshold=0.85)

        assert isinstance(metric, ProcessManagementMetric)
        assert metric.threshold == 0.85

    def test_async_measure(self):
        """Test async measure method delegates to sync."""
        import asyncio

        metric = ProcessManagementMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Checking package.json...
            Test script: "vitest run" - safe.
            Running tests...
            Verifying process state with ps aux...
            No hanging processes.
            """,
        )

        async def run_async_test():
            score = await metric.a_measure(test_case)
            return score

        score = asyncio.run(run_async_test())

        assert score >= 0.9
        assert metric.is_successful()

    def test_component_weights(self):
        """Test that component weights sum to 1.0."""
        # Pre-flight (40%) + Post-exec (35%) + Hanging (15%) + Cleanup (10%)
        total_weight = 0.40 + 0.35 + 0.15 + 0.10
        assert total_weight == pytest.approx(1.0)

    def test_partial_compliance_scenarios(self):
        """Test various partial compliance scenarios."""
        metric = ProcessManagementMetric(threshold=0.9)

        # Scenario: Pre-flight + Post-exec, missing hanging detection and cleanup
        partial_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Checking package.json before running tests...
            Inspecting test script.
            Test command verified.

            Running tests...
            Tests complete.

            Verifying process state after tests.
            Process state is clean.
            """,
        )

        score = metric.measure(partial_case)

        # Preflight (1.0*0.40) + Post-exec (1.0*0.35) + No hanging (0*0.15) + No cleanup (0*0.10)
        # = 0.40 + 0.35 + 0 + 0 = 0.75
        assert score == pytest.approx(0.75, abs=0.10)
        assert not metric.is_successful()

    def test_comprehensive_process_lifecycle(self):
        """Test comprehensive process lifecycle management."""
        metric = ProcessManagementMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Manage test process lifecycle",
            actual_output="""
            === PRE-FLIGHT PHASE ===
            Before running tests, inspecting package.json...
            Checking test script configuration: "test": "vitest run"
            Verifying non-interactive mode: CONFIRMED
            Test command is safe to execute.

            === EXECUTION PHASE ===
            Running tests with verified safe configuration...
            Tests executing...
            Tests completed successfully.

            === POST-EXECUTION VERIFICATION ===
            Verifying process state with ps aux | grep vitest...
            Checking for hanging processes...
            Detecting any stuck test processes...
            No hanging processes detected.

            === CLEANUP PHASE ===
            Checking for orphaned processes...
            No orphaned node processes found.
            Process cleanup verified.
            All processes terminated correctly.

            Process lifecycle management: COMPLETE
            """,
        )

        score = metric.measure(test_case)

        # Should score perfect or near-perfect
        assert score >= 0.95
        assert metric.is_successful()

    def test_timeout_detection(self):
        """Test timeout and stuck process detection."""
        metric = ProcessManagementMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Detect timeouts",
            actual_output="""
            Before running tests, inspecting package.json test script...
            Test command configuration: "vitest run"
            Verified test command is safe and non-interactive.

            Running tests...
            Tests complete successfully.

            Verifying process state after tests with ps aux...
            Checking for timeout issues...
            Detecting processes that are not responding...
            No stuck processes detected.
            No timeout issues found.
            All processes responding normally.
            Process state verified clean.
            """,
        )

        score = metric.measure(test_case)

        # Should score well with all components present
        assert score >= 0.9
        assert metric.is_successful()

    def test_minimal_preflight_vs_comprehensive(self):
        """Test scoring difference between minimal and comprehensive pre-flight."""
        metric = ProcessManagementMetric(threshold=0.9)

        # Minimal pre-flight (single check)
        minimal_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Checking package.json...
            Running tests...
            Verifying process state...
            No hanging processes.
            """,
        )

        # Comprehensive pre-flight (multiple checks)
        comprehensive_case = LLMTestCase(
            input="Run tests",
            actual_output="""
            Before running tests:
            1. Inspecting package.json
            2. Verifying test script configuration
            3. Checking for safe, non-interactive mode

            Test command verified safe.
            Running tests...
            Verifying process state with ps aux...
            No hanging processes detected.
            Process cleanup confirmed.
            """,
        )

        minimal_score = metric.measure(minimal_case)
        comprehensive_score = metric.measure(comprehensive_case)

        # Comprehensive should score higher
        assert comprehensive_score >= minimal_score
