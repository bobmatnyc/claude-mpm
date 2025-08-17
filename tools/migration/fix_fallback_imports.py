#!/usr/bin/env python3
"""Fix fallback imports that still reference old logger locations."""

import re
from pathlib import Path

def fix_fallback_imports(file_path: Path):
    """Fix fallback imports in a file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Fix patterns
    replacements = [
        # utils.logger fallbacks
        (r'from utils\.logger import', 'from core.logger import'),
        # logging_config fallbacks
        (r'from core\.logging_config import', 'from core.logger import'),
        # project_logger fallbacks
        (r'from core\.project_logger import', 'from core.logger import'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Main function."""
    files_to_fix = [
        '/Users/masa/Projects/claude-mpm/src/claude_mpm/services/ticket_manager.py',
        '/Users/masa/Projects/claude-mpm/core/agent_registry.py',
        '/Users/masa/Projects/claude-mpm/core/minimal_framework_loader.py',
        '/Users/masa/Projects/claude-mpm/services/hook_service_manager.py',
        '/Users/masa/Projects/claude-mpm/orchestration/subprocess_orchestrator.py',
        '/Users/masa/Projects/claude-mpm/orchestration/pexpect_orchestrator.py',
        '/Users/masa/Projects/claude-mpm/orchestration/interactive_subprocess_orchestrator.py',
        '/Users/masa/Projects/claude-mpm/cli.py',
        '/Users/masa/Projects/claude-mpm/orchestration/wrapper_orchestrator.py',
    ]
    
    fixed_count = 0
    for file_path in files_to_fix:
        file_path = Path(file_path)
        if file_path.exists():
            if fix_fallback_imports(file_path):
                print(f"Fixed fallback imports in: {file_path}")
                fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()