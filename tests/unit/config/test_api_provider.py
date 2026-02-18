"""Unit tests for API provider configuration."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from claude_mpm.config.api_provider import (
    AnthropicConfig,
    APIBackend,
    APIProviderConfig,
    BedrockConfig,
    apply_api_provider_config,
)


class TestAPIBackend:
    """Tests for APIBackend enum."""

    def test_backend_values(self):
        """Test enum values are correct."""
        assert APIBackend.BEDROCK.value == "bedrock"
        assert APIBackend.ANTHROPIC.value == "anthropic"

    def test_backend_from_string(self):
        """Test creating enum from string."""
        assert APIBackend("bedrock") == APIBackend.BEDROCK
        assert APIBackend("anthropic") == APIBackend.ANTHROPIC


class TestBedrockConfig:
    """Tests for BedrockConfig dataclass."""

    def test_default_values(self):
        """Test default values."""
        config = BedrockConfig()
        assert config.region == "us-east-1"
        assert "claude" in config.model.lower()

    def test_custom_values(self):
        """Test custom values."""
        config = BedrockConfig(region="us-west-2", model="custom-model")
        assert config.region == "us-west-2"
        assert config.model == "custom-model"


class TestAnthropicConfig:
    """Tests for AnthropicConfig dataclass."""

    def test_default_values(self):
        """Test default values."""
        config = AnthropicConfig()
        assert "claude" in config.model.lower()

    def test_custom_values(self):
        """Test custom values."""
        config = AnthropicConfig(model="claude-opus-9000")
        assert config.model == "claude-opus-9000"


class TestAPIProviderConfig:
    """Tests for APIProviderConfig dataclass."""

    def test_default_values(self):
        """Test default values."""
        config = APIProviderConfig()
        assert config.backend == APIBackend.ANTHROPIC
        assert isinstance(config.bedrock, BedrockConfig)
        assert isinstance(config.anthropic, AnthropicConfig)

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file uses defaults."""
        config = APIProviderConfig.load(Path("/nonexistent/path/config.yaml"))
        assert config.backend == APIBackend.ANTHROPIC

    def test_load_empty_file(self):
        """Test loading from empty file uses defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            config = APIProviderConfig.load(Path(f.name))
            assert config.backend == APIBackend.ANTHROPIC
            os.unlink(f.name)

    def test_load_with_api_provider_section(self):
        """Test loading with api_provider section."""
        yaml_content = {
            "api_provider": {
                "backend": "anthropic",
                "bedrock": {"region": "eu-west-1", "model": "bedrock-model"},
                "anthropic": {"model": "anthropic-model"},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            f.flush()
            config = APIProviderConfig.load(Path(f.name))
            assert config.backend == APIBackend.ANTHROPIC
            assert config.bedrock.region == "eu-west-1"
            assert config.bedrock.model == "bedrock-model"
            assert config.anthropic.model == "anthropic-model"
            os.unlink(f.name)

    def test_load_invalid_backend_uses_default(self):
        """Test loading with invalid backend uses default."""
        yaml_content = {"api_provider": {"backend": "invalid_backend"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            f.flush()
            config = APIProviderConfig.load(Path(f.name))
            # Should use default (bedrock) on invalid value
            assert config.backend == APIBackend.ANTHROPIC
            os.unlink(f.name)

    def test_apply_environment_bedrock(self):
        """Test applying environment for Bedrock backend."""
        # Clean up any existing env vars
        for var in ["CLAUDE_CODE_USE_BEDROCK", "ANTHROPIC_MODEL", "AWS_REGION"]:
            os.environ.pop(var, None)

        config = APIProviderConfig(backend=APIBackend.BEDROCK)
        changes = config.apply_environment()

        assert os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1"
        assert "ANTHROPIC_MODEL" in os.environ
        assert "CLAUDE_CODE_USE_BEDROCK" in changes
        assert "ANTHROPIC_MODEL" in changes

        # Cleanup
        for var in ["CLAUDE_CODE_USE_BEDROCK", "ANTHROPIC_MODEL", "AWS_REGION"]:
            os.environ.pop(var, None)

    def test_apply_environment_anthropic(self):
        """Test applying environment for Anthropic backend."""
        # Set bedrock var to test it gets removed
        os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"

        config = APIProviderConfig(backend=APIBackend.ANTHROPIC)
        changes = config.apply_environment()

        assert "CLAUDE_CODE_USE_BEDROCK" not in os.environ
        assert "ANTHROPIC_MODEL" in os.environ
        assert changes.get("CLAUDE_CODE_USE_BEDROCK") == "(unset)"

        # Cleanup
        os.environ.pop("ANTHROPIC_MODEL", None)

    def test_save_creates_directory(self):
        """Test save creates directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "config.yaml"
            config = APIProviderConfig(backend=APIBackend.ANTHROPIC)
            config.save(config_path)

            assert config_path.exists()
            with open(config_path) as f:
                saved = yaml.safe_load(f)
            assert saved["api_provider"]["backend"] == "anthropic"

    def test_save_preserves_other_sections(self):
        """Test save preserves other config sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create initial config with other sections
            initial = {"other_section": {"key": "value"}, "another": 123}
            with open(config_path, "w") as f:
                yaml.dump(initial, f)

            # Save API provider config
            config = APIProviderConfig(backend=APIBackend.BEDROCK)
            config.save(config_path)

            # Verify other sections preserved
            with open(config_path) as f:
                saved = yaml.safe_load(f)
            assert saved["other_section"]["key"] == "value"
            assert saved["another"] == 123
            assert saved["api_provider"]["backend"] == "bedrock"

    def test_to_dict(self):
        """Test to_dict method."""
        config = APIProviderConfig(
            backend=APIBackend.ANTHROPIC,
            bedrock=BedrockConfig(region="us-west-2", model="bedrock-m"),
            anthropic=AnthropicConfig(model="anthropic-m"),
        )
        d = config.to_dict()

        assert d["backend"] == "anthropic"
        assert d["bedrock"]["region"] == "us-west-2"
        assert d["bedrock"]["model"] == "bedrock-m"
        assert d["anthropic"]["model"] == "anthropic-m"


class TestApplyAPIProviderConfig:
    """Tests for apply_api_provider_config convenience function."""

    def test_apply_api_provider_config(self):
        """Test convenience function applies config."""
        # Clean env
        os.environ.pop("CLAUDE_CODE_USE_BEDROCK", None)
        os.environ.pop("ANTHROPIC_MODEL", None)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"api_provider": {"backend": "bedrock"}}, f)
            f.flush()
            changes = apply_api_provider_config(Path(f.name))
            assert "CLAUDE_CODE_USE_BEDROCK" in changes
            os.unlink(f.name)

        # Cleanup
        os.environ.pop("CLAUDE_CODE_USE_BEDROCK", None)
        os.environ.pop("ANTHROPIC_MODEL", None)
