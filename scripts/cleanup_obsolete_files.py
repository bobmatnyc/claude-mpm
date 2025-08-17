#!/usr/bin/env python3
"""
Script to identify and optionally remove obsolete files from the codebase.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set


class ObsoleteFilesCleaner:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.obsolete_files = []
        self.backup_files = []
        self.empty_files = []
        self.large_test_files = []

    def find_obsolete_ticketing_files(self):
        """Find obsolete ticketing-related files."""
        ticketing_patterns = [
            "**/ticketing_service_original.*",
            "**/ticket_manager_di.*",
            "**/*ticketing_service*",
            "**/api/*ticket_manager_di*",
            "**/api/*ticketing_service_original*",
        ]

        obsolete_ticketing = []
        for pattern in ticketing_patterns:
            for file_path in self.root_path.rglob(pattern):
                if file_path.is_file():
                    obsolete_ticketing.append(file_path)

        return obsolete_ticketing

    def find_backup_files(self):
        """Find backup files that can be removed."""
        backup_patterns = [
            "**/*.bak",
            "**/*_original.py",
            "**/*_backup.py",
            "**/*.orig",
            "**/*~",
        ]

        backup_files = []
        for pattern in backup_patterns:
            for file_path in self.root_path.rglob(pattern):
                if file_path.is_file():
                    backup_files.append(file_path)

        return backup_files

    def find_empty_files(self):
        """Find empty or nearly empty files."""
        empty_files = []

        for file_path in self.root_path.rglob("*.py"):
            if file_path.is_file():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()

                    # Consider file empty if it has only imports, comments, or docstrings
                    lines = [
                        line.strip() for line in content.split("\n") if line.strip()
                    ]
                    non_trivial_lines = []

                    for line in lines:
                        if (
                            not line.startswith("#")
                            and not line.startswith('"""')
                            and not line.startswith("'''")
                            and not line.startswith("import ")
                            and not line.startswith("from ")
                            and line not in ["pass", "...", "None"]
                        ):
                            non_trivial_lines.append(line)

                    if len(non_trivial_lines) <= 2:  # Very minimal content
                        empty_files.append(
                            {
                                "file": file_path,
                                "lines": len(lines),
                                "non_trivial": len(non_trivial_lines),
                            }
                        )

                except Exception:
                    continue

        return empty_files

    def find_large_test_files(self):
        """Find unusually large test files."""
        large_tests = []

        for file_path in self.root_path.rglob("*test*.py"):
            if file_path.is_file():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = len(f.readlines())

                    if lines > 500:  # Large test file
                        large_tests.append({"file": file_path, "lines": lines})

                except Exception:
                    continue

        return large_tests

    def find_duplicate_files(self):
        """Find potential duplicate files by size and name patterns."""
        file_sizes = {}
        potential_duplicates = []

        for file_path in self.root_path.rglob("*.py"):
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    if size in file_sizes:
                        file_sizes[size].append(file_path)
                    else:
                        file_sizes[size] = [file_path]
                except Exception:
                    continue

        # Find files with same size (potential duplicates)
        for size, files in file_sizes.items():
            if len(files) > 1 and size > 1000:  # Only consider files > 1KB
                potential_duplicates.append({"size": size, "files": files})

        return potential_duplicates

    def analyze(self):
        """Run complete analysis."""
        print("Analyzing codebase for obsolete files...")

        results = {
            "obsolete_ticketing": self.find_obsolete_ticketing_files(),
            "backup_files": self.find_backup_files(),
            "empty_files": self.find_empty_files(),
            "large_test_files": self.find_large_test_files(),
            "potential_duplicates": self.find_duplicate_files(),
        }

        return results

    def generate_report(self, results):
        """Generate a detailed report."""
        print("\n" + "=" * 80)
        print("OBSOLETE FILES ANALYSIS REPORT")
        print("=" * 80)

        print(f"\nOBSOLETE TICKETING FILES ({len(results['obsolete_ticketing'])}):")
        for file_path in results["obsolete_ticketing"]:
            rel_path = file_path.relative_to(self.root_path)
            print(f"  {rel_path}")

        print(f"\nBACKUP FILES ({len(results['backup_files'])}):")
        for file_path in results["backup_files"]:
            rel_path = file_path.relative_to(self.root_path)
            print(f"  {rel_path}")

        print(f"\nEMPTY/MINIMAL FILES ({len(results['empty_files'])}):")
        for item in results["empty_files"][:20]:  # Show first 20
            rel_path = item["file"].relative_to(self.root_path)
            print(
                f"  {rel_path}: {item['lines']} lines, {item['non_trivial']} non-trivial"
            )

        print(f"\nLARGE TEST FILES ({len(results['large_test_files'])}):")
        for item in sorted(
            results["large_test_files"], key=lambda x: x["lines"], reverse=True
        ):
            rel_path = item["file"].relative_to(self.root_path)
            print(f"  {rel_path}: {item['lines']} lines")

        print(f"\nPOTENTIAL DUPLICATES ({len(results['potential_duplicates'])}):")
        for item in sorted(
            results["potential_duplicates"], key=lambda x: x["size"], reverse=True
        )[:10]:
            print(f"  Size {item['size']} bytes:")
            for file_path in item["files"]:
                rel_path = file_path.relative_to(self.root_path)
                print(f"    {rel_path}")

    def create_removal_script(self, results, output_file="remove_obsolete_files.sh"):
        """Create a shell script to remove identified obsolete files."""
        script_content = ["#!/bin/bash", "# Script to remove obsolete files", ""]

        # Add obsolete ticketing files
        if results["obsolete_ticketing"]:
            script_content.append("# Remove obsolete ticketing files")
            for file_path in results["obsolete_ticketing"]:
                rel_path = file_path.relative_to(self.root_path)
                script_content.append(f'echo "Removing {rel_path}"')
                script_content.append(f'rm -f "{rel_path}"')
            script_content.append("")

        # Add backup files
        if results["backup_files"]:
            script_content.append("# Remove backup files")
            for file_path in results["backup_files"]:
                rel_path = file_path.relative_to(self.root_path)
                script_content.append(f'echo "Removing {rel_path}"')
                script_content.append(f'rm -f "{rel_path}"')
            script_content.append("")

        script_content.append('echo "Cleanup complete!"')

        with open(output_file, "w") as f:
            f.write("\n".join(script_content))

        # Make script executable
        os.chmod(output_file, 0o755)
        print(f"\nRemoval script created: {output_file}")
        print("Review the script before running it!")


def main():
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = "."

    cleaner = ObsoleteFilesCleaner(root_path)
    results = cleaner.analyze()
    cleaner.generate_report(results)
    cleaner.create_removal_script(results)


if __name__ == "__main__":
    main()
