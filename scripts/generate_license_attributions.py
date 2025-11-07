#!/usr/bin/env python3
"""
License attribution generator for bundled Claude Code skills.

Scans all bundled skills, extracts license information from SKILL.md frontmatter,
and generates a comprehensive LICENSE_ATTRIBUTIONS.md file.

Features:
- Scans src/claude_mpm/skills/bundled/ directory
- Extracts license info from SKILL.md frontmatter
- Groups by license type
- Generates markdown table format
- Validates all skills have license field
- Includes skill name, source URL, author, and license
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class LicenseAttributionGenerator:
    """Generate license attributions for bundled skills."""

    def __init__(self, bundled_dir: Path, output_path: Path) -> None:
        """Initialize generator.

        Args:
            bundled_dir: Path to bundled skills directory
            output_path: Path to output LICENSE_ATTRIBUTIONS.md
        """
        self.bundled_dir: Path = bundled_dir
        self.output_path: Path = output_path
        self.skills: List[Dict[str, Any]] = []
        self.missing_license: List[str] = []

    def scan_skills(self) -> None:
        """Scan bundled directory for skills and extract metadata."""
        if not self.bundled_dir.exists():
            print(
                f"Error: Bundled directory not found: {self.bundled_dir}",
                file=sys.stderr,
            )
            sys.exit(1)

        for category_dir in sorted(self.bundled_dir.iterdir()):
            if not category_dir.is_dir():
                continue

            for skill_dir in sorted(category_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue

                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue

                metadata = self._extract_metadata(skill_md)
                if metadata:
                    skill_info = {
                        "name": metadata.get("name", skill_dir.name),
                        "category": category_dir.name,
                        "license": metadata.get("license", "UNKNOWN"),
                        "author": metadata.get("author", "Unknown"),
                        "source": metadata.get("source", ""),
                        "description": metadata.get("description", ""),
                    }

                    self.skills.append(skill_info)

                    if not metadata.get("license"):
                        self.missing_license.append(skill_info["name"])

    def _extract_metadata(self, skill_md: Path) -> Optional[Dict[str, Any]]:
        """Extract YAML frontmatter from SKILL.md.

        Args:
            skill_md: Path to SKILL.md file

        Returns:
            Parsed metadata dictionary or None if invalid
        """
        try:
            content = skill_md.read_text(encoding="utf-8")

            # Extract frontmatter
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not match:
                return None

            return yaml.safe_load(match.group(1))
        except (OSError, yaml.YAMLError) as e:
            print(f"Warning: Could not parse {skill_md}: {e}", file=sys.stderr)
            return None
        except Exception as e:
            # Unexpected error - re-raise with context
            print(f"Unexpected error parsing {skill_md}: {e}", file=sys.stderr)
            raise

    def generate_attribution(self) -> str:
        """Generate LICENSE_ATTRIBUTIONS.md content.

        Returns:
            Markdown content string
        """
        lines = []

        # Header
        lines.append("# License Attributions for Bundled Skills")
        lines.append("")
        lines.append(
            "This document provides license information and attributions for all "
            "skills bundled with Claude MPM."
        )
        lines.append("")
        lines.append("---")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Skills**: {len(self.skills)}")

        # Count by license
        licenses_count = defaultdict(int)
        for skill in self.skills:
            licenses_count[skill["license"]] += 1

        lines.append(f"- **Unique Licenses**: {len(licenses_count)}")
        lines.append("")

        for license_type, count in sorted(
            licenses_count.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"  - **{license_type}**: {count} skill(s)")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Group skills by license
        skills_by_license = defaultdict(list)
        for skill in self.skills:
            skills_by_license[skill["license"]].append(skill)

        # Generate attribution for each license type
        for license_type in sorted(skills_by_license.keys()):
            lines.append(f"## {license_type} Licensed Skills")
            lines.append("")

            skills = skills_by_license[license_type]

            # Create table
            lines.append("| Skill Name | Author | Category | Description | Source |")
            lines.append("|------------|--------|----------|-------------|--------|")

            for skill in sorted(skills, key=lambda x: x["name"]):
                name = skill["name"]
                author = skill["author"]
                category = skill["category"]
                description = (
                    skill["description"][:60] + "..."
                    if len(skill["description"]) > 60
                    else skill["description"]
                )
                source = skill["source"]

                # Format source as link if it's a URL
                if source:
                    source_link = f"[Link]({source})"
                else:
                    source_link = "N/A"

                lines.append(
                    f"| {name} | {author} | {category} | {description} | {source_link} |"
                )

            lines.append("")
            lines.append("---")
            lines.append("")

        # Missing license warning
        if self.missing_license:
            lines.append("## ⚠️ Missing License Information")
            lines.append("")
            lines.append(
                "The following skills do not have license information in their SKILL.md:"
            )
            lines.append("")
            for skill_name in sorted(self.missing_license):
                lines.append(f"- {skill_name}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("## How to Update")
        lines.append("")
        lines.append("To update this file, run:")
        lines.append("")
        lines.append("```bash")
        lines.append("python scripts/generate_license_attributions.py")
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Generated automatically by Claude MPM*")
        lines.append("")

        return "\n".join(lines)

    def write_attribution(self, content: str) -> None:
        """Write attribution file.

        Args:
            content: Markdown content to write
        """
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(content, encoding="utf-8")


def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate license attributions for bundled skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script scans all bundled skills and generates a comprehensive
LICENSE_ATTRIBUTIONS.md file containing:

- List of all skills with their licenses
- Grouped by license type
- Includes author, source URL, and description
- Markdown table format for readability
- Validation that all skills have license information

Examples:
  # Generate attribution file
  %(prog)s

  # Specify custom bundled directory
  %(prog)s --bundled-dir path/to/bundled

  # Specify custom output path
  %(prog)s --output path/to/LICENSE_ATTRIBUTIONS.md

  # Dry run (don't write file)
  %(prog)s --dry-run
        """,
    )

    parser.add_argument(
        "--bundled-dir",
        type=Path,
        default=Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "skills"
        / "bundled",
        help="Path to bundled skills directory",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "skills"
        / "bundled"
        / "LICENSE_ATTRIBUTIONS.md",
        help="Output path for LICENSE_ATTRIBUTIONS.md",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output instead of writing to file",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate that all skills have license information",
    )

    args = parser.parse_args()

    # Initialize generator
    generator = LicenseAttributionGenerator(args.bundled_dir, args.output)

    # Scan skills
    print(f"Scanning skills in: {args.bundled_dir}")
    generator.scan_skills()

    print(f"Found {len(generator.skills)} skills")

    # Check for missing licenses
    if generator.missing_license:
        print(
            f"\n⚠️  WARNING: {len(generator.missing_license)} skill(s) missing license information:"
        )
        for skill in generator.missing_license:
            print(f"  - {skill}")
        print()

        if args.validate_only:
            print("Validation failed: Not all skills have license information")
            sys.exit(1)

    if args.validate_only:
        print("✓ All skills have license information")
        sys.exit(0)

    # Generate attribution
    print("Generating license attributions...")
    content = generator.generate_attribution()

    # Write or print
    if args.dry_run:
        print("\n" + "=" * 80)
        print("DRY RUN - Output:")
        print("=" * 80)
        print(content)
    else:
        generator.write_attribution(content)
        print(f"✓ Generated: {args.output}")

        # Summary
        lines = content.count("\n")
        print(f"  Lines: {lines}")
        print(f"  Skills: {len(generator.skills)}")
        print(f"  Licenses: {len(set(skill['license'] for skill in generator.skills))}")

    sys.exit(0)


if __name__ == "__main__":
    main()
