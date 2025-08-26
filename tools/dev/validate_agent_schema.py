#!/usr/bin/env python3
"""Validate agent templates against the schema."""

import json
import sys
from pathlib import Path

from jsonschema import ValidationError, validate


def validate_agent_template(template_path: Path, schema_path: Path) -> bool:
    """Validate an agent template against the schema."""
    try:
        # Load template
        with open(template_path) as f:
            template = json.load(f)

        # Load schema
        with open(schema_path) as f:
            schema = json.load(f)

        # Validate
        validate(instance=template, schema=schema)
        print(f"✓ {template_path.name} is valid")
        return True

    except ValidationError as e:
        print(f"✗ {template_path.name} validation failed:")
        print(f"  Path: {' -> '.join(str(x) for x in e.path)}")
        print(f"  Error: {e.message}")
        return False
    except Exception as e:
        print(f"✗ {template_path.name} error: {e}")
        return False


def main():
    """Main validation function."""
    # Find project root
    project_root = Path(__file__).parent.parent

    # Schema path
    schema_path = (
        project_root / "src" / "claude_mpm" / "agents" / "schema" / "agent_schema.json"
    )

    # Template directory
    template_dir = project_root / "src" / "claude_mpm" / "agents" / "templates"

    # Validate all templates
    templates = list(template_dir.glob("*.json"))
    if not templates:
        print("No templates found!")
        return 1

    print(f"Validating {len(templates)} templates against schema...\n")

    valid_count = 0
    for template_path in sorted(templates):
        if validate_agent_template(template_path, schema_path):
            valid_count += 1

    print(f"\nValidation complete: {valid_count}/{len(templates)} templates are valid")

    return 0 if valid_count == len(templates) else 1


if __name__ == "__main__":
    sys.exit(main())
