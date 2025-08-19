#!/usr/bin/env python3
"""
MCP Server Launcher Script
===========================

This is a simple launcher that delegates to the wrapper script.
It exists to provide a consistent entry point for the MCP server.

WHY: Claude Desktop needs a reliable entry point that can be called
directly without going through the CLI module system.

DESIGN DECISION: Keep this launcher minimal and delegate all logic
to the wrapper script for maintainability.
"""

import sys
import os
from pathlib import Path

# Disable telemetry by default
os.environ['DISABLE_TELEMETRY'] = '1'

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import and run the wrapper
from pathlib import Path
import subprocess

def main():
    """Run the MCP server via the wrapper script."""
    wrapper_script = Path(__file__).parent / "mcp_wrapper.py"
    
    if not wrapper_script.exists():
        print(f"Error: Wrapper script not found at {wrapper_script}", file=sys.stderr)
        sys.exit(1)
    
    # Execute the wrapper script with the same Python interpreter
    import subprocess
    result = subprocess.run([sys.executable, str(wrapper_script)])
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()