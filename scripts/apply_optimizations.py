#!/usr/bin/env python3
"""
Apply Phase 1 optimizations to the codebase with safety checks.
This script applies logger and utility consolidations in a controlled manner.
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Set, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class OptimizationApplicator:
    """Applies codebase optimizations safely."""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.src_dir = self.project_root / "src" / "claude_mpm"
        self.stats = {
            "files_processed": 0,
            "files_modified": 0,
            "loggers_migrated": 0,
            "imports_cleaned": 0,
        }
        self.modified_files = []

    def apply_logger_optimization(self, file_path: Path) -> bool:
        """Apply logger optimization to a single file."""
        try:
            content = file_path.read_text()
            original_content = content
            modified = False

            # Skip if already using centralized logger
            if "from claude_mpm.core.logging_utils import get_logger" in content:
                return False

            # Skip if file doesn't use logging
            if "import logging" not in content and "from logging import" not in content:
                return False

            # Pattern 1: Basic logger pattern
            if "import logging" in content and "logging.getLogger" in content:
                # Add new import after existing imports
                lines = content.split("\n")
                new_lines = []
                import_added = False

                for i, line in enumerate(lines):
                    # Skip the old import logging line
                    if line.strip() == "import logging":
                        # Check if logging is used for other purposes
                        if re.search(
                            r"logging\.(DEBUG|INFO|WARNING|ERROR|CRITICAL|basicConfig)",
                            content,
                        ):
                            new_lines.append(line)  # Keep it
                        continue

                    # Replace logger = logging.getLogger(__name__)
                    if "logger = logging.getLogger(__name__)" in line:
                        if not import_added:
                            # Add import before this line
                            new_lines.append(
                                "from claude_mpm.core.logging_utils import get_logger"
                            )
                            import_added = True
                        new_lines.append("logger = get_logger(__name__)")
                        modified = True
                        self.stats["loggers_migrated"] += 1
                    else:
                        new_lines.append(line)

                if modified:
                    content = "\n".join(new_lines)

            # Pattern 2: getLogger import pattern
            elif "from logging import" in content and "getLogger" in content:
                # Replace the import and usage
                content = re.sub(
                    r"from logging import .*getLogger.*",
                    "from claude_mpm.core.logging_utils import get_logger",
                    content,
                )
                content = re.sub(
                    r"logger = getLogger\(__name__\)",
                    "logger = get_logger(__name__)",
                    content,
                )
                modified = True
                self.stats["loggers_migrated"] += 1

            # Save if modified
            if modified and content != original_content:
                file_path.write_text(content)
                self.stats["files_modified"] += 1
                self.modified_files.append(file_path)
                return True

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

        return False

    def clean_unused_imports(self, file_path: Path) -> bool:
        """Remove unused logging imports after migration."""
        try:
            content = file_path.read_text()

            # Skip if logging is still used for other purposes
            if re.search(
                r"logging\.(DEBUG|INFO|WARNING|ERROR|CRITICAL|basicConfig|StreamHandler)",
                content,
            ):
                return False

            # Remove standalone import logging if not used
            if "import logging\n" in content and "logging." not in content.replace(
                "import logging", ""
            ):
                content = content.replace("import logging\n", "")
                file_path.write_text(content)
                self.stats["imports_cleaned"] += 1
                return True

        except Exception as e:
            print(f"Error cleaning imports in {file_path}: {e}")

        return False

    def process_directory(self, directory: Path) -> None:
        """Process all Python files in a directory."""
        python_files = list(directory.rglob("*.py"))

        print(
            f"\nProcessing {len(python_files)} files in {directory.relative_to(self.project_root)}"
        )

        for file_path in python_files:
            # Skip test files and already processed files
            if "test" in file_path.name or "__pycache__" in str(file_path):
                continue

            self.stats["files_processed"] += 1

            # Apply logger optimization
            if self.apply_logger_optimization(file_path):
                print(f"  ✓ {file_path.relative_to(self.project_root)}")

                # Clean up imports if needed
                self.clean_unused_imports(file_path)

    def generate_report(self) -> None:
        """Generate optimization report."""
        print("\n" + "=" * 60)
        print("OPTIMIZATION REPORT")
        print("=" * 60)
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Files modified: {self.stats['files_modified']}")
        print(f"Loggers migrated: {self.stats['loggers_migrated']}")
        print(f"Imports cleaned: {self.stats['imports_cleaned']}")

        if self.modified_files:
            print(f"\nModified files ({len(self.modified_files)}):")
            for file_path in sorted(self.modified_files)[:10]:  # Show first 10
                print(f"  - {file_path.relative_to(self.project_root)}")
            if len(self.modified_files) > 10:
                print(f"  ... and {len(self.modified_files) - 10} more")

    def run(self, target_dirs: List[str] = None) -> None:
        """Run the optimization process."""
        print("Applying Phase 1 Optimizations")
        print("=" * 60)

        # Default to specific directories for safety
        if target_dirs is None:
            target_dirs = ["utils", "config", "validation", "hooks", "experimental"]

        for dir_name in target_dirs:
            dir_path = self.src_dir / dir_name
            if dir_path.exists():
                self.process_directory(dir_path)

        self.generate_report()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Apply Phase 1 optimizations to the codebase"
    )
    parser.add_argument(
        "--dirs",
        nargs="+",
        help="Specific directories to process (default: utils, config, validation, hooks, experimental)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all directories (use with caution)",
    )

    args = parser.parse_args()

    applicator = OptimizationApplicator()

    if args.all:
        # Process entire src directory
        applicator.process_directory(applicator.src_dir)
    else:
        # Process specific directories
        applicator.run(target_dirs=args.dirs)


if __name__ == "__main__":
    main()
