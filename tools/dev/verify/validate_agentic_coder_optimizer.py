#!/usr/bin/env python3
"""
Validation script for Agentic Coder Optimizer Agent
===================================================

This script validates that the agent is properly deployed and functional.
"""

import json
import sys
from pathlib import Path


def validate_agent():
    """Validate the Agentic Coder Optimizer agent deployment."""
    errors = []
    warnings = []

    # 1. Check template file exists
    template_path = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "templates"
        / "agentic_coder_optimizer.json"
    )
    if not template_path.exists():
        errors.append(f"Template file not found: {template_path}")
        return errors, warnings

    print(f"✓ Template file exists: {template_path}")

    # 2. Validate JSON structure
    try:
        with open(template_path) as f:
            template = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in template: {e}")
        return errors, warnings

    print("✓ Template JSON is valid")

    # 3. Check required fields
    required_fields = {
        "agent_id": "agentic-coder-optimizer",
        "agent_version": "0.0.5",
        "agent_type": "ops",
    }

    for field, expected in required_fields.items():
        if field not in template:
            errors.append(f"Missing required field: {field}")
        elif template[field] != expected:
            warnings.append(
                f"Field {field} has value '{template[field]}', expected '{expected}'"
            )
        else:
            print(f"✓ {field}: {template[field]}")

    # 4. Check metadata
    metadata = template.get("metadata", {})
    if metadata.get("name") != "Agentic Coder Optimizer":
        warnings.append(
            f"Metadata name is '{metadata.get('name')}', expected 'Agentic Coder Optimizer'"
        )
    else:
        print(f"✓ Agent name: {metadata.get('name')}")

    # 5. Check deployment
    deploy_path = Path.cwd() / ".claude" / "agents" / "agentic_coder_optimizer.md"
    if deploy_path.exists():
        print(f"✓ Agent deployed: {deploy_path}")

        # Check deployment content
        with open(deploy_path) as f:
            content = f.read()
            if "Agentic Coder Optimizer" in content:
                print("✓ Deployment contains agent instructions")
            else:
                warnings.append(
                    "Deployment file exists but may not contain correct content"
                )
    else:
        warnings.append(f"Agent not deployed to project: {deploy_path}")

    # 6. Check agent is in metadata
    metadata_path = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "agents_metadata.py"
    )
    if metadata_path.exists():
        with open(metadata_path) as f:
            content = f.read()
            if "AGENTIC_CODER_OPTIMIZER_CONFIG" in content:
                print("✓ Agent registered in metadata")
            else:
                warnings.append("Agent not found in agents_metadata.py")

    # 7. Validate capabilities
    capabilities = template.get("capabilities", {})
    required_tools = ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
    agent_tools = capabilities.get("tools", [])
    missing_tools = [tool for tool in required_tools if tool not in agent_tools]

    if missing_tools:
        warnings.append(f"Missing required tools: {', '.join(missing_tools)}")
    else:
        print(f"✓ All required tools present ({len(agent_tools)} tools)")

    # 8. Check instructions
    instructions = template.get("instructions", "")
    if len(instructions) < 1000:
        warnings.append(f"Instructions seem too short ({len(instructions)} chars)")
    else:
        print(f"✓ Instructions present ({len(instructions)} chars)")

    return errors, warnings


def main():
    """Run validation and report results."""
    print("=" * 60)
    print("Agentic Coder Optimizer Agent Validation")
    print("=" * 60)
    print()

    errors, warnings = validate_agent()

    print()
    print("=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    if errors:
        print("\n❌ ERRORS:")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")

    if not errors and not warnings:
        print("\n✅ ALL CHECKS PASSED!")
        print("\nThe Agentic Coder Optimizer agent is:")
        print("  • Properly formatted")
        print("  • Correctly configured")
        print("  • Successfully deployed")
        print("  • Ready for use")
        return 0
    if not errors:
        print("\n✅ VALIDATION PASSED WITH WARNINGS")
        print("The agent is functional but has minor issues.")
        return 0
    print("\n❌ VALIDATION FAILED")
    print("The agent has critical errors that must be fixed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
