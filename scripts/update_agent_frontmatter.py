#!/usr/bin/env python3
"""
Update agent frontmatter with skills field.

This script reads the inverted agent → skills mapping and updates each agent's
frontmatter to include the skills they should have.
"""

import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def load_agent_mappings(yaml_path: Path) -> Dict[str, List[str]]:
    """Load the inverted agent → skills mapping."""
    with open(yaml_path) as f:
        return yaml.safe_load(f)

def extract_frontmatter(content: str) -> Tuple[Optional[Dict], str]:
    """Extract frontmatter and body from markdown content.

    Returns:
        Tuple of (frontmatter_dict, body_content)
    """
    # Match YAML frontmatter between --- delimiters
    pattern = r'^---\n(.*?)\n---\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        return None, content

    frontmatter_str = match.group(1)
    body = match.group(2)

    try:
        frontmatter = yaml.safe_load(frontmatter_str)
        return frontmatter, body
    except yaml.YAMLError as e:
        print(f"Error parsing frontmatter: {e}")
        return None, content

def reconstruct_markdown(frontmatter: Dict, body: str) -> str:
    """Reconstruct markdown file from frontmatter and body.

    Args:
        frontmatter: Dictionary of frontmatter fields
        body: Markdown body content

    Returns:
        Complete markdown content with frontmatter
    """
    # Convert frontmatter to YAML string with proper formatting
    yaml_str = yaml.dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=False,  # Preserve order
        allow_unicode=True,
        width=1000  # Prevent line wrapping
    )

    # Remove trailing newline from YAML (we'll add it back)
    yaml_str = yaml_str.rstrip('\n')

    return f"---\n{yaml_str}\n---\n{body}"

def update_agent_file(
    agent_path: Path,
    skills: List[str],
    dry_run: bool = False
) -> bool:
    """Update agent file with skills frontmatter.

    Args:
        agent_path: Path to agent markdown file
        skills: List of skill names to add
        dry_run: If True, print changes without writing

    Returns:
        True if file was updated, False otherwise
    """
    # Read current content
    content = agent_path.read_text()

    # Extract frontmatter
    frontmatter, body = extract_frontmatter(content)

    if frontmatter is None:
        print(f"⚠️  Skipping {agent_path.name}: No frontmatter found")
        return False

    # Check if skills already exist
    if 'skills' in frontmatter:
        existing_skills = frontmatter.get('skills', [])
        if existing_skills == skills:
            print(f"✓ {agent_path.name}: Skills already up-to-date ({len(skills)} skills)")
            return False

    # Add/update skills field
    frontmatter['skills'] = skills

    # Reconstruct markdown
    new_content = reconstruct_markdown(frontmatter, body)

    if dry_run:
        print(f"\n{'='*80}")
        print(f"DRY RUN: {agent_path.name}")
        print(f"{'='*80}")
        print(f"Would add {len(skills)} skills:")
        for skill in skills[:5]:
            print(f"  - {skill}")
        if len(skills) > 5:
            print(f"  ... and {len(skills) - 5} more")
        return True

    # Write updated content
    agent_path.write_text(new_content)
    print(f"✓ Updated {agent_path.name}: Added {len(skills)} skills")
    return True

def find_agent_files(agents_dir: Path) -> List[Path]:
    """Find all agent markdown files.

    Args:
        agents_dir: Root directory containing agent files

    Returns:
        List of paths to agent markdown files
    """
    # Recursively find all .md files, excluding BASE-AGENT.md and README.md
    agent_files = []
    for md_file in agents_dir.rglob("*.md"):
        if md_file.name not in ["BASE-AGENT.md", "README.md"]:
            agent_files.append(md_file)
    return sorted(agent_files)

def normalize_agent_id(agent_id: str) -> str:
    """Normalize agent_id to match mapping format.

    Handles various formats:
    - golang_engineer -> golang-engineer
    - javascript-engineer-agent -> javascript-engineer
    - api-qa-agent -> api-qa
    - documentation-agent -> documentation

    Args:
        agent_id: Raw agent_id from frontmatter

    Returns:
        Normalized agent_id for mapping lookup
    """
    # Replace underscores with hyphens
    normalized = agent_id.replace('_', '-')

    # Remove -agent suffix if present
    if normalized.endswith('-agent'):
        normalized = normalized[:-6]  # Remove '-agent'

    return normalized

def extract_agent_id(frontmatter: Dict) -> Optional[str]:
    """Extract agent_id from frontmatter.

    Args:
        frontmatter: Dictionary of frontmatter fields

    Returns:
        agent_id string or None (normalized for mapping lookup)
    """
    agent_id = frontmatter.get('agent_id')
    if agent_id:
        return normalize_agent_id(agent_id)
    return None

def main():
    """Main execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Update agent frontmatter with skills")
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would be changed without writing files"
    )
    parser.add_argument(
        '--agents-dir',
        type=Path,
        default=Path.home() / '.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents',
        help="Path to agents directory"
    )
    parser.add_argument(
        '--mapping',
        type=Path,
        default=Path(__file__).parent.parent / 'agent_skill_mappings.yaml',
        help="Path to agent skill mappings YAML"
    )

    args = parser.parse_args()

    # Load mappings
    print(f"Loading mappings from: {args.mapping}")
    agent_skills = load_agent_mappings(args.mapping)
    print(f"Loaded mappings for {len(agent_skills)} agents\n")

    # Find agent files
    print(f"Searching for agent files in: {args.agents_dir}")
    agent_files = find_agent_files(args.agents_dir)
    print(f"Found {len(agent_files)} agent files\n")

    if args.dry_run:
        print("=" * 80)
        print("DRY RUN MODE - No files will be modified")
        print("=" * 80)
        print()

    # Update each file
    updated_count = 0
    skipped_count = 0
    not_mapped_count = 0

    for agent_path in agent_files:
        # Read frontmatter to get agent_id
        content = agent_path.read_text()
        frontmatter, _ = extract_frontmatter(content)

        if frontmatter is None:
            skipped_count += 1
            continue

        agent_id = extract_agent_id(frontmatter)
        if agent_id is None:
            print(f"⚠️  Skipping {agent_path.name}: No agent_id in frontmatter")
            skipped_count += 1
            continue

        # Get skills for this agent
        skills = agent_skills.get(agent_id, [])

        if not skills:
            print(f"ℹ️  {agent_path.name} (agent_id: {agent_id}): No skills mapped")
            not_mapped_count += 1
            # Still update with empty skills list
            skills = []

        # Update file
        if update_agent_file(agent_path, skills, dry_run=args.dry_run):
            updated_count += 1

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total agent files: {len(agent_files)}")
    print(f"Updated: {updated_count}")
    print(f"Skipped (no frontmatter): {skipped_count}")
    print(f"No skills mapped: {not_mapped_count}")

    if args.dry_run:
        print()
        print("This was a DRY RUN. Run without --dry-run to apply changes.")

if __name__ == '__main__':
    main()
