"""Integration tests for Phase 3: CLI integration and multi-project deployment.

Tests the complete two-phase sync workflow:
1. Sync to cache (~/.claude-mpm/cache/agents/)
2. Deploy to project (.claude-mpm/agents/)

Verifies:
- End-to-end sync → deploy workflow
- Multi-project isolation (one cache, multiple projects)
- Force flag behavior
- Migration from old paths
- Backward compatibility
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
)
from claude_mpm.services.skills.git_skill_source_manager import GitSkillSourceManager
from claude_mpm.config.skill_sources import SkillSourceConfiguration
from claude_mpm.utils.migration import MigrationUtility


class TestPhase3AgentDeployment:
    """Test agent deployment integration with two-phase sync."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temporary cache directory."""
        cache_dir = tmp_path / "cache" / "agents"
        cache_dir.mkdir(parents=True)
        return cache_dir

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary project directory."""
        project_dir = tmp_path / "project1"
        project_dir.mkdir()
        return project_dir

    @pytest.fixture
    def git_sync_service(self, temp_cache_dir):
        """Create GitSourceSyncService with temp cache."""
        with patch.object(
            GitSourceSyncService, "__init__", lambda self: None
        ):  # Skip init
            service = GitSourceSyncService()
            service.cache_dir = temp_cache_dir
            service.logger = MagicMock()
            return service

    def test_end_to_end_sync_and_deploy(
        self, git_sync_service, temp_cache_dir, temp_project_dir
    ):
        """Test complete sync to cache → deploy to project workflow."""
        # Setup: Create mock cached agents
        (temp_cache_dir / "engineer.md").write_text("# Engineer Agent")
        (temp_cache_dir / "research.md").write_text("# Research Agent")
        (temp_cache_dir / "qa.md").write_text("# QA Agent")

        # Execute: Deploy from cache to project
        result = git_sync_service.deploy_agents_to_project(
            project_dir=temp_project_dir, agent_list=None, force=False
        )

        # Verify: All agents deployed to project
        deployed_count = len(result["deployed"]) + len(result["updated"])
        assert deployed_count == 3

        deployment_dir = temp_project_dir / ".claude-mpm" / "agents"
        assert deployment_dir.exists()
        assert (deployment_dir / "engineer.md").exists()
        assert (deployment_dir / "research.md").exists()
        assert (deployment_dir / "qa.md").exists()

    def test_multi_project_isolation(
        self, git_sync_service, temp_cache_dir, tmp_path
    ):
        """Test that multiple projects can deploy from same cache independently."""
        # Setup: Create cached agents
        (temp_cache_dir / "engineer.md").write_text("# Engineer Agent v1")
        (temp_cache_dir / "research.md").write_text("# Research Agent v1")

        # Create two separate projects
        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project1.mkdir()
        project2.mkdir()

        # Deploy to project1
        result1 = git_sync_service.deploy_agents_to_project(
            project_dir=project1, agent_list=None, force=False
        )

        # Deploy to project2
        result2 = git_sync_service.deploy_agents_to_project(
            project_dir=project2, agent_list=None, force=False
        )

        # Verify: Both projects have independent deployments
        deployed1 = len(result1["deployed"]) + len(result1["updated"])
        deployed2 = len(result2["deployed"]) + len(result2["updated"])
        assert deployed1 == 2
        assert deployed2 == 2

        project1_agents = project1 / ".claude-mpm" / "agents"
        project2_agents = project2 / ".claude-mpm" / "agents"

        assert project1_agents.exists()
        assert project2_agents.exists()
        assert (project1_agents / "engineer.md").exists()
        assert (project2_agents / "engineer.md").exists()

        # Verify: Projects are isolated (modify one doesn't affect other)
        (project1_agents / "engineer.md").write_text("# Modified in project1")
        assert (
            project2_agents / "engineer.md"
        ).read_text() != "# Modified in project1"

    def test_force_flag_redeployment(
        self, git_sync_service, temp_cache_dir, temp_project_dir
    ):
        """Test force flag forces redeployment even when up-to-date."""
        # Setup: Create cached agent and deploy once
        (temp_cache_dir / "engineer.md").write_text("# Engineer Agent v1")
        git_sync_service.deploy_agents_to_project(
            project_dir=temp_project_dir, agent_list=None, force=False
        )

        # Modify deployed file
        deployment_dir = temp_project_dir / ".claude-mpm" / "agents"
        (deployment_dir / "engineer.md").write_text("# Modified locally")

        # Deploy again without force (should skip)
        result_no_force = git_sync_service.deploy_agents_to_project(
            project_dir=temp_project_dir, agent_list=None, force=False
        )
        assert len(result_no_force["skipped"]) > 0

        # Deploy with force (should overwrite)
        result_force = git_sync_service.deploy_agents_to_project(
            project_dir=temp_project_dir, agent_list=None, force=True
        )
        assert len(result_force["updated"]) > 0

        # Verify: Local modification was overwritten
        assert (deployment_dir / "engineer.md").read_text() == "# Engineer Agent v1"

    def test_selective_agent_deployment(
        self, git_sync_service, temp_cache_dir, temp_project_dir
    ):
        """Test deploying only specific agents from cache."""
        # Setup: Create multiple cached agents
        (temp_cache_dir / "engineer.md").write_text("# Engineer Agent")
        (temp_cache_dir / "research.md").write_text("# Research Agent")
        (temp_cache_dir / "qa.md").write_text("# QA Agent")

        # Deploy only engineer and research
        result = git_sync_service.deploy_agents_to_project(
            project_dir=temp_project_dir,
            agent_list=["engineer.md", "research.md"],
            force=False,
        )

        # Verify: Only specified agents deployed
        deployment_dir = temp_project_dir / ".claude-mpm" / "agents"
        assert (deployment_dir / "engineer.md").exists()
        assert (deployment_dir / "research.md").exists()
        assert not (deployment_dir / "qa.md").exists()


class TestPhase3SkillDeployment:
    """Test skill deployment integration with two-phase sync."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temporary skill cache directory."""
        cache_dir = tmp_path / "cache" / "skills"
        cache_dir.mkdir(parents=True)
        return cache_dir

    @pytest.fixture
    def skill_config(self):
        """Create minimal skill source configuration."""
        config = MagicMock(spec=SkillSourceConfiguration)
        config.repositories = []
        return config

    @pytest.fixture
    def git_skill_manager(self, skill_config, temp_cache_dir):
        """Create GitSkillSourceManager with temp cache."""
        with patch.object(
            GitSkillSourceManager, "__init__", lambda self, config: None
        ):
            manager = GitSkillSourceManager(skill_config)
            manager.cache_dir = temp_cache_dir
            manager.logger = MagicMock()
            return manager

    def test_skill_deployment_workflow(
        self, git_skill_manager, temp_cache_dir, tmp_path
    ):
        """Test complete skill sync → deploy workflow."""
        # Setup: Create mock cached skills
        skill1 = temp_cache_dir / "python-testing"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Python Testing Skill")

        skill2 = temp_cache_dir / "api-design"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# API Design Skill")

        project_dir = tmp_path / "project1"
        project_dir.mkdir()

        # Mock get_all_skills to return our test skills
        git_skill_manager.get_all_skills = MagicMock(
            return_value=[
                {
                    "name": "python-testing",
                    "deployment_name": "python-testing",
                    "source_file": str(skill1 / "SKILL.md"),
                },
                {
                    "name": "api-design",
                    "deployment_name": "api-design",
                    "source_file": str(skill2 / "SKILL.md"),
                },
            ]
        )

        # Execute: Deploy skills to project
        result = git_skill_manager.deploy_skills_to_project(
            project_dir=project_dir, skill_list=None, force=False
        )

        # Verify: Skills deployed to project
        deployment_dir = project_dir / ".claude-mpm" / "skills"
        assert deployment_dir.exists()
        assert (deployment_dir / "python-testing" / "SKILL.md").exists()
        assert (deployment_dir / "api-design" / "SKILL.md").exists()


class TestMigrationUtility:
    """Test migration from old directory structure."""

    @pytest.fixture
    def migration_util(self, tmp_path):
        """Create MigrationUtility with temp directories."""
        util = MigrationUtility()

        # Override with temp paths for testing
        util.old_agent_dir = tmp_path / ".claude" / "agents"
        util.old_skill_dir = tmp_path / ".claude" / "skills"
        util.new_agent_cache = tmp_path / ".claude-mpm" / "cache" / "agents"
        util.new_skill_cache = tmp_path / ".claude-mpm" / "cache" / "skills"

        return util

    def test_detect_old_locations(self, migration_util):
        """Test detection of old directory structure."""
        # Setup: Create old agent files
        migration_util.old_agent_dir.mkdir(parents=True)
        (migration_util.old_agent_dir / "engineer.md").write_text("# Engineer")
        (migration_util.old_agent_dir / "research.md").write_text("# Research")

        # Setup: Create old skill directories
        migration_util.old_skill_dir.mkdir(parents=True)
        skill_dir = migration_util.old_skill_dir / "python-testing"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Python Testing")

        # Execute: Detect old locations
        result = migration_util.detect_old_locations()

        # Verify: Detection found agents and skills
        assert result["agents_exists"] is True
        assert result["agents_count"] == 2
        assert result["skills_exists"] is True
        assert result["skills_count"] == 1

    def test_migrate_agents_dry_run(self, migration_util):
        """Test agent migration in dry-run mode."""
        # Setup: Create old agents
        migration_util.old_agent_dir.mkdir(parents=True)
        (migration_util.old_agent_dir / "engineer.md").write_text("# Engineer")

        # Execute: Dry run migration
        result = migration_util.migrate_agents(dry_run=True, auto_confirm=True)

        # Verify: Reports what would be migrated but doesn't copy
        assert result["dry_run"] is True
        assert result["migrated_count"] == 1
        assert not migration_util.new_agent_cache.exists()

    def test_migrate_agents_actual(self, migration_util):
        """Test actual agent migration (not dry-run)."""
        # Setup: Create old agents
        migration_util.old_agent_dir.mkdir(parents=True)
        (migration_util.old_agent_dir / "engineer.md").write_text("# Engineer")
        (migration_util.old_agent_dir / "research.md").write_text("# Research")

        # Execute: Actual migration
        result = migration_util.migrate_agents(dry_run=False, auto_confirm=True)

        # Verify: Files copied to new cache
        assert result["migrated_count"] == 2
        assert migration_util.new_agent_cache.exists()
        assert (migration_util.new_agent_cache / "engineer.md").exists()
        assert (migration_util.new_agent_cache / "research.md").exists()

        # Verify: Original files still exist (non-destructive)
        assert (migration_util.old_agent_dir / "engineer.md").exists()

    def test_migrate_skills(self, migration_util):
        """Test skill directory migration."""
        # Setup: Create old skill directory
        migration_util.old_skill_dir.mkdir(parents=True)
        skill_dir = migration_util.old_skill_dir / "python-testing"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Python Testing")
        (skill_dir / "examples.py").write_text("# Examples")

        # Execute: Migrate skills
        result = migration_util.migrate_skills(dry_run=False, auto_confirm=True)

        # Verify: Entire skill directory copied
        assert result["migrated_count"] == 1
        target_skill = migration_util.new_skill_cache / "python-testing"
        assert target_skill.exists()
        assert (target_skill / "SKILL.md").exists()
        assert (target_skill / "examples.py").exists()

    def test_migration_skips_duplicates(self, migration_util):
        """Test that migration skips files that already exist."""
        # Setup: Create old agents
        migration_util.old_agent_dir.mkdir(parents=True)
        (migration_util.old_agent_dir / "engineer.md").write_text("# Engineer")

        # First migration
        migration_util.migrate_agents(dry_run=False, auto_confirm=True)

        # Second migration (should skip)
        result = migration_util.migrate_agents(dry_run=False, auto_confirm=True)

        # Verify: Skipped on second run
        assert result["skipped_count"] == 1
        assert result["migrated_count"] == 0


class TestBackwardCompatibility:
    """Test fallback support for unmigrated systems."""

    def test_fallback_paths_returned(self, tmp_path):
        """Test that fallback paths are returned when old directories exist."""
        util = MigrationUtility()
        util.old_agent_dir = tmp_path / ".claude" / "agents"
        util.old_skill_dir = tmp_path / ".claude" / "skills"

        # Create old directories
        util.old_agent_dir.mkdir(parents=True)
        util.old_skill_dir.mkdir(parents=True)

        # Get fallback paths
        fallback = util.get_fallback_paths()

        # Verify: Old paths returned as fallback
        assert fallback["agent_dir"] == util.old_agent_dir
        assert fallback["skill_dir"] == util.old_skill_dir

    def test_deprecation_warning_generated(self, tmp_path):
        """Test deprecation warning is generated for old paths."""
        util = MigrationUtility()
        util.old_agent_dir = tmp_path / ".claude" / "agents"
        util.old_skill_dir = tmp_path / ".claude" / "skills"

        # Create old directories with files
        util.old_agent_dir.mkdir(parents=True)
        (util.old_agent_dir / "engineer.md").write_text("# Engineer")

        # Get deprecation warning
        warning = util.show_deprecation_warning()

        # Verify: Warning contains helpful information
        assert "DEPRECATION WARNING" in warning
        assert ".claude/agents" in warning
        assert "claude-mpm migrate" in warning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
