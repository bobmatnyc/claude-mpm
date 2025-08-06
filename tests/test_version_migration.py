#!/usr/bin/env python3
"""Test agent version migration from old serial format to semantic versioning."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agent_deployment import AgentDeploymentService

def create_old_format_agent(agent_dir: Path, agent_name: str, version_format: str = "serial"):
    """Create a test agent with old version format."""
    if version_format == "serial":
        version_line = 'version: "0002-0005"'
    elif version_format == "missing":
        version_line = ""  # No version field
    else:
        version_line = 'version: "5"'  # Old numeric format
    
    agent_content = f"""---
name: {agent_name}
description: "Test agent with old version format"
{version_line}
author: "claude-mpm@anthropic.com"
created: "2024-01-01T00:00:00Z"
updated: "2024-01-01T00:00:00Z"
tags: [test, migration]
metadata:
  base_version: "0002"
  agent_version: "0005"
  deployment_type: "system"
---

# Test Agent Instructions

This is a test agent using the old {version_format} version format.
"""
    
    agent_file = agent_dir / f"{agent_name}.md"
    agent_file.write_text(agent_content)
    return agent_file

def main():
    """Test version migration functionality."""
    print("Testing agent version migration from old format to semantic versioning...\n")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        agents_dir = temp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        
        # Create test agents with old format
        print("Creating test agents with old version format...")
        old_agents = ["test_engineer", "test_qa", "test_docs"]
        for agent_name in old_agents:
            agent_file = create_old_format_agent(agents_dir, agent_name)
            print(f"  Created: {agent_file.name} with version '0002-0005'")
        
        # Initialize deployment service
        service = AgentDeploymentService()
        
        # First verification - should detect agents needing migration
        print("\n1. Verifying deployment (before migration)...")
        verify_results = service.verify_deployment(temp_path / ".claude")
        
        print(f"  Agents found: {len(verify_results['agents_found'])}")
        print(f"  Agents needing migration: {verify_results.get('agents_needing_migration', [])}")
        
        # Deploy agents - should trigger migration
        print("\n2. Deploying agents (triggering migration)...")
        results = service.deploy_agents(target_dir=agents_dir, force_rebuild=False)
        
        print(f"\n  Deployment results:")
        print(f"    Migrated: {len(results.get('migrated', []))}")
        print(f"    Updated: {len(results['updated'])}")
        print(f"    Skipped: {len(results['skipped'])}")
        
        if results.get('migrated'):
            print("\n  Migrated agents:")
            for agent in results['migrated']:
                print(f"    - {agent['name']}: {agent.get('reason', 'migrated')}")
        
        # Second verification - should show all agents with semantic versions
        print("\n3. Verifying deployment (after migration)...")
        verify_results = service.verify_deployment(temp_path / ".claude")
        
        print(f"  Agents found: {len(verify_results['agents_found'])}")
        print(f"  Agents with semantic versions:")
        for agent in verify_results['agents_found']:
            if agent.get('version'):
                needs_migration = " [still needs migration!]" if agent.get('needs_migration') else ""
                print(f"    - {agent.get('name', agent['file'])}: {agent['version']}{needs_migration}")
        
        # Test idempotency - running again should not trigger migration
        print("\n4. Testing idempotency (running deployment again)...")
        results2 = service.deploy_agents(target_dir=agents_dir, force_rebuild=False)
        
        print(f"  Migrated: {len(results2.get('migrated', []))}")
        print(f"  Updated: {len(results2['updated'])}")
        print(f"  Skipped: {len(results2['skipped'])}")
        
        if results2.get('migrated'):
            print("  WARNING: Agents were migrated again (should be 0)!")
        else:
            print("  ✓ No agents migrated (as expected)")
        
        print("\n✅ Version migration test completed!")

if __name__ == "__main__":
    main()