#!/usr/bin/env python3
"""
Apply deprecation policy by cleaning up obsolete files and code.

This script implements the formal deprecation policy by:
1. Identifying obsolete files according to the policy
2. Creating deprecation warnings for experimental code
3. Removing files that are past their deprecation timeline
4. Updating documentation and references

Usage:
    python scripts/apply_deprecation_policy.py [--dry-run] [--phase PHASE]
"""

import argparse
import os
import shutil
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class DeprecationPolicyApplier:
    """Applies the formal deprecation policy to the codebase."""

    def __init__(self, root_path: Path, dry_run: bool = False):
        self.root_path = root_path
        self.dry_run = dry_run
        self.removed_files: List[Path] = []
        self.updated_files: List[Path] = []
        self.warnings_added: List[Path] = []

        # Define obsolete files according to deprecation policy
        self.immediate_removal = {
            # One-time cleanup scripts (no longer needed)
            "cleanup_obsolete_files.py",
            "remove_obsolete_files.sh",
            "remove_duplicate_files.py",
            "post_refactor_cleanup.py",
            # Empty or minimal test files
            "test_research_agent.py",  # Root level temporary file
        }

        # Experimental code scheduled for deprecation
        self.experimental_deprecation = {
            "src/claude_mpm/experimental/cli_enhancements.py",
        }

        # Legacy modules scheduled for deprecation
        self.legacy_deprecation = {
            "src/claude_mpm/cli_module/",
        }

        # Backup and temporary files
        self.backup_patterns = {
            "*.bak",
            "*.orig",
            "*~",
            "*.tmp",
            "*_backup.py",
            "*_original.py",
        }

    def identify_obsolete_files(self) -> Dict[str, List[Path]]:
        """Identify files that should be removed according to policy."""
        obsolete = {"immediate": [], "experimental": [], "legacy": [], "backup": []}

        # Immediate removal files
        for filename in self.immediate_removal:
            file_path = self.root_path / filename
            if file_path.exists():
                obsolete["immediate"].append(file_path)

        # Experimental files
        for filepath in self.experimental_deprecation:
            file_path = self.root_path / filepath
            if file_path.exists():
                obsolete["experimental"].append(file_path)

        # Legacy directories/files
        for filepath in self.legacy_deprecation:
            file_path = self.root_path / filepath
            if file_path.exists():
                obsolete["legacy"].append(file_path)

        # Backup files
        for pattern in self.backup_patterns:
            for file_path in self.root_path.rglob(pattern):
                if file_path.is_file():
                    obsolete["backup"].append(file_path)

        return obsolete

    def add_deprecation_warnings(self, files: List[Path]) -> None:
        """Add deprecation warnings to experimental files."""
        for file_path in files:
            if not file_path.suffix == ".py":
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check if deprecation warning already exists
                if "DeprecationWarning" in content:
                    continue

                # Add deprecation warning at the top of the file
                lines = content.split("\n")

                # Find the first non-comment, non-import line
                insert_index = 0
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if (
                        stripped
                        and not stripped.startswith("#")
                        and not stripped.startswith('"""')
                        and not stripped.startswith("'''")
                        and not stripped.startswith("from ")
                        and not stripped.startswith("import ")
                    ):
                        insert_index = i
                        break

                # Create deprecation warning
                warning_code = [
                    "",
                    "# DEPRECATION WARNING",
                    "import warnings",
                    "warnings.warn(",
                    f'    "This module is deprecated and will be removed in a future version. "',
                    f'    "See docs/developer/DEPRECATION_POLICY.md for migration guidance.",',
                    "    DeprecationWarning,",
                    "    stacklevel=2",
                    ")",
                    "",
                ]

                # Insert warning
                lines[insert_index:insert_index] = warning_code

                if not self.dry_run:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines))

                self.warnings_added.append(file_path)
                print(f"✓ Added deprecation warning to {file_path}")

            except Exception as e:
                print(f"⚠️  Error adding warning to {file_path}: {e}")

    def remove_files(self, files: List[Path], category: str) -> None:
        """Remove obsolete files."""
        for file_path in files:
            try:
                if file_path.is_file():
                    if not self.dry_run:
                        file_path.unlink()
                    print(f"✓ Removed {category} file: {file_path}")
                elif file_path.is_dir():
                    if not self.dry_run:
                        shutil.rmtree(file_path)
                    print(f"✓ Removed {category} directory: {file_path}")

                self.removed_files.append(file_path)

            except Exception as e:
                print(f"⚠️  Error removing {file_path}: {e}")

    def update_gitignore(self) -> None:
        """Update .gitignore to prevent future accumulation of obsolete files."""
        gitignore_path = self.root_path / ".gitignore"

        # Additional patterns to ignore
        additional_patterns = [
            "",
            "# Obsolete file patterns (auto-added by deprecation policy)",
            "*.bak",
            "*.orig",
            "*~",
            "*_backup.py",
            "*_original.py",
            "cleanup_obsolete_files.py",
            "remove_obsolete_files.sh",
            "remove_duplicate_files.py",
        ]

        if gitignore_path.exists():
            with open(gitignore_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if patterns already exist
            needs_update = False
            for pattern in additional_patterns:
                if pattern and pattern not in content:
                    needs_update = True
                    break

            if needs_update and not self.dry_run:
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    f.write("\n".join(additional_patterns))

                self.updated_files.append(gitignore_path)
                print("✓ Updated .gitignore with obsolete file patterns")

    def generate_report(self, obsolete_files: Dict[str, List[Path]]) -> None:
        """Generate a report of actions taken."""
        print("\n" + "=" * 60)
        print("DEPRECATION POLICY APPLICATION REPORT")
        print("=" * 60)

        if self.dry_run:
            print("🔍 DRY RUN MODE - No files were actually modified")

        print(f"\nObsolete files identified:")
        for category, files in obsolete_files.items():
            if files:
                print(f"  {category.title()}: {len(files)} files")
                for file_path in files:
                    print(f"    - {file_path}")

        print(f"\nActions taken:")
        print(f"  Files removed: {len(self.removed_files)}")
        print(f"  Deprecation warnings added: {len(self.warnings_added)}")
        print(f"  Files updated: {len(self.updated_files)}")

        if self.warnings_added:
            print(f"\nDeprecation warnings added to:")
            for file_path in self.warnings_added:
                print(f"  - {file_path}")

        print(f"\nNext steps:")
        print(f"  1. Review changes before committing")
        print(f"  2. Update documentation if needed")
        print(f"  3. Run tests to ensure nothing is broken")
        print(f"  4. Consider updating import statements")

        print(f"\nFor more information, see:")
        print(f"  docs/developer/DEPRECATION_POLICY.md")

    def apply_policy(self, phase: str = "all") -> None:
        """Apply the deprecation policy."""
        print("🧹 Applying deprecation policy...")

        obsolete_files = self.identify_obsolete_files()

        if phase in ["all", "immediate"]:
            # Remove immediate files
            self.remove_files(obsolete_files["immediate"], "immediate")
            self.remove_files(obsolete_files["backup"], "backup")

        if phase in ["all", "experimental"]:
            # Add warnings to experimental files
            self.add_deprecation_warnings(obsolete_files["experimental"])

        if phase in ["all", "legacy"]:
            # Add warnings to legacy files (but don't remove yet)
            legacy_files = []
            for dir_path in obsolete_files["legacy"]:
                if dir_path.is_dir():
                    legacy_files.extend(dir_path.rglob("*.py"))
            self.add_deprecation_warnings(legacy_files)

        # Update .gitignore
        self.update_gitignore()

        # Generate report
        self.generate_report(obsolete_files)


def main():
    parser = argparse.ArgumentParser(description="Apply deprecation policy")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--phase",
        choices=["all", "immediate", "experimental", "legacy"],
        default="all",
        help="Which deprecation phase to apply",
    )

    args = parser.parse_args()

    # Get project root
    root_path = Path(__file__).parent.parent

    # Apply deprecation policy
    applier = DeprecationPolicyApplier(root_path, dry_run=args.dry_run)
    applier.apply_policy(phase=args.phase)


if __name__ == "__main__":
    main()
