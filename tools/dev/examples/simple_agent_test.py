#!/usr/bin/env python3
"""
Simple test script to verify PROJECT tier agent functionality.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.core.agent_registry import AgentRegistryAdapter

def main():
    print("🧪 Simple Agent Hierarchy Test\n")
    
    # Initialize adapter
    adapter = AgentRegistryAdapter()
    
    if not adapter.registry:
        print("❌ Failed to initialize agent registry")
        return 1
    
    # Get hierarchy
    hierarchy = adapter.get_agent_hierarchy()
    
    print("📊 Agent Counts by Tier:")
    for tier, agents in hierarchy.items():
        print(f"  {tier.upper()}: {len(agents)} agents")
    
    print(f"\n📋 PROJECT tier agents:")
    for agent in hierarchy.get('project', []):
        print(f"  - {agent}")
    
    # Test specific agents
    print(f"\n🔍 Testing specific agents:")
    
    # Test our project QA agent
    test_qa = adapter.registry.get_agent('test_project_qa')
    if test_qa:
        print(f"✅ test_project_qa found:")
        print(f"   Tier: {test_qa.tier}")
        print(f"   Path: {test_qa.path}")
    else:
        print("❌ test_project_qa not found")
    
    # Test precedence by checking what 'qa' resolves to
    qa_agent = adapter.registry.get_agent('qa')
    if qa_agent:
        print(f"✅ qa agent resolved:")
        print(f"   Name: {qa_agent.name}")
        print(f"   Tier: {qa_agent.tier}")
        print(f"   Path: {qa_agent.path}")
    else:
        print("❌ qa agent not found")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())