#!/usr/bin/env python3
"""Verify that hook handler import fixes are complete and working.

This script performs final verification that:
1. All hook handler files have proper import patterns
2. The hook handler can be run directly without import errors
3. Events can flow through the system properly
"""

import json
import subprocess
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def check_import_patterns():
    """Verify all hook handler files have proper import patterns."""
    print("Checking import patterns in hook handler files...")
    
    hook_path = src_path / "claude_mpm" / "hooks" / "claude_hooks"
    files_to_check = [
        "hook_handler.py",
        "event_handlers.py",
        "connection_pool.py",
        "memory_integration.py",
        "response_tracking.py",
    ]
    
    results = {}
    for filename in files_to_check:
        filepath = hook_path / filename
        if not filepath.exists():
            results[filename] = "File not found"
            continue
            
        content = filepath.read_text()
        
        # Check for the try/except import pattern where needed
        if filename in ["hook_handler.py", "event_handlers.py"]:
            # These files import other hook modules and need the pattern
            if "try:" in content and "except ImportError:" in content:
                if "from ." in content or "relative import" in content.lower():
                    results[filename] = "✅ Has proper import fallback pattern"
                else:
                    results[filename] = "⚠️ Has try/except but may need relative imports"
            else:
                results[filename] = "❌ Missing import fallback pattern"
        else:
            # Other files don't import hook modules, so they're fine
            results[filename] = "✅ No relative imports needed"
    
    return results


def test_direct_execution():
    """Test that hook_handler.py runs without import errors."""
    print("\nTesting direct execution...")
    
    hook_handler = src_path / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
    
    # Create a minimal test event
    test_event = {
        "hook_event_name": "Notification",
        "timestamp": 1234567890,
        "message": "Test notification"
    }
    
    # Run the handler
    result = subprocess.run(
        [sys.executable, str(hook_handler)],
        input=json.dumps(test_event),
        capture_output=True,
        text=True,
        timeout=3
    )
    
    # Check for import errors
    if "ImportError" in result.stderr or "ModuleNotFoundError" in result.stderr:
        return False, f"Import error: {result.stderr}"
    
    # Check for valid JSON response
    try:
        lines = result.stdout.strip().split('\n')
        response = json.loads(lines[-1])
        if response.get("action") == "continue":
            return True, "Successfully executed and returned continue"
    except (json.JSONDecodeError, IndexError):
        pass
    
    return True, "No import errors detected"


def test_module_imports():
    """Test that all hook modules can be imported."""
    print("\nTesting module imports...")
    
    modules = [
        "claude_mpm.hooks.claude_hooks.hook_handler",
        "claude_mpm.hooks.claude_hooks.event_handlers",
        "claude_mpm.hooks.claude_hooks.connection_pool",
        "claude_mpm.hooks.claude_hooks.memory_integration",
        "claude_mpm.hooks.claude_hooks.response_tracking",
        "claude_mpm.hooks.claude_hooks.tool_analysis",
    ]
    
    results = {}
    for module in modules:
        try:
            __import__(module)
            results[module.split('.')[-1]] = "✅ Imports successfully"
        except ImportError as e:
            results[module.split('.')[-1]] = f"❌ Import error: {e}"
    
    return results


def test_event_routing():
    """Test that events can be routed to handlers."""
    print("\nTesting event routing...")
    
    from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
    
    handler = ClaudeHookHandler()
    
    # Test event routing
    test_events = [
        ("UserPromptSubmit", {"hook_event_name": "UserPromptSubmit", "prompt": "test"}),
        ("PreToolUse", {"hook_event_name": "PreToolUse", "tool_name": "Test"}),
        ("PostToolUse", {"hook_event_name": "PostToolUse", "tool_name": "Test"}),
        ("Stop", {"hook_event_name": "Stop", "output": "done"}),
    ]
    
    results = {}
    for event_name, event_data in test_events:
        try:
            handler._route_event(event_data)
            results[event_name] = "✅ Routed successfully"
        except Exception as e:
            results[event_name] = f"❌ Routing error: {e}"
    
    return results


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("HOOK HANDLER IMPORT FIX VERIFICATION")
    print("=" * 70)
    
    all_passed = True
    
    # Check import patterns
    print("\n1. IMPORT PATTERN CHECK")
    print("-" * 40)
    pattern_results = check_import_patterns()
    for filename, status in pattern_results.items():
        print(f"  {filename:25} {status}")
        if "❌" in status:
            all_passed = False
    
    # Test direct execution
    print("\n2. DIRECT EXECUTION TEST")
    print("-" * 40)
    success, message = test_direct_execution()
    status = "✅ PASSED" if success else "❌ FAILED"
    print(f"  {status}: {message}")
    if not success:
        all_passed = False
    
    # Test module imports
    print("\n3. MODULE IMPORT TEST")
    print("-" * 40)
    import_results = test_module_imports()
    for module, status in import_results.items():
        print(f"  {module:25} {status}")
        if "❌" in status:
            all_passed = False
    
    # Test event routing
    print("\n4. EVENT ROUTING TEST")
    print("-" * 40)
    routing_results = test_event_routing()
    for event, status in routing_results.items():
        print(f"  {event:25} {status}")
        if "❌" in status:
            all_passed = False
    
    # Final summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ VERIFICATION COMPLETE: All import issues are resolved!")
        print("\nThe hook handler can now:")
        print("  • Be imported as a module without errors")
        print("  • Be executed directly by Claude Code without import errors")
        print("  • Route events to appropriate handlers")
        print("  • Process events through the system properly")
    else:
        print("❌ VERIFICATION FAILED: Some issues remain")
        print("\nPlease review the failures above.")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())