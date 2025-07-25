#!/usr/bin/env python3
"""Test agent versioning system."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agent_deployment import AgentDeploymentService

def test_versioning():
    """Test the agent versioning system."""
    print("Testing agent versioning system...")
    
    # Create deployment service
    deployment_service = AgentDeploymentService()
    
    # Check that base agent has version
    if deployment_service.base_agent_path.exists():
        base_content = deployment_service.base_agent_path.read_text()
        base_version = deployment_service._extract_version(base_content, "BASE_AGENT_VERSION:")
        print(f"✓ Base agent version: {base_version}")
    
    # Check template versions
    print("\nChecking agent template versions:")
    templates = list(deployment_service.templates_dir.glob("*_agent.md"))
    for template in templates:
        content = template.read_text()
        version = deployment_service._extract_version(content, "AGENT_VERSION:")
        print(f"  - {template.stem}: version {version}")
    
    # Test deployment with version checking
    print("\nTesting deployment with version checking...")
    results = deployment_service.deploy_agents(Path.cwd() / ".claude" / "agents")
    
    print("\nDeployment results:")
    print(f"  - Deployed: {len(results['deployed'])}")
    print(f"  - Updated: {len(results.get('updated', []))}")
    print(f"  - Skipped: {len(results.get('skipped', []))}")
    print(f"  - Errors: {len(results['errors'])}")
    
    if results.get('updated'):
        print("\nUpdated agents:")
        for agent in results['updated']:
            print(f"  - {agent['name']}")
    
    print("\n✅ Version testing complete!")

if __name__ == "__main__":
    test_versioning()