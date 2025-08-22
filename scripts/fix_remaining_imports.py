#!/usr/bin/env python3
"""Fix remaining import issues in test files."""

import re
from pathlib import Path


def fix_agent_loader_imports():
    """Fix incorrect agent_loader import paths."""
    project_root = Path('.')
    
    # Files that need agent_loader import fixes
    files_to_fix = [
        'tests/e2e/test_agent_system_e2e.py',
        'tests/agents/test_instruction_loading.py',
        'tests/agents/test_agent_loader_comprehensive.py',
        'tests/integration/test_schema_integration.py',
        'tests/test_agent_name_formats.py',
        'tests/test_schema_standardization.py',
        'tests/test_agent_name_normalization.py',
        'tests/test_agent_functionality_complete.py',
        'tests/test_agent_loader.py',
        'tests/test_agent_deployment_integration.py',
        'tests/test_agent_loader_format.py',
    ]
    
    fixed_count = 0
    for file_path in files_to_fix:
        full_path = project_root / file_path
        if full_path.exists():
            try:
                content = full_path.read_text()
                original = content
                
                # Fix agent_loader imports
                content = re.sub(
                    r'from claude_mpm\.services\.agents\.agent_loader',
                    'from claude_mpm.agents.agent_loader',
                    content
                )
                
                # Also fix any related imports
                content = re.sub(
                    r'from claude_mpm\.services\.agents import AgentLoader',
                    'from claude_mpm.agents.agent_loader import AgentLoader',
                    content
                )
                
                if content != original:
                    full_path.write_text(content)
                    print(f"✓ Fixed imports in {file_path}")
                    fixed_count += 1
            except Exception as e:
                print(f"✗ Error processing {file_path}: {e}")
    
    return fixed_count


def fix_memory_test_imports():
    """Fix memory-related test imports."""
    project_root = Path('.')
    
    # Find all test files with memory imports
    test_files = list(project_root.glob('tests/**/test_memory*.py'))
    test_files.extend(list(project_root.glob('tests/**/test_*memory*.py')))
    
    fixed_count = 0
    for test_file in test_files:
        try:
            content = test_file.read_text()
            original = content
            
            # Fix IndexedMemory -> IndexedMemoryService
            content = re.sub(
                r'from claude_mpm\.services\.memory import IndexedMemory(?!Service)',
                'from claude_mpm.services.memory import IndexedMemoryService',
                content
            )
            
            # Fix class usage
            content = re.sub(
                r'\bIndexedMemory\(',
                'IndexedMemoryService(',
                content
            )
            
            # Fix type hints
            content = re.sub(
                r': IndexedMemory(?!Service)',
                ': IndexedMemoryService',
                content
            )
            
            if content != original:
                test_file.write_text(content)
                print(f"✓ Fixed memory imports in {test_file.relative_to(project_root)}")
                fixed_count += 1
        except Exception as e:
            print(f"✗ Error processing {test_file}: {e}")
    
    return fixed_count


def fix_response_logging_imports():
    """Fix response logging test imports."""
    project_root = Path('.')
    
    # Response logging test files
    files_to_check = [
        'tests/test_response_logging_auto_switch.py',
        'tests/test_response_logging_comprehensive.py',
        'tests/test_response_logging_integration.py',
        'tests/test_response_logging.py',
    ]
    
    fixed_count = 0
    for file_path in files_to_check:
        full_path = project_root / file_path
        if full_path.exists():
            try:
                content = full_path.read_text()
                original = content
                
                # Common response logging import fixes
                content = re.sub(
                    r'from claude_mpm\.services\.response_logging',
                    'from claude_mpm.services.response_tracker',
                    content
                )
                
                content = re.sub(
                    r'from claude_mpm\.hooks\.response_logging',
                    'from claude_mpm.hooks.claude_hooks.response_tracking',
                    content
                )
                
                if content != original:
                    full_path.write_text(content)
                    print(f"✓ Fixed response logging imports in {file_path}")
                    fixed_count += 1
            except Exception as e:
                print(f"✗ Error processing {file_path}: {e}")
    
    return fixed_count


def main():
    """Main function to fix all remaining import issues."""
    print("Fixing remaining import issues...")
    print("="*60)
    
    # Fix agent loader imports
    print("\n1. Fixing agent_loader import paths...")
    agent_fixed = fix_agent_loader_imports()
    print(f"   Fixed {agent_fixed} files")
    
    # Fix memory imports
    print("\n2. Fixing memory test imports...")
    memory_fixed = fix_memory_test_imports()
    print(f"   Fixed {memory_fixed} files")
    
    # Fix response logging imports
    print("\n3. Fixing response logging imports...")
    response_fixed = fix_response_logging_imports()
    print(f"   Fixed {response_fixed} files")
    
    print("\n" + "="*60)
    print(f"Total files fixed: {agent_fixed + memory_fixed + response_fixed}")
    print("="*60)
    
    # Verify improvements
    import subprocess
    result = subprocess.run(
        ['python', '-m', 'pytest', 'tests/', '--collect-only'],
        capture_output=True,
        text=True
    )
    
    error_count = result.stderr.count('ERROR collecting')
    collected_match = re.search(r'collected (\d+) items', result.stdout)
    
    print(f"\nTest collection status:")
    print(f"  Collection errors: {error_count}")
    if collected_match:
        print(f"  Tests collected: {collected_match.group(1)}")
    
    if error_count == 0:
        print("\n✓ All test collection errors resolved!")
    else:
        print(f"\n⚠ {error_count} collection errors remain")


if __name__ == "__main__":
    main()