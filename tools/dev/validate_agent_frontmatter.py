#!/usr/bin/env python3
"""
Test script to validate and report on agent file frontmatter.

This script tests the frontmatter validation system by checking all agent files
in the .claude/agents directory and reporting validation results.
"""

import logging
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.agents.frontmatter_validator import FrontmatterValidator


def main():
    """Main function to test frontmatter validation."""
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Create validator
    validator = FrontmatterValidator()

    # Find agent files
    claude_agents_dir = Path.cwd() / ".claude" / "agents"

    if not claude_agents_dir.exists():
        print(f"Directory not found: {claude_agents_dir}")
        return 1

    print(f"\nValidating agent files in: {claude_agents_dir}")
    print("=" * 60)

    # Statistics
    stats = {
        "total": 0,
        "valid": 0,
        "corrected": 0,
        "errors": 0,
        "files_with_corrections": [],
        "files_with_errors": [],
    }

    # Process each .md file
    for md_file in sorted(claude_agents_dir.glob("*.md")):
        stats["total"] += 1
        print(f"\n📄 {md_file.name}")
        print("-" * 40)

        # Validate the file
        result = validator.validate_file(md_file)

        # Report results
        if result.is_valid and not result.corrections:
            print("✅ Valid - No issues found")
            stats["valid"] += 1
        elif result.corrections:
            print("⚠️  Auto-correctable issues found:")
            stats["corrected"] += 1
            stats["files_with_corrections"].append(md_file.name)

            for correction in result.corrections:
                print(f"   📝 {correction}")

            if result.corrected_frontmatter:
                print("\n   Corrected frontmatter fields:")
                for key, value in result.corrected_frontmatter.items():
                    if key == "tools" and isinstance(value, list):
                        print(
                            f"   - {key}: [{', '.join(value[:3])}...]"
                            if len(value) > 3
                            else f"   - {key}: {value}"
                        )
                    else:
                        print(f"   - {key}: {value}")

        if result.errors:
            print("❌ Validation errors:")
            stats["errors"] += 1
            stats["files_with_errors"].append(md_file.name)

            for error in result.errors:
                print(f"   ⚠️  {error}")

        if result.warnings:
            print("⚠️  Warnings:")
            for warning in result.warnings:
                print(f"   ℹ️  {warning}")

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total files checked: {stats['total']}")
    print(f"✅ Valid (no issues): {stats['valid']}")
    print(f"⚠️  Auto-correctable: {stats['corrected']}")
    print(f"❌ With errors: {stats['errors']}")

    if stats["files_with_corrections"]:
        print("\nFiles with auto-corrections:")
        for filename in stats["files_with_corrections"]:
            print(f"  - {filename}")

    if stats["files_with_errors"]:
        print("\nFiles with errors:")
        for filename in stats["files_with_errors"]:
            print(f"  - {filename}")

    # Test specific problematic frontmatter examples
    print("\n" + "=" * 60)
    print("TESTING SPECIFIC CORRECTION SCENARIOS")
    print("=" * 60)

    test_cases = [
        {
            "name": "String tools field",
            "frontmatter": {
                "name": "test_agent",
                "description": "Test agent for validation",
                "version": "1.0.0",
                "model": "opus",
                "tools": "Read, Write, Edit, Bash",
            },
        },
        {
            "name": "Invalid model format",
            "frontmatter": {
                "name": "test_agent",
                "description": "Test agent for validation",
                "version": "1.0.0",
                "model": "claude-3-5-sonnet-20241022",
                "tools": ["Read", "Write"],
            },
        },
        {
            "name": "Model as date",
            "frontmatter": {
                "name": "qa",
                "description": "QA agent for testing",
                "version": "1.0.0",
                "model": "20241022",
                "tools": ["Read", "Write"],
            },
        },
    ]

    for test_case in test_cases:
        print(f"\n🧪 Test: {test_case['name']}")
        print("-" * 40)

        result = validator.validate_and_correct(test_case["frontmatter"])

        if result.corrections:
            print("Corrections applied:")
            for correction in result.corrections:
                print(f"  - {correction}")

        if result.corrected_frontmatter:
            print("Corrected values:")
            if "model" in result.corrected_frontmatter:
                print(f"  - model: {result.corrected_frontmatter['model']}")
            if "tools" in result.corrected_frontmatter:
                tools = result.corrected_frontmatter["tools"]
                print(
                    f"  - tools: {type(tools).__name__} with {len(tools) if isinstance(tools, list) else 0} items"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
