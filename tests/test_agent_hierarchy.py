#!/usr/bin/env python3
"""
Test script to verify agent hierarchy and project agent precedence.
"""

import sys
from pathlib import Path

# Add src to path to import claude_mpm modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.core.agent_registry import AgentRegistryAdapter

def main():
    print("🔍 Testing Agent Hierarchy and Project Agent Discovery\n")
    
    # Initialize adapter
    adapter = AgentRegistryAdapter()
    
    if not adapter.registry:
        print("❌ Failed to initialize agent registry")
        return 1
    
    # Get agent hierarchy
    hierarchy = adapter.get_agent_hierarchy()
    
    print("📊 Agent Hierarchy:")
    print("=" * 50)
    
    for tier in ['project', 'user', 'system']:
        agents = hierarchy.get(tier, [])
        print(f"\n{tier.upper()} TIER ({len(agents)} agents):")
        if agents:
            for agent in sorted(agents):
                print(f"  - {agent}")
        else:
            print("  (none)")
    
    # Test specific project agents
    print("\n🧪 Specific Project Agent Tests:")
    print("=" * 50)
    
    test_agents = ['test_project_qa', 'custom_engineer', 'qa']
    
    for agent_name in test_agents:
        agent = adapter.registry.get_agent(agent_name)
        if agent:
            print(f"\n✓ Agent '{agent_name}':")
            tier_value = agent.tier.value if hasattr(agent.tier, 'value') else agent.tier
            print(f"    Tier: {tier_value}")
            print(f"    Path: {agent.path}")
            if hasattr(agent, 'version'):
                print(f"    Version: {agent.version}")
            if hasattr(agent, 'description'):
                print(f"    Description: {agent.description}")
            print(f"    Available attributes: {[attr for attr in dir(agent) if not attr.startswith('_')]}")
        else:
            print(f"\n❌ Agent '{agent_name}' not found")
    
    # Test precedence
    print("\n⚖️ Testing Precedence:")
    print("=" * 50)
    
    # Look for QA agents across tiers
    all_agents = adapter.registry.list_agents()
    qa_agents = []
    
    # Handle both dict and list responses
    if isinstance(all_agents, dict):
        # Convert dict values to list if needed
        all_agents = list(all_agents.values())
    
    for agent in all_agents:
        agent_name = agent.name if hasattr(agent, 'name') else str(agent)
        if 'qa' in agent_name.lower():
            qa_agents.append(agent)
    
    if qa_agents:
        print("\nQA Agents found:")
        for qa_agent in qa_agents:
            tier_value = qa_agent.tier.value if hasattr(qa_agent.tier, 'value') else qa_agent.tier
            print(f"  - {qa_agent.name} ({tier_value} tier)")
        
        # Check which one would be selected
        selected_qa = adapter.registry.get_agent('qa')
        if selected_qa:
            tier_value = selected_qa.tier.value if hasattr(selected_qa.tier, 'value') else selected_qa.tier
            print(f"\nSelected QA agent: {selected_qa.name} from {tier_value} tier")
            if tier_value == 'project':
                print("✅ PROJECT tier agent has precedence!")
            else:
                print(f"⚠️  Expected PROJECT tier, got {tier_value}")
        else:
            print("❌ No QA agent selected")
    else:
        print("❌ No QA agents found")
    
    # Show statistics
    stats = adapter.registry.get_statistics()
    print(f"\n📈 Registry Statistics:")
    print("=" * 50)
    print(f"Total agents: {stats['total_agents']}")
    print(f"By tier: {stats['agents_by_tier']}")
    print(f"By type: {stats['agents_by_type']}")
    print(f"Discovery time: {stats['discovery_stats']['discovery_duration']:.3f}s")
    print(f"Cache hits: {stats['discovery_stats']['cache_hits']}")
    print(f"Cache misses: {stats['discovery_stats']['cache_misses']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())