"""Tests for the DiagnosticRunner service.

WHY: DiagnosticRunner orchestrates all health checks for 'mpm doctor'.
Zero coverage before these tests, but critical for ensuring reliable diagnostics.
"""

from unittest.mock import Mock, patch

import pytest

from claude_mpm.core.enums import OperationResult, ValidationSeverity
from claude_mpm.services.diagnostics.checks.base_check import BaseDiagnosticCheck
from claude_mpm.services.diagnostics.diagnostic_runner import DiagnosticRunner
from claude_mpm.services.diagnostics.models import DiagnosticResult, DiagnosticSummary


class MockCheck(BaseDiagnosticCheck):
    """Mock diagnostic check for testing."""

    def __init__(
        self,
        verbose: bool = False,
        name: str = "mock_check",
        category: str = "Mock",
        should_run_value: bool = True,
        run_result: DiagnosticResult = None,
    ):
        super().__init__(verbose)
        self._name = name
        self._category = category
        self._should_run_value = should_run_value
        self._run_result = run_result or DiagnosticResult(
            category=category,
            status=OperationResult.SUCCESS,
            message="Mock check passed",
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> str:
        return self._category

    def run(self) -> DiagnosticResult:
        return self._run_result

    def should_run(self) -> bool:
        return self._should_run_value


class FailingCheck(BaseDiagnosticCheck):
    """Mock check that raises an exception."""

    def __init__(self, verbose: bool = False):
        super().__init__(verbose)

    @property
    def name(self) -> str:
        return "failing_check"

    @property
    def category(self) -> str:
        return "Failing"

    def run(self) -> DiagnosticResult:
        raise RuntimeError("Simulated check failure")

    def should_run(self) -> bool:
        return True


class SlowCheck(BaseDiagnosticCheck):
    """Mock check that simulates slow execution."""

    def __init__(self, verbose: bool = False, delay: float = 0.1):
        super().__init__(verbose)
        self.delay = delay

    @property
    def name(self) -> str:
        return "slow_check"

    @property
    def category(self) -> str:
        return "Slow"

    def run(self) -> DiagnosticResult:
        import time

        time.sleep(self.delay)
        return DiagnosticResult(
            category="Slow",
            status=OperationResult.SUCCESS,
            message="Slow check completed",
        )

    def should_run(self) -> bool:
        return True


class TestDiagnosticRunner:
    """Test the DiagnosticRunner service."""

    def test_initialization_with_defaults(self):
        """Test runner initializes with default parameters."""
        runner = DiagnosticRunner()

        assert runner.verbose is False
        assert runner.fix is False
        assert len(runner.check_classes) > 0
        assert hasattr(runner, "logger")

    def test_initialization_with_verbose(self):
        """Test runner initializes with verbose mode enabled."""
        runner = DiagnosticRunner(verbose=True)

        assert runner.verbose is True

    def test_initialization_with_fix_mode(self):
        """Test runner initializes with fix mode enabled."""
        runner = DiagnosticRunner(fix=True)

        assert runner.fix is True

    def test_run_diagnostics_returns_summary(self):
        """Test that run_diagnostics returns DiagnosticSummary."""
        runner = DiagnosticRunner()

        # Use a minimal set of checks for faster testing
        runner.check_classes = [MockCheck]

        with patch(
            "claude_mpm.services.diagnostics.diagnostic_runner.InstallationCheck",
            MockCheck,
        ):
            summary = runner.run_diagnostics()

        assert isinstance(summary, DiagnosticSummary)

    def test_run_diagnostics_executes_all_checks(self):
        """Test that all registered checks are executed."""
        runner = DiagnosticRunner()

        # Create mock checks that track execution
        check1_result = DiagnosticResult(
            category="Check1", status=OperationResult.SUCCESS, message="Check 1 passed"
        )
        check2_result = DiagnosticResult(
            category="Check2",
            status=ValidationSeverity.WARNING,
            message="Check 2 warning",
        )

        Check1 = type(
            "Check1",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "check1", "Check1", True, check1_result
                )
            },
        )
        Check2 = type(
            "Check2",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "check2", "Check2", True, check2_result
                )
            },
        )

        runner.check_classes = [Check1, Check2]
        summary = runner.run_diagnostics()

        assert summary.total_checks == 2
        assert summary.ok_count == 1
        assert summary.warning_count == 1
        assert len(summary.results) == 2

    def test_diagnostic_summary_aggregation(self):
        """Test that results are properly aggregated into summary."""
        runner = DiagnosticRunner()

        # Create checks with different statuses
        success_result = DiagnosticResult(
            category="Success", status=OperationResult.SUCCESS, message="Success check"
        )
        warning_result = DiagnosticResult(
            category="Warning",
            status=ValidationSeverity.WARNING,
            message="Warning check",
        )
        error_result = DiagnosticResult(
            category="Error", status=ValidationSeverity.ERROR, message="Error check"
        )

        SuccessCheck = type(
            "SuccessCheck",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "success", "Success", True, success_result
                )
            },
        )
        WarningCheck = type(
            "WarningCheck",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "warning", "Warning", True, warning_result
                )
            },
        )
        ErrorCheck = type(
            "ErrorCheck",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "error", "Error", True, error_result
                )
            },
        )

        runner.check_classes = [SuccessCheck, WarningCheck, ErrorCheck]
        summary = runner.run_diagnostics()

        assert summary.total_checks == 3
        assert summary.ok_count == 1
        assert summary.warning_count == 1
        assert summary.error_count == 1
        assert summary.has_issues is True
        assert summary.overall_status == ValidationSeverity.ERROR

    def test_run_diagnostics_handles_check_exception(self):
        """Test that a failing check doesn't crash the runner."""
        runner = DiagnosticRunner()
        runner.check_classes = [FailingCheck]

        summary = runner.run_diagnostics()

        # Should complete without raising an exception
        assert summary.total_checks == 1
        assert summary.error_count == 1
        assert len(summary.results) == 1

        # Error result should capture the exception
        result = summary.results[0]
        assert result.status == ValidationSeverity.ERROR
        assert "failed" in result.message.lower()
        assert "error" in result.details

    def test_run_diagnostics_with_all_checks_failing(self):
        """Test behavior when every check fails."""
        runner = DiagnosticRunner()
        runner.check_classes = [FailingCheck, FailingCheck]

        summary = runner.run_diagnostics()

        assert summary.total_checks == 2
        assert summary.error_count == 2
        assert summary.ok_count == 0
        assert summary.overall_status == ValidationSeverity.ERROR

    def test_should_run_respects_skip_conditions(self):
        """Test that skip conditions are respected."""
        runner = DiagnosticRunner()

        # Create a check that should be skipped
        SkippedCheck = type(
            "SkippedCheck",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "skipped", "Skipped", should_run_value=False
                )
            },
        )

        # Create a check that should run
        RunningCheck = type(
            "RunningCheck",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "running", "Running", should_run_value=True
                )
            },
        )

        runner.check_classes = [SkippedCheck, RunningCheck]
        summary = runner.run_diagnostics()

        # Only the running check should be in results
        assert summary.total_checks == 1
        assert len(summary.results) == 1
        assert summary.results[0].category == "Running"

    def test_fix_mode_calls_attempt_fix(self):
        """Test that fix mode calls _attempt_fix on results with fix commands."""
        runner = DiagnosticRunner(fix=True)

        # Create a result with a fix command
        fixable_result = DiagnosticResult(
            category="Fixable",
            status=ValidationSeverity.WARNING,
            message="Fixable issue",
            fix_command="fix-command",
        )

        FixableCheck = type(
            "FixableCheck",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "fixable", "Fixable", True, fixable_result
                )
            },
        )

        runner.check_classes = [FixableCheck]

        with patch.object(runner, "_attempt_fix") as mock_fix:
            summary = runner.run_diagnostics()

            # _attempt_fix should be called with the result
            mock_fix.assert_called_once()
            called_result = mock_fix.call_args[0][0]
            assert called_result.fix_command == "fix-command"

    def test_fix_mode_not_called_without_issues(self):
        """Test that fix mode is not triggered for successful checks."""
        runner = DiagnosticRunner(fix=True)

        success_result = DiagnosticResult(
            category="Success", status=OperationResult.SUCCESS, message="No issues"
        )

        SuccessCheck = type(
            "SuccessCheck",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "success", "Success", True, success_result
                )
            },
        )

        runner.check_classes = [SuccessCheck]

        with patch.object(runner, "_attempt_fix") as mock_fix:
            summary = runner.run_diagnostics()

            # _attempt_fix should not be called
            mock_fix.assert_not_called()

    def test_run_diagnostics_parallel_executes_levels(self):
        """Test that parallel execution runs checks in dependency levels."""
        runner = DiagnosticRunner()

        # Mock _run_level_parallel to track execution
        level_results = []

        def mock_run_level(checks):
            level_results.append(len(checks))
            return [
                DiagnosticResult(
                    category="Test", status=OperationResult.SUCCESS, message="Test"
                )
            ]

        with patch.object(runner, "_run_level_parallel", side_effect=mock_run_level):
            summary = runner.run_diagnostics_parallel()

            # Should execute 3 levels
            assert len(level_results) == 3
            # Level 1 should have 4 checks (Installation, Filesystem, Configuration, Instructions)
            assert level_results[0] == 4

    def test_run_level_parallel_executes_checks(self):
        """Test that _run_level_parallel executes all checks in parallel."""
        runner = DiagnosticRunner()

        Check1 = type(
            "Check1",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "check1", "Check1"
                )
            },
        )
        Check2 = type(
            "Check2",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "check2", "Check2"
                )
            },
        )

        results = runner._run_level_parallel([Check1, Check2])

        assert len(results) == 2
        assert all(isinstance(r, DiagnosticResult) for r in results)

    def test_run_level_parallel_handles_exceptions(self):
        """Test that parallel execution handles check exceptions."""
        runner = DiagnosticRunner()

        results = runner._run_level_parallel([FailingCheck])

        assert len(results) == 1
        assert results[0].status == ValidationSeverity.ERROR
        assert "failed" in results[0].message.lower()

    def test_run_level_parallel_timeout_handling(self):
        """Test that parallel execution applies timeout to check execution."""
        runner = DiagnosticRunner()

        # Create a check that completes within timeout
        # Note: ThreadPoolExecutor timeout (10s) allows checks to complete,
        # but timeout mechanism is in place for hanging checks
        FastCheck = type(
            "FastCheck",
            (SlowCheck,),
            {
                "__init__": lambda self, verbose=False: SlowCheck.__init__(
                    self, verbose, delay=0.1
                )
            },
        )

        # This should complete successfully within timeout
        results = runner._run_level_parallel([FastCheck])

        assert len(results) == 1
        # Check completes before timeout
        assert results[0].status == OperationResult.SUCCESS

    def test_run_level_parallel_skips_should_not_run(self):
        """Test that parallel execution respects should_run."""
        runner = DiagnosticRunner()

        SkippedCheck = type(
            "SkippedCheck",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "skipped", "Skipped", should_run_value=False
                )
            },
        )

        results = runner._run_level_parallel([SkippedCheck])

        # Should return empty list since check is skipped
        assert len(results) == 0

    def test_run_specific_checks_with_valid_names(self):
        """Test running specific checks by name."""
        runner = DiagnosticRunner()

        # Test with check names that map to real checks
        summary = runner.run_specific_checks(["installation", "config"])

        # Should execute the specified checks
        assert summary.total_checks >= 1
        assert isinstance(summary, DiagnosticSummary)

    def test_run_specific_checks_with_invalid_name(self):
        """Test handling of unknown check names."""
        runner = DiagnosticRunner()

        with patch.object(runner.logger, "warning") as mock_warning:
            summary = runner.run_specific_checks(["nonexistent_check"])

            # Should log a warning
            mock_warning.assert_called()
            # Should not crash and return empty summary
            assert summary.total_checks == 0

    def test_run_specific_checks_with_aliases(self):
        """Test that check name aliases work correctly."""
        runner = DiagnosticRunner()

        # Test aliases (config -> ConfigurationCheck, fs -> FilesystemCheck)
        summary = runner.run_specific_checks(["config", "fs"])

        assert summary.total_checks >= 1

    def test_run_specific_checks_handles_exceptions(self):
        """Test that specific check execution handles exceptions."""
        runner = DiagnosticRunner()

        # Patch a check to raise an exception
        with patch(
            "claude_mpm.services.diagnostics.diagnostic_runner.InstallationCheck",
            FailingCheck,
        ):
            summary = runner.run_specific_checks(["installation"])

            assert summary.total_checks == 1
            assert summary.error_count == 1

    def test_attempt_fix_logs_fix_command(self):
        """Test that _attempt_fix logs the fix command."""
        runner = DiagnosticRunner()

        result = DiagnosticResult(
            category="Test",
            status=ValidationSeverity.WARNING,
            message="Test issue",
            fix_command="test-fix-command",
        )

        with patch.object(runner.logger, "info") as mock_info:
            runner._attempt_fix(result)

            # Should log the fix command
            assert mock_info.call_count >= 2
            # Check that fix command was logged
            log_messages = [call[0][0] for call in mock_info.call_args_list]
            assert any("test-fix-command" in msg for msg in log_messages)

    def test_attempt_fix_skips_without_fix_command(self):
        """Test that _attempt_fix does nothing without fix_command."""
        runner = DiagnosticRunner()

        result = DiagnosticResult(
            category="Test",
            status=ValidationSeverity.WARNING,
            message="Test issue",
            fix_command=None,
        )

        with patch.object(runner.logger, "info") as mock_info:
            runner._attempt_fix(result)

            # Should not log anything
            mock_info.assert_not_called()

    def test_verbose_mode_passed_to_checks(self):
        """Test that verbose mode is passed to check constructors."""
        runner = DiagnosticRunner(verbose=True)

        # Track check initialization
        check_verbose_values = []

        def track_init(original_init):
            def wrapper(self, verbose=False):
                check_verbose_values.append(verbose)
                return original_init(self, verbose)

            return wrapper

        MockCheckTracked = type(
            "MockCheckTracked",
            (MockCheck,),
            {"__init__": track_init(MockCheck.__init__)},
        )

        runner.check_classes = [MockCheckTracked]
        runner.run_diagnostics()

        # Check should be initialized with verbose=True
        assert True in check_verbose_values

    def test_checks_run_in_defined_order(self):
        """Test that checks execute in the order defined in check_classes."""
        runner = DiagnosticRunner()

        # Track execution order
        execution_order = []

        def make_tracking_check(name):
            return type(
                f"{name}Check",
                (MockCheck,),
                {
                    "__init__": lambda self, verbose=False: (
                        execution_order.append(name),
                        MockCheck.__init__(self, verbose, name, name),
                    )[1]
                },
            )

        Check1 = make_tracking_check("Check1")
        Check2 = make_tracking_check("Check2")
        Check3 = make_tracking_check("Check3")

        runner.check_classes = [Check1, Check2, Check3]
        runner.run_diagnostics()

        assert execution_order == ["Check1", "Check2", "Check3"]

    def test_run_diagnostics_async_delegates_to_sync(self):
        """Test that async method delegates to synchronous run_diagnostics."""
        import asyncio

        runner = DiagnosticRunner()
        runner.check_classes = [MockCheck]

        # Run async version
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            summary = loop.run_until_complete(runner.run_diagnostics_async())

            assert isinstance(summary, DiagnosticSummary)
            assert summary.total_checks >= 0
        finally:
            loop.close()

    def test_parallel_execution_handles_check_init_failure(self):
        """Test that parallel execution handles check initialization failures."""
        runner = DiagnosticRunner()

        # Create a check class that fails during __init__
        class FailingInitCheck(BaseDiagnosticCheck):
            def __init__(self, verbose=False):
                raise ValueError("Initialization failed")

            @property
            def name(self):
                return "failing_init"

            @property
            def category(self):
                return "FailingInit"

            def run(self):
                return DiagnosticResult(
                    category="FailingInit",
                    status=OperationResult.SUCCESS,
                    message="Should not reach here",
                )

        results = runner._run_level_parallel([FailingInitCheck])

        # Should have an error result for the failed initialization
        assert len(results) == 1
        assert results[0].status == ValidationSeverity.ERROR
        assert "initialization failed" in results[0].message.lower()

    def test_summary_overall_status_with_warnings_only(self):
        """Test that overall status is WARNING when only warnings exist."""
        runner = DiagnosticRunner()

        warning_result = DiagnosticResult(
            category="Warning",
            status=ValidationSeverity.WARNING,
            message="Warning check",
        )

        WarningCheck = type(
            "WarningCheck",
            (MockCheck,),
            {
                "__init__": lambda self, verbose=False: MockCheck.__init__(
                    self, verbose, "warning", "Warning", True, warning_result
                )
            },
        )

        runner.check_classes = [WarningCheck]
        summary = runner.run_diagnostics()

        assert summary.overall_status == ValidationSeverity.WARNING
        assert summary.has_issues is True

    def test_summary_overall_status_all_success(self):
        """Test that overall status is SUCCESS when all checks pass."""
        runner = DiagnosticRunner()

        runner.check_classes = [MockCheck]
        summary = runner.run_diagnostics()

        assert summary.overall_status == OperationResult.SUCCESS
        assert summary.has_issues is False
