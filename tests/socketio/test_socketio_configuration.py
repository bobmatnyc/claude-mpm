#!/usr/bin/env python3
"""
Comprehensive unit tests for SocketIO Configuration System.

Tests critical configuration management including:
- Configuration loading from different sources
- Environment variable overrides
- Ping/pong configuration consistency
- Default fallback values
- Configuration validation

WHY: These tests address critical gaps in configuration system test coverage
identified during analysis. They ensure proper configuration management across
different deployment environments and prevent mismatched client/server settings.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.config.socketio_config import (CONNECTION_CONFIG,
                                               ConfigManager, SocketIOConfig,
                                               get_config, get_discovery_hosts,
                                               get_server_ports)


class TestSocketIOConfiguration:
    """Test SocketIO configuration system."""

    def setup_method(self):
        """Set up test fixtures."""
        # Save original environment
        self.original_env = dict(os.environ)

        # Clear any socketio-related environment variables for clean tests
        socketio_env_vars = [
            key for key in os.environ if key.startswith("CLAUDE_MPM_SOCKETIO")
        ]
        for var in socketio_env_vars:
            if var in os.environ:
                del os.environ[var]

    def teardown_method(self):
        """Clean up after each test."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_connection_config_consistency(self):
        """Test that CONNECTION_CONFIG has consistent ping/pong settings."""
        # Critical: ping_interval and ping_timeout must be reasonable
        assert CONNECTION_CONFIG["ping_interval"] > 0
        assert CONNECTION_CONFIG["ping_timeout"] > 0

        # ping_timeout should be less than ping_interval for stability
        assert CONNECTION_CONFIG["ping_timeout"] < CONNECTION_CONFIG["ping_interval"]

        # JavaScript and Python versions should be consistent (accounting for ms/s difference)
        assert (
            CONNECTION_CONFIG["ping_interval_ms"]
            == CONNECTION_CONFIG["ping_interval"] * 1000
        )
        assert (
            CONNECTION_CONFIG["ping_timeout_ms"]
            == CONNECTION_CONFIG["ping_timeout"] * 1000
        )

        # Stale timeout should be longer than ping interval to allow retries
        assert (
            CONNECTION_CONFIG["stale_timeout"] > CONNECTION_CONFIG["ping_interval"] * 2
        )

    def test_socketio_config_default_initialization(self):
        """Test SocketIOConfig initialization with defaults."""
        config = SocketIOConfig()

        # Check default values
        assert config.host == "localhost"
        assert config.port == 8765  # NetworkConfig.DEFAULT_DASHBOARD_PORT
        assert config.server_id is None
        assert config.cors_allowed_origins == "*"

        # Check connection settings use centralized config
        assert config.ping_timeout == CONNECTION_CONFIG["ping_timeout"]
        assert config.ping_interval == CONNECTION_CONFIG["ping_interval"]
        assert config.max_http_buffer_size == int(
            CONNECTION_CONFIG["max_http_buffer_size"]
        )

        # Check deployment settings
        assert config.deployment_mode == "auto"
        assert config.auto_start is True
        assert config.persistent is True

    def test_socketio_config_from_env_basic(self):
        """Test configuration loading from environment variables."""
        # Set environment variables
        os.environ["CLAUDE_MPM_SOCKETIO_HOST"] = "192.168.1.100"
        os.environ["CLAUDE_MPM_SOCKETIO_PORT"] = "9999"
        os.environ["CLAUDE_MPM_SOCKETIO_SERVER_ID"] = "test-server-1"
        os.environ["CLAUDE_MPM_SOCKETIO_CORS"] = "https://example.com"

        config = SocketIOConfig.from_env()

        assert config.host == "192.168.1.100"
        assert config.port == 9999
        assert config.server_id == "test-server-1"
        assert config.cors_allowed_origins == "https://example.com"

    def test_socketio_config_from_env_timeout_settings(self):
        """Test timeout configuration from environment."""
        os.environ["CLAUDE_MPM_SOCKETIO_PING_TIMEOUT"] = "30"
        os.environ["CLAUDE_MPM_SOCKETIO_PING_INTERVAL"] = "15"

        config = SocketIOConfig.from_env()

        assert config.ping_timeout == 30
        assert config.ping_interval == 15

    def test_socketio_config_from_env_boolean_flags(self):
        """Test boolean flag parsing from environment."""
        # Test various boolean string representations
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("1", False),  # Only "true" should be True
            ("0", False),
            ("", False),
        ]

        for env_value, expected in test_cases:
            os.environ.clear()
            os.environ.update(self.original_env)

            os.environ["CLAUDE_MPM_SOCKETIO_AUTO_START"] = env_value
            os.environ["CLAUDE_MPM_SOCKETIO_PERSISTENT"] = env_value

            config = SocketIOConfig.from_env()

            assert (
                config.auto_start == expected
            ), f"auto_start: '{env_value}' should be {expected}"
            assert (
                config.persistent == expected
            ), f"persistent: '{env_value}' should be {expected}"

    def test_socketio_config_for_development(self):
        """Test development-optimized configuration."""
        config = SocketIOConfig.for_development()

        assert config.host == "localhost"
        assert config.port == 8765
        assert config.deployment_mode == "auto"
        assert config.log_level == "DEBUG"
        assert config.ping_timeout == 30
        assert config.ping_interval == 10
        assert config.max_history_size == 5000

    def test_socketio_config_for_production(self):
        """Test production-optimized configuration."""
        config = SocketIOConfig.for_production()

        assert config.host == "0.0.0.0"
        assert config.port == 8765
        assert config.cors_allowed_origins == "https://your-domain.com"
        assert config.deployment_mode == "standalone"
        assert config.persistent is True
        assert config.log_level == "INFO"
        assert config.log_to_file is True
        assert config.log_file_path == "/var/log/claude-mpm-socketio.log"
        assert config.ping_timeout == 120
        assert config.ping_interval == 30
        assert config.max_history_size == 20000

    def test_socketio_config_for_docker(self):
        """Test Docker-optimized configuration."""
        config = SocketIOConfig.for_docker()

        assert config.host == "0.0.0.0"
        assert config.port == 8765
        assert config.deployment_mode == "standalone"
        assert config.persistent is True
        assert config.log_level == "INFO"
        assert config.ping_timeout == 90
        assert config.ping_interval == 25
        assert config.max_history_size == 15000

    def test_socketio_config_to_dict(self):
        """Test configuration serialization to dictionary."""
        config = SocketIOConfig(
            host="test-host", port=1234, server_id="test-server", log_level="DEBUG"
        )

        config_dict = config.to_dict()

        # Check all required fields are present
        required_fields = [
            "host",
            "port",
            "server_id",
            "cors_allowed_origins",
            "ping_timeout",
            "ping_interval",
            "max_http_buffer_size",
            "min_client_version",
            "max_history_size",
            "deployment_mode",
            "auto_start",
            "persistent",
            "log_level",
            "log_to_file",
            "log_file_path",
            "health_check_interval",
            "max_connection_attempts",
            "reconnection_delay",
        ]

        for field in required_fields:
            assert field in config_dict

        # Check specific values
        assert config_dict["host"] == "test-host"
        assert config_dict["port"] == 1234
        assert config_dict["server_id"] == "test-server"
        assert config_dict["log_level"] == "DEBUG"

    def test_config_manager_initialization(self):
        """Test ConfigManager initialization."""
        manager = ConfigManager()

        assert manager.config_file_name == "socketio_config.json"
        assert len(manager.config_search_paths) >= 3

        # Check search paths include expected locations
        paths = [str(p) for p in manager.config_search_paths]
        assert any("socketio_config.json" in path for path in paths)

    def test_config_manager_detect_environment_docker(self):
        """Test environment detection for Docker."""
        manager = ConfigManager()

        # Test Docker container detection via file
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True  # /.dockerenv exists
            assert manager.detect_environment() == "docker"

        # Test Docker container detection via environment
        with patch.dict(os.environ, {"DOCKER_CONTAINER": "1"}):
            assert manager.detect_environment() == "docker"

    def test_config_manager_detect_environment_production(self):
        """Test environment detection for production."""
        manager = ConfigManager()

        # Test via ENVIRONMENT variable
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            assert manager.detect_environment() == "production"

        # Test via NODE_ENV variable
        with patch.dict(os.environ, {"NODE_ENV": "production"}):
            assert manager.detect_environment() == "production"

    def test_config_manager_detect_environment_installed(self):
        """Test environment detection for installed package."""
        manager = ConfigManager()

        # Mock importing claude_mpm to simulate installed package
        mock_claude_mpm = MagicMock()
        mock_claude_mpm.__file__ = (
            "/usr/local/lib/python3.9/site-packages/claude_mpm/__init__.py"
        )

        with patch("builtins.__import__") as mock_import:

            def side_effect(name, *args, **kwargs):
                if name == "claude_mpm":
                    return mock_claude_mpm
                # For any other import, call the real import
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = side_effect
            assert manager.detect_environment() == "installed"

    def test_config_manager_detect_environment_development(self):
        """Test environment detection defaults to development."""
        manager = ConfigManager()

        # With no special indicators, should default to development
        with patch("os.path.exists", return_value=False), patch.dict(
            os.environ, {}, clear=True
        ):
            assert manager.detect_environment() == "development"

    def test_config_manager_get_config_with_environment(self):
        """Test getting configuration for specific environment."""
        manager = ConfigManager()

        # Test development config
        dev_config = manager.get_config("development")
        assert isinstance(dev_config, SocketIOConfig)
        assert dev_config.log_level == "DEBUG"

        # Test production config
        prod_config = manager.get_config("production")
        assert isinstance(prod_config, SocketIOConfig)
        assert prod_config.host == "0.0.0.0"
        assert prod_config.log_level == "INFO"

        # Test docker config
        docker_config = manager.get_config("docker")
        assert isinstance(docker_config, SocketIOConfig)
        assert docker_config.host == "0.0.0.0"
        assert docker_config.deployment_mode == "standalone"

    def test_config_manager_env_override(self):
        """Test that environment variables override config defaults."""
        manager = ConfigManager()

        # Set environment override
        os.environ["CLAUDE_MPM_SOCKETIO_HOST"] = "custom-host"
        os.environ["CLAUDE_MPM_SOCKETIO_PORT"] = "7777"

        config = manager.get_config("development")

        # Environment should override development defaults
        assert config.host == "custom-host"
        assert config.port == 7777
        # But other development settings should remain
        assert config.log_level == "DEBUG"

    def test_config_manager_config_file_loading(self):
        """Test loading configuration from file."""
        manager = ConfigManager()

        # Create temporary config file
        config_data = {
            "host": "file-host",
            "port": 8888,
            "log_level": "WARNING",
            "custom_field": "custom_value",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            # Mock config search paths to include our temp file
            manager.config_search_paths = [Path(temp_path)]

            config = manager.get_config("development")

            # File values should override defaults
            assert config.host == "file-host"
            assert config.port == 8888
            assert config.log_level == "WARNING"

        finally:
            os.unlink(temp_path)

    def test_config_manager_config_file_malformed(self):
        """Test handling of malformed configuration file."""
        manager = ConfigManager()

        # Create malformed JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            manager.config_search_paths = [Path(temp_path)]

            # Should handle malformed file gracefully
            config = manager.get_config("development")
            assert isinstance(config, SocketIOConfig)
            # Should fall back to development defaults
            assert config.log_level == "DEBUG"

        finally:
            os.unlink(temp_path)

    def test_config_manager_save_config(self):
        """Test saving configuration to file."""
        manager = ConfigManager()

        config = SocketIOConfig(host="save-test", port=9999, log_level="ERROR")

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"

            success = manager.save_config(config, str(config_path))
            assert success
            assert config_path.exists()

            # Verify saved content
            with config_path.open() as f:
                saved_data = json.load(f)

            assert saved_data["host"] == "save-test"
            assert saved_data["port"] == 9999
            assert saved_data["log_level"] == "ERROR"

    def test_global_get_config_function(self):
        """Test the global get_config function."""
        # Clear environment first
        os.environ.clear()
        os.environ.update(self.original_env)

        config = get_config()
        assert isinstance(config, SocketIOConfig)

        # Should use detected environment
        config_env = get_config("production")
        assert isinstance(config_env, SocketIOConfig)
        assert config_env.host == "0.0.0.0"

    def test_get_server_ports_function(self):
        """Test server port discovery function."""
        config = SocketIOConfig(port=8765)

        ports = get_server_ports(config)

        assert isinstance(ports, list)
        assert len(ports) == 5
        assert 8765 in ports
        assert 8766 in ports
        assert 8767 in ports
        assert 8768 in ports
        assert 8769 in ports

    def test_get_discovery_hosts_function(self):
        """Test server host discovery function."""
        # Test with specific host
        config = SocketIOConfig(host="example.com")
        hosts = get_discovery_hosts(config)

        assert isinstance(hosts, list)
        assert "example.com" in hosts
        assert "localhost" in hosts
        assert "127.0.0.1" in hosts

        # Test with bind-all host
        config = SocketIOConfig(host="0.0.0.0")
        hosts = get_discovery_hosts(config)

        assert "localhost" in hosts
        assert "127.0.0.1" in hosts

    def test_connection_config_required_fields(self):
        """Test that CONNECTION_CONFIG has all required fields."""
        required_fields = [
            "ping_interval_ms",
            "ping_interval",
            "ping_timeout_ms",
            "ping_timeout",
            "stale_timeout",
            "health_check_interval",
            "event_ttl",
            "connection_timeout",
            "reconnection_attempts",
            "reconnection_delay",
            "reconnection_delay_max",
            "enable_extra_heartbeat",
            "enable_health_monitoring",
            "max_events_buffer",
            "max_http_buffer_size",
        ]

        for field in required_fields:
            assert (
                field in CONNECTION_CONFIG
            ), f"CONNECTION_CONFIG missing required field: {field}"

    def test_connection_config_reasonable_values(self):
        """Test that CONNECTION_CONFIG values are within reasonable ranges."""
        # Ping intervals should be reasonable (5-60 seconds)
        assert 5 <= CONNECTION_CONFIG["ping_interval"] <= 60
        assert 5 <= CONNECTION_CONFIG["ping_timeout"] <= 60

        # Reconnection attempts should be reasonable (1-10)
        assert 1 <= CONNECTION_CONFIG["reconnection_attempts"] <= 10

        # Delays should be reasonable (0.1-30 seconds converted to ms)
        assert 100 <= CONNECTION_CONFIG["reconnection_delay"] <= 30000
        assert (
            CONNECTION_CONFIG["reconnection_delay_max"]
            >= CONNECTION_CONFIG["reconnection_delay"]
        )

        # Buffer sizes should be positive
        assert CONNECTION_CONFIG["max_events_buffer"] > 0
        assert CONNECTION_CONFIG["max_http_buffer_size"] > 0

    def test_configuration_priority_order(self):
        """Test configuration priority: file > env > defaults."""
        manager = ConfigManager()

        # Create config file
        file_config = {"host": "file-host", "port": 1111}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(file_config, f)
            temp_path = f.name

        try:
            # Set environment variable
            os.environ["CLAUDE_MPM_SOCKETIO_HOST"] = "env-host"
            os.environ["CLAUDE_MPM_SOCKETIO_LOG_LEVEL"] = "WARNING"

            # Mock file search to find our temp file
            manager.config_search_paths = [Path(temp_path)]

            config = manager.get_config("development")

            # File should override environment and defaults
            assert config.host == "file-host"  # from file
            assert config.port == 1111  # from file
            assert config.log_level == "WARNING"  # from env (not in file)
            # Development default that's not overridden anywhere

        finally:
            os.unlink(temp_path)

    def test_config_validation_edge_cases(self):
        """Test configuration validation for edge cases."""
        # Test with extreme values
        config = SocketIOConfig(
            port=0,  # Invalid port
            ping_timeout=0,  # Invalid timeout
            ping_interval=-1,  # Invalid interval
            max_history_size=-100,  # Invalid size
        )

        # Configuration should be created but may not be functional
        # This tests that the configuration system doesn't crash
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["port"] == 0
        assert config_dict["ping_timeout"] == 0
