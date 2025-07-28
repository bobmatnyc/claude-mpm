#!/usr/bin/env python3
"""Test agent deployment with semantic versioning."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agent_deployment import AgentDeploymentService

def main():
    """Test agent deployment service."""
    service = AgentDeploymentService()
    
    # List available agents
    print("Available agents:")
    agents = service.list_available_agents()
    for agent in agents:
        print(f"  - {agent['name']}: version {agent.get('version', 'unknown')}")
    
    # Deploy agents (without force to test version comparison)
    print("\nDeploying agents...")
    results = service.deploy_agents(force_rebuild=False)
    
    print(f"\nDeployment results:")
    print(f"  Target: {results['target_dir']}")
    print(f"  Deployed: {len(results['deployed'])}")
    print(f"  Updated: {len(results['updated'])}")
    print(f"  Migrated: {len(results.get('migrated', []))}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Errors: {len(results['errors'])}")
    
    if results.get('migrated'):
        print("\nMigrated agents (from old to semantic versioning):")
        for agent in results['migrated']:
            print(f"  - {agent['name']}: {agent.get('reason', 'migrated')}")
    
    if results['updated']:
        print("\nUpdated agents:")
        for agent in results['updated']:
            print(f"  - {agent['name']}")
    
    if results['deployed']:
        print("\nNewly deployed agents:")
        for agent in results['deployed']:
            print(f"  - {agent['name']}")
    
    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")
    
    # Verify deployment
    print("\n\nVerifying deployment...")
    verify_results = service.verify_deployment()
    
    print(f"\nAgents found: {len(verify_results['agents_found'])}")
    if verify_results.get('agents_needing_migration'):
        print(f"Agents needing migration: {verify_results['agents_needing_migration']}")
    
    for agent in verify_results['agents_found']:
        version_info = f" (version: {agent.get('version', 'unknown')})"
        migration_info = " [needs migration]" if agent.get('needs_migration') else ""
        print(f"  - {agent.get('name', agent['file'])}{version_info}{migration_info}")

if __name__ == "__main__":
    main()