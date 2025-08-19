#!/usr/bin/env python3
"""
Verify that the --resume flag fix is properly implemented.
Simple verification script without complex dependencies.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def verify_fix():
    """Verify the --resume flag implementation."""
    print("Verifying --resume flag implementation...")
    print("=" * 50)
    
    # Check 1: Bash wrapper includes --resume
    bash_script = Path(__file__).parent / "claude-mpm"
    if bash_script.exists():
        content = bash_script.read_text()
        if '"--resume"' in content and 'MPM_FLAGS=' in content:
            print("✅ Bash wrapper includes --resume in MPM_FLAGS")
        else:
            print("❌ Bash wrapper missing --resume in MPM_FLAGS")
            return False
    
    # Check 2: Parser includes --resume
    from claude_mpm.cli.parser import create_parser
    parser = create_parser("test", "1.0.0")
    
    # Check if --resume is in the parser (top-level arguments)
    has_resume = False
    for action in parser._actions:
        if hasattr(action, 'dest') and action.dest == 'resume':
            has_resume = True
            break
    
    if has_resume:
        print("✅ Parser includes --resume flag")
    else:
        print("❌ Parser missing --resume flag")
        return False
    
    # Check 3: Run parser also has --resume
    from claude_mpm.cli.parsers.run_parser import add_run_arguments
    import argparse
    run_parser = argparse.ArgumentParser()
    add_run_arguments(run_parser)
    
    has_resume = False
    for action in run_parser._actions:
        if hasattr(action, 'dest') and action.dest == 'resume':
            has_resume = True
            break
    
    if has_resume:
        print("✅ Run subparser includes --resume flag")
    else:
        print("❌ Run subparser missing --resume flag")
        return False
    
    # Check 4: Filter function doesn't filter out --resume
    from claude_mpm.cli.commands.run import filter_claude_mpm_args
    test_args = ["--resume", "--model", "opus", "--monitor"]
    filtered = filter_claude_mpm_args(test_args)
    
    if "--resume" in filtered and "--monitor" not in filtered:
        print("✅ Filter function correctly handles --resume")
    else:
        print("❌ Filter function incorrectly handles --resume")
        return False
    
    # Check 5: _ensure_run_attributes handles --resume
    from claude_mpm.cli import _ensure_run_attributes
    
    class MockArgs:
        def __init__(self):
            self.resume = True
            self.claude_args = []
    
    args = MockArgs()
    _ensure_run_attributes(args)
    
    if "--resume" in args.claude_args:
        print("✅ _ensure_run_attributes adds --resume to claude_args")
    else:
        print("❌ _ensure_run_attributes doesn't add --resume")
        return False
    
    print("=" * 50)
    print("✅ ALL CHECKS PASSED!")
    print("\nThe --resume flag is properly implemented and will:")
    print("1. Be recognized by the bash wrapper")
    print("2. Be parsed correctly by the argument parser")
    print("3. Pass through to Claude Desktop")
    print("\nUsage:")
    print("  claude-mpm --resume")
    print("  claude-mpm run --resume")
    
    return True

if __name__ == "__main__":
    success = verify_fix()
    sys.exit(0 if success else 1)