#!/usr/bin/env python3
"""Test that SimpleClaudeRunner processes the {{capabilities-list}} placeholder at runtime."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.simple_runner import SimpleClaudeRunner


def test_runtime_capabilities():
    """Test that system instructions contain processed agent capabilities."""
    print("Testing runtime capabilities processing...\n")
    
    # Create a runner instance
    runner = SimpleClaudeRunner()
    
    # Check if system instructions were loaded
    if not runner.system_instructions:
        print("❌ System instructions not loaded")
        return False
    
    print(f"✓ System instructions loaded ({len(runner.system_instructions)} chars)")
    
    # Check if the placeholder is still present (it shouldn't be)
    if "{{capabilities-list}}" in runner.system_instructions:
        print("❌ Template placeholder {{capabilities-list}} still present - not processed!")
        return False
    
    print("✓ Template placeholder {{capabilities-list}} has been processed")
    
    # Check if agent capabilities are present
    expected_agents = [
        "research", "engineer", "qa", "documentation",
        "security", "ops", "version-control", "data-engineer"
    ]
    
    found_agents = []
    for agent in expected_agents:
        if agent in runner.system_instructions.lower():
            found_agents.append(agent)
    
    print(f"\nFound {len(found_agents)}/{len(expected_agents)} expected agents:")
    for agent in found_agents:
        print(f"  ✓ {agent}")
    
    missing_agents = set(expected_agents) - set(found_agents)
    if missing_agents:
        print("\nMissing agents:")
        for agent in missing_agents:
            print(f"  ❌ {agent}")
    
    # Check for key capability markers
    capability_markers = [
        "## Available Specialized Agents",
        "Task(description=",
        "subagent_type="
    ]
    
    print("\nChecking for capability section markers:")
    for marker in capability_markers:
        if marker in runner.system_instructions:
            print(f"  ✓ Found: {marker}")
        else:
            print(f"  ❌ Missing: {marker}")
    
    # Extract a sample of the capabilities section
    print("\nSample of processed capabilities section:")
    lines = runner.system_instructions.split('\n')
    in_capabilities = False
    sample_lines = []
    
    for i, line in enumerate(lines):
        if "## Available Specialized Agents" in line:
            in_capabilities = True
            sample_lines = lines[i:i+20]  # Get 20 lines after the header
            break
    
    if sample_lines:
        print("-" * 60)
        print('\n'.join(sample_lines))
        print("-" * 60)
    else:
        print("Could not find capabilities section")
    
    return True


if __name__ == "__main__":
    success = test_runtime_capabilities()
    sys.exit(0 if success else 1)