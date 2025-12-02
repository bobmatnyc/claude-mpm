#!/usr/bin/env python3
"""Test script to verify agent deployment service can find templates after reorganization."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_deployment import (
    AgentDeploymentService,
)


def test_agent_deployment_paths():
    """Test that agent deployment service finds correct paths."""
    print("Testing Agent Deployment Service path resolution...")
    print("=" * 60)

    # Initialize service
    service = AgentDeploymentService()

    # Check templates directory
    print(f"\nTemplates directory: {service.templates_dir}")
    print(f"Templates dir exists: {service.templates_dir.exists()}")

    if service.templates_dir.exists():
        templates = list(service.templates_dir.glob("*.json"))
        print(f"Found {len(templates)} template files:")
        for template in templates[:5]:  # Show first 5
            print(f"  - {template.name}")
    else:
        print("ERROR: Templates directory not found!")
        return False

    # Check base agent path
    print(f"\nBase agent path: {service.base_agent_path}")
    print(f"Base agent exists: {service.base_agent_path.exists()}")

    if not service.base_agent_path.exists():
        print("ERROR: Base agent file not found!")
        return False

    # Verify the paths are correct
    expected_templates = (
        Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "templates"
    )
    expected_base = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "base_agent.json"
    )

    print(f"\nExpected templates: {expected_templates}")
    print(f"Actual templates:   {service.templates_dir}")
    print(f"Match: {expected_templates.resolve() == service.templates_dir.resolve()}")

    print(f"\nExpected base agent: {expected_base}")
    print(f"Actual base agent:   {service.base_agent_path}")
    print(f"Match: {expected_base.resolve() == service.base_agent_path.resolve()}")

    if (
        expected_templates.resolve() == service.templates_dir.resolve()
        and expected_base.resolve() == service.base_agent_path.resolve()
    ):
        print("\n✅ SUCCESS: All paths resolved correctly!")
        return True
    print("\n❌ FAILURE: Path resolution mismatch!")
    return False


if __name__ == "__main__":
    success = test_agent_deployment_paths()
    sys.exit(0 if success else 1)
