#!/usr/bin/env python3
"""Script to update agent service imports to new hierarchical structure."""

import os
import re
from pathlib import Path


def update_imports_in_file(filepath):
    """Update imports in a single file."""
    with open(filepath, "r") as f:
        content = f.read()

    original_content = content

    # Define import replacements
    replacements = [
        # Direct service imports
        (
            r"from claude_mpm\.services\.agent_registry import",
            "from claude_mpm.services.agents.registry import",
        ),
        (
            r"from claude_mpm\.services\.agent_deployment import",
            "from claude_mpm.services.agents.deployment import",
        ),
        (
            r"from claude_mpm\.services\.agent_memory_manager import",
            "from claude_mpm.services.agents.memory import",
        ),
        (
            r"from claude_mpm\.services\.agent_lifecycle_manager import",
            "from claude_mpm.services.agents.deployment import",
        ),
        (
            r"from claude_mpm\.services\.agent_management_service import",
            "from claude_mpm.services.agents.management import",
        ),
        (
            r"from claude_mpm\.services\.agent_capabilities_generator import",
            "from claude_mpm.services.agents.management import",
        ),
        (
            r"from claude_mpm\.services\.agent_modification_tracker import",
            "from claude_mpm.services.agents.registry.modification_tracker import",
        ),
        (
            r"from claude_mpm\.services\.agent_persistence_service import",
            "from claude_mpm.services.agents.memory import",
        ),
        (
            r"from claude_mpm\.services\.agent_profile_loader import",
            "from claude_mpm.services.agents.loading import",
        ),
        (
            r"from claude_mpm\.services\.agent_versioning import",
            "from claude_mpm.services.agents.deployment import",
        ),
        (
            r"from claude_mpm\.services\.base_agent_manager import",
            "from claude_mpm.services.agents.loading import",
        ),
        (
            r"from claude_mpm\.services\.deployed_agent_discovery import",
            "from claude_mpm.services.agents.registry import",
        ),
        (
            r"from claude_mpm\.services\.framework_agent_loader import",
            "from claude_mpm.services.agents.loading import",
        ),
    ]

    for old_pattern, new_pattern in replacements:
        content = re.sub(old_pattern, new_pattern, content)

    # Only write if content changed
    if content != original_content:
        with open(filepath, "w") as f:
            f.write(content)
        return True
    return False


def main():
    """Update all Python files with old imports."""
    project_root = Path(__file__).parent.parent

    # Directories to update
    dirs_to_update = [
        project_root / "tests",
        project_root / "scripts",
        project_root / "docs",
    ]

    updated_files = []

    for directory in dirs_to_update:
        if not directory.exists():
            continue

        for py_file in directory.rglob("*.py"):
            # Skip the services/agents directory itself
            if "services/agents" in str(py_file):
                continue

            if update_imports_in_file(py_file):
                updated_files.append(py_file)
                print(f"✓ Updated: {py_file.relative_to(project_root)}")

    # Also update markdown files in docs
    for md_file in (project_root / "docs").rglob("*.md"):
        with open(md_file, "r") as f:
            content = f.read()

        original_content = content

        # Update import statements in code blocks
        replacements = [
            (
                "from claude_mpm.services.agent_registry",
                "from claude_mpm.services.agents.registry",
            ),
            (
                "from claude_mpm.services.agent_deployment",
                "from claude_mpm.services.agents.deployment",
            ),
            (
                "from claude_mpm.services.agent_memory_manager",
                "from claude_mpm.services.agents.memory",
            ),
            (
                "from claude_mpm.services.agent_lifecycle_manager",
                "from claude_mpm.services.agents.deployment",
            ),
            (
                "from claude_mpm.services.agent_management_service",
                "from claude_mpm.services.agents.management",
            ),
            (
                "from claude_mpm.services.agent_capabilities_generator",
                "from claude_mpm.services.agents.management",
            ),
        ]

        for old_text, new_text in replacements:
            content = content.replace(old_text, new_text)

        if content != original_content:
            with open(md_file, "w") as f:
                f.write(content)
            updated_files.append(md_file)
            print(f"✓ Updated: {md_file.relative_to(project_root)}")

    print(f"\n✅ Updated {len(updated_files)} files")


if __name__ == "__main__":
    main()
