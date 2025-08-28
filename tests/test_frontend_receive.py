#!/usr/bin/env python3
"""Test what the frontend actually receives from the backend"""

import asyncio
import json
from pathlib import Path
import sys
sys.path.insert(0, 'src')

from claude_mpm.tools.code_tree_analyzer import CodeTreeAnalyzer

def test_direct_discovery():
    """Test what discover_top_level actually returns"""
    print("Testing discover_top_level with show_hidden_files=False")
    print("=" * 60)
    
    # Create analyzer with show_hidden_files=False (default behavior)
    analyzer = CodeTreeAnalyzer(show_hidden_files=False)
    
    # Get current directory
    working_dir = Path.cwd()
    print(f"Working directory: {working_dir}")
    print(f"Analyzer show_hidden_files: {analyzer.show_hidden_files}")
    print(f"GitignoreManager show_hidden_files: {analyzer.gitignore_manager.show_hidden_files}")
    print()
    
    # Call discover_top_level
    result = analyzer.discover_top_level(working_dir)
    
    print(f"Total items returned: {len(result.get('children', []))}")
    print()
    
    # Check for dotfiles
    dotfiles_found = []
    regular_files = []
    
    for item in result.get('children', []):
        name = item.get('name', '')
        if name.startswith('.'):
            dotfiles_found.append(name)
        else:
            regular_files.append(name)
    
    print(f"Dotfiles found ({len(dotfiles_found)}):")
    for df in sorted(dotfiles_found):
        print(f"  - {df}")
    
    print()
    print(f"Regular items found ({len(regular_files)}):")
    for rf in sorted(regular_files)[:10]:  # Show first 10
        print(f"  - {rf}")
    
    if len(regular_files) > 10:
        print(f"  ... and {len(regular_files) - 10} more")
    
    print()
    print("RESULT:", "❌ DOTFILES STILL PRESENT!" if dotfiles_found else "✅ NO DOTFILES")
    
    # Return the actual result for inspection
    return result

if __name__ == "__main__":
    result = test_direct_discovery()
    
    # Save to file for inspection
    with open('test_discovery_result.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("\nFull result saved to test_discovery_result.json")