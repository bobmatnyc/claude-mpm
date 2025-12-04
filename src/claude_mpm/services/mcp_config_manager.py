"""
MCP Configuration Manager
========================

Manages MCP service configurations, preferring pipx installations
over local virtual environments for better isolation and management.

This module provides utilities to detect, configure, and validate
MCP service installations.
"""

import json
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..core.logger import get_logger


class ConfigLocation(Enum):
    """Enumeration of Claude configuration file locations."""

    CLAUDE_JSON = Path.home() / ".claude.json"  # Primary Claude config
    CLAUDE_DESKTOP = (
        Path.home() / ".claude" / "claude_desktop_config.json"
    )  # Not used by Claude Code
    PROJECT_MCP = ".mcp.json"  # Project-level MCP config (deprecated)


class MCPConfigManager:
    """Manages MCP service configurations with pipx preference."""

    # Standard MCP services that should use pipx
    PIPX_SERVICES = {
        "mcp-vector-search",
        "mcp-browser",
        "mcp-ticketer",
        "kuzu-memory",
    }

    # Known missing dependencies for MCP services that pipx doesn't handle automatically
    # Maps service names to list of missing dependencies that need injection
    SERVICE_MISSING_DEPENDENCIES = {
        "mcp-ticketer": [
            "gql"
        ],  # mcp-ticketer v0.1.8+ needs gql but doesn't declare it
        # Add more services here as needed, e.g.:
        # "another-service": ["dep1", "dep2"],
    }

    # Static known-good MCP service configurations
    # These are the correct, tested configurations that work reliably
    # Note: Commands will be resolved to full paths dynamically in get_static_service_config()
    STATIC_MCP_CONFIGS = {
        "kuzu-memory": {
            "type": "stdio",
            # Use full path to kuzu-memory binary from pipx venv
            # This ensures it runs with the correct Python version
            "command": "kuzu-memory",  # Will be resolved to pipx venv path
            "args": ["mcp", "serve"],  # v1.1.0+ uses 'mcp serve' command
        },
        "mcp-ticketer": {
            "type": "stdio",
            "command": "mcp-ticketer",  # Will be resolved to full path
            "args": ["mcp"],
        },
        "mcp-browser": {
            "type": "stdio",
            "command": "mcp-browser",  # Will be resolved to full path
            "args": ["mcp"],
            "env": {"MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")},
        },
        "mcp-vector-search": {
            "type": "stdio",
            # Special handling: needs Python interpreter from pipx venv
            "command": "python",  # Will be resolved to pipx venv Python
            "args": ["-m", "mcp_vector_search.mcp.server", "{project_root}"],
            "env": {},
        },
    }

    def __init__(self, config=None):
        """Initialize the MCP configuration manager.

        Args:
            config: Optional Config object for filtering services
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

        # Use the proper Claude config file location
        self.claude_config_path = ConfigLocation.CLAUDE_JSON.value

    def should_enable_service(self, service_name: str) -> bool:
        """
        Check if an MCP service should be enabled based on startup configuration.

        Args:
            service_name: Name of the MCP service

        Returns:
            True if the service should be enabled, False otherwise
        """
        # If no config provided, enable all services by default
        if self.config is None:
            return True

        # Import Config here to avoid circular import at module level
        from ..core.config import Config

        # Validate config type
        if not isinstance(self.config, Config):
            self.logger.warning(
                f"Invalid config type: {type(self.config).__name__}, "
                f"expected Config. Enabling all services by default."
            )
            return True

        # Get startup configuration
        enabled_services = self.config.get("startup.enabled_mcp_services", None)

        # If no startup preferences configured, enable all services
        if enabled_services is None:
            return True

        # Check if this service is in the enabled list
        is_enabled = service_name in enabled_services

        if not is_enabled:
            self.logger.debug(
                f"MCP service '{service_name}' disabled by startup configuration"
            )

        return is_enabled

    def detect_service_path(self, service_name: str) -> Optional[str]:
        """
        Detect the best path for an MCP service.

        Priority order:
        1. For kuzu-memory: prefer v1.1.0+ with MCP support
        2. Pipx installation (preferred)
        3. System PATH (likely from pipx or homebrew)
        4. Local venv (fallback)

        Args:
            service_name: Name of the MCP service

        Returns:
            Path to the service executable or None if not found
        """
        # Special handling for kuzu-memory - prefer v1.1.0+ with MCP support
        if service_name == "kuzu-memory":
            candidates = []

            # Check pipx installation
            pipx_path = self._check_pipx_installation(service_name)
            if pipx_path:
                candidates.append(pipx_path)

            # Check system PATH (including homebrew)
            import shutil

            system_path = shutil.which(service_name)
            if system_path and system_path not in candidates:
                candidates.append(system_path)

            # Choose the best candidate (prefer v1.1.0+ with MCP support)
            for path in candidates:
                try:
                    result = subprocess.run(
                        [path, "--help"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    # Check if this version has MCP support
                    if "claude" in result.stdout or "mcp" in result.stdout:
                        self.logger.debug(
                            f"Found kuzu-memory with MCP support at {path}"
                        )
                        return path
                except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
                    pass

            # If no MCP-capable version found, log warning but return None
            if candidates:
                self.logger.warning(
                    f"Found kuzu-memory at {candidates[0]} but it lacks MCP support. "
                    f"Upgrade to v1.1.0+ for MCP integration: pipx upgrade kuzu-memory"
                )
            return None  # Don't configure MCP for incompatible versions

        # Standard detection for other services
        # Check pipx installation first
        pipx_path = self._check_pipx_installation(service_name)
        if pipx_path:
            self.logger.debug(f"Found {service_name} via pipx: {pipx_path}")
            return pipx_path

        # Check system PATH
        system_path = self._check_system_path(service_name)
        if system_path:
            self.logger.debug(f"Found {service_name} in PATH: {system_path}")
            return system_path

        # Fallback to local venv
        local_path = self._check_local_venv(service_name)
        if local_path:
            self.logger.warning(
                f"Using local venv for {service_name} (consider installing via pipx)"
            )
            return local_path

        self.logger.debug(
            f"Service {service_name} not found - will auto-install when needed"
        )
        return None

    def _check_pipx_installation(self, service_name: str) -> Optional[str]:
        """Check if service is installed via pipx."""
        pipx_venv = self.pipx_base / service_name

        if not pipx_venv.exists():
            return None

        # Special handling for mcp-vector-search (needs Python interpreter)
        if service_name == "mcp-vector-search":
            python_bin = pipx_venv / "bin" / "python"
            if python_bin.exists() and python_bin.is_file():
                return str(python_bin)
        else:
            # Other services use direct binary
            service_bin = pipx_venv / "bin" / service_name
            if service_bin.exists() and service_bin.is_file():
                return str(service_bin)

        return None

    def _check_system_path(self, service_name: str) -> Optional[str]:
        """Check if service is available in system PATH."""
        try:
            result = subprocess.run(
                ["which", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                # Verify it's from pipx
                if "/.local/bin/" in path or "/pipx/" in path:
                    return path
        except Exception as e:
            self.logger.debug(f"Error checking system PATH: {e}")

        return None

    def _check_local_venv(self, service_name: str) -> Optional[str]:
        """Check for local virtual environment installation (fallback)."""
        # Common local development paths
        possible_paths = [
            Path.home() / "Projects" / "managed" / service_name / ".venv" / "bin",
            self.project_root / ".venv" / "bin",
            self.project_root / "venv" / "bin",
        ]

        for base_path in possible_paths:
            if service_name == "mcp-vector-search":
                python_bin = base_path / "python"
                if python_bin.exists():
                    return str(python_bin)
            else:
                service_bin = base_path / service_name
                if service_bin.exists():
                    return str(service_bin)

        return None

    def test_service_command(self, service_name: str, config: Dict) -> bool:
        """
        Test if a service configuration actually works.

        Args:
            service_name: Name of the MCP service
            config: Service configuration to test

        Returns:
            True if service responds correctly, False otherwise
        """
        try:
            import shutil

            # Build command - handle pipx PATH issues
            command = config["command"]

            # If command is pipx and not found, try common paths
            if command == "pipx":
                pipx_path = shutil.which("pipx")
                if not pipx_path:
                    # Try common pipx locations
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

            # Add test args (--help or --version)
            if "args" in config:
                # For MCP services, test with --help after the subcommand
                test_args = config["args"].copy()
                # Replace project root placeholder for testing
                test_args = [
                    (
                        arg.replace("{project_root}", str(self.project_root))
                        if "{project_root}" in arg
                        else arg
                    )
                    for arg in test_args
                ]

                # Add --help at the end
                if service_name == "mcp-vector-search":
                    # For Python module invocation, just test if Python can import the module
                    cmd.extend(test_args[:2])  # Just python -m module_name
                    cmd.extend(["--help"])
                else:
                    cmd.extend(test_args)
                    cmd.append("--help")
            else:
                cmd.append("--help")

            # Run test command with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                env=config.get("env", {}),
            )

            # Check if command executed (exit code 0 or 1 for help)
            if result.returncode in [0, 1]:
                # Additional check for import errors in stderr
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

    def get_static_service_config(
        self, service_name: str, project_path: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get the static, known-good configuration for an MCP service.

        Args:
            service_name: Name of the MCP service
            project_path: Optional project path to use (defaults to current project)

        Returns:
            Static service configuration dict or None if service not known
        """
        if service_name not in self.STATIC_MCP_CONFIGS:
            return None

        config = self.STATIC_MCP_CONFIGS[service_name].copy()
        import shutil

        # Resolve service binary commands to full paths
        if service_name in ["kuzu-memory", "mcp-ticketer", "mcp-browser"]:
            # Try to find the full path of the binary
            binary_name = config["command"]

            # First check pipx location
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
                binary_path = str(pipx_bin)
            else:
                # Try which command
                binary_path = shutil.which(binary_name)

                if not binary_path:
                    # Try common installation locations
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
                # Fall back to pipx run method if binary not found
                self.logger.debug(
                    f"Could not find {binary_name}, using pipx run fallback"
                )
                config["command"] = "pipx"
                config["args"] = ["run", service_name] + config["args"]

        # Resolve pipx command to full path if needed (for fallback configs)
        if config.get("command") == "pipx":
            pipx_path = shutil.which("pipx")
            if not pipx_path:
                # Try common pipx locations
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
            # Get the correct pipx venv path for the current user
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

            # Check if the Python interpreter exists
            if python_path.exists():
                config["command"] = str(python_path)
            else:
                # Fallback to pipx run method
                pipx_path = shutil.which("pipx")
                if not pipx_path:
                    # Try common pipx locations
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
                    config["command"] = "pipx"  # Hope it's in PATH

                # Use pipx run with the spec argument
                config["args"] = [
                    "run",
                    "--spec",
                    "mcp-vector-search",
                    "python",
                    "-m",
                    "mcp_vector_search.mcp.server",
                    "{project_root}",
                ]

            # Use provided project path or current project
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

    def generate_service_config(self, service_name: str) -> Optional[Dict]:
        """
        Generate configuration for a specific MCP service.

        Prefers static configurations over detection. Falls back to detection
        only for unknown services.

        Args:
            service_name: Name of the MCP service

        Returns:
            Service configuration dict or None if service not found
        """
        # First try to get static configuration
        static_config = self.get_static_service_config(service_name)
        if static_config:
            # Validate that the static config actually works
            if self.test_service_command(service_name, static_config):
                self.logger.debug(
                    f"Static config for {service_name} validated successfully"
                )
                return static_config
            self.logger.warning(
                f"Static config for {service_name} failed validation, trying fallback"
            )

        # Fall back to detection-based configuration for unknown services
        import shutil

        # Check for pipx run first (preferred for isolation)
        use_pipx_run = False
        use_uvx = False

        # Try pipx run test
        if shutil.which("pipx"):
            try:
                result = subprocess.run(
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

        # Try uvx if pipx run not available
        if not use_pipx_run and shutil.which("uvx"):
            try:
                result = subprocess.run(
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

        # If neither work, try to find direct path
        service_path = None
        if not use_pipx_run and not use_uvx:
            service_path = self.detect_service_path(service_name)
            if not service_path:
                return None

        # Build configuration
        config = {"type": "stdio"}

        # Service-specific configurations
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
            # For kuzu-memory, prefer using the binary from pipx venv
            # This ensures it runs with Python 3.12 instead of system Python 3.13
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
                # Use pipx venv binary directly - this runs with the correct Python
                config["command"] = str(pipx_binary)
                config["args"] = ["mcp", "serve"]
            elif use_pipx_run:
                # Fallback to pipx run
                config["command"] = "pipx"
                config["args"] = ["run", "kuzu-memory", "mcp", "serve"]
            elif use_uvx:
                # UVX fallback
                config["command"] = "uvx"
                config["args"] = ["kuzu-memory", "mcp", "serve"]
            elif service_path:
                # Direct binary path
                config["command"] = service_path
                config["args"] = ["mcp", "serve"]
            else:
                # Default fallback
                config["command"] = "pipx"
                config["args"] = ["run", "kuzu-memory", "mcp", "serve"]

        # Generic config for unknown services
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

    def check_mcp_services_available(self) -> Tuple[bool, str]:
        """
        Check if required MCP services are available in ~/.claude.json (READ-ONLY).

        This method performs a READ-ONLY check of MCP service availability.
        It does NOT modify ~/.claude.json. Users should install and configure
        MCP services themselves via pip, npx, or Claude Desktop.

        Returns:
            Tuple of (all_available: bool, message: str)
        """
        # Get services Claude MPM expects to use (from ~/.claude-mpm/config/)
        expected_services = self.get_filtered_services()

        if not expected_services:
            return True, "No MCP services configured in Claude MPM"

        # Load Claude config (read-only)
        if not self.claude_config_path.exists():
            return False, f"Claude config not found at {self.claude_config_path}"

        try:
            with self.claude_config_path.open() as f:
                claude_config = json.load(f)
        except Exception as e:
            return False, f"Failed to read Claude config: {e}"

        # Check current project
        current_project_key = str(self.project_root)
        project_config = claude_config.get("projects", {}).get(current_project_key)

        if not project_config:
            missing = list(expected_services.keys())
            return (
                False,
                f"Current project not configured in Claude. Missing services: {', '.join(missing)}",
            )

        # Check which services are missing
        mcp_servers = project_config.get("mcpServers", {})
        missing_services = [
            name for name in expected_services if name not in mcp_servers
        ]

        if missing_services:
            msg = (
                f"Missing MCP services: {', '.join(missing_services)}. "
                f"Install via: pip install {' '.join(missing_services)} "
                f"or configure in Claude Desktop"
            )
            return False, msg

        return (
            True,
            f"All required MCP services available ({len(expected_services)} services)",
        )

    def ensure_mcp_services_configured(self) -> Tuple[bool, str]:
        """
        DEPRECATED: Auto-configuring ~/.claude.json is no longer supported.

        As of v4.15.0+, MCP services are user-controlled. Users should install
        and configure MCP services themselves via:
        - pip install <service-name>
        - npx @modelcontextprotocol/...
        - Claude Desktop UI

        This method now only performs a read-only check and logs a deprecation warning.
        Use check_mcp_services_available() for read-only checks.

        Returns:
            Tuple of (success, message)
        """
        import warnings

        warnings.warn(
            "ensure_mcp_services_configured() is deprecated and will be removed in v6.0.0. "
            "MCP services are now user-controlled. Use check_mcp_services_available() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Delegate to read-only check
        return self.check_mcp_services_available()

    def update_mcp_config(self, force_pipx: bool = True) -> Tuple[bool, str]:
        """
        DEPRECATED: Check MCP configuration in ~/.claude.json (READ-ONLY).

        This method no longer modifies ~/.claude.json. Users should install
        and configure MCP services themselves.

        Args:
            force_pipx: Ignored (kept for backward compatibility)

        Returns:
            Tuple of (success, message) from read-only check
        """
        # Delegate to read-only check
        return self.check_mcp_services_available()

    def update_project_mcp_config(self, force_pipx: bool = True) -> Tuple[bool, str]:
        """
        Update the .mcp.json configuration file (legacy method).

        Args:
            force_pipx: If True, only use pipx installations

        Returns:
            Tuple of (success, message)
        """
        mcp_config_path = self.project_root / ConfigLocation.PROJECT_MCP.value

        # Load existing config if it exists
        existing_config = {}
        if mcp_config_path.exists():
            try:
                with mcp_config_path.open() as f:
                    existing_config = json.load(f)
            except Exception as e:
                self.logger.error(f"Error reading existing config: {e}")

        # Generate new configurations
        new_config = {"mcpServers": {}}
        missing_services = []

        for service_name in self.PIPX_SERVICES:
            config = self.generate_service_config(service_name)
            if config:
                new_config["mcpServers"][service_name] = config
            elif force_pipx:
                missing_services.append(service_name)
            # Keep existing config if not forcing pipx
            elif service_name in existing_config.get("mcpServers", {}):
                new_config["mcpServers"][service_name] = existing_config["mcpServers"][
                    service_name
                ]

        # Add any additional services from existing config
        for service_name, config in existing_config.get("mcpServers", {}).items():
            if service_name not in new_config["mcpServers"]:
                new_config["mcpServers"][service_name] = config

        # Write the updated configuration
        try:
            with mcp_config_path.open("w") as f:
                json.dump(new_config, f, indent=2)

            if missing_services:
                message = f"Updated .mcp.json. Missing services (install via pipx): {', '.join(missing_services)}"
                return True, message
            return True, "Successfully updated .mcp.json with pipx paths"
        except Exception as e:
            return False, f"Failed to update .mcp.json: {e}"

    def validate_configuration(self) -> Dict[str, bool]:
        """
        Validate that all configured MCP services are accessible.

        Returns:
            Dict mapping service names to availability status
        """
        project_key = str(self.project_root)

        # Check Claude config
        if not self.claude_config_path.exists():
            # Also check legacy .mcp.json
            mcp_config_path = self.project_root / ConfigLocation.PROJECT_MCP.value
            if mcp_config_path.exists():
                try:
                    with mcp_config_path.open() as f:
                        config = json.load(f)
                        results = {}
                        for service_name, service_config in config.get(
                            "mcpServers", {}
                        ).items():
                            command_path = service_config.get("command", "")
                            results[service_name] = Path(command_path).exists()
                        return results
                except Exception:
                    pass
            return {}

        try:
            with self.claude_config_path.open() as f:
                claude_config = json.load(f)

            # Get project's MCP servers
            if "projects" in claude_config and project_key in claude_config["projects"]:
                mcp_servers = claude_config["projects"][project_key].get(
                    "mcpServers", {}
                )
                results = {}
                for service_name, service_config in mcp_servers.items():
                    command_path = service_config.get("command", "")
                    results[service_name] = Path(command_path).exists()
                return results
        except Exception as e:
            self.logger.error(f"Error reading config: {e}")

        return {}

    def install_missing_services(self) -> Tuple[bool, str]:
        """
        Install missing MCP services via pipx with verification and fallbacks.

        Returns:
            Tuple of (success, message)
        """
        missing = []
        for service_name in self.PIPX_SERVICES:
            if not self.detect_service_path(service_name):
                missing.append(service_name)

        if not missing:
            return True, "All MCP services are already installed"

        installed = []
        failed = []

        for service_name in missing:
            # Try pipx install first
            success, method = self._install_service_with_fallback(service_name)
            if success:
                installed.append(f"{service_name} ({method})")
                self.logger.info(f"Successfully installed {service_name} via {method}")
            else:
                failed.append(service_name)
                self.logger.error(f"Failed to install {service_name}")

        if failed:
            return False, f"Failed to install: {', '.join(failed)}"
        if installed:
            return True, f"Successfully installed: {', '.join(installed)}"
        return True, "No services needed installation"

    def _install_service_with_fallback(self, service_name: str) -> Tuple[bool, str]:
        """
        Install a service with multiple fallback methods.

        Returns:
            Tuple of (success, installation_method)
        """
        import shutil

        # Method 1: Try pipx install
        if shutil.which("pipx"):
            try:
                self.logger.debug(f"Attempting to install {service_name} via pipx...")
                result = subprocess.run(
                    ["pipx", "install", service_name],
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout
                    check=False,
                )

                if result.returncode == 0:
                    # Inject any missing dependencies if needed
                    if service_name in self.SERVICE_MISSING_DEPENDENCIES:
                        self.logger.debug(
                            f"Injecting missing dependencies for newly installed {service_name}..."
                        )
                        self._inject_missing_dependencies(service_name)

                    # Verify installation worked
                    if self._verify_service_installed(service_name, "pipx"):
                        return True, "pipx"

                    self.logger.warning(
                        f"pipx install succeeded but verification failed for {service_name}"
                    )
                else:
                    self.logger.debug(f"pipx install failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                self.logger.warning(f"pipx install timed out for {service_name}")
            except Exception as e:
                self.logger.debug(f"pipx install error: {e}")

        # Method 2: Try uvx (if available)
        if shutil.which("uvx"):
            try:
                self.logger.debug(f"Attempting to install {service_name} via uvx...")
                result = subprocess.run(
                    ["uvx", "install", service_name],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )

                if result.returncode == 0:
                    if self._verify_service_installed(service_name, "uvx"):
                        return True, "uvx"
            except Exception as e:
                self.logger.debug(f"uvx install error: {e}")

        # Method 3: Try pip install --user
        try:
            self.logger.debug(f"Attempting to install {service_name} via pip --user...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--user", service_name],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if result.returncode == 0:
                if self._verify_service_installed(service_name, "pip"):
                    return True, "pip --user"

                self.logger.warning(
                    f"pip install succeeded but verification failed for {service_name}"
                )
        except Exception as e:
            self.logger.debug(f"pip install error: {e}")

        return False, "none"

    # COMMENTED OUT: These functions are no longer used
    # Package maintainers should fix dependency declarations in their packages
    # Automatic dependency injection can cause conflicts and is not recommended

    # def _get_mcp_ticketer_version(self) -> Optional[str]:
    #     """Get the installed version of mcp-ticketer.
    #
    #     Returns:
    #         Version string (e.g., "0.1.8") or None if not installed
    #     """
    #     try:
    #         result = subprocess.run(
    #             ["pipx", "runpip", "mcp-ticketer", "show", "mcp-ticketer"],
    #             capture_output=True,
    #             text=True,
    #             timeout=5,
    #             check=False,
    #         )
    #
    #         if result.returncode == 0:
    #             # Parse version from output
    #             for line in result.stdout.split("\n"):
    #                 if line.startswith("Version:"):
    #                     return line.split(":", 1)[1].strip()
    #         return None
    #     except Exception:
    #         return None
    #
    # def _check_and_fix_mcp_ticketer_dependencies(self) -> bool:
    #     """Check and fix mcp-ticketer missing gql dependency.
    #
    #     DEPRECATED: This workaround is no longer used.
    #     Package maintainers should fix dependency declarations.
    #
    #     Returns:
    #         False (no longer performs injection)
    #     """
    #     return False

    def fix_mcp_service_issues(self) -> Tuple[bool, str]:
        """
        Detect and fix corrupted MCP service installations.

        NOTE: Proactive health checking has been disabled.
        Each MCP service should stand on its own and handle its own issues.
        This function now only returns success without checking services.

        Returns:
            Tuple of (success, message)
        """
        # Services should stand on their own - no proactive health checking
        return True, "MCP services managing their own health"

    def _detect_service_issue(self, service_name: str) -> Optional[str]:
        """
        Detect what type of issue a service has.

        Returns:
            Issue type: 'not_installed', 'import_error', 'missing_dependency', 'path_issue', or None
        """
        import shutil

        # First check if pipx is available
        if not shutil.which("pipx"):
            return "not_installed"  # Can't use pipx services without pipx

        # Try to run the service with --help to detect issues
        try:
            # First check if service is installed in pipx venv
            pipx_venv_bin = self.pipx_base / service_name / "bin" / service_name
            if pipx_venv_bin.exists():
                # Test the installed version directly (has injected dependencies)
                # This avoids using pipx run which downloads a fresh cache copy without dependencies
                self.logger.debug(
                    f"    Testing {service_name} from installed pipx venv: {pipx_venv_bin}"
                )
                result = subprocess.run(
                    [str(pipx_venv_bin), "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )

                # Check for specific error patterns in installed version
                stderr_lower = result.stderr.lower()
                stdout_lower = result.stdout.lower()
                combined_output = stderr_lower + stdout_lower

                # Import errors in installed version (should be rare if dependencies injected)
                if (
                    "modulenotfounderror" in combined_output
                    or "importerror" in combined_output
                ):
                    # Check if it's specifically the gql dependency for mcp-ticketer
                    if service_name == "mcp-ticketer" and "gql" in combined_output:
                        return "missing_dependency"
                    return "import_error"

                # Path issues
                if "no such file or directory" in combined_output:
                    return "path_issue"

                # If help text appears, service is working
                if (
                    "usage:" in combined_output
                    or "help" in combined_output
                    or result.returncode in [0, 1]
                ):
                    self.logger.debug(
                        f"    {service_name} is working correctly (installed in venv)"
                    )
                    return None  # Service is working

                # Unknown issue
                if result.returncode not in [0, 1]:
                    self.logger.debug(
                        f"{service_name} returned unexpected exit code: {result.returncode}"
                    )
                    return "unknown_error"

                return None  # Default to working if no issues detected

            # Service not installed in pipx venv - use pipx run for detection
            # Note: pipx run uses cache which may not have injected dependencies
            self.logger.debug(
                f"    Testing {service_name} via pipx run (not installed in venv)"
            )
            result = subprocess.run(
                ["pipx", "run", service_name, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            # Check for specific error patterns
            stderr_lower = result.stderr.lower()
            stdout_lower = result.stdout.lower()
            combined_output = stderr_lower + stdout_lower

            # Not installed
            if (
                "no apps associated" in combined_output
                or "not found" in combined_output
            ):
                return "not_installed"

            # Import errors when using pipx run (cache version)
            if (
                "modulenotfounderror" in combined_output
                or "importerror" in combined_output
            ):
                # Don't report missing_dependency for cache version - it may be missing injected deps
                # Just report that service needs to be installed properly
                self.logger.debug(
                    f"{service_name} has import errors in pipx run cache - needs proper installation"
                )
                return "not_installed"

            # Path issues
            if "no such file or directory" in combined_output:
                return "path_issue"

            # If help text appears, service is working
            if (
                "usage:" in combined_output
                or "help" in combined_output
                or result.returncode in [0, 1]
            ):
                return None  # Service is working

            # Unknown issue
            if result.returncode not in [0, 1]:
                return "unknown_error"

        except subprocess.TimeoutExpired:
            # Timeout might mean service is actually working but waiting for input
            return None
        except Exception as e:
            self.logger.debug(f"Error detecting issue for {service_name}: {e}")
            return "unknown_error"

        return None

    def _reinstall_service(self, service_name: str) -> bool:
        """
        Reinstall a corrupted MCP service.

        Args:
            service_name: Name of the service to reinstall

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Uninstalling {service_name}...")

            # First uninstall the corrupted version
            uninstall_result = subprocess.run(
                ["pipx", "uninstall", service_name],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            # Don't check return code - uninstall might fail if partially corrupted
            self.logger.debug(f"Uninstall result: {uninstall_result.returncode}")

            # Now reinstall
            self.logger.debug(f"Installing fresh {service_name}...")
            install_result = subprocess.run(
                ["pipx", "install", service_name],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if install_result.returncode == 0:
                # Inject any missing dependencies if needed
                if service_name in self.SERVICE_MISSING_DEPENDENCIES:
                    self.logger.debug(
                        f"Injecting missing dependencies for {service_name}..."
                    )
                    self._inject_missing_dependencies(service_name)

                # Verify the reinstall worked
                issue = self._detect_service_issue(service_name)
                if issue is None:
                    self.logger.info(f"✅ Successfully reinstalled {service_name}")
                    return True
                self.logger.warning(
                    f"Reinstalled {service_name} but still has issue: {issue}"
                )
                return False
            self.logger.error(
                f"Failed to reinstall {service_name}: {install_result.stderr}"
            )
            return False

        except Exception as e:
            self.logger.error(f"Error reinstalling {service_name}: {e}")
            return False

    def _inject_missing_dependencies(self, service_name: str) -> bool:
        """
        Inject missing dependencies into a pipx-installed MCP service.

        Some MCP services don't properly declare all their dependencies in their
        package metadata, which causes import errors when pipx creates isolated
        virtual environments. This method injects the missing dependencies using
        pipx inject.

        Args:
            service_name: Name of the MCP service to fix

        Returns:
            True if dependencies were injected successfully or no injection needed, False otherwise
        """
        # Check if this service has known missing dependencies
        if service_name not in self.SERVICE_MISSING_DEPENDENCIES:
            return True  # No dependencies to inject

        missing_deps = self.SERVICE_MISSING_DEPENDENCIES[service_name]
        if not missing_deps:
            return True  # No dependencies to inject

        self.logger.info(
            f"  → Injecting missing dependencies for {service_name}: {', '.join(missing_deps)}"
        )

        all_successful = True
        for dep in missing_deps:
            try:
                self.logger.debug(f"    Injecting {dep} into {service_name}...")
                result = subprocess.run(
                    ["pipx", "inject", service_name, dep],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )

                if result.returncode == 0:
                    self.logger.debug(f"    ✅ Successfully injected {dep}")
                # Check if already injected (pipx will complain if package already exists)
                elif (
                    "already satisfied" in result.stderr.lower()
                    or "already installed" in result.stderr.lower()
                ):
                    self.logger.debug(f"    {dep} already present in {service_name}")
                else:
                    self.logger.error(f"    Failed to inject {dep}: {result.stderr}")
                    all_successful = False

            except subprocess.TimeoutExpired:
                self.logger.error(f"    Timeout while injecting {dep}")
                all_successful = False
            except Exception as e:
                self.logger.error(f"    Error injecting {dep}: {e}")
                all_successful = False

        return all_successful

    def _auto_reinstall_mcp_service(self, service_name: str) -> bool:
        """
        Automatically reinstall an MCP service with missing dependencies.

        This method:
        1. Uninstalls the corrupted/incomplete service
        2. Reinstalls it fresh from pipx
        3. Verifies the reinstall was successful
        4. Updates status after successful reinstall

        Args:
            service_name: Name of the MCP service to reinstall

        Returns:
            True if reinstall successful, False otherwise
        """
        try:
            import shutil

            # Verify pipx is available
            if not shutil.which("pipx"):
                self.logger.error("pipx not found - cannot auto-reinstall")
                return False

            self.logger.info(f"  → Uninstalling {service_name}...")
            uninstall_result = subprocess.run(
                ["pipx", "uninstall", service_name],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            # Log result but don't fail if uninstall had issues
            if uninstall_result.returncode != 0:
                self.logger.debug(
                    f"Uninstall had warnings (expected if corrupted): {uninstall_result.stderr}"
                )

            self.logger.info(f"  → Installing fresh {service_name}...")
            install_result = subprocess.run(
                ["pipx", "install", service_name],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if install_result.returncode != 0:
                self.logger.error(
                    f"Install failed for {service_name}: {install_result.stderr}"
                )
                return False

            # Inject any missing dependencies that pipx doesn't handle automatically
            if service_name in self.SERVICE_MISSING_DEPENDENCIES:
                self.logger.info(
                    f"  → Fixing missing dependencies for {service_name}..."
                )
                if not self._inject_missing_dependencies(service_name):
                    self.logger.warning(
                        f"Failed to inject all dependencies for {service_name}, but continuing..."
                    )

            # Verify the reinstall worked
            self.logger.debug(f"  → Verifying {service_name} installation...")
            issue = self._detect_service_issue(service_name)

            if issue is None:
                self.logger.info(f"  ✅ Successfully reinstalled {service_name}")
                return True

            # If still has missing dependency issue after injection, log specific instructions
            if issue == "missing_dependency" and service_name == "mcp-ticketer":
                self.logger.error(
                    f"  {service_name} still has missing dependencies after injection. "
                    f"Manual fix: pipx inject {service_name} gql"
                )
            else:
                self.logger.warning(
                    f"Reinstalled {service_name} but still has issue: {issue}"
                )
            return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout while reinstalling {service_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error auto-reinstalling {service_name}: {e}")
            return False

    def _verify_service_installed(self, service_name: str, method: str) -> bool:
        """
        Verify that a service was successfully installed and is functional.

        Args:
            service_name: Name of the service
            method: Installation method used

        Returns:
            True if service is installed and functional
        """
        import time

        # Give the installation a moment to settle
        time.sleep(1)

        # Note: mcp-ticketer dependency fix is now handled once in ensure_mcp_services_configured()
        # to avoid running the same pipx inject command multiple times

        # Check if we can find the service
        service_path = self.detect_service_path(service_name)
        if not service_path:
            # Try pipx run as fallback for pipx installations
            if method == "pipx":
                try:
                    result = subprocess.run(
                        ["pipx", "run", service_name, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    )
                    if result.returncode == 0 or "version" in result.stdout.lower():
                        self.logger.debug(f"{service_name} accessible via 'pipx run'")
                        return True
                except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
                    pass
            return False

        # Try to verify it works
        try:
            # Different services may need different verification
            test_commands = [
                [service_path, "--version"],
                [service_path, "--help"],
            ]

            for cmd in test_commands:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )

                output = (result.stdout + result.stderr).lower()
                # Check for signs of success
                if result.returncode == 0:
                    return True
                # Some tools return non-zero but still work
                if any(
                    indicator in output
                    for indicator in ["version", "usage", "help", service_name.lower()]
                ):
                    # Make sure it's not an error message
                    if not any(
                        error in output
                        for error in ["error", "not found", "traceback", "no such"]
                    ):
                        return True
        except Exception as e:
            self.logger.debug(f"Verification error for {service_name}: {e}")

        return False

    def _get_fallback_config(
        self, service_name: str, project_path: str
    ) -> Optional[Dict]:
        """
        Get a fallback configuration for a service if the primary config fails.

        Args:
            service_name: Name of the MCP service
            project_path: Project path to use

        Returns:
            Fallback configuration or None
        """
        # Special fallback for mcp-vector-search using pipx run
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

        # For other services, try pipx run
        return None

    def get_filtered_services(self) -> Dict[str, Dict]:
        """Get all MCP service configurations filtered by startup configuration.

        Returns:
            Dictionary of service configurations, filtered based on startup settings
        """
        filtered_services = {}

        for service_name in self.STATIC_MCP_CONFIGS:
            if self.should_enable_service(service_name):
                # Get the actual service configuration with proper paths
                service_config = self.get_static_service_config(service_name)
                if service_config:
                    filtered_services[service_name] = service_config
                    # Removed noisy debug logging that was called multiple times per startup

        return filtered_services
