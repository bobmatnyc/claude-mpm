"""MCP external services setup module.

This module handles the registration of external MCP services
(mcp-vector-search, mcp-browser) as separate MCP servers in Claude Code.
"""

import json
import subprocess
import sys
from datetime import timezone
from pathlib import Path
from typing import Dict, Optional, Tuple


class MCPExternalServicesSetup:
    """Handles setup of external MCP services in Claude Code configuration."""

    def get_project_services(self, project_path: Path) -> Dict:
        """Get external services configuration for the current project.

        Args:
            project_path: Path to the project directory

        Returns:
            Dict: Configuration for external services
        """
        # Detect best command paths for services
        mcp_browser_config = self._get_best_service_config("mcp-browser", project_path)
        mcp_vector_search_config = self._get_best_service_config(
            "mcp-vector-search", project_path
        )

        return {
            "mcp-vector-search": {
                "package_name": "mcp-vector-search",
                "module_name": "mcp_vector_search",
                "description": "Semantic code search with vector embeddings",
                "config": mcp_vector_search_config,
            },
            "mcp-browser": {
                "package_name": "mcp-browser",
                "module_name": "mcp_browser",
                "description": "Web browsing and content extraction",
                "config": mcp_browser_config,
            },
        }

    def _get_best_service_config(self, service_name: str, project_path: Path) -> Dict:
        """Get the best configuration for a service.

        Priority order:
        1. Pipx installation (preferred for isolation and reliability)
        2. Local development installation (e.g., ~/Projects/managed/)
        3. Local project venv
        4. System Python

        Args:
            service_name: Name of the service
            project_path: Path to the project directory

        Returns:
            Dict: Service configuration
        """
        # First try pipx (preferred for isolation and reliability)
        pipx_config = self._get_pipx_config(service_name, project_path)
        if pipx_config:
            # Verify the executable actually exists before using it
            command = pipx_config.get("command", "")
            if Path(command).exists():
                return pipx_config

        # Then try local development installations
        local_dev_config = self._get_local_dev_config(service_name, project_path)
        if local_dev_config:
            # Verify the command exists
            command = local_dev_config.get("command", "")
            if Path(command).exists():
                return local_dev_config

        # Then try local venv if exists
        venv_config = self._get_venv_config(service_name, project_path)
        if venv_config:
            command = venv_config.get("command", "")
            if Path(command).exists():
                return venv_config

        # Fall back to system Python
        return self._get_system_config(service_name, project_path)

    def _get_local_dev_config(
        self, service_name: str, project_path: Path
    ) -> Optional[Dict]:
        """Get configuration for a locally developed service.

        Checks common development locations like ~/Projects/managed/

        Args:
            service_name: Name of the service
            project_path: Path to the project directory

        Returns:
            Configuration dict or None if not available
        """
        # Check common local development locations
        dev_locations = [
            Path.home() / "Projects" / "managed" / service_name,
            Path.home() / "Projects" / service_name,
            Path.home() / "Development" / service_name,
            Path.home() / "dev" / service_name,
        ]

        for dev_path in dev_locations:
            if not dev_path.exists():
                continue

            # Check for venv in the development location
            venv_paths = [
                dev_path / ".venv" / "bin" / "python",
                dev_path / "venv" / "bin" / "python",
                dev_path / "env" / "bin" / "python",
            ]

            for venv_python in venv_paths:
                if venv_python.exists():
                    # Special handling for mcp-browser
                    if service_name == "mcp-browser":
                        # First check for mcp-browser binary in the same directory as python
                        mcp_browser_binary = venv_python.parent / "mcp-browser"
                        if mcp_browser_binary.exists():
                            return {
                                "type": "stdio",
                                "command": str(mcp_browser_binary),
                                "args": ["mcp"],
                                "env": {
                                    "MCP_BROWSER_HOME": str(
                                        Path.home() / ".mcp-browser"
                                    )
                                },
                            }

                        # Then check for mcp-server.py
                        mcp_server = dev_path / "mcp-server.py"
                        if mcp_server.exists():
                            return {
                                "type": "stdio",
                                "command": str(venv_python),
                                "args": [str(mcp_server)],
                                "env": {
                                    "MCP_BROWSER_HOME": str(
                                        Path.home() / ".mcp-browser"
                                    ),
                                    "PYTHONPATH": str(dev_path),
                                },
                            }

                    # Check if the package is installed in this venv
                    module_name = service_name.replace("-", "_")
                    try:
                        result = subprocess.run(
                            [str(venv_python), "-c", f"import {module_name}"],
                            capture_output=True,
                            timeout=5,
                            check=False,
                        )
                        if result.returncode == 0:
                            # Use special configuration for local dev
                            if service_name == "mcp-vector-search":
                                return {
                                    "type": "stdio",
                                    "command": str(venv_python),
                                    "args": [
                                        "-m",
                                        "mcp_vector_search.mcp.server",
                                        str(project_path),
                                    ],
                                    "env": {},
                                }
                            if service_name == "mcp-browser":
                                # Fallback for mcp-browser without mcp-server.py
                                return {
                                    "type": "stdio",
                                    "command": str(venv_python),
                                    "args": ["-m", "mcp_browser", "mcp"],
                                    "env": {
                                        "MCP_BROWSER_HOME": str(
                                            Path.home() / ".mcp-browser"
                                        ),
                                        "PYTHONPATH": str(dev_path),
                                    },
                                }
                    except Exception:
                        continue

        return None

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
                        timeout=5,
                        check=False,
                    )
                    if result.returncode == 0:
                        return self._create_service_config(
                            service_name, str(venv_python), project_path
                        )
                except Exception:
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

    def _create_service_config(
        self, service_name: str, python_path: str, project_path: Path
    ) -> Dict:
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
                    "env": {"MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")},
                }
            # Use Python module invocation
            return {
                "type": "stdio",
                "command": python_path,
                "args": ["-m", "mcp_browser", "mcp"],
                "env": {"MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")},
            }
        if service_name == "mcp-vector-search":
            return {
                "type": "stdio",
                "command": python_path,
                "args": ["-m", "mcp_vector_search.mcp.server", str(project_path)],
                "env": {},
            }
        # Generic configuration for other services
        module_name = service_name.replace("-", "_")
        return {
            "type": "stdio",
            "command": python_path,
            "args": ["-m", module_name],
            "env": {},
        }

    def detect_mcp_installations(self) -> Dict[str, Dict]:
        """Detect all MCP service installations and their locations.

        Returns:
            Dict mapping service name to installation info:
            {
                "service-name": {
                    "type": "local_dev" | "pipx" | "venv" | "system" | "not_installed",
                    "path": "/path/to/installation",
                    "config": {...}  # Ready-to-use configuration
                }
            }
        """
        installations = {}
        project_path = Path.cwd()

        for service_name in ["mcp-browser", "mcp-vector-search"]:
            # Try each detection method in priority order
            local_dev_config = self._get_local_dev_config(service_name, project_path)
            if local_dev_config:
                installations[service_name] = {
                    "type": "local_dev",
                    "path": local_dev_config["command"],
                    "config": local_dev_config,
                }
                continue

            pipx_config = self._get_pipx_config(service_name, project_path)
            if pipx_config:
                # Verify the command actually exists before reporting it as available
                command_path = Path(pipx_config["command"])
                if command_path.exists():
                    installations[service_name] = {
                        "type": "pipx",
                        "path": pipx_config["command"],
                        "config": pipx_config,
                    }
                    continue

            venv_config = self._get_venv_config(service_name, project_path)
            if venv_config:
                installations[service_name] = {
                    "type": "venv",
                    "path": venv_config["command"],
                    "config": venv_config,
                }
                continue

            # Check if available in system Python
            module_name = service_name.replace("-", "_")
            if self._check_python_package(module_name):
                system_config = self._get_system_config(service_name, project_path)
                installations[service_name] = {
                    "type": "system",
                    "path": system_config["command"],
                    "config": system_config,
                }
            else:
                installations[service_name] = {
                    "type": "not_installed",
                    "path": None,
                    "config": None,
                }

        return installations

    def update_mcp_json_with_detected(self, force: bool = False) -> bool:
        """Update .mcp.json with auto-detected service configurations.

        Args:
            force: Whether to overwrite existing configurations

        Returns:
            bool: True if configuration was updated successfully
        """
        print("\n🔍 Auto-detecting MCP service installations...")
        print("=" * 50)

        installations = self.detect_mcp_installations()

        # Display detected installations
        for service_name, info in installations.items():
            print(f"\n{service_name}:")
            if info["type"] == "not_installed":
                print("  ❌ Not installed")
            else:
                type_emoji = {
                    "local_dev": "🔧",
                    "pipx": "📦",
                    "venv": "🐍",
                    "system": "💻",
                }.get(info["type"], "❓")
                print(f"  {type_emoji} Type: {info['type']}")
                print(f"  📍 Path: {info['path']}")

        # Load current configuration
        config_path = Path.cwd() / ".mcp.json"
        config = self._load_config(config_path)
        if not config:
            print("\n❌ Failed to load configuration")
            return False

        # Update configurations
        updated = False
        for service_name, info in installations.items():
            if info["type"] == "not_installed":
                continue

            # Check if already configured
            if service_name in config.get("mcpServers", {}) and not force:
                print(
                    f"\n⚠️ {service_name} already configured, skipping (use --force to override)"
                )
                continue

            # Update configuration
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            config["mcpServers"][service_name] = info["config"]
            print(f"\n✅ Updated {service_name} configuration")
            updated = True

        # Save configuration if updated
        if updated:
            if self._save_config(config, config_path):
                print(
                    "\n✅ Successfully updated .mcp.json with detected configurations"
                )
                return True
            print("\n❌ Failed to save configuration")
            return False
        print("\n📌 No updates needed")
        return True

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
        for service_name, service_info in self.get_project_services(
            project_path
        ).items():
            if self._setup_service(config, service_name, service_info, force):
                success_count += 1

        # Save the updated configuration
        if success_count > 0:
            if self._save_config(config, config_path):
                print(
                    f"\n✅ Successfully configured {success_count} external services in .mcp.json"
                )
                print("\n📌 Note: Claude Code will automatically load these services")
                print("   when you open this project directory in Claude Code.")
                return True
            print("❌ Failed to save configuration")
            return False
        print("\n⚠️ No external services were configured")
        return False

    def _setup_service(
        self, config: Dict, service_name: str, service_info: Dict, force: bool
    ) -> bool:
        """Setup a single external MCP service.

        Args:
            config: The Claude Code configuration
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

            # Check if it's using a local development path
            command = str(existing_config.get("command", ""))
            if any(
                path in command
                for path in ["/Projects/managed/", "/Projects/", "/Development/"]
            ):
                print("   📍 Using local development version")
                response = (
                    input("   Keep local development version? (Y/n): ").strip().lower()
                )
                if response not in ["n", "no"]:
                    print(
                        f"   ✅ Keeping existing local configuration for {service_name}"
                    )
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
            print(f"   [INFO]️ Installing {service_info['package_name']}...")
            if not self._install_python_package(service_info["package_name"]):
                print(f"   ❌ Failed to install {service_info['package_name']}")
                print(
                    f"   [INFO]️ Install manually with: pip install {service_info['package_name']}"
                )
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
            ("mcp-browser", "mcp_browser"),
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
                timeout=60,
                check=False,
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
                with config_path.open() as f:
                    config = json.load(f)
                    # Ensure mcpServers key exists
                    if "mcpServers" not in config:
                        config["mcpServers"] = {}
                    return config
            else:
                # Create new configuration
                print("   📝 Creating new .mcp.json file")
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

                backup_path = (
                    config_path.parent
                    / f".mcp.backup.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
                )
                import shutil

                shutil.copy2(config_path, backup_path)
                print(f"   📁 Created backup: {backup_path}")

            # Write configuration with proper formatting
            with config_path.open("w") as f:
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
            # mcp-browser uses Python module invocation for MCP mode
            python_path = pipx_venv / "bin" / "python"
            if python_path.exists():
                # Check if module is importable
                try:
                    result = subprocess.run(
                        [str(python_path), "-c", "import mcp_browser.cli.main"],
                        capture_output=True,
                        timeout=5,
                        check=False,
                    )
                    if result.returncode == 0:
                        return {
                            "type": "stdio",
                            "command": str(python_path),
                            "args": ["-m", "mcp_browser.cli.main", "mcp"],
                            "env": {
                                "MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")
                            },
                        }
                except Exception:
                    pass
        elif package_name == "mcp-vector-search":
            # mcp-vector-search uses Python module invocation
            python_path = pipx_venv / "bin" / "python"
            if python_path.exists():
                # Check if module is importable
                try:
                    result = subprocess.run(
                        [str(python_path), "-c", "import mcp_vector_search"],
                        capture_output=True,
                        timeout=5,
                        check=False,
                    )
                    if result.returncode == 0:
                        return {
                            "type": "stdio",
                            "command": str(python_path),
                            "args": [
                                "-m",
                                "mcp_vector_search.mcp.server",
                                str(project_path),
                            ],
                            "env": {},
                        }
                except Exception:
                    pass

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
            print("\n📌 Note: Claude Code will automatically use this configuration")
            print("   when you open this project directory.")
            return True
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
                with mcp_config_path.open() as f:
                    mcp_config = json.load(f)
                print(f"\n📁 Project MCP config: {mcp_config_path}")
            except Exception:
                print("\n⚠️ Could not read project .mcp.json")
        else:
            print("\n📝 No .mcp.json found in project directory")

        # Get service configurations for this project
        services = self.get_project_services(project_path)

        for service_name, service_info in services.items():
            print(f"\n{service_name}:")
            print(f"  Description: {service_info['description']}")
            print(f"  Python Package: {service_info['package_name']}")

            # Check if configured in .mcp.json
            if mcp_config.get("mcpServers", {}).get(service_name):
                print("  Project Status: ✅ Configured in .mcp.json")
                service_config = mcp_config["mcpServers"][service_name]
                print(f"    Command: {service_config.get('command')}")
                if service_config.get("args"):
                    print(f"    Args: {service_config.get('args')}")
            else:
                print("  Project Status: ❌ Not configured in .mcp.json")

            # Check installation type
            is_installed, install_type = self._check_pipx_installation(service_name)
            if is_installed:
                if install_type == "pipx":
                    print("  Installation: ✅ Installed via pipx (recommended)")
                else:
                    print("  Installation: ✅ Installed via pip")
            else:
                print("  Installation: ❌ Not installed")
                print(f"    Install with: pipx install {service_info['package_name']}")
