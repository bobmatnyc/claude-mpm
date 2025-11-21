"""MCP install command implementations.

This module provides MCP installation and configuration commands.
Extracted from mcp.py to reduce complexity and improve maintainability.
"""

import subprocess
import sys
from pathlib import Path


class MCPInstallCommands:
    """Handles MCP install commands."""

    def __init__(self, logger):
        """Initialize the MCP install commands handler."""
        self.logger = logger

    def install_gateway(self, args):
        """Install and configure MCP gateway.

        WHY: This command installs the MCP package dependencies and configures
        Claude Code to use the MCP gateway server directly via the CLI command.

        DESIGN DECISION: We handle both package installation and configuration
        in one command for user convenience, using the new direct CLI approach.
        """
        self.logger.info("MCP gateway installation command called")
        print("📦 Installing and Configuring MCP Gateway")
        print("=" * 50)

        # Step 1: Install MCP package if needed
        print("\n1️⃣  Checking MCP package installation...")
        import importlib.util

        mcp_spec = importlib.util.find_spec("mcp")
        if mcp_spec:
            print("✅ MCP package already installed")
        else:
            print("📦 Installing MCP package...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
                print("✅ MCP package installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"❌ Error installing MCP package: {e}")
                print("\nPlease install manually with: pip install mcp")
                return 1

        # Step 2: Configure Claude Code with the new CLI command
        print("\n2️⃣  Configuring Claude Code...")
        try:
            success = self._configure_claude_desktop(args.force)
            if not success:
                print("❌ Main gateway configuration failed")
                return 1

            # Step 3: Setup external MCP services
            print("\n3️⃣  Setting up External MCP Services...")
            from .mcp_setup_external import MCPExternalServicesSetup

            external_setup = MCPExternalServicesSetup(self.logger)

            # Check if user wants to set up external services
            response = (
                input(
                    "\nDo you want to set up external MCP services (mcp-vector-search, mcp-browser)? (Y/n): "
                )
                .strip()
                .lower()
            )
            if response in ["", "y", "yes"]:
                # Install Python packages for external services
                external_setup.check_and_install_pip_packages()

                # Setup external services in Claude Code config
                if external_setup.setup_external_services(force=args.force):
                    print("✅ External services configured successfully")
                else:
                    print("⚠️ Some external services may not have been configured")
            else:
                print("⏭️ Skipping external services setup")
                print(
                    "   You can set them up later with: claude-mpm mcp external setup"
                )

            print("\n✅ Configuration completed successfully")
            print("\n🎉 MCP Gateway is ready to use!")
            print("\nNext steps:")
            print("1. Restart Claude Code (if running)")
            print("2. Test the server: claude-mpm mcp server --test")
            print("3. Check status: claude-mpm mcp status")
            print("4. List external services: claude-mpm mcp external list")
            return 0

        except Exception as e:
            print(f"❌ Error during configuration: {e}")
            return 1

    def _configure_claude_desktop(self, force=False):
        """Configure Claude Code to use the MCP gateway via CLI command.

        WHY: Claude Code reads MCP server configurations from a platform-specific
        configuration file. This method updates that file to include the claude-mpm-gateway
        server configuration.

        Args:
            force: Whether to overwrite existing configuration

        Returns:
            bool: True if configuration was successful
        """

        # Determine Claude Code config path
        config_path = self._get_claude_config_path()
        if not config_path:
            print("❌ Could not determine Claude Code configuration path")
            return False

        print(f"   Configuration path: {config_path}")

        # Load existing configuration or create new one
        config = self._load_or_create_config(config_path, force)
        if config is None:
            return False

        # Configure the claude-mpm-gateway server using the CLI command
        claude_mpm_path = self._find_claude_mpm_executable()
        if not claude_mpm_path:
            print("❌ Could not find claude-mpm executable")
            return False

        # Determine if we need to use -m claude_mpm or direct command
        if claude_mpm_path.endswith(("python", "python3", "python.exe", "python3.exe")):
            # Using Python interpreter directly
            mcp_config = {
                "command": claude_mpm_path,
                "args": ["-m", "claude_mpm", "mcp", "server"],
                "env": {
                    "PYTHONPATH": str(Path(__file__).parent.parent.parent.parent),
                    "MCP_MODE": "production",
                },
            }
        else:
            # Using installed claude-mpm command
            mcp_config = {
                "command": claude_mpm_path,
                "args": ["mcp", "server"],
                "env": {
                    "PYTHONPATH": str(Path(__file__).parent.parent.parent.parent),
                    "MCP_MODE": "production",
                },
            }

        # Update configuration
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"]["claude-mpm-gateway"] = mcp_config

        print("\n✅ Configured claude-mpm-gateway server:")
        print(f"   Command: {mcp_config['command']}")
        print(f"   Args: {mcp_config['args']}")
        print(f"   Environment variables: {list(mcp_config['env'].keys())}")

        # Save configuration
        return self._save_config(config, config_path)

    def _get_claude_config_path(self):
        """Get the Claude Code configuration file path.

        Returns:
            Path or None: Path to Claude Code config file
        """
        import platform

        # Try multiple possible locations for Claude Code config
        possible_paths = [
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json",  # macOS
            Path.home() / ".config" / "Claude" / "claude_desktop_config.json",  # Linux
            Path.home()
            / "AppData"
            / "Roaming"
            / "Claude"
            / "claude_desktop_config.json",  # Windows
            Path.home() / ".claude" / "claude_desktop_config.json",  # Alternative
            Path.home() / ".claude.json",  # Legacy
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # If none exist, return the platform-appropriate default
        system = platform.system()
        if system == "Darwin":  # macOS
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
        if system == "Windows":
            return (
                Path.home()
                / "AppData"
                / "Roaming"
                / "Claude"
                / "claude_desktop_config.json"
            )
        # Linux and others
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    def _find_claude_mpm_executable(self):
        """Find the claude-mpm executable path.

        WHY: We need to find the installed claude-mpm command to use as the
        MCP server command. This ensures we're using the properly installed
        version with all dependencies, not a raw Python script.

        DESIGN DECISION: We prioritize in this order:
        1. System-installed claude-mpm (most reliable)
        2. pipx-installed claude-mpm (detected via deployment context)
        3. Virtual environment claude-mpm (development)
        4. Python module invocation (fallback)

        Returns:
            str or None: Path to claude-mpm executable
        """
        import sys

        from ...core.unified_paths import get_executable_path

        # Use the enhanced unified path manager for executable detection
        executable_path = get_executable_path()
        if executable_path:
            print(f"   Found claude-mpm: {executable_path}")
            return str(executable_path)

        # Fallback: Use Python module invocation if no executable found
        import importlib.util

        claude_mpm_spec = importlib.util.find_spec("claude_mpm")
        if claude_mpm_spec:
            print(f"   Using Python module: {sys.executable} -m claude_mpm")
            return sys.executable

        return None

    def _load_or_create_config(self, config_path, force=False):
        """Load existing configuration or create a new one.

        Args:
            config_path: Path to configuration file
            force: Whether to overwrite existing configuration

        Returns:
            dict or None: Configuration dictionary
        """
        import json
        from datetime import datetime, timezone

        config = {}

        if config_path.exists():
            if not force:
                # Check if claude-mpm-gateway already exists
                try:
                    with config_path.open() as f:
                        existing_config = json.load(f)

                    if (
                        existing_config.get("mcpServers", {}).get("claude-mpm-gateway")
                        and not force
                    ):
                        print("⚠️  claude-mpm-gateway is already configured")
                        response = (
                            input("Do you want to overwrite it? (y/N): ")
                            .strip()
                            .lower()
                        )
                        if response not in ["y", "yes"]:
                            print("❌ Configuration cancelled")
                            return None

                    config = existing_config

                except (OSError, json.JSONDecodeError) as e:
                    print(f"⚠️  Error reading existing config: {e}")
                    print("Creating backup and starting fresh...")

                    # Create backup
                    backup_path = config_path.with_suffix(
                        f".backup.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
                    )
                    try:
                        config_path.rename(backup_path)
                        print(f"   Backup created: {backup_path}")
                    except Exception as backup_error:
                        print(f"   Warning: Could not create backup: {backup_error}")
            else:
                # Force mode - create backup but proceed
                try:
                    with config_path.open() as f:
                        existing_config = json.load(f)
                    config = existing_config
                    print("   Force mode: Overwriting existing configuration")
                except Exception:
                    pass  # File doesn't exist or is invalid, start fresh

        # Ensure mcpServers section exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        return config

    def _save_config(self, config, config_path):
        """Save configuration to file.

        Args:
            config: Configuration dictionary
            config_path: Path to save configuration

        Returns:
            bool: True if successful
        """
        import json

        try:
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write configuration with nice formatting
            with config_path.open("w") as f:
                json.dump(config, f, indent=2)

            print(f"\n✅ Configuration saved to {config_path}")
            return True

        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
            return False
