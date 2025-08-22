#!/usr/bin/env python3
"""
Comprehensive test fixing script that addresses all common issues.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


class TestFixer:
    """Comprehensive test fixer for Claude MPM."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"
        self.stats = {
            'files_fixed': 0,
            'imports_fixed': 0,
            'mocks_fixed': 0,
            'async_fixed': 0,
            'paths_fixed': 0,
            'fixtures_fixed': 0,
        }
    
    def fix_imports(self, content: str) -> str:
        """Fix all import statements."""
        replacements = [
            # Service imports
            (r'from claude_mpm\.manager import', 'from claude_mpm.services import'),
            (r'from claude_mpm\.session_manager', 'from claude_mpm.services.session_manager'),
            (r'from claude_mpm\.response_tracker', 'from claude_mpm.services.response_tracker'),
            (r'from claude_mpm\.hook_service', 'from claude_mpm.services.hook_service'),
            (r'from claude_mpm\.agent_loader', 'from claude_mpm.services.agents.loading.agent_loader'),
            (r'from claude_mpm\.memory\.', 'from claude_mpm.services.memory.'),
            (r'from claude_mpm\.agents\.', 'from claude_mpm.services.agents.'),
            
            # Config imports
            (r'from claude_mpm\.config import', 'from claude_mpm.config.manager import'),
            (r'from claude_mpm\.core\.config import Config', 'from claude_mpm.config.manager import ConfigManager'),
            
            # Socket.IO imports
            (r'from claude_mpm\.socketio import StandaloneSocketIOServer', 
             'from claude_mpm.services.communication.socketio_service import SocketIOServer'),
            (r'StandaloneSocketIOServer', 'SocketIOServer'),
            
            # CLI imports
            (r'from claude_mpm\.cli\.([^\.]+) import', r'from claude_mpm.cli.commands.\1 import'),
        ]
        
        for pattern, replacement in replacements:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                self.stats['imports_fixed'] += 1
                content = new_content
        
        return content
    
    def fix_cli_commands(self, content: str) -> str:
        """Fix CLI command function names."""
        commands = [
            'aggregate', 'config', 'memory', 'monitor', 'run', 
            'tickets', 'info', 'agents', 'cleanup', 'mcp'
        ]
        
        for cmd in commands:
            pattern = f'{cmd}_command\\('
            replacement = f'{cmd}_subcommand('
            content = re.sub(pattern, replacement, content)
        
        return content
    
    def fix_mock_patterns(self, content: str) -> str:
        """Fix mock usage patterns."""
        replacements = [
            # Mock config patterns
            (r'mock_config\.get\(', 'mock_config.return_value.get('),
            (r'mock_config\.get_', 'mock_config.return_value.get_'),
            
            # Patch paths
            (r'@patch\(["\']claude_mpm\.config["\']', '@patch("claude_mpm.config.manager"'),
            (r'@patch\(["\']claude_mpm\.utils\.paths\.get_path_manager\(\)["\']', 
             '@patch("claude_mpm.utils.paths.get_path_manager"'),
            
            # Service patches
            (r'@patch\(["\']claude_mpm\.([^\.]+)_service["\']', 
             r'@patch("claude_mpm.services.\1_service"'),
        ]
        
        for pattern, replacement in replacements:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                self.stats['mocks_fixed'] += 1
                content = new_content
        
        return content
    
    def fix_async_patterns(self, content: str) -> str:
        """Add missing async decorators and fix async patterns."""
        lines = content.splitlines()
        new_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check for async test functions without decorator
            if re.match(r'\s*async def test_', line):
                # Check if previous line has the decorator
                if i > 0 and '@pytest.mark.asyncio' not in lines[i-1]:
                    # Add decorator with proper indentation
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(' ' * indent + '@pytest.mark.asyncio')
                    self.stats['async_fixed'] += 1
            
            new_lines.append(line)
            i += 1
        
        # Ensure pytest is imported if we added async decorators
        if self.stats['async_fixed'] > 0:
            if not any('import pytest' in line for line in new_lines[:30]):
                # Find the right place to add import
                for j, line in enumerate(new_lines):
                    if line.startswith('from ') or line.startswith('import '):
                        continue
                    else:
                        new_lines.insert(j, 'import pytest')
                        break
        
        return '\n'.join(new_lines)
    
    def fix_paths(self, content: str) -> str:
        """Fix file paths and directory references."""
        replacements = [
            # Config files
            (r'config\.yaml(?!")', 'config.yml'),
            
            # Agent directories
            (r'\.claude_mpm/agents', '.claude/agents'),
            (r'\.claude-mpm/memories', '.claude/memories'),
            (r'~/\.claude_mpm', '~/.claude'),
            
            # Test data paths
            (r'test_data/config\.yaml', 'test_data/config.yml'),
        ]
        
        for pattern, replacement in replacements:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                self.stats['paths_fixed'] += 1
                content = new_content
        
        return content
    
    def fix_fixtures(self, content: str) -> str:
        """Fix fixture usage and common fixture patterns."""
        replacements = [
            # Common fixture replacements
            (r'tempfile\.mkdtemp\(\)', 'tmp_path'),
            (r'tempfile\.TemporaryDirectory\(\)', 'tmp_path'),
        ]
        
        # Fix self parameter in test methods
        content = re.sub(
            r'def (test_\w+)\(self(?:,\s*)?([^)]*)\):',
            r'def \1(\2):',
            content
        )
        
        for pattern, replacement in replacements:
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            if new_content != content:
                self.stats['fixtures_fixed'] += 1
                content = new_content
        
        return content
    
    def fix_file(self, file_path: Path) -> bool:
        """Fix a single test file."""
        try:
            original_content = file_path.read_text()
            content = original_content
            
            # Apply all fixes
            content = self.fix_imports(content)
            content = self.fix_cli_commands(content)
            content = self.fix_mock_patterns(content)
            content = self.fix_async_patterns(content)
            content = self.fix_paths(content)
            content = self.fix_fixtures(content)
            
            # Write back if changed
            if content != original_content:
                file_path.write_text(content)
                self.stats['files_fixed'] += 1
                return True
            
            return False
            
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")
            return False
    
    def fix_all_tests(self):
        """Fix all test files in the project."""
        print("Starting comprehensive test fixes...")
        print("=" * 60)
        
        test_files = list(self.test_dir.rglob("test_*.py"))
        print(f"Found {len(test_files)} test files to process")
        
        for i, test_file in enumerate(test_files, 1):
            if self.fix_file(test_file):
                print(f"[{i}/{len(test_files)}] Fixed: {test_file.relative_to(self.project_root)}")
            
            # Show progress every 10 files
            if i % 10 == 0:
                print(f"Progress: {i}/{len(test_files)} files processed...")
        
        print("\n" + "=" * 60)
        print("Fix Summary:")
        print(f"  Files fixed:     {self.stats['files_fixed']}")
        print(f"  Imports fixed:   {self.stats['imports_fixed']}")
        print(f"  Mocks fixed:     {self.stats['mocks_fixed']}")
        print(f"  Async fixed:     {self.stats['async_fixed']}")
        print(f"  Paths fixed:     {self.stats['paths_fixed']}")
        print(f"  Fixtures fixed:  {self.stats['fixtures_fixed']}")
        
        return self.stats['files_fixed']
    
    def verify_fixes(self):
        """Run a quick test to verify fixes worked."""
        print("\nVerifying fixes...")
        
        # Run a quick pytest to see if imports work
        result = os.system("pytest tests/ -x --collect-only 2>&1 | head -20")
        
        if result == 0:
            print("✅ Test collection successful!")
        else:
            print("⚠️  Some tests may still have issues")
        
        print("\nNext steps:")
        print("1. Run 'pytest tests/ -x' to see remaining failures")
        print("2. Run './scripts/run_all_tests.sh' for full validation")
        print("3. Fix any remaining issues manually")


def main():
    """Main entry point."""
    # Change to project root
    os.chdir(Path(__file__).parent.parent)
    
    fixer = TestFixer()
    files_fixed = fixer.fix_all_tests()
    
    if files_fixed > 0:
        fixer.verify_fixes()
    else:
        print("No files needed fixing!")
    
    return 0 if files_fixed >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())