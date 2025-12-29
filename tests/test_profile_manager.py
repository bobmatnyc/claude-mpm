"""
Unit tests for ProfileManager service.

Tests profile loading, filtering, and glob pattern matching for skills.
"""

import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest
import yaml

from src.claude_mpm.services.profile_manager import ProfileManager


@pytest.fixture
def profiles_dir():
    """Create temporary profiles directory with test profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        profiles_path = Path(tmpdir) / ".claude-mpm" / "profiles"
        profiles_path.mkdir(parents=True)

        # Create test profiles
        _create_test_profile(
            profiles_path / "framework-development.yaml",
            {
                "profile": {
                    "name": "framework-development",
                    "description": "Python backend + TypeScript/Svelte dashboard",
                },
                "agents": {
                    "enabled": [
                        "python-engineer",
                        "typescript-engineer",
                        "svelte-engineer",
                    ],
                    "disabled": ["java-engineer", "dart-engineer"],
                },
                "skills": {
                    "enabled": ["flask", "pytest", "typescript-core"],
                    "disabled_categories": ["wordpress-*", "react-*", "php-*"],
                },
            },
        )

        _create_test_profile(
            profiles_path / "minimal.yaml",
            {
                "profile": {
                    "name": "minimal",
                    "description": "Minimal agent set for focused work",
                },
                "agents": {"enabled": ["pm"], "disabled": []},
                "skills": {"enabled": [], "disabled_categories": ["*"]},
            },
        )

        _create_test_profile(
            profiles_path / "all-disabled.yaml",
            {
                "profile": {"name": "all-disabled", "description": "All agents disabled"},
                "agents": {
                    "enabled": [],
                    "disabled": ["python-engineer", "typescript-engineer"],
                },
                "skills": {"enabled": [], "disabled_categories": []},
            },
        )

        yield profiles_path


def _create_test_profile(path: Path, data: Dict[str, Any]):
    """Helper to create a test profile YAML file."""
    with path.open("w") as f:
        yaml.safe_dump(data, f)


def test_list_available_profiles(profiles_dir):
    """Test listing available profiles."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    profiles = manager.list_available_profiles()

    assert len(profiles) == 3
    assert "framework-development" in profiles
    assert "minimal" in profiles
    assert "all-disabled" in profiles


def test_load_profile_success(profiles_dir):
    """Test successful profile loading."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    success = manager.load_profile("framework-development")

    assert success is True
    assert manager.active_profile == "framework-development"


def test_load_profile_not_found(profiles_dir):
    """Test loading non-existent profile."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    success = manager.load_profile("non-existent")

    assert success is False
    assert manager.active_profile is None


def test_get_profile_description(profiles_dir):
    """Test getting profile description."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    description = manager.get_profile_description("framework-development")

    assert description == "Python backend + TypeScript/Svelte dashboard"


def test_is_agent_enabled_with_enabled_list(profiles_dir):
    """Test agent filtering with enabled list."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    manager.load_profile("framework-development")

    # Agents in enabled list should be enabled
    assert manager.is_agent_enabled("python-engineer") is True
    assert manager.is_agent_enabled("typescript-engineer") is True

    # Agents not in enabled list should be disabled
    assert manager.is_agent_enabled("java-engineer") is False
    assert manager.is_agent_enabled("unknown-agent") is False


def test_is_agent_enabled_no_profile(profiles_dir):
    """Test agent filtering with no active profile."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    # No profile loaded - all agents should be enabled
    assert manager.is_agent_enabled("python-engineer") is True
    assert manager.is_agent_enabled("java-engineer") is True


def test_is_skill_enabled_with_patterns(profiles_dir):
    """Test skill filtering with glob patterns."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    manager.load_profile("framework-development")

    # Skills in enabled list should be enabled
    assert manager.is_skill_enabled("flask") is True
    assert manager.is_skill_enabled("pytest") is True

    # Skills matching disabled patterns should be disabled
    assert manager.is_skill_enabled("wordpress-plugin") is False
    assert manager.is_skill_enabled("wordpress-theme") is False
    assert manager.is_skill_enabled("react-hooks") is False
    assert manager.is_skill_enabled("php-laravel") is False

    # Skills not in enabled list and not matching patterns
    assert manager.is_skill_enabled("django") is False


def test_is_skill_enabled_wildcard_pattern(profiles_dir):
    """Test skill filtering with wildcard pattern."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    manager.load_profile("minimal")

    # Wildcard pattern should disable all skills
    assert manager.is_skill_enabled("flask") is False
    assert manager.is_skill_enabled("pytest") is False
    assert manager.is_skill_enabled("typescript-core") is False


def test_is_skill_enabled_no_profile(profiles_dir):
    """Test skill filtering with no active profile."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    # No profile loaded - all skills should be enabled
    assert manager.is_skill_enabled("flask") is True
    assert manager.is_skill_enabled("wordpress-plugin") is True


def test_get_enabled_agents(profiles_dir):
    """Test getting enabled agents set."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    manager.load_profile("framework-development")

    enabled = manager.get_enabled_agents()
    assert len(enabled) == 3
    assert "python-engineer" in enabled
    assert "typescript-engineer" in enabled
    assert "svelte-engineer" in enabled


def test_get_disabled_agents(profiles_dir):
    """Test getting disabled agents set."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    manager.load_profile("framework-development")

    disabled = manager.get_disabled_agents()
    assert len(disabled) == 2
    assert "java-engineer" in disabled
    assert "dart-engineer" in disabled


def test_get_enabled_skills(profiles_dir):
    """Test getting enabled skills set."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    manager.load_profile("framework-development")

    enabled = manager.get_enabled_skills()
    assert len(enabled) == 3
    assert "flask" in enabled
    assert "pytest" in enabled
    assert "typescript-core" in enabled


def test_get_disabled_skill_patterns(profiles_dir):
    """Test getting disabled skill patterns."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    manager.load_profile("framework-development")

    patterns = manager.get_disabled_skill_patterns()
    assert len(patterns) == 3
    assert "wordpress-*" in patterns
    assert "react-*" in patterns
    assert "php-*" in patterns


def test_get_filtering_summary(profiles_dir):
    """Test getting filtering summary."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    manager.load_profile("framework-development")

    summary = manager.get_filtering_summary()
    assert summary["active_profile"] == "framework-development"
    assert summary["enabled_agents_count"] == 3
    assert summary["disabled_agents_count"] == 2
    assert summary["enabled_skills_count"] == 3
    assert summary["disabled_patterns_count"] == 3


def test_glob_pattern_matching(profiles_dir):
    """Test various glob pattern matching scenarios."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    manager.load_profile("framework-development")

    # Test prefix matching
    assert manager.is_skill_enabled("wordpress-plugins") is False
    assert manager.is_skill_enabled("wordpress") is False

    # Test exact matching
    assert manager.is_skill_enabled("react") is False

    # Test nested patterns
    assert manager.is_skill_enabled("php-framework-laravel") is False
    assert manager.is_skill_enabled("php-testing") is False


def test_empty_profile_fields(profiles_dir):
    """Test profile with empty enabled/disabled lists."""
    # Create profile with empty lists
    empty_profile_path = profiles_dir / "empty.yaml"
    _create_test_profile(
        empty_profile_path,
        {
            "profile": {"name": "empty"},
            "agents": {"enabled": [], "disabled": []},
            "skills": {"enabled": [], "disabled_categories": []},
        },
    )

    manager = ProfileManager(profiles_dir=profiles_dir)
    manager.load_profile("empty")

    # With empty enabled list and no disabled list, all agents should be enabled
    assert manager.is_agent_enabled("python-engineer") is True

    # With empty enabled list and empty disabled patterns, all skills should be enabled
    assert manager.is_skill_enabled("flask") is True


def test_profile_with_only_disabled_agents(profiles_dir):
    """Test profile that only specifies disabled agents."""
    manager = ProfileManager(profiles_dir=profiles_dir)
    manager.load_profile("all-disabled")

    # Disabled agents should be disabled
    assert manager.is_agent_enabled("python-engineer") is False
    assert manager.is_agent_enabled("typescript-engineer") is False

    # Other agents should be enabled (not in disabled list)
    assert manager.is_agent_enabled("java-engineer") is True
