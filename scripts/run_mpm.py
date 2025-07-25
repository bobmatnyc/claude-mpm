#!/usr/bin/env python3
"""Simple runner for claude-mpm that properly handles imports."""

import sys
import os
from pathlib import Path
import importlib.util

# Add src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

# Import from cli.py directly to avoid package/module confusion
cli_path = src_dir / "claude_mpm" / "cli.py"
spec = importlib.util.spec_from_file_location("cli_module", cli_path)
cli_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli_module)

if __name__ == "__main__":
    # Enable debug logging if requested
    if "--debug" in sys.argv or "-d" in sys.argv:
        os.environ["CLAUDE_MPM_DEBUG"] = "1"
    
    # Run the CLI
    sys.exit(cli_module.main())