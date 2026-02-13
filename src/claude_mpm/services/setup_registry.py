"""Setup Registry Service - Track configured MCP servers and CLI tools."""

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional


class SetupRegistry:
    """Registry for tracking configured services (MCP servers and CLI tools)."""

    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize setup registry.

        Args:
            registry_path: Path to registry file (default: ~/.claude-mpm/setup-registry.json)
        """
        if registry_path is None:
            registry_path = Path.home() / ".claude-mpm" / "setup-registry.json"

        self.registry_path = registry_path
        self._lock = Lock()
        self._ensure_registry_exists()

    def _ensure_registry_exists(self) -> None:
        """Ensure registry file and directory exist."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._save_registry({"services": {}})

    def _load_registry(self) -> Dict:
        """Load registry from disk (thread-safe)."""
        with self._lock:
            try:
                with open(self.registry_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {"services": {}}

    def _save_registry(self, data: Dict) -> None:
        """Save registry to disk (thread-safe)."""
        with self._lock:
            with open(self.registry_path, "w") as f:
                json.dump(data, f, indent=2)

    def add_service(
        self,
        name: str,
        service_type: str,
        version: str = "",
        tools: Optional[List[str]] = None,
        cli_help: str = "",
        config_location: str = "user",
    ) -> None:
        """Add or update a service in the registry.

        Args:
            name: Service name (e.g., "gworkspace-mcp")
            service_type: "mcp" or "cli"
            version: Service version
            tools: List of available tools/commands
            cli_help: CLI help text for the tool
            config_location: "user" or "project"
        """
        registry = self._load_registry()

        registry["services"][name] = {
            "type": service_type,
            "version": version,
            "setup_date": datetime.now().astimezone().isoformat(),
            "tools": tools or [],
            "cli_help": cli_help,
            "config_location": config_location,
        }

        self._save_registry(registry)

    def remove_service(self, name: str) -> bool:
        """Remove a service from the registry.

        Args:
            name: Service name to remove

        Returns:
            True if service was removed, False if not found
        """
        registry = self._load_registry()

        if name in registry["services"]:
            del registry["services"][name]
            self._save_registry(registry)
            return True
        return False

    def get_service(self, name: str) -> Optional[Dict]:
        """Get service details.

        Args:
            name: Service name

        Returns:
            Service details dict or None if not found
        """
        registry = self._load_registry()
        return registry["services"].get(name)

    def list_services(self, service_type: Optional[str] = None) -> List[str]:
        """List all services (optionally filtered by type).

        Args:
            service_type: Filter by "mcp" or "cli" (None = all)

        Returns:
            List of service names
        """
        registry = self._load_registry()
        services = registry["services"]

        if service_type is None:
            return list(services.keys())

        return [
            name
            for name, details in services.items()
            if details.get("type") == service_type
        ]

    def get_all_tools(self) -> Dict[str, List[str]]:
        """Get all tools grouped by service.

        Returns:
            Dict mapping service name to list of tools
        """
        registry = self._load_registry()
        return {
            name: details.get("tools", [])
            for name, details in registry["services"].items()
        }

    def get_services_with_details(self) -> Dict[str, Dict]:
        """Get all services with full details.

        Returns:
            Dict mapping service name to service details
        """
        registry = self._load_registry()
        return registry["services"]
