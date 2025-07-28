#!/usr/bin/env python3
"""Test the complete migration flow"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.services.agent_deployment import AgentDeploymentService
from pathlib import Path
import logging

# Set up verbose logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def main():
    """Test migration flow"""
    service = AgentDeploymentService()
    
    # First, let's check a specific agent
    print("=== Checking Research Agent ===")
    agent_file = Path.home() / ".claude" / "agents" / "research.md"
    template_file = Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "templates" / "research.json"
    
    if agent_file.exists() and template_file.exists():
        # Check if update needed
        needs_update, reason = service._check_agent_needs_update(agent_file, template_file, (0, 2, 0))
        print(f"Needs update: {needs_update}")
        print(f"Reason: {reason}")
    
    # Now run deployment without force_rebuild
    print("\n=== Running Deployment (without force_rebuild) ===")
    results = service.deploy_agents(force_rebuild=False)
    
    print(f"\nResults:")
    print(f"  Deployed: {len(results['deployed'])}")
    print(f"  Updated: {len(results['updated'])}")
    print(f"  Migrated: {len(results['migrated'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Errors: {len(results['errors'])}")
    
    if results['migrated']:
        print(f"\nMigrated agents:")
        for agent in results['migrated']:
            print(f"  - {agent['name']}: {agent['reason']}")

if __name__ == "__main__":
    main()