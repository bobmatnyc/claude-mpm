"""Main entry point for CLI that can be run directly."""

import sys
from pathlib import Path

# Add src directory to path so claude_mpm can be imported
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from claude_mpm.cli import main

if __name__ == "__main__":
    sys.exit(main())