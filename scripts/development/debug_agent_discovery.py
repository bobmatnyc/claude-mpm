#!/usr/bin/env python3
"""Debug agent discovery issue."""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.services.agents.deployment.multi_source_deployment_service import (
    MultiSourceAgentDeploymentService,
)


def debug_discovery():
    """Debug agent discovery."""
    print("=" * 60)
    print("DEBUG AGENT DISCOVERY")
    print("=" * 60)

    service = MultiSourceAgentDeploymentService()

    # Discover agents from all sources
    print("\n📊 Discovering agents from all sources...")
    all_agents = service.discover_agents_from_all_sources()

    print(f"\nFound agents from sources: {len(all_agents)} unique names")

    # Show first few agents
    for i, (name, sources) in enumerate(list(all_agents.items())[:3]):
        print(f"\n{i+1}. Agent: {name}")
        if isinstance(sources, list):
            print(f"   Sources: {len(sources)} source(s)")
            for j, source in enumerate(sources):
                if isinstance(source, dict):
                    print(
                        f"   [{j}] Version: {source.get('agent_version', 'unknown')}, Source: {source.get('source', 'unknown')}"
                    )
                else:
                    print(f"   [{j}] Type: {type(source)}")
        else:
            print(f"   Type: {type(sources)}")

    # Check deployed agents
    project_agents_dir = Path.cwd() / ".claude" / "agents"
    if project_agents_dir.exists():
        deployed = list(project_agents_dir.glob("*.md"))
        print(f"\n✅ Found {len(deployed)} deployed agents")

        # Check for orphans
        orphaned = service.detect_orphaned_agents(project_agents_dir, all_agents)
        print(f"\n⚠️  Orphaned agents detected: {len(orphaned)}")

        if orphaned:
            print("\nFirst orphaned agent details:")
            first_orphan = orphaned[0]
            print(f"  Name: {first_orphan['name']}")
            print(f"  In all_agents? {first_orphan['name'] in all_agents}")

            # Debug why it's considered orphaned
            if first_orphan["name"] not in all_agents:
                print("  Reason: Not found in all_agents dictionary")
                print("\n  Available agent names:")
                for name in sorted(all_agents.keys())[:10]:
                    print(f"    - {name}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    debug_discovery()
