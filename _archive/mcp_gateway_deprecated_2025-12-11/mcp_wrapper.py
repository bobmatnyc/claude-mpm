"""
MCP Wrapper Module
==================

This module provides an importable entry point for the MCP wrapper script.
It delegates to the actual wrapper script in the scripts directory.

WHY: We need this to make the wrapper accessible as a Python module entry point
for the pyproject.toml scripts configuration.
"""

import sys
from pathlib import Path


def entry_point():
    """Entry point that delegates to the actual wrapper script."""
    # Find the actual wrapper script
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent
    wrapper_script = project_root / "scripts" / "mcp_wrapper.py"

    if not wrapper_script.exists():
        print(f"Error: Wrapper script not found at {wrapper_script}", file=sys.stderr)
        sys.exit(1)

    # Add the scripts directory to path and import the wrapper
    scripts_dir = str(wrapper_script.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    # Import and run the wrapper
    import mcp_wrapper

    mcp_wrapper.main()


if __name__ == "__main__":
    entry_point()
