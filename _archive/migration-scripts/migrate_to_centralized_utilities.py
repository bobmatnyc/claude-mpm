#!/usr/bin/env python3
"""
Migration script to update codebase to use centralized utilities.

This script:
1. Replaces duplicate logger initialization with centralized version
2. Replaces duplicate utility functions with common.py versions
3. Creates a backup before making changes
4. Generates a migration report
"""

import ast
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class CodeMigrator:
    """Handles code migration to centralized utilities."""

    def __init__(self, dry_run: bool = True):
        """Initialize migrator.

        Args:
            dry_run: If True, don't actually modify files
        """
        self.dry_run = dry_run
        self.project_root = PROJECT_ROOT
        self.src_dir = self.project_root / "src" / "claude_mpm"
        self.backup_dir = (
            self.project_root / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.changes: Dict[Path, List[str]] = {}
        self.stats = {
            "files_analyzed": 0,
            "files_modified": 0,
            "loggers_migrated": 0,
            "utils_migrated": 0,
            "lines_removed": 0,
        }

    def create_backup(self) -> None:
        """Create backup of source directory."""
        if not self.dry_run and not self.backup_dir.exists():
            print(f"Creating backup at {self.backup_dir}")
            shutil.copytree(self.src_dir, self.backup_dir)

    def migrate_logger_pattern(self, file_path: Path) -> Tuple[str, int]:
        """Migrate old logger pattern to new centralized one.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (modified content, number of changes)
        """
        content = file_path.read_text()
        original_content = content
        changes = 0

        # Pattern 1: import logging + logger = logging.getLogger
        pattern1 = re.compile(
            r"^import logging\s*\n(.*?\n)?logger = logging\.getLogger\(__name__\)",
            re.MULTILINE,
        )

        replacement1 = "from claude_mpm.core.logging_utils import get_logger\nlogger = get_logger(__name__)"

        if pattern1.search(content):
            content = pattern1.sub(replacement1, content)
            changes += 1

        # Pattern 2: from logging import getLogger
        pattern2 = re.compile(
            r"^from logging import .*?getLogger.*?\n.*?logger = getLogger\(__name__\)",
            re.MULTILINE,
        )

        if pattern2.search(content):
            content = pattern2.sub(replacement1, content)
            changes += 1

        # Pattern 3: Just logging.getLogger without import at top
        if "logging.getLogger" in content and "import logging" in content:
            # Check if we haven't already replaced it
            if "from claude_mpm.core.logging_utils import get_logger" not in content:
                # Add import at top after other imports
                import_added = False
                lines = content.split("\n")
                new_lines = []

                for i, line in enumerate(lines):
                    new_lines.append(line)
                    # Add after first import block
                    if (
                        not import_added
                        and line.startswith("import ")
                        and i + 1 < len(lines)
                        and not lines[i + 1].startswith("import ")
                    ):
                        new_lines.append(
                            "from claude_mpm.core.logging_utils import get_logger"
                        )
                        import_added = True

                content = "\n".join(new_lines)

                # Replace logging.getLogger with get_logger
                content = re.sub(r"logging\.getLogger\(", "get_logger(", content)
                changes += 1

        # Remove now-unused logging import if no other logging usage
        if "from claude_mpm.core.logging_utils import get_logger" in content:
            # Check if logging is still used for other purposes
            if not re.search(
                r"logging\.(debug|info|warning|error|critical|DEBUG|INFO|WARNING|ERROR|CRITICAL)",
                content,
            ):
                content = re.sub(
                    r"^import logging\s*\n", "", content, flags=re.MULTILINE
                )
                changes += 1

        return content, changes

    def migrate_utility_patterns(self, file_path: Path) -> Tuple[str, int]:
        """Migrate duplicate utility patterns to common.py versions.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (modified content, number of changes)
        """
        content = file_path.read_text()
        changes = 0

        # Skip if it's the common.py file itself
        if file_path.name == "common.py":
            return content, changes

        replacements = []

        # Pattern: JSON loading with try/except
        json_pattern = re.compile(
            r"try:\s*\n\s*with open\((.*?)\) as f:\s*\n\s*.*?json\.load\(f\).*?\n.*?except.*?:.*?\n.*?(?:return )?\{\}",
            re.DOTALL,
        )

        if json_pattern.search(content):
            replacements.append(("json_loading", "load_json_safe"))
            changes += 1

        # Pattern: Path existence check with creation
        path_pattern = re.compile(
            r"if not .*?\.exists\(\):\s*\n\s*.*?\.mkdir\(parents=True, exist_ok=True\)",
            re.DOTALL,
        )

        if path_pattern.search(content):
            replacements.append(("path_exists", "ensure_path_exists"))
            changes += 1

        # Pattern: subprocess.run with common options
        subprocess_pattern = re.compile(
            r"subprocess\.run\([^,]+,\s*capture_output=True,\s*text=True[^)]*\)",
            re.DOTALL,
        )

        if subprocess_pattern.search(content):
            replacements.append(("subprocess", "run_command_safe"))
            changes += 1

        # Add imports if we have replacements
        if replacements:
            import_line = "from claude_mpm.utils.common import "
            import_line += ", ".join([repl[1] for repl in replacements])

            # Add import after other imports
            lines = content.split("\n")
            import_added = False
            new_lines = []

            for i, line in enumerate(lines):
                new_lines.append(line)
                if (
                    not import_added
                    and line.startswith("import ")
                    and i + 1 < len(lines)
                    and not lines[i + 1].startswith("import ")
                ):
                    new_lines.append(import_line)
                    import_added = True

            content = "\n".join(new_lines)

        return content, changes

    def analyze_file(self, file_path: Path) -> None:
        """Analyze and potentially migrate a single Python file.

        Args:
            file_path: Path to Python file
        """
        self.stats["files_analyzed"] += 1

        # Skip test files and migration script itself
        if (
            "test" in file_path.name
            or file_path.name == "migrate_to_centralized_utilities.py"
        ):
            return

        try:
            original_content = file_path.read_text()
            content = original_content
            total_changes = 0
            file_changes = []

            # Migrate logger pattern
            content, logger_changes = self.migrate_logger_pattern(file_path)
            if logger_changes > 0:
                self.stats["loggers_migrated"] += logger_changes
                total_changes += logger_changes
                file_changes.append(f"Migrated {logger_changes} logger pattern(s)")

            # Migrate utility patterns
            content, util_changes = self.migrate_utility_patterns(file_path)
            if util_changes > 0:
                self.stats["utils_migrated"] += util_changes
                total_changes += util_changes
                file_changes.append(f"Migrated {util_changes} utility pattern(s)")

            # Apply changes if any
            if total_changes > 0:
                self.stats["files_modified"] += 1
                self.changes[file_path] = file_changes

                # Calculate lines removed (approximate)
                original_lines = len(original_content.splitlines())
                new_lines = len(content.splitlines())
                self.stats["lines_removed"] += max(0, original_lines - new_lines)

                if not self.dry_run:
                    file_path.write_text(content)
                    print(f"✓ Modified {file_path.relative_to(self.project_root)}")
                else:
                    print(f"→ Would modify {file_path.relative_to(self.project_root)}")
                    for change in file_changes:
                        print(f"  - {change}")

        except Exception as e:
            print(f"✗ Error processing {file_path}: {e}")

    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project.

        Returns:
            List of Python file paths
        """
        python_files = []
        for file_path in self.src_dir.rglob("*.py"):
            python_files.append(file_path)
        return python_files

    def generate_report(self) -> None:
        """Generate migration report."""
        report = [
            "\n" + "=" * 60,
            "MIGRATION REPORT",
            "=" * 60,
            f"Mode: {'DRY RUN' if self.dry_run else 'APPLIED'}",
            f"Files analyzed: {self.stats['files_analyzed']}",
            f"Files modified: {self.stats['files_modified']}",
            f"Loggers migrated: {self.stats['loggers_migrated']}",
            f"Utilities migrated: {self.stats['utils_migrated']}",
            f"Estimated lines removed: {self.stats['lines_removed']}",
            "",
        ]

        if self.changes:
            report.append("Files changed:")
            for file_path, changes in sorted(self.changes.items()):
                report.append(f"\n{file_path.relative_to(self.project_root)}:")
                for change in changes:
                    report.append(f"  - {change}")

        if not self.dry_run and self.backup_dir.exists():
            report.append(f"\nBackup created at: {self.backup_dir}")

        print("\n".join(report))

        # Save report to file
        report_path = (
            self.project_root
            / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        report_path.write_text("\n".join(report))
        print(f"\nReport saved to: {report_path}")

    def run(self) -> None:
        """Run the migration process."""
        print("Starting migration to centralized utilities...")
        print(f"Project root: {self.project_root}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'APPLYING CHANGES'}")
        print("-" * 60)

        # Create backup if not dry run
        if not self.dry_run:
            self.create_backup()

        # Find and process Python files
        python_files = self.find_python_files()
        print(f"Found {len(python_files)} Python files to analyze")
        print("-" * 60)

        for file_path in python_files:
            self.analyze_file(file_path)

        # Generate report
        self.generate_report()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate codebase to use centralized utilities"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry run)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Custom backup directory",
    )

    args = parser.parse_args()

    migrator = CodeMigrator(dry_run=not args.apply)
    if args.backup_dir:
        migrator.backup_dir = args.backup_dir

    migrator.run()


if __name__ == "__main__":
    main()
