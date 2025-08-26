#!/usr/bin/env python3
"""
Agent Configuration Validator

This script validates agent configurations against the Claude MPM agent schema.
It provides detailed error reporting and examples of both valid and invalid configurations.

Usage:
    python validate_agent_configuration.py <agent_config.json>
    python validate_agent_configuration.py --example
    python validate_agent_configuration.py --all
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from jsonschema import Draft7Validator, ValidationError, validate
except ImportError:
    print("Error: jsonschema is required. Install with: pip install jsonschema")
    sys.exit(1)


class AgentConfigValidator:
    """Validates agent configurations against the Claude MPM schema."""

    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize validator with schema."""
        if schema_path is None:
            # Use the primary schema by default
            schema_path = (
                Path(__file__).parent.parent
                / "src"
                / "claude_mpm"
                / "schemas"
                / "agent_schema.json"
            )

        with open(schema_path) as f:
            self.schema = json.load(f)

        self.validator = Draft7Validator(self.schema)

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate an agent configuration.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Collect all validation errors
        for error in self.validator.iter_errors(config):
            error_path = (
                " -> ".join(str(p) for p in error.path) if error.path else "root"
            )
            errors.append(f"{error_path}: {error.message}")

        return len(errors) == 0, errors

    def validate_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Validate an agent configuration file."""
        try:
            with open(file_path) as f:
                config = json.load(f)
            return self.validate_config(config)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]
        except Exception as e:
            return False, [f"Error reading file: {e}"]

    def generate_report(self, file_path: Path) -> str:
        """Generate a detailed validation report."""
        is_valid, errors = self.validate_file(file_path)

        report = f"\n{'='*60}\n"
        report += f"Validation Report for: {file_path.name}\n"
        report += f"{'='*60}\n\n"

        if is_valid:
            report += "✅ VALID - Configuration passes all validation checks\n"

            # Load config to show summary
            with open(file_path) as f:
                config = json.load(f)

            report += "\nAgent Summary:\n"
            report += f"  - ID: {config.get('agent_id', 'N/A')}\n"
            report += f"  - Type: {config.get('agent_type', 'N/A')}\n"
            report += f"  - Version: {config.get('agent_version', 'N/A')}\n"
            report += (
                f"  - Model: {config.get('capabilities', {}).get('model', 'N/A')}\n"
            )

            tools = config.get("capabilities", {}).get("tools", [])
            report += f"  - Tools: {len(tools)} enabled\n"

        else:
            report += "❌ INVALID - Configuration has validation errors\n\n"
            report += f"Found {len(errors)} error(s):\n\n"

            for i, error in enumerate(errors, 1):
                report += f"{i}. {error}\n"

        return report


def create_example_configs():
    """Create example valid and invalid configurations."""

    # Valid minimal configuration
    valid_minimal = {
        "schema_version": "1.2.0",
        "agent_id": "example_agent",
        "agent_version": "1.0.0",
        "agent_type": "base",
        "metadata": {
            "name": "Example Agent",
            "description": "A minimal valid agent configuration example",
            "tags": ["example", "minimal"],
        },
        "capabilities": {
            "model": "claude-3-haiku-20240307",
            "tools": ["Read", "Write"],
            "resource_tier": "basic",
        },
        "instructions": "You are a helpful assistant that demonstrates a minimal valid agent configuration. Always be concise and accurate in your responses.",
    }

    # Invalid configuration with multiple errors
    invalid_example = {
        "schema_version": "1.2",  # Missing patch version
        "agent_id": "Invalid-Agent",  # Contains uppercase and hyphen
        "agent_type": "custom",  # Not in enum
        "metadata": {"name": "Ex", "tags": "example"},  # Too short  # Should be array
        "capabilities": {
            "model": "gpt-4",  # Not a Claude model
            "tools": ["Read", "InvalidTool"],
            "resource_tier": "extreme",  # Not in enum
        }
        # Missing required fields: agent_version, instructions
    }

    return valid_minimal, invalid_example


def validate_all_templates():
    """Validate all agent templates in the project."""
    templates_dir = (
        Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "templates"
    )

    if not templates_dir.exists():
        print(f"Templates directory not found: {templates_dir}")
        return

    validator = AgentConfigValidator()
    results = []

    for template_file in sorted(templates_dir.glob("*.json")):
        is_valid, errors = validator.validate_file(template_file)
        results.append((template_file, is_valid, errors))

    # Print summary
    print(f"\n{'='*60}")
    print("Agent Template Validation Summary")
    print(f"{'='*60}\n")

    valid_count = sum(1 for _, is_valid, _ in results if is_valid)
    print(f"Total templates: {len(results)}")
    print(f"Valid: {valid_count}")
    print(f"Invalid: {len(results) - valid_count}\n")

    # Show details
    for template_file, is_valid, errors in results:
        if is_valid:
            print(f"✅ {template_file.name}")
        else:
            print(f"❌ {template_file.name}")
            for error in errors[:3]:  # Show first 3 errors
                print(f"   - {error}")
            if len(errors) > 3:
                print(f"   ... and {len(errors) - 3} more errors")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Claude MPM agent configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a specific agent configuration
  python validate_agent_configuration.py path/to/agent.json

  # Show example configurations
  python validate_agent_configuration.py --example

  # Validate all templates
  python validate_agent_configuration.py --all
        """,
    )

    parser.add_argument(
        "config_file", nargs="?", help="Path to agent configuration JSON file"
    )
    parser.add_argument(
        "--example", action="store_true", help="Show example configurations"
    )
    parser.add_argument(
        "--all", action="store_true", help="Validate all agent templates"
    )
    parser.add_argument("--schema", help="Path to custom schema file")

    args = parser.parse_args()

    if args.example:
        # Show example configurations
        valid, invalid = create_example_configs()

        print("\n" + "=" * 60)
        print("VALID CONFIGURATION EXAMPLE")
        print("=" * 60)
        print(json.dumps(valid, indent=2))

        print("\n" + "=" * 60)
        print("INVALID CONFIGURATION EXAMPLE")
        print("=" * 60)
        print(json.dumps(invalid, indent=2))

        # Validate the examples
        validator = AgentConfigValidator()
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)

        is_valid, errors = validator.validate_config(valid)
        print(f"\nValid example: {'✅ PASSES' if is_valid else '❌ FAILS'}")

        is_valid, errors = validator.validate_config(invalid)
        print(f"\nInvalid example: {'❌ FAILS' if not is_valid else '✅ PASSES'}")
        if errors:
            print("Errors found:")
            for error in errors:
                print(f"  - {error}")

    elif args.all:
        # Validate all templates
        validate_all_templates()

    elif args.config_file:
        # Validate specific file
        config_path = Path(args.config_file)

        if not config_path.exists():
            print(f"Error: File not found: {config_path}")
            sys.exit(1)

        schema_path = Path(args.schema) if args.schema else None
        validator = AgentConfigValidator(schema_path)

        report = validator.generate_report(config_path)
        print(report)

        # Exit with error code if invalid
        is_valid, _ = validator.validate_file(config_path)
        sys.exit(0 if is_valid else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
