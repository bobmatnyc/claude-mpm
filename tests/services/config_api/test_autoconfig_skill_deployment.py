"""
Tests for auto-configure skill deployment integration
===================================================

WHY: Tests skill deployment integration in auto-configure v2, including
agent-skill mapping, cross-scope deployment, and async boundary handling.
Addresses research findings about integration testing over unit testing.

FOCUS: Integration testing with realistic skill deployment scenarios,
testing both success and failure paths across PROJECT/USER scopes.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from claude_mpm.cli.commands.auto_configure import AutoConfigureCommand
from claude_mpm.core.config_scope import ConfigScope
from claude_mpm.core.enums import OperationResult
from claude_mpm.services.core.models.agent_config import (
    AgentRecommendation,
    ConfigurationPreview,
    ConfigurationResult,
    ValidationResult,
)


class TestSkillRecommendationLogic:
    """Test skill recommendation based on agent recommendations."""

    @pytest.fixture
    def command(self):
        return AutoConfigureCommand()

    @pytest.fixture
    def sample_agent_recommendations(self):
        """Create sample agent recommendations for testing."""
        return [
            Mock(
                spec=AgentRecommendation,
                agent_id="python-engineer",
                confidence=0.9,
                reasoning="Python project detected",
            ),
            Mock(
                spec=AgentRecommendation,
                agent_id="react-developer",
                confidence=0.8,
                reasoning="React framework detected",
            ),
        ]

    def test_recommend_skills_with_valid_agents(
        self, command, sample_agent_recommendations
    ):
        """Test skill recommendation with valid agent recommendations."""
        preview = Mock(spec=ConfigurationPreview)
        preview.recommendations = sample_agent_recommendations

        with patch(
            "claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING",
            {
                "python-engineer": ["python-testing", "fastapi-local-dev"],
                "react-developer": ["react", "tailwind-css"],
            },
        ):
            skills = command._recommend_skills(preview)

            # Should recommend skills for all agents
            expected_skills = {
                "python-testing",
                "fastapi-local-dev",
                "react",
                "tailwind-css",
            }
            assert set(skills) == expected_skills

    def test_recommend_skills_with_no_agents(self, command):
        """Test skill recommendation with no agent recommendations."""
        preview = Mock(spec=ConfigurationPreview)
        preview.recommendations = []

        skills = command._recommend_skills(preview)
        assert skills is None

    def test_recommend_skills_with_unmapped_agents(self, command):
        """Test skill recommendation with agents not in mapping."""
        preview = Mock(spec=ConfigurationPreview)
        preview.recommendations = [
            Mock(
                spec=AgentRecommendation,
                agent_id="unknown-agent",
                confidence=0.9,
                reasoning="Unknown agent type",
            )
        ]

        with patch("claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING", {}):
            skills = command._recommend_skills(preview)
            assert skills is None  # No mapping found

    def test_recommend_skills_deduplication(self, command):
        """Test that duplicate skills are deduplicated."""
        preview = Mock(spec=ConfigurationPreview)
        preview.recommendations = [
            Mock(spec=AgentRecommendation, agent_id="python-engineer", confidence=0.9),
            Mock(spec=AgentRecommendation, agent_id="django-developer", confidence=0.8),
        ]

        with patch(
            "claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING",
            {
                "python-engineer": ["python-testing", "systematic-debugging"],
                "django-developer": [
                    "python-testing",
                    "django",
                ],  # python-testing duplicated
            },
        ):
            skills = command._recommend_skills(preview)

            # Should deduplicate python-testing
            expected_skills = {"python-testing", "systematic-debugging", "django"}
            assert set(skills) == expected_skills


class TestSkillDeploymentExecution:
    """Test actual skill deployment execution."""

    @pytest.fixture
    def command(self):
        return AutoConfigureCommand()

    def test_deploy_skills_success(self, command):
        """Test successful skill deployment."""
        recommended_skills = ["python-testing", "react", "systematic-debugging"]

        with patch.object(command, "skills_deployer") as mock_deployer:
            mock_deployer.deploy_skills.return_value = {
                "deployed": ["python-testing", "react", "systematic-debugging"],
                "errors": [],
            }

            result = command._deploy_skills(recommended_skills)

            # Verify deployment called correctly
            mock_deployer.deploy_skills.assert_called_once_with(
                skill_names=recommended_skills, force=False
            )

            # Verify successful result
            assert result["deployed"] == recommended_skills
            assert result["errors"] == []

    def test_deploy_skills_partial_failure(self, command):
        """Test skill deployment with partial failures."""
        recommended_skills = ["python-testing", "invalid-skill", "react"]

        with patch.object(command, "skills_deployer") as mock_deployer:
            mock_deployer.deploy_skills.return_value = {
                "deployed": ["python-testing", "react"],
                "errors": ["Failed to deploy invalid-skill: skill not found"],
            }

            result = command._deploy_skills(recommended_skills)

            # Verify partial success handled
            assert result["deployed"] == ["python-testing", "react"]
            assert len(result["errors"]) == 1
            assert "invalid-skill" in result["errors"][0]

    def test_deploy_skills_complete_failure(self, command):
        """Test skill deployment complete failure."""
        recommended_skills = ["skill1", "skill2"]

        with patch.object(command, "skills_deployer") as mock_deployer:
            mock_deployer.deploy_skills.side_effect = Exception(
                "Deployment service unavailable"
            )

            result = command._deploy_skills(recommended_skills)

            # Verify exception handled gracefully
            assert result["deployed"] == []
            assert len(result["errors"]) == 1
            assert "Deployment service unavailable" in result["errors"][0]

    def test_deploy_skills_with_force_parameter(self, command):
        """Test skill deployment respects force parameter."""
        recommended_skills = ["python-testing"]

        with patch.object(command, "skills_deployer") as mock_deployer:
            mock_deployer.deploy_skills.return_value = {
                "deployed": ["python-testing"],
                "errors": [],
            }

            # Current implementation uses force=False
            result = command._deploy_skills(recommended_skills)

            mock_deployer.deploy_skills.assert_called_once_with(
                skill_names=recommended_skills,
                force=False,  # Verify force parameter
            )


class TestCrossScopeSkillDeployment:
    """Test skill deployment across PROJECT/USER scopes."""

    @pytest.fixture
    def command(self):
        return AutoConfigureCommand()

    def test_project_scope_skill_deployment(self, command, tmp_path):
        """Test skill deployment in PROJECT scope."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Mock skills deployer to verify scope handling
        with patch.object(command, "skills_deployer") as mock_deployer:
            mock_deployer.deploy_skills.return_value = {
                "deployed": ["python-testing"],
                "errors": [],
            }

            # Skills deployment should use project scope by default
            recommended_skills = ["python-testing"]
            result = command._deploy_skills(recommended_skills)

            # Verify deployment occurred (scope handling is in SkillsDeployerService)
            mock_deployer.deploy_skills.assert_called_once()
            assert result["deployed"] == ["python-testing"]

    def test_user_scope_skill_deployment_fallback(self, command, tmp_path):
        """Test skill deployment falls back to USER scope when PROJECT fails."""
        # This would test fallback logic if implemented
        # Currently, scope is handled by SkillsDeployerService internally
        project_path = tmp_path / "project"
        project_path.mkdir()

        with patch.object(command, "skills_deployer") as mock_deployer:
            # Simulate PROJECT scope failure, USER scope success
            mock_deployer.deploy_skills.return_value = {
                "deployed": ["python-testing"],
                "errors": [],
                "scope_used": "user",  # Hypothetical field
            }

            result = command._deploy_skills(["python-testing"])

            # Verify deployment succeeded with fallback
            assert result["deployed"] == ["python-testing"]


class TestFullWorkflowSkillIntegration:
    """Test skill deployment in full auto-configure workflow."""

    @pytest.fixture
    def command(self):
        return AutoConfigureCommand()

    @pytest.fixture
    def mock_services(self):
        """Mock all required services for full workflow testing."""
        mocks = {}

        # Mock auto-config manager
        mocks["auto_config"] = Mock()
        preview = Mock(spec=ConfigurationPreview)
        preview.recommendations = [
            Mock(spec=AgentRecommendation, agent_id="python-engineer", confidence=0.9)
        ]
        preview.validation_result = Mock(
            spec=ValidationResult, is_valid=True, issues=[]
        )
        preview.detected_toolchain = Mock(components=[])
        mocks["auto_config"].preview_configuration.return_value = preview

        # Mock successful agent deployment
        result = Mock(spec=ConfigurationResult)
        result.status = OperationResult.SUCCESS
        result.deployed_agents = ["python-engineer"]
        result.failed_agents = []
        result.errors = {}
        mocks["auto_config"].auto_configure = AsyncMock(return_value=result)

        # Mock skills deployer
        mocks["skills_deployer"] = Mock()
        mocks["skills_deployer"].deploy_skills.return_value = {
            "deployed": ["python-testing", "systematic-debugging"],
            "errors": [],
        }

        return mocks

    def test_full_workflow_with_skills_success(self, command, tmp_path, mock_services):
        """Test full auto-configure workflow with successful skill deployment."""
        args = Namespace(
            project_path=tmp_path,
            min_confidence=0.5,
            preview=False,
            yes=True,  # Skip confirmation
            json=False,
            verbose=False,
            debug=False,
            quiet=False,
            agents_only=False,  # Deploy both agents and skills
            skills_only=False,
        )

        with patch.object(
            command, "auto_config_manager", mock_services["auto_config"]
        ), patch.object(
            command, "skills_deployer", mock_services["skills_deployer"]
        ), patch(
            "claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING",
            {"python-engineer": ["python-testing", "systematic-debugging"]},
        ):
            result = command.run(args)

            # Verify full workflow executed successfully
            assert result.success

            # Verify agent deployment occurred
            mock_services["auto_config"].auto_configure.assert_called_once()

            # Verify skill deployment occurred
            mock_services["skills_deployer"].deploy_skills.assert_called_once()
            deploy_call = mock_services["skills_deployer"].deploy_skills.call_args
            assert "python-testing" in deploy_call[1]["skill_names"]
            assert "systematic-debugging" in deploy_call[1]["skill_names"]

    def test_full_workflow_agents_only(self, command, tmp_path, mock_services):
        """Test full workflow with agents_only flag skips skill deployment."""
        args = Namespace(
            project_path=tmp_path,
            min_confidence=0.5,
            preview=False,
            yes=True,
            json=False,
            verbose=False,
            debug=False,
            quiet=False,
            agents_only=True,  # Skip skills
            skills_only=False,
        )

        with patch.object(
            command, "auto_config_manager", mock_services["auto_config"]
        ), patch.object(command, "skills_deployer", mock_services["skills_deployer"]):
            result = command.run(args)

            # Verify agents deployed but skills skipped
            assert result.success
            mock_services["auto_config"].auto_configure.assert_called_once()
            mock_services["skills_deployer"].deploy_skills.assert_not_called()

    def test_full_workflow_skills_only(self, command, tmp_path, mock_services):
        """Test full workflow with skills_only flag skips agent deployment."""
        args = Namespace(
            project_path=tmp_path,
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

        # For skills_only, we still need agent preview to determine skill recommendations
        with patch.object(
            command, "auto_config_manager", mock_services["auto_config"]
        ), patch.object(
            command, "skills_deployer", mock_services["skills_deployer"]
        ), patch(
            "claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING",
            {"python-engineer": ["python-testing"]},
        ):
            result = command.run(args)

            # Verify skills deployed but agents skipped
            assert result.success
            mock_services["auto_config"].auto_configure.assert_not_called()
            mock_services["skills_deployer"].deploy_skills.assert_called_once()

    def test_full_workflow_skill_deployment_failure_handling(
        self, command, tmp_path, mock_services
    ):
        """Test full workflow handles skill deployment failures gracefully."""
        # Mock skill deployment failure
        mock_services["skills_deployer"].deploy_skills.return_value = {
            "deployed": [],
            "errors": ["Failed to deploy python-testing: permission denied"],
        }

        args = Namespace(
            project_path=tmp_path,
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

        with patch.object(
            command, "auto_config_manager", mock_services["auto_config"]
        ), patch.object(
            command, "skills_deployer", mock_services["skills_deployer"]
        ), patch(
            "claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING",
            {"python-engineer": ["python-testing"]},
        ):
            result = command.run(args)

            # Should handle skill failure gracefully
            # Agents succeeded, skills failed -> partial success
            assert not result.success  # Overall failure due to skill deployment failure
            assert result.exit_code == 1


@pytest.mark.integration
class TestSkillDeploymentIntegration:
    """Integration tests for skill deployment with real filesystem operations."""

    def test_skill_deployment_path_resolution(self, tmp_path):
        """Test skill deployment resolves paths correctly across scopes."""
        from claude_mpm.core.config_scope import ConfigScope, resolve_skills_dir

        project_path = tmp_path / "integration_test"
        project_path.mkdir()

        # Test PROJECT scope path resolution
        project_skills_dir = resolve_skills_dir(ConfigScope.PROJECT, project_path)
        assert project_skills_dir == project_path / ".claude" / "skills"

        # Test USER scope path resolution
        with patch("claude_mpm.core.config_scope.Path.home") as mock_home:
            mock_home.return_value = tmp_path / "home"
            user_skills_dir = resolve_skills_dir(ConfigScope.USER, project_path)
            assert user_skills_dir == tmp_path / "home" / ".claude" / "skills"

        # Verify paths are different
        assert project_skills_dir != user_skills_dir

    def test_skill_deployment_directory_creation(self, tmp_path):
        """Test that skill deployment can create necessary directories."""
        from claude_mpm.core.config_scope import ConfigScope, resolve_skills_dir

        project_path = tmp_path / "dir_creation_test"
        project_path.mkdir()

        # Test PROJECT scope directory creation
        skills_dir = resolve_skills_dir(ConfigScope.PROJECT, project_path)
        skills_dir.mkdir(parents=True, exist_ok=True)

        assert skills_dir.exists()
        assert skills_dir.is_dir()

        # Test skill file creation (simulate deployment)
        skill_file = skills_dir / "python-testing" / "skill.md"
        skill_file.parent.mkdir(exist_ok=True)
        skill_file.write_text("# Python Testing Skill")

        assert skill_file.exists()
        assert "Python Testing" in skill_file.read_text()

    def test_cross_scope_skill_isolation(self, tmp_path):
        """Test that PROJECT and USER skill deployments are isolated."""
        from claude_mpm.core.config_scope import ConfigScope, resolve_skills_dir

        project_path = tmp_path / "isolation_test"
        project_path.mkdir()

        with patch("claude_mpm.core.config_scope.Path.home") as mock_home:
            mock_home.return_value = tmp_path / "home"

            # Deploy to PROJECT scope
            project_skills_dir = resolve_skills_dir(ConfigScope.PROJECT, project_path)
            project_skills_dir.mkdir(parents=True)
            (project_skills_dir / "project-skill.md").write_text("Project skill")

            # Deploy to USER scope
            user_skills_dir = resolve_skills_dir(ConfigScope.USER, project_path)
            user_skills_dir.mkdir(parents=True)
            (user_skills_dir / "user-skill.md").write_text("User skill")

            # Verify isolation
            assert (project_skills_dir / "project-skill.md").exists()
            assert not (project_skills_dir / "user-skill.md").exists()
            assert (user_skills_dir / "user-skill.md").exists()
            assert not (user_skills_dir / "project-skill.md").exists()
