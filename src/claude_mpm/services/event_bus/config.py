"""Configuration for EventBus service.

WHY configuration module:
- Centralized configuration management
- Environment variable support
- Easy testing with different configurations
- Runtime configuration changes
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EventBusConfig:
    """Configuration for EventBus service.

    All settings can be overridden via environment variables.
    """

    # Enable/disable the EventBus
    enabled: bool = field(
        default_factory=lambda: os.environ.get(
            "CLAUDE_MPM_EVENTBUS_ENABLED", "true"
        ).lower()
        == "true"
    )

    # Debug logging
    debug: bool = field(
        default_factory=lambda: os.environ.get(
            "CLAUDE_MPM_EVENTBUS_DEBUG", "false"
        ).lower()
        == "true"
    )

    # Event history settings
    max_history_size: int = field(
        default_factory=lambda: int(
            os.environ.get("CLAUDE_MPM_EVENTBUS_HISTORY_SIZE", "100")
        )
    )

    # Event filters (comma-separated list)
    event_filters: List[str] = field(
        default_factory=lambda: [
            f.strip()
            for f in os.environ.get("CLAUDE_MPM_EVENTBUS_FILTERS", "").split(",")
            if f.strip()
        ]
    )

    # Relay configuration
    # DirectSocketIORelay disabled by default - events already emit via direct sio.emit()
    # Enable with CLAUDE_MPM_RELAY_ENABLED=true if needed for external consumers
    relay_enabled: bool = field(
        default_factory=lambda: os.environ.get(
            "CLAUDE_MPM_RELAY_ENABLED", "false"
        ).lower()
        == "true"
    )

    relay_port: int = field(
        default_factory=lambda: int(os.environ.get("CLAUDE_MPM_SOCKETIO_PORT", "8765"))
    )

    relay_debug: bool = field(
        default_factory=lambda: os.environ.get(
            "CLAUDE_MPM_RELAY_DEBUG", "false"
        ).lower()
        == "true"
    )

    # Connection settings
    relay_max_retries: int = field(
        default_factory=lambda: int(os.environ.get("CLAUDE_MPM_RELAY_MAX_RETRIES", "3"))
    )

    relay_retry_delay: float = field(
        default_factory=lambda: float(
            os.environ.get("CLAUDE_MPM_RELAY_RETRY_DELAY", "0.5")
        )
    )

    relay_connection_cooldown: float = field(
        default_factory=lambda: float(
            os.environ.get("CLAUDE_MPM_RELAY_CONNECTION_COOLDOWN", "5.0")
        )
    )

    @classmethod
    def from_env(cls) -> "EventBusConfig":
        """Create configuration from environment variables.

        Returns:
            EventBusConfig: Configuration instance
        """
        return cls()

    def to_dict(self) -> dict:
        """Convert configuration to dictionary.

        Returns:
            dict: Configuration as dictionary
        """
        return {
            "enabled": self.enabled,
            "debug": self.debug,
            "max_history_size": self.max_history_size,
            "event_filters": self.event_filters,
            "relay_enabled": self.relay_enabled,
            "relay_port": self.relay_port,
            "relay_debug": self.relay_debug,
            "relay_max_retries": self.relay_max_retries,
            "relay_retry_delay": self.relay_retry_delay,
            "relay_connection_cooldown": self.relay_connection_cooldown,
        }

    def apply_to_eventbus(self, event_bus) -> None:
        """Apply configuration to an EventBus instance.

        Args:
            event_bus: EventBus instance to configure
        """
        if not self.enabled:
            event_bus.disable()
        else:
            event_bus.enable()

        event_bus.set_debug(self.debug)
        event_bus._max_history_size = self.max_history_size

        # Apply filters
        event_bus.clear_filters()
        for filter_pattern in self.event_filters:
            event_bus.add_filter(filter_pattern)

    def apply_to_relay(self, relay) -> None:
        """Apply configuration to a SocketIORelay instance.

        Args:
            relay: SocketIORelay instance to configure
        """
        if not self.relay_enabled:
            relay.disable()
        else:
            relay.enable()

        relay.port = self.relay_port
        relay.debug = self.relay_debug
        relay.max_retries = self.relay_max_retries
        relay.retry_delay = self.relay_retry_delay
        relay.connection_cooldown = self.relay_connection_cooldown


# Global configuration instance
_config: Optional[EventBusConfig] = None


def get_config() -> EventBusConfig:
    """Get the global EventBus configuration.

    Returns:
        EventBusConfig: Configuration instance
    """
    global _config
    if _config is None:
        _config = EventBusConfig.from_env()
    return _config


def set_config(config: EventBusConfig) -> None:
    """Set the global EventBus configuration.

    Args:
        config: Configuration to set
    """
    global _config
    _config = config


def reset_config() -> None:
    """Reset configuration to defaults from environment."""
    global _config
    _config = EventBusConfig.from_env()
