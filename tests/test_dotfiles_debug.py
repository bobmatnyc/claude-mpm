#!/usr/bin/env python3
"""Test script to debug dotfile filtering issue"""

import logging
import tempfile
from pathlib import Path

# Set up basic logging to see debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test the analyzer directly
from src.claude_mpm.tools.code_tree_analyzer import CodeTreeAnalyzer

def test_dotfiles():
    """Test dotfile filtering with debug output"""
    
    print(f"\n{'='*60}")
    print("Testing CodeTreeAnalyzer with show_hidden_files=False")
    print(f"{'='*60}\n")
    
    # Create analyzer with show_hidden_files=False
    analyzer = CodeTreeAnalyzer(show_hidden_files=False)
    
    print(f"Analyzer created with show_hidden_files={analyzer.show_hidden_files}")
    print(f"GitignoreManager.show_hidden_files={analyzer.gitignore_manager.show_hidden_files}")
    
    # Use current directory
    test_dir = Path.cwd()
    
    # Discover top level
    result = analyzer.discover_top_level(test_dir, [])
    
    # Check results
    items = result.get("children", [])
    dotfiles = [item for item in items if item.get("name", "").startswith(".")]
    
    print(f"\nResults with show_hidden_files=False:")
    print(f"  Total items: {len(items)}")
    print(f"  Dotfiles found: {len(dotfiles)}")
    if dotfiles:
        print(f"  Dotfile names: {[d.get('name') for d in dotfiles]}")
    
    print(f"\n{'='*60}")
    print("Testing CodeTreeAnalyzer with show_hidden_files=True")
    print(f"{'='*60}\n")
    
    # Create analyzer with show_hidden_files=True
    analyzer2 = CodeTreeAnalyzer(show_hidden_files=True)
    
    print(f"Analyzer created with show_hidden_files={analyzer2.show_hidden_files}")
    print(f"GitignoreManager.show_hidden_files={analyzer2.gitignore_manager.show_hidden_files}")
    
    # Discover top level
    result2 = analyzer2.discover_top_level(test_dir, [])
    
    # Check results
    items2 = result2.get("children", [])
    dotfiles2 = [item for item in items2 if item.get("name", "").startswith(".")]
    
    print(f"\nResults with show_hidden_files=True:")
    print(f"  Total items: {len(items2)}")
    print(f"  Dotfiles found: {len(dotfiles2)}")
    if dotfiles2:
        print(f"  Dotfile names: {[d.get('name') for d in dotfiles2][:10]}")  # Limit to first 10

if __name__ == "__main__":
    test_dotfiles()