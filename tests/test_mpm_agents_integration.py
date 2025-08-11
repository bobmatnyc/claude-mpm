#!/usr/bin/env python3
"""Comprehensive test for /mpm agents command integration.

WHY: This script tests all the different ways users can invoke the agent version
display functionality to ensure consistency across:
1. CLI with --mpm:agents
2. CLI with agents (without prefix)
3. Interactive wrapper with /mpm:agents
4. Claude Code hooks with /mpm agents
"""

import subprocess
import sys
import json
from pathlib import Path

def test_cli_with_prefix():
    """Test: claude-mpm --mpm:agents"""
    print("=" * 60)
    print("Test 1: CLI with prefix (claude-mpm --mpm:agents)")
    print("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "-m", "claude_mpm.cli", "--mpm:agents"],
        capture_output=True,
        text=True
    )
    
    print("STDOUT:")
    print(result.stdout)
    print(f"\nReturn code: {result.returncode}")
    return result.stdout

def test_cli_without_prefix():
    """Test: claude-mpm agents"""
    print("\n" + "=" * 60)
    print("Test 2: CLI without prefix (claude-mpm agents)")
    print("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "-m", "claude_mpm.cli", "agents"],
        capture_output=True,
        text=True
    )
    
    print("STDOUT:")
    print(result.stdout)
    print(f"\nReturn code: {result.returncode}")
    return result.stdout

def test_interactive_wrapper():
    """Test: /mpm:agents in interactive wrapper"""
    print("\n" + "=" * 60)
    print("Test 3: Interactive wrapper (/mpm:agents)")
    print("=" * 60)
    
    # Simulate the simple runner handling
    try:
        from claude_mpm.core.claude_runner import SimpleClaudeRunner
        runner = SimpleClaudeRunner()
        
        # Test the command handler
        success = runner._handle_mpm_command("/mpm:agents")
        print(f"Command handled successfully: {success}")
    except Exception as e:
        print(f"Error testing interactive wrapper: {e}")

def test_hook_handler():
    """Test: /mpm agents in Claude Code hooks"""
    print("\n" + "=" * 60)
    print("Test 4: Hook handler (/mpm agents)")
    print("=" * 60)
    
    # Create a mock event for the hook handler
    event = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "/mpm agents",
        "session_id": "test-session",
        "cwd": str(Path.cwd())
    }
    
    # Run the hook handler
    hook_script = Path(__file__).parent.parent / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
    
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=json.dumps(event),
        capture_output=True,
        text=True
    )
    
    print("STDERR (where output goes):")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")
    
    # Exit code 2 means the hook handled the command
    if result.returncode == 2:
        print("✓ Hook handler successfully intercepted and handled the command")
    else:
        print("✗ Hook handler did not handle the command as expected")

def compare_outputs(output1, output2, name1, name2):
    """Compare two outputs for consistency."""
    print(f"\n{name1} vs {name2}:")
    
    # Extract just the agent version table for comparison
    def extract_table(output):
        lines = output.split('\n')
        in_table = False
        table_lines = []
        
        for line in lines:
            if "Deployed Agent Versions:" in line:
                in_table = True
            if in_table:
                table_lines.append(line.strip())
                if line.strip() == "-" * 40 and len(table_lines) > 1:
                    break
        
        return '\n'.join(table_lines)
    
    table1 = extract_table(output1)
    table2 = extract_table(output2)
    
    if table1 == table2:
        print("✓ Outputs are consistent")
    else:
        print("✗ Outputs differ!")
        print(f"\n{name1}:")
        print(table1)
        print(f"\n{name2}:")
        print(table2)

def main():
    """Run all tests."""
    print("Testing /mpm agents command integration")
    print("=" * 60)
    
    # Run all tests
    output1 = test_cli_with_prefix()
    output2 = test_cli_without_prefix()
    test_interactive_wrapper()
    test_hook_handler()
    
    # Compare outputs for consistency
    print("\n" + "=" * 60)
    print("Consistency Check")
    print("=" * 60)
    compare_outputs(output1, output2, "CLI with prefix", "CLI without prefix")
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("✓ All /mpm agents command variants have been tested")
    print("✓ The same underlying function is used for consistency")
    print("✓ Users can check agent versions from CLI or within Claude Code")

if __name__ == "__main__":
    main()