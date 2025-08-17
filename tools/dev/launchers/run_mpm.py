#!/usr/bin/env python3
"""Simple runner for claude-mpm that properly handles imports."""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

# Import from the new CLI module structure
from claude_mpm.cli import main

if __name__ == "__main__":
    # Enable debug logging if requested
    if "--debug" in sys.argv or "-d" in sys.argv:
        os.environ["CLAUDE_MPM_DEBUG"] = "1"
    
    # Run the CLI
    sys.exit(main())