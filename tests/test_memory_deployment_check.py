#!/usr/bin/env python3
"""Test that memory injection only loads memories for deployed agents."""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_memory_deployment_check():
    """Test that memories are only loaded for deployed agents."""

    # Set up logging to capture messages
    logging.basicConfig(level=logging.DEBUG)

    # Create framework loader
    loader = FrameworkLoader()

    # Get deployed agents
    deployed = loader._get_deployed_agents()
    print("\n=== Deployed Agents Found ===")
    print(f"Total: {len(deployed)}")
    for agent in sorted(deployed):
        print(f"  - {agent}")

    # Check memory files
    print("\n=== Memory Files Analysis ===")

    # Check user memories
    user_memories_dir = Path.home() / ".claude-mpm" / "memories"
    if user_memories_dir.exists():
        print(f"\nUser memories in {user_memories_dir}:")
        for memory_file in user_memories_dir.glob("*_memories.md"):
            if memory_file.name == "PM_memories.md":
                print(f"  ✓ {memory_file.name} - PM (always loaded)")
                continue

            # Extract agent name (remove "_memories" suffix)
            agent_name = memory_file.stem[:-9]

            if agent_name in deployed:
                print(f"  ✓ {memory_file.name} - Agent '{agent_name}' is deployed")
            else:
                print(
                    f"  ✗ {memory_file.name} - Agent '{agent_name}' NOT deployed (should be skipped)"
                )

    # Check project memories
    project_memories_dir = Path.cwd() / ".claude-mpm" / "memories"
    if project_memories_dir.exists():
        print(f"\nProject memories in {project_memories_dir}:")
        for memory_file in project_memories_dir.glob("*_memories.md"):
            if memory_file.name == "PM_memories.md":
                print(f"  ✓ {memory_file.name} - PM (always loaded)")
                continue

            # Extract agent name (remove "_memories" suffix)
            agent_name = memory_file.stem[:-9]

            if agent_name in deployed:
                print(f"  ✓ {memory_file.name} - Agent '{agent_name}' is deployed")
            else:
                print(
                    f"  ✗ {memory_file.name} - Agent '{agent_name}' NOT deployed (should be skipped)"
                )

    # Now test actual loading with mock content
    print("\n=== Testing Actual Load Process ===")

    # NEW ARCHITECTURE: Agent memories are no longer loaded at framework time
    # They are loaded at agent deployment time via append_agent_memory()
    # So we just verify the framework content structure
    content = loader.framework_content

    # Capture log messages (not needed anymore, but keep for reference)
    log_messages = []

    # Analyze framework content (NEW ARCHITECTURE)
    print("\n=== Framework Content Analysis ===")
    print("\nNEW ARCHITECTURE:")
    print("  - Agent memories are NOT loaded into framework content")
    print("  - Agent memories are loaded at deployment time")
    print("  - Only PM memories are in framework content")

    # Verify specific cases
    print("\n=== Verification ===")

    # NEW ARCHITECTURE: Agent memories are not loaded at framework time
    # Check that PM memories are in framework content
    pm_loaded = "actual_memories" in content
    if pm_loaded:
        print("✓ PM memories are in framework content")
    else:
        print("✗ PM memories NOT in framework content (should always be there)")

    # Check that agent memories are NOT in framework content
    agent_memories = content.get("agent_memories", {})
    if len(agent_memories) == 0:
        print("✓ Agent memories NOT in framework content (correct)")
    else:
        print(
            f"✗ Agent memories found in framework content: {list(agent_memories.keys())}"
        )
        print(
            "  Agent memories should be loaded at deployment time, not framework time"
        )

    # Check actual content
    if "actual_memories" in content:
        print(
            f"✓ PM memories injected into content ({len(content['actual_memories'])} bytes)"
        )

    # NEW ARCHITECTURE: Agent memories should NOT be in framework content
    # They are loaded at deployment time and appended to agent files
    if "agent_memories" in content and len(content["agent_memories"]) > 0:
        print("⚠ Agent memories found in framework content (should NOT be there):")
        for agent_name in content["agent_memories"]:
            print(
                f"  - {agent_name}: {len(content['agent_memories'][agent_name])} bytes"
            )
        print("  NOTE: Agent memories are now loaded at deployment time")
    else:
        print("✓ No agent memories in framework (correct - now in agent files)")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_memory_deployment_check()
