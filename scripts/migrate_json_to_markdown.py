#!/usr/bin/env python3
"""
One-time migration script: JSON agent templates → Markdown with YAML frontmatter

This script converts JSON agent templates to the new Markdown format with YAML frontmatter,
preserving all metadata and validating output against the frontmatter schema.

Usage:
    # Dry-run (preview changes)
    python scripts/migrate_json_to_markdown.py --dry-run

    # Convert specific agent
    python scripts/migrate_json_to_markdown.py --agent research-agent

    # Convert all agents
    python scripts/migrate_json_to_markdown.py --all

    # Convert with archive (keeps JSON as backup)
    python scripts/migrate_json_to_markdown.py --all --archive

    # Validate migrated files
    python scripts/migrate_json_to_markdown.py --validate-only
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.claude_mpm.agents.frontmatter_validator import (
    FrontmatterValidator,
    ValidationResult,
)


# Error types
class MigrationError(Exception):
    """Base exception for migration errors."""


class JSONParseError(MigrationError):
    """JSON parsing failed."""


class ValidationError(MigrationError):
    """Frontmatter validation failed."""


class FileWriteError(MigrationError):
    """Failed to write markdown file."""


@dataclass
class ConversionResult:
    """Result of a single template conversion."""

    json_path: str
    md_path: Optional[str]
    status: str  # success, error, skipped
    validation: Optional[ValidationResult]
    error_message: Optional[str] = None


@dataclass
class MigrationReport:
    """Summary report of migration operation."""

    total_templates: int
    converted: int
    errors: int
    warnings: int
    results: List[ConversionResult]
    archive_path: Optional[Path] = None


def extract_frontmatter_fields(template_data: dict) -> dict:
    """
    Extract fields suitable for YAML frontmatter from JSON template.

    This function maps JSON agent schema fields to the frontmatter structure,
    handling nested fields and optional values correctly.

    Args:
        template_data: Parsed JSON template data

    Returns:
        Dictionary of frontmatter fields with None values removed

    Raises:
        KeyError: If required fields are missing from template
    """
    # Core required fields with validation
    metadata = template_data.get("metadata", {})
    capabilities = template_data.get("capabilities", {})

    # Build frontmatter with defaults for missing fields
    frontmatter = {
        "name": metadata.get(
            "name", f"Agent {template_data.get('agent_id', 'unknown')}"
        ),
        "description": metadata.get("description", "Agent description not provided"),
        "version": template_data.get("agent_version", "1.0.0"),
        "schema_version": template_data.get("schema_version", "1.3.0"),
        "agent_id": template_data.get("agent_id", "unknown-agent"),
        "agent_type": template_data.get("agent_type", "specialized"),
        "model": capabilities.get("model", "sonnet"),
        "resource_tier": capabilities.get("resource_tier", "standard"),
    }

    # Metadata fields (optional)
    if "tags" in metadata:
        frontmatter["tags"] = metadata["tags"]

    if "category" in metadata:
        frontmatter["category"] = metadata["category"]

    if "color" in metadata:
        frontmatter["color"] = metadata["color"]

    if "author" in metadata:
        frontmatter["author"] = metadata["author"]

    # Capability fields (optional)
    if "temperature" in capabilities:
        frontmatter["temperature"] = capabilities["temperature"]

    if "max_tokens" in capabilities:
        frontmatter["max_tokens"] = capabilities["max_tokens"]

    if "timeout" in capabilities:
        frontmatter["timeout"] = capabilities["timeout"]

    # Nested capabilities (only if any are present)
    nested_caps = {}
    for field in ["memory_limit", "cpu_limit", "network_access"]:
        if field in capabilities:
            nested_caps[field] = capabilities[field]

    if nested_caps:
        frontmatter["capabilities"] = nested_caps

    # Optional extended fields
    if "dependencies" in template_data:
        frontmatter["dependencies"] = template_data["dependencies"]

    if "skills" in template_data:
        frontmatter["skills"] = template_data["skills"]

    if "template_version" in template_data:
        frontmatter["template_version"] = template_data["template_version"]

    if "template_changelog" in template_data:
        frontmatter["template_changelog"] = template_data["template_changelog"]

    # Optional knowledge, interactions, memory_routing (preserve if present)
    for field in ["knowledge", "interactions", "memory_routing"]:
        if field in template_data:
            frontmatter[field] = template_data[field]

    # Remove None values to keep frontmatter clean
    return {k: v for k, v in frontmatter.items() if v is not None}


def build_markdown(frontmatter: dict, instructions: str) -> str:
    """
    Build final markdown content with YAML frontmatter.

    Args:
        frontmatter: Dictionary of frontmatter fields
        instructions: Agent instructions markdown

    Returns:
        Complete markdown content with frontmatter
    """
    # Generate YAML with proper formatting
    yaml_content = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=float("inf"),  # Prevent line wrapping
    )

    # Combine frontmatter and instructions
    return f"---\n{yaml_content}---\n\n{instructions}"


def convert_json_to_markdown(
    json_path: Path, validate: bool = True
) -> Tuple[str, ValidationResult]:
    """
    Convert JSON template to markdown with YAML frontmatter.

    This is the core conversion function that orchestrates the transformation
    from JSON to Markdown format, including validation.

    Args:
        json_path: Path to JSON template file
        validate: Whether to validate frontmatter

    Returns:
        Tuple of (markdown_content, validation_result)

    Raises:
        JSONParseError: If JSON parsing fails
        ValidationError: If validation fails with errors
    """
    # Load JSON template
    try:
        with json_path.open() as f:
            template_data = json.load(f)
    except json.JSONDecodeError as e:
        raise JSONParseError(f"Failed to parse JSON: {e}")
    except Exception as e:
        raise JSONParseError(f"Error reading JSON file: {e}")

    # Extract frontmatter fields
    frontmatter = extract_frontmatter_fields(template_data)

    # Validate and correct frontmatter
    validator = FrontmatterValidator()
    validation = validator.validate_and_correct(frontmatter)

    # Use corrected frontmatter if corrections were made
    final_frontmatter = validation.corrected_frontmatter or frontmatter

    # Check for critical validation errors
    if validate and not validation.is_valid:
        raise ValidationError(f"Validation failed: {validation.errors}")

    # Extract instructions (markdown body)
    instructions = template_data.get("instructions", "")

    # Build markdown content
    markdown = build_markdown(final_frontmatter, instructions)

    return markdown, validation


def safe_convert(
    json_path: Path,
    output_dir: Optional[Path] = None,
    archive_mode: bool = False,
    dry_run: bool = False,
) -> ConversionResult:
    """
    Convert with error handling and rollback.

    This function wraps the conversion process with comprehensive error handling,
    rollback on failure, and optional dry-run mode.

    Args:
        json_path: Path to JSON template
        output_dir: Optional output directory (default: same as input)
        archive_mode: Archive JSON instead of deleting
        dry_run: Preview only, don't write files

    Returns:
        ConversionResult with status and details
    """
    output_path = None

    try:
        # Convert to markdown
        markdown, validation = convert_json_to_markdown(json_path)

        # Determine output path
        if output_dir:
            output_path = output_dir / json_path.with_suffix(".md").name
        else:
            output_path = json_path.with_suffix(".md")

        if dry_run:
            # Dry-run: don't write, just validate
            return ConversionResult(
                json_path=str(json_path),
                md_path=str(output_path),
                status="preview",
                validation=validation,
            )

        # Write markdown file
        try:
            output_path.write_text(markdown, encoding="utf-8")
        except Exception as e:
            raise FileWriteError(f"Failed to write markdown: {e}")

        # Archive or delete JSON
        if archive_mode:
            archive_path = json_path.parent / "archive" / json_path.name
            archive_path.parent.mkdir(exist_ok=True, parents=True)
            json_path.rename(archive_path)
        else:
            # For now, don't delete JSON - just leave it alongside markdown
            # This provides a safety net during migration
            pass

        return ConversionResult(
            json_path=str(json_path),
            md_path=str(output_path),
            status="success",
            validation=validation,
        )

    except JSONParseError as e:
        return ConversionResult(
            json_path=str(json_path),
            md_path=None,
            status="error",
            validation=None,
            error_message=f"JSON parse error: {e}",
        )

    except ValidationError as e:
        # Rollback: delete generated markdown if validation failed
        if output_path and output_path.exists():
            output_path.unlink()

        return ConversionResult(
            json_path=str(json_path),
            md_path=None,
            status="error",
            validation=None,
            error_message=f"Validation error: {e}",
        )

    except Exception as e:
        # Rollback on unexpected errors
        if output_path and output_path.exists():
            output_path.unlink()

        return ConversionResult(
            json_path=str(json_path),
            md_path=None,
            status="error",
            validation=None,
            error_message=f"Unexpected error: {e}",
        )


def migrate_templates(
    templates_dir: Path,
    dry_run: bool = False,
    agent_name: Optional[str] = None,
    archive: bool = False,
    output_dir: Optional[Path] = None,
    verbose: bool = False,
) -> MigrationReport:
    """
    Migrate templates with CLI options.

    This is the main migration orchestrator that handles batch or single-agent
    conversion based on CLI arguments.

    Args:
        templates_dir: Directory containing JSON templates
        dry_run: Preview mode without writing files
        agent_name: Specific agent ID to convert (None = all)
        archive: Archive JSON files instead of deleting
        output_dir: Optional output directory
        verbose: Verbose logging

    Returns:
        MigrationReport with conversion results
    """
    # Find JSON templates
    if agent_name:
        # Single agent mode
        json_files = list(templates_dir.glob(f"{agent_name}.json"))
        if not json_files:
            print(f"ERROR: Template not found: {agent_name}.json")
            return MigrationReport(
                total_templates=0, converted=0, errors=1, warnings=0, results=[]
            )
    else:
        # Batch mode - all JSON files
        json_files = sorted(templates_dir.glob("*.json"))

    if not json_files:
        print("No JSON templates found.")
        return MigrationReport(
            total_templates=0, converted=0, errors=0, warnings=0, results=[]
        )

    # Convert each template
    results: List[ConversionResult] = []
    for json_path in json_files:
        if verbose:
            print(f"Converting: {json_path.name}...")

        result = safe_convert(
            json_path, output_dir=output_dir, archive_mode=archive, dry_run=dry_run
        )
        results.append(result)

        if verbose and result.status == "success":
            print(f"  ✅ {result.md_path}")
            if result.validation and result.validation.warnings:
                for warning in result.validation.warnings:
                    print(f"     ⚠️  {warning}")
        elif verbose and result.status == "error":
            print(f"  ❌ {result.error_message}")

    # Calculate statistics
    converted = sum(1 for r in results if r.status in ["success", "preview"])
    errors = sum(1 for r in results if r.status == "error")
    warnings = sum(
        len(r.validation.warnings)
        for r in results
        if r.validation and r.validation.warnings
    )

    # Determine archive path
    archive_path = None
    if archive and not dry_run:
        archive_path = templates_dir / "archive"

    return MigrationReport(
        total_templates=len(json_files),
        converted=converted,
        errors=errors,
        warnings=warnings,
        results=results,
        archive_path=archive_path,
    )


def print_migration_report(report: MigrationReport, dry_run: bool = False) -> None:
    """
    Print comprehensive migration report.

    Args:
        report: MigrationReport to display
        dry_run: Whether this was a dry-run
    """
    print("\n" + "=" * 70)
    print("JSON to Markdown Agent Template Migration Report")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if dry_run:
        print("Mode: DRY-RUN (preview only, no files written)")
    print()

    # Summary
    print("Summary:")
    print("-" * 70)
    print(f"Total templates found:      {report.total_templates}")
    print(f"Successfully converted:     {report.converted}")
    print(f"Validation errors:          {report.errors}")
    print(f"Validation warnings:        {report.warnings}")
    if report.archive_path:
        print(f"Archived JSON files:        {report.total_templates}")
        print(f"Archive location:           {report.archive_path}")
    print()

    # Conversions
    print("Conversions:")
    print("-" * 70)

    for result in report.results:
        json_name = Path(result.json_path).name

        if result.status in ["success", "preview"]:
            md_name = Path(result.md_path).name if result.md_path else "unknown"
            status_icon = "🔍" if result.status == "preview" else "✅"

            warning_count = (
                len(result.validation.warnings)
                if result.validation and result.validation.warnings
                else 0
            )

            if warning_count > 0:
                print(f"⚠️  {json_name} → {md_name} ({warning_count} warnings)")
            else:
                print(f"{status_icon} {json_name} → {md_name}")

            # Show warnings if present
            if result.validation and result.validation.warnings:
                for warning in result.validation.warnings:
                    print(f"     - {warning}")

        elif result.status == "error":
            print(f"❌ {json_name} → FAILED")
            print(f"     Error: {result.error_message}")

    print()

    # Next steps
    if not dry_run and report.converted > 0:
        print("Next Steps:")
        print("-" * 70)
        print("1. Review validation warnings above")
        if report.errors > 0:
            print("2. Fix validation errors in failed conversions")
        print("3. Update code references from *.json to *.md (see ticket 1M-394)")
        print("4. Run test suite to verify agent loading")
        print("5. Deploy migrated agents: claude-mpm agents deploy --all --force")
    elif dry_run:
        print("To execute migration:")
        print("-" * 70)
        print("  python scripts/migrate_json_to_markdown.py --all --archive")

    print()


def validate_existing_markdown(templates_dir: Path, verbose: bool = False) -> None:
    """
    Validate existing markdown files without conversion.

    Args:
        templates_dir: Directory containing markdown files
        verbose: Verbose output
    """
    validator = FrontmatterValidator()
    md_files = sorted(templates_dir.glob("*.md"))

    if not md_files:
        print("No markdown files found.")
        return

    print(f"Validating {len(md_files)} markdown files...\n")

    errors_count = 0
    warnings_count = 0

    for md_path in md_files:
        result = validator.validate_file(md_path)

        if not result.is_valid:
            errors_count += 1
            print(f"❌ {md_path.name} - INVALID")
            for error in result.errors:
                print(f"     Error: {error}")
        elif result.warnings:
            warnings_count += 1
            print(f"⚠️  {md_path.name} - Valid with warnings")
            for warning in result.warnings:
                print(f"     Warning: {warning}")
        elif verbose:
            print(f"✅ {md_path.name} - Valid")

    print()
    print(f"Validation complete: {len(md_files)} files checked")
    print(f"Errors: {errors_count}, Warnings: {warnings_count}")


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate JSON agent templates to Markdown with YAML frontmatter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview all conversions
  python scripts/migrate_json_to_markdown.py --dry-run

  # Convert specific agent
  python scripts/migrate_json_to_markdown.py --agent research-agent

  # Convert all with archive
  python scripts/migrate_json_to_markdown.py --all --archive

  # Validate existing markdown files
  python scripts/migrate_json_to_markdown.py --validate-only
        """,
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without writing files"
    )

    parser.add_argument(
        "--agent",
        type=str,
        help="Convert specific agent by ID (e.g., 'research-agent')",
    )

    parser.add_argument("--all", action="store_true", help="Convert all JSON templates")

    parser.add_argument(
        "--archive",
        action="store_true",
        help="Archive JSON files to templates/archive/ instead of deleting",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate existing markdown files without conversion",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for migrated files (default: same as input)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output with detailed logging",
    )

    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=PROJECT_ROOT / "src" / "claude_mpm" / "agents" / "templates",
        help="Templates directory (default: src/claude_mpm/agents/templates)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.agent and not args.validate_only:
        parser.error("Must specify --all, --agent, or --validate-only")

    if args.agent and args.all:
        parser.error("Cannot specify both --agent and --all")

    # Check templates directory
    if not args.templates_dir.exists():
        print(f"ERROR: Templates directory not found: {args.templates_dir}")
        sys.exit(1)

    # Validate-only mode
    if args.validate_only:
        validate_existing_markdown(args.templates_dir, verbose=args.verbose)
        return

    # Run migration
    report = migrate_templates(
        templates_dir=args.templates_dir,
        dry_run=args.dry_run,
        agent_name=args.agent,
        archive=args.archive,
        output_dir=args.output_dir,
        verbose=args.verbose,
    )

    # Print report
    print_migration_report(report, dry_run=args.dry_run)

    # Exit with error code if there were failures
    if report.errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
