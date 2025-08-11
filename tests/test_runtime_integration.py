#!/usr/bin/env python3
"""Integration test for runtime capabilities in SimpleClaudeRunner."""

import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_non_interactive_mode():
    """Test that capabilities are loaded in non-interactive mode."""
    print("Testing non-interactive mode with /mpm:test command...")
    
    # Run a simple command that doesn't actually invoke Claude
    result = subprocess.run(
        [sys.executable, "-m", "claude_mpm.cli", "run", "-i", "/mpm:test", "--non-interactive"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    if result.returncode == 0 and "Hello World" in result.stdout:
        print("✓ Non-interactive mode works")
        return True
    else:
        print(f"❌ Non-interactive mode failed: {result.stderr}")
        return False


def test_system_prompt_creation():
    """Test that system prompt is correctly created with capabilities."""
    from claude_mpm.core.claude_runner import SimpleClaudeRunner
    
    print("\nTesting system prompt creation...")
    
    # Test with default runner
    runner = SimpleClaudeRunner()
    prompt = runner._create_system_prompt()
    
    if prompt and "{{capabilities-list}}" not in prompt:
        print("✓ System prompt created without placeholders")
        
        # Check for key components
        components = {
            "PM Identity": "Claude Multi-Agent Project Manager" in prompt,
            "Agent List": "data_engineer, documentation, engineer" in prompt,
            "Capabilities": "## Agent Names & Capabilities" in prompt,
            "Formats": "Agent Name Formats" in prompt
        }
        
        print("\nKey components:")
        for name, present in components.items():
            print(f"  {'✓' if present else '❌'} {name}")
        
        return all(components.values())
    else:
        print("❌ System prompt creation failed")
        return False


def test_agent_deployment_integration():
    """Test that agent deployment works with capabilities loading."""
    from claude_mpm.services.agent_deployment import AgentDeploymentService
    
    print("\nTesting agent deployment integration...")
    
    service = AgentDeploymentService()
    
    # Just check that the service initializes correctly
    # (actual deployment was already tested in other scripts)
    if hasattr(service, 'deploy_agents'):
        print("✓ Agent deployment service initialized")
        return True
    else:
        print("❌ Agent deployment service failed to initialize")
        return False


def main():
    """Run all integration tests."""
    print("Running Runtime Capabilities Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Non-interactive Mode", test_non_interactive_mode),
        ("System Prompt Creation", test_system_prompt_creation),
        ("Agent Deployment Integration", test_agent_deployment_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("-" * 40)
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)