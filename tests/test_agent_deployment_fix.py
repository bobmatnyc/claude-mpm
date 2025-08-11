#!/usr/bin/env python3
"""Test script to verify agent deployment fix."""

import sys
import tempfile
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService


def test_agent_deployment_fix():
    """Test that agents are properly marked with author: claude-mpm."""
    
    print("Testing agent deployment fix...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a test template directory
        templates_dir = temp_path / "templates"
        templates_dir.mkdir()
        
        # Create a base agent template
        base_agent = {
            "agent_id": "base_agent",
            "version": "1.0.0",
            "metadata": {
                "name": "Base Agent",
                "description": "Base template for all agents"
            },
            "instructions": "You are a base agent."
        }
        
        base_agent_path = templates_dir / "base_agent.json"
        base_agent_path.write_text(json.dumps(base_agent, indent=2))
        
        # Create a test agent template
        test_agent = {
            "agent_id": "test_agent",
            "version": "1.0.0",
            "metadata": {
                "name": "Test Agent",
                "description": "Test agent for verification"
            },
            "capabilities": {
                "model": "claude-3-5-sonnet-20241022",
                "tools": ["Read", "Write", "Edit"]
            },
            "instructions": "You are a test agent for verifying deployment."
        }
        
        test_agent_path = templates_dir / "test_agent.json"
        test_agent_path.write_text(json.dumps(test_agent, indent=2))
        
        # Create deployment service with test directory
        deployment_service = AgentDeploymentService(templates_dir=templates_dir)
        
        # Create target directory for deployment
        target_dir = temp_path / "deployed_agents"
        target_dir.mkdir()
        
        # Deploy agents
        results = deployment_service.deploy_agents(target_dir, force_rebuild=True)
        
        print(f"Deployment results:")
        print(f"  - Deployed: {len(results['deployed'])}")
        print(f"  - Updated: {len(results['updated'])}")
        print(f"  - Skipped: {len(results['skipped'])}")
        print(f"  - Errors: {len(results['errors'])}")
        
        # Check if test agent was deployed (may be in .claude/agents subdirectory)
        test_agent_file = target_dir / ".claude" / "agents" / "test_agent.md"
        if not test_agent_file.exists():
            # Try the direct path as fallback
            test_agent_file = target_dir / "test_agent.md"
        
        if test_agent_file.exists():
            content = test_agent_file.read_text()
            
            # Check for author field
            if "author: claude-mpm" in content:
                print("✅ SUCCESS: Agent has 'author: claude-mpm' field")
                print("\nAgent frontmatter:")
                # Print the frontmatter section
                lines = content.split('\n')
                in_frontmatter = False
                for line in lines:
                    if line == '---':
                        if in_frontmatter:
                            print(line)
                            break
                        else:
                            in_frontmatter = True
                            print(line)
                    elif in_frontmatter:
                        print(line)
                
                # Now test the check_agent_needs_update method
                print("\n\nTesting system agent detection...")
                needs_update, reason = deployment_service._check_agent_needs_update(
                    test_agent_file, test_agent_path, (1, 0, 0)
                )
                
                if not needs_update and reason == "not a system agent":
                    print("❌ ERROR: Agent not recognized as system agent")
                else:
                    print(f"✅ Agent recognized properly - needs_update: {needs_update}, reason: {reason}")
                    
            else:
                print("❌ ERROR: Agent missing 'author: claude-mpm' field")
                print("\nAgent content preview:")
                print(content[:500])
        else:
            print(f"❌ ERROR: Test agent not deployed to {test_agent_file}")
            print(f"Available files: {list(target_dir.glob('*'))}")
        
        if results['errors']:
            print("\nErrors encountered:")
            for error in results['errors']:
                print(f"  - {error}")


if __name__ == "__main__":
    test_agent_deployment_fix()