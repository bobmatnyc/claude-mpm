#!/usr/bin/env python3
"""Fix test infrastructure issues blocking 500+ tests."""

import os
import re
from pathlib import Path


def fix_command_base_imports():
    """Fix all imports from command_base to base_command."""
    project_root = Path('.')
    files_updated = []
    
    # Files that need updating based on grep results
    files_to_update = [
        'tests/cli/commands/test_cleanup_command.py',
        'tests/cli/commands/test_run_command_fixed.py',
        'tests/cli/commands/test_aggregate_command.py',
        'tests/cli/commands/test_cleanup_command_fixed.py',
        'tests/cli/commands/test_run_command.py',
        'tests/cli/commands/test_agents_command.py',
        'tests/cli/commands/test_monitor_command.py',
        'tests/cli/commands/test_config_command_fixed.py',
        'tests/cli/commands/test_config_command.py',
        'tests/cli/test_shared_utilities.py',
        'tests/cli/test_base_command.py',
        'tests/test_tickets_command_migration.py',
        'tests/test_memory_cli_commands.py',
        'tests/test_run_command_migration.py',
        'tests/test_memory_command_unit.py',
        'src/claude_mpm/cli/commands/memory.py',
    ]
    
    for file_path in files_to_update:
        full_path = project_root / file_path
        if full_path.exists():
            try:
                content = full_path.read_text()
                original = content
                
                # Fix direct imports
                content = re.sub(
                    r'from claude_mpm\.cli\.shared\.command_base',
                    'from claude_mpm.cli.shared.base_command',
                    content
                )
                
                # Fix relative imports
                content = re.sub(
                    r'from \.\.shared\.command_base',
                    'from ..shared.base_command',
                    content
                )
                
                # Fix another relative import pattern
                content = re.sub(
                    r'from \.command_base',
                    'from .base_command',
                    content
                )
                
                if content != original:
                    full_path.write_text(content)
                    files_updated.append(str(file_path))
                    print(f"✓ Updated imports in {file_path}")
            except Exception as e:
                print(f"✗ Error processing {file_path}: {e}")
    
    return files_updated


def fix_memory_module_imports():
    """Fix memory module import issues."""
    memory_init = Path('src/claude_mpm/services/memory/__init__.py')
    
    # Check what actually exists in memory module
    memory_dir = Path('src/claude_mpm/services/memory')
    if not memory_dir.exists():
        print(f"✗ Memory directory does not exist: {memory_dir}")
        return []
    
    # List existing files
    py_files = list(memory_dir.glob('*.py'))
    print(f"Found memory module files: {[f.name for f in py_files]}")
    
    # Check for specific classes
    files_updated = []
    
    # Update memory __init__.py if it exists
    if memory_init.exists():
        content = memory_init.read_text()
        
        # Check if builder.py exists
        if (memory_dir / 'builder.py').exists():
            if 'from .builder import' not in content:
                content += '\nfrom .builder import MemoryBuilder\n'
                files_updated.append('memory/__init__.py - added MemoryBuilder')
        
        # Check for indexed_memory
        if (memory_dir / 'indexed_memory.py').exists():
            if 'from .indexed_memory import' not in content:
                content += 'from .indexed_memory import IndexedMemory\n'
                files_updated.append('memory/__init__.py - added IndexedMemory')
        
        # Check for agent_memory_manager
        if (memory_dir / 'agent_memory_manager.py').exists():
            if 'from .agent_memory_manager import' not in content:
                content += 'from .agent_memory_manager import AgentMemoryManager\n'
                files_updated.append('memory/__init__.py - added AgentMemoryManager')
        
        # Write back if modified
        if files_updated:
            memory_init.write_text(content)
            print(f"✓ Updated memory module __init__.py")
    
    return files_updated


def fix_agent_module_imports():
    """Fix agent module import issues."""
    agents_init = Path('src/claude_mpm/services/agents/__init__.py')
    agents_dir = Path('src/claude_mpm/services/agents')
    
    if not agents_dir.exists():
        print(f"✗ Agents directory does not exist: {agents_dir}")
        return []
    
    files_updated = []
    
    # Check for loading submodule
    loading_dir = agents_dir / 'loading'
    if loading_dir.exists():
        # Check if agent_loader.py exists
        if (loading_dir / 'agent_loader.py').exists():
            loading_init = loading_dir / '__init__.py'
            if loading_init.exists():
                content = loading_init.read_text()
                if 'from .agent_loader import' not in content:
                    content += '\nfrom .agent_loader import AgentLoader\n'
                    loading_init.write_text(content)
                    files_updated.append('agents/loading/__init__.py - added AgentLoader')
                    print(f"✓ Updated agents/loading __init__.py")
    
    return files_updated


def verify_test_collection():
    """Run pytest to verify collection improvements."""
    import subprocess
    
    print("\n" + "="*60)
    print("Verifying test collection improvements...")
    print("="*60)
    
    # Count collection errors
    result = subprocess.run(
        ['python', '-m', 'pytest', 'tests/', '--collect-only'],
        capture_output=True,
        text=True
    )
    
    error_count = result.stderr.count('ERROR collecting')
    print(f"\nCollection errors: {error_count}")
    
    # Count collected tests
    collected_match = re.search(r'collected (\d+) items', result.stdout)
    if collected_match:
        collected_count = int(collected_match.group(1))
        print(f"Tests collected: {collected_count}")
    
    return error_count


def main():
    """Main function to fix all test infrastructure issues."""
    print("Fixing test infrastructure issues...")
    print("="*60)
    
    # Fix command_base imports
    print("\n1. Fixing command_base -> base_command imports...")
    command_files = fix_command_base_imports()
    print(f"   Updated {len(command_files)} files")
    
    # Fix memory module imports
    print("\n2. Fixing memory module imports...")
    memory_files = fix_memory_module_imports()
    print(f"   Updated {len(memory_files)} items")
    
    # Fix agent module imports
    print("\n3. Fixing agent module imports...")
    agent_files = fix_agent_module_imports()
    print(f"   Updated {len(agent_files)} items")
    
    # Verify improvements
    error_count = verify_test_collection()
    
    print("\n" + "="*60)
    print("Summary:")
    print(f"  - Command base imports fixed: {len(command_files)} files")
    print(f"  - Memory module updates: {len(memory_files)} items")
    print(f"  - Agent module updates: {len(agent_files)} items")
    print(f"  - Remaining collection errors: {error_count}")
    print("="*60)
    
    if error_count < 10:
        print("✓ Test infrastructure significantly improved!")
    else:
        print("⚠ Some collection errors remain. Run pytest --collect-only for details.")


if __name__ == "__main__":
    main()