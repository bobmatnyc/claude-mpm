#!/usr/bin/env python3
"""Trace deployment with extra logging"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.services.agents.deployment import AgentDeploymentService
from pathlib import Path
import logging

# Monkey patch to add extra logging
original_deploy = AgentDeploymentService.deploy_agents

def traced_deploy(self, target_dir=None, force_rebuild=False):
    """Traced version of deploy_agents"""
    print(f"\n=== TRACE: deploy_agents called with force_rebuild={force_rebuild} ===")
    
    # Get the actual method code and trace through it
    if not target_dir:
        target_dir = Path.home() / ".claude" / "agents"
    
    template_dir = self.templates_dir
    templates = list(template_dir.glob("*.json"))
    print(f"TRACE: Found {len(templates)} templates")
    
    # Check research specifically
    for template in templates:
        if template.stem == "research":
            print(f"\nTRACE: Processing research template")
            print(f"  Template path: {template}")
            target_file = target_dir / f"research.md"
            print(f"  Target file: {target_file}")
            print(f"  Target exists: {target_file.exists()}")
            print(f"  force_rebuild: {force_rebuild}")
            
            # The key condition
            needs_update = force_rebuild
            print(f"  Initial needs_update: {needs_update}")
            
            if not needs_update and target_file.exists():
                print(f"  Checking if needs update...")
                # This is where it should detect migration need
                
    # Call original
    return original_deploy(self, target_dir, force_rebuild)

# Apply patch
AgentDeploymentService.deploy_agents = traced_deploy

def main():
    """Run deployment with tracing"""
    service = AgentDeploymentService()
    results = service.deploy_agents(force_rebuild=False)
    
    print(f"\nFinal results:")
    print(f"  Updated: {results['updated']}")
    print(f"  Migrated: {results['migrated']}")
    print(f"  Skipped: {results['skipped']}")

if __name__ == "__main__":
    main()