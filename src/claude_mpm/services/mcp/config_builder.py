"""
MCP Service Config Builder
==========================

Generates MCP service configurations, preferring static known-good configs
and falling back to runtime detection (pipx run, uvx, direct binaries).

Extracted from MCPConfigManager as part of god-class decomposition (#507).

References
----------
SPEC-INTEGRATIONS-04~1 : docs/specs/integrations.md#SPEC-INTEGRATIONS-04~1
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - Required for MCP service config validation
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ...core.logger import get_logger

if TYPE_CHECKING:
    from .service_locator import MCPServiceLocator


class MCPServiceConfigBuilder:
    """Build MCP service configuration dicts from static templates or detection.

    Depends on an :class:`MCPServiceLocator` for executable discovery.

    :spec: SPEC-INTEGRATIONS-04~1
    """

    # Static known-good MCP service configurations.
    # These are the correct, tested configurations that work reliably.
    # Commands will be resolved to full paths dynamically.
    STATIC_MCP_CONFIGS: dict[str, dict[str, Any]] = {
        "kuzu-memory": {
            "type": "stdio",
            "command": "kuzu-memory",
            "args": ["mcp", "serve"],
        },
        "mcp-ticketer": {
            "type": "stdio",
            "command": "mcp-ticketer",
            "args": ["mcp"],
        },
        "mcp-browser": {
            "type": "stdio",
            "command": "mcp-browser",
            "args": ["mcp"],
            "env": {"MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")},
        },
        "mcp-vector-search": {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "mcp_vector_search.mcp.server", "{project_root}"],
            "env": {},
        },
        "trusty-search": {
            "type": "stdio",
            "command": "trusty-search",
            "args": ["serve"],
        },
        "trusty-memory": {
            "type": "stdio",
            "command": "trusty-memory",
            "args": ["serve", "--stdio"],
        },
        "trusty-analyze": {
            "type": "stdio",
            "command": "trusty-analyze",
            "args": ["mcp"],
        },
        # Review-on-demand MCP server. ``env`` carries ONLY non-secret config:
        # TRUSTY_REVIEW_AUTH_MODE=cli lets a local GitHub PAT work in serve mode.
        # AWS creds / GITHUB_TOKEN are inherited from the Claude Code process
        # environment and must NOT be hardcoded here.
        "trusty-review": {
            "type": "stdio",
            "command": "trusty-review",
            "args": ["serve", "--stdio"],
            "env": {"TRUSTY_REVIEW_AUTH_MODE": "cli"},
        },
    }

    def __init__(
        self,
        locator: MCPServiceLocator,
        project_root: Path | None = None,
    ) -> None:
        """Initialize the config builder.

        Args:
            locator: The :class:`MCPServiceLocator` used for executable discovery.
            project_root: Project root for substituting ``{project_root}``
                placeholders. Defaults to ``Path.cwd()``.
        """
        self.logger = get_logger(__name__)
        self.locator = locator
        self.project_root = project_root or Path.cwd()

    def get_registry_service_config(
        self, service_name: str, env_overrides: dict[str, str] | None = None
    ) -> dict | None:
        """Get configuration for a service from the MCP Service Registry.

        Args:
            service_name: Name of the service
            env_overrides: Optional environment variable overrides

        Returns:
            Service configuration dict or None if service not in registry
        """
        try:
            from ..mcp_service_registry import MCPServiceRegistry

            service = MCPServiceRegistry.get(service_name)
            if not service:
                return None

            return MCPServiceRegistry.generate_config(service, env_overrides)
        except ImportError:
            self.logger.debug("MCP Service Registry not available")
            return None

    def get_static_service_config(
        self, service_name: str, project_path: str | None = None
    ) -> dict | None:
        """Get the static, known-good configuration for an MCP service.

        Args:
            service_name: Name of the MCP service
            project_path: Optional project path to use (defaults to current project)

        Returns:
            Static service configuration dict or None if service not known
        """
        if service_name not in self.STATIC_MCP_CONFIGS:
            return None

        config = self.STATIC_MCP_CONFIGS[service_name].copy()

        # Resolve service binary commands to full paths
        if service_name in ["kuzu-memory", "mcp-ticketer", "mcp-browser"]:
            binary_name = config["command"]

            pipx_bin = (
                Path.home()
                / ".local"
                / "pipx"
                / "venvs"
                / service_name
                / "bin"
                / binary_name
            )
            if pipx_bin.exists():
                binary_path: str | None = str(pipx_bin)
            else:
                binary_path = shutil.which(binary_name)

                if not binary_path:
                    possible_paths = [
                        Path.home() / ".local" / "bin" / binary_name,
                        Path("/opt/homebrew/bin") / binary_name,
                        Path("/usr/local/bin") / binary_name,
                    ]
                    for path in possible_paths:
                        if path.exists():
                            binary_path = str(path)
                            break

            if binary_path:
                config["command"] = binary_path
            else:
                self.logger.debug(
                    f"Could not find {binary_name}, using pipx run fallback"
                )
                config["command"] = "pipx"
                config["args"] = ["run", service_name] + config["args"]

        # Resolve pipx command to full path if needed (for fallback configs)
        if config.get("command") == "pipx":
            pipx_path = shutil.which("pipx")
            if not pipx_path:
                possible_pipx_paths = [
                    Path.home() / ".local" / "bin" / "pipx",
                    Path("/opt/homebrew/bin/pipx"),
                    Path("/usr/local/bin/pipx"),
                ]
                for path in possible_pipx_paths:
                    if path.exists():
                        pipx_path = str(path)
                        break
            if pipx_path:
                config["command"] = pipx_path

        # Handle user-specific paths for mcp-vector-search
        if service_name == "mcp-vector-search":
            home = Path.home()
            python_path = (
                home
                / ".local"
                / "pipx"
                / "venvs"
                / "mcp-vector-search"
                / "bin"
                / "python"
            )

            if python_path.exists():
                config["command"] = str(python_path)
            else:
                pipx_path = shutil.which("pipx")
                if not pipx_path:
                    possible_pipx_paths = [
                        Path.home() / ".local" / "bin" / "pipx",
                        Path("/opt/homebrew/bin/pipx"),
                        Path("/usr/local/bin/pipx"),
                    ]
                    for path in possible_pipx_paths:
                        if path.exists():
                            pipx_path = str(path)
                            break

                if pipx_path:
                    config["command"] = pipx_path
                else:
                    config["command"] = "pipx"

                config["args"] = [
                    "run",
                    "--spec",
                    "mcp-vector-search",
                    "python",
                    "-m",
                    "mcp_vector_search.mcp.server",
                    "{project_root}",
                ]

            project_root = project_path if project_path else str(self.project_root)
            config["args"] = [
                (
                    arg.replace("{project_root}", project_root)
                    if "{project_root}" in arg
                    else arg
                )
                for arg in config["args"]
            ]

        return config

    def test_service_command(self, service_name: str, config: dict) -> bool:
        """Test if a service configuration actually works.

        Args:
            service_name: Name of the MCP service
            config: Service configuration to test

        Returns:
            True if service responds correctly, False otherwise
        """
        try:
            command = config["command"]

            if command == "pipx":
                pipx_path = shutil.which("pipx")
                if not pipx_path:
                    for possible_path in [
                        "/opt/homebrew/bin/pipx",
                        "/usr/local/bin/pipx",
                        str(Path.home() / ".local" / "bin" / "pipx"),
                    ]:
                        if Path(possible_path).exists():
                            command = possible_path
                            break
                else:
                    command = pipx_path

            cmd = [command]

            if "args" in config:
                test_args = config["args"].copy()
                test_args = [
                    (
                        arg.replace("{project_root}", str(self.project_root))
                        if "{project_root}" in arg
                        else arg
                    )
                    for arg in test_args
                ]

                if service_name == "mcp-vector-search":
                    cmd.extend(test_args[:2])
                    cmd.extend(["--help"])
                else:
                    cmd.extend(test_args)
                    cmd.append("--help")
            else:
                cmd.append("--help")

            result = subprocess.run(  # nosec B603 - Controlled service test command
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                env=config.get("env", {}),
            )

            if result.returncode in [0, 1]:
                if (
                    "ModuleNotFoundError" in result.stderr
                    or "ImportError" in result.stderr
                ):
                    self.logger.debug(f"Service {service_name} has import errors")
                    return False
                return True

        except subprocess.TimeoutExpired:
            # Timeout might mean the service started successfully and is waiting for input
            return True
        except Exception as e:
            self.logger.debug(f"Error testing {service_name}: {e}")

        return False

    def generate_service_config(self, service_name: str) -> dict | None:
        """Generate configuration for a specific MCP service.

        Prefers static configurations over detection. Falls back to detection
        only for unknown services.

        Args:
            service_name: Name of the MCP service

        Returns:
            Service configuration dict or None if service not found

        :spec: SPEC-INTEGRATIONS-04~1
        """
        static_config = self.get_static_service_config(service_name)
        if static_config:
            if self.test_service_command(service_name, static_config):
                self.logger.debug(
                    f"Static config for {service_name} validated successfully"
                )
                return static_config
            self.logger.warning(
                f"Static config for {service_name} failed validation, trying fallback"
            )

        # Fall back to detection-based configuration for unknown services
        use_pipx_run = False
        use_uvx = False

        if shutil.which("pipx"):
            try:
                result = subprocess.run(  # nosec B603 B607 - Controlled pipx run command
                    ["pipx", "run", service_name, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0 or "version" in result.stdout.lower():
                    use_pipx_run = True
                    self.logger.debug(f"Will use 'pipx run' for {service_name}")
            except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
                pass

        if not use_pipx_run and shutil.which("uvx"):
            try:
                result = subprocess.run(  # nosec B603 B607 - Controlled uvx command
                    ["uvx", service_name, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0 or "version" in result.stdout.lower():
                    use_uvx = True
                    self.logger.debug(f"Will use 'uvx' for {service_name}")
            except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
                pass

        service_path: str | None = None
        if not use_pipx_run and not use_uvx:
            service_path = self.locator.detect_service_path(service_name)
            if not service_path:
                return None

        config: dict[str, Any] = {"type": "stdio"}

        if service_name == "mcp-vector-search":
            if use_pipx_run:
                config["command"] = "pipx"
                config["args"] = [
                    "run",
                    "mcp-vector-search",
                    "-m",
                    "mcp_vector_search.mcp.server",
                    str(self.project_root),
                ]
            elif use_uvx:
                config["command"] = "uvx"
                config["args"] = [
                    "mcp-vector-search",
                    "-m",
                    "mcp_vector_search.mcp.server",
                    str(self.project_root),
                ]
            else:
                config["command"] = service_path
                config["args"] = [
                    "-m",
                    "mcp_vector_search.mcp.server",
                    str(self.project_root),
                ]
            config["env"] = {}

        elif service_name == "mcp-browser":
            if use_pipx_run:
                config["command"] = "pipx"
                config["args"] = ["run", "mcp-browser", "mcp"]
            elif use_uvx:
                config["command"] = "uvx"
                config["args"] = ["mcp-browser", "mcp"]
            else:
                config["command"] = service_path
                config["args"] = ["mcp"]
            config["env"] = {"MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")}

        elif service_name == "mcp-ticketer":
            if use_pipx_run:
                config["command"] = "pipx"
                config["args"] = ["run", "mcp-ticketer", "mcp"]
            elif use_uvx:
                config["command"] = "uvx"
                config["args"] = ["mcp-ticketer", "mcp"]
            else:
                config["command"] = service_path
                config["args"] = ["mcp"]

        elif service_name == "kuzu-memory":
            pipx_binary = (
                Path.home()
                / ".local"
                / "pipx"
                / "venvs"
                / "kuzu-memory"
                / "bin"
                / "kuzu-memory"
            )

            if pipx_binary.exists():
                config["command"] = str(pipx_binary)
                config["args"] = ["mcp", "serve"]
            elif use_pipx_run:
                config["command"] = "pipx"
                config["args"] = ["run", "kuzu-memory", "mcp", "serve"]
            elif use_uvx:
                config["command"] = "uvx"
                config["args"] = ["kuzu-memory", "mcp", "serve"]
            elif service_path:
                config["command"] = service_path
                config["args"] = ["mcp", "serve"]
            else:
                config["command"] = "pipx"
                config["args"] = ["run", "kuzu-memory", "mcp", "serve"]

        elif use_pipx_run:
            config["command"] = "pipx"
            config["args"] = ["run", service_name]
        elif use_uvx:
            config["command"] = "uvx"
            config["args"] = [service_name]
        else:
            config["command"] = service_path
            config["args"] = []

        return config

    def get_fallback_config(self, service_name: str, project_path: str) -> dict | None:
        """Get a fallback configuration for a service if the primary config fails.

        Args:
            service_name: Name of the MCP service
            project_path: Project path to use

        Returns:
            Fallback configuration or None
        """
        if service_name == "mcp-vector-search":
            return {
                "type": "stdio",
                "command": "pipx",
                "args": [
                    "run",
                    "--spec",
                    "mcp-vector-search",
                    "python",
                    "-m",
                    "mcp_vector_search.mcp.server",
                    project_path,
                ],
                "env": {},
            }

        return None
