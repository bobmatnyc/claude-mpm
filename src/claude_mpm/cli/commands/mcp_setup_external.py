"""MCP external services setup module.

This module handles the registration of external MCP services
(mcp-vector-search, mcp-browser) as separate MCP servers in Claude Desktop.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple


class MCPExternalServicesSetup:
    """Handles setup of external MCP services in Claude Desktop configuration."""

    def get_project_services(self, project_path: Path) -> Dict:
        """Get external services configuration for the current project.

        Args:
            project_path: Path to the project directory

        Returns:
            Dict: Configuration for external services
        """
        # Detect best command paths for services
        mcp_browser_config = self._get_best_service_config("mcp-browser", project_path)
        mcp_vector_search_config = self._get_best_service_config("mcp-vector-search", project_path)

        return {
            "mcp-vector-search": {
                "package_name": "mcp-vector-search",
                "module_name": "mcp_vector_search",
                "description": "Semantic code search with vector embeddings",
                "config": mcp_vector_search_config
            },
            "mcp-browser": {
                "package_name": "mcp-browser",
                "module_name": "mcp_browser",
                "description": "Web browsing and content extraction",
                "config": mcp_browser_config
            }
        }

    def _get_best_service_config(self, service_name: str, project_path: Path) -> Dict:
        """Get the best configuration for a service (prefer pipx, then local venv, then system).

        Args:
            service_name: Name of the service
            project_path: Path to the project directory

        Returns:
            Dict: Service configuration
        """
        # First try pipx (preferred for isolation)
        pipx_config = self._get_pipx_config(service_name, project_path)
        if pipx_config:
            return pipx_config

        # Then try local venv if exists
        venv_config = self._get_venv_config(service_name, project_path)
        if venv_config:
            return venv_config

        # Fall back to system Python
        return self._get_system_config(service_name, project_path)

    def _get_venv_config(self, service_name: str, project_path: Path) -> Optional[Dict]:
        """Get configuration for a service in the local virtual environment.

        Args:
            service_name: Name of the service
            project_path: Path to the project directory

        Returns:
            Configuration dict or None if not available
        """
        # Check common venv locations
        venv_paths = [
            project_path / "venv" / "bin" / "python",
            project_path / ".venv" / "bin" / "python",
            project_path / "env" / "bin" / "python",
        ]

        for venv_python in venv_paths:
            if venv_python.exists():
                # Check if the package is installed in this venv
                module_name = service_name.replace("-", "_")
                try:
                    result = subprocess.run(
                        [str(venv_python), "-c", f"import {module_name}"],
                        capture_output=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        return self._create_service_config(service_name, str(venv_python), project_path)
                except:
                    continue

        return None

    def _get_system_config(self, service_name: str, project_path: Path) -> Dict:
        """Get configuration using system Python.

        Args:
            service_name: Name of the service
            project_path: Path to the project directory

        Returns:
            Configuration dict
        """
        return self._create_service_config(service_name, sys.executable, project_path)

    def _create_service_config(self, service_name: str, python_path: str, project_path: Path) -> Dict:
        """Create service configuration for the given Python executable.

        Args:
            service_name: Name of the service
            python_path: Path to Python executable
            project_path: Path to the project directory

        Returns:
            Configuration dict
        """
        if service_name == "mcp-browser":
            # Check if mcp-browser binary exists (for pipx installations)
            binary_path = Path(python_path).parent / "mcp-browser"
            if binary_path.exists():
                return {
                    "type": "stdio",
                    "command": str(binary_path),
                    "args": ["mcp"],
                    "env": {"MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")}
                }
            else:
                # Use Python module invocation
                return {
                    "type": "stdio",
                    "command": python_path,
                    "args": ["-m", "mcp_browser", "mcp"],
                    "env": {"MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")}
                }
        elif service_name == "mcp-vector-search":
            return {
                "type": "stdio",
                "command": python_path,
                "args": ["-m", "mcp_vector_search.mcp.server", str(project_path)],
                "env": {}
            }
        else:
            # Generic configuration for other services
            module_name = service_name.replace("-", "_")
            return {
                "type": "stdio",
                "command": python_path,
                "args": ["-m", module_name],
                "env": {}
            }

    def __init__(self, logger):
        """Initialize the external services setup handler."""
        self.logger = logger
        self._pipx_path = Path.home() / ".local" / "pipx" / "venvs"

    def setup_external_services(self, force: bool = False) -> bool:
        """Setup external MCP services in project .mcp.json file.

        Args:
            force: Whether to overwrite existing configurations

        Returns:
            bool: True if all services were set up successfully
        """
        print("\n📦 Setting up External MCP Services")
        print("=" * 50)

        # Use project-level .mcp.json file
        project_path = Path.cwd()
        config_path = project_path / ".mcp.json"

        print(f"📁 Project directory: {project_path}")
        print(f"📄 Using config: {config_path}")

        # Load existing configuration
        config = self._load_config(config_path)
        if config is None:
            print("❌ Failed to load configuration")
            return False

        # Ensure mcpServers section exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Setup each external service
        success_count = 0
        for service_name, service_info in self.get_project_services(project_path).items():
            if self._setup_service(config, service_name, service_info, force):
                success_count += 1

        # Save the updated configuration
        if success_count > 0:
            if self._save_config(config, config_path):
                print(f"\n✅ Successfully configured {success_count} external services in .mcp.json")
                print(f"\n📌 Note: Claude Desktop will automatically load these services")
                print(f"   when you open this project directory in Claude Desktop.")
                return True
            else:
                print("❌ Failed to save configuration")
                return False
        else:
            print("\n⚠️ No external services were configured")
            return False

    def _setup_service(
        self,
        config: Dict,
        service_name: str,
        service_info: Dict,
        force: bool
    ) -> bool:
        """Setup a single external MCP service.

        Args:
            config: The Claude Desktop configuration
            service_name: Name of the service to setup
            service_info: Service configuration information
            force: Whether to overwrite existing configuration

        Returns:
            bool: True if service was set up successfully
        """
        print(f"\n📦 Setting up {service_name}...")

        # Check if already configured
        if service_name in config["mcpServers"] and not force:
            existing_config = config["mcpServers"][service_name]
            print(f"   ⚠️ {service_name} already configured")
            print(f"      Current command: {existing_config.get('command')}")
            print(f"      Current args: {existing_config.get('args')}")

            # Check if it's using a local path
            if "/Projects/managed/" in str(existing_config.get('command', '')):
                print("   📍 Using local development version")
                response = input("   Switch to npm/npx version? (y/N): ").strip().lower()
                if response not in ["y", "yes"]:
                    print(f"   ✅ Keeping existing local configuration for {service_name}")
                    return True  # Consider it successfully configured
            else:
                response = input("   Overwrite? (y/N): ").strip().lower()
                if response not in ["y", "yes"]:
                    print(f"   ⏭️ Skipping {service_name}")
                    return False

        # Check if Python package is available
        module_name = service_info.get("module_name", service_name.replace("-", "_"))
        if not self._check_python_package(module_name):
            print(f"   ⚠️ Python package {service_info['package_name']} not installed")
            print(f"   ℹ️ Installing {service_info['package_name']}...")
            if not self._install_python_package(service_info['package_name']):
                print(f"   ❌ Failed to install {service_info['package_name']}")
                print(f"   ℹ️ Install manually with: pip install {service_info['package_name']}")
                return False

        # Add service configuration
        config["mcpServers"][service_name] = service_info["config"]
        print(f"   ✅ Configured {service_name}")
        print(f"      Command: {service_info['config']['command']}")
        print(f"      Args: {service_info['config']['args']}")
        if "env" in service_info["config"]:
            print(f"      Environment: {list(service_info['config']['env'].keys())}")

        return True


    def check_and_install_pip_packages(self) -> bool:
        """Check and install Python packages for external services.

        Returns:
            bool: True if all packages are available
        """
        print("\n🐍 Checking Python packages for external services...")

        packages_to_check = [
            ("mcp-vector-search", "mcp_vector_search"),
            ("mcp-browser", "mcp_browser")
        ]

        all_installed = True
        for package_name, module_name in packages_to_check:
            if self._check_python_package(module_name):
                print(f"   ✅ {package_name} is installed")
            else:
                print(f"   📦 Installing {package_name}...")
                if self._install_python_package(package_name):
                    print(f"   ✅ Successfully installed {package_name}")
                else:
                    print(f"   ❌ Failed to install {package_name}")
                    all_installed = False

        return all_installed

    def _check_python_package(self, module_name: str) -> bool:
        """Check if a Python package is installed.

        Args:
            module_name: Name of the module to import

        Returns:
            bool: True if package is installed
        """
        try:
            import importlib.util
            spec = importlib.util.find_spec(module_name)
            return spec is not None
        except (ImportError, ModuleNotFoundError):
            return False

    def _install_python_package(self, package_name: str) -> bool:
        """Install a Python package using pip.

        Args:
            package_name: Name of the package to install

        Returns:
            bool: True if installation was successful
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False

    def _load_config(self, config_path: Path) -> Optional[Dict]:
        """Load MCP configuration.

        Args:
            config_path: Path to the configuration file

        Returns:
            Optional[Dict]: Configuration dictionary or None if failed
        """
        try:
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    # Ensure mcpServers key exists
                    if "mcpServers" not in config:
                        config["mcpServers"] = {}
                    return config
            else:
                # Create new configuration
                print(f"   📝 Creating new .mcp.json file")
                return {"mcpServers": {}}
        except (OSError, json.JSONDecodeError) as e:
            print(f"❌ Error loading config: {e}")
            # Try to return empty config instead of None
            return {"mcpServers": {}}

    def _save_config(self, config: Dict, config_path: Path) -> bool:
        """Save MCP configuration.

        Args:
            config: Configuration dictionary
            config_path: Path to save the configuration

        Returns:
            bool: True if save was successful
        """
        try:
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Create backup if file exists
            if config_path.exists():
                from datetime import datetime
                backup_path = config_path.parent / f".mcp.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                import shutil
                shutil.copy2(config_path, backup_path)
                print(f"   📁 Created backup: {backup_path}")

            # Write configuration with proper formatting
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
                f.write("\n")  # Add newline at end of file

            print(f"   💾 Saved configuration to {config_path}")
            return True

        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False

    def _get_pipx_config(self, package_name: str, project_path: Path) -> Optional[Dict]:
        """Get configuration for a pipx-installed package.

        Args:
            package_name: Name of the package (e.g., "mcp-browser")
            project_path: Path to the project directory

        Returns:
            Configuration dict for the service or None if not found
        """
        pipx_venv = self._pipx_path / package_name
        if not pipx_venv.exists():
            return None

        if package_name == "mcp-browser":
            # mcp-browser uses 'mcp' subcommand for MCP mode
            binary_path = pipx_venv / "bin" / "mcp-browser"
            if binary_path.exists():
                return {
                    "type": "stdio",
                    "command": str(binary_path),
                    "args": ["mcp"],
                    "env": {"MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")}
                }
        elif package_name == "mcp-vector-search":
            # mcp-vector-search uses Python module invocation
            python_path = pipx_venv / "bin" / "python"
            if python_path.exists():
                return {
                    "type": "stdio",
                    "command": str(python_path),
                    "args": ["-m", "mcp_vector_search.mcp.server", str(project_path)],
                    "env": {}
                }

        return None

    def _check_pipx_installation(self, package_name: str) -> Tuple[bool, str]:
        """Check if a package is installed via pipx.

        Args:
            package_name: Name of the package to check

        Returns:
            Tuple of (is_installed, installation_type)
        """
        pipx_venv = self._pipx_path / package_name
        if pipx_venv.exists():
            return True, "pipx"

        # Check if available as Python module
        module_name = package_name.replace("-", "_")
        if self._check_python_package(module_name):
            return True, "pip"

        return False, "none"

    def fix_browser_configuration(self) -> bool:
        """Quick fix for mcp-browser configuration in project .mcp.json.

        Updates only the mcp-browser configuration in the project's .mcp.json
        to use the best available installation (pipx preferred).

        Returns:
            bool: True if configuration was updated successfully
        """
        print("\n🔧 Fixing mcp-browser Configuration")
        print("=" * 50)

        project_path = Path.cwd()
        config_path = project_path / ".mcp.json"

        print(f"📁 Project directory: {project_path}")
        print(f"📄 Using config: {config_path}")

        # Check if mcp-browser is installed
        is_installed, install_type = self._check_pipx_installation("mcp-browser")
        if not is_installed:
            print("❌ mcp-browser is not installed")
            print("   Install with: pipx install mcp-browser")
            return False

        if install_type != "pipx":
            print("⚠️ mcp-browser is not installed via pipx")
            print("   For best results, install with: pipx install mcp-browser")

        # Get best configuration for mcp-browser
        browser_config = self._get_best_service_config("mcp-browser", project_path)
        if not browser_config:
            print("❌ Could not determine mcp-browser configuration")
            return False

        # Load project configuration
        config = self._load_config(config_path)
        if not config:
            print("❌ Failed to load configuration")
            return False

        # Update mcp-browser configuration
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"]["mcp-browser"] = browser_config

        # Save configuration
        if self._save_config(config, config_path):
            print("✅ Successfully updated mcp-browser configuration in .mcp.json")
            print(f"   Command: {browser_config['command']}")
            print(f"   Args: {browser_config['args']}")
            print("\n📌 Note: Claude Desktop will automatically use this configuration")
            print("   when you open this project directory.")
            return True
        else:
            print("❌ Failed to save configuration")
            return False


    def list_external_services(self) -> None:
        """List all available external MCP services and their status."""
        print("\n📋 Available External MCP Services")
        print("=" * 50)

        # Check project-level .mcp.json
        project_path = Path.cwd()
        mcp_config_path = project_path / ".mcp.json"
        mcp_config = {}

        if mcp_config_path.exists():
            try:
                with open(mcp_config_path) as f:
                    mcp_config = json.load(f)
                print(f"\n📁 Project MCP config: {mcp_config_path}")
            except:
                print(f"\n⚠️ Could not read project .mcp.json")
        else:
            print(f"\n📝 No .mcp.json found in project directory")

        # Get service configurations for this project
        services = self.get_project_services(project_path)

        for service_name, service_info in services.items():
            print(f"\n{service_name}:")
            print(f"  Description: {service_info['description']}")
            print(f"  Python Package: {service_info['package_name']}")

            # Check if configured in .mcp.json
            if mcp_config.get("mcpServers", {}).get(service_name):
                print(f"  Project Status: ✅ Configured in .mcp.json")
                service_config = mcp_config["mcpServers"][service_name]
                print(f"    Command: {service_config.get('command')}")
                if service_config.get('args'):
                    print(f"    Args: {service_config.get('args')}")
            else:
                print(f"  Project Status: ❌ Not configured in .mcp.json")

            # Check installation type
            is_installed, install_type = self._check_pipx_installation(service_name)
            if is_installed:
                if install_type == "pipx":
                    print(f"  Installation: ✅ Installed via pipx (recommended)")
                else:
                    print(f"  Installation: ✅ Installed via pip")
            else:
                print(f"  Installation: ❌ Not installed")
                print(f"    Install with: pipx install {service_info['package_name']}")