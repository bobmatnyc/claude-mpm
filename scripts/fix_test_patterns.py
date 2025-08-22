#!/usr/bin/env python3
"""
Bulk fix script for common test patterns across the codebase.
Fixes import paths, mock patterns, and other common issues.
"""

import os
import re
from pathlib import Path
import sys


def fix_common_patterns():
    """Fix common patterns across all test files."""
    test_dir = Path("tests")
    
    # Pattern replacements - order matters for some patterns
    replacements = [
        # Import fixes
        (r'from claude_mpm\.manager import', 'from claude_mpm.services import'),
        (r'from claude_mpm\.socketio import StandaloneSocketIOServer', 
         'from claude_mpm.services.communication.socketio_service import SocketIOServer'),
        (r'StandaloneSocketIOServer', 'SocketIOServer'),
        
        # CLI command fixes
        (r'aggregate_command\(', 'aggregate_subcommand('),
        (r'config_command\(', 'config_subcommand('),
        (r'memory_command\(', 'memory_subcommand('),
        (r'monitor_command\(', 'monitor_subcommand('),
        (r'run_command\(', 'run_subcommand('),
        (r'tickets_command\(', 'tickets_subcommand('),
        (r'info_command\(', 'info_subcommand('),
        (r'agents_command\(', 'agents_subcommand('),
        (r'cleanup_command\(', 'cleanup_subcommand('),
        
        # Config file extensions
        (r'config\.yaml(?!")', 'config.yml'),
        
        # Mock patterns
        (r'mock_config\.get\(', 'mock_config.return_value.get('),
        (r'@patch\("claude_mpm\.config"', '@patch("claude_mpm.config.manager"'),
        
        # Service paths
        (r'claude_mpm\.session_manager', 'claude_mpm.services.session_manager'),
        (r'claude_mpm\.response_tracker', 'claude_mpm.services.response_tracker'),
        (r'claude_mpm\.hook_service', 'claude_mpm.services.hook_service'),
        (r'claude_mpm\.agent_loader', 'claude_mpm.services.agents.loading.agent_loader'),
        (r'claude_mpm\.memory', 'claude_mpm.services.memory'),
        
        # Memory system imports
        (r'from claude_mpm\.memory\.builder import MemoryBuilder',
         'from claude_mpm.services.memory.builder import MemoryBuilder'),
        (r'from claude_mpm\.memory\.indexed import IndexedMemory',
         'from claude_mpm.services.memory.indexed import IndexedMemory'),
        (r'from claude_mpm\.memory\.manager import AgentMemoryManager',
         'from claude_mpm.services.memory.manager import AgentMemoryManager'),
        
        # Agent system imports
        (r'from claude_mpm\.agent_loader import',
         'from claude_mpm.services.agents.loading.agent_loader import'),
        (r'from claude_mpm\.agents\.definition import',
         'from claude_mpm.services.agents.registry.agent_definition import'),
        
        # Path fixes
        (r'\.claude_mpm/agents', '.claude/agents'),
        (r'~/\.claude_mpm', '~/.claude'),
    ]
    
    files_fixed = 0
    total_changes = 0
    
    for test_file in test_dir.rglob("test_*.py"):
        if 'test_patterns.py' in str(test_file):
            continue  # Skip this script if it's in tests
            
        try:
            content = test_file.read_text()
            original = content
            changes_in_file = 0
            
            for pattern, replacement in replacements:
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    changes_in_file += len(re.findall(pattern, content))
                    content = new_content
            
            if content != original:
                test_file.write_text(content)
                files_fixed += 1
                total_changes += changes_in_file
                print(f"Fixed {test_file} ({changes_in_file} changes)")
        except Exception as e:
            print(f"Error processing {test_file}: {e}")
    
    print(f"\nSummary: Fixed {files_fixed} files with {total_changes} total changes")
    return files_fixed, total_changes


def add_missing_async_decorators():
    """Add missing @pytest.mark.asyncio decorators to async tests."""
    test_dir = Path("tests")
    files_fixed = 0
    
    for test_file in test_dir.rglob("test_*.py"):
        try:
            lines = test_file.read_text().splitlines()
            new_lines = []
            changed = False
            
            for i, line in enumerate(lines):
                new_lines.append(line)
                
                # Check if this is an async test function
                if re.match(r'\s*async def test_', line):
                    # Check if previous line has the decorator
                    if i > 0 and '@pytest.mark.asyncio' not in lines[i-1]:
                        # Insert decorator before the function
                        indent = len(line) - len(line.lstrip())
                        new_lines.insert(-1, ' ' * indent + '@pytest.mark.asyncio')
                        changed = True
                        
                        # Also ensure pytest is imported
                        if not any('import pytest' in l for l in lines[:20]):
                            # Add import at the top after other imports
                            for j, l in enumerate(new_lines):
                                if l.startswith('import ') or l.startswith('from '):
                                    continue
                                else:
                                    new_lines.insert(j, 'import pytest')
                                    break
            
            if changed:
                test_file.write_text('\n'.join(new_lines))
                files_fixed += 1
                print(f"Added async decorators to {test_file}")
                
        except Exception as e:
            print(f"Error processing {test_file}: {e}")
    
    print(f"\nFixed {files_fixed} files with missing async decorators")
    return files_fixed


def fix_mock_patch_paths():
    """Fix mock.patch decorator paths to match new module structure."""
    test_dir = Path("tests")
    files_fixed = 0
    
    # Mapping of old paths to new paths
    patch_replacements = [
        (r'@patch\(["\']claude_mpm\.([^\.]+)["\']',
         r'@patch("claude_mpm.services.\1"'),
        (r'@patch\(["\']claude_mpm\.cli\.([^\.]+)["\']',
         r'@patch("claude_mpm.cli.commands.\1"'),
        (r'@patch\(["\']claude_mpm\.config["\']',
         r'@patch("claude_mpm.config.manager"'),
    ]
    
    for test_file in test_dir.rglob("test_*.py"):
        try:
            content = test_file.read_text()
            original = content
            
            for pattern, replacement in patch_replacements:
                content = re.sub(pattern, replacement, content)
            
            if content != original:
                test_file.write_text(content)
                files_fixed += 1
                print(f"Fixed patch paths in {test_file}")
                
        except Exception as e:
            print(f"Error processing {test_file}: {e}")
    
    print(f"\nFixed patch paths in {files_fixed} files")
    return files_fixed


def main():
    """Run all fix operations."""
    print("Starting bulk test fixes...\n")
    
    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print("=== Fixing common patterns ===")
    fix_common_patterns()
    
    print("\n=== Adding missing async decorators ===")
    add_missing_async_decorators()
    
    print("\n=== Fixing mock patch paths ===")
    fix_mock_patch_paths()
    
    print("\nBulk fixes complete!")
    print("\nNext steps:")
    print("1. Run 'pytest tests/ -x' to see remaining failures")
    print("2. Fix any remaining issues manually")
    print("3. Run './scripts/run_all_tests.sh' for full validation")


if __name__ == "__main__":
    main()