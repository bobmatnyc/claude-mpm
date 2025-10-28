#!/usr/bin/env python3
"""Debug script to see what's in agent data."""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def debug_agent_data():
    """Debug what's in the agent data."""

    print("Debugging Agent Data Structure")
    print("=" * 50)

    # Initialize framework loader
    framework_loader = FrameworkLoader()

    # Parse a single agent to see full structure
    test_agent_file = Path(".claude/agents/engineer.md")

    if test_agent_file.exists():
        print(f"\n1. Raw metadata from {test_agent_file}:")
        metadata = framework_loader._parse_agent_metadata(test_agent_file)

        if metadata:
            # Show all keys
            print(f"  Keys in metadata: {list(metadata.keys())}")
            print(f"  Has memory_routing: {'memory_routing' in metadata}")

            # Show structure
            print("\n  Full structure (JSON):")
            print(json.dumps(metadata, indent=2, default=str)[:1000] + "...")

    # Now test what happens in capabilities generation
    print("\n2. Testing in capabilities generation context:")

    # We need to look at what's actually in all_agents
    # Let's monkey-patch the method to debug it

    def debug_capabilities():
        # Call the original method but intercept

        # Try to get from cache first
        cached_capabilities = framework_loader._cache_manager.get_capabilities()
        if cached_capabilities is not None:
            print("  Using cached capabilities")
            return cached_capabilities

        # Get agents directories
        agents_dirs = [
            (Path(".claude/agents"), 0),  # Project agents (priority 0)
            (Path.home() / ".claude-mpm/agents", 1),  # User agents (priority 1)
        ]

        all_agents = {}
        for potential_dir, priority in agents_dirs:
            if potential_dir.exists():
                for agent_file in potential_dir.glob("*.md"):
                    if agent_file.name.startswith("."):
                        continue

                    agent_data = framework_loader._parse_agent_metadata(agent_file)
                    if agent_data:
                        agent_id = agent_data["id"]

                        # Debug output
                        if agent_id == "engineer":
                            print(
                                f"\n  Engineer agent data keys: {list(agent_data.keys())}"
                            )
                            print(
                                f"  Has memory_routing: {'memory_routing' in agent_data}"
                            )
                            if "memory_routing" in agent_data:
                                print(
                                    f"  Memory routing: {agent_data['memory_routing'].get('description', 'No desc')[:60]}..."
                                )

                        if (
                            agent_id not in all_agents
                            or priority < all_agents[agent_id][1]
                        ):
                            all_agents[agent_id] = (agent_data, priority)

        # Extract deployed agents
        deployed_agents = [agent_data for agent_data, _ in all_agents.values()]

        # Check engineer in deployed_agents
        for agent in deployed_agents:
            if agent["id"] == "engineer":
                print("\n  Engineer in deployed_agents:")
                print(f"    Keys: {list(agent.keys())}")
                print(f"    Has memory_routing: {'memory_routing' in agent}")
                break

        return "Debug complete"

    # Run the debug version
    debug_capabilities()

    print("\n" + "=" * 50)
    print("Debug complete!")


if __name__ == "__main__":
    debug_agent_data()
