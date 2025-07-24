"""Main entry point for claude-mpm."""

import sys

# Import from the correct cli.py file (not the cli package)
from claude_mpm.cli import main

if __name__ == "__main__":
    sys.exit(main())