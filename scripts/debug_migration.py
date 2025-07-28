#!/usr/bin/env python3
"""Debug script to test agent migration detection"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.services.agent_deployment import AgentDeploymentService
from pathlib import Path

def main():
    """Test migration detection"""
    service = AgentDeploymentService()
    
    # Check research agent
    agent_name = "research"
    agent_file = Path.home() / ".claude" / "agents" / f"{agent_name}.md"
    
    if agent_file.exists():
        print(f"\nChecking {agent_name} agent:")
        content = agent_file.read_text()
        
        # Extract version
        import re
        version_match = re.search(r"^version:\s*[\"']?([^\"'\n]+)[\"']?", content, re.MULTILINE)
        if version_match:
            version = version_match.group(1)
            print(f"Current version: {version}")
            
            # Check if old format
            is_old = service._is_old_version_format(version)
            print(f"Is old format: {is_old}")
            
            # Check if needs update
            needs_update, reason = service._check_agent_needs_update(agent_name)
            print(f"Needs update: {needs_update}")
            print(f"Reason: {reason}")
    
    # Now test actual deployment
    print("\n" + "="*50)
    print("Running actual deployment...")
    results = service.deploy_agents()
    print(f"\nDeployment results:")
    print(f"Deployed: {results['deployed']}")
    print(f"Updated: {results['updated']}")
    print(f"Migrated: {results['migrated']}")
    print(f"Skipped: {results['skipped']}")
    print(f"Errors: {results['errors']}")

if __name__ == "__main__":
    main()