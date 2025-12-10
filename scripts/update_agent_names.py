#!/usr/bin/env python3
"""
Update agent markdown files with user-friendly display names.

Converts internal IDs like 'research_agent' to 'Research Agent'.
"""

import re
from pathlib import Path
from typing import Dict


def convert_to_display_name(internal_name: str) -> str:
    """Convert internal agent name to user-friendly display name.

    Rules:
    1. Replace underscores/hyphens with spaces
    2. Remove '_agent' suffix
    3. Title case
    4. Fix common abbreviations (qa, api, ui, mpm, gcp)

    Examples:
        research_agent -> Research Agent
        qa_agent -> QA Agent
        mpm-agent-manager -> MPM Agent Manager
        web-ui -> Web UI
        gcp-ops -> GCP Ops
    """
    # Replace underscores and hyphens with spaces
    name = internal_name.replace("_", " ").replace("-", " ")

    # Remove '_agent' or 'agent' suffix if present
    name = re.sub(r"\s+agent$", "", name, flags=re.IGNORECASE)

    # Split into words
    words = name.split()

    # Special case mappings for abbreviations
    special_cases = {
        "qa": "QA",
        "api": "API",
        "ui": "UI",
        "mpm": "MPM",
        "gcp": "GCP",
        "aws": "AWS",
        "id": "ID",
        "url": "URL",
        "http": "HTTP",
        "html": "HTML",
        "css": "CSS",
        "js": "JS",
        "ts": "TS",
        "sql": "SQL",
    }

    # Process each word
    processed_words = []
    for word in words:
        lower_word = word.lower()
        if lower_word in special_cases:
            processed_words.append(special_cases[lower_word])
        else:
            processed_words.append(word.capitalize())

    return " ".join(processed_words)


def update_agent_file(file_path: Path) -> tuple[bool, str, str]:
    """Update the name field in agent markdown frontmatter.

    Returns:
        tuple: (success, old_name, new_name)
    """
    content = file_path.read_text()

    # Match YAML frontmatter name field
    # Pattern: name: <value> (with optional quotes)
    pattern = r'^(name:\s+)(["\']?)([^"\'\n]+)\2$'

    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return False, "", ""

    old_name = match.group(3)
    new_name = convert_to_display_name(old_name)

    # Skip if no change needed
    if old_name == new_name:
        return False, old_name, new_name

    # Replace the name field
    updated_content = re.sub(
        pattern, rf"\1{new_name}", content, count=1, flags=re.MULTILINE
    )

    # Write back to file
    file_path.write_text(updated_content)

    return True, old_name, new_name


def main():
    """Update all agent markdown files in the cache directory."""
    # Agent cache directory
    cache_dir = (
        Path.home()
        / ".claude-mpm"
        / "cache"
        / "remote-agents"
        / "bobmatnyc"
        / "claude-mpm-agents"
        / "agents"
    )

    if not cache_dir.exists():
        print(f"Error: Cache directory not found: {cache_dir}")
        return

    # Find all markdown files (exclude BASE-AGENT.md backup files)
    md_files = [
        f
        for f in cache_dir.rglob("*.md")
        if not f.name.endswith(".backup") and not f.name.endswith(".migrated")
    ]

    print(f"Found {len(md_files)} agent files to process")
    print("-" * 80)

    # Track results
    updated_files: list[tuple[Path, str, str]] = []
    skipped_files: list[Path] = []

    # Process each file
    for file_path in sorted(md_files):
        success, old_name, new_name = update_agent_file(file_path)

        if success:
            updated_files.append((file_path, old_name, new_name))
            relative_path = file_path.relative_to(cache_dir)
            print(f"✓ {relative_path}")
            print(f"  {old_name} → {new_name}")
        else:
            skipped_files.append(file_path)

    # Summary
    print("-" * 80)
    print("\nSummary:")
    print(f"  Updated: {len(updated_files)} files")
    print(f"  Skipped: {len(skipped_files)} files (no change needed)")

    if updated_files:
        print("\nUpdated files:")
        for file_path, old_name, new_name in updated_files:
            relative_path = file_path.relative_to(cache_dir)
            print(f"  - {relative_path}: '{old_name}' → '{new_name}'")


if __name__ == "__main__":
    main()
