#!/usr/bin/env python3
"""
Script to remove duplicate 'version' field from agent templates.
Preserves agent_version, template_version, and schema_version fields.
"""
import json
from pathlib import Path
from typing import Dict, List


def remove_duplicate_version(filepath: Path) -> Dict:
    """Remove standalone 'version' field from agent template."""
    with open(filepath) as f:
        data = json.load(f)

    result = {
        "filename": filepath.name,
        "had_duplicate": False,
        "version_value": None,
        "has_agent_version": "agent_version" in data,
        "has_template_version": "template_version" in data,
        "has_schema_version": "schema_version" in data
    }

    # Check if duplicate version exists
    if "version" in data:
        result["had_duplicate"] = True
        result["version_value"] = data["version"]

        # Remove the duplicate version field
        del data["version"]

        # Write back to file with proper formatting
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')  # Add trailing newline

    return result

def validate_json(filepath: Path) -> bool:
    """Validate that JSON is still valid after modification."""
    try:
        with open(filepath) as f:
            json.load(f)
        return True
    except json.JSONDecodeError:
        return False

def main():
    """Main execution function."""
    templates_dir = Path("/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates")

    # Find all agent templates
    agent_files = sorted(templates_dir.glob("*.json"))

    print(f"Found {len(agent_files)} agent templates\n")
    print("=" * 80)
    print("Processing templates...")
    print("=" * 80 + "\n")

    # Process all agents
    results = []
    for filepath in agent_files:
        try:
            result = remove_duplicate_version(filepath)
            results.append(result)

            if result["had_duplicate"]:
                # Validate JSON is still valid
                if validate_json(filepath):
                    print(f"✓ Removed version '{result['version_value']}' from {result['filename']}")
                else:
                    print(f"✗ ERROR: Invalid JSON after processing {result['filename']}")

        except Exception as e:
            print(f"✗ Error processing {filepath.name}: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal agents processed: {len(results)}")
    print(f"Agents with duplicate version removed: {sum(1 for r in results if r['had_duplicate'])}")
    print(f"Agents without duplicate version: {sum(1 for r in results if not r['had_duplicate'])}")

    # Verify version fields
    print("\nVersion field verification:")
    print(f"  - Templates with agent_version: {sum(1 for r in results if r['has_agent_version'])}")
    print(f"  - Templates with template_version: {sum(1 for r in results if r['has_template_version'])}")
    print(f"  - Templates with schema_version: {sum(1 for r in results if r['has_schema_version'])}")

    # List agents that were modified
    modified = [r for r in results if r["had_duplicate"]]
    if modified:
        print(f"\n\nAgents modified ({len(modified)} total):")
        for r in modified:
            print(f"  - {r['filename']}")

    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
