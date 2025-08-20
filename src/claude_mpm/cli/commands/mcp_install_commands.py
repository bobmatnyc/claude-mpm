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
        try:
            import mcp
            print("✅ MCP package already installed")
        except ImportError:
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
            if success:
                print("✅ Configuration completed successfully")
                print("\n🎉 MCP Gateway is ready to use!")
                print("\nNext steps:")
                print("1. Restart Claude Code")
                print("2. Test the server: claude-mpm mcp server --test")
                print("3. Check status: claude-mpm mcp status")
                return 0
            else:
                print("❌ Configuration failed")
                return 1

        except Exception as e:
            print(f"❌ Error during configuration: {e}")
            return 1

    def _configure_claude_desktop(self, force=False):
        """Configure Claude Code to use the MCP gateway via CLI command.

        Args:
            force: Whether to overwrite existing configuration

        Returns:
            bool: True if configuration was successful
        """
        import json
        import platform
        from pathlib import Path
        from datetime import datetime

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
        if claude_mpm_path.endswith(('python', 'python3', 'python.exe', 'python3.exe')):
            # Using Python interpreter directly
            mcp_config = {
                "command": claude_mpm_path,
                "args": ["-m", "claude_mpm", "mcp", "server"],
                "env": {
                    "PYTHONPATH": str(Path(__file__).parent.parent.parent.parent),
                    "MCP_MODE": "production"
                }
            }
        else:
            # Using installed claude-mpm command
            mcp_config = {
                "command": claude_mpm_path,
                "args": ["mcp", "server"],
                "env": {
                    "PYTHONPATH": str(Path(__file__).parent.parent.parent.parent),
                    "MCP_MODE": "production"
                }
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
        from pathlib import Path

        # Claude Code uses ~/.claude/settings.local.json regardless of platform
        return Path.home() / ".claude" / "settings.local.json"

    def _find_claude_mpm_executable(self):
        """Find the claude-mpm executable path.

        WHY: We need to find the installed claude-mpm command to use as the
        MCP server command. This ensures we're using the properly installed
        version with all dependencies, not a raw Python script.

        DESIGN DECISION: We prioritize in this order:
        1. System-installed claude-mpm (most reliable)
        2. Virtual environment claude-mpm (development)
        3. Python module invocation (fallback)

        Returns:
            str or None: Path to claude-mpm executable
        """
        import shutil
        import sys
        import os

        # 1. Try to find claude-mpm in PATH (system-wide or venv)
        claude_mpm_path = shutil.which("claude-mpm")
        if claude_mpm_path:
            print(f"   Found claude-mpm: {claude_mpm_path}")
            return claude_mpm_path

        # 2. Check if we're in a virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            # We're in a virtual environment
            venv_bin = Path(sys.prefix) / ("Scripts" if sys.platform == "win32" else "bin")
            venv_claude_mpm = venv_bin / "claude-mpm"
            if venv_claude_mpm.exists():
                print(f"   Found claude-mpm in venv: {venv_claude_mpm}")
                return str(venv_claude_mpm)

        # 3. Check if claude_mpm module is installed and use Python to run it
        try:
            import claude_mpm
            # Return the Python executable - we'll handle the -m args separately
            print(f"   Using Python module: {sys.executable} -m claude_mpm")
            return sys.executable
        except ImportError:
            pass

        # 4. Last resort: check project's local venv (development mode)
        project_root = Path(__file__).parent.parent.parent.parent.parent
        local_venv_bin = project_root / "venv" / ("Scripts" if sys.platform == "win32" else "bin")
        local_claude_mpm = local_venv_bin / "claude-mpm"
        if local_claude_mpm.exists():
            print(f"   Found claude-mpm in project venv: {local_claude_mpm}")
            return str(local_claude_mpm)

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
        from datetime import datetime

        config = {}

        if config_path.exists():
            if not force:
                # Check if claude-mpm-gateway already exists
                try:
                    with open(config_path, 'r') as f:
                        existing_config = json.load(f)

                    if (existing_config.get("mcpServers", {}).get("claude-mpm-gateway") and
                        not force):
                        print("⚠️  claude-mpm-gateway is already configured")
                        response = input("Do you want to overwrite it? (y/N): ").strip().lower()
                        if response not in ['y', 'yes']:
                            print("❌ Configuration cancelled")
                            return None

                    config = existing_config

                except (json.JSONDecodeError, IOError) as e:
                    print(f"⚠️  Error reading existing config: {e}")
                    print("Creating backup and starting fresh...")

                    # Create backup
                    backup_path = config_path.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                    try:
                        config_path.rename(backup_path)
                        print(f"   Backup created: {backup_path}")
                    except Exception as backup_error:
                        print(f"   Warning: Could not create backup: {backup_error}")
            else:
                # Force mode - create backup but proceed
                try:
                    with open(config_path, 'r') as f:
                        existing_config = json.load(f)
                    config = existing_config
                    print("   Force mode: Overwriting existing configuration")
                except:
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
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"\n✅ Configuration saved to {config_path}")
            return True

        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
            return False
