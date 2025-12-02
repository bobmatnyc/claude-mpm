"""Tests for skill sources configuration management.

Test Coverage:
- SkillSource validation and initialization
- SkillSourceConfiguration load/save operations
- Configuration file management (create, update, delete)
- Priority validation and conflict detection
- Error handling for invalid configurations
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.claude_mpm.config.skill_sources import SkillSource, SkillSourceConfiguration


class TestSkillSource:
    """Tests for SkillSource dataclass."""

    def test_skill_source_creation(self):
        """Test creating a valid skill source."""
        source = SkillSource(
            id="test",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=True,
        )

        assert source.id == "test"
        assert source.type == "git"
        assert source.url == "https://github.com/owner/repo"
        assert source.branch == "main"
        assert source.priority == 100
        assert source.enabled is True

    def test_skill_source_defaults(self):
        """Test default values for optional fields."""
        source = SkillSource(id="test", type="git", url="https://github.com/owner/repo")

        assert source.branch == "main"
        assert source.priority == 100
        assert source.enabled is True

    def test_skill_source_validation_empty_id(self):
        """Test validation fails for empty ID."""
        with pytest.raises(ValueError, match="ID cannot be empty"):
            SkillSource(id="", type="git", url="https://github.com/owner/repo")

    def test_skill_source_validation_invalid_id_characters(self):
        """Test validation fails for invalid ID characters."""
        with pytest.raises(ValueError, match="must be alphanumeric"):
            SkillSource(id="test@id!", type="git", url="https://github.com/owner/repo")

    def test_skill_source_validation_invalid_type(self):
        """Test validation fails for unsupported type."""
        with pytest.raises(ValueError, match="Only 'git' type"):
            SkillSource(id="test", type="svn", url="https://github.com/owner/repo")

    def test_skill_source_validation_empty_url(self):
        """Test validation fails for empty URL."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            SkillSource(id="test", type="git", url="")

    def test_skill_source_validation_invalid_url_scheme(self):
        """Test validation fails for invalid URL scheme."""
        with pytest.raises(ValueError, match="must use http:// or https://"):
            SkillSource(id="test", type="git", url="ftp://github.com/owner/repo")

    def test_skill_source_validation_non_github_url(self):
        """Test validation fails for non-GitHub URL."""
        with pytest.raises(ValueError, match="must be a GitHub repository"):
            SkillSource(id="test", type="git", url="https://gitlab.com/owner/repo")

    def test_skill_source_validation_invalid_url_path(self):
        """Test validation fails for URL without owner/repo."""
        with pytest.raises(ValueError, match="must include owner/repo path"):
            SkillSource(id="test", type="git", url="https://github.com/")

    def test_skill_source_validation_empty_branch(self):
        """Test validation fails for empty branch name."""
        with pytest.raises(ValueError, match="Branch name cannot be empty"):
            SkillSource(
                id="test", type="git", url="https://github.com/owner/repo", branch=""
            )

    def test_skill_source_validation_negative_priority(self):
        """Test validation fails for negative priority."""
        with pytest.raises(ValueError, match="Priority must be non-negative"):
            SkillSource(
                id="test",
                type="git",
                url="https://github.com/owner/repo",
                priority=-1,
            )

    def test_skill_source_validation_high_priority_warning(self):
        """Test validation warns for unusually high priority."""
        with pytest.raises(ValueError, match="unusually high"):
            SkillSource(
                id="test",
                type="git",
                url="https://github.com/owner/repo",
                priority=1001,
            )

    def test_skill_source_validate_method(self):
        """Test validate() method returns error list."""
        source = SkillSource(id="test", type="git", url="https://github.com/owner/repo")
        errors = source.validate()
        assert errors == []

    def test_skill_source_repr(self):
        """Test string representation."""
        source = SkillSource(id="test", type="git", url="https://github.com/owner/repo")
        repr_str = repr(source)

        assert "SkillSource" in repr_str
        assert "test" in repr_str
        assert "priority=100" in repr_str


class TestSkillSourceConfiguration:
    """Tests for SkillSourceConfiguration class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_path = Path(f.name)
        yield config_path
        # Cleanup
        if config_path.exists():
            config_path.unlink()

    @pytest.fixture
    def config(self, temp_config_file):
        """Create a SkillSourceConfiguration instance for testing."""
        return SkillSourceConfiguration(config_path=temp_config_file)

    def test_initialization_default_path(self):
        """Test initialization with default config path."""
        config = SkillSourceConfiguration()
        expected_path = Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"
        assert config.config_path == expected_path

    def test_initialization_custom_path(self, temp_config_file):
        """Test initialization with custom config path."""
        config = SkillSourceConfiguration(config_path=temp_config_file)
        assert config.config_path == temp_config_file

    def test_from_file_classmethod(self, temp_config_file):
        """Test from_file() class method."""
        config = SkillSourceConfiguration.from_file(temp_config_file)
        assert config.config_path == temp_config_file

    def test_load_nonexistent_file_returns_default(self, config):
        """Test load() returns default sources when file doesn't exist."""
        sources = config.load()

        assert len(sources) == 2  # system + anthropic-official
        assert sources[0].id == "system"
        assert sources[0].url == "https://github.com/bobmatnyc/claude-mpm-skills"
        assert sources[0].priority == 0
        assert sources[1].id == "anthropic-official"
        assert sources[1].url == "https://github.com/anthropics/skills"
        assert sources[1].priority == 1

    def test_load_empty_file_returns_default(self, config):
        """Test load() returns default sources when file is empty."""
        # Create empty file
        config.config_path.write_text("", encoding="utf-8")

        sources = config.load()

        assert len(sources) == 2  # system + anthropic-official
        assert sources[0].id == "system"
        assert sources[1].id == "anthropic-official"

    def test_load_invalid_yaml_returns_default(self, config):
        """Test load() returns default sources when YAML is invalid."""
        # Create file with invalid YAML
        config.config_path.write_text("invalid: yaml: content:", encoding="utf-8")

        sources = config.load()

        assert len(sources) == 2  # system + anthropic-official
        assert sources[0].id == "system"
        assert sources[1].id == "anthropic-official"

    def test_load_valid_configuration(self, config):
        """Test load() parses valid configuration correctly."""
        # Create valid config file
        data = {
            "sources": [
                {
                    "id": "system",
                    "type": "git",
                    "url": "https://github.com/bobmatnyc/claude-mpm-skills",
                    "branch": "main",
                    "priority": 0,
                    "enabled": True,
                },
                {
                    "id": "custom",
                    "type": "git",
                    "url": "https://github.com/owner/custom-skills",
                    "branch": "develop",
                    "priority": 200,
                    "enabled": False,
                },
            ]
        }
        with open(config.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        sources = config.load()

        assert len(sources) == 2
        assert sources[0].id == "system"
        assert sources[0].priority == 0
        assert sources[1].id == "custom"
        assert sources[1].branch == "develop"
        assert sources[1].enabled is False

    def test_load_skips_invalid_sources(self, config):
        """Test load() skips sources with invalid data."""
        # Create config with one valid and one invalid source
        data = {
            "sources": [
                {
                    "id": "system",
                    "type": "git",
                    "url": "https://github.com/bobmatnyc/claude-mpm-skills",
                },
                {
                    "id": "invalid",
                    "type": "invalid_type",  # Invalid type
                    "url": "https://github.com/owner/repo",
                },
            ]
        }
        with open(config.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        sources = config.load()

        # Should only load valid source
        assert len(sources) == 1
        assert sources[0].id == "system"

    def test_save_creates_directory(self, temp_config_file):
        """Test save() creates parent directory if needed."""
        # Use path in non-existent directory
        config_path = temp_config_file.parent / "subdir" / "config.yaml"
        config = SkillSourceConfiguration(config_path=config_path)

        source = SkillSource(id="test", type="git", url="https://github.com/owner/repo")
        config.save([source])

        assert config_path.parent.exists()
        assert config_path.exists()

        # Cleanup
        config_path.unlink()
        config_path.parent.rmdir()

    def test_save_writes_valid_yaml(self, config):
        """Test save() writes valid YAML configuration."""
        sources = [
            SkillSource(
                id="system",
                type="git",
                url="https://github.com/bobmatnyc/claude-mpm-skills",
                priority=0,
            ),
            SkillSource(
                id="custom",
                type="git",
                url="https://github.com/owner/custom",
                priority=100,
            ),
        ]

        config.save(sources)

        # Verify file exists and is valid YAML
        assert config.config_path.exists()

        with open(config.config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "sources" in data
        assert len(data["sources"]) == 2
        assert data["sources"][0]["id"] == "system"
        assert data["sources"][1]["id"] == "custom"

    def test_save_empty_list_raises_error(self, config):
        """Test save() raises error for empty sources list."""
        with pytest.raises(ValueError, match="Cannot save empty sources list"):
            config.save([])

    def test_save_invalid_source_raises_error(self, config):
        """Test save() raises error for invalid source."""
        # Create source with invalid data (bypass __post_init__)
        source = SkillSource.__new__(SkillSource)
        source.id = ""  # Invalid empty ID
        source.type = "git"
        source.url = "https://github.com/owner/repo"
        source.branch = "main"
        source.priority = 100
        source.enabled = True

        with pytest.raises(ValueError, match="Cannot save invalid source"):
            config.save([source])

    def test_add_source(self, config):
        """Test add_source() adds new source."""
        source = SkillSource(
            id="custom", type="git", url="https://github.com/owner/custom"
        )

        config.add_source(source)

        sources = config.load()
        assert len(sources) == 3  # system + anthropic-official + custom
        assert any(s.id == "custom" for s in sources)

    def test_add_source_duplicate_id_raises_error(self, config):
        """Test add_source() raises error for duplicate ID."""
        source1 = SkillSource(
            id="custom", type="git", url="https://github.com/owner/repo1"
        )
        source2 = SkillSource(
            id="custom", type="git", url="https://github.com/owner/repo2"
        )

        config.add_source(source1)

        with pytest.raises(ValueError, match="already exists"):
            config.add_source(source2)

    def test_remove_source_existing(self, config):
        """Test remove_source() removes existing source."""
        source = SkillSource(
            id="custom", type="git", url="https://github.com/owner/custom"
        )
        config.add_source(source)

        result = config.remove_source("custom")

        assert result is True
        sources = config.load()
        assert not any(s.id == "custom" for s in sources)

    def test_remove_source_nonexistent(self, config):
        """Test remove_source() returns False for non-existent source."""
        result = config.remove_source("nonexistent")
        assert result is False

    def test_get_source_existing(self, config):
        """Test get_source() returns existing source."""
        source = SkillSource(
            id="custom", type="git", url="https://github.com/owner/custom"
        )
        config.add_source(source)

        retrieved = config.get_source("custom")

        assert retrieved is not None
        assert retrieved.id == "custom"
        assert retrieved.url == "https://github.com/owner/custom"

    def test_get_source_nonexistent(self, config):
        """Test get_source() returns None for non-existent source."""
        result = config.get_source("nonexistent")
        assert result is None

    def test_update_source(self, config):
        """Test update_source() updates existing source."""
        source = SkillSource(
            id="custom",
            type="git",
            url="https://github.com/owner/custom",
            priority=100,
        )
        config.add_source(source)

        config.update_source("custom", priority=200, enabled=False)

        updated = config.get_source("custom")
        assert updated.priority == 200
        assert updated.enabled is False

    def test_update_source_nonexistent_raises_error(self, config):
        """Test update_source() raises error for non-existent source."""
        with pytest.raises(ValueError, match="Source not found"):
            config.update_source("nonexistent", priority=200)

    def test_update_source_invalid_field_raises_error(self, config):
        """Test update_source() raises error for invalid field."""
        source = SkillSource(
            id="custom", type="git", url="https://github.com/owner/custom"
        )
        config.add_source(source)

        with pytest.raises(ValueError, match="Invalid update field"):
            config.update_source("custom", invalid_field="value")

    def test_update_source_invalid_value_raises_error(self, config):
        """Test update_source() raises error for invalid value."""
        source = SkillSource(
            id="custom", type="git", url="https://github.com/owner/custom"
        )
        config.add_source(source)

        with pytest.raises(ValueError, match="Invalid updates"):
            config.update_source("custom", priority=-1)

    def test_get_enabled_sources(self, config):
        """Test get_enabled_sources() returns only enabled sources."""
        sources = [
            SkillSource(
                id="enabled1",
                type="git",
                url="https://github.com/owner/repo1",
                enabled=True,
            ),
            SkillSource(
                id="disabled",
                type="git",
                url="https://github.com/owner/repo2",
                enabled=False,
            ),
            SkillSource(
                id="enabled2",
                type="git",
                url="https://github.com/owner/repo3",
                enabled=True,
            ),
        ]
        config.save(sources)

        enabled = config.get_enabled_sources()

        assert len(enabled) == 2
        assert all(s.enabled for s in enabled)

    def test_get_enabled_sources_sorted_by_priority(self, config):
        """Test get_enabled_sources() returns sources sorted by priority."""
        sources = [
            SkillSource(
                id="low",
                type="git",
                url="https://github.com/owner/repo1",
                priority=200,
            ),
            SkillSource(
                id="high",
                type="git",
                url="https://github.com/owner/repo2",
                priority=50,
            ),
            SkillSource(
                id="medium",
                type="git",
                url="https://github.com/owner/repo3",
                priority=100,
            ),
        ]
        config.save(sources)

        enabled = config.get_enabled_sources()

        assert len(enabled) == 3
        assert enabled[0].id == "high"  # Priority 50
        assert enabled[1].id == "medium"  # Priority 100
        assert enabled[2].id == "low"  # Priority 200

    def test_validate_priority_conflicts_no_conflicts(self, config):
        """Test validate_priority_conflicts() with no conflicts."""
        sources = [
            SkillSource(
                id="source1",
                type="git",
                url="https://github.com/owner/repo1",
                priority=100,
            ),
            SkillSource(
                id="source2",
                type="git",
                url="https://github.com/owner/repo2",
                priority=200,
            ),
        ]
        config.save(sources)

        warnings = config.validate_priority_conflicts()
        assert warnings == []

    def test_validate_priority_conflicts_with_conflicts(self, config):
        """Test validate_priority_conflicts() detects conflicts."""
        sources = [
            SkillSource(
                id="source1",
                type="git",
                url="https://github.com/owner/repo1",
                priority=100,
            ),
            SkillSource(
                id="source2",
                type="git",
                url="https://github.com/owner/repo2",
                priority=100,
            ),
            SkillSource(
                id="source3",
                type="git",
                url="https://github.com/owner/repo3",
                priority=200,
            ),
        ]
        config.save(sources)

        warnings = config.validate_priority_conflicts()

        assert len(warnings) == 1
        assert "Priority 100" in warnings[0]
        assert "source1" in warnings[0]
        assert "source2" in warnings[0]

    def test_validate_priority_conflicts_ignores_disabled(self, config):
        """Test validate_priority_conflicts() ignores disabled sources."""
        sources = [
            SkillSource(
                id="source1",
                type="git",
                url="https://github.com/owner/repo1",
                priority=100,
                enabled=True,
            ),
            SkillSource(
                id="source2",
                type="git",
                url="https://github.com/owner/repo2",
                priority=100,
                enabled=False,
            ),
        ]
        config.save(sources)

        warnings = config.validate_priority_conflicts()
        assert warnings == []

    def test_repr(self, config):
        """Test string representation."""
        source = SkillSource(id="test", type="git", url="https://github.com/owner/repo")
        config.add_source(source)

        repr_str = repr(config)

        assert "SkillSourceConfiguration" in repr_str
        assert "sources=3" in repr_str  # system + anthropic-official + test
        assert "enabled=3" in repr_str

    def test_default_sources_include_anthropic(self, config):
        """Test that default sources include official Anthropic repository."""
        sources = config._get_default_sources()

        # Should have exactly 2 sources: system and anthropic-official
        assert len(sources) == 2

        # Verify system source (priority 0)
        system_source = sources[0]
        assert system_source.id == "system"
        assert system_source.url == "https://github.com/bobmatnyc/claude-mpm-skills"
        assert system_source.priority == 0
        assert system_source.branch == "main"
        assert system_source.enabled is True

        # Verify Anthropic source (priority 1)
        anthropic_source = sources[1]
        assert anthropic_source.id == "anthropic-official"
        assert anthropic_source.url == "https://github.com/anthropics/skills"
        assert anthropic_source.priority == 1
        assert anthropic_source.branch == "main"
        assert anthropic_source.enabled is True

    def test_anthropic_source_lower_priority_than_system(self, config):
        """Test that Anthropic source has lower priority than system (higher number)."""
        sources = config._get_default_sources()

        system_source = next(s for s in sources if s.id == "system")
        anthropic_source = next(s for s in sources if s.id == "anthropic-official")

        # System should have priority 0 (highest)
        # Anthropic should have priority 1 (lower than system)
        assert system_source.priority < anthropic_source.priority
        assert system_source.priority == 0
        assert anthropic_source.priority == 1
