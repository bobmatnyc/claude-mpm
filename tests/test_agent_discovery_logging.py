#!/usr/bin/env python3
"""Test script to verify agent discovery logging is clear and not duplicated."""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging to see INFO messages
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def test_multi_source_discovery():
    """Test multi-source agent discovery logging."""
    print("=" * 60)
    print("Testing Multi-Source Agent Discovery Logging")
    print("=" * 60)

    from claude_mpm.services.agents.deployment.multi_source_deployment_service import (
        MultiSourceAgentDeploymentService,
    )

    # Create service and discover agents
    service = MultiSourceAgentDeploymentService()

    print("\n🔍 Discovering agents from all sources...\n")
    agents_by_name = service.discover_agents_from_all_sources()

    print(f"\n✅ Discovery complete. Found {len(agents_by_name)} unique agents")

    # Show the discovered agents by source
    source_counts = {}
    for _agent_name, agent_versions in agents_by_name.items():
        for agent_info in agent_versions:
            source = agent_info.get("source", "unknown")
            if source not in source_counts:
                source_counts[source] = 0
            source_counts[source] += 1

    print("\n📊 Agent distribution by source:")
    for source, count in source_counts.items():
        print(f"   - {source}: {count} agents")


def test_single_source_discovery():
    """Test single source discovery logging."""
    print("\n" + "=" * 60)
    print("Testing Single Source Discovery Logging")
    print("=" * 60)

    from claude_mpm.config.paths import paths
    from claude_mpm.services.agents.deployment.agent_discovery_service import (
        AgentDiscoveryService,
    )

    templates_dir = paths.agents_dir / "templates"

    if templates_dir.exists():
        print(f"\n🔍 Discovering agents from single source: {templates_dir}\n")

        discovery_service = AgentDiscoveryService(templates_dir)

        # Test with logging enabled (default)
        print("Test 1: With logging enabled (default):")
        agents = discovery_service.list_available_agents()
        print(f"   Found {len(agents)} agents")

        # Test with logging disabled
        print("\nTest 2: With logging disabled:")
        agents = discovery_service.list_available_agents(log_discovery=False)
        print(f"   Found {len(agents)} agents (no log message above)")
    else:
        print(f"⚠️  Templates directory not found: {templates_dir}")


def test_agent_deployment_service():
    """Test that AgentDeploymentService initialization doesn't cause duplicate logs."""
    print("\n" + "=" * 60)
    print("Testing AgentDeploymentService Initialization")
    print("=" * 60)

    from claude_mpm.services.agents.deployment.agent_deployment import (
        AgentDeploymentService,
    )

    print("\n🔍 Initializing AgentDeploymentService...\n")

    # This should not cause duplicate discovery logs
    service = AgentDeploymentService()

    print("\n✅ Service initialized successfully")
    print(f"   Templates dir: {service.templates_dir}")
    print(f"   Base agent path: {service.base_agent_path}")


if __name__ == "__main__":
    # Run all tests
    test_multi_source_discovery()
    test_single_source_discovery()
    test_agent_deployment_service()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    print("\n📝 Summary:")
    print("- Multi-source discovery should show clear source-specific messages")
    print("- Single source discovery can optionally suppress logging")
    print("- AgentDeploymentService init should not trigger discovery logs")
    print("- No duplicate 'available agent templates' messages should appear")
