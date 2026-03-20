#!/usr/bin/env python3
"""
Test script to verify Code Analyzer agent template with Mermaid capabilities.

This script validates that the updated Code Analyzer agent template:
1. Has valid JSON structure
2. Includes mermaid visualization capabilities
3. Has proper tool configurations
4. Contains updated instructions for diagram generation
"""

import json
import sys
from pathlib import Path


def validate_code_analyzer_template():
    """Validate the updated Code Analyzer agent template."""

    # Path to the agent template
    template_path = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "templates"
        / "code_analyzer.json"
    )

    if not template_path.exists():
        print(f"✗ Template file not found: {template_path}")
        return False

    print(f"✓ Found template file: {template_path}")

    # Load and parse the JSON
    try:
        with template_path.open() as f:
            template = json.load(f)
        print("✓ Valid JSON structure")
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        return False

    # Check for required fields
    required_fields = [
        "schema_version",
        "agent_id",
        "agent_version",
        "capabilities",
        "knowledge",
        "instructions",
    ]
    for field in required_fields:
        if field not in template:
            print(f"✗ Missing required field: {field}")
            return False
    print("✓ All required fields present")

    # Verify mermaid-related updates
    checks_passed = True

    # Check if Write tool is added (needed to save diagrams)
    if "Write" not in template["capabilities"]["tools"]:
        print("✗ Write tool not found in capabilities")
        checks_passed = False
    else:
        print("✓ Write tool present in capabilities")

    # Check for mermaid in domain expertise
    domain_expertise = template["knowledge"]["domain_expertise"]
    mermaid_expertise = any(
        "mermaid" in exp.lower() or "visualization" in exp.lower()
        for exp in domain_expertise
    )
    if not mermaid_expertise:
        print("✗ Mermaid/visualization not found in domain expertise")
        checks_passed = False
    else:
        print("✓ Mermaid visualization in domain expertise")

    # Check for mermaid in tags
    tags = template["metadata"]["tags"]
    mermaid_tags = any(
        tag in ["mermaid", "visualization", "architecture-diagrams"] for tag in tags
    )
    if not mermaid_tags:
        print("✗ Mermaid-related tags not found")
        checks_passed = False
    else:
        print("✓ Mermaid-related tags present")

    # Check instructions for mermaid content
    instructions = template["instructions"]
    mermaid_sections = [
        "Visualization Capabilities",
        "MermaidGeneratorService",
        "DiagramType",
        "entry_points",
        "module_deps",
        "class_hierarchy",
        "call_graph",
    ]

    missing_sections = []
    for section in mermaid_sections:
        if section not in instructions:
            missing_sections.append(section)

    if missing_sections:
        print(f"✗ Missing instruction sections: {', '.join(missing_sections)}")
        checks_passed = False
    else:
        print("✓ All mermaid instruction sections present")

    # Check for example code in instructions
    if "from claude_mpm.services.visualization import" not in instructions:
        print("✗ MermaidGeneratorService import example not found")
        checks_passed = False
    else:
        print("✓ MermaidGeneratorService usage example present")

    # Check version update
    if template["agent_version"] >= "2.6.0":
        print(f"✓ Agent version updated: {template['agent_version']}")
    else:
        print(f"⚠ Agent version might need update: {template['agent_version']}")

    # Final result
    print("\n" + "=" * 60)
    if checks_passed:
        print(
            "✅ Code Analyzer agent template successfully updated with Mermaid capabilities!"
        )
        print("\nThe agent can now:")
        print("  - Generate entry point flow diagrams")
        print("  - Create module dependency visualizations")
        print("  - Build class hierarchy diagrams")
        print("  - Produce function call graphs")
        print("\nTrigger words for visualization:")
        print('  - "visualization", "diagram", "show relationships"')
        print('  - "architecture overview", "dependency graph"')
        print('  - "class structure", "call flow"')
        return True
    print("❌ Template validation failed. Please review the issues above.")
    return False


if __name__ == "__main__":
    success = validate_code_analyzer_template()
    sys.exit(0 if success else 1)
