#!/usr/bin/env python3
"""
Script to increment minor version for all agents in the system.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


def increment_minor_version(version: str) -> str:
    """Increment the minor version number."""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")

    major, minor, patch = parts
    new_minor = int(minor) + 1
    # Keep patch as 1 (or as-is if already 1)
    new_patch = "1" if patch == "0" else patch

    return f"{major}.{new_minor}.{new_patch}"


def update_json_templates(base_path: Path) -> List[Tuple[str, str, str]]:
    """Update agent versions in JSON template files."""
    templates_dir = base_path / "src" / "claude_mpm" / "agents" / "templates"
    updates = []

    for json_file in templates_dir.glob("*.json"):
        with open(json_file, "r") as f:
            data = json.load(f)

        old_version = data.get("agent_version", "0.0.0")
        new_version = increment_minor_version(old_version)

        data["agent_version"] = new_version

        with open(json_file, "w") as f:
            json.dump(data, f, indent=2)

        updates.append((json_file.stem, old_version, new_version))
        print(f"Updated {json_file.name}: {old_version} → {new_version}")

    return updates


def update_markdown_agents(base_path: Path) -> List[Tuple[str, str, str]]:
    """Update agent versions in deployed Markdown files."""
    agents_dir = base_path / ".claude" / "agents"
    updates = []

    for md_file in agents_dir.glob("*.md"):
        with open(md_file, "r") as f:
            content = f.read()

        # Find the version in YAML frontmatter
        version_match = re.search(r"^version:\s*([0-9.]+)", content, re.MULTILINE)
        if version_match:
            old_version = version_match.group(1)
            new_version = increment_minor_version(old_version)

            # Update the version
            new_content = re.sub(
                r"^version:\s*[0-9.]+",
                f"version: {new_version}",
                content,
                count=1,
                flags=re.MULTILINE,
            )

            with open(md_file, "w") as f:
                f.write(new_content)

            updates.append((md_file.stem, old_version, new_version))
            print(f"Updated {md_file.name}: {old_version} → {new_version}")

    return updates


def generate_summary(
    json_updates: List[Tuple[str, str, str]], md_updates: List[Tuple[str, str, str]]
) -> str:
    """Generate a summary report of all updates."""
    summary = []
    summary.append("# Agent Version Update Summary\n")
    summary.append("=" * 50 + "\n")

    summary.append("\n## Template Files (JSON)\n")
    summary.append("-" * 30 + "\n")
    for name, old, new in sorted(json_updates):
        summary.append(f"  {name:<20} {old:>8} → {new:<8}\n")

    summary.append("\n## Deployed Agents (Markdown)\n")
    summary.append("-" * 30 + "\n")
    for name, old, new in sorted(md_updates):
        summary.append(f"  {name:<20} {old:>8} → {new:<8}\n")

    summary.append("\n## Statistics\n")
    summary.append("-" * 30 + "\n")
    summary.append(f"  Total JSON templates updated: {len(json_updates)}\n")
    summary.append(f"  Total MD agents updated: {len(md_updates)}\n")
    summary.append(f"  Total files updated: {len(json_updates) + len(md_updates)}\n")

    # Check for consistency
    summary.append("\n## Version Consistency Check\n")
    summary.append("-" * 30 + "\n")

    # Create dictionaries for easy lookup
    json_versions = {name: new for name, _, new in json_updates}
    md_versions = {
        name.replace("-", "_").replace("_agent", ""): new for name, _, new in md_updates
    }

    all_agents = set(json_versions.keys()) | set(md_versions.keys())
    inconsistencies = []

    for agent in sorted(all_agents):
        json_ver = json_versions.get(agent, "N/A")
        md_ver = md_versions.get(agent, "N/A")

        if json_ver != "N/A" and md_ver != "N/A" and json_ver != md_ver:
            inconsistencies.append(f"  ⚠️  {agent}: JSON={json_ver}, MD={md_ver}")
        elif json_ver == "N/A" or md_ver == "N/A":
            source = "JSON" if json_ver != "N/A" else "MD"
            version = json_ver if json_ver != "N/A" else md_ver
            summary.append(f"  ℹ️  {agent}: Only in {source} ({version})\n")

    if inconsistencies:
        summary.append("\n  ⚠️  Version Inconsistencies Found:\n")
        for item in inconsistencies:
            summary.append(item + "\n")
    else:
        summary.append("  ✅ All matching agents have consistent versions\n")

    return "".join(summary)


def main():
    """Main execution function."""
    base_path = Path("/Users/masa/Projects/claude-mpm")

    print("Starting agent version update...")
    print("=" * 50)

    # Update JSON templates
    print("\nUpdating JSON template files...")
    json_updates = update_json_templates(base_path)

    # Update Markdown agents
    print("\nUpdating Markdown agent files...")
    md_updates = update_markdown_agents(base_path)

    # Generate and display summary
    summary = generate_summary(json_updates, md_updates)
    print("\n" + summary)

    # Save summary to file
    summary_file = base_path / "agent_version_update_summary.txt"
    with open(summary_file, "w") as f:
        f.write(summary)
    print(f"\nSummary saved to: {summary_file}")


if __name__ == "__main__":
    main()
