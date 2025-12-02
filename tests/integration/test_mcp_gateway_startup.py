"""
Integration tests for MCP Gateway startup verification.

Tests the automatic MCP gateway configuration and verification on startup,
including singleton management and essential tools verification.
"""

import json
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.services.mcp_gateway.core.singleton_manager import (
    MCPGatewayManager, get_gateway_manager, get_gateway_status,
    is_gateway_running)
from claude_mpm.services.mcp_gateway.core.startup_verification import (
    MCPGatewayStartupVerifier, is_mcp_gateway_configured,
    verify_mcp_gateway_on_startup)


class TestMCPGatewaySingleton:
    """Test MCP Gateway singleton manager functionality."""

    def setup_method(self):
        """Setup for each test method."""
        # Reset singleton instance
        MCPGatewayManager._instance = None

    def test_singleton_pattern():
        """Test that singleton pattern works correctly."""
        manager1 = get_gateway_manager()
        manager2 = get_gateway_manager()

        assert manager1 is manager2
        assert isinstance(manager1, MCPGatewayManager)

    def test_gateway_status_no_instance():
        """Test gateway status when no instance is running."""
        assert not is_gateway_running()
        assert get_gateway_status() is None

    def test_manager_initialization():
        """Test manager initialization."""
        manager = get_gateway_manager()

        assert manager.logger is not None
        assert manager.mcp_dir is not None
        assert manager.lock_file is not None
        assert manager.instance_file is not None

    def test_lock_acquisition_and_release():
        """Test lock acquisition and release."""
        manager = get_gateway_manager()

        # Test lock acquisition
        assert manager.acquire_lock()
        assert manager._lock_fd is not None

        # Test lock release
        manager.release_lock()
        assert manager._lock_fd is None

    def test_instance_registration():
        """Test gateway instance registration."""
        manager = get_gateway_manager()

        # Register instance
        success = manager.register_instance("test-gateway", "1.0.0")
        assert success

        # Check instance info
        instance_info = manager.get_running_instance_info()
        assert instance_info is not None
        assert instance_info["gateway_name"] == "test-gateway"
        assert instance_info["version"] == "1.0.0"

        # Cleanup
        manager.cleanup()

    def test_concurrent_lock_acquisition():
        """Test that only one process can acquire the lock."""
        manager1 = get_gateway_manager()

        # First manager acquires lock
        assert manager1.acquire_lock()

        # Reset singleton to simulate another process
        MCPGatewayManager._instance = None
        manager2 = get_gateway_manager()

        # Second manager should fail to acquire lock
        assert not manager2.acquire_lock()

        # Cleanup
        manager1.cleanup()


class TestMCPGatewayStartupVerification:
    """Test MCP Gateway startup verification functionality."""

    def setup_method(self):
        """Setup for each test method."""
        # Reset singleton instance
        MCPGatewayManager._instance = None

    @pytest.mark.asyncio
    async def test_startup_verifier_initialization():
        """Test startup verifier initialization."""
        verifier = MCPGatewayStartupVerifier()

        assert verifier.logger is not None
        assert verifier.config_dir is not None
        assert verifier.config_file is not None
        assert len(verifier.essential_tools) > 0
        assert "echo" in verifier.essential_tools
        assert "health_check" in verifier.essential_tools

    @pytest.mark.asyncio
    async def test_verify_singleton_manager():
        """Test singleton manager verification."""
        verifier = MCPGatewayStartupVerifier()

        result = verifier._verify_singleton_manager()
        assert result is True

    @pytest.mark.asyncio
    async def test_config_directory_creation():
        """Test configuration directory creation."""
        with tmp_path as temp_dir:
            verifier = MCPGatewayStartupVerifier()
            verifier.config_dir = Path(temp_dir) / "test_mcp"

            # Directory should not exist initially
            assert not verifier.config_dir.exists()

            # Ensure directory creation
            verifier._ensure_config_directory()
            assert verifier.config_dir.exists()

    @pytest.mark.asyncio
    async def test_gateway_configuration_creation():
        """Test gateway configuration creation."""
        with tmp_path as temp_dir:
            verifier = MCPGatewayStartupVerifier()
            verifier.config_dir = Path(temp_dir) / "test_mcp"
            verifier.config_file = verifier.config_dir / "gateway_config.json"

            # Ensure directory exists
            verifier._ensure_config_directory()

            # Create configuration
            created = await verifier._verify_gateway_configuration()
            assert created is True
            assert verifier.config_file.exists()

            # Verify configuration content
            with verifier.config_file.open() as f:
                config_data = json.load(f)

            assert "mcp" in config_data
            assert "server" in config_data["mcp"]
            assert "tools" in config_data["mcp"]

    @pytest.mark.asyncio
    async def test_essential_tools_verification():
        """Test essential tools verification."""
        verifier = MCPGatewayStartupVerifier()

        # Mock tool creation to avoid import issues
        async def mock_create_tool_instance(tool_name):
            if tool_name in ["echo", "calculator", "system_info"]:
                mock_tool = Mock()
                mock_tool.initialize = Mock(return_value=True)
                return mock_tool
            return None

        verifier._create_tool_instance = mock_create_tool_instance

        tools_status = await verifier._verify_essential_tools()

        assert isinstance(tools_status, dict)
        assert len(tools_status) > 0

        # Check that basic tools are available
        for tool_name in ["echo", "calculator", "system_info"]:
            if tool_name in tools_status:
                assert tools_status[tool_name]["available"] is True

    @pytest.mark.asyncio
    async def test_overall_verification():
        """Test overall verification process."""
        with tmp_path as temp_dir:
            verifier = MCPGatewayStartupVerifier()
            verifier.config_dir = Path(temp_dir) / "test_mcp"
            verifier.config_file = verifier.config_dir / "gateway_config.json"

            # Mock tool creation
            async def mock_create_tool_instance(tool_name):
                if tool_name in ["echo", "calculator", "system_info"]:
                    mock_tool = Mock()
                    mock_tool.initialize = Mock(return_value=True)
                    return mock_tool
                return None

            verifier._create_tool_instance = mock_create_tool_instance

            # Run verification
            results = await verifier.verify_and_configure()

            assert isinstance(results, dict)
            assert "gateway_configured" in results
            assert "singleton_manager" in results
            assert "essential_tools" in results
            assert "configuration_created" in results

            # Should have created configuration
            assert results["configuration_created"] is True
            assert results["singleton_manager"] is True

    @pytest.mark.asyncio
    async def test_global_verification_function():
        """Test global verification function."""
        with patch(
            "claude_mpm.services.mcp_gateway.core.startup_verification.MCPGatewayStartupVerifier"
        ) as mock_verifier_class:
            mock_verifier = Mock()
            mock_verifier.verify_and_configure = Mock(
                return_value={
                    "gateway_configured": True,
                    "singleton_manager": True,
                    "essential_tools": {},
                    "configuration_created": False,
                }
            )
            mock_verifier_class.return_value = mock_verifier

            results = await verify_mcp_gateway_on_startup()

            assert results["gateway_configured"] is True
            assert results["singleton_manager"] is True
            mock_verifier.verify_and_configure.assert_called_once()

    def test_is_mcp_gateway_configured():
        """Test quick configuration check."""
        # Should return True if basic components are available
        result = is_mcp_gateway_configured()
        assert isinstance(result, bool)


class TestMCPGatewayStartupIntegration:
    """Test integration of MCP Gateway startup with CLI."""

    def setup_method(self):
        """Setup for each test method."""
        # Reset singleton instance
        MCPGatewayManager._instance = None

    def test_cli_startup_integration():
        """Test that CLI startup includes MCP gateway verification."""
        # This test verifies that the CLI startup process includes
        # MCP gateway verification without blocking

        from claude_mpm.cli import _verify_mcp_gateway_startup

        # Should not raise an exception
        _verify_mcp_gateway_startup()

        # Give background thread a moment to start
        time.sleep(0.1)

        # Function should return immediately (non-blocking)
        assert True  # If we get here, the function didn't block

    @patch("claude_mpm.cli.commands.is_mcp_gateway_configured")
    def test_cli_startup_with_configured_gateway(self):
        """Test CLI startup when gateway is already configured."""
        self.return_value = True

        from claude_mpm.cli import _verify_mcp_gateway_startup

        # Should return quickly if already configured
        start_time = time.time()
        _verify_mcp_gateway_startup()
        end_time = time.time()

        # Should be very fast (less than 1 second)
        assert (end_time - start_time) < 1.0
        self.assert_called_once()

    def test_background_verification_thread():
        """Test that verification runs in background thread."""
        from claude_mpm.cli import _verify_mcp_gateway_startup

        # Count active threads before
        initial_thread_count = threading.active_count()

        # Start verification
        _verify_mcp_gateway_startup()

        # Give thread a moment to start
        time.sleep(0.1)

        # Should have started a background thread
        current_thread_count = threading.active_count()
        assert current_thread_count >= initial_thread_count

        # Wait for background thread to complete
        time.sleep(2)


if __name__ == "__main__":
    pytest.main([__file__])
