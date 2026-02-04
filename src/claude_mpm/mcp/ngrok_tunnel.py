"""Ngrok tunnel management for MCP Session Server.

This module provides ngrok tunnel lifecycle management for exposing
local MCP servers to the internet for remote access.
"""

import logging
from dataclasses import dataclass
from typing import Any

import ngrok

logger = logging.getLogger(__name__)


@dataclass
class TunnelInfo:
    """Information about an active ngrok tunnel.

    Attributes:
        url: The public ngrok URL (https://xxx.ngrok.io).
        local_port: The local port being tunneled.
        tunnel_id: Unique identifier for this tunnel instance.
    """

    url: str
    local_port: int
    tunnel_id: str


class NgrokTunnel:
    """Manages ngrok tunnel lifecycle for MCP Session Server.

    This class handles creating, monitoring, and closing ngrok tunnels
    to expose local MCP servers to the internet.

    Attributes:
        listener: The active ngrok listener, or None if not connected.
        tunnel_info: Information about the active tunnel, or None.

    Example:
        >>> tunnel = NgrokTunnel()
        >>> info = await tunnel.start(port=8080)
        >>> print(f"Server available at: {info.url}")
        >>> await tunnel.stop()
    """

    def __init__(self) -> None:
        """Initialize NgrokTunnel manager."""
        self.listener: Any | None = None
        self.tunnel_info: TunnelInfo | None = None
        self._tunnel_counter = 0

    async def start(
        self,
        port: int,
        authtoken: str | None = None,
        domain: str | None = None,
    ) -> TunnelInfo:
        """Start an ngrok tunnel to the specified port.

        Args:
            port: Local port to tunnel.
            authtoken: Optional ngrok authtoken. If not provided,
                uses NGROK_AUTHTOKEN environment variable.
            domain: Optional custom domain (requires ngrok paid plan).

        Returns:
            TunnelInfo with the public URL and tunnel details.

        Raises:
            RuntimeError: If tunnel is already active or ngrok auth fails.
            ngrok.NgrokError: If ngrok connection fails.
        """
        if self.listener is not None:
            raise RuntimeError("Tunnel already active. Stop it first.")

        try:
            # Build forward options
            if authtoken:
                # Use provided authtoken
                self.listener = await ngrok.forward(
                    port,
                    authtoken=authtoken,
                    domain=domain,
                )
            else:
                # Use authtoken from environment (NGROK_AUTHTOKEN)
                self.listener = await ngrok.forward(
                    port,
                    authtoken_from_env=True,
                    domain=domain,
                )

            url = self.listener.url()
            self._tunnel_counter += 1
            tunnel_id = f"tunnel-{self._tunnel_counter}-{port}"

            self.tunnel_info = TunnelInfo(
                url=url,
                local_port=port,
                tunnel_id=tunnel_id,
            )

            logger.info(
                "Ngrok tunnel started: %s -> localhost:%d (id: %s)",
                url,
                port,
                tunnel_id,
            )

            return self.tunnel_info

        except ngrok.NgrokError as e:
            error_msg = str(e).lower()
            if "auth" in error_msg or "token" in error_msg:
                raise RuntimeError(
                    "Ngrok authentication failed. Please set NGROK_AUTHTOKEN "
                    "environment variable or provide authtoken parameter. "
                    "Get your token at: https://dashboard.ngrok.com/get-started/your-authtoken"
                ) from e
            raise

    async def stop(self) -> bool:
        """Stop the active ngrok tunnel.

        Returns:
            True if tunnel was stopped, False if no tunnel was active.
        """
        if self.listener is None:
            logger.warning("No active tunnel to stop")
            return False

        try:
            await self.listener.close()
            logger.info(
                "Ngrok tunnel stopped: %s",
                self.tunnel_info.url if self.tunnel_info else "unknown",
            )
        except Exception as e:
            logger.warning("Error closing ngrok tunnel: %s", e)
        finally:
            self.listener = None
            self.tunnel_info = None

        return True

    @property
    def is_active(self) -> bool:
        """Check if tunnel is currently active.

        Returns:
            True if tunnel is active, False otherwise.
        """
        return self.listener is not None

    def get_url(self) -> str | None:
        """Get the public URL of the active tunnel.

        Returns:
            The public ngrok URL, or None if no tunnel is active.
        """
        if self.tunnel_info:
            return self.tunnel_info.url
        return None

    async def __aenter__(self) -> "NgrokTunnel":
        """Async context manager entry (tunnel must be started separately)."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit - ensures tunnel is stopped."""
        await self.stop()
