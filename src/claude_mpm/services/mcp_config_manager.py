"""
MCP Configuration Manager (Facade)
==================================

Thin backward-compatible facade over the decomposed ``mcp`` subpackage.

The historic ``MCPConfigManager`` was a 1,676-line god class with
cyclomatic complexity ~273. It has been split into focused services
under :mod:`claude_mpm.services.mcp` (#507):

- :class:`~claude_mpm.services.mcp.service_locator.MCPServiceLocator`
- :class:`~claude_mpm.services.mcp.config_builder.MCPServiceConfigBuilder`
- :class:`~claude_mpm.services.mcp.config_file_manager.MCPConfigFileManager`
- :class:`~claude_mpm.services.mcp.service_installer.MCPServiceInstaller`
- :class:`~claude_mpm.services.mcp.health_manager.MCPServiceHealthManager`

This module preserves the public ``MCPConfigManager`` API (constructor
signature, methods, ``PIPX_SERVICES`` / ``STATIC_MCP_CONFIGS`` class
attributes) so existing callers continue to work unchanged.
"""

from __future__ import annotations

from pathlib import Path

from ..core.logger import get_logger
from .mcp.config_builder import MCPServiceConfigBuilder
from .mcp.config_file_manager import ConfigLocation, MCPConfigFileManager
from .mcp.health_manager import MCPServiceHealthManager
from .mcp.service_installer import MCPServiceInstaller
from .mcp.service_locator import MCPServiceLocator

# Re-export ConfigLocation for backward compatibility
__all__ = ["ConfigLocation", "MCPConfigManager"]


class MCPConfigManager:
    """Backward-compatible facade for MCP service configuration.

    Delegates to focused services under :mod:`claude_mpm.services.mcp`.
    The public surface is preserved verbatim so external callers
    (``cli/commands/mcp_config.py``, ``cli/startup_logging.py``,
    ``services/diagnostics/checks/mcp_services_check.py``, etc.)
    continue to work without code changes.
    """

    # Class-level aliases for backward compatibility.
    # Callers rely on these as ``MCPConfigManager.PIPX_SERVICES`` etc.
    PIPX_SERVICES = MCPServiceInstaller.PIPX_SERVICES
    CARGO_SERVICES = MCPServiceInstaller.CARGO_SERVICES
    SERVICE_MISSING_DEPENDENCIES = MCPServiceInstaller.SERVICE_MISSING_DEPENDENCIES
    STATIC_MCP_CONFIGS = MCPServiceConfigBuilder.STATIC_MCP_CONFIGS

    def __init__(self, config=None):
        """Initialize the MCP configuration manager.

        Args:
            config: Optional ``Config`` object for filtering services.
        """
        self.logger = get_logger(__name__)
        self.pipx_base = Path.home() / ".local" / "pipx" / "venvs"
        self.project_root = Path.cwd()

        # Validate config type if provided
        if config is not None:
            from ..core.config import Config

            if not isinstance(config, Config):
                self.logger.warning(
                    f"Invalid config type provided to MCPConfigManager: "
                    f"{type(config).__name__}. Expected Config. "
                    f"Proceeding with config=None (all services enabled)."
                )
                config = None

        self.config = config
        self.claude_config_path = ConfigLocation.CLAUDE_JSON.value

        # Compose the decomposed services
        self._locator = MCPServiceLocator(
            pipx_base=self.pipx_base, project_root=self.project_root
        )
        self._builder = MCPServiceConfigBuilder(
            self._locator, project_root=self.project_root
        )
        self._installer = MCPServiceInstaller(self._locator)
        self._health = MCPServiceHealthManager(self._locator, self._installer)
        self._file_mgr = MCPConfigFileManager(
            self._builder,
            self._installer,
            get_filtered_services=self.get_filtered_services,
            project_root=self.project_root,
            claude_config_path=self.claude_config_path,
        )

    # ------------------------------------------------------------------ #
    # Filtering / orchestration (kept inline -- thin coordination logic) #
    # ------------------------------------------------------------------ #

    def should_enable_service(self, service_name: str) -> bool:
        """Check if an MCP service should be enabled based on startup config.

        Args:
            service_name: Name of the MCP service

        Returns:
            True if the service should be enabled, False otherwise.
        """
        if self.config is None:
            return True

        from ..core.config import Config

        if not isinstance(self.config, Config):
            self.logger.warning(
                f"Invalid config type: {type(self.config).__name__}, "
                f"expected Config. Enabling all services by default."
            )
            return True

        enabled_services = self.config.get("startup.enabled_mcp_services", None)

        if enabled_services is None:
            return True

        is_enabled = service_name in enabled_services

        if not is_enabled:
            self.logger.debug(
                f"MCP service '{service_name}' disabled by startup configuration"
            )

        return is_enabled

    def filter_services_by_mcp_flag(
        self, mcp_flag: str | None, all_services: dict[str, dict]
    ) -> dict[str, dict]:
        """Filter MCP services based on the ``--mcp`` command line flag.

        Args:
            mcp_flag: Comma-separated list of service names, or None for all
            all_services: Dict of all available service configurations

        Returns:
            Filtered dict of service configurations.
        """
        if not mcp_flag:
            return all_services

        requested_services = {s.strip() for s in mcp_flag.split(",") if s.strip()}

        filtered = {}
        for name, config in all_services.items():
            if name in requested_services:
                filtered[name] = config
            else:
                self.logger.debug(f"MCP service '{name}' excluded by --mcp flag")

        available = set(all_services.keys())
        missing = requested_services - available
        if missing:
            self.logger.warning(
                f"Requested MCP services not available: {', '.join(missing)}"
            )

        return filtered

    def list_available_services(self) -> list[str]:
        """List all available MCP services from registry and static configs."""
        services = set(self.STATIC_MCP_CONFIGS.keys())

        try:
            from .mcp_service_registry import MCPServiceRegistry

            services.update(MCPServiceRegistry.list_names())
        except ImportError:
            pass

        return sorted(services)

    def get_filtered_services(self) -> dict[str, dict]:
        """Get all MCP service configurations filtered by startup configuration.

        Returns:
            Dictionary of service configurations, filtered based on startup
            settings.
        """
        filtered_services: dict[str, dict] = {}

        for service_name in self.STATIC_MCP_CONFIGS:
            if self.should_enable_service(service_name):
                service_config = self._builder.get_static_service_config(service_name)
                if service_config:
                    filtered_services[service_name] = service_config

        return filtered_services

    # ------------------------------------------------------------------ #
    # Delegations to MCPServiceLocator                                   #
    # ------------------------------------------------------------------ #

    def detect_service_path(self, service_name: str) -> str | None:
        """Detect the best path for an MCP service. See ``MCPServiceLocator``."""
        return self._locator.detect_service_path(service_name)

    def _check_pipx_installation(self, service_name: str) -> str | None:
        return self._locator._check_pipx_installation(service_name)

    def _check_uv_tool_installation(self, service_name: str) -> str | None:
        return self._locator._check_uv_tool_installation(service_name)

    def _check_system_path(self, service_name: str) -> str | None:
        return self._locator._check_system_path(service_name)

    def _check_local_venv(self, service_name: str) -> str | None:
        return self._locator._check_local_venv(service_name)

    # ------------------------------------------------------------------ #
    # Delegations to MCPServiceConfigBuilder                             #
    # ------------------------------------------------------------------ #

    def get_registry_service_config(
        self, service_name: str, env_overrides: dict[str, str] | None = None
    ) -> dict | None:
        """Get config from MCP Service Registry. See ``MCPServiceConfigBuilder``."""
        return self._builder.get_registry_service_config(service_name, env_overrides)

    def get_static_service_config(
        self, service_name: str, project_path: str | None = None
    ) -> dict | None:
        """Get static service config. See ``MCPServiceConfigBuilder``."""
        return self._builder.get_static_service_config(service_name, project_path)

    def generate_service_config(self, service_name: str) -> dict | None:
        """Generate service config. See ``MCPServiceConfigBuilder``."""
        return self._builder.generate_service_config(service_name)

    def test_service_command(self, service_name: str, config: dict) -> bool:
        """Test if a service configuration works. See ``MCPServiceConfigBuilder``."""
        return self._builder.test_service_command(service_name, config)

    def _get_fallback_config(self, service_name: str, project_path: str) -> dict | None:
        return self._builder.get_fallback_config(service_name, project_path)

    # ------------------------------------------------------------------ #
    # Delegations to MCPConfigFileManager                                #
    # ------------------------------------------------------------------ #

    def check_mcp_services_available(self) -> tuple[bool, str]:
        """Check available MCP services in ``~/.claude.json`` (read-only)."""
        return self._file_mgr.check_mcp_services_available()

    def ensure_mcp_services_configured(self) -> tuple[bool, str]:
        """DEPRECATED: see :meth:`check_mcp_services_available`."""
        return self._file_mgr.ensure_mcp_services_configured()

    def update_mcp_config(self, _force_pipx: bool = True) -> tuple[bool, str]:  # pyright: ignore[reportUnusedParameter]
        """DEPRECATED: see :meth:`check_mcp_services_available`."""
        return self._file_mgr.update_mcp_config(_force_pipx)

    def update_project_mcp_config(self, force_pipx: bool = True) -> tuple[bool, str]:
        """Update legacy ``.mcp.json``. See ``MCPConfigFileManager``."""
        return self._file_mgr.update_project_mcp_config(force_pipx)

    def validate_configuration(self) -> dict[str, bool]:
        """Validate configured services. See ``MCPConfigFileManager``."""
        return self._file_mgr.validate_configuration()

    # ------------------------------------------------------------------ #
    # Delegations to MCPServiceInstaller                                 #
    # ------------------------------------------------------------------ #

    def install_missing_services(self) -> tuple[bool, str]:
        """Install missing MCP services. See ``MCPServiceInstaller``."""
        return self._installer.install_missing_services()

    def _install_service_with_fallback(self, service_name: str) -> tuple[bool, str]:
        return self._installer._install_service_with_fallback(service_name)

    def _inject_missing_dependencies(self, service_name: str) -> bool:
        return self._installer.inject_missing_dependencies(service_name)

    def _verify_service_installed(self, service_name: str, method: str) -> bool:
        return self._installer._verify_service_installed(service_name, method)

    # ------------------------------------------------------------------ #
    # Delegations to MCPServiceHealthManager                             #
    # ------------------------------------------------------------------ #

    def fix_mcp_service_issues(self) -> tuple[bool, str]:
        """Detect and repair MCP service issues. See ``MCPServiceHealthManager``."""
        return self._health.fix_mcp_service_issues()

    def _detect_service_issue(self, service_name: str) -> str | None:
        return self._health._detect_service_issue(service_name)

    def _reinstall_service(self, service_name: str) -> bool:
        return self._health._reinstall_service(service_name)

    def _auto_reinstall_mcp_service(self, service_name: str) -> bool:
        return self._health._auto_reinstall_mcp_service(service_name)
