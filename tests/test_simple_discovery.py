#!/usr/bin/env python3
"""Simple test to check dotfile filtering"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_mpm.tools.code_tree_analyzer import CodeTreeAnalyzer

def test():
    print("\n" + "="*60)
    print("Testing discover_top_level with show_hidden_files=False")
    print("="*60)
    
    # Test with False
    analyzer = CodeTreeAnalyzer(show_hidden_files=False)
    result = analyzer.discover_top_level(Path.cwd(), [])
    
    items = result.get("children", [])
    names = [item.get("name") for item in items]
    dotfiles = [n for n in names if n.startswith(".")]
    
    print(f"Items found: {names}")
    print(f"Dotfiles found: {dotfiles}")
    
    if dotfiles:
        print(f"ERROR: Found {len(dotfiles)} dotfiles when show_hidden_files=False")
        print(f"Dotfiles that shouldn't be visible: {dotfiles}")
        return False
    else:
        print("SUCCESS: No dotfiles found when show_hidden_files=False")
        return True

if __name__ == "__main__":
    success = test()
    sys.exit(0 if success else 1)