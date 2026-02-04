"""Tests for NgrokTunnel module.

Tests ngrok tunnel lifecycle management with all ngrok calls mocked.
These tests verify the logic and configuration without actually connecting to ngrok.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip entire module if ngrok is not available
ngrok = pytest.importorskip("ngrok")

from claude_mpm.mcp.ngrok_tunnel import NgrokTunnel, TunnelInfo


# Create a mock NgrokError class for testing error handling
# The actual ngrok package may not export this class directly in all versions
class MockNgrokError(Exception):
    """Mock NgrokError for testing."""


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
        """Should initialize with None listener and tunnel_info."""
        tunnel = NgrokTunnel()

        assert tunnel.listener is None
        assert tunnel.tunnel_info is None
        assert tunnel._tunnel_counter == 0

    def test_initial_state_is_not_active(self):
        """Tunnel should not be active after initialization."""
        tunnel = NgrokTunnel()

        assert tunnel.is_active is False


class TestNgrokTunnelStart:
    """Tests for NgrokTunnel.start() method."""

    @pytest.mark.asyncio
    async def test_start_with_authtoken_from_env(self):
        """Should start tunnel using authtoken from environment."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://envtoken.ngrok.io"

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()
            info = await tunnel.start(port=8080)

            mock_forward.assert_called_once_with(
                8080,
                authtoken_from_env=True,
                domain=None,
            )
            assert info.url == "https://envtoken.ngrok.io"
            assert info.local_port == 8080
            assert tunnel.is_active is True

    @pytest.mark.asyncio
    async def test_start_with_provided_authtoken(self):
        """Should start tunnel using provided authtoken."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://provided.ngrok.io"

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()
            info = await tunnel.start(port=8080, authtoken="my-token-123")

            mock_forward.assert_called_once_with(
                8080,
                authtoken="my-token-123",
                domain=None,
            )
            assert info.url == "https://provided.ngrok.io"

    @pytest.mark.asyncio
    async def test_start_with_custom_domain(self):
        """Should pass custom domain to ngrok.forward."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://custom.mydomain.com"

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()
            info = await tunnel.start(
                port=8080,
                authtoken="token",
                domain="custom.mydomain.com",
            )

            mock_forward.assert_called_once_with(
                8080,
                authtoken="token",
                domain="custom.mydomain.com",
            )
            assert info.url == "https://custom.mydomain.com"

    @pytest.mark.asyncio
    async def test_start_sets_tunnel_info(self):
        """Should set tunnel_info with correct values."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://info.ngrok.io"

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()
            info = await tunnel.start(port=9000)

            assert tunnel.tunnel_info is not None
            assert tunnel.tunnel_info.url == "https://info.ngrok.io"
            assert tunnel.tunnel_info.local_port == 9000
            assert tunnel.tunnel_info.tunnel_id == "tunnel-1-9000"

    @pytest.mark.asyncio
    async def test_start_increments_tunnel_counter(self):
        """Should increment tunnel counter on each start."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://counter.ngrok.io"
        mock_listener.close = AsyncMock()

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()

            info1 = await tunnel.start(port=8080)
            assert info1.tunnel_id == "tunnel-1-8080"

            await tunnel.stop()

            info2 = await tunnel.start(port=8080)
            assert info2.tunnel_id == "tunnel-2-8080"

    @pytest.mark.asyncio
    async def test_start_raises_when_already_active(self):
        """Should raise RuntimeError if tunnel is already active."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://active.ngrok.io"

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()
            await tunnel.start(port=8080)

            with pytest.raises(RuntimeError) as exc_info:
                await tunnel.start(port=8080)

            assert "Tunnel already active" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_raises_friendly_message_on_auth_error(self):
        """Should raise RuntimeError with helpful message on auth failure."""
        # Mock NgrokError class on the module being tested with create=True
        # since the attribute may not exist in all ngrok package versions
        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.NgrokError", MockNgrokError, create=True
        ), patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_ngrok_error = MockNgrokError("authentication failed: invalid token")
            mock_forward.side_effect = mock_ngrok_error

            tunnel = NgrokTunnel()

            with pytest.raises(RuntimeError) as exc_info:
                await tunnel.start(port=8080)

            error_msg = str(exc_info.value)
            assert "authentication failed" in error_msg.lower()
            assert "NGROK_AUTHTOKEN" in error_msg
            assert "https://dashboard.ngrok.com" in error_msg

    @pytest.mark.asyncio
    async def test_start_raises_friendly_message_on_token_error(self):
        """Should handle token-related errors with helpful message."""
        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.NgrokError", MockNgrokError, create=True
        ), patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_ngrok_error = MockNgrokError("token expired or invalid")
            mock_forward.side_effect = mock_ngrok_error

            tunnel = NgrokTunnel()

            with pytest.raises(RuntimeError) as exc_info:
                await tunnel.start(port=8080)

            error_msg = str(exc_info.value)
            assert "NGROK_AUTHTOKEN" in error_msg

    @pytest.mark.asyncio
    async def test_start_propagates_non_auth_ngrok_errors(self):
        """Should propagate non-auth NgrokError unchanged."""
        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.NgrokError", MockNgrokError, create=True
        ), patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_ngrok_error = MockNgrokError("connection refused")
            mock_forward.side_effect = mock_ngrok_error

            tunnel = NgrokTunnel()

            with pytest.raises(MockNgrokError):
                await tunnel.start(port=8080)


class TestNgrokTunnelStop:
    """Tests for NgrokTunnel.stop() method."""

    @pytest.mark.asyncio
    async def test_stop_closes_listener(self):
        """Should call close() on listener when stopping."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://close.ngrok.io"
        mock_listener.close = AsyncMock()

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()
            await tunnel.start(port=8080)

            result = await tunnel.stop()

            assert result is True
            mock_listener.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_clears_listener_and_info(self):
        """Should clear listener and tunnel_info after stop."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://clear.ngrok.io"
        mock_listener.close = AsyncMock()

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()
            await tunnel.start(port=8080)

            assert tunnel.listener is not None
            assert tunnel.tunnel_info is not None

            await tunnel.stop()

            assert tunnel.listener is None
            assert tunnel.tunnel_info is None

    @pytest.mark.asyncio
    async def test_stop_returns_false_when_not_active(self):
        """Should return False when stopping inactive tunnel."""
        tunnel = NgrokTunnel()

        result = await tunnel.stop()

        assert result is False

    @pytest.mark.asyncio
    async def test_stop_handles_close_exception_gracefully(self):
        """Should handle exception during close and still cleanup."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://error.ngrok.io"
        mock_listener.close = AsyncMock(side_effect=Exception("Close failed"))

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()
            await tunnel.start(port=8080)

            # Should not raise, should still cleanup
            result = await tunnel.stop()

            assert result is True
            assert tunnel.listener is None
            assert tunnel.tunnel_info is None


class TestNgrokTunnelIsActive:
    """Tests for NgrokTunnel.is_active property."""

    def test_is_active_false_when_listener_none(self):
        """Should return False when listener is None."""
        tunnel = NgrokTunnel()

        assert tunnel.is_active is False

    @pytest.mark.asyncio
    async def test_is_active_true_when_listener_set(self):
        """Should return True when listener is set."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://active.ngrok.io"

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()
            await tunnel.start(port=8080)

            assert tunnel.is_active is True


class TestNgrokTunnelGetUrl:
    """Tests for NgrokTunnel.get_url() method."""

    def test_get_url_returns_none_when_inactive(self):
        """Should return None when tunnel is not active."""
        tunnel = NgrokTunnel()

        assert tunnel.get_url() is None

    @pytest.mark.asyncio
    async def test_get_url_returns_url_when_active(self):
        """Should return tunnel URL when active."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://geturl.ngrok.io"

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()
            await tunnel.start(port=8080)

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
    async def test_context_manager_exit_calls_stop(self):
        """Async context manager should call stop on exit."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://ctx.ngrok.io"
        mock_listener.close = AsyncMock()

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()

            async with tunnel:
                await tunnel.start(port=8080)
                assert tunnel.is_active is True

            # After exiting context, tunnel should be stopped
            assert tunnel.is_active is False
            mock_listener.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exit_handles_no_active_tunnel(self):
        """Context manager exit should handle case where tunnel never started."""
        tunnel = NgrokTunnel()

        # Should not raise
        async with tunnel:
            pass

        assert tunnel.is_active is False

    @pytest.mark.asyncio
    async def test_context_manager_exit_on_exception(self):
        """Context manager should stop tunnel even on exception."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://except.ngrok.io"
        mock_listener.close = AsyncMock()

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()

            with pytest.raises(ValueError):
                async with tunnel:
                    await tunnel.start(port=8080)
                    raise ValueError("Test exception")

            # Tunnel should still be stopped
            assert tunnel.is_active is False
            mock_listener.close.assert_called_once()


class TestNgrokTunnelIntegration:
    """Integration-style tests for NgrokTunnel lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_start_stop(self):
        """Test complete tunnel lifecycle: start -> verify -> stop."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://lifecycle.ngrok.io"
        mock_listener.close = AsyncMock()

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()

            # Verify initial state
            assert tunnel.is_active is False
            assert tunnel.get_url() is None

            # Start tunnel
            info = await tunnel.start(port=8080)

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

    @pytest.mark.asyncio
    async def test_multiple_start_stop_cycles(self):
        """Test multiple start/stop cycles work correctly."""
        mock_listener = MagicMock()
        mock_listener.url.return_value = "https://multi.ngrok.io"
        mock_listener.close = AsyncMock()

        with patch(
            "claude_mpm.mcp.ngrok_tunnel.ngrok.forward", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = mock_listener

            tunnel = NgrokTunnel()

            # First cycle
            info1 = await tunnel.start(port=8080)
            assert tunnel.is_active is True
            await tunnel.stop()
            assert tunnel.is_active is False

            # Second cycle
            info2 = await tunnel.start(port=9090)
            assert tunnel.is_active is True
            assert info2.local_port == 9090
            await tunnel.stop()
            assert tunnel.is_active is False

            # Verify tunnel IDs increment
            assert info1.tunnel_id == "tunnel-1-8080"
            assert info2.tunnel_id == "tunnel-2-9090"
