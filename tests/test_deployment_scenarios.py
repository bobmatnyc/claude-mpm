#!/usr/bin/env python3
"""Test comprehensive deployment scenarios to ensure agents are correctly deployed."""

import sys
import tempfile
import json
import shutil
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService


def test_deployment_scenarios():
    """Test various deployment scenarios for agent management."""
    
    print("Testing comprehensive deployment scenarios...\n")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Set up test project directory
        project_dir = temp_path / "test_project"
        project_dir.mkdir()
        
        # Create templates directory with test agents
        templates_dir = temp_path / "templates"
        templates_dir.mkdir()
        
        # Create base agent
        base_agent = {
            "agent_id": "base_agent",
            "version": "1.0.0",
            "metadata": {
                "name": "Base Agent",
                "description": "Base template for all agents"
            },
            "instructions": "Base agent instructions."
        }
        (templates_dir / "base_agent.json").write_text(json.dumps(base_agent, indent=2))
        
        # Create test agents
        test_agents = [
            {
                "agent_id": "engineer",
                "version": "1.0.0",
                "metadata": {
                    "name": "Engineer Agent",
                    "description": "Engineering agent"
                },
                "capabilities": {
                    "model": "claude-3-5-sonnet-20241022",
                    "tools": ["Read", "Write", "Edit"]
                },
                "instructions": "You are an engineering agent."
            },
            {
                "agent_id": "qa",
                "version": "1.0.0",
                "metadata": {
                    "name": "QA Agent",
                    "description": "Quality assurance agent"
                },
                "capabilities": {
                    "model": "claude-3-5-sonnet-20241022",
                    "tools": ["Read", "Bash", "Grep"]
                },
                "instructions": "You are a QA agent."
            }
        ]
        
        for agent in test_agents:
            agent_path = templates_dir / f"{agent['agent_id']}.json"
            agent_path.write_text(json.dumps(agent, indent=2))
        
        # Initialize deployment service
        deployment_service = AgentDeploymentService(templates_dir=templates_dir)
        
        # Test 1: Initial deployment to project
        print("Test 1: Initial deployment to project")
        print("-" * 40)
        
        agents_dir = project_dir / ".claude" / "agents"
        results = deployment_service.deploy_agents(agents_dir, force_rebuild=True)
        
        print(f"Deployed agents: {results.get('deployed', [])}")
        print(f"Updated agents: {results.get('updated', [])}")
        print(f"Skipped agents: {results.get('skipped', [])}")
        print(f"Errors: {results.get('errors', [])}")
        print(f"Target directory: {agents_dir}")
        print(f"Target exists: {agents_dir.exists()}")
        
        # Check what's actually in the .claude directory
        if (project_dir / ".claude").exists():
            print(f"Contents of .claude: {list((project_dir / '.claude').iterdir())}")
            
        # Check actual deployed location
        actual_agents_dir = project_dir / ".claude" / "agents"
        if actual_agents_dir.exists():
            deployed_files = list(actual_agents_dir.glob("*.md"))
            print(f"Actually deployed {len(deployed_files)} files:")
            for f in deployed_files:
                print(f"  - {f.name}")
        
        # Verify agents have author field  
        for agent_name in ["engineer", "qa", "base_agent"]:
            agent_file = actual_agents_dir / f"{agent_name}.md"
            if agent_file.exists():
                content = agent_file.read_text()
                if "author: claude-mpm" in content:
                    print(f"✅ {agent_name}: Has author field")
                else:
                    print(f"❌ {agent_name}: Missing author field")
            else:
                print(f"  {agent_name}: Not found at {agent_file}")
        
        print()
        
        # Test 2: Re-deployment (should skip unchanged agents)
        print("Test 2: Re-deployment (should skip unchanged)")
        print("-" * 40)
        
        results = deployment_service.deploy_agents(agents_dir, force_rebuild=False)
        
        print(f"Deployed: {len(results['deployed'])}")
        print(f"Updated: {len(results['updated'])}")
        print(f"Skipped: {len(results['skipped'])}")
        
        if len(results['skipped']) > 0:
            print("✅ Correctly skipped unchanged agents")
        else:
            print("❌ Should have skipped unchanged agents")
        
        print()
        
        # Test 3: Update agent and redeploy
        print("Test 3: Update agent template and redeploy")
        print("-" * 40)
        
        # Update engineer agent version
        engineer_data = test_agents[0].copy()
        engineer_data['version'] = "2.0.0"
        engineer_data['instructions'] = "Updated engineer instructions."
        (templates_dir / "engineer.json").write_text(json.dumps(engineer_data, indent=2))
        
        results = deployment_service.deploy_agents(agents_dir, force_rebuild=False)
        
        print(f"Updated: {len(results['updated'])}")
        updated_agents = [agent['name'] if isinstance(agent, dict) else agent for agent in results['updated']]
        if "engineer" in updated_agents:
            print("✅ Engineer agent updated correctly")
        else:
            print("❌ Engineer agent should have been updated")
        
        # Verify updated agent still has author field
        engineer_file = agents_dir / "engineer.md"
        if engineer_file.exists():
            content = engineer_file.read_text()
            if "author: claude-mpm" in content:
                print("✅ Updated agent maintains author field")
            else:
                print("❌ Updated agent lost author field")
        
        print()
        
        # Test 4: List deployed agents
        print("Test 4: List deployed agents")
        print("-" * 40)
        
        deployed_agents = list(agents_dir.glob("*.md"))
        print(f"Found {len(deployed_agents)} deployed agents:")
        for agent_file in deployed_agents:
            print(f"  - {agent_file.name}")
        
        print()
        
        # Test 5: Verify all agents have author field
        print("Test 5: Verify all agents have author field")
        print("-" * 40)
        
        all_have_author = True
        for agent_file in deployed_agents:
            content = agent_file.read_text()
            if "author: claude-mpm" not in content:
                print(f"❌ {agent_file.name}: Missing author field")
                all_have_author = False
        
        if all_have_author and len(deployed_agents) > 0:
            print("✅ All deployed agents have author field")
        elif len(deployed_agents) == 0:
            print("❌ No agents found to verify")
        
        print("\n" + "=" * 50)
        print("All deployment scenario tests completed!")


if __name__ == "__main__":
    test_deployment_scenarios()