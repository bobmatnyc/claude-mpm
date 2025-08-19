#!/usr/bin/env python3
"""
Memory Deduplication Utility
============================

Command-line tool to deduplicate existing memory files using NLP similarity detection.
Can be run on individual agents or all agents at once.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager
from claude_mpm.services.agents.memory.content_manager import MemoryContentManager


def deduplicate_memory_file(memory_file: Path, dry_run: bool = False) -> Tuple[int, List[str]]:
    """Deduplicate a single memory file.
    
    Args:
        memory_file: Path to the memory file
        dry_run: If True, don't save changes
    
    Returns:
        Tuple of (items_removed, list of removed items)
    """
    if not memory_file.exists():
        print(f"  ✗ File not found: {memory_file}")
        return 0, []
    
    content = memory_file.read_text(encoding="utf-8")
    content_manager = MemoryContentManager({
        "max_items_per_section": 15,
        "max_line_length": 120
    })
    
    # Find all sections
    sections = []
    for line in content.split("\n"):
        if line.startswith("## ") and "Memory Usage" not in line:
            section_name = line[3:].strip()
            sections.append(section_name)
    
    total_removed = 0
    removed_items = []
    updated_content = content
    
    # Deduplicate each section
    for section in sections:
        deduped_content, removed_count = content_manager.deduplicate_section(
            updated_content, section
        )
        
        if removed_count > 0:
            # Track what was removed
            old_items = extract_section_items(updated_content, section)
            new_items = extract_section_items(deduped_content, section)
            for item in old_items:
                if item not in new_items:
                    removed_items.append(f"[{section}] {item}")
            
            updated_content = deduped_content
            total_removed += removed_count
    
    # Save if not dry run and changes were made
    if total_removed > 0 and not dry_run:
        memory_file.write_text(updated_content, encoding="utf-8")
    
    return total_removed, removed_items


def extract_section_items(content: str, section: str) -> List[str]:
    """Extract items from a specific section."""
    items = []
    in_section = False
    
    for line in content.split("\n"):
        if line.startswith(f"## {section}"):
            in_section = True
        elif line.startswith("## ") and in_section:
            break
        elif in_section and line.strip().startswith("- "):
            items.append(line.strip()[2:])
    
    return items


def main():
    """Main entry point for the deduplication utility."""
    parser = argparse.ArgumentParser(
        description="Deduplicate agent memory files using NLP similarity detection"
    )
    parser.add_argument(
        "agent",
        nargs="?",
        default="all",
        help="Agent ID to deduplicate (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without making changes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed information about removed items"
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory)"
    )
    parser.add_argument(
        "--user-memories",
        action="store_true",
        help="Deduplicate user-level memories instead of project memories"
    )
    
    args = parser.parse_args()
    
    # Determine memories directory
    if args.user_memories:
        memories_dir = Path.home() / ".claude-mpm" / "memories"
        print(f"Deduplicating user memories in: {memories_dir}")
    else:
        memories_dir = args.project_dir / ".claude-mpm" / "memories"
        print(f"Deduplicating project memories in: {memories_dir}")
    
    if not memories_dir.exists():
        print(f"✗ Memories directory not found: {memories_dir}")
        return 1
    
    # Find memory files to process
    if args.agent == "all":
        memory_files = list(memories_dir.glob("*_memories.md"))
    else:
        memory_files = [memories_dir / f"{args.agent}_memories.md"]
    
    if not memory_files:
        print("✗ No memory files found")
        return 1
    
    print(f"\n{'DRY RUN - ' if args.dry_run else ''}Processing {len(memory_files)} memory file(s)...")
    print("-" * 60)
    
    total_removed_all = 0
    all_removed_items = []
    
    for memory_file in memory_files:
        if not memory_file.exists():
            continue
            
        agent_id = memory_file.stem.replace("_memories", "")
        print(f"\n{agent_id}:")
        
        removed_count, removed_items = deduplicate_memory_file(
            memory_file, dry_run=args.dry_run
        )
        
        if removed_count > 0:
            print(f"  ✓ Removed {removed_count} duplicate item(s)")
            if args.verbose and removed_items:
                print("  Removed items:")
                for item in removed_items:
                    print(f"    - {item[:80]}{'...' if len(item) > 80 else ''}")
        else:
            print(f"  ✓ No duplicates found")
        
        total_removed_all += removed_count
        all_removed_items.extend(removed_items)
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total files processed: {len(memory_files)}")
    print(f"  Total duplicates removed: {total_removed_all}")
    
    if args.dry_run:
        print("\n⚠️  This was a dry run. No files were modified.")
        print("    Run without --dry-run to apply changes.")
    elif total_removed_all > 0:
        print("\n✓ Memory files have been deduplicated successfully!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())