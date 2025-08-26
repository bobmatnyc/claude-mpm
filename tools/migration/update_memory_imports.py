#!/usr/bin/env python3
"""Update memory service imports after reorganization."""

import re
from pathlib import Path

# Define the import mappings
IMPORT_MAPPINGS = [
    # Memory services
    (
        r"from claude_mpm\.services\.memory_builder import",
        "from claude_mpm.services.memory.builder import",
    ),
    (
        r"from claude_mpm\.services\.memory_router import",
        "from claude_mpm.services.memory.router import",
    ),
    (
        r"from claude_mpm\.services\.memory_optimizer import",
        "from claude_mpm.services.memory.optimizer import",
    ),
    # Cache services
    (
        r"from claude_mpm\.services\.simple_cache_service import",
        "from claude_mpm.services.memory.cache.simple_cache import",
    ),
    (
        r"from claude_mpm\.services\.shared_prompt_cache import",
        "from claude_mpm.services.memory.cache.shared_prompt_cache import",
    ),
]


def update_file(file_path: Path) -> bool:
    """Update imports in a single file."""
    try:
        content = file_path.read_text()
        original_content = content

        for old_pattern, new_import in IMPORT_MAPPINGS:
            content = re.sub(old_pattern, new_import, content)

        if content != original_content:
            file_path.write_text(content)
            print(f"Updated: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False


def main():
    """Update all Python files with new import paths."""
    project_root = Path(__file__).parent.parent

    # Directories to search
    search_dirs = [
        project_root / "src",
        project_root / "tests",
        project_root / "scripts",
    ]

    updated_count = 0
    for search_dir in search_dirs:
        if search_dir.exists():
            for py_file in search_dir.rglob("*.py"):
                if update_file(py_file):
                    updated_count += 1

    # Also update markdown docs if they contain code examples
    docs_dir = project_root / "docs"
    if docs_dir.exists():
        for md_file in docs_dir.rglob("*.md"):
            if update_file(md_file):
                updated_count += 1

    print(f"\nTotal files updated: {updated_count}")


if __name__ == "__main__":
    main()
