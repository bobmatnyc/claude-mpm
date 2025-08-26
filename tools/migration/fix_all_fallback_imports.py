#!/usr/bin/env python3
"""Fix all fallback imports in orchestration files."""

import re
from pathlib import Path


def fix_file(file_path: Path):
    """Fix fallback imports in a single file."""
    with open(file_path) as f:
        content = f.read()

    original_content = content

    # Replace fallback imports
    content = re.sub(
        r"    from utils\.logger import", "    from core.logger import", content
    )
    content = re.sub(
        r"    from core\.project_logger import", "    from core.logger import", content
    )

    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        return True
    return False


def main():
    """Main function."""
    orchestration_dir = Path(
        "/Users/masa/Projects/claude-mpm/src/claude_mpm/orchestration"
    )

    files_to_fix = [
        "wrapper_orchestrator.py",
        "direct_orchestrator.py",
        "system_prompt_orchestrator.py",
        "orchestrator.py",
        "pty_orchestrator.py",
        "interactive_subprocess_orchestrator.py",
        "todo_hijacker.py",
        "todo_transformer.py",
        "pexpect_orchestrator.py",
        "ticket_extractor.py",
        "agent_delegator.py",
    ]

    fixed_count = 0
    for file_name in files_to_fix:
        file_path = orchestration_dir / file_name
        if file_path.exists() and fix_file(file_path):
            print(f"Fixed: {file_name}")
            fixed_count += 1

    # Also fix other files
    other_files = [
        "/Users/masa/Projects/claude-mpm/src/claude_mpm/core/agent_registry.py",
        "/Users/masa/Projects/claude-mpm/src/claude_mpm/core/minimal_framework_loader.py",
        "/Users/masa/Projects/claude-mpm/src/claude_mpm/services/hook_service_manager.py",
        "/Users/masa/Projects/claude-mpm/src/claude_mpm/cli.py",
    ]

    for file_path in other_files:
        file_path = Path(file_path)
        if file_path.exists() and fix_file(file_path):
            print(f"Fixed: {file_path.name}")
            fixed_count += 1

    print(f"\nTotal files fixed: {fixed_count}")


if __name__ == "__main__":
    main()
