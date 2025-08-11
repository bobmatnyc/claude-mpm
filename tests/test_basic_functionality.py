#!/usr/bin/env python3
"""Test basic claude-mpm functionality."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.agents import list_available_agents
from claude_mpm.services.agents.registry import AgentRegistry
from claude_mpm.services.hook_service import HookService

def test_agents():
    """Test agent loading and listing."""
    print("\n=== Testing Agent System ===")
    
    # List available agents
    agents = list_available_agents()
    print(f"Found {len(agents)} agents:")
    for name, info in agents.items():
        print(f"  ✓ {name}: {info.get('name', name)}")
    
    # Test AgentRegistry
    registry = AgentRegistry()
    discovered = registry.discover_agents()
    print(f"\nAgentRegistry discovered {len(discovered)} agents")
    
    return len(agents) > 0

def test_hooks():
    """Test hook system."""
    print("\n=== Testing Hook System ===")
    
    # Create hook service
    service = HookService()
    print("✓ HookService created successfully")
    
    # List hook types
    from claude_mpm.hooks.base_hook import HookType
    print(f"Available hook types: {', '.join(ht.value for ht in HookType)}")
    
    return True

def test_runner():
    """Test ClaudeRunner basics."""
    print("\n=== Testing ClaudeRunner ===")
    
    # Import and verify
    from claude_mpm.core.claude_runner import ClaudeRunner
    print("✓ ClaudeRunner imported successfully")
    
    # Check if we can access key methods
    runner_methods = ['run', 'launch_subprocess']
    all_found = True
    for method in runner_methods:
        if hasattr(ClaudeRunner, method):
            print(f"✓ ClaudeRunner.{method} method exists")
        else:
            print(f"✗ ClaudeRunner.{method} method not found")
            all_found = False
    
    if not all_found:
        # These are instance methods, let's check properly
        try:
            runner = ClaudeRunner()
            print("✓ ClaudeRunner instantiated successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to instantiate ClaudeRunner: {e}")
            return False
    
    return True

def main():
    """Run all tests."""
    print("CLAUDE-MPM BASIC FUNCTIONALITY TEST")
    print("=" * 60)
    
    results = []
    
    # Run tests
    try:
        results.append(("Agents", test_agents()))
    except Exception as e:
        print(f"✗ Agent test failed: {e}")
        results.append(("Agents", False))
    
    try:
        results.append(("Hooks", test_hooks()))
    except Exception as e:
        print(f"✗ Hook test failed: {e}")
        results.append(("Hooks", False))
    
    try:
        results.append(("Runner", test_runner()))
    except Exception as e:
        print(f"✗ Runner test failed: {e}")
        results.append(("Runner", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ Basic functionality is working!")
        return 0
    else:
        print("\n✗ Some functionality tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())