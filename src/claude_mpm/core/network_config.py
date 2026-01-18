"""Centralized network port configuration for Claude MPM.

This module provides the single source of truth for all network port defaults
and environment variable names used throughout the MPM system.

WHY: Previously, port defaults were hardcoded in multiple locations (config.py,
constants.py, commander/config.py, CLI parsers), leading to inconsistencies and
difficulty maintaining different defaults per service.

USAGE:
    from claude_mpm.core.network_config import NetworkPorts

    # Get default ports
    monitor_port = NetworkPorts.MONITOR_DEFAULT
    commander_port = NetworkPorts.COMMANDER_DEFAULT

    # Get from environment with fallback
    port = NetworkPorts.get_monitor_port()
"""

import os
from typing import Optional


class NetworkPorts:
    """Network port configuration with different defaults for each service.

    Service Default Ports:
    - Monitor: 8765 (user's preferred default)
    - Commander: 8766
    - Dashboard: 8767
    - SocketIO: 8768

    Port Range: 8765-8785 (21 ports available)

    Environment Variables:
    - CLAUDE_MPM_MONITOR_PORT: Override monitor port
    - CLAUDE_MPM_COMMANDER_PORT: Override commander port
    - CLAUDE_MPM_DASHBOARD_PORT: Override dashboard port
    - CLAUDE_MPM_SOCKETIO_PORT: Override socketio port
    - CLAUDE_MPM_DEFAULT_HOST: Override default host (default: 127.0.0.1)
    """

    # Default ports for each service
    MONITOR_DEFAULT = 8765
    COMMANDER_DEFAULT = 8766
    DASHBOARD_DEFAULT = 8767
    SOCKETIO_DEFAULT = 8768

    # Port range configuration
    PORT_RANGE_START = 8765
    PORT_RANGE_END = 8785

    # Default host
    DEFAULT_HOST = "127.0.0.1"

    # Environment variable names
    ENV_MONITOR_PORT = "CLAUDE_MPM_MONITOR_PORT"
    ENV_COMMANDER_PORT = "CLAUDE_MPM_COMMANDER_PORT"
    ENV_DASHBOARD_PORT = "CLAUDE_MPM_DASHBOARD_PORT"
    ENV_SOCKETIO_PORT = "CLAUDE_MPM_SOCKETIO_PORT"
    ENV_DEFAULT_HOST = "CLAUDE_MPM_DEFAULT_HOST"

    @classmethod
    def get_monitor_port(cls, default: Optional[int] = None) -> int:
        """Get monitor port from environment or default.

        Args:
            default: Optional override default (if not provided, uses MONITOR_DEFAULT)

        Returns:
            Port number from environment or default
        """
        if default is None:
            default = cls.MONITOR_DEFAULT
        return int(os.getenv(cls.ENV_MONITOR_PORT, default))

    @classmethod
    def get_commander_port(cls, default: Optional[int] = None) -> int:
        """Get commander port from environment or default.

        Args:
            default: Optional override default (if not provided, uses COMMANDER_DEFAULT)

        Returns:
            Port number from environment or default
        """
        if default is None:
            default = cls.COMMANDER_DEFAULT
        return int(os.getenv(cls.ENV_COMMANDER_PORT, default))

    @classmethod
    def get_dashboard_port(cls, default: Optional[int] = None) -> int:
        """Get dashboard port from environment or default.

        Args:
            default: Optional override default (if not provided, uses DASHBOARD_DEFAULT)

        Returns:
            Port number from environment or default
        """
        if default is None:
            default = cls.DASHBOARD_DEFAULT
        return int(os.getenv(cls.ENV_DASHBOARD_PORT, default))

    @classmethod
    def get_socketio_port(cls, default: Optional[int] = None) -> int:
        """Get socketio port from environment or default.

        Args:
            default: Optional override default (if not provided, uses SOCKETIO_DEFAULT)

        Returns:
            Port number from environment or default
        """
        if default is None:
            default = cls.SOCKETIO_DEFAULT
        return int(os.getenv(cls.ENV_SOCKETIO_PORT, default))

    @classmethod
    def get_default_host(cls) -> str:
        """Get default host from environment or default.

        Returns:
            Host address from environment or DEFAULT_HOST
        """
        return os.getenv(cls.ENV_DEFAULT_HOST, cls.DEFAULT_HOST)

    @classmethod
    def get_port_range(cls) -> range:
        """Get the valid port range.

        Returns:
            Range object from PORT_RANGE_START to PORT_RANGE_END (inclusive)
        """
        return range(cls.PORT_RANGE_START, cls.PORT_RANGE_END + 1)

    @classmethod
    def is_port_in_range(cls, port: int) -> bool:
        """Check if port is within valid range.

        Args:
            port: Port number to check

        Returns:
            True if port is in valid range, False otherwise
        """
        return cls.PORT_RANGE_START <= port <= cls.PORT_RANGE_END
