"""Daemon configuration for MPM Commander.

This module defines configuration structures for the Commander daemon,
including server settings, resource limits, and persistence options.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class DaemonConfig:
    """Configuration for Commander daemon.

    Attributes:
        host: API server bind address
        port: API server port (default: 8766 from NetworkPorts.COMMANDER_DEFAULT)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        state_dir: Directory for state persistence
        max_projects: Maximum concurrent projects
        healthcheck_interval: Healthcheck interval in seconds
        save_interval: State persistence interval in seconds
        poll_interval: Event polling interval in seconds
        summarize_responses: Whether to use LLM to summarize instance responses

    Example:
        >>> config = DaemonConfig(port=8766, log_level="DEBUG")
        >>> config.state_dir
        PosixPath('/Users/user/.claude-mpm/commander')
    """

    host: str = "127.0.0.1"
    port: int = 8766  # Default commander port (from network_config.NetworkPorts.COMMANDER_DEFAULT)
    log_level: str = "INFO"
    state_dir: Path = Path.home() / ".claude-mpm" / "commander"
    max_projects: int = 10
    healthcheck_interval: int = 30
    save_interval: int = 30
    poll_interval: float = 2.0
    summarize_responses: bool = True

    def __post_init__(self):
        """Ensure state_dir is a Path object and create if needed."""
        if isinstance(self.state_dir, str):
            self.state_dir = Path(self.state_dir)

        # Expand user home directory
        self.state_dir = self.state_dir.expanduser()

        # Create state directory if it doesn't exist
        self.state_dir.mkdir(parents=True, exist_ok=True)
