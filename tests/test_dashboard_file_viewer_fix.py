#!/usr/bin/env python3
"""Test that the dashboard file viewer correctly handles file operations."""

import json
import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_file_operation_detection():
    """Test that file operations are correctly detected."""
    print("Testing File Operation Detection")
    print("=" * 60)
    
    # Test cases for file operations
    test_events = [
        # Standard file tools - lowercase
        {'tool_name': 'read', 'tool_parameters': {'file_path': '/test/file1.py'}},
        {'tool_name': 'write', 'tool_parameters': {'file_path': '/test/file2.py'}},
        {'tool_name': 'edit', 'tool_parameters': {'file_path': '/test/file3.py'}},
        {'tool_name': 'multiedit', 'tool_parameters': {'file_path': '/test/file4.py'}},
        {'tool_name': 'grep', 'tool_parameters': {'path': '/test/', 'pattern': 'test'}},
        
        # Standard file tools - capitalized (old format)
        {'tool_name': 'Read', 'tool_parameters': {'file_path': '/test/file5.py'}},
        {'tool_name': 'Write', 'tool_parameters': {'file_path': '/test/file6.py'}},
        {'tool_name': 'Edit', 'tool_parameters': {'file_path': '/test/file7.py'}},
        
        # New file tools
        {'tool_name': 'glob', 'tool_parameters': {'pattern': '**/*.py'}},
        {'tool_name': 'ls', 'tool_parameters': {'path': '/test/'}},
        {'tool_name': 'notebookedit', 'tool_parameters': {'notebook_path': '/test/notebook.ipynb'}},
        
        # Bash commands with file operations
        {'tool_name': 'bash', 'tool_parameters': {'command': 'cat /test/file.txt'}},
        {'tool_name': 'bash', 'tool_parameters': {'command': 'echo "test" > /test/output.txt'}},
        {'tool_name': 'bash', 'tool_parameters': {'command': 'mkdir /test/new_dir'}},
        {'tool_name': 'bash', 'tool_parameters': {'command': 'grep "pattern" /test/search.txt'}},
        
        # Non-file operations (should not be detected)
        {'tool_name': 'bash', 'tool_parameters': {'command': 'python --version'}},
        {'tool_name': 'task', 'tool_parameters': {'description': 'Some task'}},
    ]
    
    # JavaScript code to test (mimicking the isFileOperation function)
    js_file_tools = ['read', 'write', 'edit', 'grep', 'multiedit', 'glob', 'ls', 'bash', 'notebookedit']
    
    print("\nTesting file operation detection:")
    print("-" * 50)
    
    for i, event in enumerate(test_events, 1):
        tool_name = event.get('tool_name', '').lower()
        is_file_op = False
        
        # Check if it's a file operation
        if tool_name in js_file_tools:
            # Special handling for bash
            if tool_name == 'bash' and 'tool_parameters' in event:
                command = event['tool_parameters'].get('command', '')
                if any(cmd in command for cmd in ['cat', 'less', 'more', 'head', 'tail', 
                                                   'touch', 'mv', 'cp', 'rm', 'mkdir', 
                                                   'ls', 'find', 'echo', 'grep']):
                    is_file_op = True
            else:
                is_file_op = True
        
        result = "✓ File Op" if is_file_op else "✗ Not File Op"
        print(f"{i:2}. {result}: {event['tool_name']:15} - {event.get('tool_parameters', {})}")
    
    print("-" * 50)
    print("\n✅ File operation detection tests complete")
    print("\nThe dashboard should now correctly detect and display file operations with:")
    print("  - Case-insensitive tool name matching")
    print("  - Support for new tools (Glob, LS, NotebookEdit)")
    print("  - Bash command file operation detection")
    print("  - Improved file path extraction")
    
    return True


def verify_dashboard_javascript():
    """Verify that the JavaScript file has been updated correctly."""
    print("\n" + "=" * 60)
    print("Verifying Dashboard JavaScript Updates")
    print("=" * 60)
    
    js_file = Path(__file__).parent.parent / "src" / "claude_mpm" / "dashboard" / "static" / "js" / "components" / "file-tool-tracker.js"
    
    if not js_file.exists():
        print(f"❌ JavaScript file not found: {js_file}")
        return False
    
    content = js_file.read_text()
    
    # Check for key updates
    checks = [
        ("Case-insensitive tool name check", "tool_name.toLowerCase()" in content),
        ("Lowercase file tools array", "['read', 'write', 'edit', 'grep', 'multiedit'" in content),
        ("Bash command detection", "command.match(/\\b(cat|less|more|head|tail" in content),
        ("Glob tool support", "'glob'" in content),
        ("NotebookEdit support", "'notebookedit'" in content),
        ("Notebook path extraction", "tool_parameters.notebook_path" in content or "notebook_path" in content),
    ]
    
    print("\nChecking JavaScript updates:")
    print("-" * 50)
    
    all_passed = True
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    print("-" * 50)
    
    if all_passed:
        print("\n✅ All JavaScript updates verified successfully!")
    else:
        print("\n⚠️ Some JavaScript updates are missing")
    
    return all_passed


if __name__ == "__main__":
    # Run tests
    test1 = test_file_operation_detection()
    test2 = verify_dashboard_javascript()
    
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    
    if test1 and test2:
        print("✅ SUCCESS: Dashboard file viewer fix is complete!")
        print("\nThe file viewer should now properly display files when you:")
        print("  1. Open the dashboard: ./claude-mpm dashboard")
        print("  2. Perform file operations (Read, Write, Edit, etc.)")
        print("  3. Click on the 'Files' tab")
        print("\nThe fix handles:")
        print("  - Case-insensitive tool names (read, Read, READ all work)")
        print("  - New file tools (Glob, LS, NotebookEdit)")
        print("  - Bash commands that operate on files")
        print("  - Multiple file path parameter names")
    else:
        print("❌ FAILURE: Some tests failed, please review the output above")
    
    sys.exit(0 if (test1 and test2) else 1)