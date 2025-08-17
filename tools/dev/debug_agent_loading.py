#!/usr/bin/env python3
"""Debug script to understand agent loading and structure."""

import json
import sys
from pathlib import Path
from pprint import pprint

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.agent_registry import AgentRegistryAdapter


def main():
    """Debug agent loading process."""
    print("=== Debugging Agent Loading ===\n")

    # Load a specific agent file to see its structure
    print("1. Checking raw agent JSON structure:")
    agent_path = (
        Path(__file__).parent.parent / "src/claude_mpm/agents/templates/research.json"
    )
    if agent_path.exists():
        print(f"   Loading {agent_path.name}...")
        try:
            with open(agent_path, "r") as f:
                agent_data = json.load(f)

            print(f"   Top-level keys: {list(agent_data.keys())}")
            print(f"   Agent ID: {agent_data.get('agent_id')}")
            print(f"   Agent type: {agent_data.get('agent_type')}")

            if "metadata" in agent_data:
                print(f"   Metadata keys: {list(agent_data['metadata'].keys())}")

            if "configuration" in agent_data:
                print(
                    f"   Configuration keys: {list(agent_data['configuration'].keys())}"
                )
                if "tools" in agent_data["configuration"]:
                    print(f"   Tools: {agent_data['configuration']['tools']}")

            if "capabilities" in agent_data:
                print(
                    f"   Capabilities keys: {list(agent_data['capabilities'].keys())}"
                )

        except Exception as e:
            print(f"   Error loading agent: {e}")

    print("\n2. Checking AgentRegistry internals:")
    registry = AgentRegistryAdapter()

    # Check internal registry structure
    if hasattr(registry, "registry"):
        print(f"   Has internal registry: Yes")
        internal_reg = registry.registry
        print(f"   Internal registry type: {type(internal_reg)}")

        # Try to access agents directly
        if hasattr(internal_reg, "_agents"):
            print(f"   Has _agents attribute: Yes")
            agents = internal_reg._agents
            print(f"   _agents type: {type(agents)}")
            if agents:
                first_key = list(agents.keys())[0]
                first_agent = agents[first_key]
                print(f"   First agent type: {type(first_agent)}")
                print(f"   First agent: {first_agent}")

    print("\n3. Checking loaded agent objects from list_agents:")
    # Get agents and inspect structure
    agents = registry.list_agents()
    print(f"   list_agents() returned type: {type(agents)}")
    print(f"   Number of agents: {len(agents)}")

    if isinstance(agents, dict) and agents:
        # Look for the research agent specifically
        research_agent = None
        for key, agent in agents.items():
            if isinstance(agent, dict) and agent.get("type") == "research":
                research_agent = agent
                break

        if research_agent:
            print(f"\n   Research agent structure:")
            print(f"   Type: {type(research_agent)}")
            print("   Keys:", list(research_agent.keys()))

            # Check all possible locations for tools
            print("\n   Looking for tools in research agent:")
            if "tools" in research_agent:
                print(f"   Tools (direct): {research_agent['tools']}")
            if "configuration" in research_agent:
                print(f"   Configuration type: {type(research_agent['configuration'])}")
                if (
                    isinstance(research_agent["configuration"], dict)
                    and "tools" in research_agent["configuration"]
                ):
                    print(
                        f"   Tools (in configuration dict): {research_agent['configuration']['tools']}"
                    )

            # Check capabilities
            if "capabilities" in research_agent:
                print(f"\n   Capabilities type: {type(research_agent['capabilities'])}")
                if isinstance(research_agent["capabilities"], dict):
                    print(
                        f"   Capabilities keys: {list(research_agent['capabilities'].keys())}"
                    )


if __name__ == "__main__":
    main()
