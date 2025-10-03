#!/usr/bin/env python3
"""Script to update agent tag format from YAML list to comma-separated string."""

import re
from pathlib import Path
from typing import List


def extract_yaml_list_tags(content: str) -> tuple[List[str], str]:
    """Extract YAML list format tags and return tags list and remaining content."""
    lines = content.split("\n")
    tags = []
    in_tags_section = False
    in_frontmatter = False

    for _i, line in enumerate(lines):
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            break

        if in_frontmatter and line.startswith("tags:"):
            in_tags_section = True
            continue
        if in_tags_section and line.startswith("  - "):
            # Extract tag from YAML list format
            tag = line.strip()[2:].strip()
            tags.append(tag)
        elif in_tags_section and not line.startswith("  "):
            # End of tags section
            in_tags_section = False

    return tags, content


def update_agent_tags_format(file_path: Path) -> bool:
    """Update agent file to use comma-separated tag format."""
    try:
        content = file_path.read_text(encoding="utf-8")

        # Check if file has YAML list format tags
        if "tags:\n  -" not in content:
            print(f"  No YAML list tags found in {file_path.name}")
            return False

        # Extract tags and content
        tags, original_content = extract_yaml_list_tags(content)

        if not tags:
            print(f"  No tags extracted from {file_path.name}")
            return False

        # Convert YAML list format to comma-separated format
        # Match the pattern: "tags:\n  - tag1\n  - tag2\n..."
        yaml_list_pattern = r"^tags:\n(?:  - [^\n]+\n)+"
        tags_str = ",".join(tags)
        replacement = f"tags: {tags_str}\n"

        updated_content = re.sub(
            yaml_list_pattern, replacement, content, flags=re.MULTILINE
        )

        if updated_content != content:
            file_path.write_text(updated_content, encoding="utf-8")
            print(f"  ✅ Updated {file_path.name}: {', '.join(tags)}")
            return True
        print(f"  No changes needed for {file_path.name}")
        return False

    except Exception as e:
        print(f"  ❌ Error updating {file_path.name}: {e}")
        return False


def main():
    """Update all deployed agent files to use comma-separated tag format."""
    project_root = Path(__file__).parent.parent
    agent_dirs = [
        project_root / ".claude" / "agents",
        project_root / "agents" / "templates",  # If any exist here
    ]

    total_files = 0
    updated_files = 0

    for agent_dir in agent_dirs:
        if not agent_dir.exists():
            continue

        print(f"\nScanning {agent_dir}...")

        for agent_file in agent_dir.glob("*.md"):
            total_files += 1
            print(f"\nProcessing {agent_file.name}...")
            if update_agent_tags_format(agent_file):
                updated_files += 1

    print(f"\n{'='*50}")
    print("Tag format update complete!")
    print(f"Files processed: {total_files}")
    print(f"Files updated: {updated_files}")
    print(f"Files unchanged: {total_files - updated_files}")


if __name__ == "__main__":
    main()
