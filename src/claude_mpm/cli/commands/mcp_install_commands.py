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
        Claude Desktop to use the MCP gateway server.
        
        DESIGN DECISION: We handle both package installation and configuration
        in one command for user convenience.
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
        
        # Step 2: Run the configuration script
        print("\n2️⃣  Configuring Claude Desktop...")
        project_root = Path(__file__).parent.parent.parent.parent.parent
        config_script = project_root / "scripts" / "configure_mcp_server.py"
        
        if not config_script.exists():
            print(f"⚠️  Configuration script not found at {config_script}")
            print("\nPlease configure manually. See:")
            print("  claude-mpm mcp start --instructions")
            return 1
        
        try:
            result = subprocess.run(
                [sys.executable, str(config_script)],
                cwd=str(project_root)
            )
            
            if result.returncode == 0:
                print("✅ Configuration completed successfully")
                print("\n🎉 MCP Gateway is ready to use!")
                print("\nNext steps:")
                print("1. Restart Claude Desktop")
                print("2. Check process status: python scripts/check_mcp_processes.py")
                return 0
            else:
                print("❌ Configuration script failed")
                return 1
                
        except Exception as e:
            print(f"❌ Error running configuration: {e}")
            return 1
