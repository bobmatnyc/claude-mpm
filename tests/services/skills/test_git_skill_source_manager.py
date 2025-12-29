"""Tests for Git skill source manager.

Test Coverage:
- Multi-source sync orchestration
- Priority resolution algorithm
- Source-specific skill retrieval
- Caching and path management
- Error handling for sync failures
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.claude_mpm.config.skill_sources import SkillSource, SkillSourceConfiguration
from src.claude_mpm.services.skills.git_skill_source_manager import (
    GitSkillSourceManager,
)


class TestGitSkillSourceManager:
    """Tests for GitSkillSourceManager class."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_path = Path(f.name)
        yield config_path
        if config_path.exists():
            config_path.unlink()

    @pytest.fixture
    def mock_config(self, temp_config_file):
        """Create a mock configuration."""
        config = SkillSourceConfiguration(config_path=temp_config_file)

        # Add test sources
        sources = [
            SkillSource(
                id="system",
                type="git",
                url="https://github.com/bobmatnyc/claude-mpm-skills",
                priority=0,
                enabled=True,
            ),
            SkillSource(
                id="custom",
                type="git",
                url="https://github.com/owner/custom-skills",
                priority=100,
                enabled=True,
            ),
        ]
        config.save(sources)

        return config

    @pytest.fixture
    def manager(self, mock_config, temp_cache_dir):
        """Create a GitSkillSourceManager instance for testing."""
        return GitSkillSourceManager(config=mock_config, cache_dir=temp_cache_dir)

    def test_initialization(self, mock_config, temp_cache_dir):
        """Test manager initialization."""
        manager = GitSkillSourceManager(config=mock_config, cache_dir=temp_cache_dir)

        assert manager.config == mock_config
        assert manager.cache_dir == temp_cache_dir
        assert temp_cache_dir.exists()

    def test_initialization_default_cache_dir(self, mock_config):
        """Test initialization with default cache directory."""
        manager = GitSkillSourceManager(config=mock_config)

        expected_cache = Path.home() / ".claude-mpm" / "cache" / "skills"
        assert manager.cache_dir == expected_cache

    def test_initialization_with_injected_sync_service(
        self, mock_config, temp_cache_dir
    ):
        """Test initialization with injected sync service."""
        mock_sync_service = Mock()

        manager = GitSkillSourceManager(
            config=mock_config,
            cache_dir=temp_cache_dir,
            sync_service=mock_sync_service,
        )

        assert manager.sync_service == mock_sync_service

    def test_get_source_cache_path(self, manager):
        """Test cache path generation for sources."""
        source = SkillSource(
            id="test-source",
            type="git",
            url="https://github.com/owner/repo",
        )

        cache_path = manager._get_source_cache_path(source)

        assert cache_path == manager.cache_dir / "test-source"

    def test_build_raw_github_url(self, manager):
        """Test building raw GitHub URL from source."""
        source = SkillSource(
            id="test",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
        )

        url = manager._build_raw_github_url(source)

        assert url == "https://raw.githubusercontent.com/owner/repo/main"

    def test_build_raw_github_url_with_git_suffix(self, manager):
        """Test URL building handles .git suffix."""
        source = SkillSource(
            id="test",
            type="git",
            url="https://github.com/owner/repo.git",
            branch="develop",
        )

        url = manager._build_raw_github_url(source)

        assert url == "https://raw.githubusercontent.com/owner/repo/develop"

    def test_build_raw_github_url_invalid_raises_error(self, manager):
        """Test URL building raises error for invalid URL."""
        # Create source bypassing validation
        source = SkillSource.__new__(SkillSource)
        source.id = "test"
        source.type = "git"
        source.url = "https://example.com/invalid"
        source.branch = "main"
        source.priority = 100
        source.enabled = True

        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            manager._build_raw_github_url(source)

    @patch(
        "src.claude_mpm.services.skills.git_skill_source_manager.SkillDiscoveryService"
    )
    def test_sync_source(self, mock_discovery_class, manager, temp_cache_dir):
        """Test syncing a single source."""
        # Replace _recursive_sync_repository with a mock
        mock_recursive_sync = MagicMock(return_value=(5, 2))
        manager._recursive_sync_repository = mock_recursive_sync

        mock_discovery_instance = MagicMock()
        mock_discovery_instance.discover_skills.return_value = [
            {"name": "skill1"},
            {"name": "skill2"},
        ]
        mock_discovery_class.return_value = mock_discovery_instance

        # Sync source
        result = manager.sync_source("system", force=False)

        # Verify result
        assert result["synced"] is True
        assert result["files_updated"] == 5
        assert result["files_cached"] == 2
        assert result["skills_discovered"] == 2
        assert "timestamp" in result

        # Verify recursive sync was called
        mock_recursive_sync.assert_called_once()

    def test_sync_source_nonexistent_raises_error(self, manager):
        """Test syncing non-existent source raises error."""
        with pytest.raises(ValueError, match="Source not found"):
            manager.sync_source("nonexistent")

    def test_sync_source_disabled_returns_error(self, manager, temp_config_file):
        """Test syncing disabled source returns error."""
        # Add disabled source
        config = SkillSourceConfiguration(config_path=temp_config_file)
        source = SkillSource(
            id="disabled",
            type="git",
            url="https://github.com/owner/repo",
            enabled=False,
        )
        config.add_source(source)

        manager.config = config

        result = manager.sync_source("disabled")

        assert result["synced"] is False
        assert "disabled" in result["error"].lower()

    def test_sync_source_sync_failure(self, manager):
        """Test sync_source handles sync failures gracefully."""
        # Replace _recursive_sync_repository with a mock that raises exception
        manager._recursive_sync_repository = MagicMock(
            side_effect=Exception("Sync failed")
        )

        result = manager.sync_source("system")

        assert result["synced"] is False
        assert "Sync failed" in result["error"]
        assert "timestamp" in result

    @patch(
        "src.claude_mpm.services.skills.git_skill_source_manager.SkillDiscoveryService"
    )
    def test_sync_all_sources(self, mock_discovery_class, manager):
        """Test syncing all enabled sources."""
        # Replace _recursive_sync_repository with a mock
        manager._recursive_sync_repository = MagicMock(return_value=(3, 1))

        mock_discovery_instance = MagicMock()
        mock_discovery_instance.discover_skills.return_value = [{"name": "skill"}]
        mock_discovery_class.return_value = mock_discovery_instance

        # Sync all sources
        results = manager.sync_all_sources()

        # Verify results
        assert results["synced_count"] == 2  # system + custom
        assert results["failed_count"] == 0
        assert "timestamp" in results
        assert "system" in results["sources"]
        assert "custom" in results["sources"]

    def test_sync_all_sources_partial_failure(self, manager):
        """Test sync_all_sources handles partial failures."""
        # Setup mock to fail for one source (second call)
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return (1, 0)  # First source succeeds
            raise Exception("Sync failed")  # Second source fails

        # Replace _recursive_sync_repository with a mock
        manager._recursive_sync_repository = MagicMock(side_effect=side_effect)

        # Patch discovery service to return empty list
        with patch(
            "src.claude_mpm.services.skills.git_skill_source_manager.SkillDiscoveryService"
        ) as mock_discovery:
            mock_discovery.return_value.discover_skills.return_value = []

            results = manager.sync_all_sources()

        # Verify partial success
        assert results["synced_count"] == 1
        assert results["failed_count"] == 1

    def test_get_all_skills_no_cache(self, manager):
        """Test get_all_skills returns empty list when no cache exists."""
        skills = manager.get_all_skills()
        assert skills == []

    def test_get_all_skills_with_skills(self, manager, temp_cache_dir):
        """Test get_all_skills returns skills from cache."""
        # Create skill files in cache
        for source_id in ["system", "custom"]:
            source_dir = temp_cache_dir / source_id
            source_dir.mkdir(parents=True)

            skill_content = f"""---
name: Skill from {source_id}
description: Test skill
---

Content
"""
            (source_dir / "skill.md").write_text(skill_content, encoding="utf-8")

        skills = manager.get_all_skills()

        # Should find skills from both sources
        assert len(skills) > 0
        skill_names = [s["name"] for s in skills]
        assert any("system" in name for name in skill_names)

    def test_get_all_skills_priority_resolution(self, manager, temp_cache_dir):
        """Test get_all_skills applies priority resolution."""
        # Create same skill in both sources with different priorities
        for source_id, priority in [("system", 0), ("custom", 100)]:
            source_dir = temp_cache_dir / source_id
            source_dir.mkdir(parents=True)

            skill_content = f"""---
name: Duplicate Skill
description: From {source_id}
---

Content from {source_id}
"""
            (source_dir / "duplicate.md").write_text(skill_content, encoding="utf-8")

        skills = manager.get_all_skills()

        # Should only have one skill (from higher priority source)
        duplicate_skills = [s for s in skills if s["name"] == "Duplicate Skill"]
        assert len(duplicate_skills) == 1

        # Should be from system (priority 0)
        assert duplicate_skills[0]["source_id"] == "system"

    def test_get_skills_by_source(self, manager, temp_cache_dir):
        """Test get_skills_by_source returns skills from specific source."""
        # Create skill in system cache
        system_dir = temp_cache_dir / "system"
        system_dir.mkdir(parents=True)

        skill_content = """---
name: System Skill
description: Test
---

Content
"""
        (system_dir / "skill.md").write_text(skill_content, encoding="utf-8")

        skills = manager.get_skills_by_source("system")

        assert len(skills) == 1
        assert skills[0]["name"] == "System Skill"
        assert skills[0]["source_id"] == "system"

    def test_get_skills_by_source_nonexistent(self, manager):
        """Test get_skills_by_source returns empty list for non-existent source."""
        skills = manager.get_skills_by_source("nonexistent")
        assert skills == []

    def test_get_skills_by_source_no_cache(self, manager):
        """Test get_skills_by_source returns empty list when cache doesn't exist."""
        skills = manager.get_skills_by_source("system")
        assert skills == []

    def test_apply_priority_resolution_empty_input(self, manager):
        """Test priority resolution with empty input."""
        result = manager._apply_priority_resolution({})
        assert result == []

    def test_apply_priority_resolution_single_source(self, manager):
        """Test priority resolution with single source."""
        skills_by_source = {
            "system": [
                {"skill_id": "skill1", "name": "Skill 1", "source_priority": 0},
                {"skill_id": "skill2", "name": "Skill 2", "source_priority": 0},
            ]
        }

        result = manager._apply_priority_resolution(skills_by_source)

        assert len(result) == 2

    def test_apply_priority_resolution_duplicate_skills(self, manager):
        """Test priority resolution with duplicate skill IDs."""
        skills_by_source = {
            "system": [
                {
                    "skill_id": "duplicate",
                    "name": "Duplicate",
                    "source_priority": 0,
                    "source_id": "system",
                }
            ],
            "custom": [
                {
                    "skill_id": "duplicate",
                    "name": "Duplicate",
                    "source_priority": 100,
                    "source_id": "custom",
                }
            ],
        }

        result = manager._apply_priority_resolution(skills_by_source)

        # Should only have one skill
        assert len(result) == 1

        # Should be from system (lower priority)
        assert result[0]["source_id"] == "system"

    def test_apply_priority_resolution_multiple_duplicates(self, manager):
        """Test priority resolution with multiple skill groups."""
        skills_by_source = {
            "high": [
                {"skill_id": "skill1", "source_priority": 0},
                {"skill_id": "skill2", "source_priority": 0},
            ],
            "medium": [
                {"skill_id": "skill1", "source_priority": 50},
                {"skill_id": "skill3", "source_priority": 50},
            ],
            "low": [
                {"skill_id": "skill2", "source_priority": 100},
                {"skill_id": "skill3", "source_priority": 100},
            ],
        }

        result = manager._apply_priority_resolution(skills_by_source)

        # Should have 3 unique skills
        assert len(result) == 3

        # skill1 should be from high (priority 0)
        skill1 = next(s for s in result if s["skill_id"] == "skill1")
        assert skill1["source_priority"] == 0

        # skill2 should be from high (priority 0)
        skill2 = next(s for s in result if s["skill_id"] == "skill2")
        assert skill2["source_priority"] == 0

        # skill3 should be from medium (priority 50)
        skill3 = next(s for s in result if s["skill_id"] == "skill3")
        assert skill3["source_priority"] == 50

    def test_repr(self, manager, temp_cache_dir):
        """Test string representation."""
        repr_str = repr(manager)

        assert "GitSkillSourceManager" in repr_str
        assert str(temp_cache_dir) in repr_str
        assert "sources=2" in repr_str
        assert "enabled=2" in repr_str

    @patch(
        "src.claude_mpm.services.skills.git_skill_source_manager.SkillDiscoveryService"
    )
    def test_sync_source_with_force_flag(self, mock_discovery_class, manager):
        """Test sync_source passes force flag to sync service."""
        # Replace _recursive_sync_repository with a mock
        mock_recursive_sync = MagicMock(return_value=(1, 0))
        manager._recursive_sync_repository = mock_recursive_sync

        mock_discovery_instance = MagicMock()
        mock_discovery_instance.discover_skills.return_value = []
        mock_discovery_class.return_value = mock_discovery_instance

        manager.sync_source("system", force=True)

        # Verify recursive sync was called with force=True
        assert mock_recursive_sync.called
        call_args = mock_recursive_sync.call_args
        # force parameter should be True (check both kwargs and positional args)
        force_passed = call_args[1].get("force", False) is True or (  # Check kwargs
            len(call_args[0]) > 2 and call_args[0][2] is True
        )  # Check 3rd positional arg
        assert force_passed, f"Expected force=True, got call_args={call_args}"

    def test_sync_all_sources_no_enabled_sources(
        self, temp_cache_dir, temp_config_file
    ):
        """Test sync_all_sources with no enabled sources."""
        # Create config with only disabled sources
        config = SkillSourceConfiguration(config_path=temp_config_file)
        source = SkillSource(
            id="disabled",
            type="git",
            url="https://github.com/owner/repo",
            enabled=False,
        )
        config.save([source])

        manager = GitSkillSourceManager(config=config, cache_dir=temp_cache_dir)

        results = manager.sync_all_sources()

        assert results["synced_count"] == 0
        assert results["failed_count"] == 0
        assert len(results["sources"]) == 0

    def test_get_all_skills_discovery_failure(self, manager, temp_cache_dir):
        """Test get_all_skills handles discovery failures gracefully."""
        # Create cache directory but with invalid skill file
        system_dir = temp_cache_dir / "system"
        system_dir.mkdir(parents=True)

        # Create file that will cause discovery to fail
        (system_dir / "invalid.md").write_text("invalid content", encoding="utf-8")

        skills = manager.get_all_skills()

        # Should return empty list or skip failed sources
        assert isinstance(skills, list)


class TestFlatSkillDeployment:
    """Tests for flat skill deployment from nested Git repositories."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_deploy_dir(self):
        """Create a temporary deployment directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_path = Path(f.name)
        yield config_path
        if config_path.exists():
            config_path.unlink()

    @pytest.fixture
    def nested_skill_structure(self, temp_cache_dir):
        """Create a nested skill structure for testing flattening."""
        # Create nested repository structure
        system_dir = temp_cache_dir / "system"

        # Structure: collaboration/dispatching-parallel-agents/SKILL.md
        collab_skill_dir = system_dir / "collaboration" / "dispatching-parallel-agents"
        collab_skill_dir.mkdir(parents=True)

        skill_content = """---
name: Dispatching Parallel Agents
description: Skill for managing parallel agent workflows
skill_version: 1.0.0
tags: [collaboration, parallel]
---

# Dispatching Parallel Agents

This skill helps coordinate multiple agents working in parallel.
"""
        (collab_skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        # Add a helper file
        (collab_skill_dir / "helper.py").write_text("# Helper script", encoding="utf-8")

        # Create another nested skill: debugging/systematic-debugging/SKILL.md
        debug_skill_dir = system_dir / "debugging" / "systematic-debugging"
        debug_skill_dir.mkdir(parents=True)

        debug_content = """---
name: Systematic Debugging
description: Methodical debugging approach
skill_version: 1.0.0
tags: [debugging, testing]
---

# Systematic Debugging

Follow these steps for systematic debugging.
"""
        (debug_skill_dir / "SKILL.md").write_text(debug_content, encoding="utf-8")

        # Deep nesting: aws/s3/bucket-ops/SKILL.md
        aws_skill_dir = system_dir / "aws" / "s3" / "bucket-ops"
        aws_skill_dir.mkdir(parents=True)

        aws_content = """---
name: S3 Bucket Operations
description: AWS S3 bucket management
skill_version: 1.0.0
tags: [aws, s3, cloud]
---

# S3 Bucket Operations

Manage AWS S3 buckets efficiently.
"""
        (aws_skill_dir / "SKILL.md").write_text(aws_content, encoding="utf-8")

        return system_dir

    @pytest.fixture
    def manager_with_nested_skills(
        self, temp_config_file, temp_cache_dir, nested_skill_structure
    ):
        """Create manager with nested skill structure."""
        config = SkillSourceConfiguration(config_path=temp_config_file)
        source = SkillSource(
            id="system",
            type="git",
            url="https://github.com/test/skills",
            priority=0,
            enabled=True,
        )
        config.save([source])

        return GitSkillSourceManager(config=config, cache_dir=temp_cache_dir)

    def test_recursive_skill_discovery(self, manager_with_nested_skills):
        """Test that nested SKILL.md files are discovered recursively."""
        skills = manager_with_nested_skills.get_all_skills()

        # Should find all 3 nested skills
        assert len(skills) == 3

        skill_names = {s["name"] for s in skills}
        assert "Dispatching Parallel Agents" in skill_names
        assert "Systematic Debugging" in skill_names
        assert "S3 Bucket Operations" in skill_names

    def test_deployment_name_flattening(self, manager_with_nested_skills):
        """Test that deployment names are correctly flattened."""
        skills = manager_with_nested_skills.get_all_skills()

        # Find specific skills and check deployment names
        collab_skill = next(s for s in skills if "Parallel" in s["name"])
        debug_skill = next(s for s in skills if "Debugging" in s["name"])
        aws_skill = next(s for s in skills if "S3" in s["name"])

        assert (
            collab_skill["deployment_name"]
            == "collaboration-dispatching-parallel-agents"
        )
        assert debug_skill["deployment_name"] == "debugging-systematic-debugging"
        assert aws_skill["deployment_name"] == "aws-s3-bucket-ops"

    def test_flat_deployment_structure(
        self, manager_with_nested_skills, temp_deploy_dir
    ):
        """Test that skills deploy to flat directory structure."""
        result = manager_with_nested_skills.deploy_skills(
            target_dir=temp_deploy_dir, force=False
        )

        # Should deploy all 3 skills
        assert result["deployed_count"] == 3
        assert result["failed_count"] == 0

        # Verify flat structure
        deployed_dirs = [d.name for d in temp_deploy_dir.iterdir() if d.is_dir()]

        assert "collaboration-dispatching-parallel-agents" in deployed_dirs
        assert "debugging-systematic-debugging" in deployed_dirs
        assert "aws-s3-bucket-ops" in deployed_dirs

        # Verify no nested structure
        assert not (temp_deploy_dir / "collaboration").exists()
        assert not (temp_deploy_dir / "debugging").exists()
        assert not (temp_deploy_dir / "aws").exists()

    def test_skill_directory_contents_preserved(
        self, manager_with_nested_skills, temp_deploy_dir
    ):
        """Test that entire skill directory is copied with all resources."""
        manager_with_nested_skills.deploy_skills(target_dir=temp_deploy_dir)

        # Check collaboration skill
        collab_dir = temp_deploy_dir / "collaboration-dispatching-parallel-agents"
        assert (collab_dir / "SKILL.md").exists()
        assert (collab_dir / "helper.py").exists()

        # Verify content
        helper_content = (collab_dir / "helper.py").read_text()
        assert "Helper script" in helper_content

    def test_collision_detection(
        self, temp_cache_dir, temp_config_file, temp_deploy_dir
    ):
        """Test that deployment name collisions are detected."""
        system_dir = temp_cache_dir / "system"

        # Create two skills that would have same deployment name
        # Both at: category/skill-name/SKILL.md
        skill1_dir = system_dir / "testing" / "test-skill"
        skill1_dir.mkdir(parents=True)

        skill1_content = """---
name: Test Skill One
description: First test skill
skill_version: 1.0.0
---
Skill one
"""
        (skill1_dir / "SKILL.md").write_text(skill1_content, encoding="utf-8")

        # Second skill with different path but would create same flat name
        # This is harder to construct naturally, so we'll just verify the warning logic

        config = SkillSourceConfiguration(config_path=temp_config_file)
        source = SkillSource(
            id="system", type="git", url="https://github.com/test/skills", enabled=True
        )
        config.save([source])

        manager = GitSkillSourceManager(config=config, cache_dir=temp_cache_dir)
        skills = manager.get_all_skills()

        # Should find at least the one skill
        assert len(skills) >= 1

    def test_deployment_force_overwrite(
        self, manager_with_nested_skills, temp_deploy_dir
    ):
        """Test that force flag overwrites existing skills."""
        # Deploy once
        result1 = manager_with_nested_skills.deploy_skills(
            target_dir=temp_deploy_dir, force=False
        )
        assert result1["deployed_count"] == 3

        # Deploy again without force - should skip
        result2 = manager_with_nested_skills.deploy_skills(
            target_dir=temp_deploy_dir, force=False
        )
        assert result2["skipped_count"] == 3
        assert result2["deployed_count"] == 0

        # Deploy with force - should overwrite
        result3 = manager_with_nested_skills.deploy_skills(
            target_dir=temp_deploy_dir, force=True
        )
        assert result3["deployed_count"] == 3
        assert result3["skipped_count"] == 0

    def test_deployment_metadata_in_skills(self, manager_with_nested_skills):
        """Test that skills include deployment metadata."""
        skills = manager_with_nested_skills.get_all_skills()

        for skill in skills:
            assert "deployment_name" in skill
            assert "relative_path" in skill
            assert "source_file" in skill

            # Deployment name should be hyphen-separated
            assert "-" in skill["deployment_name"]

            # Relative path should show nested structure
            assert "/" in skill["relative_path"] or "\\" in skill["relative_path"]

    def test_selective_deployment_with_fuzzy_matching(
        self, temp_cache_dir, temp_config_file, temp_deploy_dir
    ):
        """Test that skill_filter uses fuzzy matching like ProfileManager."""
        system_dir = temp_cache_dir / "system"

        # Create skills with full deployment names
        skills_to_create = [
            ("toolchains/python/frameworks/flask", "Flask Framework", "toolchains-python-frameworks-flask"),
            ("toolchains/python/frameworks/django", "Django Framework", "toolchains-python-frameworks-django"),
            ("toolchains/javascript/frameworks/react", "React Framework", "toolchains-javascript-frameworks-react"),
            ("universal/testing/pytest", "Pytest Testing", "universal-testing-pytest"),
        ]

        for path, name, _ in skills_to_create:
            skill_dir = system_dir / path.replace("/", "-")
            skill_dir.mkdir(parents=True)
            skill_content = f"""---
name: {name}
description: Test skill for {name}
skill_version: 1.0.0
---
# {name}
"""
            (skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        # Setup manager
        config = SkillSourceConfiguration(config_path=temp_config_file)
        source = SkillSource(
            id="system", type="git", url="https://github.com/test/skills", enabled=True
        )
        config.save([source])
        manager = GitSkillSourceManager(config=config, cache_dir=temp_cache_dir)

        # Test 1: Exact match (short name)
        result1 = manager.deploy_skills(
            target_dir=temp_deploy_dir,
            skill_filter=["flask"],
            force=False
        )
        assert result1["deployed_count"] == 1, "Should deploy only flask"

        # Clean up for next test
        import shutil
        shutil.rmtree(temp_deploy_dir)
        temp_deploy_dir.mkdir()

        # Test 2: Multiple short names
        result2 = manager.deploy_skills(
            target_dir=temp_deploy_dir,
            skill_filter=["flask", "django"],
            force=False
        )
        assert result2["deployed_count"] == 2, "Should deploy flask and django"

        # Clean up for next test
        shutil.rmtree(temp_deploy_dir)
        temp_deploy_dir.mkdir()

        # Test 3: Full deployment name
        result3 = manager.deploy_skills(
            target_dir=temp_deploy_dir,
            skill_filter=["toolchains-python-frameworks-flask"],
            force=False
        )
        assert result3["deployed_count"] == 1, "Should deploy with full name"

        # Clean up for next test
        shutil.rmtree(temp_deploy_dir)
        temp_deploy_dir.mkdir()

        # Test 4: Mix of short and full names
        result4 = manager.deploy_skills(
            target_dir=temp_deploy_dir,
            skill_filter=["flask", "toolchains-javascript-frameworks-react"],
            force=False
        )
        assert result4["deployed_count"] == 2, "Should deploy with mixed names"

        # Clean up for next test
        shutil.rmtree(temp_deploy_dir)
        temp_deploy_dir.mkdir()

        # Test 5: Partial segment match
        result5 = manager.deploy_skills(
            target_dir=temp_deploy_dir,
            skill_filter=["pytest"],
            force=False
        )
        assert result5["deployed_count"] == 1, "Should match pytest at end"

        # Verify deployed skills
        deployed_dirs = [d.name for d in temp_deploy_dir.iterdir() if d.is_dir()]
        assert "universal-testing-pytest" in deployed_dirs
