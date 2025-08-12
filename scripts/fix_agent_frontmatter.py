#!/usr/bin/env python3
"""
Script to automatically fix frontmatter issues in agent files.

This script applies the frontmatter validator's corrections to agent files,
updating them in place with corrected frontmatter.
"""

import sys
import logging
import argparse
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.agents.frontmatter_validator import FrontmatterValidator


def main():
    """Main function to fix agent frontmatter."""
    parser = argparse.ArgumentParser(description="Fix frontmatter in agent files")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes"
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path.cwd() / ".claude" / "agents",
        help="Directory containing agent files (default: .claude/agents)"
    )
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    # Create validator
    validator = FrontmatterValidator()
    
    # Check directory exists
    if not args.directory.exists():
        print(f"Error: Directory not found: {args.directory}")
        return 1
    
    print(f"\n{'DRY RUN - ' if args.dry_run else ''}Fixing agent files in: {args.directory}")
    print("=" * 60)
    
    # Statistics
    stats = {
        'total': 0,
        'fixed': 0,
        'already_valid': 0,
        'errors': 0
    }
    
    # Process each .md file
    for md_file in sorted(args.directory.glob("*.md")):
        stats['total'] += 1
        print(f"\n📄 {md_file.name}")
        
        # Validate and correct the file
        result = validator.correct_file(md_file, dry_run=args.dry_run)
        
        if result.is_valid and not result.corrections:
            print("  ✅ Already valid - no changes needed")
            stats['already_valid'] += 1
        elif result.corrections:
            if args.dry_run:
                print("  ⚠️  Would fix:")
            else:
                print("  ✅ Fixed:")
            stats['fixed'] += 1
            
            for correction in result.corrections:
                print(f"    - {correction}")
        
        if result.errors:
            print("  ❌ Errors that cannot be auto-fixed:")
            stats['errors'] += 1
            for error in result.errors:
                print(f"    - {error}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files processed: {stats['total']}")
    print(f"✅ Already valid: {stats['already_valid']}")
    if args.dry_run:
        print(f"⚠️  Would fix: {stats['fixed']}")
    else:
        print(f"✅ Fixed: {stats['fixed']}")
    print(f"❌ With unfixable errors: {stats['errors']}")
    
    if not args.dry_run and stats['fixed'] > 0:
        print("\n✨ Frontmatter has been fixed in the agent files!")
        print("The agent loader will now use the corrected values.")
    elif args.dry_run and stats['fixed'] > 0:
        print("\n💡 Run without --dry-run to apply these fixes.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())