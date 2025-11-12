#!/usr/bin/env python3
"""
Fix migration issues where imports were incorrectly placed inside methods.
"""

import re
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def fix_misplaced_imports(file_path: Path) -> bool:
    """Fix imports that were mistakenly placed inside methods."""
    try:
        content = file_path.read_text()
        original_content = content

        # Pattern to find imports inside method/function definitions
        # This matches lines that start with "from claude_mpm" or "logger ="
        # that appear to be indented (have leading spaces)
        pattern = re.compile(
            r"^(\s+)(from claude_mpm\.core\.logging_utils import get_logger)\n(\s+)(logger = get_logger\(__name__\))",
            re.MULTILINE,
        )

        # Check if we have this pattern
        if pattern.search(content):
            # Extract the import and move it to module level
            # First, remove the misplaced imports
            content = pattern.sub("", content)

            # Now add them at the module level if not already there
            if "from claude_mpm.core.logging_utils import get_logger" not in content:
                # Find a good place to insert - after other imports
                lines = content.split("\n")
                insert_index = -1

                # Find the last import statement
                for i, line in enumerate(lines):
                    if line.startswith("from ") or line.startswith("import "):
                        insert_index = i + 1
                    elif (
                        insert_index > 0
                        and not line.strip().startswith("#")
                        and line.strip()
                    ):
                        # We've found the first non-comment, non-empty line after imports
                        break

                if insert_index > 0:
                    # Insert the logger import and initialization
                    lines.insert(insert_index, "")
                    lines.insert(
                        insert_index + 1,
                        "from claude_mpm.core.logging_utils import get_logger",
                    )
                    lines.insert(insert_index + 2, "")
                    lines.insert(insert_index + 3, "logger = get_logger(__name__)")
                    content = "\n".join(lines)

            # Save if changed
            if content != original_content:
                file_path.write_text(content)
                return True

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")

    return False


def main():
    """Main entry point."""
    src_dir = PROJECT_ROOT / "src" / "claude_mpm"

    # Find files that might have issues
    problem_files = [
        src_dir / "services" / "core" / "path_resolver.py",
        src_dir / "services" / "agents" / "memory" / "memory_categorization_service.py",
    ]

    # Also check all recently modified files
    for file_path in src_dir.rglob("*.py"):
        content = file_path.read_text()
        # Check for indented logger imports (sign of misplacement)
        if re.search(
            r"^\s+from claude_mpm\.core\.logging_utils import get_logger",
            content,
            re.MULTILINE,
        ):
            problem_files.append(file_path)

    # Remove duplicates
    problem_files = list(set(problem_files))

    print(f"Found {len(problem_files)} files with potential issues")

    fixed_count = 0
    for file_path in problem_files:
        if file_path.exists():
            if fix_misplaced_imports(file_path):
                print(f"Fixed: {file_path.relative_to(PROJECT_ROOT)}")
                fixed_count += 1

    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    main()
