#!/usr/bin/env python3
"""Direct test to find why dotfiles are still appearing in code tree."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from claude_mpm.tools.code_tree_analyzer import CodeTreeAnalyzer, GitignoreManager

def test_direct_discovery():
    """Test the exact method called by the dashboard."""
    print("=" * 80)
    print("TESTING DIRECT DISCOVERY")
    print("=" * 80)
    
    root_path = Path("/Users/masa/Projects/claude-mpm")
    
    # Initialize analyzer with show_hidden_files=False (like dashboard does)
    analyzer = CodeTreeAnalyzer(
        show_hidden_files=False,
        emit_events=False  # Disable events for testing
    )
    
    print(f"\nAnalyzer initialized:")
    print(f"  show_hidden_files: {analyzer.show_hidden_files}")
    print(f"  gitignore_manager exists: {analyzer.gitignore_manager is not None}")
    print(f"  gitignore_manager.show_hidden_files: {analyzer.gitignore_manager.show_hidden_files}")
    
    # Call discover_top_level exactly as dashboard does
    print("\n" + "=" * 80)
    print(f"Calling discover_top_level({root_path})...")
    print("=" * 80)
    
    result = analyzer.discover_top_level(root_path)
    top_level_items = result.get('children', [])
    
    print(f"\n\nRESULTS - Found {len(top_level_items)} items:")
    print("-" * 80)
    
    # Check for dotfiles
    dotfiles_found = []
    for item in top_level_items:
        name = item.get('name', '')
        path = item.get('path', '')
        item_type = item.get('type', '')
        
        print(f"  [{item_type:4}] {name:30} -> {path}")
        
        if name.startswith('.'):
            dotfiles_found.append(name)
            print(f"         ^^^ DOTFILE FOUND! ^^^")
    
    if dotfiles_found:
        print(f"\n❌ ERROR: Found {len(dotfiles_found)} dotfiles: {dotfiles_found}")
    else:
        print("\n✓ No dotfiles found")
    
    return dotfiles_found

def test_gitignore_directly():
    """Test GitignoreManager directly."""
    print("\n" + "=" * 80)
    print("TESTING GITIGNORE MANAGER DIRECTLY")
    print("=" * 80)
    
    root = Path("/Users/masa/Projects/claude-mpm")
    
    # Test with show_hidden_files=False (should hide dotfiles)
    manager = GitignoreManager(show_hidden_files=False)
    
    print(f"\nGitignoreManager initialized with show_hidden_files=False")
    print(f"  DOTFILE_EXCEPTIONS: {manager.DOTFILE_EXCEPTIONS}")
    
    # Test specific dotfiles
    test_paths = [
        ".github",
        ".ai-trackdown",
        ".git",
        ".gitignore",
        ".env",
        ".vscode"
    ]
    
    for test_path in test_paths:
        full_path = root / test_path
        # GitignoreManager.should_ignore needs working_dir parameter
        should_ignore = manager.should_ignore(full_path, root)
        exists = full_path.exists()
        is_dir = full_path.is_dir() if exists else False
        in_exceptions = test_path in manager.DOTFILE_EXCEPTIONS
        
        print(f"\n  Testing: {test_path}")
        print(f"    Exists: {exists}")
        print(f"    Is directory: {is_dir}")
        print(f"    In DOTFILE_EXCEPTIONS: {in_exceptions}")
        print(f"    Should ignore: {should_ignore}")
        
        # Expected behavior: dotfiles should be ignored unless in exceptions
        expected = not in_exceptions  # Should ignore if NOT in exceptions
        if should_ignore != expected:
            print(f"    ❌ UNEXPECTED! Expected: {expected}")

def test_discover_with_tracing():
    """Test with detailed tracing of the discovery process."""
    print("\n" + "=" * 80)
    print("TESTING WITH METHOD TRACING")
    print("=" * 80)
    
    root_path = Path("/Users/masa/Projects/claude-mpm")
    
    # Monkey-patch to trace calls
    original_should_ignore = GitignoreManager.should_ignore
    
    def traced_should_ignore(self, path, working_dir):
        result = original_should_ignore(self, path, working_dir)
        if Path(path).name.startswith('.'):
            print(f"  GitignoreManager.should_ignore({Path(path).name}, working_dir) -> {result}")
        return result
    
    GitignoreManager.should_ignore = traced_should_ignore
    
    try:
        analyzer = CodeTreeAnalyzer(
            show_hidden_files=False,
            emit_events=False
        )
        
        print("\nCalling discover_top_level with tracing...")
        result = analyzer.discover_top_level(root_path)
        items = result.get('children', [])
        
        dotfiles = [item['name'] for item in items if item['name'].startswith('.')]
        if dotfiles:
            print(f"\n❌ Still found dotfiles: {dotfiles}")
        else:
            print("\n✓ No dotfiles found with tracing")
            
    finally:
        # Restore original method
        GitignoreManager.should_ignore = original_should_ignore

def check_actual_filesystem():
    """Check what's actually in the filesystem."""
    print("\n" + "=" * 80)
    print("ACTUAL FILESYSTEM CONTENTS")
    print("=" * 80)
    
    root = Path("/Users/masa/Projects/claude-mpm")
    
    print("\nAll top-level items:")
    for item in sorted(root.iterdir()):
        name = item.name
        is_dir = item.is_dir()
        is_hidden = name.startswith('.')
        
        marker = "DIR" if is_dir else "FILE"
        hidden_marker = " [HIDDEN]" if is_hidden else ""
        print(f"  [{marker:4}] {name}{hidden_marker}")
    
    print("\nDotfiles/folders found:")
    dotfiles = [item.name for item in root.iterdir() if item.name.startswith('.')]
    for df in sorted(dotfiles):
        print(f"  - {df}")

if __name__ == "__main__":
    # Run all tests
    check_actual_filesystem()
    
    dotfiles = test_direct_discovery()
    
    test_gitignore_directly()
    
    test_discover_with_tracing()
    
    if dotfiles:
        print("\n" + "=" * 80)
        print("❌ DOTFILES ARE STILL APPEARING!")
        print(f"Found: {dotfiles}")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("✓ All tests passed - no dotfiles found")
        print("=" * 80)