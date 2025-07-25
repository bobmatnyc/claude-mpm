"""Main entry point for claude-mpm."""

import sys
import os
from pathlib import Path

# Add parent directory to path to ensure proper imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import main function from cli
from claude_mpm.cli import main

if __name__ == "__main__":
    sys.exit(main())