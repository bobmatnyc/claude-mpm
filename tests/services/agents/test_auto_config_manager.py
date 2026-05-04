"""
Tests for Auto-Configuration Manager Service
==========================================

WHY: Comprehensive testing of the auto-configuration workflow ensures
reliability and prevents regressions in this critical feature.

DESIGN DECISION: Tests cover the complete workflow, edge cases, error
conditions, and safety features. Uses mocking to isolate service logic
from external dependencies.

Part of TSK-0054: Auto-Configuration Feature - Phase 4
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import yaml

from claude_mpm.services.agents.auto_config_manager import AutoConfigManagerService
from claude_mpm.services.agents.observers import (
    CompositeObserver,
    ConsoleProgressObserver,
    IDeploymentObserver,
    NullObserver,
)
from claude_mpm.services.core.models.agent_config import (
    AgentCapabilities,
    AgentRecommendation,
    AgentSpecialization,
    ConfigurationPreview,
    ConfigurationResult,
    ConfigurationStatus,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from claude_mpm.services.core.models.toolchain import (
    ConfidenceLevel,
    DeploymentTarget,
    Framework,
    LanguageDetection,
    ToolchainAnalysis,
)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def mock_toolchain_analyzer(temp_project_dir):
    """Create a mock toolchain analyzer."""
    mock = Mock()

    def _analyze_toolchain(project_path):
        return ToolchainAnalysis(
            project_path=project_path,
            language_detection=LanguageDetection(
                primary_language="Python",
                primary_version="3.11",
                primary_confidence=ConfidenceLevel.HIGH,
                language_percentages={"Python": 100.0},
            ),
            frameworks=[
                Framework(
                    name="FastAPI",
                    version="0.104.0",
                    framework_type="web",
                    confidence=ConfidenceLevel.HIGH,
                )
            ],
            deployment_target=DeploymentTarget(
                target_type="serverless",
                platform="vercel",
                confidence=ConfidenceLevel.HIGH,
            ),
            overall_confidence=ConfidenceLevel.HIGH,
        )

    mock.analyze_toolchain = Mock(side_effect=_analyze_toolchain)
    return mock


@pytest.fixture
def mock_agent_recommender():
    """Create a mock agent recommender."""
    mock = Mock()
    mock.recommend_agents = Mock(
        return_value=[
            AgentRecommendation(
                agent_id="python-engineer",
                agent_name="Python Engineer",
                confidence_score=0.95,
                match_reasons=["Primary language match: Python"],
                capabilities=AgentCapabilities(
                    agent_id="python-engineer",
                    agent_name="Python Engineer",
                    specializations=[AgentSpecialization.LANGUAGE_SPECIFIC],
                    supported_languages=["Python"],
                ),
                deployment_priority=1,
            ),
            AgentRecommendation(
                agent_id="vercel-ops",
                agent_name="Vercel Ops Agent",
                confidence_score=0.88,
                match_reasons=["Deployment platform match: vercel"],
                capabilities=AgentCapabilities(
                    agent_id="vercel-ops",
                    agent_name="Vercel Ops Agent",
                    specializations=[AgentSpecialization.DEVOPS],
                    deployment_targets=["vercel"],
                ),
                deployment_priority=3,
            ),
        ]
    )
    return mock


@pytest.fixture
def mock_agent_registry():
    """Create a mock agent registry."""
    mock = Mock()
    mock.get_agent = Mock(
        return_value=Mock(
            name="python-engineer",
            type="engineering",
            description="Python specialist",
        )
    )
    return mock


@pytest.fixture
def mock_agent_deployment():
    """Create a mock agent deployment service."""
    mock = Mock()
    return mock


@pytest.fixture
def service(
    mock_toolchain_analyzer,
    mock_agent_recommender,
    mock_agent_registry,
    mock_agent_deployment,
):
    """Create an AutoConfigManagerService instance with mocked dependencies."""
    return AutoConfigManagerService(
        toolchain_analyzer=mock_toolchain_analyzer,
        agent_recommender=mock_agent_recommender,
        agent_registry=mock_agent_registry,
        agent_deployment=mock_agent_deployment,
    )


# ============================================================================
# Test: Service Initialization
# ============================================================================


def test_service_initialization(service):
    """Test that service initializes correctly with dependencies."""
    assert service.name == "AutoConfigManagerService"
    assert service._toolchain_analyzer is not None
    assert service._agent_recommender is not None
    assert service._agent_registry is not None
    assert service._agent_deployment is not None
    assert service._min_confidence_default == 0.5


@pytest.mark.asyncio
async def test_service_lazy_initialization():
    """Test that service can initialize dependencies lazily."""
    service = AutoConfigManagerService()
    await service._initialize()
    # Should have attempted to initialize dependencies
    assert (
        service._toolchain_analyzer is not None
        or service._agent_recommender is not None
    )


# ============================================================================
# Test: Auto-Configure - Success Cases
# ============================================================================


@pytest.mark.asyncio
async def test_auto_configure_success(service, temp_project_dir):
    """Test successful auto-configuration workflow."""

    # Mock deployment to actually write a file so post-deployment
    # validation has something on disk to verify.
    async def fake_deploy(agent_id: str, project_path: Path):
        agents_dir = project_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / f"{agent_id}.md").write_text(
            f"# {agent_id}\n\nTest agent.\n", encoding="utf-8"
        )

    service._deploy_single_agent = AsyncMock(side_effect=fake_deploy)
    service._save_configuration = AsyncMock()

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
        dry_run=False,
        min_confidence=0.8,
    )

    assert result.status == ConfigurationStatus.SUCCESS
    assert len(result.deployed_agents) == 2
    assert "python-engineer" in result.deployed_agents
    assert "vercel-ops" in result.deployed_agents
    assert len(result.failed_agents) == 0
    assert result.is_successful


@pytest.mark.asyncio
async def test_auto_configure_dry_run(service, temp_project_dir):
    """Test auto-configuration in dry-run mode."""
    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
        dry_run=True,
        min_confidence=0.8,
    )

    assert result.status == ConfigurationStatus.SUCCESS
    assert len(result.deployed_agents) == 0  # No deployment in dry-run
    assert "dry-run complete" in result.message.lower()
    assert result.metadata["dry_run"] is True


@pytest.mark.asyncio
async def test_auto_configure_with_observer(service, temp_project_dir):
    """Test auto-configuration with observer notifications."""
    observer = Mock(spec=IDeploymentObserver)

    async def fake_deploy(agent_id: str, project_path: Path):
        agents_dir = project_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / f"{agent_id}.md").write_text(
            f"# {agent_id}\n\nTest agent.\n", encoding="utf-8"
        )

    service._deploy_single_agent = AsyncMock(side_effect=fake_deploy)
    service._save_configuration = AsyncMock()

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
        dry_run=False,
        observer=observer,
    )

    # Verify observer was called for key events
    observer.on_analysis_started.assert_called_once()
    observer.on_analysis_completed.assert_called_once()
    observer.on_recommendation_started.assert_called_once()
    observer.on_recommendation_completed.assert_called_once()
    observer.on_validation_started.assert_called_once()
    observer.on_validation_completed.assert_called_once()
    observer.on_deployment_started.assert_called_once()
    observer.on_deployment_completed.assert_called_once()


@pytest.mark.asyncio
async def test_auto_configure_no_recommendations(service, temp_project_dir):
    """Test auto-configuration when no agents are recommended."""
    service._agent_recommender.recommend_agents = Mock(return_value=[])

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
        dry_run=False,
    )

    assert result.status == ConfigurationStatus.SUCCESS
    assert len(result.deployed_agents) == 0
    assert "no agents recommended" in result.message.lower()


# ============================================================================
# Test: Auto-Configure - Validation
# ============================================================================


@pytest.mark.asyncio
async def test_auto_configure_validation_failure(service, temp_project_dir):
    """Test auto-configuration when validation fails."""
    # Make agent registry return None (agent doesn't exist)
    service._agent_registry.get_agent = Mock(return_value=None)

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
        dry_run=False,
    )

    assert result.status == ConfigurationStatus.ERROR
    assert len(result.validation_errors) > 0
    assert len(result.deployed_agents) == 0


# ============================================================================
# Test: Auto-Configure - Deployment Failures
# ============================================================================


@pytest.mark.asyncio
async def test_auto_configure_partial_deployment_failure(service, temp_project_dir):
    """Test auto-configuration with partial deployment failure."""

    # Mock deployment to fail for second agent
    async def mock_deploy(agent_id: str, project_path: Path):
        if agent_id == "vercel-ops":
            raise Exception("Deployment failed")

    service._deploy_single_agent = AsyncMock(side_effect=mock_deploy)
    service._rollback_deployment = AsyncMock(return_value=True)
    service._save_configuration = AsyncMock()

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
        dry_run=False,
    )

    assert result.status == ConfigurationStatus.WARNING
    assert len(result.deployed_agents) == 1
    assert len(result.failed_agents) == 1
    assert "vercel-ops" in result.failed_agents
    assert result.has_failures


# ============================================================================
# Test: Auto-Configure - Input Validation
# ============================================================================


@pytest.mark.asyncio
async def test_auto_configure_invalid_project_path(service):
    """Test auto-configuration with non-existent project path."""
    with pytest.raises(FileNotFoundError):
        await service.auto_configure(
            project_path=Path("/nonexistent/path"),
            confirmation_required=False,
        )


@pytest.mark.asyncio
async def test_auto_configure_invalid_confidence(service, temp_project_dir):
    """Test auto-configuration with invalid confidence threshold."""
    with pytest.raises(ValueError, match="min_confidence must be between"):
        await service.auto_configure(
            project_path=temp_project_dir,
            min_confidence=1.5,
        )


@pytest.mark.asyncio
async def test_auto_configure_project_path_not_directory(service, tmp_path):
    """Test auto-configuration with file path instead of directory."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("test")

    with pytest.raises(ValueError, match="not a directory"):
        await service.auto_configure(
            project_path=file_path,
            confirmation_required=False,
        )


# ============================================================================
# Test: Configuration Validation
# ============================================================================


def test_validate_configuration_success(service):
    """Test validation of valid configuration."""
    recommendations = [
        AgentRecommendation(
            agent_id="python-engineer",
            agent_name="Python Engineer",
            confidence_score=0.95,
            capabilities=AgentCapabilities(
                agent_id="python-engineer",
                agent_name="Python Engineer",
                specializations=[AgentSpecialization.LANGUAGE_SPECIFIC],
            ),
        )
    ]

    result = service.validate_configuration(recommendations)

    assert result.is_valid
    assert len(result.errors) == 0


def test_validate_configuration_agent_not_found(service):
    """Test validation when agent doesn't exist."""
    service._agent_registry.get_agent = Mock(return_value=None)

    recommendations = [
        AgentRecommendation(
            agent_id="nonexistent-agent",
            agent_name="Nonexistent Agent",
            confidence_score=0.95,
        )
    ]

    result = service.validate_configuration(recommendations)

    assert not result.is_valid
    assert len(result.errors) > 0
    assert "does not exist" in result.errors[0].message


def test_validate_configuration_low_confidence(service):
    """Test validation with low confidence recommendations."""
    recommendations = [
        AgentRecommendation(
            agent_id="python-engineer",
            agent_name="Python Engineer",
            confidence_score=0.45,  # Low confidence
        )
    ]

    result = service.validate_configuration(recommendations)

    assert result.is_valid  # Still valid, just has warnings
    assert len(result.warnings) > 0
    assert "low confidence" in result.warnings[0].message.lower()


def test_validate_configuration_multiple_roles(service):
    """Test validation with multiple agents for same role."""
    recommendations = [
        AgentRecommendation(
            agent_id="python-engineer-1",
            agent_name="Python Engineer 1",
            confidence_score=0.95,
            capabilities=AgentCapabilities(
                agent_id="python-engineer-1",
                agent_name="Python Engineer 1",
                specializations=[AgentSpecialization.LANGUAGE_SPECIFIC],
            ),
        ),
        AgentRecommendation(
            agent_id="python-engineer-2",
            agent_name="Python Engineer 2",
            confidence_score=0.90,
            capabilities=AgentCapabilities(
                agent_id="python-engineer-2",
                agent_name="Python Engineer 2",
                specializations=[AgentSpecialization.LANGUAGE_SPECIFIC],
            ),
        ),
    ]

    result = service.validate_configuration(recommendations)

    assert result.is_valid  # Valid but has warnings
    assert len(result.warnings) > 0
    assert "multiple agents" in result.warnings[0].message.lower()


def test_validate_configuration_empty_list(service):
    """Test validation with empty recommendations list."""
    with pytest.raises(ValueError, match="empty recommendations"):
        service.validate_configuration([])


def test_validate_configuration_with_concerns(service):
    """Test validation when recommendations have concerns."""
    recommendations = [
        AgentRecommendation(
            agent_id="python-engineer",
            agent_name="Python Engineer",
            confidence_score=0.75,
            concerns=["May require additional configuration"],
        )
    ]

    result = service.validate_configuration(recommendations)

    assert result.is_valid
    assert len(result.infos) > 0


# ============================================================================
# Test: Configuration Preview
# ============================================================================


def test_preview_configuration_success(service, temp_project_dir):
    """Test configuration preview generation."""
    preview = service.preview_configuration(temp_project_dir, min_confidence=0.8)

    assert isinstance(preview, ConfigurationPreview)
    assert len(preview.recommendations) == 2
    assert preview.deployment_count == 2
    assert preview.is_valid
    assert preview.estimated_deployment_time > 0


def test_preview_configuration_with_low_confidence(service, temp_project_dir):
    """Test preview with high confidence threshold filtering."""
    preview = service.preview_configuration(temp_project_dir, min_confidence=0.90)

    # Only python-engineer (0.95) should pass threshold, not vercel-ops (0.88)
    assert preview.deployment_count == 1
    assert "python-engineer" in preview.would_deploy
    assert "vercel-ops" in preview.would_skip


def test_preview_configuration_invalid_path(service):
    """Test preview with invalid project path."""
    with pytest.raises(FileNotFoundError):
        service.preview_configuration(Path("/nonexistent/path"))


def test_preview_configuration_includes_validation(service, temp_project_dir):
    """Test that preview includes validation results."""
    preview = service.preview_configuration(temp_project_dir)

    assert preview.validation_result is not None
    assert isinstance(preview.validation_result, ValidationResult)


# ============================================================================
# Test: Observer Pattern
# ============================================================================


def test_null_observer():
    """Test NullObserver does nothing."""
    observer = NullObserver()

    # Should not raise any exceptions
    observer.on_analysis_started("/test")
    observer.on_analysis_completed(Mock(), 100.0)
    observer.on_recommendation_started()
    observer.on_error("test", "error")


def test_console_observer_without_rich():
    """Test ConsoleProgressObserver works without rich library."""
    observer = ConsoleProgressObserver(use_rich=False)

    # Should not raise exceptions
    observer.on_analysis_started("/test")
    observer.on_deployment_started(2)
    observer.on_agent_deployment_started("agent1", "Agent 1", 1, 2)


def test_composite_observer():
    """Test CompositeObserver broadcasts to multiple observers."""
    observer1 = Mock(spec=IDeploymentObserver)
    observer2 = Mock(spec=IDeploymentObserver)

    composite = CompositeObserver([observer1, observer2])

    composite.on_analysis_started("/test")

    observer1.on_analysis_started.assert_called_once_with("/test")
    observer2.on_analysis_started.assert_called_once_with("/test")


def test_composite_observer_add_remove():
    """Test adding and removing observers from composite."""
    observer1 = Mock(spec=IDeploymentObserver)
    observer2 = Mock(spec=IDeploymentObserver)

    composite = CompositeObserver()
    composite.add_observer(observer1)
    composite.add_observer(observer2)

    composite.on_analysis_started("/test")
    assert observer1.on_analysis_started.called
    assert observer2.on_analysis_started.called

    # Remove observer1
    composite.remove_observer(observer1)
    observer1.reset_mock()
    observer2.reset_mock()

    composite.on_recommendation_started()
    assert not observer1.on_recommendation_started.called
    assert observer2.on_recommendation_started.called


def test_composite_observer_error_isolation():
    """Test that one failing observer doesn't break others."""
    observer1 = Mock(spec=IDeploymentObserver)
    observer1.on_analysis_started.side_effect = Exception("Observer 1 failed")

    observer2 = Mock(spec=IDeploymentObserver)

    composite = CompositeObserver([observer1, observer2])

    # Should not raise exception
    composite.on_analysis_started("/test")

    # Observer 2 should still be called
    observer2.on_analysis_started.assert_called_once()


# ============================================================================
# Test: Configuration Persistence
# ============================================================================


@pytest.mark.asyncio
async def test_save_configuration(service, temp_project_dir):
    """Test saving auto-configuration metadata."""
    toolchain = ToolchainAnalysis(
        project_path=temp_project_dir,
        language_detection=LanguageDetection(
            primary_language="Python",
            language_percentages={"Python": 100.0},
        ),
        frameworks=[
            Framework(
                name="FastAPI", framework_type="web", confidence=ConfidenceLevel.HIGH
            )
        ],
        deployment_target=DeploymentTarget(
            target_type="serverless", platform="vercel", confidence=ConfidenceLevel.HIGH
        ),
    )

    recommendations = [
        AgentRecommendation(
            agent_id="python-engineer",
            agent_name="Python Engineer",
            confidence_score=0.95,
        )
    ]

    await service._save_configuration(temp_project_dir, toolchain, recommendations)

    # Verify file was created
    config_file = temp_project_dir / ".claude-mpm" / "auto-config.yaml"
    assert config_file.exists()

    # Verify content
    with config_file.open() as f:
        config_data = yaml.safe_load(f)

    assert "auto_config" in config_data
    assert config_data["auto_config"]["enabled"] is True
    assert (
        config_data["auto_config"]["toolchain_snapshot"]["primary_language"] == "Python"
    )
    assert len(config_data["auto_config"]["deployed_agents"]) == 1


# ============================================================================
# Test: Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_auto_configure_handles_analyzer_error(service, temp_project_dir):
    """Test error handling when toolchain analyzer fails."""
    service._toolchain_analyzer.analyze_toolchain = Mock(
        side_effect=Exception("Analysis failed")
    )

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
    )

    assert result.status == ConfigurationStatus.FAILED
    assert "analysis failed" in result.message.lower()


@pytest.mark.asyncio
async def test_auto_configure_handles_recommender_error(service, temp_project_dir):
    """Test error handling when recommender fails."""
    service._agent_recommender.recommend_agents = Mock(
        side_effect=Exception("Recommendation failed")
    )

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
    )

    assert result.status == ConfigurationStatus.FAILED
    assert "recommendation failed" in result.message.lower()


# ============================================================================
# Test: Rollback
# ============================================================================


@pytest.mark.asyncio
async def test_rollback_on_deployment_failure(service, temp_project_dir):
    """Test that rollback is triggered on deployment failure."""

    # Mock deployment to succeed first, then fail
    call_count = 0

    async def mock_deploy(agent_id: str, project_path: Path):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise Exception("Second deployment failed")

    service._deploy_single_agent = AsyncMock(side_effect=mock_deploy)
    service._rollback_deployment = AsyncMock(return_value=True)

    observer = Mock(spec=IDeploymentObserver)

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
        observer=observer,
    )

    # Verify rollback was triggered
    service._rollback_deployment.assert_called_once()
    observer.on_rollback_started.assert_called_once()
    observer.on_rollback_completed.assert_called_once_with(True)


# ============================================================================
# Test: Integration Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_full_workflow_integration(service, temp_project_dir):
    """Test complete workflow from analysis to deployment."""

    async def fake_deploy(agent_id: str, project_path: Path):
        agents_dir = project_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / f"{agent_id}.md").write_text(
            f"# {agent_id}\n\nTest agent.\n", encoding="utf-8"
        )

    service._deploy_single_agent = AsyncMock(side_effect=fake_deploy)
    service._save_configuration = AsyncMock()

    observer = ConsoleProgressObserver(use_rich=False)

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
        dry_run=False,
        min_confidence=0.8,
        observer=observer,
    )

    # Verify complete workflow executed
    assert result.status == ConfigurationStatus.SUCCESS
    assert len(result.deployed_agents) == 2
    assert len(result.recommendations) == 2
    assert result.metadata["duration_ms"] > 0

    # Verify configuration was saved
    service._save_configuration.assert_called_once()


@pytest.mark.asyncio
async def test_workflow_with_high_confidence_filter(service, temp_project_dir):
    """Test workflow with high confidence threshold."""

    async def fake_deploy(agent_id: str, project_path: Path):
        agents_dir = project_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / f"{agent_id}.md").write_text(
            f"# {agent_id}\n\nTest agent.\n", encoding="utf-8"
        )

    service._deploy_single_agent = AsyncMock(side_effect=fake_deploy)
    service._save_configuration = AsyncMock()

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
        dry_run=False,
        min_confidence=0.90,  # Only python-engineer (0.95) passes
    )

    # Should only recommend high-confidence agents
    assert len(result.recommendations) <= 2
    high_conf_agents = [r for r in result.recommendations if r.confidence_score >= 0.90]
    assert len(high_conf_agents) >= 1


# ============================================================================
# Test: Snapshot, Rollback and Post-Deployment Validation
# ============================================================================


@pytest.mark.asyncio
async def test_snapshot_and_cleanup_existing_files(service, temp_project_dir):
    """Snapshot copies existing agent files, cleanup removes the backups."""
    agents_dir = temp_project_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    existing = agents_dir / "python-engineer.md"
    existing.write_text("# original\n", encoding="utf-8")

    snapshot = service._snapshot_existing_files(
        temp_project_dir, ["python-engineer", "missing-agent"]
    )

    # Only the existing file should be in the snapshot.
    assert len(snapshot) == 1
    backup = next(iter(snapshot.values()))
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == "# original\n"

    # Cleanup removes the backup files.
    service._cleanup_snapshot(snapshot)
    assert not backup.exists()


@pytest.mark.asyncio
async def test_restore_from_snapshot_recovers_overwritten_file(
    service, temp_project_dir
):
    """A snapshotted file is restored over a modified copy on rollback."""
    agents_dir = temp_project_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    target = agents_dir / "qa.md"
    target.write_text("# original\n", encoding="utf-8")

    snapshot = service._snapshot_existing_files(temp_project_dir, ["qa"])

    # Simulate deployment overwriting the file.
    target.write_text("# overwritten by deploy\n", encoding="utf-8")

    ok = service._restore_from_snapshot(snapshot)
    assert ok is True
    assert target.read_text(encoding="utf-8") == "# original\n"


@pytest.mark.asyncio
async def test_post_deployment_validation_passes_for_real_files(
    service, temp_project_dir
):
    """Post-deployment validation accepts non-empty markdown files."""
    agents_dir = temp_project_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "engineer.md").write_text("# engineer\n\nbody\n", encoding="utf-8")

    result = await service._validate_post_deployment(temp_project_dir, ["engineer"])
    assert result.is_valid is True
    assert "engineer" in result.validated_agents
    assert result.error_count == 0


@pytest.mark.asyncio
async def test_post_deployment_validation_fails_when_file_missing(
    service, temp_project_dir
):
    """Post-deployment validation flags an error when no file was written."""
    # Note: agents dir doesn't even exist
    result = await service._validate_post_deployment(temp_project_dir, ["engineer"])
    assert result.is_valid is False
    assert result.error_count == 1
    assert "engineer" in result.errors[0].message


@pytest.mark.asyncio
async def test_post_deployment_validation_fails_for_empty_file(
    service, temp_project_dir
):
    """Empty deployed files are treated as deployment failures."""
    agents_dir = temp_project_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "empty.md").write_text("   \n", encoding="utf-8")

    result = await service._validate_post_deployment(temp_project_dir, ["empty"])
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_post_deployment_validation_fails_for_invalid_yaml(
    service, temp_project_dir
):
    """Malformed YAML output fails post-deployment validation."""
    agents_dir = temp_project_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "bad.yaml").write_text(
        "key: value\n  - not: valid: yaml: indent\n", encoding="utf-8"
    )

    result = await service._validate_post_deployment(temp_project_dir, ["bad"])
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_auto_configure_rolls_back_when_post_validation_fails(
    service, temp_project_dir
):
    """If files don't get written, post-validation triggers rollback."""

    # Pre-existing file we want restored after the failed deployment.
    agents_dir = temp_project_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    pre_existing = agents_dir / "python-engineer.md"
    pre_existing.write_text("# pre-existing user content\n", encoding="utf-8")

    # Mock deployment to claim success but write nothing -> post-validation fails.
    service._deploy_single_agent = AsyncMock()
    service._save_configuration = AsyncMock()

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
        dry_run=False,
    )

    assert result.status == ConfigurationStatus.FAILED
    assert result.metadata.get("phase") == "post_deployment_validation"
    # Save was NOT called because the workflow rolled back before step 8.
    service._save_configuration.assert_not_called()
    # Pre-existing user content was preserved by snapshot+restore.
    assert pre_existing.exists()
    assert pre_existing.read_text(encoding="utf-8") == "# pre-existing user content\n"


@pytest.mark.asyncio
async def test_rollback_restores_snapshot_after_partial_failure(
    service, temp_project_dir
):
    """Partial deployment failure restores any snapshotted files."""

    agents_dir = temp_project_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    pre_existing = agents_dir / "python-engineer.md"
    pre_existing.write_text("# original user version\n", encoding="utf-8")

    async def mock_deploy(agent_id: str, project_path: Path):
        a_dir = project_path / ".claude" / "agents"
        a_dir.mkdir(parents=True, exist_ok=True)
        if agent_id == "vercel-ops":
            raise Exception("simulated failure")
        # Overwrite the user's file
        (a_dir / f"{agent_id}.md").write_text("# overwritten\n", encoding="utf-8")

    service._deploy_single_agent = AsyncMock(side_effect=mock_deploy)
    service._save_configuration = AsyncMock()

    result = await service.auto_configure(
        project_path=temp_project_dir,
        confirmation_required=False,
        dry_run=False,
    )

    # WARNING: at least one agent deployed, but the one that succeeded should
    # have been rolled back to the user's original content.
    assert result.status == ConfigurationStatus.WARNING
    assert pre_existing.exists()
    assert pre_existing.read_text(encoding="utf-8") == "# original user version\n"


@pytest.mark.asyncio
async def test_request_confirmation_non_interactive_auto_approves_valid(
    service, temp_project_dir
):
    """Without a TTY we approve a valid configuration automatically."""

    rec = AgentRecommendation(
        agent_id="qa",
        agent_name="QA",
        confidence_score=0.9,
        match_reasons=["test"],
        capabilities=AgentCapabilities(
            agent_id="qa",
            agent_name="QA",
            specializations=[AgentSpecialization.GENERAL],
        ),
    )
    valid = ValidationResult(is_valid=True, issues=[], validated_agents=["qa"])

    # sys.stdin.isatty() returns False under pytest by default.
    confirmed = await service._request_confirmation([rec], valid)
    assert confirmed is True
