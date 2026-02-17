"""Tests for NgrokTunnel module.

Tests ngrok tunnel lifecycle management with all pyngrok calls mocked.
These tests verify the logic and configuration without actually connecting to ngrok.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Skip entire module if pyngrok is not available
pyngrok = pytest.importorskip("pyngrok")

from claude_mpm.mcp.ngrok_tunnel import NgrokTunnel, TunnelInfo


# Create mock exception classes for testing error handling
class MockPyngrokError(Exception):
    """Mock PyngrokError for testing."""


class MockPyngrokNgrokError(Exception):
    """Mock PyngrokNgrokError for testing."""


@pytest.fixture
def mock_pyngrok():
    """Fixture that provides mocked pyngrok modules for testing.

    This fixture patches the pyngrok module imports that happen inside
    the NgrokTunnel.start() and stop() methods.
    """
    # Create mock modules
    mock_ngrok_module = MagicMock()
    mock_conf_module = MagicMock()
    mock_exception_module = MagicMock()
    mock_exception_module.PyngrokError = MockPyngrokError
    mock_exception_module.PyngrokNgrokError = MockPyngrokNgrokError

    # Create the parent pyngrok module mock
    mock_pyngrok_parent = MagicMock()
    mock_pyngrok_parent.ngrok = mock_ngrok_module

    # Store original modules
    original_modules = {}
    modules_to_patch = [
        "pyngrok",
        "pyngrok.ngrok",
        "pyngrok.conf",
        "pyngrok.exception",
    ]
    for mod_name in modules_to_patch:
        if mod_name in sys.modules:
            original_modules[mod_name] = sys.modules[mod_name]
            # Remove from cache so the import happens fresh
            del sys.modules[mod_name]

    # Install mock modules
    sys.modules["pyngrok"] = mock_pyngrok_parent
    sys.modules["pyngrok.ngrok"] = mock_ngrok_module
    sys.modules["pyngrok.conf"] = mock_conf_module
    sys.modules["pyngrok.exception"] = mock_exception_module

    yield mock_ngrok_module

    # Restore original modules
    for mod_name in modules_to_patch:
        if mod_name in sys.modules:
            del sys.modules[mod_name]
    for mod_name, original in original_modules.items():
        sys.modules[mod_name] = original


class TestTunnelInfo:
    """Tests for TunnelInfo dataclass."""

    def test_creates_tunnel_info_with_all_fields(self):
        """Should create TunnelInfo with all required fields."""
        info = TunnelInfo(
            url="https://abc123.ngrok.io",
            local_port=8080,
            tunnel_id="tunnel-1-8080",
        )

        assert info.url == "https://abc123.ngrok.io"
        assert info.local_port == 8080
        assert info.tunnel_id == "tunnel-1-8080"

    def test_tunnel_info_is_immutable_dataclass(self):
        """TunnelInfo should be a dataclass with expected attributes."""
        info = TunnelInfo(
            url="https://test.ngrok.io",
            local_port=3000,
            tunnel_id="test-tunnel",
        )

        # Verify dataclass fields
        assert hasattr(info, "url")
        assert hasattr(info, "local_port")
        assert hasattr(info, "tunnel_id")

    def test_tunnel_info_equality(self):
        """Two TunnelInfo with same values should be equal."""
        info1 = TunnelInfo(url="https://test.ngrok.io", local_port=8080, tunnel_id="t1")
        info2 = TunnelInfo(url="https://test.ngrok.io", local_port=8080, tunnel_id="t1")

        assert info1 == info2

    def test_tunnel_info_different_values_not_equal(self):
        """Two TunnelInfo with different values should not be equal."""
        info1 = TunnelInfo(
            url="https://test1.ngrok.io", local_port=8080, tunnel_id="t1"
        )
        info2 = TunnelInfo(
            url="https://test2.ngrok.io", local_port=8080, tunnel_id="t1"
        )

        assert info1 != info2


class TestNgrokTunnelInit:
    """Tests for NgrokTunnel initialization."""

    def test_default_initialization(self):
        """Should initialize with None tunnel and tunnel_info."""
        tunnel = NgrokTunnel()

        assert tunnel.tunnel is None
        assert tunnel.tunnel_info is None
        assert tunnel._tunnel_counter == 0

    def test_initial_state_is_not_active(self):
        """Tunnel should not be active after initialization."""
        tunnel = NgrokTunnel()

        assert tunnel.is_active is False


class TestNgrokTunnelStart:
    """Tests for NgrokTunnel.start() method."""

    @pytest.mark.asyncio
    async def test_start_with_authtoken_from_env(self, mock_pyngrok):
        """Should start tunnel using authtoken from environment."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://envtoken.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        with patch.dict("os.environ", {"NGROK_AUTHTOKEN": "env-token-123"}):
            tunnel = NgrokTunnel()
            info = await tunnel.start(port=8080)

            mock_pyngrok.set_auth_token.assert_called_once_with("env-token-123")
            mock_pyngrok.connect.assert_called_once_with(addr=8080)
            assert info.url == "https://envtoken.ngrok.io"
            assert info.local_port == 8080
            assert tunnel.is_active is True

    @pytest.mark.asyncio
    async def test_start_with_provided_authtoken(self, mock_pyngrok):
        """Should start tunnel using provided authtoken."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://provided.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()
        info = await tunnel.start(port=8080, authtoken="my-token-123")

        mock_pyngrok.set_auth_token.assert_called_once_with("my-token-123")
        mock_pyngrok.connect.assert_called_once_with(addr=8080)
        assert info.url == "https://provided.ngrok.io"

    @pytest.mark.asyncio
    async def test_start_with_custom_domain(self, mock_pyngrok):
        """Should pass custom domain to ngrok.connect."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://custom.mydomain.com"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()
        info = await tunnel.start(
            port=8080,
            authtoken="token",
            domain="custom.mydomain.com",
        )

        mock_pyngrok.set_auth_token.assert_called_once_with("token")
        mock_pyngrok.connect.assert_called_once_with(
            addr=8080,
            hostname="custom.mydomain.com",
        )
        assert info.url == "https://custom.mydomain.com"

    @pytest.mark.asyncio
    async def test_start_sets_tunnel_info(self, mock_pyngrok):
        """Should set tunnel_info with correct values."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://info.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()
        info = await tunnel.start(port=9000, authtoken="token")

        assert tunnel.tunnel_info is not None
        assert tunnel.tunnel_info.url == "https://info.ngrok.io"
        assert tunnel.tunnel_info.local_port == 9000
        assert tunnel.tunnel_info.tunnel_id == "tunnel-1-9000"

    @pytest.mark.asyncio
    async def test_start_converts_http_to_https(self, mock_pyngrok):
        """Should convert http:// URLs to https://."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "http://http-test.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()
        info = await tunnel.start(port=8080, authtoken="token")

        assert info.url == "https://http-test.ngrok.io"

    @pytest.mark.asyncio
    async def test_start_increments_tunnel_counter(self, mock_pyngrok):
        """Should increment tunnel counter on each start."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://counter.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()

        info1 = await tunnel.start(port=8080, authtoken="token")
        assert info1.tunnel_id == "tunnel-1-8080"

        await tunnel.stop()

        info2 = await tunnel.start(port=8080, authtoken="token")
        assert info2.tunnel_id == "tunnel-2-8080"

    @pytest.mark.asyncio
    async def test_start_raises_when_already_active(self, mock_pyngrok):
        """Should raise RuntimeError if tunnel is already active."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://active.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()
        await tunnel.start(port=8080, authtoken="token")

        with pytest.raises(RuntimeError) as exc_info:
            await tunnel.start(port=8080, authtoken="token")

        assert "Tunnel already active" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_raises_without_authtoken(self):
        """Should raise RuntimeError when no authtoken is provided."""
        with patch.dict("os.environ", {}, clear=True):
            # Clear NGROK_AUTHTOKEN from environment
            with patch.object(__import__("os"), "environ", {"HOME": "/home/test"}):
                tunnel = NgrokTunnel()

                with pytest.raises(RuntimeError) as exc_info:
                    await tunnel.start(port=8080)

                error_msg = str(exc_info.value)
                assert "NGROK_AUTHTOKEN" in error_msg
                assert "https://dashboard.ngrok.com" in error_msg

    @pytest.mark.asyncio
    async def test_start_raises_friendly_message_on_auth_error(self, mock_pyngrok):
        """Should raise RuntimeError with helpful message on auth failure."""
        mock_pyngrok.connect.side_effect = MockPyngrokError(
            "authentication failed: invalid token"
        )

        tunnel = NgrokTunnel()

        with pytest.raises(RuntimeError) as exc_info:
            await tunnel.start(port=8080, authtoken="bad-token")

        error_msg = str(exc_info.value)
        assert "authentication failed" in error_msg.lower()
        assert "NGROK_AUTHTOKEN" in error_msg
        assert "https://dashboard.ngrok.com" in error_msg

    @pytest.mark.asyncio
    async def test_start_raises_friendly_message_on_token_error(self, mock_pyngrok):
        """Should handle token-related errors with helpful message."""
        mock_pyngrok.connect.side_effect = MockPyngrokNgrokError(
            "token expired or invalid"
        )

        tunnel = NgrokTunnel()

        with pytest.raises(RuntimeError) as exc_info:
            await tunnel.start(port=8080, authtoken="expired-token")

        error_msg = str(exc_info.value)
        assert "NGROK_AUTHTOKEN" in error_msg

    @pytest.mark.asyncio
    async def test_start_wraps_non_auth_pyngrok_errors(self, mock_pyngrok):
        """Should wrap non-auth PyngrokError in RuntimeError."""
        mock_pyngrok.connect.side_effect = MockPyngrokError("connection refused")

        tunnel = NgrokTunnel()

        with pytest.raises(RuntimeError) as exc_info:
            await tunnel.start(port=8080, authtoken="token")

        assert "Failed to start ngrok tunnel" in str(exc_info.value)
        assert "connection refused" in str(exc_info.value)


class TestNgrokTunnelStop:
    """Tests for NgrokTunnel.stop() method."""

    @pytest.mark.asyncio
    async def test_stop_disconnects_tunnel(self, mock_pyngrok):
        """Should call ngrok.disconnect() when stopping."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://close.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()
        await tunnel.start(port=8080, authtoken="token")

        result = await tunnel.stop()

        assert result is True
        mock_pyngrok.disconnect.assert_called_once_with("https://close.ngrok.io")

    @pytest.mark.asyncio
    async def test_stop_clears_tunnel_and_info(self, mock_pyngrok):
        """Should clear tunnel and tunnel_info after stop."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://clear.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()
        await tunnel.start(port=8080, authtoken="token")

        assert tunnel.tunnel is not None
        assert tunnel.tunnel_info is not None

        await tunnel.stop()

        assert tunnel.tunnel is None
        assert tunnel.tunnel_info is None

    @pytest.mark.asyncio
    async def test_stop_returns_false_when_not_active(self):
        """Should return False when stopping inactive tunnel."""
        tunnel = NgrokTunnel()

        result = await tunnel.stop()

        assert result is False

    @pytest.mark.asyncio
    async def test_stop_handles_disconnect_exception_gracefully(self, mock_pyngrok):
        """Should handle exception during disconnect and still cleanup."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://error.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel
        mock_pyngrok.disconnect.side_effect = Exception("Disconnect failed")

        tunnel = NgrokTunnel()
        await tunnel.start(port=8080, authtoken="token")

        # Should not raise, should still cleanup
        result = await tunnel.stop()

        assert result is True
        assert tunnel.tunnel is None
        assert tunnel.tunnel_info is None


class TestNgrokTunnelIsActive:
    """Tests for NgrokTunnel.is_active property."""

    def test_is_active_false_when_tunnel_none(self):
        """Should return False when tunnel is None."""
        tunnel = NgrokTunnel()

        assert tunnel.is_active is False

    @pytest.mark.asyncio
    async def test_is_active_true_when_tunnel_set(self, mock_pyngrok):
        """Should return True when tunnel is set."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://active.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()
        await tunnel.start(port=8080, authtoken="token")

        assert tunnel.is_active is True


class TestNgrokTunnelGetUrl:
    """Tests for NgrokTunnel.get_url() method."""

    def test_get_url_returns_none_when_inactive(self):
        """Should return None when tunnel is not active."""
        tunnel = NgrokTunnel()

        assert tunnel.get_url() is None

    @pytest.mark.asyncio
    async def test_get_url_returns_url_when_active(self, mock_pyngrok):
        """Should return tunnel URL when active."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://geturl.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()
        await tunnel.start(port=8080, authtoken="token")

        assert tunnel.get_url() == "https://geturl.ngrok.io"


class TestNgrokTunnelContextManager:
    """Tests for NgrokTunnel async context manager protocol."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_returns_self(self):
        """Async context manager should return self on enter."""
        tunnel = NgrokTunnel()

        async with tunnel as ctx:
            assert ctx is tunnel

    @pytest.mark.asyncio
    async def test_context_manager_exit_calls_stop(self, mock_pyngrok):
        """Async context manager should call stop on exit."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://ctx.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()

        async with tunnel:
            await tunnel.start(port=8080, authtoken="token")
            assert tunnel.is_active is True

        # After exiting context, tunnel should be stopped
        assert tunnel.is_active is False
        mock_pyngrok.disconnect.assert_called_once_with("https://ctx.ngrok.io")

    @pytest.mark.asyncio
    async def test_context_manager_exit_handles_no_active_tunnel(self):
        """Context manager exit should handle case where tunnel never started."""
        tunnel = NgrokTunnel()

        # Should not raise
        async with tunnel:
            pass

        assert tunnel.is_active is False

    @pytest.mark.asyncio
    async def test_context_manager_exit_on_exception(self, mock_pyngrok):
        """Context manager should stop tunnel even on exception."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://except.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()

        with pytest.raises(ValueError):
            async with tunnel:
                await tunnel.start(port=8080, authtoken="token")
                raise ValueError("Test exception")

        # Tunnel should still be stopped
        assert tunnel.is_active is False
        mock_pyngrok.disconnect.assert_called_once_with("https://except.ngrok.io")


class TestNgrokTunnelIntegration:
    """Integration-style tests for NgrokTunnel lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_start_stop(self, mock_pyngrok):
        """Test complete tunnel lifecycle: start -> verify -> stop."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://lifecycle.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()

        # Verify initial state
        assert tunnel.is_active is False
        assert tunnel.get_url() is None

        # Start tunnel
        info = await tunnel.start(port=8080, authtoken="token")

        # Verify active state
        assert tunnel.is_active is True
        assert tunnel.get_url() == "https://lifecycle.ngrok.io"
        assert info.url == "https://lifecycle.ngrok.io"
        assert info.local_port == 8080

        # Stop tunnel
        result = await tunnel.stop()

        # Verify stopped state
        assert result is True
        assert tunnel.is_active is False
        assert tunnel.get_url() is None
        mock_pyngrok.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_start_stop_cycles(self, mock_pyngrok):
        """Test multiple start/stop cycles work correctly."""
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://multi.ngrok.io"
        mock_pyngrok.connect.return_value = mock_tunnel

        tunnel = NgrokTunnel()

        # First cycle
        info1 = await tunnel.start(port=8080, authtoken="token")
        assert tunnel.is_active is True
        await tunnel.stop()
        assert tunnel.is_active is False

        # Second cycle
        info2 = await tunnel.start(port=9090, authtoken="token")
        assert tunnel.is_active is True
        assert info2.local_port == 9090
        await tunnel.stop()
        assert tunnel.is_active is False

        # Verify tunnel IDs increment
        assert info1.tunnel_id == "tunnel-1-8080"
        assert info2.tunnel_id == "tunnel-2-9090"
