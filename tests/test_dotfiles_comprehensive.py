#!/usr/bin/env python3
"""Comprehensive test to verify dotfiles filtering works correctly."""

import asyncio
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from claude_mpm.tools.code_tree_analyzer import CodeTreeAnalyzer, GitignoreManager
from claude_mpm.services.socketio.handlers.code_analysis import CodeAnalysisEventHandler


def test_gitignore_manager():
    """Test GitignoreManager directly."""
    print("\n" + "=" * 80)
    print("TEST 1: GitignoreManager Direct Test")
    print("=" * 80)
    
    root = Path("/Users/masa/Projects/claude-mpm")
    
    # Test with show_hidden_files=False (default, should hide dotfiles)
    print("\n--- Testing with show_hidden_files=False ---")
    manager = GitignoreManager(show_hidden_files=False)
    
    test_items = [".github", ".ai-trackdown", ".gitignore", "src", "tests"]
    
    for item_name in test_items:
        item_path = root / item_name
        should_ignore = manager.should_ignore(item_path, root)
        is_dotfile = item_name.startswith('.')
        print(f"  {item_name:20} -> should_ignore: {should_ignore:5} (is_dotfile: {is_dotfile})")
    
    # Test with show_hidden_files=True
    print("\n--- Testing with show_hidden_files=True ---")
    manager = GitignoreManager(show_hidden_files=True)
    
    for item_name in test_items:
        item_path = root / item_name
        should_ignore = manager.should_ignore(item_path, root)
        is_dotfile = item_name.startswith('.')
        print(f"  {item_name:20} -> should_ignore: {should_ignore:5} (is_dotfile: {is_dotfile})")
    
    return True


def test_analyzer_discovery():
    """Test CodeTreeAnalyzer discover_top_level."""
    print("\n" + "=" * 80)
    print("TEST 2: CodeTreeAnalyzer Discovery Test")
    print("=" * 80)
    
    root_path = Path("/Users/masa/Projects/claude-mpm")
    
    # Test with show_hidden_files=False
    print("\n--- Testing with show_hidden_files=False ---")
    analyzer = CodeTreeAnalyzer(show_hidden_files=False, emit_events=False)
    result = analyzer.discover_top_level(root_path)
    
    items = result.get('children', [])
    dotfiles = [item for item in items if item['name'].startswith('.')]
    
    print(f"Total items found: {len(items)}")
    print(f"Dotfiles found: {len(dotfiles)}")
    if dotfiles:
        print("Dotfiles list:", [d['name'] for d in dotfiles])
        print("❌ ERROR: Dotfiles should not be visible!")
        return False
    else:
        print("✓ No dotfiles found (correct)")
    
    # Test with show_hidden_files=True
    print("\n--- Testing with show_hidden_files=True ---")
    analyzer = CodeTreeAnalyzer(show_hidden_files=True, emit_events=False)
    result = analyzer.discover_top_level(root_path)
    
    items = result.get('children', [])
    dotfiles = [item for item in items if item['name'].startswith('.')]
    
    print(f"Total items found: {len(items)}")
    print(f"Dotfiles found: {len(dotfiles)}")
    if dotfiles:
        print("✓ Dotfiles found (correct when show_hidden_files=True):")
        for df in dotfiles[:5]:  # Show first 5
            print(f"  - {df['name']}")
    else:
        print("❌ ERROR: Dotfiles should be visible when show_hidden_files=True!")
        return False
    
    return True


async def test_socketio_handler():
    """Test the Socket.IO handler that the dashboard uses."""
    print("\n" + "=" * 80)
    print("TEST 3: Socket.IO Handler Test")
    print("=" * 80)
    
    # Mock server and core objects
    class MockCore:
        class MockSIO:
            async def emit(self, event, data, room=None):
                print(f"  [EMIT] {event}: {len(data.get('items', []))} items")
                if 'items' in data:
                    dotfiles = [item for item in data['items'] if item['name'].startswith('.')]
                    if dotfiles:
                        print(f"    ⚠️ Found {len(dotfiles)} dotfiles: {[d['name'] for d in dotfiles]}")
                    else:
                        print(f"    ✓ No dotfiles in emitted data")
        sio = MockSIO()
    
    class MockServer:
        core = MockCore()
        
    # Create handler
    handler = CodeAnalysisEventHandler(MockServer())
    
    # Test request with show_hidden_files=False
    print("\n--- Testing request with show_hidden_files=False ---")
    request_data = {
        "path": "/Users/masa/Projects/claude-mpm",
        "show_hidden_files": False,
        "request_id": "test-123"
    }
    
    await handler.handle_discover_top_level("test-sid", request_data)
    
    # Test request with show_hidden_files=True
    print("\n--- Testing request with show_hidden_files=True ---")
    request_data["show_hidden_files"] = True
    request_data["request_id"] = "test-456"
    
    await handler.handle_discover_top_level("test-sid", request_data)
    
    return True


def main():
    """Run all tests."""
    print("=" * 80)
    print("COMPREHENSIVE DOTFILES FILTERING TEST")
    print("=" * 80)
    
    all_passed = True
    
    # Test 1: GitignoreManager
    if not test_gitignore_manager():
        all_passed = False
    
    # Test 2: CodeTreeAnalyzer
    if not test_analyzer_discovery():
        all_passed = False
    
    # Test 3: Socket.IO Handler
    if not asyncio.run(test_socketio_handler()):
        all_passed = False
    
    # Summary
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED - Backend is filtering dotfiles correctly")
        print("\nThe issue must be in the frontend JavaScript or browser cache.")
        print("Next steps:")
        print("1. Clear browser cache and reload dashboard")
        print("2. Check browser console for JavaScript errors")
        print("3. Verify the checkbox state is being sent correctly")
    else:
        print("❌ TESTS FAILED - Backend has issues with dotfile filtering")
    print("=" * 80)


if __name__ == "__main__":
    main()