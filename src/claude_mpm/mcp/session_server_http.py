"""HTTP wrapper for MCP Session Server with SSE transport.

This module provides an HTTP server wrapper around the MCP Session Server,
enabling remote access via Server-Sent Events (SSE) transport with optional
ngrok tunnel integration.
"""

import argparse
import asyncio
import logging
import signal

import uvicorn
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from claude_mpm.mcp.ngrok_tunnel import NgrokTunnel, TunnelInfo
from claude_mpm.mcp.session_server import SessionServer

logger = logging.getLogger(__name__)


class SessionServerHTTP:
    """HTTP wrapper for MCP Session Server with SSE transport.

    Provides an HTTP server that exposes the MCP Session Server via
    Server-Sent Events (SSE) transport, with optional ngrok tunnel
    for remote access.

    Attributes:
        session_server: The underlying MCP SessionServer instance.
        host: Host address to bind to.
        port: Port number to bind to.
        ngrok_tunnel: NgrokTunnel instance for remote access.
        sse_transport: SSE transport for MCP communication.
        app: Starlette ASGI application.

    Example:
        >>> server = SessionServerHTTP(port=8080)
        >>> await server.run()  # Blocks until shutdown

        With ngrok:
        >>> server = SessionServerHTTP(port=8080, enable_ngrok=True)
        >>> await server.run()
        >>> # Server accessible at ngrok URL
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        max_concurrent: int = 5,
        default_timeout: float | None = None,
        enable_ngrok: bool = False,
        ngrok_authtoken: str | None = None,
        ngrok_domain: str | None = None,
    ) -> None:
        """Initialize the HTTP Session Server.

        Args:
            host: Host address to bind to (default: 127.0.0.1).
            port: Port number to bind to (default: 8080).
            max_concurrent: Maximum concurrent sessions (default: 5).
            default_timeout: Default timeout for session operations.
            enable_ngrok: Whether to enable ngrok tunnel (default: False).
            ngrok_authtoken: Optional ngrok authtoken (uses env if not provided).
            ngrok_domain: Optional custom ngrok domain (paid feature).
        """
        self.host = host
        self.port = port
        self.enable_ngrok = enable_ngrok
        self.ngrok_authtoken = ngrok_authtoken
        self.ngrok_domain = ngrok_domain

        # Create the underlying session server
        self.session_server = SessionServer(
            max_concurrent=max_concurrent,
            default_timeout=default_timeout,
        )

        # SSE transport for MCP communication
        self.sse_transport = SseServerTransport("/messages/")

        # Ngrok tunnel manager
        self.ngrok_tunnel = NgrokTunnel()

        # Starlette app
        self.app = self._create_app()

        # Shutdown event
        self._shutdown_event = asyncio.Event()

    def _create_app(self) -> Starlette:
        """Create the Starlette ASGI application.

        Returns:
            Configured Starlette application with routes.
        """
        routes = [
            Route("/", endpoint=self._handle_root, methods=["GET"]),
            Route("/health", endpoint=self._handle_health, methods=["GET"]),
            Route("/sse", endpoint=self._handle_sse, methods=["GET"]),
            Route("/messages/", endpoint=self._handle_messages, methods=["POST"]),
        ]

        return Starlette(
            routes=routes,
            on_startup=[self._on_startup],
            on_shutdown=[self._on_shutdown],
        )

    async def _on_startup(self) -> None:
        """Handle application startup."""
        logger.info("MCP Session Server HTTP starting...")

        if self.enable_ngrok:
            try:
                tunnel_info = await self.ngrok_tunnel.start(
                    port=self.port,
                    authtoken=self.ngrok_authtoken,
                    domain=self.ngrok_domain,
                )
                logger.info("Ngrok tunnel active: %s", tunnel_info.url)
                print(f"\n{'=' * 60}")
                print("MCP Session Server HTTP")
                print(f"{'=' * 60}")
                print(f"Local:  http://{self.host}:{self.port}")
                print(f"Public: {tunnel_info.url}")
                print(f"SSE:    {tunnel_info.url}/sse")
                print(f"{'=' * 60}\n")
            except RuntimeError as e:
                logger.error("Failed to start ngrok tunnel: %s", e)
                print(f"\nWarning: Ngrok tunnel failed - {e}")
                print(f"Server running locally at http://{self.host}:{self.port}\n")
        else:
            print(f"\n{'=' * 60}")
            print("MCP Session Server HTTP")
            print(f"{'=' * 60}")
            print(f"Local: http://{self.host}:{self.port}")
            print(f"SSE:   http://{self.host}:{self.port}/sse")
            print(f"{'=' * 60}\n")

    async def _on_shutdown(self) -> None:
        """Handle application shutdown."""
        logger.info("MCP Session Server HTTP shutting down...")

        # Stop ngrok tunnel
        if self.ngrok_tunnel.is_active:
            await self.ngrok_tunnel.stop()

        # Shutdown session manager
        await self.session_server.manager.shutdown()

        logger.info("MCP Session Server HTTP shutdown complete")

    async def _handle_root(self, request: Request) -> JSONResponse:
        """Handle root endpoint with server info.

        Args:
            request: Incoming HTTP request.

        Returns:
            JSON response with server information.
        """
        tunnel_url = self.ngrok_tunnel.get_url()
        return JSONResponse(
            {
                "name": "mpm-session-server",
                "version": "1.0.0",
                "transport": "sse",
                "endpoints": {
                    "sse": "/sse",
                    "messages": "/messages/",
                    "health": "/health",
                },
                "tunnel": {
                    "enabled": self.enable_ngrok,
                    "active": self.ngrok_tunnel.is_active,
                    "url": tunnel_url,
                },
            }
        )

    async def _handle_health(self, request: Request) -> JSONResponse:
        """Handle health check endpoint.

        Args:
            request: Incoming HTTP request.

        Returns:
            JSON response with health status.
        """
        active_sessions = await self.session_server.manager.get_active_count()
        return JSONResponse(
            {
                "status": "healthy",
                "active_sessions": active_sessions,
                "tunnel_active": self.ngrok_tunnel.is_active,
            }
        )

    async def _handle_sse(self, request: Request) -> Response:
        """Handle SSE connection endpoint.

        Args:
            request: Incoming HTTP request.

        Returns:
            SSE stream response.
        """
        async with self.sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as streams:
            await self.session_server.server.run(
                streams[0],
                streams[1],
                self.session_server.server.create_initialization_options(),
            )
        return Response()

    async def _handle_messages(self, request: Request) -> Response:
        """Handle POST messages for SSE transport.

        Args:
            request: Incoming HTTP request with message data.

        Returns:
            Response from SSE transport message handler.
        """
        return await self.sse_transport.handle_post_message(
            request.scope,
            request.receive,
            request._send,
        )

    async def run(self) -> None:
        """Run the HTTP server.

        Blocks until shutdown signal is received (SIGINT, SIGTERM).
        """
        # Setup signal handlers
        loop = asyncio.get_event_loop()

        def signal_handler() -> None:
            logger.info("Shutdown signal received")
            self._shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        # Create uvicorn config
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        # Run server until shutdown
        await server.serve()

    def get_tunnel_info(self) -> TunnelInfo | None:
        """Get information about the active ngrok tunnel.

        Returns:
            TunnelInfo if tunnel is active, None otherwise.
        """
        return self.ngrok_tunnel.tunnel_info


def main() -> None:
    """Entry point for the MCP Session Server HTTP."""
    parser = argparse.ArgumentParser(
        description="MCP Session Server with HTTP/SSE transport"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port number to bind to (default: 8080)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum concurrent sessions (default: 5)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Default timeout for session operations in seconds",
    )
    parser.add_argument(
        "--ngrok",
        action="store_true",
        help="Enable ngrok tunnel for remote access",
    )
    parser.add_argument(
        "--ngrok-authtoken",
        default=None,
        help="Ngrok authtoken (uses NGROK_AUTHTOKEN env if not provided)",
    )
    parser.add_argument(
        "--ngrok-domain",
        default=None,
        help="Custom ngrok domain (paid feature)",
    )

    args = parser.parse_args()

    server = SessionServerHTTP(
        host=args.host,
        port=args.port,
        max_concurrent=args.max_concurrent,
        default_timeout=args.timeout,
        enable_ngrok=args.ngrok,
        ngrok_authtoken=args.ngrok_authtoken,
        ngrok_domain=args.ngrok_domain,
    )

    asyncio.run(server.run())


if __name__ == "__main__":
    main()
