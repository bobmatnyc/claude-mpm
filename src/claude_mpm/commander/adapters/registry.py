"""Adapter registry for runtime detection and selection.

This module provides a registry for managing runtime adapters, with
automatic detection of available runtimes on the system.
"""

import logging
import shutil
from typing import Dict, List, Optional, Type

from .base import RuntimeAdapter

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Registry for managing runtime adapters.

    Provides centralized registration, retrieval, and auto-detection
    of available runtime adapters.

    Example:
        >>> # Register adapter
        >>> AdapterRegistry.register('claude-code', ClaudeCodeAdapter)
        >>> # Get adapter instance
        >>> adapter = AdapterRegistry.get('claude-code')
        >>> # Detect available runtimes
        >>> available = AdapterRegistry.detect_available()
        >>> print(available)
        ['claude-code', 'mpm']
    """

    _adapters: Dict[str, Type[RuntimeAdapter]] = {}
    _runtime_commands: Dict[str, str] = {
        "claude-code": "claude",
        "auggie": "auggie",
        "codex": "codex",
        "mpm": "claude",  # MPM uses claude with extra config
    }

    @classmethod
    def register(cls, name: str, adapter_class: Type[RuntimeAdapter]) -> None:
        """Register a runtime adapter.

        Args:
            name: Unique identifier for the adapter
            adapter_class: RuntimeAdapter subclass to register

        Example:
            >>> AdapterRegistry.register('my-runtime', MyAdapter)
        """
        cls._adapters[name] = adapter_class
        logger.debug(f"Registered adapter: {name}")

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a runtime adapter.

        Args:
            name: Identifier of adapter to unregister

        Example:
            >>> AdapterRegistry.unregister('my-runtime')
        """
        if name in cls._adapters:
            del cls._adapters[name]
            logger.debug(f"Unregistered adapter: {name}")

    @classmethod
    def get(cls, name: str) -> Optional[RuntimeAdapter]:
        """Get adapter instance by name.

        Args:
            name: Identifier of adapter to retrieve

        Returns:
            RuntimeAdapter instance if found, None otherwise

        Example:
            >>> adapter = AdapterRegistry.get('claude-code')
            >>> if adapter:
            ...     print(adapter.name)
            'claude-code'
        """
        if name in cls._adapters:
            adapter = cls._adapters[name]()
            logger.debug(f"Retrieved adapter: {name}")
            return adapter
        logger.warning(f"Adapter not found: {name}")
        return None

    @classmethod
    def list_registered(cls) -> List[str]:
        """List all registered adapter names.

        Returns:
            List of registered adapter identifiers

        Example:
            >>> registered = AdapterRegistry.list_registered()
            >>> print(registered)
            ['claude-code', 'auggie', 'codex', 'mpm']
        """
        return list(cls._adapters.keys())

    @classmethod
    def detect_available(cls) -> List[str]:
        """Detect which runtimes are available on this system.

        Checks for CLI commands in PATH to determine which runtimes
        are installed and accessible.

        Returns:
            List of available runtime identifiers

        Example:
            >>> available = AdapterRegistry.detect_available()
            >>> if 'claude-code' in available:
            ...     print("Claude Code is available")
        """
        available = []

        for name, command in cls._runtime_commands.items():
            if name in cls._adapters and shutil.which(command):
                available.append(name)
                logger.debug(f"Detected available runtime: {name} (command: {command})")

        logger.info(f"Available runtimes: {available}")
        return available

    @classmethod
    def get_default(cls) -> Optional[RuntimeAdapter]:
        """Get the best available adapter.

        Selection priority: mpm > claude-code > auggie > codex

        Returns:
            RuntimeAdapter instance for best available runtime, or None

        Example:
            >>> adapter = AdapterRegistry.get_default()
            >>> if adapter:
            ...     print(f"Using {adapter.name}")
        """
        # Priority order: MPM has most features, then Claude Code, etc.
        priority = ["mpm", "claude-code", "auggie", "codex"]

        available = cls.detect_available()

        for name in priority:
            if name in available:
                adapter = cls.get(name)
                logger.info(f"Selected default adapter: {name}")
                return adapter

        logger.warning("No adapters available")
        return None

    @classmethod
    def is_available(cls, name: str) -> bool:
        """Check if a specific runtime is available.

        Args:
            name: Runtime identifier to check

        Returns:
            True if runtime is registered and command is in PATH

        Example:
            >>> if AdapterRegistry.is_available('claude-code'):
            ...     adapter = AdapterRegistry.get('claude-code')
        """
        return name in cls.detect_available()

    @classmethod
    def get_command(cls, name: str) -> Optional[str]:
        """Get CLI command for a runtime.

        Args:
            name: Runtime identifier

        Returns:
            CLI command string if found, None otherwise

        Example:
            >>> cmd = AdapterRegistry.get_command('claude-code')
            >>> print(cmd)
            'claude'
        """
        return cls._runtime_commands.get(name)

    @classmethod
    def register_command(cls, name: str, command: str) -> None:
        """Register CLI command for a runtime.

        Args:
            name: Runtime identifier
            command: CLI command to invoke runtime

        Example:
            >>> AdapterRegistry.register_command('my-runtime', 'my-cli')
        """
        cls._runtime_commands[name] = command
        logger.debug(f"Registered command for {name}: {command}")
