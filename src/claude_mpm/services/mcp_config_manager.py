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
from datetime import datetime, timezone
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

    # Static known-good MCP service configurations
    # These are the correct, tested configurations that work reliably
    STATIC_MCP_CONFIGS = {
        "kuzu-memory": {
            "type": "stdio",
            "command": "pipx",
            "args": ["run", "kuzu-memory", "mcp", "serve"]
        },
        "mcp-ticketer": {
            "type": "stdio",
            "command": "pipx",
            "args": ["run", "mcp-ticketer", "mcp"]
        },
        "mcp-browser": {
            "type": "stdio",
            "command": "pipx",
            "args": ["run", "mcp-browser", "mcp"],
            "env": {"MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")}
        },
        "mcp-vector-search": {
            "type": "stdio",
            "command": "pipx",
            "args": ["run", "mcp-vector-search", "-m", "mcp_vector_search.mcp.server", "{project_root}"],
            "env": {}
        }
    }

    def __init__(self):
        """Initialize the MCP configuration manager."""
        self.logger = get_logger(__name__)
        self.pipx_base = Path.home() / ".local" / "pipx" / "venvs"
        self.project_root = Path.cwd()

        # Use the proper Claude config file location
        self.claude_config_path = ConfigLocation.CLAUDE_JSON.value

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
                except:
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

    def get_static_service_config(self, service_name: str) -> Optional[Dict]:
        """
        Get the static, known-good configuration for an MCP service.

        Args:
            service_name: Name of the MCP service

        Returns:
            Static service configuration dict or None if service not known
        """
        if service_name not in self.STATIC_MCP_CONFIGS:
            return None

        config = self.STATIC_MCP_CONFIGS[service_name].copy()

        # Special handling for mcp-vector-search: replace {project_root} placeholder
        if service_name == "mcp-vector-search":
            config["args"] = [
                arg.replace("{project_root}", str(self.project_root)) if "{project_root}" in arg else arg
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
            return static_config

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
            except:
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
            except:
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
            # Determine kuzu-memory command version
            kuzu_args = ["mcp", "serve"]  # Default to the standard v1.1.0+ format
            test_cmd = None

            if use_pipx_run:
                test_cmd = ["pipx", "run", "kuzu-memory", "--help"]
            elif use_uvx:
                test_cmd = ["uvx", "kuzu-memory", "--help"]
            elif service_path:
                test_cmd = [service_path, "--help"]

            if test_cmd:
                try:
                    result = subprocess.run(
                        test_cmd,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    )
                    # Check for MCP support in help output
                    help_output = result.stdout.lower() + result.stderr.lower()

                    # Standard version detection - look for "mcp serve" command (v1.1.0+)
                    # This is the correct format for kuzu-memory v1.1.0 and later
                    if "mcp serve" in help_output or ("mcp" in help_output and "serve" in help_output):
                        # Standard v1.1.0+ version with mcp serve command
                        kuzu_args = ["mcp", "serve"]
                    # Legacy version detection - only "serve" without "mcp"
                    elif "serve" in help_output and "mcp" not in help_output:
                        # Very old version that only has serve command
                        kuzu_args = ["serve"]
                    else:
                        # Default to the standard mcp serve format (v1.1.0+)
                        # Note: "claude mcp-server" format is deprecated and does not work
                        kuzu_args = ["mcp", "serve"]
                except Exception:
                    # Default to the standard mcp serve command on any error
                    kuzu_args = ["mcp", "serve"]

            if use_pipx_run:
                config["command"] = "pipx"
                config["args"] = ["run", "kuzu-memory"] + kuzu_args
            elif use_uvx:
                config["command"] = "uvx"
                config["args"] = ["kuzu-memory"] + kuzu_args
            else:
                config["command"] = service_path
                config["args"] = kuzu_args

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

    def ensure_mcp_services_configured(self) -> Tuple[bool, str]:
        """
        Ensure MCP services are configured correctly in ~/.claude.json on startup.

        This method checks ALL projects in ~/.claude.json and ensures each has
        the correct, static MCP service configurations. It will:
        1. Add missing services
        2. Fix incorrect configurations
        3. Update all projects, not just the current one

        Returns:
            Tuple of (success, message)
        """
        updated = False
        fixed_services = []
        added_services = []

        # Load existing Claude config or create minimal structure
        claude_config = {}
        if self.claude_config_path.exists():
            try:
                with open(self.claude_config_path) as f:
                    claude_config = json.load(f)
            except Exception as e:
                self.logger.error(f"Error reading {self.claude_config_path}: {e}")
                return False, f"Failed to read Claude config: {e}"

        # Ensure projects structure exists
        if "projects" not in claude_config:
            claude_config["projects"] = {}
            updated = True

        # Check and fix mcp-ticketer dependencies ONCE before processing projects
        # This avoids running the same pipx inject command 100+ times
        mcp_ticketer_fixed = False
        if "mcp-ticketer" in self.PIPX_SERVICES:
            mcp_ticketer_fixed = self._check_and_fix_mcp_ticketer_dependencies()

        # Process ALL projects in the config, not just current one
        projects_to_update = list(claude_config.get("projects", {}).keys())

        # Also add the current project if not in list
        current_project_key = str(self.project_root)
        if current_project_key not in projects_to_update:
            projects_to_update.append(current_project_key)
            # Initialize new project structure
            claude_config["projects"][current_project_key] = {
                "allowedTools": [],
                "history": [],
                "mcpContextUris": [],
                "mcpServers": {},
                "enabledMcpjsonServers": [],
                "disabledMcpjsonServers": [],
                "hasTrustDialogAccepted": False,
                "projectOnboardingSeenCount": 0,
                "hasClaudeMdExternalIncludesApproved": False,
                "hasClaudeMdExternalIncludesWarningShown": False,
            }
            updated = True

        # Update each project's MCP configurations
        for project_key in projects_to_update:
            project_config = claude_config["projects"][project_key]

            # Ensure mcpServers section exists
            if "mcpServers" not in project_config:
                project_config["mcpServers"] = {}
                updated = True

            # Check and fix each service configuration
            for service_name in self.PIPX_SERVICES:
                # Get the correct static configuration
                correct_config = self.STATIC_MCP_CONFIGS[service_name].copy()

                # Special handling for mcp-vector-search: replace {project_root} placeholder
                if service_name == "mcp-vector-search":
                    # Use the project key as the project root for each project
                    correct_config["args"] = [
                        arg.replace("{project_root}", project_key) if "{project_root}" in arg else arg
                        for arg in correct_config["args"]
                    ]

                # Check if service exists and has correct configuration
                existing_config = project_config["mcpServers"].get(service_name)

                # Determine if we need to update
                needs_update = False
                if not existing_config:
                    # Service is missing
                    needs_update = True
                    added_services.append(f"{service_name} in {Path(project_key).name}")
                else:
                    # Service exists, check if configuration is correct
                    # Compare command and args (the most critical parts)
                    if (existing_config.get("command") != correct_config.get("command") or
                        existing_config.get("args") != correct_config.get("args")):
                        needs_update = True
                        fixed_services.append(f"{service_name} in {Path(project_key).name}")

                # Update configuration if needed
                if needs_update:
                    project_config["mcpServers"][service_name] = correct_config
                    updated = True
                    self.logger.debug(
                        f"Updated MCP service config for {service_name} in project {Path(project_key).name}"
                    )

        # Write updated config if changes were made
        if updated:
            try:
                # Create backup if file exists and is large (> 100KB)
                if self.claude_config_path.exists():
                    file_size = self.claude_config_path.stat().st_size
                    if file_size > 100000:  # 100KB
                        backup_path = self.claude_config_path.with_suffix(
                            f".backup.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
                        )
                        import shutil
                        shutil.copy2(self.claude_config_path, backup_path)
                        self.logger.debug(f"Created backup: {backup_path}")

                # Write updated config
                with open(self.claude_config_path, "w") as f:
                    json.dump(claude_config, f, indent=2)

                messages = []
                if added_services:
                    messages.append(f"Added MCP services: {', '.join(added_services[:3])}")
                if fixed_services:
                    messages.append(f"Fixed MCP services: {', '.join(fixed_services[:3])}")

                if messages:
                    return True, "; ".join(messages)
                return True, "All MCP services already configured correctly"
            except Exception as e:
                self.logger.error(f"Failed to write Claude config: {e}")
                return False, f"Failed to write configuration: {e}"

        return True, "All MCP services already configured correctly"

    def update_mcp_config(self, force_pipx: bool = True) -> Tuple[bool, str]:
        """
        Update the MCP configuration in ~/.claude.json.

        Args:
            force_pipx: If True, only use pipx installations

        Returns:
            Tuple of (success, message)
        """
        # This method now delegates to ensure_mcp_services_configured
        # since we're updating the Claude config directly
        return self.ensure_mcp_services_configured()

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
                with open(mcp_config_path) as f:
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
            with open(mcp_config_path, "w") as f:
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
                    with open(mcp_config_path) as f:
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
            with open(self.claude_config_path) as f:
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

    def _check_and_fix_mcp_ticketer_dependencies(self) -> bool:
        """Check and fix mcp-ticketer missing gql dependency.

        Note: This is a workaround for mcp-ticketer <= 0.1.8 which is missing
        the gql dependency in its package metadata. Future versions (> 0.1.8)
        should include 'gql[httpx]>=3.0.0' as a dependency, making this fix
        unnecessary. We keep this for backward compatibility with older versions.
        """
        try:
            # Test if gql is available in mcp-ticketer's environment
            test_result = subprocess.run(
                ["pipx", "run", "--spec", "mcp-ticketer", "python", "-c", "import gql"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            # If import fails, inject the dependency
            if test_result.returncode != 0:
                self.logger.info("🔧 mcp-ticketer missing gql dependency, fixing...")

                inject_result = subprocess.run(
                    ["pipx", "inject", "mcp-ticketer", "gql"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )

                if inject_result.returncode == 0:
                    self.logger.info("✅ Successfully injected gql dependency into mcp-ticketer")
                    return True
                else:
                    self.logger.warning(f"Failed to inject gql: {inject_result.stderr}")
                    return False

            return False

        except Exception as e:
            self.logger.debug(f"Could not check/fix mcp-ticketer dependencies: {e}")
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
                except:
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
