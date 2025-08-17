#!/usr/bin/env python3
"""
Test script to verify agent deployment uses correct user directory.

This script tests that:
1. AgentDeploymentService respects CLAUDE_MPM_USER_PWD environment variable
2. Agents are deployed to the user's directory, not the framework directory
3. Project agents are loaded from the user's .claude-mpm/agents directory
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_agent_deployment():
    """Test that agent deployment respects user directory."""
    from claude_mpm.services.agents.deployment import AgentDeploymentService
    
    # Create a temporary user directory
    with tempfile.TemporaryDirectory() as tmpdir:
        user_dir = Path(tmpdir) / "user_project"
        user_dir.mkdir(exist_ok=True)
        
        # Set the environment variable
        os.environ['CLAUDE_MPM_USER_PWD'] = str(user_dir)
        
        print(f"Testing with user directory: {user_dir}")
        
        # Create deployment service
        service = AgentDeploymentService()
        
        # Verify working directory is set correctly
        assert service.working_directory == user_dir, \
            f"Working directory mismatch: {service.working_directory} != {user_dir}"
        print("✓ AgentDeploymentService correctly uses CLAUDE_MPM_USER_PWD")
        
        # Test deploy_agents method
        results = service.deploy_agents()
        target_dir = Path(results['target_dir'])
        
        # Verify target directory is in user directory
        expected_dir = user_dir / ".claude" / "agents"
        assert target_dir == expected_dir, \
            f"Deploy target mismatch: {target_dir} != {expected_dir}"
        print(f"✓ Agents deployed to correct directory: {target_dir}")
        
        # Test verify_deployment method
        verification = service.verify_deployment()
        config_dir = Path(verification['config_dir'])
        expected_config = user_dir / ".claude"
        assert config_dir == expected_config, \
            f"Config dir mismatch: {config_dir} != {expected_config}"
        print(f"✓ Verification uses correct config directory: {config_dir}")
        
        # Test set_claude_environment method
        env_vars = service.set_claude_environment()
        claude_config = Path(env_vars.get('CLAUDE_CONFIG_DIR', ''))
        assert claude_config == expected_config.absolute(), \
            f"Environment config mismatch: {claude_config} != {expected_config.absolute()}"
        print(f"✓ Environment variables set correctly: CLAUDE_CONFIG_DIR={claude_config}")
        
        # Clean up environment
        del os.environ['CLAUDE_MPM_USER_PWD']
        
        print("\n✅ All tests passed! Agent deployment correctly respects user directory.")
        return True

def test_claude_runner():
    """Test that ClaudeRunner respects user directory."""
    from claude_mpm.core.claude_runner import ClaudeRunner
    
    # Create a temporary user directory
    with tempfile.TemporaryDirectory() as tmpdir:
        user_dir = Path(tmpdir) / "user_project"
        user_dir.mkdir(exist_ok=True)
        
        # Set the environment variable
        os.environ['CLAUDE_MPM_USER_PWD'] = str(user_dir)
        
        print(f"\nTesting ClaudeRunner with user directory: {user_dir}")
        
        # Create runner
        runner = ClaudeRunner(enable_tickets=False, log_level="OFF")
        
        # Verify deployment service has correct working directory
        assert runner.deployment_service.working_directory == user_dir, \
            f"Runner deployment service mismatch: {runner.deployment_service.working_directory} != {user_dir}"
        print("✓ ClaudeRunner's deployment service uses correct directory")
        
        # Test ensure_project_agents method
        success = runner.ensure_project_agents()
        print(f"✓ ensure_project_agents completed: {success}")
        
        # Create a test project agent directory
        project_agents_dir = user_dir / ".claude-mpm" / "agents"
        project_agents_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test agent JSON file
        test_agent = {
            "agent_id": "test_agent",
            "version": "1.0.0",
            "metadata": {
                "name": "Test Agent",
                "description": "Test agent for verification"
            },
            "instructions": "You are a test agent."
        }
        
        import json
        test_agent_file = project_agents_dir / "test_agent.json"
        test_agent_file.write_text(json.dumps(test_agent, indent=2))
        
        # Test deploy_project_agents_to_claude
        success = runner.deploy_project_agents_to_claude()
        assert success, "Failed to deploy project agents"
        print("✓ deploy_project_agents_to_claude completed successfully")
        
        # Verify the agent was deployed to the correct location
        deployed_agent = user_dir / ".claude" / "agents" / "test_agent.md"
        if deployed_agent.exists():
            print(f"✓ Project agent deployed to correct location: {deployed_agent}")
        else:
            print(f"⚠️  Agent not found at expected location: {deployed_agent}")
        
        # Clean up environment
        del os.environ['CLAUDE_MPM_USER_PWD']
        
        print("\n✅ ClaudeRunner tests passed!")
        return True

if __name__ == "__main__":
    try:
        # Run tests
        test_agent_deployment()
        test_claude_runner()
        
        print("\n🎉 All tests passed! The fix is working correctly.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)