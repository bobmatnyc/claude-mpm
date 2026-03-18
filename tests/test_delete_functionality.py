#!/usr/bin/env python3
"""Test script for local agent delete functionality."""

import json
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.local_template_manager import (
    LocalAgentTemplate,
    LocalAgentTemplateManager,
)


def test_delete_functionality():
    """Test the delete functionality of LocalAgentTemplateManager."""
    print("Testing Local Agent Delete Functionality")
    print("=" * 50)

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        manager = LocalAgentTemplateManager(working_directory=temp_path)

        # Create test agents
        print("\n1. Creating test agents...")
        test_agents = [
            {
                "agent_id": "test-agent-1",
                "name": "Test Agent 1",
                "description": "First test agent",
            },
            {
                "agent_id": "test-agent-2",
                "name": "Test Agent 2",
                "description": "Second test agent",
            },
            {
                "agent_id": "test-agent-3",
                "name": "Test Agent 3",
                "description": "Third test agent",
            },
        ]

        for agent_data in test_agents:
            template = manager.create_local_template(
                agent_id=agent_data["agent_id"],
                name=agent_data["name"],
                description=agent_data["description"],
                instructions="Test instructions",
                tier="project",
            )
            manager.save_local_template(template)
            print(f"   Created: {agent_data['agent_id']}")

        # List agents
        print("\n2. Listing created agents...")
        templates = manager.list_local_templates()
        print(f"   Found {len(templates)} agents")
        for t in templates:
            print(f"   - {t.agent_id}: {t.metadata.get('name')}")

        # Test single deletion without backup
        print("\n3. Testing single deletion (no backup)...")
        result = manager.delete_local_template(
            agent_id="test-agent-1",
            tier="project",
            delete_deployment=True,
            backup_first=False,
        )
        if result["success"]:
            print("   ✅ Deleted test-agent-1")
            print(f"   Removed files: {len(result['deleted_files'])}")
        else:
            print(f"   ❌ Failed: {result['errors']}")

        # Test single deletion with backup
        print("\n4. Testing single deletion (with backup)...")
        result = manager.delete_local_template(
            agent_id="test-agent-2",
            tier="project",
            delete_deployment=True,
            backup_first=True,
        )
        if result["success"]:
            print("   ✅ Deleted test-agent-2")
            print(f"   Backup location: {result['backup_location']}")
        else:
            print(f"   ❌ Failed: {result['errors']}")

        # Test system agent protection
        print("\n5. Testing system agent protection...")
        result = manager.delete_local_template(
            agent_id="orchestrator",
            tier="project",
            delete_deployment=True,
            backup_first=False,
        )
        if not result["success"]:
            print("   ✅ Correctly prevented deletion of system agent")
            print(f"   Error: {result['errors'][0]}")
        else:
            print("   ❌ System agent protection failed!")

        # Create more agents for bulk deletion test
        print("\n6. Creating agents for bulk deletion test...")
        bulk_agents = ["bulk-1", "bulk-2", "bulk-3"]
        for agent_id in bulk_agents:
            template = manager.create_local_template(
                agent_id=agent_id,
                name=f"Bulk Agent {agent_id}",
                description=f"Bulk test agent {agent_id}",
                instructions="Bulk test",
                tier="project",
            )
            manager.save_local_template(template)
            print(f"   Created: {agent_id}")

        # Test bulk deletion
        print("\n7. Testing bulk deletion...")
        results = manager.delete_multiple_templates(
            agent_ids=bulk_agents,
            tier="project",
            delete_deployment=True,
            backup_first=True,
        )
        print(f"   Successful: {len(results['successful'])} agents")
        print(f"   Failed: {len(results['failed'])} agents")
        for agent_id in results["successful"]:
            print(f"   ✅ Deleted: {agent_id}")
        for agent_id in results["failed"]:
            print(f"   ❌ Failed: {agent_id}")

        # Final agent count
        print("\n8. Final agent count...")
        remaining = manager.list_local_templates()
        print(f"   Remaining agents: {len(remaining)}")
        for t in remaining:
            print(f"   - {t.agent_id}")

    print("\n" + "=" * 50)
    print("✅ Delete functionality test completed successfully!")


if __name__ == "__main__":
    try:
        test_delete_functionality()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
