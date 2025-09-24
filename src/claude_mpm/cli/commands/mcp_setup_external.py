"""MCP external services setup module.

This module handles the registration of external MCP services
(mcp-vector-search, mcp-browser) as separate MCP servers in Claude Desktop.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, List


class MCPExternalServicesSetup:
    """Handles setup of external MCP services in Claude Desktop configuration."""

    # Define external services and their configurations
    @property
    def EXTERNAL_SERVICES(self):
        """Get external services configuration with current Python executable."""
        return {
            "mcp-vector-search": {
                "package_name": "mcp-vector-search",
                "module_name": "mcp_vector_search",
                "description": "Semantic code search with vector embeddings",
                "config": {
                    "command": sys.executable,
                    "args": ["-m", "mcp_vector_search"],
                    "env": {}
                }
            },
            "mcp-browser": {
                "package_name": "mcp-browser",
                "module_name": "mcp_browser",
                "description": "Web browsing and content extraction",
                "config": {
                    "command": sys.executable,
                    "args": ["-m", "mcp_browser"],
                    "env": {}
                }
            }
        }

    def __init__(self, logger):
        """Initialize the external services setup handler."""
        self.logger = logger

    def setup_external_services(self, force: bool = False) -> bool:
        """Setup external MCP services as separate servers.

        Args:
            force: Whether to overwrite existing configurations

        Returns:
            bool: True if all services were set up successfully
        """
        print("\n📦 Setting up External MCP Services")
        print("=" * 50)

        # Get Claude Desktop config path - try multiple possible locations
        possible_paths = [
            Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",  # macOS
            Path.home() / ".config" / "Claude" / "claude_desktop_config.json",  # Linux
            Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",  # Windows
            Path.home() / ".claude" / "claude_desktop_config.json",  # Alternative
            Path.home() / ".claude.json",  # Legacy location
        ]

        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break

        if not config_path:
            # Try to create in the most appropriate location
            import platform
            system = platform.system()
            if system == "Darwin":  # macOS
                config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
            elif system == "Windows":
                config_path = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
            else:  # Linux and others
                config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

            print(f"📁 Creating new configuration at: {config_path}")

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
        for service_name, service_info in self.EXTERNAL_SERVICES.items():
            if self._setup_service(config, service_name, service_info, force):
                success_count += 1

        # Save the updated configuration
        if success_count > 0:
            if self._save_config(config, config_path):
                print(f"\n✅ Successfully configured {success_count} external services")
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
        """Load Claude Desktop configuration.

        Args:
            config_path: Path to the configuration file

        Returns:
            Optional[Dict]: Configuration dictionary or None if failed
        """
        try:
            if config_path.exists():
                with open(config_path) as f:
                    return json.load(f)
            else:
                # Create new configuration
                return {"mcpServers": {}}
        except (OSError, json.JSONDecodeError) as e:
            print(f"❌ Error loading config: {e}")
            return None

    def _save_config(self, config: Dict, config_path: Path) -> bool:
        """Save Claude Desktop configuration.

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
                backup_path = config_path.with_suffix(
                    f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                config_path.rename(backup_path)
                print(f"   📁 Created backup: {backup_path}")

            # Write configuration
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            print(f"   💾 Saved configuration to {config_path}")
            return True

        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False

    def list_external_services(self) -> None:
        """List all available external MCP services and their status."""
        print("\n📋 Available External MCP Services")
        print("=" * 50)

        # Check Claude Desktop configuration - try multiple possible locations
        possible_paths = [
            Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",  # macOS
            Path.home() / ".config" / "Claude" / "claude_desktop_config.json",  # Linux
            Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",  # Windows
            Path.home() / ".claude" / "claude_desktop_config.json",  # Alternative
            Path.home() / ".claude.json",  # Legacy location
        ]

        config_path = None
        config = {}
        for path in possible_paths:
            if path.exists():
                config_path = path
                try:
                    with open(config_path) as f:
                        config = json.load(f)
                    break
                except:
                    continue

        for service_name, service_info in self.EXTERNAL_SERVICES.items():
            print(f"\n{service_name}:")
            print(f"  Description: {service_info['description']}")
            print(f"  Python Package: {service_info['package_name']}")

            # Check if configured
            if config_path:
                if config.get("mcpServers", {}).get(service_name):
                    print(f"  Status: ✅ Configured")
                else:
                    print(f"  Status: ❌ Not configured")
            else:
                print(f"  Status: ❌ Claude Desktop not configured")

            # Check Python package
            module_name = service_info.get("module_name", service_info["package_name"].replace("-", "_"))
            if self._check_python_package(module_name):
                print(f"  Python Package: ✅ Installed")
            else:
                print(f"  Python Package: ❌ Not installed")