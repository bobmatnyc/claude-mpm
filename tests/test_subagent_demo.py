#!/usr/bin/env python3
"""Simple test script demonstrating claude-mpm subagent functionality."""

import sys
import os
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService
from claude_mpm.core.claude_runner import SimpleClaudeRunner


def test_agent_deployment():
    """Test agent deployment functionality."""
    print("🚀 Testing Claude-MPM Subagent Deployment")
    print("=" * 60)
    
    # Initialize the deployment service
    deployment_service = AgentDeploymentService()
    
    # Check templates directory
    templates_dir = deployment_service.templates_dir
    print(f"\n📁 Templates directory: {templates_dir}")
    
    if templates_dir.exists():
        template_files = list(templates_dir.glob("*_agent.json"))
        print(f"✓ Found {len(template_files)} agent templates:")
        for template in template_files:
            print(f"  - {template.stem}")
    else:
        print("❌ Templates directory not found!")
        return False
    
    # Deploy agents to .claude/agents/
    print("\n📦 Deploying agents...")
    results = deployment_service.deploy_agents()
    
    # Display results
    print(f"\n📊 Deployment Results:")
    print(f"  Target directory: {results['target_dir']}")
    print(f"  Total templates: {results['total']}")
    print(f"  Deployed: {len(results['deployed'])}")
    print(f"  Updated: {len(results.get('updated', []))}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Errors: {len(results['errors'])}")
    
    if results['deployed']:
        print("\n✅ Successfully deployed agents:")
        for agent in results['deployed']:
            print(f"  - {agent}")
    
    if results.get('updated'):
        print("\n🔄 Updated agents:")
        for agent in results['updated']:
            print(f"  - {agent}")
    
    if results['errors']:
        print("\n❌ Errors encountered:")
        for error in results['errors']:
            print(f"  - {error}")
    
    return len(results['errors']) == 0


def test_simple_runner():
    """Test SimpleClaudeRunner initialization."""
    print("\n\n🧪 Testing SimpleClaudeRunner")
    print("=" * 60)
    
    try:
        # Initialize runner
        runner = SimpleClaudeRunner(
            enable_tickets=True,
            log_level="INFO"
        )
        
        print("✓ SimpleClaudeRunner initialized successfully")
        
        # Setup agents
        print("\n📦 Setting up agents via runner...")
        success = runner.setup_agents()
        
        if success:
            print("✅ Agents setup completed successfully!")
            
            # Check deployed agents
            agent_dir = Path.home() / ".claude" / "agents"
            if agent_dir.exists():
                agents = list(agent_dir.glob("*.md"))
                print(f"\n📋 Available subagents in {agent_dir}:")
                for agent in agents:
                    print(f"  - {agent.stem}")
        else:
            print("❌ Agent setup failed!")
            
        return success
        
    except Exception as e:
        print(f"❌ Error initializing runner: {e}")
        return False


def main():
    """Run all tests."""
    print("🎯 Claude-MPM Subagent Demo")
    print("This script demonstrates the subagent deployment functionality.\n")
    
    # Test 1: Direct agent deployment
    deployment_success = test_agent_deployment()
    
    # Test 2: SimpleClaudeRunner with agent setup
    runner_success = test_simple_runner()
    
    # Summary
    print("\n\n📊 Test Summary")
    print("=" * 60)
    print(f"Agent Deployment: {'✅ PASSED' if deployment_success else '❌ FAILED'}")
    print(f"Simple Runner: {'✅ PASSED' if runner_success else '❌ FAILED'}")
    
    if deployment_success and runner_success:
        print("\n✅ All tests passed!")
        print("\n💡 Next steps:")
        print("1. Run 'claude' to start Claude with the deployed agents")
        print("2. Ask Claude: 'Can you list available subagents?'")
        print("3. Try delegating to a specific agent:")
        print("   - 'Delegate to engineer: Help me implement a feature'")
        print("   - 'Delegate to research: Analyze this codebase'")
        print("   - 'Delegate to qa: Write tests for this function'")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()