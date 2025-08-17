#!/usr/bin/env python3
"""Debug script to inspect actual agent structure from registry."""

import sys
from pathlib import Path
from pprint import pprint

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.agent_registry import AgentRegistryAdapter
from claude_mpm.core.unified_paths import get_path_manager


def main():
    """Inspect actual agent structure."""
    print("=== Debugging Agent Structure ===\n")
    
    # Get agents from registry
    registry = AgentRegistryAdapter()
    agents = registry.list_agents()
    
    print(f"Found {len(agents)} agents")
    print(f"Agents type: {type(agents)}\n")
    
    # Convert to list if needed
    if isinstance(agents, dict):
        print("Agents is a dictionary, converting to list...")
        agent_list = list(agents.values())
    else:
        agent_list = list(agents)
    
    # Inspect first few agents in detail
    for i, agent in enumerate(agent_list[:3]):  # Just inspect first 3
        print(f"\n--- Agent {i+1} ---")
        print(f"Type: {type(agent)}")
        print(f"Attributes: {dir(agent)}")
        
        # Try to extract key attributes
        attrs_to_check = [
            'agent_id', 'id', 'type', 'name', 'metadata', 
            'description', 'specializations', 'capabilities',
            'configuration', 'tools', 'source_tier', 'source_path'
        ]
        
        print("\nAttribute values:")
        for attr in attrs_to_check:
            if hasattr(agent, attr):
                value = getattr(agent, attr)
                print(f"  {attr}: {value}")
        
        # If it's a dict-like object
        if hasattr(agent, 'keys'):
            print("\nDict keys:")
            print(f"  {list(agent.keys())}")
        
        # Check if it's actually a dict
        if isinstance(agent, dict):
            print("\nAgent is a dictionary:")
            pprint(agent, indent=2)
        
        print("-" * 40)


if __name__ == "__main__":
    main()