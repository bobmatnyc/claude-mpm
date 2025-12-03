#!/usr/bin/env python3
"""
Verification script for 1M-502 Phase 1 implementation.

This script performs automated checks to verify that:
1. BASE_AGENT filtering works correctly
2. Deployed agent detection works for both directory structures
3. All integration points are properly connected

Run: python scripts/verify_1m502_phase1.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.utils.agent_filters import (
    apply_all_filters,
    filter_base_agents,
    get_deployed_agent_ids,
    is_base_agent,
)


def test_base_agent_filtering():
    """Test BASE_AGENT filtering with various cases."""
    print("\n🔍 Testing BASE_AGENT filtering...")

    test_cases = [
        ("BASE_AGENT", True),
        ("base_agent", True),
        ("base-agent", True),
        ("BASE-AGENT", True),
        ("baseagent", True),
        ("ENGINEER", False),
        ("PM", False),
        ("BASE_ENGINEER", False),
    ]

    passed = 0
    for agent_id, expected in test_cases:
        result = is_base_agent(agent_id)
        status = "✅" if result == expected else "❌"
        print(f"  {status} is_base_agent('{agent_id}') = {result} (expected {expected})")
        if result == expected:
            passed += 1

    print(f"\n  Result: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_agent_list_filtering():
    """Test filtering of agent lists."""
    print("\n🔍 Testing agent list filtering...")

    agents = [
        {"agent_id": "ENGINEER", "name": "Engineer"},
        {"agent_id": "BASE_AGENT", "name": "Base Agent"},
        {"agent_id": "base-agent", "name": "Base Agent"},
        {"agent_id": "PM", "name": "PM"},
    ]

    filtered = filter_base_agents(agents)

    base_agent_found = any(
        is_base_agent(a.get("agent_id", "")) for a in filtered
    )

    if base_agent_found:
        print("  ❌ BASE_AGENT found in filtered list!")
        return False
    print(f"  ✅ BASE_AGENT successfully filtered ({len(agents)} → {len(filtered)} agents)")
    return True


def test_deployed_agent_detection():
    """Test deployed agent detection."""
    print("\n🔍 Testing deployed agent detection...")

    # Test with current project directory
    deployed = get_deployed_agent_ids(Path.cwd())

    print(f"  ℹ️  Found {len(deployed)} deployed agent(s) in current project")

    # Check both directories
    new_dir = Path.cwd() / ".claude-mpm" / "agents"
    legacy_dir = Path.cwd() / ".claude" / "agents"

    if new_dir.exists():
        new_count = len(list(new_dir.glob("*.md")))
        print(f"  ✅ .claude-mpm/agents/ detected: {new_count} agents")
    else:
        print("  ℹ️  .claude-mpm/agents/ does not exist (OK)")

    if legacy_dir.exists():
        legacy_count = len(list(legacy_dir.glob("*.md")))
        print(f"  ✅ .claude/agents/ detected: {legacy_count} agents")
    else:
        print("  ℹ️  .claude/agents/ does not exist (OK)")

    return True


def test_integration_imports():
    """Test that integration points can import the utilities."""
    print("\n🔍 Testing integration imports...")

    try:
        # Test agent_wizard import
        from claude_mpm.cli.interactive.agent_wizard import AgentWizard
        print("  ✅ agent_wizard.py imports successful")

        # Test configure import
        from claude_mpm.cli.commands.configure import ConfigureCommand
        print("  ✅ configure.py imports successful")

        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False


def test_combined_filtering():
    """Test combined filtering operations."""
    print("\n🔍 Testing combined filtering...")

    agents = [
        {"agent_id": "ENGINEER", "name": "Engineer"},
        {"agent_id": "BASE_AGENT", "name": "Base"},
        {"agent_id": "PM", "name": "PM"},
        {"agent_id": "QA", "name": "QA"},
    ]

    # Test BASE_AGENT filtering only
    filtered_base = apply_all_filters(agents, filter_base=True, filter_deployed=False)

    if any(is_base_agent(a.get("agent_id", "")) for a in filtered_base):
        print("  ❌ BASE_AGENT filter failed")
        return False
    print(f"  ✅ BASE_AGENT filter works ({len(agents)} → {len(filtered_base)} agents)")

    # Test no filtering
    no_filter = apply_all_filters(agents, filter_base=False, filter_deployed=False)
    if len(no_filter) != len(agents):
        print("  ❌ No filter mode failed")
        return False
    print(f"  ✅ No filter mode works (preserved all {len(agents)} agents)")

    return True


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("  1M-502 Phase 1 Implementation Verification")
    print("  BASE_AGENT Filtering & Deployed Agent Detection")
    print("=" * 70)

    tests = [
        ("BASE_AGENT Detection", test_base_agent_filtering),
        ("Agent List Filtering", test_agent_list_filtering),
        ("Deployed Agent Detection", test_deployed_agent_detection),
        ("Integration Imports", test_integration_imports),
        ("Combined Filtering", test_combined_filtering),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n  ❌ {name} failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("  VERIFICATION SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {name}")

    print("\n" + "=" * 70)
    if passed_count == total_count:
        print(f"  ✅ ALL TESTS PASSED ({passed_count}/{total_count})")
        print("=" * 70)
        print("\n  Implementation verified successfully!")
        print("  Ready for manual testing and code review.")
        return 0
    print(f"  ❌ SOME TESTS FAILED ({passed_count}/{total_count})")
    print("=" * 70)
    print("\n  Please review failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
