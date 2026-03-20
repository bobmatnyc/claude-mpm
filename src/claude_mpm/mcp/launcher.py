#!/usr/bin/env python3
"""
MCP Server Entry Point Launcher
================================

This is a simple launcher that delegates to the wrapper module.
It exists to provide a consistent entry point for the MCP server.

WHY: Claude Code needs a reliable entry point that can be called
directly without going through the CLI module system.

DESIGN DECISION: Keep this launcher minimal and delegate all logic
to the wrapper module for maintainability.
"""

import sys
from pathlib import Path


def _find_project_root() -> Path:
    """Locate the project root by searching for pyproject.toml."""
    # This file lives at src/claude_mpm/mcp/launcher.py
    # Project root is four levels up.
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / "pyproject.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path(__file__).resolve().parent.parent.parent.parent


def main():
    """Run the MCP server via the wrapper module."""
    project_root = _find_project_root()

    # Ensure src is on the path so imports resolve correctly
    src_dir = str(project_root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    try:
        from claude_mpm.core.env_defaults import apply_env_defaults

        apply_env_defaults()
    except ImportError:
        pass

    # Delegate to the wrapper module (which contains all real logic)
    from claude_mpm.mcp.wrapper import main as wrapper_main

    wrapper_main()


if __name__ == "__main__":
    main()
