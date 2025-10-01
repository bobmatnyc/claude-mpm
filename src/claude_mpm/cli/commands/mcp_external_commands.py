"""MCP external services command implementations.

This module provides commands for managing external MCP services
like mcp-vector-search and mcp-browser.
"""


class MCPExternalCommands:
    """Handles MCP external service commands."""

    def __init__(self, logger):
        """Initialize the MCP external commands handler."""
        self.logger = logger

    def manage_external(self, args):
        """Manage external MCP services.

        Args:
            args: Parsed command line arguments

        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        # Get the external subcommand if it exists
        external_action = getattr(args, "external_action", None)

        if not external_action:
            # No subcommand provided, show help
            self._show_help()
            return 0

        # Route to appropriate handler
        if external_action == "setup":
            return self._setup_external(args)
        if external_action == "list":
            return self._list_external(args)
        if external_action == "check":
            return self._check_external(args)
        if external_action == "fix-browser":
            return self._fix_browser(args)
        if external_action == "detect":
            return self._detect_and_update(args)
        print(f"Unknown external subcommand: {external_action}")
        self._show_help()
        return 1

    def _setup_external(self, args):
        """Setup external MCP services in Claude Code.

        Args:
            args: Command line arguments

        Returns:
            int: Exit code
        """
        print("📦 Setting up External MCP Services")
        print("=" * 50)

        from .mcp_setup_external import MCPExternalServicesSetup

        setup = MCPExternalServicesSetup(self.logger)

        # First install Python packages
        print("\n1️⃣  Installing Python packages...")
        if not setup.check_and_install_pip_packages():
            print("⚠️ Some Python packages could not be installed")
            print("   You may need to install them manually:")
            print("   pip install mcp-vector-search mcp-browser")

        # Then configure in Claude Code
        print("\n2️⃣  Configuring Claude Code...")
        force = getattr(args, "force", False)
        if setup.setup_external_services(force=force):
            print("\n✅ External services setup completed successfully!")
            print("\nNext steps:")
            print("1. Restart Claude Code to load the new services")
            print("2. Check status with: claude-mpm mcp external list")
            print("3. The services will be available in Claude as separate MCP servers")
            return 0
        print("\n❌ Failed to setup external services")
        print("Please check the error messages above and try again")
        return 1

    def _list_external(self, args):
        """List external MCP services and their status.

        Args:
            args: Command line arguments

        Returns:
            int: Exit code
        """
        from .mcp_setup_external import MCPExternalServicesSetup

        setup = MCPExternalServicesSetup(self.logger)
        setup.list_external_services()
        return 0

    def _check_external(self, args):
        """Check if external services are properly configured.

        Args:
            args: Command line arguments

        Returns:
            int: Exit code
        """
        print("🔍 Checking External MCP Services Configuration")
        print("=" * 50)

        import json
        from pathlib import Path

        # Check Claude Code configuration
        config_paths = [
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

        config_found = False
        for config_path in config_paths:
            if config_path.exists():
                config_found = True
                print(f"\n📄 Found config: {config_path}")

                try:
                    with config_path.open() as f:
                        config = json.load(f)

                    mcp_servers = config.get("mcpServers", {})

                    # Check for external services
                    external_services = ["mcp-vector-search", "mcp-browser"]
                    for service in external_services:
                        if service in mcp_servers:
                            print(f"  ✅ {service} is configured")
                            server_config = mcp_servers[service]
                            print(f"     Command: {server_config.get('command')}")
                            print(f"     Args: {server_config.get('args')}")
                        else:
                            print(f"  ❌ {service} is NOT configured")

                except Exception as e:
                    print(f"  ❌ Error reading config: {e}")

                break

        if not config_found:
            print("❌ No Claude Code configuration found")
            print("   Please run: claude-mpm mcp install")

        # Check Python packages
        print("\n🐍 Python Package Status:")
        from .mcp_setup_external import MCPExternalServicesSetup

        setup = MCPExternalServicesSetup(self.logger)

        packages = [
            ("mcp-vector-search", "mcp_vector_search"),
            ("mcp-browser", "mcp_browser"),
        ]

        for package_name, module_name in packages:
            if setup._check_python_package(module_name):
                print(f"  ✅ {package_name} is installed")
            else:
                print(f"  ❌ {package_name} is NOT installed")

        return 0

    def _fix_browser(self, args):
        """Fix mcp-browser configuration to use pipx installation.

        Args:
            args: Command line arguments

        Returns:
            int: Exit code
        """
        from .mcp_setup_external import MCPExternalServicesSetup

        setup = MCPExternalServicesSetup(self.logger)
        if setup.fix_browser_configuration():
            return 0
        return 1

    def _detect_and_update(self, args):
        """Auto-detect MCP service installations and update configuration.

        Prioritizes local development installations over pipx/system.

        Args:
            args: Command line arguments

        Returns:
            int: Exit code
        """
        from .mcp_setup_external import MCPExternalServicesSetup

        setup = MCPExternalServicesSetup(self.logger)
        force = getattr(args, "force", False)

        if setup.update_mcp_json_with_detected(force=force):
            print("\n✅ Configuration updated successfully!")
            print("\nNext steps:")
            print("1. Review the .mcp.json file to verify the configuration")
            print("2. Restart Claude Code to load the updated services")
            return 0
        print("\n❌ Failed to update configuration")
        return 1

    def _show_help(self):
        """Show help for external commands."""
        print("\nMCP External Services Management")
        print("=" * 40)
        print("\nAvailable commands:")
        print(
            "  setup       - Setup external MCP services (mcp-vector-search, mcp-browser)"
        )
        print("  list        - List available external services and their status")
        print("  check       - Check configuration and installation status")
        print(
            "  detect      - Auto-detect installations and update .mcp.json (prioritizes local dev)"
        )
        print("  fix-browser - Fix mcp-browser configuration to use pipx installation")
        print("\nUsage:")
        print("  claude-mpm mcp external setup         # Interactive setup")
        print("  claude-mpm mcp external setup --force # Force reconfiguration")
        print("  claude-mpm mcp external detect        # Auto-detect and update config")
        print(
            "  claude-mpm mcp external detect --force # Force update even if configured"
        )
        print("  claude-mpm mcp external list          # Show service status")
        print("  claude-mpm mcp external check         # Detailed configuration check")
        print("  claude-mpm mcp external fix-browser   # Fix mcp-browser to use pipx")
        print("\nExternal services provide additional capabilities:")
        print("  - mcp-vector-search: Semantic code search with embeddings")
        print("  - mcp-browser: Web browsing and content extraction")
