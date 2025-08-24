from pathlib import Path

"""
Main entry point for claude-mpm package.

WHY: This module enables running claude-mpm as a Python module via `python -m claude_mpm`.
It's the standard Python pattern for making packages executable.

DESIGN DECISION: We only import and call the main function from the CLI module,
keeping this file minimal and focused on its single responsibility.
"""

import os
import sys

# Disable telemetry by default
os.environ["DISABLE_TELEMETRY"] = "1"

# Add parent directory to path to ensure proper imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import main function from the new CLI module structure
from claude_mpm.cli import main

if __name__ == "__main__":
    sys.exit(main())
