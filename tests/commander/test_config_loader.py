"""Tests for config_loader.

Tests cover:
- Loading configuration from .claude-mpm/ directory
- YAML parsing and validation
- Directory existence checks
- Error handling for malformed YAML
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from claude_mpm.commander.config_loader import load_project_config


class TestConfigLoading:
    """Tests for load_project_config function."""

    def test_no_config_directory(self):
        """Test returns None when .claude-mpm/ does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_project_config(tmpdir)
            assert result is None

    def test_empty_config_directory(self):
        """Test returns empty config when .claude-mpm/ exists but is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir()

            result = load_project_config(tmpdir)

            assert result is not None
            assert result["configuration"] == {}
            assert result["has_agents"] is False
            assert result["has_skills"] is False
            assert result["has_memories"] is False

    def test_load_configuration_yaml(self):
        """Test loads configuration.yaml correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir()

            # Create configuration.yaml
            config_data = {
                "default_adapter": "linear",
                "default_project": "PROJ-123",
                "settings": {"timeout": 30},
            }

            config_file = config_dir / "configuration.yaml"
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            result = load_project_config(tmpdir)

            assert result is not None
            assert result["configuration"] == config_data
            assert result["configuration"]["default_adapter"] == "linear"
            assert result["configuration"]["settings"]["timeout"] == 30

    def test_detect_agents_directory(self):
        """Test detects agents/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir()

            agents_dir = config_dir / "agents"
            agents_dir.mkdir()

            result = load_project_config(tmpdir)

            assert result is not None
            assert result["has_agents"] is True
            assert result["has_skills"] is False
            assert result["has_memories"] is False

    def test_detect_skills_directory(self):
        """Test detects skills/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir()

            skills_dir = config_dir / "skills"
            skills_dir.mkdir()

            result = load_project_config(tmpdir)

            assert result is not None
            assert result["has_agents"] is False
            assert result["has_skills"] is True
            assert result["has_memories"] is False

    def test_detect_memories_directory(self):
        """Test detects memories/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir()

            memories_dir = config_dir / "memories"
            memories_dir.mkdir()

            result = load_project_config(tmpdir)

            assert result is not None
            assert result["has_agents"] is False
            assert result["has_skills"] is False
            assert result["has_memories"] is True

    def test_detect_all_directories(self):
        """Test detects all subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir()

            # Create all subdirectories
            (config_dir / "agents").mkdir()
            (config_dir / "skills").mkdir()
            (config_dir / "memories").mkdir()

            result = load_project_config(tmpdir)

            assert result is not None
            assert result["has_agents"] is True
            assert result["has_skills"] is True
            assert result["has_memories"] is True

    def test_full_config_with_all_features(self):
        """Test loads complete config with all features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir()

            # Create configuration.yaml
            config_data = {
                "default_adapter": "linear",
                "api_keys": {"linear": "key-123"},
            }

            config_file = config_dir / "configuration.yaml"
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            # Create all directories
            (config_dir / "agents").mkdir()
            (config_dir / "skills").mkdir()
            (config_dir / "memories").mkdir()

            result = load_project_config(tmpdir)

            assert result is not None
            assert result["configuration"] == config_data
            assert result["has_agents"] is True
            assert result["has_skills"] is True
            assert result["has_memories"] is True

    def test_malformed_yaml_raises_error(self):
        """Test raises YAMLError for malformed configuration.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir()

            # Create malformed YAML
            config_file = config_dir / "configuration.yaml"
            with open(config_file, "w", encoding="utf-8") as f:
                f.write("invalid: yaml: content:\n  - bad indent\n bad")

            with pytest.raises(yaml.YAMLError):
                load_project_config(tmpdir)

    def test_empty_yaml_file(self):
        """Test handles empty configuration.yaml file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir()

            # Create empty YAML file
            config_file = config_dir / "configuration.yaml"
            config_file.touch()

            result = load_project_config(tmpdir)

            assert result is not None
            assert result["configuration"] == {}

    def test_file_as_directory(self):
        """Test handles file when directory expected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir()

            # Create file instead of agents directory
            agents_file = config_dir / "agents"
            agents_file.touch()

            result = load_project_config(tmpdir)

            assert result is not None
            # File should not be detected as directory
            assert result["has_agents"] is False

    def test_unicode_in_config(self):
        """Test handles unicode in configuration.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir()

            # Create config with unicode
            config_data = {
                "project_name": "プロジェクト",
                "description": "Test with émojis 🎉",
            }

            config_file = config_dir / "configuration.yaml"
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, allow_unicode=True)

            result = load_project_config(tmpdir)

            assert result is not None
            assert result["configuration"]["project_name"] == "プロジェクト"
            assert "🎉" in result["configuration"]["description"]
