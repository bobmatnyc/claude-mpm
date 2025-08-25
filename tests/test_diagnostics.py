"""
Unit tests for the diagnostic system.

WHY: Ensure diagnostic checks work correctly and provide accurate results
across different system states and configurations.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.diagnostics import (
    DiagnosticResult,
    DiagnosticRunner,
    DiagnosticStatus,
    DiagnosticSummary,
    DoctorReporter,
)
from claude_mpm.services.diagnostics.checks import (
    AgentCheck,
    BaseDiagnosticCheck,
    ConfigurationCheck,
    InstallationCheck,
)


class TestDiagnosticModels(unittest.TestCase):
    """Test diagnostic data models."""

    def test_diagnostic_result_creation(self):
        """Test creating a diagnostic result."""
        result = DiagnosticResult(
            category="Test",
            status=DiagnosticStatus.OK,
            message="Test passed",
            details={"key": "value"},
            fix_command="test fix",
            fix_description="Fix description",
        )

        self.assertEqual(result.category, "Test")
        self.assertEqual(result.status, DiagnosticStatus.OK)
        self.assertEqual(result.message, "Test passed")
        self.assertEqual(result.details["key"], "value")
        self.assertEqual(result.fix_command, "test fix")
        self.assertFalse(result.has_issues)

    def test_diagnostic_result_serialization(self):
        """Test converting result to dictionary."""
        result = DiagnosticResult(
            category="Test",
            status=DiagnosticStatus.WARNING,
            message="Test warning",
            details={"count": 5},
        )

        data = result.to_dict()
        self.assertEqual(data["category"], "Test")
        self.assertEqual(data["status"], "warning")
        self.assertEqual(data["message"], "Test warning")
        self.assertEqual(data["details"]["count"], 5)
        self.assertTrue(result.has_issues)

    def test_diagnostic_summary(self):
        """Test diagnostic summary aggregation."""
        summary = DiagnosticSummary()

        # Add various results
        summary.add_result(
            DiagnosticResult(category="Test1", status=DiagnosticStatus.OK, message="OK")
        )
        summary.add_result(
            DiagnosticResult(
                category="Test2", status=DiagnosticStatus.WARNING, message="Warning"
            )
        )
        summary.add_result(
            DiagnosticResult(
                category="Test3", status=DiagnosticStatus.ERROR, message="Error"
            )
        )

        self.assertEqual(summary.total_checks, 3)
        self.assertEqual(summary.ok_count, 1)
        self.assertEqual(summary.warning_count, 1)
        self.assertEqual(summary.error_count, 1)
        self.assertTrue(summary.has_issues)
        self.assertEqual(summary.overall_status, DiagnosticStatus.ERROR)


class TestDiagnosticChecks(unittest.TestCase):
    """Test individual diagnostic checks."""

    def test_base_check_interface(self):
        """Test base diagnostic check interface."""

        class TestCheck(BaseDiagnosticCheck):
            @property
            def name(self):
                return "test_check"

            @property
            def category(self):
                return "Test"

            def run(self):
                return DiagnosticResult(
                    category=self.category,
                    status=DiagnosticStatus.OK,
                    message="Test passed",
                )

        check = TestCheck()
        self.assertEqual(check.name, "test_check")
        self.assertEqual(check.category, "Test")
        self.assertTrue(check.should_run())

        result = check.run()
        self.assertEqual(result.status, DiagnosticStatus.OK)

    @patch("claude_mpm.services.diagnostics.checks.installation_check.sys.version_info")
    def test_installation_check_python_version(self, mock_version):
        """Test Python version checking."""
        check = InstallationCheck()

        # Test with old Python version
        mock_version.major = 3
        mock_version.minor = 8
        result = check._check_python_version()
        self.assertEqual(result.status, DiagnosticStatus.ERROR)

        # Test with recommended version
        mock_version.major = 3
        mock_version.minor = 11
        result = check._check_python_version()
        self.assertEqual(result.status, DiagnosticStatus.OK)

    @patch("claude_mpm.services.diagnostics.checks.configuration_check.Path")
    def test_configuration_check(self, mock_path):
        """Test configuration checking."""
        check = ConfigurationCheck()

        # Mock config file doesn't exist
        mock_config = MagicMock()
        mock_config.exists.return_value = False
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value = mock_config

        result = check._check_user_config()
        self.assertEqual(result.status, DiagnosticStatus.OK)
        self.assertIn("No user configuration", result.message)

    @patch("claude_mpm.services.diagnostics.checks.agent_check.Path")
    def test_agent_check_no_agents(self, mock_path):
        """Test agent check with no deployed agents."""
        check = AgentCheck()

        # Mock agents directory doesn't exist
        mock_agents_dir = MagicMock()
        mock_agents_dir.exists.return_value = False
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value = (
            mock_agents_dir
        )

        result = check._check_deployed_agents()
        self.assertEqual(result.status, DiagnosticStatus.ERROR)
        self.assertIn("does not exist", result.message)


class TestDiagnosticRunner(unittest.TestCase):
    """Test diagnostic runner orchestration."""

    def test_runner_initialization(self):
        """Test runner initialization."""
        runner = DiagnosticRunner(verbose=True, fix=False)
        self.assertTrue(runner.verbose)
        self.assertFalse(runner.fix)
        self.assertTrue(len(runner.check_classes) > 0)

    @patch("claude_mpm.services.diagnostics.diagnostic_runner.InstallationCheck")
    def test_run_diagnostics(self, mock_check_class):
        """Test running diagnostics."""
        # Mock a check
        mock_check = MagicMock()
        mock_check.should_run.return_value = True
        mock_check.run.return_value = DiagnosticResult(
            category="Test", status=DiagnosticStatus.OK, message="Test passed"
        )
        mock_check_class.return_value = mock_check

        runner = DiagnosticRunner()
        runner.check_classes = [mock_check_class]

        summary = runner.run_diagnostics()

        self.assertEqual(summary.total_checks, 1)
        self.assertEqual(summary.ok_count, 1)
        mock_check.run.assert_called_once()

    def test_run_specific_checks(self):
        """Test running specific checks."""
        runner = DiagnosticRunner()

        # Run only installation check
        summary = runner.run_specific_checks(["installation"])

        # Should have run at least one check
        self.assertGreater(summary.total_checks, 0)

    @patch("claude_mpm.services.diagnostics.diagnostic_runner.ThreadPoolExecutor")
    def test_parallel_execution(self, mock_executor):
        """Test parallel diagnostic execution."""
        # Mock executor
        mock_executor.return_value.__enter__ = MagicMock()
        mock_executor.return_value.__exit__ = MagicMock()
        mock_executor.return_value.submit = MagicMock()

        runner = DiagnosticRunner()
        runner._run_level_parallel([InstallationCheck])

        # Verify thread pool was used
        mock_executor.assert_called()


class TestDoctorReporter(unittest.TestCase):
    """Test diagnostic result reporting."""

    def test_reporter_initialization(self):
        """Test reporter initialization."""
        reporter = DoctorReporter(use_color=True, verbose=True)
        self.assertTrue(reporter.verbose)

    def test_json_output(self):
        """Test JSON output format."""
        summary = DiagnosticSummary()
        summary.add_result(
            DiagnosticResult(
                category="Test", status=DiagnosticStatus.OK, message="Test passed"
            )
        )

        reporter = DoctorReporter()

        # Capture output
        import sys
        from io import StringIO

        captured = StringIO()
        sys.stdout = captured

        reporter._report_json(summary)

        sys.stdout = sys.__stdout__
        output = captured.getvalue()

        # Verify JSON structure
        data = json.loads(output)
        self.assertIn("summary", data)
        self.assertIn("results", data)
        self.assertEqual(data["summary"]["total_checks"], 1)

    def test_terminal_output(self):
        """Test terminal output format."""
        summary = DiagnosticSummary()
        summary.add_result(
            DiagnosticResult(
                category="Test",
                status=DiagnosticStatus.WARNING,
                message="Test warning",
                fix_command="test fix",
                fix_description="Fix this issue",
            )
        )

        reporter = DoctorReporter(use_color=False)

        # Capture output
        import sys
        from io import StringIO

        captured = StringIO()
        sys.stdout = captured

        reporter._report_terminal(summary)

        sys.stdout = sys.__stdout__
        output = captured.getvalue()

        # Verify output contains key elements
        self.assertIn("Claude MPM Doctor Report", output)
        self.assertIn("Test: Warning", output)
        self.assertIn("test fix", output)
        self.assertIn("Summary:", output)

    def test_markdown_output(self):
        """Test Markdown output format."""
        summary = DiagnosticSummary()
        summary.add_result(
            DiagnosticResult(
                category="Test", status=DiagnosticStatus.ERROR, message="Test error"
            )
        )

        reporter = DoctorReporter()

        # Capture output
        import sys
        from io import StringIO

        captured = StringIO()
        sys.stdout = captured

        reporter._report_markdown(summary)

        sys.stdout = sys.__stdout__
        output = captured.getvalue()

        # Verify Markdown structure
        self.assertIn("# Claude MPM Doctor Report", output)
        self.assertIn("## Summary", output)
        self.assertIn("| Status | Count |", output)
        self.assertIn("## Diagnostic Results", output)


class TestDoctorCommand(unittest.TestCase):
    """Test doctor CLI command."""

    @patch("claude_mpm.cli.commands.doctor.DiagnosticRunner")
    @patch("claude_mpm.cli.commands.doctor.DoctorReporter")
    def test_doctor_command_execution(self, mock_reporter, mock_runner):
        """Test doctor command execution."""
        from claude_mpm.cli.commands.doctor import doctor_command

        # Mock runner
        mock_summary = DiagnosticSummary()
        mock_runner.return_value.run_diagnostics.return_value = mock_summary

        # Mock args
        args = MagicMock()
        args.verbose = False
        args.fix = False
        args.json = False
        args.markdown = False
        args.checks = None
        args.parallel = False
        args.no_color = False
        args.output = None

        # Run command
        exit_code = doctor_command(args)

        # Verify execution
        self.assertEqual(exit_code, 0)  # No issues
        mock_runner.return_value.run_diagnostics.assert_called_once()
        mock_reporter.return_value.report.assert_called_once()

    @patch("claude_mpm.cli.commands.doctor.DiagnosticRunner")
    def test_doctor_command_with_errors(self, mock_runner):
        """Test doctor command with errors."""
        from claude_mpm.cli.commands.doctor import doctor_command

        # Mock runner with errors
        mock_summary = DiagnosticSummary()
        mock_summary.error_count = 2
        mock_runner.return_value.run_diagnostics.return_value = mock_summary

        # Mock args
        args = MagicMock()
        args.verbose = False
        args.fix = False
        args.json = True
        args.markdown = False
        args.checks = None
        args.parallel = False
        args.no_color = True
        args.output = None

        # Run command
        exit_code = doctor_command(args)

        # Should return error code
        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
