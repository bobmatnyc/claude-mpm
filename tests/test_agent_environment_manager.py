#!/usr/bin/env python3
"""
Tests for AgentEnvironmentManager Service
=========================================

Comprehensive test suite for the extracted AgentEnvironmentManager service.
Tests all environment configuration and management functionality.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_environment_manager import (
    AgentEnvironmentManager,
)


class TestAgentEnvironmentManager:
    """Test suite for AgentEnvironmentManager."""

    @pytest.fixture
    def env_manager(self):
        """Create AgentEnvironmentManager instance."""
        return AgentEnvironmentManager()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tmp_path as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def clean_environment(self):
        """Clean up environment variables before and after tests."""
        # Store original environment
        original_env = os.environ.copy()

        # Remove Claude-related variables
        claude_vars = [key for key in os.environ if key.startswith("CLAUDE_")]
        for var in claude_vars:
            if var in os.environ:
                del os.environ[var]

        yield

        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

    def test_initialization(self):
        """Test AgentEnvironmentManager initialization."""
        assert hasattr(self, "logger")
        assert self.logger is not None

    def test_set_claude_environment_default_dir(
        self, env_manager, temp_dir, clean_environment
    ):
        """Test setting Claude environment with default directory."""
        with patch("pathlib.Path.cwd", return_value=temp_dir):
            env_vars = env_manager.set_claude_environment()

        assert "CLAUDE_CONFIG_DIR" in env_vars
        assert "CLAUDE_MAX_PARALLEL_SUBAGENTS" in env_vars
        assert "CLAUDE_TIMEOUT" in env_vars

        # Check that environment variables were actually set
        assert os.environ.get("CLAUDE_CONFIG_DIR") == str(temp_dir / ".claude")
        assert os.environ.get("CLAUDE_MAX_PARALLEL_SUBAGENTS") == "3"
        assert os.environ.get("CLAUDE_TIMEOUT") == "300"

        # Check that config directory was created
        assert (temp_dir / ".claude").exists()

    def test_set_claude_environment_custom_dir(
        self, env_manager, temp_dir, clean_environment
    ):
        """Test setting Claude environment with custom directory."""
        custom_config = temp_dir / "custom_claude"

        env_vars = env_manager.set_claude_environment(custom_config)

        assert env_vars["CLAUDE_CONFIG_DIR"] == str(custom_config.absolute())
        assert os.environ.get("CLAUDE_CONFIG_DIR") == str(custom_config.absolute())

        # Check that custom directory was created
        assert custom_config.exists()

    def test_get_current_environment_empty(self, clean_environment):
        """Test getting current environment when no Claude variables are set."""
        current_env = self.get_current_environment()
        assert isinstance(current_env, dict)
        assert len(current_env) == 0

    def test_get_current_environment_with_variables(
        self, env_manager, clean_environment
    ):
        """Test getting current environment with Claude variables set."""
        # Set some test environment variables
        os.environ["CLAUDE_CONFIG_DIR"] = "/test/path"
        os.environ["CLAUDE_TIMEOUT"] = "600"
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        os.environ["OTHER_VAR"] = "should-not-appear"

        current_env = env_manager.get_current_environment()

        assert "CLAUDE_CONFIG_DIR" in current_env
        assert "CLAUDE_TIMEOUT" in current_env
        assert "ANTHROPIC_API_KEY" in current_env
        assert "OTHER_VAR" not in current_env

        assert current_env["CLAUDE_CONFIG_DIR"] == "/test/path"
        assert current_env["CLAUDE_TIMEOUT"] == "600"
        assert current_env["ANTHROPIC_API_KEY"] == "test-key"

    def test_validate_environment_missing_config_dir(
        self, env_manager, temp_dir, clean_environment
    ):
        """Test environment validation when config directory is missing."""
        non_existent_dir = temp_dir / "non_existent"

        validation = env_manager.validate_environment(non_existent_dir)

        assert not validation["valid"]
        assert not validation["config_dir_exists"]
        assert not validation["agents_dir_exists"]
        assert len(validation["errors"]) > 0
        assert any("does not exist" in error for error in validation["errors"])

    def test_validate_environment_existing_config(
        self, env_manager, temp_dir, clean_environment
    ):
        """Test environment validation with existing config directory."""
        config_dir = temp_dir / ".claude"
        agents_dir = config_dir / "agents"

        # Create directories
        config_dir.mkdir()
        agents_dir.mkdir()

        # Set environment variable
        os.environ["CLAUDE_CONFIG_DIR"] = str(config_dir)

        validation = env_manager.validate_environment(config_dir)

        assert validation["valid"]
        assert validation["config_dir_exists"]
        assert validation["agents_dir_exists"]
        assert len(validation["errors"]) == 0

    def test_validate_environment_warnings(
        self, env_manager, temp_dir, clean_environment
    ):
        """Test environment validation warnings."""
        config_dir = temp_dir / ".claude"
        config_dir.mkdir()
        # Don't create agents directory to trigger warning

        validation = env_manager.validate_environment(config_dir)

        assert len(validation["warnings"]) > 0
        assert any(
            "Agents directory does not exist" in warning
            for warning in validation["warnings"]
        )

    def test_validate_environment_recommendations(
        self, env_manager, temp_dir, clean_environment
    ):
        """Test environment validation recommendations."""
        config_dir = temp_dir / ".claude"
        config_dir.mkdir()

        validation = env_manager.validate_environment(config_dir)

        assert len(validation["recommendations"]) > 0
        # Should recommend setting missing environment variables
        recommendations_text = " ".join(validation["recommendations"])
        assert "CLAUDE_MAX_PARALLEL_SUBAGENTS" in recommendations_text
        assert "CLAUDE_TIMEOUT" in recommendations_text

    def test_setup_development_environment(
        self, env_manager, temp_dir, clean_environment
    ):
        """Test setting up complete development environment."""
        config_dir = temp_dir / "dev_claude"

        setup_results = env_manager.setup_development_environment(config_dir)

        assert setup_results["success"]
        assert len(setup_results["created_directories"]) > 0
        assert len(setup_results["set_environment_variables"]) > 0
        assert len(setup_results["errors"]) == 0

        # Check that directories were created
        assert config_dir.exists()
        assert (config_dir / "agents").exists()
        assert (config_dir / "logs").exists()
        assert (config_dir / "cache").exists()

        # Check that .gitignore was created
        assert (config_dir / ".gitignore").exists()

        # Check environment variables
        assert "CLAUDE_CONFIG_DIR" in setup_results["set_environment_variables"]

    def test_setup_development_environment_error_handling(
        self, env_manager, clean_environment
    ):
        """Test development environment setup error handling."""
        # Try to create in a location that should fail (root directory on most systems)
        invalid_path = Path("/root/invalid_claude_config")

        setup_results = env_manager.setup_development_environment(invalid_path)

        # Should handle the error gracefully
        assert not setup_results["success"]
        assert len(setup_results["errors"]) > 0

    def test_get_environment_info(self, clean_environment):
        """Test getting comprehensive environment information."""
        # Set some test environment variables
        os.environ["CLAUDE_CONFIG_DIR"] = "/test/config"
        os.environ["PYTHONPATH"] = "/test/python"

        info = self.get_environment_info()

        assert "claude_environment_variables" in info
        assert "python_path" in info
        assert "current_working_directory" in info
        assert "user_home_directory" in info
        assert "claude_config_locations" in info

        assert (
            info["claude_environment_variables"]["CLAUDE_CONFIG_DIR"] == "/test/config"
        )
        assert info["python_path"] == "/test/python"

    def test_cleanup_environment(self, clean_environment):
        """Test cleaning up environment variables."""
        # Set some Claude environment variables
        os.environ["CLAUDE_CONFIG_DIR"] = "/test/config"
        os.environ["CLAUDE_TIMEOUT"] = "300"
        os.environ["CLAUDE_MAX_PARALLEL_SUBAGENTS"] = "3"
        os.environ["OTHER_VAR"] = "should-remain"

        cleanup_results = self.cleanup_environment()

        assert len(cleanup_results["removed_variables"]) == 3
        assert len(cleanup_results["errors"]) == 0

        # Check that Claude variables were removed
        assert "CLAUDE_CONFIG_DIR" not in os.environ
        assert "CLAUDE_TIMEOUT" not in os.environ
        assert "CLAUDE_MAX_PARALLEL_SUBAGENTS" not in os.environ

        # Check that other variables remain
        assert os.environ.get("OTHER_VAR") == "should-remain"

    def test_find_claude_config_locations(self, temp_dir):
        """Test finding Claude configuration locations."""
        # Create some test config directories
        test_configs = [
            temp_dir / ".claude",
            temp_dir / "home" / ".claude",
            temp_dir / "config" / "claude",
        ]

        for config_dir in test_configs:
            config_dir.mkdir(parents=True, exist_ok=True)

        with patch("pathlib.Path.cwd", return_value=temp_dir), patch(
            "pathlib.Path.home", return_value=temp_dir / "home"
        ):
            locations = self._find_claude_config_locations()

        # Should find the existing directories
        assert len(locations) >= 2  # At least cwd/.claude and home/.claude
        assert str(temp_dir / ".claude") in locations
        assert str(temp_dir / "home" / ".claude") in locations

    def test_environment_variable_precedence(
        self, env_manager, temp_dir, clean_environment
    ):
        """Test that environment variables are set with correct precedence."""
        config_dir = temp_dir / "test_config"

        # Set environment first
        env_vars = env_manager.set_claude_environment(config_dir)

        # Verify the values are as expected
        assert env_vars["CLAUDE_MAX_PARALLEL_SUBAGENTS"] == "3"
        assert env_vars["CLAUDE_TIMEOUT"] == "300"

        # Verify they're actually in the environment
        assert os.environ["CLAUDE_MAX_PARALLEL_SUBAGENTS"] == "3"
        assert os.environ["CLAUDE_TIMEOUT"] == "300"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
