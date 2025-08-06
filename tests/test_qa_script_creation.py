#!/usr/bin/env python3
"""Test QA agent's ability to create various script types"""

import os
import tempfile
import shutil
import glob

def test_qa_script_patterns():
    """Test that QA agent's allowed patterns work correctly"""
    
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test directories
        scripts_dir = os.path.join(tmpdir, 'scripts')
        tests_dir = os.path.join(tmpdir, 'tests')
        nested_dir = os.path.join(tmpdir, 'src', 'module')
        
        os.makedirs(scripts_dir)
        os.makedirs(tests_dir)
        os.makedirs(nested_dir)
        
        # Test files that QA agent should be able to create
        allowed_files = [
            # Test files
            os.path.join(tests_dir, 'test_example.py'),
            os.path.join(tests_dir, 'integration', 'test_api.py'),
            os.path.join(nested_dir, 'test_module.py'),
            os.path.join(nested_dir, 'module_test.py'),
            
            # Script files
            os.path.join(scripts_dir, 'run_tests.sh'),
            os.path.join(scripts_dir, 'test_coverage.py'),
            os.path.join(scripts_dir, 'e2e', 'test_flow.js'),
            os.path.join(scripts_dir, 'test_qa_automation.sh'),
            os.path.join(scripts_dir, 'test_performance.py'),
        ]
        
        # Test files that QA agent should NOT be able to create
        disallowed_files = [
            # Source code files
            os.path.join(tmpdir, 'main.py'),
            os.path.join(nested_dir, 'module.py'),
            
            # Non-script files in scripts dir
            os.path.join(scripts_dir, 'config.json'),
            os.path.join(scripts_dir, 'README.md'),
            
            # Scripts without proper extensions
            os.path.join(scripts_dir, 'script'),
            os.path.join(scripts_dir, 'test.txt'),
        ]
        
        # Load QA agent allowed patterns
        qa_patterns = {
            'Edit': [
                "tests/**", "test/**", "**/test_*.py", "**/*_test.py",
                "scripts/*.sh", "scripts/*.py", "scripts/*.js",
                "scripts/**/*.sh", "scripts/**/*.py", "scripts/**/*.js",
                "scripts/test_*.sh", "scripts/test_*.py"
            ],
            'Write': [
                "tests/**", "test/**", "**/test_*.py", "**/*_test.py",
                "scripts/*.sh", "scripts/*.py", "scripts/*.js",
                "scripts/**/*.sh", "scripts/**/*.py", "scripts/**/*.js",
                "scripts/test_*.sh", "scripts/test_*.py"
            ]
        }
        
        print("Testing QA agent file access patterns...\n")
        
        # Test allowed files
        print("✅ Files QA agent SHOULD be able to create/edit:")
        for filepath in allowed_files:
            # Create parent directory if needed
            parent = os.path.dirname(filepath)
            if parent and not os.path.exists(parent):
                os.makedirs(parent)
                
            # Create the file
            with open(filepath, 'w') as f:
                f.write("# Test file")
                
            # Check if file matches any allowed pattern
            rel_path = os.path.relpath(filepath, tmpdir)
            matches = check_pattern_match(rel_path, qa_patterns['Write'])
            
            status = "✅" if matches else "❌"
            print(f"  {status} {rel_path} {'(matches: ' + ', '.join(matches) + ')' if matches else '(NO MATCH)'}")
            
        print("\n❌ Files QA agent should NOT be able to create/edit:")
        for filepath in disallowed_files:
            rel_path = os.path.relpath(filepath, tmpdir)
            matches = check_pattern_match(rel_path, qa_patterns['Write'])
            
            status = "❌" if not matches else "✅"
            print(f"  {status} {rel_path} {'(INCORRECTLY matches: ' + ', '.join(matches) + ')' if matches else '(correctly blocked)'}")
            
        return True


def check_pattern_match(filepath, patterns):
    """Check if a filepath matches any of the glob patterns"""
    from pathlib import Path
    
    matches = []
    for pattern in patterns:
        # Use pathlib's match method which properly handles ** patterns
        if Path(filepath).match(pattern):
            matches.append(pattern)
                    
    return matches


if __name__ == "__main__":
    print("Testing QA agent script creation permissions...\n")
    
    if test_qa_script_patterns():
        print("\n✅ QA agent pattern test completed!")
    else:
        print("\n❌ QA agent pattern test failed!")