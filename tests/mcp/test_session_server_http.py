"""Tests for SessionServerHTTP module.

Tests HTTP server wrapper with SSE transport and ngrok integration.
All uvicorn and ngrok calls are mocked.
"""

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip entire module if starlette is not available
starlette = pytest.importorskip("starlette")
uvicorn = pytest.importorskip("uvicorn")

from claude_mpm.mcp.ngrok_tunnel import TunnelInfo


class TestSessionServerHTTPInit:
    """Tests for SessionServerHTTP initialization."""

    def test_default_initialization(self):
        """Should initialize with default values."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServer"
        ) as MockSessionServer, patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ) as MockSSE:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            server = SessionServerHTTP()

            assert server.host == "127.0.0.1"
            assert server.port == 8080
            assert server.enable_ngrok is False
            assert server.ngrok_authtoken is None
            assert server.ngrok_domain is None
            MockSessionServer.assert_called_once_with(
                max_concurrent=5,
                default_timeout=None,
            )

    def test_custom_initialization(self):
        """Should accept custom parameters."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServer"
        ) as MockSessionServer, patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ) as MockSSE:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            server = SessionServerHTTP(
                host="0.0.0.0",
                port=9000,
                max_concurrent=10,
                default_timeout=30.0,
                enable_ngrok=True,
                ngrok_authtoken="test-token",
                ngrok_domain="custom.domain.com",
            )

            assert server.host == "0.0.0.0"
            assert server.port == 9000
            assert server.enable_ngrok is True
            assert server.ngrok_authtoken == "test-token"
            assert server.ngrok_domain == "custom.domain.com"
            MockSessionServer.assert_called_once_with(
                max_concurrent=10,
                default_timeout=30.0,
            )

    def test_creates_sse_transport(self):
        """Should create SSE transport with correct path."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ) as MockSSE:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            server = SessionServerHTTP()

            MockSSE.assert_called_once_with("/messages/")

    def test_creates_ngrok_tunnel_manager(self):
        """Should create NgrokTunnel manager."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.NgrokTunnel") as MockTunnel:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            server = SessionServerHTTP()

            MockTunnel.assert_called_once()

    def test_creates_starlette_app(self):
        """Should create Starlette app on init."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ):
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            server = SessionServerHTTP()

            assert server.app is not None
            # Verify it's a Starlette app by checking for routes
            assert hasattr(server.app, "routes")


class TestSessionServerHTTPCreateApp:
    """Tests for _create_app() method."""

    def test_creates_app_with_required_routes(self):
        """Should create app with all required route endpoints."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ):
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            server = SessionServerHTTP()
            app = server._create_app()

            # Extract route paths
            route_paths = [route.path for route in app.routes]

            assert "/" in route_paths
            assert "/health" in route_paths
            assert "/sse" in route_paths
            assert "/messages/" in route_paths

    def test_creates_app_with_lifecycle_hooks(self):
        """Should configure startup and shutdown hooks."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ):
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            server = SessionServerHTTP()
            app = server._create_app()

            # Verify lifecycle hooks are configured
            # Starlette may store hooks on app, app.router, or use lifespan depending on version
            has_startup_hooks = (
                (hasattr(app, "on_startup") and len(app.on_startup) > 0)
                or (
                    hasattr(app, "router")
                    and hasattr(app.router, "on_startup")
                    and len(app.router.on_startup) > 0
                )
                or hasattr(app, "lifespan")
            )
            has_shutdown_hooks = (
                (hasattr(app, "on_shutdown") and len(app.on_shutdown) > 0)
                or (
                    hasattr(app, "router")
                    and hasattr(app.router, "on_shutdown")
                    and len(app.router.on_shutdown) > 0
                )
                or hasattr(app, "lifespan")
            )

            assert has_startup_hooks, "App should have startup hooks configured"
            assert has_shutdown_hooks, "App should have shutdown hooks configured"


class TestSessionServerHTTPHandleRoot:
    """Tests for _handle_root() endpoint."""

    @pytest.mark.asyncio
    async def test_returns_server_info(self):
        """Should return server information as JSON."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ):
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            server = SessionServerHTTP()

            # Mock request
            mock_request = MagicMock()

            response = await server._handle_root(mock_request)

            # Response should be JSONResponse
            assert response.status_code == 200

            # Decode body
            import json

            body = json.loads(response.body.decode())

            assert body["name"] == "mpm-session-server"
            assert body["version"] == "1.0.0"
            assert body["transport"] == "sse"
            assert "endpoints" in body
            assert body["endpoints"]["sse"] == "/sse"
            assert body["endpoints"]["messages"] == "/messages/"
            assert body["endpoints"]["health"] == "/health"

    @pytest.mark.asyncio
    async def test_includes_tunnel_info_when_disabled(self):
        """Should include tunnel info showing disabled state."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ):
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            server = SessionServerHTTP(enable_ngrok=False)
            mock_request = MagicMock()

            response = await server._handle_root(mock_request)

            import json

            body = json.loads(response.body.decode())

            assert body["tunnel"]["enabled"] is False
            assert body["tunnel"]["active"] is False
            assert body["tunnel"]["url"] is None

    @pytest.mark.asyncio
    async def test_includes_tunnel_url_when_active(self):
        """Should include tunnel URL when ngrok is active."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.NgrokTunnel") as MockTunnel:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            # Configure mock tunnel
            mock_tunnel_instance = MagicMock()
            mock_tunnel_instance.is_active = True
            mock_tunnel_instance.get_url.return_value = "https://active.ngrok.io"
            MockTunnel.return_value = mock_tunnel_instance

            server = SessionServerHTTP(enable_ngrok=True)
            mock_request = MagicMock()

            response = await server._handle_root(mock_request)

            import json

            body = json.loads(response.body.decode())

            assert body["tunnel"]["enabled"] is True
            assert body["tunnel"]["active"] is True
            assert body["tunnel"]["url"] == "https://active.ngrok.io"


class TestSessionServerHTTPHandleHealth:
    """Tests for _handle_health() endpoint."""

    @pytest.mark.asyncio
    async def test_returns_healthy_status(self):
        """Should return healthy status."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServer"
        ) as MockSessionServer, patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ):
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            # Configure mock session server
            mock_session_server = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_active_count = AsyncMock(return_value=3)
            mock_session_server.manager = mock_manager
            MockSessionServer.return_value = mock_session_server

            server = SessionServerHTTP()
            mock_request = MagicMock()

            response = await server._handle_health(mock_request)

            assert response.status_code == 200

            import json

            body = json.loads(response.body.decode())

            assert body["status"] == "healthy"
            assert body["active_sessions"] == 3
            assert "tunnel_active" in body

    @pytest.mark.asyncio
    async def test_includes_tunnel_status(self):
        """Should include tunnel active status in health check."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServer"
        ) as MockSessionServer, patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.NgrokTunnel") as MockTunnel:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            # Configure mocks
            mock_session_server = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_active_count = AsyncMock(return_value=0)
            mock_session_server.manager = mock_manager
            MockSessionServer.return_value = mock_session_server

            mock_tunnel_instance = MagicMock()
            mock_tunnel_instance.is_active = True
            MockTunnel.return_value = mock_tunnel_instance

            server = SessionServerHTTP(enable_ngrok=True)
            mock_request = MagicMock()

            response = await server._handle_health(mock_request)

            import json

            body = json.loads(response.body.decode())

            assert body["tunnel_active"] is True


class TestSessionServerHTTPOnStartup:
    """Tests for _on_startup() lifecycle hook."""

    @pytest.mark.asyncio
    async def test_startup_without_ngrok(self):
        """Should start without ngrok when disabled."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.NgrokTunnel") as MockTunnel:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            mock_tunnel_instance = MagicMock()
            mock_tunnel_instance.start = AsyncMock()
            MockTunnel.return_value = mock_tunnel_instance

            server = SessionServerHTTP(enable_ngrok=False)

            # Should not raise
            await server._on_startup()

            # Ngrok should not be started
            mock_tunnel_instance.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_startup_with_ngrok_enabled(self):
        """Should start ngrok tunnel when enabled."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.NgrokTunnel") as MockTunnel:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            mock_tunnel_instance = MagicMock()
            mock_tunnel_instance.start = AsyncMock(
                return_value=TunnelInfo(
                    url="https://startup.ngrok.io",
                    local_port=8080,
                    tunnel_id="test-1",
                )
            )
            MockTunnel.return_value = mock_tunnel_instance

            server = SessionServerHTTP(
                port=8080,
                enable_ngrok=True,
                ngrok_authtoken="test-token",
                ngrok_domain="test.domain.com",
            )

            await server._on_startup()

            mock_tunnel_instance.start.assert_called_once_with(
                port=8080,
                authtoken="test-token",
                domain="test.domain.com",
            )

    @pytest.mark.asyncio
    async def test_startup_handles_ngrok_failure(self):
        """Should handle ngrok startup failure gracefully."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.NgrokTunnel") as MockTunnel:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            mock_tunnel_instance = MagicMock()
            mock_tunnel_instance.start = AsyncMock(
                side_effect=RuntimeError("Auth failed")
            )
            MockTunnel.return_value = mock_tunnel_instance

            server = SessionServerHTTP(enable_ngrok=True)

            # Should not raise, just log warning
            await server._on_startup()


class TestSessionServerHTTPOnShutdown:
    """Tests for _on_shutdown() lifecycle hook."""

    @pytest.mark.asyncio
    async def test_shutdown_stops_ngrok(self):
        """Should stop ngrok tunnel on shutdown."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServer"
        ) as MockSessionServer, patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.NgrokTunnel") as MockTunnel:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            # Configure mocks
            mock_session_server = MagicMock()
            mock_manager = MagicMock()
            mock_manager.shutdown = AsyncMock()
            mock_session_server.manager = mock_manager
            MockSessionServer.return_value = mock_session_server

            mock_tunnel_instance = MagicMock()
            mock_tunnel_instance.is_active = True
            mock_tunnel_instance.stop = AsyncMock()
            MockTunnel.return_value = mock_tunnel_instance

            server = SessionServerHTTP()

            await server._on_shutdown()

            mock_tunnel_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_calls_manager_shutdown(self):
        """Should shutdown session manager on shutdown."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServer"
        ) as MockSessionServer, patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.NgrokTunnel") as MockTunnel:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            # Configure mocks
            mock_session_server = MagicMock()
            mock_manager = MagicMock()
            mock_manager.shutdown = AsyncMock()
            mock_session_server.manager = mock_manager
            MockSessionServer.return_value = mock_session_server

            mock_tunnel_instance = MagicMock()
            mock_tunnel_instance.is_active = False
            MockTunnel.return_value = mock_tunnel_instance

            server = SessionServerHTTP()

            await server._on_shutdown()

            mock_manager.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_skips_ngrok_when_not_active(self):
        """Should skip ngrok stop when tunnel not active."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServer"
        ) as MockSessionServer, patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.NgrokTunnel") as MockTunnel:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            # Configure mocks
            mock_session_server = MagicMock()
            mock_manager = MagicMock()
            mock_manager.shutdown = AsyncMock()
            mock_session_server.manager = mock_manager
            MockSessionServer.return_value = mock_session_server

            mock_tunnel_instance = MagicMock()
            mock_tunnel_instance.is_active = False
            mock_tunnel_instance.stop = AsyncMock()
            MockTunnel.return_value = mock_tunnel_instance

            server = SessionServerHTTP()

            await server._on_shutdown()

            mock_tunnel_instance.stop.assert_not_called()


class TestSessionServerHTTPGetTunnelInfo:
    """Tests for get_tunnel_info() method."""

    def test_returns_none_when_no_tunnel(self):
        """Should return None when no tunnel info available."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.NgrokTunnel") as MockTunnel:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            mock_tunnel_instance = MagicMock()
            mock_tunnel_instance.tunnel_info = None
            MockTunnel.return_value = mock_tunnel_instance

            server = SessionServerHTTP()

            assert server.get_tunnel_info() is None

    def test_returns_tunnel_info_when_active(self):
        """Should return TunnelInfo when tunnel is active."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.NgrokTunnel") as MockTunnel:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            expected_info = TunnelInfo(
                url="https://tunnel.ngrok.io",
                local_port=8080,
                tunnel_id="test-tunnel",
            )

            mock_tunnel_instance = MagicMock()
            mock_tunnel_instance.tunnel_info = expected_info
            MockTunnel.return_value = mock_tunnel_instance

            server = SessionServerHTTP()

            assert server.get_tunnel_info() == expected_info


class TestSessionServerHTTPCLIParsing:
    """Tests for CLI argument parsing in main()."""

    def test_default_arguments(self):
        """Should use default values when no arguments provided."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServerHTTP"
        ) as MockServer, patch("claude_mpm.mcp.session_server_http.asyncio.run"):
            from claude_mpm.mcp.session_server_http import main

            # Simulate no command line arguments
            with patch("sys.argv", ["session_server_http"]):
                main()

            MockServer.assert_called_once_with(
                host="127.0.0.1",
                port=8080,
                max_concurrent=5,
                default_timeout=None,
                enable_ngrok=False,
                ngrok_authtoken=None,
                ngrok_domain=None,
            )

    def test_custom_host_and_port(self):
        """Should accept custom host and port arguments."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServerHTTP"
        ) as MockServer, patch("claude_mpm.mcp.session_server_http.asyncio.run"):
            from claude_mpm.mcp.session_server_http import main

            with patch(
                "sys.argv",
                ["session_server_http", "--host", "0.0.0.0", "--port", "9000"],
            ):
                main()

            MockServer.assert_called_once()
            call_kwargs = MockServer.call_args[1]
            assert call_kwargs["host"] == "0.0.0.0"
            assert call_kwargs["port"] == 9000

    def test_ngrok_flag(self):
        """Should enable ngrok when --ngrok flag provided."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServerHTTP"
        ) as MockServer, patch("claude_mpm.mcp.session_server_http.asyncio.run"):
            from claude_mpm.mcp.session_server_http import main

            with patch("sys.argv", ["session_server_http", "--ngrok"]):
                main()

            MockServer.assert_called_once()
            call_kwargs = MockServer.call_args[1]
            assert call_kwargs["enable_ngrok"] is True

    def test_ngrok_authtoken_argument(self):
        """Should accept ngrok authtoken argument."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServerHTTP"
        ) as MockServer, patch("claude_mpm.mcp.session_server_http.asyncio.run"):
            from claude_mpm.mcp.session_server_http import main

            with patch(
                "sys.argv",
                ["session_server_http", "--ngrok", "--ngrok-authtoken", "my-token"],
            ):
                main()

            MockServer.assert_called_once()
            call_kwargs = MockServer.call_args[1]
            assert call_kwargs["ngrok_authtoken"] == "my-token"

    def test_ngrok_domain_argument(self):
        """Should accept ngrok domain argument."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServerHTTP"
        ) as MockServer, patch("claude_mpm.mcp.session_server_http.asyncio.run"):
            from claude_mpm.mcp.session_server_http import main

            with patch(
                "sys.argv",
                ["session_server_http", "--ngrok", "--ngrok-domain", "my.domain.com"],
            ):
                main()

            MockServer.assert_called_once()
            call_kwargs = MockServer.call_args[1]
            assert call_kwargs["ngrok_domain"] == "my.domain.com"

    def test_max_concurrent_argument(self):
        """Should accept max-concurrent argument."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServerHTTP"
        ) as MockServer, patch("claude_mpm.mcp.session_server_http.asyncio.run"):
            from claude_mpm.mcp.session_server_http import main

            with patch("sys.argv", ["session_server_http", "--max-concurrent", "20"]):
                main()

            MockServer.assert_called_once()
            call_kwargs = MockServer.call_args[1]
            assert call_kwargs["max_concurrent"] == 20

    def test_timeout_argument(self):
        """Should accept timeout argument."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServerHTTP"
        ) as MockServer, patch("claude_mpm.mcp.session_server_http.asyncio.run"):
            from claude_mpm.mcp.session_server_http import main

            with patch("sys.argv", ["session_server_http", "--timeout", "60.0"]):
                main()

            MockServer.assert_called_once()
            call_kwargs = MockServer.call_args[1]
            assert call_kwargs["default_timeout"] == 60.0

    def test_all_arguments_combined(self):
        """Should accept all arguments combined."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServerHTTP"
        ) as MockServer, patch("claude_mpm.mcp.session_server_http.asyncio.run"):
            from claude_mpm.mcp.session_server_http import main

            with patch(
                "sys.argv",
                [
                    "session_server_http",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "9000",
                    "--max-concurrent",
                    "10",
                    "--timeout",
                    "120.0",
                    "--ngrok",
                    "--ngrok-authtoken",
                    "token123",
                    "--ngrok-domain",
                    "custom.ngrok.io",
                ],
            ):
                main()

            MockServer.assert_called_once_with(
                host="0.0.0.0",
                port=9000,
                max_concurrent=10,
                default_timeout=120.0,
                enable_ngrok=True,
                ngrok_authtoken="token123",
                ngrok_domain="custom.ngrok.io",
            )


class TestSessionServerHTTPRun:
    """Tests for run() method."""

    @pytest.mark.asyncio
    async def test_run_creates_uvicorn_config(self):
        """Should create uvicorn config with correct parameters."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch(
            "claude_mpm.mcp.session_server_http.uvicorn.Config"
        ) as MockConfig, patch(
            "claude_mpm.mcp.session_server_http.uvicorn.Server"
        ) as MockUvicornServer, patch(
            "claude_mpm.mcp.session_server_http.asyncio.get_event_loop"
        ) as mock_loop, patch("claude_mpm.mcp.session_server_http.signal"):
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            # Configure mocks
            mock_server_instance = MagicMock()
            mock_server_instance.serve = AsyncMock()
            MockUvicornServer.return_value = mock_server_instance

            mock_event_loop = MagicMock()
            mock_loop.return_value = mock_event_loop

            server = SessionServerHTTP(host="0.0.0.0", port=9000)

            await server.run()

            MockConfig.assert_called_once()
            config_kwargs = MockConfig.call_args[1]
            assert config_kwargs["host"] == "0.0.0.0"
            assert config_kwargs["port"] == 9000
            assert config_kwargs["log_level"] == "info"

    @pytest.mark.asyncio
    async def test_run_calls_server_serve(self):
        """Should call uvicorn server.serve()."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.uvicorn.Config"), patch(
            "claude_mpm.mcp.session_server_http.uvicorn.Server"
        ) as MockUvicornServer, patch(
            "claude_mpm.mcp.session_server_http.asyncio.get_event_loop"
        ) as mock_loop, patch("claude_mpm.mcp.session_server_http.signal"):
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            mock_server_instance = MagicMock()
            mock_server_instance.serve = AsyncMock()
            MockUvicornServer.return_value = mock_server_instance

            mock_event_loop = MagicMock()
            mock_loop.return_value = mock_event_loop

            server = SessionServerHTTP()

            await server.run()

            mock_server_instance.serve.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_sets_up_signal_handlers(self):
        """Should set up signal handlers for graceful shutdown."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ), patch("claude_mpm.mcp.session_server_http.uvicorn.Config"), patch(
            "claude_mpm.mcp.session_server_http.uvicorn.Server"
        ) as MockUvicornServer, patch(
            "claude_mpm.mcp.session_server_http.asyncio.get_event_loop"
        ) as mock_loop, patch(
            "claude_mpm.mcp.session_server_http.signal"
        ) as mock_signal:
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            mock_server_instance = MagicMock()
            mock_server_instance.serve = AsyncMock()
            MockUvicornServer.return_value = mock_server_instance

            mock_event_loop = MagicMock()
            mock_loop.return_value = mock_event_loop

            server = SessionServerHTTP()

            await server.run()

            # Should add signal handlers for SIGINT and SIGTERM
            assert mock_event_loop.add_signal_handler.call_count == 2


class TestSessionServerHTTPIntegration:
    """Integration-style tests for SessionServerHTTP."""

    def test_app_routes_have_correct_methods(self):
        """App routes should have correct HTTP methods."""
        with patch("claude_mpm.mcp.session_server_http.SessionServer"), patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ):
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            server = SessionServerHTTP()

            # Build a map of path -> methods
            route_methods = {}
            for route in server.app.routes:
                if hasattr(route, "methods"):
                    route_methods[route.path] = route.methods

            # Verify expected methods
            assert "GET" in route_methods.get("/", set())
            assert "GET" in route_methods.get("/health", set())
            assert "GET" in route_methods.get("/sse", set())
            assert "POST" in route_methods.get("/messages/", set())

    @pytest.mark.asyncio
    async def test_full_endpoint_responses(self):
        """Test that all endpoints return valid responses."""
        with patch(
            "claude_mpm.mcp.session_server_http.SessionServer"
        ) as MockSessionServer, patch(
            "claude_mpm.mcp.session_server_http.SseServerTransport"
        ):
            from claude_mpm.mcp.session_server_http import SessionServerHTTP

            # Configure mock
            mock_session_server = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_active_count = AsyncMock(return_value=0)
            mock_session_server.manager = mock_manager
            MockSessionServer.return_value = mock_session_server

            server = SessionServerHTTP()
            mock_request = MagicMock()

            # Test root endpoint
            root_response = await server._handle_root(mock_request)
            assert root_response.status_code == 200

            # Test health endpoint
            health_response = await server._handle_health(mock_request)
            assert health_response.status_code == 200

            # Verify response content types
            assert root_response.media_type == "application/json"
            assert health_response.media_type == "application/json"
