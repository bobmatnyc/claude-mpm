"""
Entry point for executing the CLI module with python -m claude_mpm.cli.

WHY: This file enables the CLI to be executed as a module using the -m flag,
which is the preferred way to run Python packages as scripts. This ensures
proper module resolution and import paths.

DESIGN DECISION: We simply import and call the main() function from __init__.py
to maintain a single source of truth for the CLI logic while enabling module
execution.

Usage:
    python -m claude_mpm.cli [arguments]

This is equivalent to calling the claude-mpm script directly but ensures
proper Python module context and import resolution.
"""

import os
import sys

# Disable telemetry by default
os.environ["DISABLE_TELEMETRY"] = "1"

from . import main

if __name__ == "__main__":
    # Execute the main CLI function and exit with its return code
    sys.exit(main())
