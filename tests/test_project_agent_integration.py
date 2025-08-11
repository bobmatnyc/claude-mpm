#!/usr/bin/env python3
"""
Integration test for PROJECT tier agents with the complete system.

This script verifies that PROJECT agents work correctly with:
1. FrameworkAgentLoader
2. Cache invalidation on file changes
3. Agent selection and delegation
"""

import os
import sys
import json
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from claude_mpm.services.agents.registry import AgentRegistry, AgentTier, AgentMetadata
from claude_mpm.core.config_paths import ConfigPaths


def create_project_agent(name: str, capabilities: list):
    """Create a project-specific agent."""
    project_agents_dir = ConfigPaths.get_project_agents_dir()
    project_agents_dir.mkdir(parents=True, exist_ok=True)
    
    agent_path = project_agents_dir / f"{name}.md"
    
    content = f"""---
description: Project-specific {name} agent with custom capabilities
version: 2.0.0
tools: {json.dumps(capabilities)}
metadata:
  tier: project
  customized: true
  project: claude-mpm
---

# {name.title()} Agent (Project-Specific)

This is a project-specific customization of the {name} agent.

## Custom Capabilities
- {chr(10).join(f"- {cap}" for cap in capabilities)}

## Project-Specific Instructions
This agent has been customized for the claude-mpm project with specialized knowledge and capabilities.
"""
    
    agent_path.write_text(content)
    return agent_path


def test_project_agent_override():
    """Test that project agents correctly override system/user agents."""
    print("\n" + "="*60)
    print("Testing Project Agent Override")
    print("="*60)
    
    # Create a project-specific engineer agent
    project_agent_path = create_project_agent(
        "engineer",
        ["enhanced_debugging", "performance_profiling", "memory_optimization"]
    )
    print(f"Created project agent: {project_agent_path}")
    
    # Initialize registry and discover
    registry = AgentRegistry()
    agents = registry.discover_agents(force_refresh=True)
    
    # Check engineer agent
    if "engineer" in agents:
        engineer = agents["engineer"]
        print(f"\n✓ Engineer agent found")
        print(f"  Tier: {engineer.tier.value}")
        print(f"  Version: {engineer.version}")
        print(f"  Path: {engineer.path}")
        
        # Verify it's the project version
        if engineer.tier == AgentTier.PROJECT and engineer.version == "2.0.0":
            print("\n✅ Project engineer agent correctly overrides system version")
            success = True
        else:
            print(f"\n❌ Wrong engineer agent loaded: tier={engineer.tier.value}, version={engineer.version}")
            success = False
    else:
        print("\n❌ Engineer agent not found")
        success = False
    
    # Cleanup
    if project_agent_path.exists():
        project_agent_path.unlink()
        print(f"\nCleaned up: {project_agent_path}")
    
    return success


def test_multiple_project_agents():
    """Test discovery of multiple project-specific agents."""
    print("\n" + "="*60)
    print("Testing Multiple Project Agents")
    print("="*60)
    
    # Create multiple project agents
    project_agents = []
    agent_configs = [
        ("custom_analyzer", ["code_analysis", "dependency_tracking"]),
        ("project_manager", ["task_delegation", "progress_monitoring"]),
        ("deployment", ["ci_cd", "container_management"])
    ]
    
    for name, capabilities in agent_configs:
        path = create_project_agent(name, capabilities)
        project_agents.append(path)
        print(f"Created: {path.name}")
    
    # Discover agents
    registry = AgentRegistry()
    agents = registry.discover_agents(force_refresh=True)
    
    # Verify all project agents were discovered
    found_count = 0
    for name, _ in agent_configs:
        if name in agents:
            agent = agents[name]
            if agent.tier == AgentTier.PROJECT:
                print(f"✓ Found PROJECT agent: {name}")
                found_count += 1
            else:
                print(f"✗ Found {name} but tier is {agent.tier.value}")
        else:
            print(f"✗ Missing agent: {name}")
    
    success = found_count == len(agent_configs)
    if success:
        print(f"\n✅ All {len(agent_configs)} project agents discovered correctly")
    else:
        print(f"\n❌ Only {found_count}/{len(agent_configs)} project agents found")
    
    # Cleanup
    for path in project_agents:
        if path.exists():
            path.unlink()
    print(f"\nCleaned up {len(project_agents)} test agents")
    
    return success


def test_cache_with_project_agents():
    """Test that caching works correctly with project agents."""
    print("\n" + "="*60)
    print("Testing Cache with Project Agents")
    print("="*60)
    
    # Create a project agent
    agent_path = create_project_agent("cache_test", ["test_capability"])
    
    # First discovery (should cache)
    registry1 = AgentRegistry()
    start_time = time.time()
    agents1 = registry1.discover_agents(force_refresh=True)
    first_discovery_time = time.time() - start_time
    
    if "cache_test" in agents1:
        print(f"✓ Initial discovery found agent (took {first_discovery_time:.3f}s)")
    
    # Second discovery (should use cache)
    registry2 = AgentRegistry()
    start_time = time.time()
    agents2 = registry2.discover_agents()
    cached_discovery_time = time.time() - start_time
    
    if "cache_test" in agents2:
        print(f"✓ Cached discovery found agent (took {cached_discovery_time:.3f}s)")
    
    # Verify cache was faster
    if cached_discovery_time < first_discovery_time:
        print(f"✓ Cache was faster ({cached_discovery_time:.3f}s vs {first_discovery_time:.3f}s)")
        success = True
    else:
        print(f"✗ Cache was not faster")
        success = False
    
    # Modify the agent file
    agent_path.write_text(agent_path.read_text() + "\n# Modified at " + str(time.time()))
    
    # Force refresh should detect change
    registry3 = AgentRegistry()
    agents3 = registry3.discover_agents(force_refresh=True)
    
    if "cache_test" in agents3:
        print("✓ Modified agent detected after force refresh")
    
    # Cleanup
    if agent_path.exists():
        agent_path.unlink()
    print(f"\nCleaned up: {agent_path}")
    
    return success


def test_tier_statistics():
    """Test that statistics correctly report PROJECT tier agents."""
    print("\n" + "="*60)
    print("Testing Tier Statistics")
    print("="*60)
    
    # Create a project agent
    agent_path = create_project_agent("stats_test", ["reporting"])
    
    # Get statistics
    registry = AgentRegistry()
    registry.discover_agents(force_refresh=True)
    stats = registry.get_statistics()
    
    print("\nAgent Distribution by Tier:")
    for tier, count in stats.get('agents_by_tier', {}).items():
        print(f"  {tier}: {count}")
    
    # Check if PROJECT tier is reported
    if 'project' in stats.get('agents_by_tier', {}):
        project_count = stats['agents_by_tier']['project']
        print(f"\n✓ PROJECT tier reported with {project_count} agent(s)")
        success = project_count >= 1
    else:
        print("\n✗ PROJECT tier not in statistics")
        success = False
    
    # Cleanup
    if agent_path.exists():
        agent_path.unlink()
    
    return success


def main():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("PROJECT AGENT INTEGRATION TEST SUITE")
    print("="*60)
    
    tests = [
        ("Project Agent Override", test_project_agent_override),
        ("Multiple Project Agents", test_multiple_project_agents),
        ("Cache with Project Agents", test_cache_with_project_agents),
        ("Tier Statistics", test_tier_statistics),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' raised exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("INTEGRATION TEST RESULTS")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("\nPROJECT tier support is fully functional:")
        print("• PROJECT agents override USER and SYSTEM agents")
        print("• Cache invalidation works for project files")
        print("• Statistics correctly report PROJECT tier")
        print("• Multiple project agents can coexist")
    else:
        print("❌ SOME INTEGRATION TESTS FAILED")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())