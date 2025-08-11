#!/usr/bin/env python3
"""Test agent deployment in actual project directory."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_deployment import AgentDeploymentService


def test_deployment_in_project():
    """Test deployment to actual .claude-mpm/agents directory."""
    print("Testing Agent Deployment in Project Directory...")
    print("=" * 60)
    
    # Initialize service
    service = AgentDeploymentService()
    
    # Set target to project's .claude-mpm directory
    project_root = Path(__file__).parent.parent
    target_dir = project_root / ".claude-mpm"
    
    print(f"\nProject root: {project_root}")
    print(f"Target directory: {target_dir}")
    
    # Expected agents directory
    expected_agents_dir = target_dir / "agents"
    print(f"Expected agents directory: {expected_agents_dir}")
    
    # Check current state
    if expected_agents_dir.exists():
        existing_agents = list(expected_agents_dir.glob("*.md"))
        print(f"\nExisting agents: {len(existing_agents)}")
    else:
        print(f"\nAgents directory doesn't exist yet")
    
    try:
        # Deploy agents (update mode - won't overwrite unless versions changed)
        print(f"\nDeploying agents (update mode)...")
        result = service.deploy_agents(
            target_dir=target_dir,
            force_rebuild=False,
            deployment_mode="update"
        )
        
        print(f"\nDeployment result:")
        print(f"  Target: {result.get('target_dir', 'unknown')}")
        print(f"  Deployed (new): {len(result.get('deployed', []))}")
        print(f"  Updated: {len(result.get('updated', []))}")
        print(f"  Skipped: {len(result.get('skipped', []))}")
        print(f"  Errors: {len(result.get('errors', []))}")
        
        if result.get('errors'):
            print(f"\nErrors encountered:")
            for error in result['errors']:
                print(f"  - {error}")
        
        # Verify files exist
        if expected_agents_dir.exists():
            final_agents = list(expected_agents_dir.glob("*.md"))
            print(f"\nFinal agent count: {len(final_agents)}")
            
            # Check for PM instructions
            pm_instructions = expected_agents_dir / "pm_instructions.md"
            if pm_instructions.exists():
                print(f"✅ PM instructions present: {pm_instructions.stat().st_size} bytes")
            else:
                print("⚠️  PM instructions not found")
            
            # Sample a few agents
            print(f"\nSample agents:")
            for agent_file in final_agents[:3]:
                print(f"  - {agent_file.name} ({agent_file.stat().st_size} bytes)")
            
            print("\n✅ SUCCESS: Deployment verified in project directory!")
            return True
        else:
            print("\n❌ FAILURE: Agents directory not created")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR during deployment: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_deployment_in_project()
    sys.exit(0 if success else 1)