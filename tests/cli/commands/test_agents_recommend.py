"""
Tests for Agents Recommend CLI Command
=======================================

WHY: Tests for the agents recommend command to ensure reliable agent
recommendations with proper reasoning and output formatting.

Part of TSK-0054: Auto-Configuration Feature - Phase 5
"""

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.cli.commands.agents_recommend import AgentsRecommendCommand
from claude_mpm.cli.shared import CommandResult
from claude_mpm.services.core.models.agent_config import AgentRecommendation
from claude_mpm.services.core.models.toolchain import ToolchainAnalysis


class TestAgentsRecommendCommand:
    """Test suite for AgentsRecommendCommand."""

    @pytest.fixture
    def command(self):
        """Create command instance."""
        return AgentsRecommendCommand()

    @pytest.fixture
    def mock_toolchain_analyzer(self):
        """Create mock toolchain analyzer."""
        analyzer = Mock()
        analyzer.analyze_project = Mock()
        return analyzer

    @pytest.fixture
    def mock_agent_recommender(self):
        """Create mock agent recommender."""
        recommender = Mock()
        recommender.recommend_agents = Mock()
        return recommender

    @pytest.fixture
    def sample_analysis(self):
        """Create sample toolchain analysis."""
        analysis = Mock(spec=ToolchainAnalysis)
        analysis.project_path = "/test/project"
        analysis.languages = []
        analysis.frameworks = []
        analysis.deployment_targets = []
        return analysis

    @pytest.fixture
    def sample_recommendations(self):
        """Create sample recommendations."""
        return [
            Mock(
                spec=AgentRecommendation,
                agent_id="python-engineer",
                confidence=0.95,
                priority=1,
                reasoning="Python 3.12 detected",
                matched_capabilities=["python", "pip"],
                requirements=[],
            )
        ]

    def test_validate_args_valid(self, command):
        """Test argument validation with valid arguments."""
        args = Namespace(
            project_path=Path.cwd(),
            min_confidence=0.8,
            json=False,
            show_reasoning=True,
        )

        error = command.validate_args(args)
        assert error is None

    def test_validate_args_invalid_path(self, command):
        """Test argument validation with invalid path."""
        args = Namespace(
            project_path=Path("/nonexistent/path"),
            min_confidence=0.8,
            json=False,
            show_reasoning=True,
        )

        error = command.validate_args(args)
        assert error is not None
        assert "does not exist" in error

    def test_validate_args_invalid_confidence(self, command):
        """Test argument validation with invalid confidence."""
        args = Namespace(
            project_path=Path.cwd(),
            min_confidence=1.5,
            json=False,
            show_reasoning=True,
        )

        error = command.validate_args(args)
        assert error is not None
        assert "between 0.0 and 1.0" in error

    @patch("claude_mpm.cli.commands.agents_recommend.AgentRecommenderService")
    @patch("claude_mpm.cli.commands.agents_recommend.ToolchainAnalyzerService")
    def test_run_success(
        self,
        mock_analyzer_class,
        mock_recommender_class,
        command,
        sample_analysis,
        sample_recommendations,
        mock_toolchain_analyzer,
        mock_agent_recommender,
    ):
        """Test successful recommendation generation."""
        mock_toolchain_analyzer.analyze_project.return_value = sample_analysis
        mock_agent_recommender.recommend_agents.return_value = sample_recommendations

        mock_analyzer_class.return_value = mock_toolchain_analyzer
        mock_recommender_class.return_value = mock_agent_recommender

        command._toolchain_analyzer = mock_toolchain_analyzer
        command._agent_recommender = mock_agent_recommender

        args = Namespace(
            project_path=Path.cwd(),
            min_confidence=0.8,
            json=False,
            show_reasoning=True,
            debug=False,
            verbose=False,
            quiet=False,
        )

        result = command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success
        mock_toolchain_analyzer.analyze_project.assert_called_once()
        mock_agent_recommender.recommend_agents.assert_called_once()

    @patch("claude_mpm.cli.commands.agents_recommend.AgentRecommenderService")
    @patch("claude_mpm.cli.commands.agents_recommend.ToolchainAnalyzerService")
    def test_run_json_output(
        self,
        mock_analyzer_class,
        mock_recommender_class,
        command,
        sample_analysis,
        sample_recommendations,
        mock_toolchain_analyzer,
        mock_agent_recommender,
    ):
        """Test JSON output format."""
        mock_toolchain_analyzer.analyze_project.return_value = sample_analysis
        mock_agent_recommender.recommend_agents.return_value = sample_recommendations

        mock_analyzer_class.return_value = mock_toolchain_analyzer
        mock_recommender_class.return_value = mock_agent_recommender

        command._toolchain_analyzer = mock_toolchain_analyzer
        command._agent_recommender = mock_agent_recommender

        args = Namespace(
            project_path=Path.cwd(),
            min_confidence=0.8,
            json=True,
            show_reasoning=True,
            debug=False,
            verbose=False,
            quiet=False,
        )

        with patch("builtins.print") as mock_print:
            result = command.run(args)

            assert result.success
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            data = json.loads(output)
            assert "project_path" in data
            assert "recommendations" in data
            assert len(data["recommendations"]) == 1

    @patch("claude_mpm.cli.commands.agents_recommend.AgentRecommenderService")
    @patch("claude_mpm.cli.commands.agents_recommend.ToolchainAnalyzerService")
    def test_run_no_recommendations(
        self,
        mock_analyzer_class,
        mock_recommender_class,
        command,
        sample_analysis,
        mock_toolchain_analyzer,
        mock_agent_recommender,
    ):
        """Test when no recommendations are found."""
        mock_toolchain_analyzer.analyze_project.return_value = sample_analysis
        mock_agent_recommender.recommend_agents.return_value = []

        mock_analyzer_class.return_value = mock_toolchain_analyzer
        mock_recommender_class.return_value = mock_agent_recommender

        command._toolchain_analyzer = mock_toolchain_analyzer
        command._agent_recommender = mock_agent_recommender

        args = Namespace(
            project_path=Path.cwd(),
            min_confidence=0.8,
            json=False,
            show_reasoning=True,
            debug=False,
            verbose=False,
            quiet=False,
        )

        result = command.run(args)

        assert result.success

    @patch("claude_mpm.cli.commands.agents_recommend.AgentRecommenderService")
    @patch("claude_mpm.cli.commands.agents_recommend.ToolchainAnalyzerService")
    def test_run_keyboard_interrupt(
        self,
        mock_analyzer_class,
        mock_recommender_class,
        command,
        mock_toolchain_analyzer,
        mock_agent_recommender,
    ):
        """Test handling of keyboard interrupt."""
        mock_toolchain_analyzer.analyze_project.side_effect = KeyboardInterrupt()

        mock_analyzer_class.return_value = mock_toolchain_analyzer
        mock_recommender_class.return_value = mock_agent_recommender

        command._toolchain_analyzer = mock_toolchain_analyzer
        command._agent_recommender = mock_agent_recommender

        args = Namespace(
            project_path=Path.cwd(),
            min_confidence=0.8,
            json=False,
            show_reasoning=True,
            debug=False,
            verbose=False,
            quiet=False,
        )

        result = command.run(args)

        assert not result.success
        assert result.exit_code == 130

    @patch("claude_mpm.cli.commands.agents_recommend.AgentRecommenderService")
    @patch("claude_mpm.cli.commands.agents_recommend.ToolchainAnalyzerService")
    def test_run_exception_handling(
        self,
        mock_analyzer_class,
        mock_recommender_class,
        command,
        mock_toolchain_analyzer,
        mock_agent_recommender,
    ):
        """Test exception handling."""
        mock_toolchain_analyzer.analyze_project.side_effect = Exception("Test error")

        mock_analyzer_class.return_value = mock_toolchain_analyzer
        mock_recommender_class.return_value = mock_agent_recommender

        command._toolchain_analyzer = mock_toolchain_analyzer
        command._agent_recommender = mock_agent_recommender

        args = Namespace(
            project_path=Path.cwd(),
            min_confidence=0.8,
            json=False,
            show_reasoning=True,
            debug=False,
            verbose=False,
            quiet=False,
        )

        result = command.run(args)

        assert not result.success
        assert "Test error" in result.message

    @patch("claude_mpm.cli.commands.agents_recommend.AgentRecommenderService")
    @patch("claude_mpm.cli.commands.agents_recommend.ToolchainAnalyzerService")
    def test_display_results_without_reasoning(
        self,
        mock_analyzer_class,
        mock_recommender_class,
        command,
        sample_analysis,
        sample_recommendations,
        mock_toolchain_analyzer,
        mock_agent_recommender,
    ):
        """Test display without detailed reasoning."""
        mock_analyzer_class.return_value = mock_toolchain_analyzer
        mock_recommender_class.return_value = mock_agent_recommender

        command._toolchain_analyzer = mock_toolchain_analyzer
        command._agent_recommender = mock_agent_recommender

        result = command._display_results(
            sample_recommendations, sample_analysis, show_reasoning=False
        )

        assert result.success

    @patch("claude_mpm.cli.commands.agents_recommend.AgentRecommenderService")
    @patch("claude_mpm.cli.commands.agents_recommend.ToolchainAnalyzerService")
    def test_output_json_complete(
        self,
        mock_analyzer_class,
        mock_recommender_class,
        command,
        sample_analysis,
        sample_recommendations,
        mock_toolchain_analyzer,
        mock_agent_recommender,
    ):
        """Test JSON output includes all recommendation details."""
        mock_analyzer_class.return_value = mock_toolchain_analyzer
        mock_recommender_class.return_value = mock_agent_recommender

        command._toolchain_analyzer = mock_toolchain_analyzer
        command._agent_recommender = mock_agent_recommender

        with patch("builtins.print") as mock_print:
            result = command._output_json(sample_recommendations, sample_analysis)

            assert result.success
            output = mock_print.call_args[0][0]
            data = json.loads(output)
            assert "recommendations" in data
            rec = data["recommendations"][0]
            assert "agent_id" in rec
            assert "confidence" in rec
            assert "reasoning" in rec
            assert "matched_capabilities" in rec
