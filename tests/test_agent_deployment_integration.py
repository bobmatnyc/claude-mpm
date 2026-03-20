#!/usr/bin/env python3
"""Test agent deployment integration with the fixed agent loader.

This script tests the integration between AgentDeploymentService and the
agent loader functionality, ensuring that deployed agents can be properly
loaded and used by the system.

TEST SCENARIOS COVERED:
1. AgentDeploymentService initialization
2. Individual agent deployment with success/failure tracking
3. Deployed agent content validation
4. Comparison between direct loading and deployment service
5. Model selection through deployment with complexity factors
6. Integration with agent loader (get_agent_prompt)

TEST FOCUS:
- Validates that the deployment service produces agents compatible with the loader
- Ensures deployment results include necessary metadata
- Verifies that deployed agents have proper content
- Tests advanced features like model selection based on complexity

TEST COVERAGE GAPS:
- No testing of concurrent deployments
- No testing of partial deployment failures
- No testing of deployment rollback scenarios
- No testing of custom template directories
- No testing of base agent merging logic
- No testing of deployment to production directories
"""

import os
import sys

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_mpm.agents.agent_loader import get_agent_prompt
from claude_mpm.services.agents.deployment import AgentDeploymentService


def test_agent_deployment():
    """Test that agent deployment works with the fixed loader.

    This comprehensive test validates:
    1. Service initialization without errors
    2. Deployment of multiple agent types (qa, research, engineer)
    3. Verification that deployed agents have proper content
    4. Consistency between direct loading and deployment methods
    5. Model selection based on task complexity

    The test uses the deploy_agent method which is designed for
    runtime agent deployment (not file-based deployment).
    """
    print("=== Testing Agent Deployment Integration ===\n")

    # Test 1: Initialize deployment service
    print("1. Initializing AgentDeploymentService:")
    try:
        deployment_service = AgentDeploymentService()
        print("   ✓ Service initialized successfully")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        return
    print()

    # Test 2: Deploy agents
    print("2. Testing agent deployment:")
    test_agents = ["qa", "research", "engineer"]

    for agent_type in test_agents:
        try:
            # Deploy agent
            result = deployment_service.deploy_agent(
                agent_type=agent_type,
                task_description=f"Test deployment of {agent_type} agent",
            )

            if result and result.get("success"):
                print(f"   - {agent_type}: ✓ (deployed successfully)")

                # Verify the deployed agent has proper content
                if "agent_prompt" in result:
                    prompt_length = len(result["agent_prompt"])
                    has_content = prompt_length > 100
                    print(f"     • Prompt length: {prompt_length}")
                    print(f"     • Has content: {'✓' if has_content else '✗'}")
            else:
                print(f"   - {agent_type}: ✗ (deployment failed)")
                if result:
                    print(f"     • Error: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"   - {agent_type}: ✗ (exception: {e})")
    print()

    # Test 3: Compare direct loading vs deployment
    print("3. Comparing direct loading vs deployment:")
    for agent_type in ["qa"]:
        try:
            # Direct loading
            direct_prompt = get_agent_prompt(agent_type)

            # Via deployment service
            deployment_result = deployment_service.deploy_agent(
                agent_type=agent_type, task_description="Comparison test"
            )

            if deployment_result and deployment_result.get("success"):
                deployed_prompt = deployment_result.get("agent_prompt", "")

                # Both should contain the agent content
                print(f"   - Direct load length: {len(direct_prompt)}")
                print(f"   - Deployed length: {len(deployed_prompt)}")

                # Check if both contain expected content
                direct_has_qa = (
                    "QA Agent" in direct_prompt or "qa agent" in direct_prompt.lower()
                )
                deployed_has_qa = (
                    "QA Agent" in deployed_prompt
                    or "qa agent" in deployed_prompt.lower()
                )

                print(f"   - Direct has QA content: {'✓' if direct_has_qa else '✗'}")
                print(
                    f"   - Deployed has QA content: {'✓' if deployed_has_qa else '✗'}"
                )
                print(
                    f"   - Consistency: {'✓' if direct_has_qa == deployed_has_qa else '✗'}"
                )
            else:
                print("   ✗ Deployment failed")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    print()

    # Test 4: Test model selection through deployment
    print("4. Testing model selection through deployment:")
    try:
        result = deployment_service.deploy_agent(
            agent_type="engineer",
            task_description="Complex engineering task requiring advanced analysis",
            complexity_factors={
                "file_count": 50,
                "integration_points": 10,
                "requires_architecture": True,
            },
        )

        if result and result.get("success"):
            print("   ✓ Deployment successful")
            print(f"   - Selected model: {result.get('model', 'Not specified')}")
            print(f"   - Model config: {result.get('model_config', {})}")
        else:
            print("   ✗ Deployment failed")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n=== Agent Deployment Integration Test Complete ===")


if __name__ == "__main__":
    test_agent_deployment()
