#!/usr/bin/env python3
"""Test agent loading functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.agents.agent_loader import _get_loader, list_available_agents

def main():
    """Test agent loading."""
    try:
        # Initialize loader
        loader = _get_loader()
        print(f"✅ Loaded {len(loader._agent_registry)} agents")
        
        # List available agents
        agents = list_available_agents()
        print("\nAvailable agents:")
        for agent_id, agent_info in agents.items():
            print(f"  - {agent_id}: {agent_info['name']} ({agent_info['category']})")
        
        # Test loading a specific agent
        test_agent = "documentation_agent"
        prompt = loader.get_agent_prompt(test_agent)
        if prompt:
            print(f"\n✅ Successfully loaded '{test_agent}' agent prompt ({len(prompt)} chars)")
        else:
            print(f"\n❌ Failed to load '{test_agent}' agent prompt")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())