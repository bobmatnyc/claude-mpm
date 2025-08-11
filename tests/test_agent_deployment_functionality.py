#!/usr/bin/env python3
"""Test agent deployment functionality after path fix."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_deployment import AgentDeploymentService


def test_deployment_functionality():
    """Test that agent deployment actually works with correct paths."""
    print("Testing Agent Deployment Functionality...")
    print("=" * 60)
    
    # Initialize service
    service = AgentDeploymentService()
    
    # Create a temporary directory for deployment
    with tempfile.TemporaryDirectory() as tmpdir:
        target_dir = Path(tmpdir) / "deployed_agents"
        target_dir.mkdir(exist_ok=True)
        
        print(f"\nDeploying agents to: {target_dir}")
        
        try:
            # Deploy agents
            result = service.deploy_agents(
                target_dir=target_dir,
                force_rebuild=True,
                deployment_mode="update"
            )
            
            print(f"\nDeployment result:")
            print(f"  Deployed: {len(result.get('deployed', []))} agents")
            print(f"  Updated: {len(result.get('updated', []))} agents")
            print(f"  Skipped: {len(result.get('skipped', []))} agents")
            print(f"  Errors: {len(result.get('errors', []))} errors")
            
            all_deployed = result.get('deployed', []) + result.get('updated', [])
            if all_deployed:
                print(f"  Agents deployed/updated:")
                for agent in all_deployed[:5]:  # Show first 5
                    print(f"    - {agent}")
            
            # Check if files were actually created
            # The service deploys to .claude/agents/ subdirectory
            actual_agents_dir = target_dir / ".claude" / "agents"
            deployed_files = list(actual_agents_dir.glob("*.md")) if actual_agents_dir.exists() else []
            print(f"\nActual files created in {actual_agents_dir}: {len(deployed_files)}")
            for file in deployed_files[:5]:  # Show first 5
                print(f"  - {file.name} ({file.stat().st_size} bytes)")
            
            # Check if PM instructions were deployed
            pm_instructions = actual_agents_dir / "pm_instructions.md" if actual_agents_dir.exists() else None
            if pm_instructions and pm_instructions.exists():
                print(f"\n✅ PM instructions deployed: {pm_instructions.stat().st_size} bytes")
            else:
                print("\n⚠️  PM instructions not found")
            
            # Consider it a success if we deployed or updated agents
            total_deployed = len(result.get('deployed', [])) + len(result.get('updated', []))
            if total_deployed > 0 and len(deployed_files) > 0:
                print("\n✅ SUCCESS: Agent deployment functionality working!")
                return True
            else:
                print(f"\n❌ FAILURE: Deployment issues detected")
                if result.get('errors'):
                    print(f"  Errors:")
                    for error in result['errors']:
                        print(f"    - {error}")
                return False
                
        except Exception as e:
            print(f"\n❌ ERROR during deployment: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = test_deployment_functionality()
    sys.exit(0 if success else 1)