#!/usr/bin/env python3
"""Test that PM receives properly processed instructions with agent capabilities."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.claude_runner import SimpleClaudeRunner


def test_pm_instructions():
    """Test that PM instructions are properly processed."""
    print("Testing PM Instructions Processing\n")
    print("=" * 60)
    
    # Create runner
    runner = SimpleClaudeRunner()
    
    # Get the system prompt that would be sent to Claude
    system_prompt = runner._create_system_prompt()
    
    print("1. Basic Checks:")
    print(f"   - System prompt loaded: {'✓' if system_prompt else '❌'}")
    print(f"   - Length: {len(system_prompt)} chars")
    print(f"   - Contains placeholder: {'❌ FAIL' if '{{capabilities-list}}' in system_prompt else '✓ PASS'}")
    
    print("\n2. Agent Capabilities Section:")
    if "## Agent Names & Capabilities" in system_prompt:
        print("   ✓ Found agent capabilities section")
        
        # Extract the capabilities section
        lines = system_prompt.split('\n')
        start_idx = None
        for i, line in enumerate(lines):
            if "## Agent Names & Capabilities" in line:
                start_idx = i
                break
        
        if start_idx:
            # Show 30 lines of the capabilities section
            print("\n   Capabilities Section Preview:")
            print("   " + "-" * 56)
            for i in range(start_idx, min(start_idx + 30, len(lines))):
                print(f"   {lines[i]}")
            print("   " + "-" * 56)
    else:
        print("   ❌ Agent capabilities section not found")
    
    print("\n3. Core Agent List Check:")
    expected_agents = [
        "research", "engineer", "qa", "documentation",
        "security", "ops", "version_control", "data_engineer"
    ]
    
    found_agents = []
    for agent in expected_agents:
        if agent in system_prompt:
            found_agents.append(agent)
    
    print(f"   Found {len(found_agents)}/{len(expected_agents)} expected agents:")
    for agent in found_agents:
        print(f"   ✓ {agent}")
    
    missing = set(expected_agents) - set(found_agents)
    if missing:
        print("\n   Missing agents:")
        for agent in missing:
            print(f"   ❌ {agent}")
    
    print("\n4. Key Instruction Elements:")
    key_elements = [
        "Claude Multi-Agent Project Manager",
        "Task Tool",
        "TodoWrite",
        "orchestration and delegation",
        "Agent Name Formats",
        "Core Agents:"
    ]
    
    for element in key_elements:
        if element in system_prompt:
            print(f"   ✓ {element}")
        else:
            print(f"   ❌ {element}")
    
    print("\n5. Summary:")
    if "{{capabilities-list}}" not in system_prompt and "## Agent Names & Capabilities" in system_prompt:
        print("   ✅ SUCCESS: PM instructions are properly processed with dynamic agent capabilities!")
        return True
    else:
        print("   ❌ FAIL: PM instructions are not properly processed")
        return False


if __name__ == "__main__":
    success = test_pm_instructions()
    print("\n" + "=" * 60)
    sys.exit(0 if success else 1)