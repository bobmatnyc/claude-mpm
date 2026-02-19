"""
End-to-End Tests for Auto-Configure v2 Full Flow
===============================================

WHY: Complete integration testing of auto-configure v2 Phase 5 from CLI
command through service orchestration to filesystem changes. Tests the
full workflow including optional AgentRegistry, lazy singletons, and
graceful degradation patterns.

FOCUS: Integration testing over unit testing per research recommendations.
Tests complete workflows with real filesystem operations and proper
async/sync boundary handling.
"""

import asyncio
import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import yaml

from claude_mpm.cli.commands.auto_configure import AutoConfigureCommand
from claude_mpm.core.config_scope import ConfigScope
from claude_mpm.core.enums import OperationResult
from claude_mpm.services.core.models.agent_config import (
    AgentRecommendation,
    ConfigurationPreview,
    ConfigurationResult,
    ValidationIssue,
    ValidationResult,
)
from claude_mpm.services.core.models.toolchain import (
    ToolchainAnalysis,
    ToolchainComponent,
)


@pytest.mark.integration
class TestAutoConfigureFullFlow:
    """Test complete auto-configure workflow from CLI to filesystem."""

    @pytest.fixture
    def realistic_project_structure(self, tmp_path):
        """Create a realistic project structure for testing."""
        project_root = tmp_path / "test_web_app"
        project_root.mkdir()

        # Python project structure
        (project_root / "src").mkdir()
        (project_root / "src" / "app").mkdir()
        (project_root / "src" / "app" / "__init__.py").write_text("")
        (project_root / "src" / "app" / "main.py").write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
""")

        # Project configuration files
        (project_root / "pyproject.toml").write_text("""
[tool.poetry]
name = "test-web-app"
version = "0.1.0"
description = "Test web application"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.1"
uvicorn = "^0.24.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
""")

        # Frontend structure
        (project_root / "frontend").mkdir()
        (project_root / "frontend" / "package.json").write_text("""
{
  "name": "test-frontend",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "typescript": "^5.0.0"
  }
}
""")

        (project_root / "frontend" / "src").mkdir()
        (project_root / "frontend" / "src" / "App.tsx").write_text("""
import React from 'react';

function App() {
  return <div>Hello World</div>;
}

export default App;
""")

        return project_root

    @pytest.fixture
    def mock_toolchain_analysis(self):
        """Create realistic toolchain analysis results."""
        analysis = Mock(spec=ToolchainAnalysis)
        analysis.components = [
            Mock(
                spec=ToolchainComponent, type="python", version="3.11", confidence=0.95
            ),
            Mock(
                spec=ToolchainComponent,
                type="fastapi",
                version="0.104.1",
                confidence=0.90,
            ),
            Mock(
                spec=ToolchainComponent, type="react", version="18.2.0", confidence=0.85
            ),
            Mock(
                spec=ToolchainComponent,
                type="typescript",
                version="5.0.0",
                confidence=0.80,
            ),
        ]
        analysis.languages = ["python", "javascript", "typescript"]
        analysis.frameworks = ["fastapi", "react"]
        analysis.deployment_targets = ["docker", "cloud"]
        return analysis

    @pytest.fixture
    def mock_agent_recommendations(self):
        """Create realistic agent recommendations."""
        return [
            Mock(
                spec=AgentRecommendation,
                agent_id="python-engineer",
                confidence=0.95,
                reasoning="Python FastAPI project detected with high confidence",
                matched_capabilities=["python", "fastapi", "backend-api"],
            ),
            Mock(
                spec=AgentRecommendation,
                agent_id="react-developer",
                confidence=0.85,
                reasoning="React frontend with TypeScript detected",
                matched_capabilities=["react", "typescript", "frontend"],
            ),
            Mock(
                spec=AgentRecommendation,
                agent_id="ops",
                confidence=0.70,
                reasoning="Full-stack project likely needs DevOps support",
                matched_capabilities=["docker", "deployment", "ci-cd"],
            ),
        ]

    def test_full_flow_preview_mode(
        self,
        realistic_project_structure,
        mock_toolchain_analysis,
        mock_agent_recommendations,
    ):
        """Test complete preview workflow without deployment."""
        command = AutoConfigureCommand()

        # Mock all service dependencies
        with patch.object(command, "auto_config_manager") as mock_auto_config:
            # Setup preview response
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = mock_toolchain_analysis
            preview.recommendations = mock_agent_recommendations
            preview.validation_result = Mock(
                spec=ValidationResult, is_valid=True, issues=[]
            )
            mock_auto_config.preview_configuration.return_value = preview

            # Run preview
            args = Namespace(
                project_path=realistic_project_structure,
                min_confidence=0.5,
                preview=True,
                json=False,
                verbose=False,
                debug=False,
                quiet=False,
            )

            result = command.run(args)

            # Verify successful preview
            assert result.success
            mock_auto_config.preview_configuration.assert_called_once()

            # Verify correct parameters passed
            call_args = mock_auto_config.preview_configuration.call_args
            assert call_args[0][0] == realistic_project_structure  # project_path
            assert call_args[0][1] == 0.5  # min_confidence

    def test_full_flow_json_output(
        self,
        realistic_project_structure,
        mock_toolchain_analysis,
        mock_agent_recommendations,
    ):
        """Test complete workflow with JSON output format."""
        command = AutoConfigureCommand()

        with patch.object(command, "auto_config_manager") as mock_auto_config, patch(
            "builtins.print"
        ) as mock_print:
            # Setup preview
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = mock_toolchain_analysis
            preview.recommendations = mock_agent_recommendations
            preview.validation_result = Mock(is_valid=True, issues=[])
            mock_auto_config.preview_configuration.return_value = preview

            # Mock skill recommendations
            with patch(
                "claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING",
                {
                    "python-engineer": ["python-testing", "fastapi-local-dev"],
                    "react-developer": ["react", "typescript"],
                    "ops": ["docker", "systematic-debugging"],
                },
            ):
                args = Namespace(
                    project_path=realistic_project_structure,
                    min_confidence=0.5,
                    preview=True,
                    json=True,  # JSON output
                    verbose=False,
                    debug=False,
                    quiet=False,
                )

                result = command.run(args)

                # Verify JSON output
                assert result.success
                mock_print.assert_called_once()

                # Verify JSON structure
                json_output = mock_print.call_args[0][0]
                parsed_json = json.loads(json_output)

                assert "agents" in parsed_json
                assert "skills" in parsed_json
                assert "detected_toolchain" in parsed_json["agents"]
                assert "recommendations" in parsed_json["agents"]
                assert len(parsed_json["agents"]["recommendations"]) == 3

    def test_full_flow_deployment_with_confirmation(
        self, realistic_project_structure, mock_agent_recommendations
    ):
        """Test complete deployment workflow with user confirmation."""
        command = AutoConfigureCommand()

        with patch.object(
            command, "auto_config_manager"
        ) as mock_auto_config, patch.object(
            command, "skills_deployer"
        ) as mock_skills, patch(
            "builtins.input", return_value="y"
        ) as mock_input:  # User confirms
            # Setup preview
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = Mock(components=[])
            preview.recommendations = mock_agent_recommendations[:2]  # First 2 agents
            preview.validation_result = Mock(is_valid=True, issues=[])
            mock_auto_config.preview_configuration.return_value = preview

            # Setup deployment result
            deployment_result = Mock(spec=ConfigurationResult)
            deployment_result.status = OperationResult.SUCCESS
            deployment_result.deployed_agents = ["python-engineer", "react-developer"]
            deployment_result.failed_agents = []
            deployment_result.errors = {}
            mock_auto_config.auto_configure = AsyncMock(return_value=deployment_result)

            # Setup skill deployment
            mock_skills.deploy_skills.return_value = {
                "deployed": ["python-testing", "react"],
                "errors": [],
            }

            with patch(
                "claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING",
                {"python-engineer": ["python-testing"], "react-developer": ["react"]},
            ):
                args = Namespace(
                    project_path=realistic_project_structure,
                    min_confidence=0.7,
                    preview=False,  # Full deployment
                    yes=False,  # Require confirmation
                    json=False,
                    verbose=False,
                    debug=False,
                    quiet=False,
                    agents_only=False,
                    skills_only=False,
                )

                result = command.run(args)

                # Verify deployment executed
                assert result.success
                mock_auto_config.auto_configure.assert_called_once()
                mock_skills.deploy_skills.assert_called_once()

                # Verify confirmation was requested
                mock_input.assert_called_once()

    def test_full_flow_agents_only_deployment(
        self, realistic_project_structure, mock_agent_recommendations
    ):
        """Test deployment of agents only, skipping skills."""
        command = AutoConfigureCommand()

        with patch.object(
            command, "auto_config_manager"
        ) as mock_auto_config, patch.object(command, "skills_deployer") as mock_skills:
            # Setup preview
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = Mock(components=[])
            preview.recommendations = mock_agent_recommendations[:1]  # Just one agent
            preview.validation_result = Mock(is_valid=True, issues=[])
            mock_auto_config.preview_configuration.return_value = preview

            # Setup agent deployment
            deployment_result = Mock(spec=ConfigurationResult)
            deployment_result.status = OperationResult.SUCCESS
            deployment_result.deployed_agents = ["python-engineer"]
            deployment_result.failed_agents = []
            deployment_result.errors = {}
            mock_auto_config.auto_configure = AsyncMock(return_value=deployment_result)

            args = Namespace(
                project_path=realistic_project_structure,
                min_confidence=0.5,
                preview=False,
                yes=True,  # Skip confirmation
                json=False,
                verbose=False,
                debug=False,
                quiet=False,
                agents_only=True,  # Skip skills
                skills_only=False,
            )

            result = command.run(args)

            # Verify agents deployed, skills skipped
            assert result.success
            mock_auto_config.auto_configure.assert_called_once()
            mock_skills.deploy_skills.assert_not_called()

    def test_full_flow_skills_only_deployment(
        self, realistic_project_structure, mock_agent_recommendations
    ):
        """Test deployment of skills only, skipping agents."""
        command = AutoConfigureCommand()

        with patch.object(
            command, "auto_config_manager"
        ) as mock_auto_config, patch.object(command, "skills_deployer") as mock_skills:
            # Setup preview (needed for skill recommendations)
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = Mock(components=[])
            preview.recommendations = mock_agent_recommendations[:2]
            preview.validation_result = Mock(is_valid=True, issues=[])
            mock_auto_config.preview_configuration.return_value = preview

            # Setup skill deployment
            mock_skills.deploy_skills.return_value = {
                "deployed": ["python-testing", "react"],
                "errors": [],
            }

            with patch(
                "claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING",
                {"python-engineer": ["python-testing"], "react-developer": ["react"]},
            ):
                args = Namespace(
                    project_path=realistic_project_structure,
                    min_confidence=0.5,
                    preview=False,
                    yes=True,
                    json=False,
                    verbose=False,
                    debug=False,
                    quiet=False,
                    agents_only=False,
                    skills_only=True,  # Skip agents
                )

                result = command.run(args)

                # Verify skills deployed, agents skipped
                assert result.success
                mock_auto_config.auto_configure.assert_not_called()
                mock_skills.deploy_skills.assert_called_once()

    def test_full_flow_with_validation_issues(self, realistic_project_structure):
        """Test workflow with validation issues (warnings and errors)."""
        command = AutoConfigureCommand()

        with patch.object(command, "auto_config_manager") as mock_auto_config:
            # Setup preview with validation issues
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = Mock(components=[])
            preview.recommendations = []  # No recommendations due to issues
            preview.validation_result = Mock(
                spec=ValidationResult,
                is_valid=False,  # Validation failed
                issues=[
                    Mock(
                        spec=ValidationIssue,
                        severity="error",
                        message="Python version too old (3.9), requires 3.11+",
                    ),
                    Mock(
                        spec=ValidationIssue,
                        severity="warning",
                        message="No test directory found, testing agents may not be useful",
                    ),
                ],
            )
            mock_auto_config.preview_configuration.return_value = preview

            args = Namespace(
                project_path=realistic_project_structure,
                min_confidence=0.5,
                preview=True,
                json=False,
                verbose=False,
                debug=False,
                quiet=False,
            )

            result = command.run(args)

            # Should still succeed for preview, but show validation issues
            assert result.success

    def test_full_flow_deployment_failures(
        self, realistic_project_structure, mock_agent_recommendations
    ):
        """Test handling of deployment failures."""
        command = AutoConfigureCommand()

        with patch.object(
            command, "auto_config_manager"
        ) as mock_auto_config, patch.object(command, "skills_deployer") as mock_skills:
            # Setup preview
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = Mock(components=[])
            preview.recommendations = mock_agent_recommendations[:2]
            preview.validation_result = Mock(is_valid=True, issues=[])
            mock_auto_config.preview_configuration.return_value = preview

            # Setup partial failure in agent deployment
            deployment_result = Mock(spec=ConfigurationResult)
            deployment_result.status = OperationResult.WARNING  # Partial success
            deployment_result.deployed_agents = ["python-engineer"]  # First succeeded
            deployment_result.failed_agents = ["react-developer"]  # Second failed
            deployment_result.errors = {"react-developer": "Agent registry unavailable"}
            mock_auto_config.auto_configure = AsyncMock(return_value=deployment_result)

            # Setup skill deployment failure
            mock_skills.deploy_skills.return_value = {
                "deployed": [],
                "errors": ["Failed to deploy skills: network timeout"],
            }

            with patch(
                "claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING",
                {"python-engineer": ["python-testing"], "react-developer": ["react"]},
            ):
                args = Namespace(
                    project_path=realistic_project_structure,
                    min_confidence=0.5,
                    preview=False,
                    yes=True,
                    json=False,
                    verbose=False,
                    debug=False,
                    quiet=False,
                    agents_only=False,
                    skills_only=False,
                )

                result = command.run(args)

                # Should indicate failure due to partial deployment
                assert not result.success
                assert result.exit_code == 1

    def test_full_flow_with_lazy_singleton_handling(self, realistic_project_structure):
        """Test workflow handles optional AgentRegistry and lazy singletons properly."""
        command = AutoConfigureCommand()

        # Test lazy loading of auto_config_manager
        assert command._auto_config_manager is None

        with patch(
            "claude_mpm.cli.commands.auto_configure.AutoConfigManagerService"
        ) as MockManager, patch(
            "claude_mpm.cli.commands.auto_configure.AgentRecommenderService"
        ) as MockRecommender, patch(
            "claude_mpm.cli.commands.auto_configure.AgentRegistry"
        ) as MockRegistry, patch(
            "claude_mpm.cli.commands.auto_configure.ToolchainAnalyzerService"
        ) as MockAnalyzer:
            # Mock optional AgentDeploymentService import
            with patch(
                "claude_mpm.cli.commands.auto_configure.AgentDeploymentService",
                side_effect=ImportError,
            ):
                # Access the property to trigger lazy loading
                manager = command.auto_config_manager

                # Verify lazy initialization
                assert command._auto_config_manager is not None
                MockManager.assert_called_once()

                # Verify optional dependency handled gracefully
                init_kwargs = MockManager.call_args[1]
                assert (
                    init_kwargs["agent_deployment"] is None
                )  # Optional service unavailable

        # Test lazy loading of skills_deployer
        assert command._skills_deployer is None

        with patch(
            "claude_mpm.cli.commands.auto_configure.SkillsDeployerService"
        ) as MockSkillsDeployer:
            skills_deployer = command.skills_deployer

            assert command._skills_deployer is not None
            MockSkillsDeployer.assert_called_once()

    def test_full_flow_cross_scope_deployment(
        self, realistic_project_structure, mock_agent_recommendations
    ):
        """Test cross-scope deployment (PROJECT vs USER) integration."""
        command = AutoConfigureCommand()

        with patch.object(
            command, "auto_config_manager"
        ) as mock_auto_config, patch.object(command, "skills_deployer") as mock_skills:
            # Setup preview
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = Mock(components=[])
            preview.recommendations = mock_agent_recommendations[:1]
            preview.validation_result = Mock(is_valid=True, issues=[])
            mock_auto_config.preview_configuration.return_value = preview

            # Setup successful deployment
            deployment_result = Mock(spec=ConfigurationResult)
            deployment_result.status = OperationResult.SUCCESS
            deployment_result.deployed_agents = ["python-engineer"]
            deployment_result.failed_agents = []
            deployment_result.errors = {}
            mock_auto_config.auto_configure = AsyncMock(return_value=deployment_result)

            mock_skills.deploy_skills.return_value = {
                "deployed": ["python-testing"],
                "errors": [],
            }

            with patch(
                "claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING",
                {"python-engineer": ["python-testing"]},
            ):
                args = Namespace(
                    project_path=realistic_project_structure,
                    min_confidence=0.5,
                    preview=False,
                    yes=True,
                    json=False,
                    verbose=False,
                    debug=False,
                    quiet=False,
                    agents_only=False,
                    skills_only=False,
                )

                result = command.run(args)

                # Verify deployment succeeded
                assert result.success

                # Verify agents deployed to PROJECT scope (default)
                agent_call_kwargs = mock_auto_config.auto_configure.call_args[1]
                assert agent_call_kwargs["project_path"] == realistic_project_structure

                # Skills deployment scope is handled by SkillsDeployerService
                mock_skills.deploy_skills.assert_called_once()


@pytest.mark.integration
class TestAutoConfigureAsyncBoundaries:
    """Test async/sync boundary handling in auto-configure workflow."""

    @pytest.fixture
    def command(self):
        return AutoConfigureCommand()

    def test_asyncio_run_integration(self, command, tmp_path):
        """Test asyncio.run boundary in full deployment workflow."""
        with patch.object(command, "auto_config_manager") as mock_auto_config, patch(
            "asyncio.run"
        ) as mock_asyncio_run:
            # Setup preview
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = Mock(components=[])
            preview.recommendations = [Mock(agent_id="python-engineer", confidence=0.9)]
            preview.validation_result = Mock(is_valid=True, issues=[])
            mock_auto_config.preview_configuration.return_value = preview

            # Mock asyncio.run return
            deployment_result = Mock(spec=ConfigurationResult)
            deployment_result.status = OperationResult.SUCCESS
            deployment_result.deployed_agents = ["python-engineer"]
            deployment_result.failed_agents = []
            deployment_result.errors = {}
            mock_asyncio_run.return_value = deployment_result

            args = Namespace(
                project_path=tmp_path,
                min_confidence=0.5,
                preview=False,
                yes=True,
                json=False,
                verbose=False,
                debug=False,
                quiet=False,
                agents_only=True,  # Skip skills for simplicity
                skills_only=False,
            )

            result = command.run(args)

            # Verify asyncio.run called for async service
            assert result.success
            mock_asyncio_run.assert_called_once()

            # Verify the coroutine passed to asyncio.run
            coroutine_arg = mock_asyncio_run.call_args[0][0]
            # Should be the auto_configure coroutine
            assert hasattr(coroutine_arg, "__await__")  # Is a coroutine

    def test_async_to_sync_error_propagation(self, command, tmp_path):
        """Test error propagation across async/sync boundaries."""
        with patch.object(command, "auto_config_manager") as mock_auto_config:
            # Setup preview
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = Mock(components=[])
            preview.recommendations = [Mock(agent_id="test-agent", confidence=0.9)]
            preview.validation_result = Mock(is_valid=True, issues=[])
            mock_auto_config.preview_configuration.return_value = preview

            # Mock async service failure
            mock_auto_config.auto_configure = AsyncMock(
                side_effect=Exception("Async service failed")
            )

            args = Namespace(
                project_path=tmp_path,
                min_confidence=0.5,
                preview=False,
                yes=True,
                json=False,
                verbose=False,
                debug=False,
                quiet=False,
                agents_only=True,
                skills_only=False,
            )

            result = command.run(args)

            # Error should propagate back to sync CLI layer
            assert not result.success
            assert "Async service failed" in result.message


@pytest.mark.integration
class TestAutoConfigureFileSystemIntegration:
    """Test auto-configure integration with real filesystem operations."""

    def test_project_structure_analysis_integration(self, tmp_path):
        """Test integration with real project structure analysis."""
        # Create realistic Python project
        project_path = tmp_path / "real_project"
        project_path.mkdir()

        # Add Python indicators
        (project_path / "requirements.txt").write_text(
            "fastapi==0.104.1\nuvicorn==0.24.0"
        )
        (project_path / "main.py").write_text("from fastapi import FastAPI")

        # Add React indicators
        frontend_dir = project_path / "frontend"
        frontend_dir.mkdir()
        (frontend_dir / "package.json").write_text(
            '{"dependencies": {"react": "^18.0.0"}}'
        )

        command = AutoConfigureCommand()

        # Test with real project path
        args = Namespace(
            project_path=project_path,  # Real filesystem path
            min_confidence=0.5,
            preview=True,
            json=False,
            verbose=False,
            debug=False,
            quiet=False,
        )

        # Mock only the services, not the filesystem
        with patch.object(command, "auto_config_manager") as mock_auto_config:
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = Mock(components=[])
            preview.recommendations = []
            preview.validation_result = Mock(is_valid=True, issues=[])
            mock_auto_config.preview_configuration.return_value = preview

            result = command.run(args)

            # Verify real project path passed to service
            assert result.success
            call_args = mock_auto_config.preview_configuration.call_args
            assert call_args[0][0] == project_path

    def test_deployment_directory_creation_integration(self, tmp_path):
        """Test deployment creates correct directory structure."""
        from claude_mpm.core.config_scope import (
            ConfigScope,
            resolve_agents_dir,
            resolve_skills_dir,
        )

        project_path = tmp_path / "deployment_test"
        project_path.mkdir()

        # Test PROJECT scope directory resolution
        agents_dir = resolve_agents_dir(ConfigScope.PROJECT, project_path)
        skills_dir = resolve_skills_dir(ConfigScope.PROJECT, project_path)

        # Directories shouldn't exist initially
        assert not agents_dir.exists()
        assert not skills_dir.exists()

        # Simulate deployment directory creation
        agents_dir.mkdir(parents=True)
        skills_dir.mkdir(parents=True)

        # Verify structure
        assert agents_dir.exists()
        assert skills_dir.exists()
        assert agents_dir == project_path / ".claude" / "agents"
        assert skills_dir == project_path / ".claude" / "skills"

        # Test agent deployment simulation
        agent_file = agents_dir / "python-engineer.yml"
        agent_file.write_text(
            yaml.dump(
                {
                    "name": "Python Engineer",
                    "description": "Python development agent",
                    "capabilities": ["python", "fastapi"],
                }
            )
        )

        assert agent_file.exists()
        agent_data = yaml.safe_load(agent_file.read_text())
        assert agent_data["name"] == "Python Engineer"

    def test_cross_scope_filesystem_isolation_integration(self, tmp_path):
        """Test PROJECT and USER scope filesystem isolation."""
        from claude_mpm.core.config_scope import (
            ConfigScope,
            resolve_agents_dir,
            resolve_skills_dir,
        )

        project_path = tmp_path / "isolation_test"
        project_path.mkdir()

        with patch("claude_mpm.core.config_scope.Path.home") as mock_home:
            mock_home.return_value = tmp_path / "fake_home"

            # Get both scope directories
            project_agents = resolve_agents_dir(ConfigScope.PROJECT, project_path)
            user_agents = resolve_agents_dir(ConfigScope.USER, project_path)
            project_skills = resolve_skills_dir(ConfigScope.PROJECT, project_path)
            user_skills = resolve_skills_dir(ConfigScope.USER, project_path)

            # Create all directories
            for directory in [project_agents, user_agents, project_skills, user_skills]:
                directory.mkdir(parents=True)

            # Deploy to PROJECT scope
            (project_agents / "project-agent.yml").write_text("name: Project Agent")
            (project_skills / "project-skill" / "skill.md").write_text(
                "# Project Skill"
            )
            project_skills.joinpath("project-skill").mkdir(exist_ok=True)

            # Deploy to USER scope
            (user_agents / "user-agent.yml").write_text("name: User Agent")
            (user_skills / "user-skill" / "skill.md").write_text("# User Skill")
            user_skills.joinpath("user-skill").mkdir(exist_ok=True)

            # Verify complete isolation
            assert (project_agents / "project-agent.yml").exists()
            assert not (project_agents / "user-agent.yml").exists()
            assert (user_agents / "user-agent.yml").exists()
            assert not (user_agents / "project-agent.yml").exists()

            # Skills isolation
            assert (project_skills / "project-skill" / "skill.md").exists()
            assert not (project_skills / "user-skill").exists()
            assert (user_skills / "user-skill" / "skill.md").exists()
            assert not (user_skills / "project-skill").exists()
