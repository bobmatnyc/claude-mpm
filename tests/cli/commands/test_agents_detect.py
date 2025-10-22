"""
Tests for Agents Detect CLI Command
====================================

WHY: Tests for the agents detect command to ensure reliable toolchain
detection and proper output formatting.

Part of TSK-0054: Auto-Configuration Feature - Phase 5
"""

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.cli.commands.agents_detect import AgentsDetectCommand
from claude_mpm.cli.shared import CommandResult
from claude_mpm.services.core.models.toolchain import ToolchainAnalysis


class TestAgentsDetectCommand:
    """Test suite for AgentsDetectCommand."""

    @pytest.fixture
    def command(self):
        """Create command instance."""
        return AgentsDetectCommand()

    @pytest.fixture
    def mock_toolchain_analyzer(self):
        """Create mock toolchain analyzer."""
        analyzer = Mock()
        analyzer.analyze_project = Mock()
        return analyzer

    @pytest.fixture
    def sample_analysis(self):
        """Create sample toolchain analysis."""
        analysis = Mock(spec=ToolchainAnalysis)
        analysis.project_path = "/test/project"
        analysis.analysis_time = 1.5
        analysis.languages = []
        analysis.frameworks = []
        analysis.deployment_targets = []
        analysis.components = []
        return analysis

    def test_validate_args_valid(self, command):
        """Test argument validation with valid arguments."""
        args = Namespace(project_path=Path.cwd(), json=False, verbose=False)

        error = command.validate_args(args)
        assert error is None

    def test_validate_args_invalid_path(self, command):
        """Test argument validation with invalid path."""
        args = Namespace(
            project_path=Path("/nonexistent/path"), json=False, verbose=False
        )

        error = command.validate_args(args)
        assert error is not None
        assert "does not exist" in error

    @patch("claude_mpm.cli.commands.agents_detect.ToolchainAnalyzerService")
    def test_run_success(
        self, mock_service_class, command, sample_analysis, mock_toolchain_analyzer
    ):
        """Test successful toolchain detection."""
        mock_toolchain_analyzer.analyze_project.return_value = sample_analysis
        mock_service_class.return_value = mock_toolchain_analyzer
        command._toolchain_analyzer = mock_toolchain_analyzer

        args = Namespace(
            project_path=Path.cwd(),
            json=False,
            verbose=False,
            debug=False,
            quiet=False,
        )

        result = command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success
        mock_toolchain_analyzer.analyze_project.assert_called_once()

    @patch("claude_mpm.cli.commands.agents_detect.ToolchainAnalyzerService")
    def test_run_json_output(
        self, mock_service_class, command, sample_analysis, mock_toolchain_analyzer
    ):
        """Test JSON output format."""
        mock_toolchain_analyzer.analyze_project.return_value = sample_analysis
        mock_service_class.return_value = mock_toolchain_analyzer
        command._toolchain_analyzer = mock_toolchain_analyzer

        args = Namespace(
            project_path=Path.cwd(),
            json=True,
            verbose=False,
            debug=False,
            quiet=False,
        )

        with patch("builtins.print") as mock_print:
            result = command.run(args)

            assert result.success
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            data = json.loads(output)
            assert "project_path" in data
            assert "languages" in data
            assert "frameworks" in data

    @patch("claude_mpm.cli.commands.agents_detect.ToolchainAnalyzerService")
    def test_run_verbose_output(
        self, mock_service_class, command, sample_analysis, mock_toolchain_analyzer
    ):
        """Test verbose output includes evidence."""
        # Add language with evidence
        lang = Mock()
        lang.language = "Python"
        lang.version = "3.12"
        lang.confidence = 0.95
        lang.evidence = ["requirements.txt", "setup.py"]
        sample_analysis.languages = [lang]

        mock_toolchain_analyzer.analyze_project.return_value = sample_analysis
        mock_service_class.return_value = mock_toolchain_analyzer
        command._toolchain_analyzer = mock_toolchain_analyzer

        args = Namespace(
            project_path=Path.cwd(),
            json=False,
            verbose=True,
            debug=False,
            quiet=False,
        )

        result = command.run(args)

        assert result.success
        mock_toolchain_analyzer.analyze_project.assert_called_once()

    @patch("claude_mpm.cli.commands.agents_detect.ToolchainAnalyzerService")
    def test_run_keyboard_interrupt(
        self, mock_service_class, command, mock_toolchain_analyzer
    ):
        """Test handling of keyboard interrupt."""
        mock_toolchain_analyzer.analyze_project.side_effect = KeyboardInterrupt()
        mock_service_class.return_value = mock_toolchain_analyzer
        command._toolchain_analyzer = mock_toolchain_analyzer

        args = Namespace(
            project_path=Path.cwd(),
            json=False,
            verbose=False,
            debug=False,
            quiet=False,
        )

        result = command.run(args)

        assert not result.success
        assert result.exit_code == 130

    @patch("claude_mpm.cli.commands.agents_detect.ToolchainAnalyzerService")
    def test_run_exception_handling(
        self, mock_service_class, command, mock_toolchain_analyzer
    ):
        """Test exception handling."""
        mock_toolchain_analyzer.analyze_project.side_effect = Exception("Test error")
        mock_service_class.return_value = mock_toolchain_analyzer
        command._toolchain_analyzer = mock_toolchain_analyzer

        args = Namespace(
            project_path=Path.cwd(),
            json=False,
            verbose=False,
            debug=False,
            quiet=False,
        )

        result = command.run(args)

        assert not result.success
        assert "Test error" in result.message

    @patch("claude_mpm.cli.commands.agents_detect.ToolchainAnalyzerService")
    def test_display_results_with_components(
        self, mock_service_class, command, sample_analysis, mock_toolchain_analyzer
    ):
        """Test display with detected components."""
        # Add components
        comp = Mock()
        comp.type = Mock(value="language")
        comp.name = "Python"
        comp.version = "3.12"
        comp.confidence = 0.95
        sample_analysis.components = [comp]

        mock_service_class.return_value = mock_toolchain_analyzer
        command._toolchain_analyzer = mock_toolchain_analyzer

        result = command._display_results(sample_analysis, verbose=False)

        assert result.success

    @patch("claude_mpm.cli.commands.agents_detect.ToolchainAnalyzerService")
    def test_output_json_with_verbose(
        self, mock_service_class, command, sample_analysis, mock_toolchain_analyzer
    ):
        """Test JSON output with verbose flag includes evidence."""
        lang = Mock()
        lang.language = "Python"
        lang.version = "3.12"
        lang.confidence = 0.95
        lang.evidence = ["requirements.txt"]
        sample_analysis.languages = [lang]

        mock_service_class.return_value = mock_toolchain_analyzer
        command._toolchain_analyzer = mock_toolchain_analyzer

        with patch("builtins.print") as mock_print:
            result = command._output_json(sample_analysis, verbose=True)

            assert result.success
            output = mock_print.call_args[0][0]
            data = json.loads(output)
            assert data["languages"][0]["evidence"] is not None
