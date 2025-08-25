#!/usr/bin/env python3
"""Test script for the configure TUI improvements."""

import sys
from pathlib import Path

# Add the source directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_mpm.cli.commands.configure_tui import ConfigureTUI

def test_tui():
    """Test the TUI application."""
    print("Testing Configure TUI...")
    print("=" * 60)
    print("Expected improvements:")
    print("1. Headers should be compact (single line)")
    print("2. Headers should be left-aligned with a line decoration")
    print("3. DataTable should populate with agents")
    print("=" * 60)
    print("\nLaunching TUI in 3 seconds...")
    
    import time
    time.sleep(3)
    
    app = ConfigureTUI()
    app.run()
    
    print("\nTUI closed.")
    print("Test complete!")

if __name__ == "__main__":
    test_tui()