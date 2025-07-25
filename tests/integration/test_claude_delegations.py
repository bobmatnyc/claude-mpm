#!/usr/bin/env python3
"""Test Claude's native delegation with logging."""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.orchestration.orchestrator import MPMOrchestrator
from claude_mpm.core.logger import get_project_logger

def main():
    print("🚀 Testing Claude's Native Delegation")
    print("=" * 80)
    
    # Initialize project logger
    project_logger = get_project_logger("DEBUG")
    
    # Create standard orchestrator (not subprocess)
    orchestrator = MPMOrchestrator(log_level="DEBUG")
    
    # Log the session
    project_logger.log_system(
        "Starting Claude session with framework injection",
        level="INFO",
        component="test"
    )
    
    print("\nThis test will:")
    print("1. Start Claude with the PM framework")
    print("2. You can manually delegate tasks using Claude's Task tool")
    print("3. Logs will be created in .claude-mpm/")
    print("\nExample delegation in Claude:")
    print('  Task("Create a Python function to calculate factorial")')
    print("\nStarting Claude interactive session...\n")
    
    try:
        orchestrator.run_interactive()
    except KeyboardInterrupt:
        print("\nSession ended by user")
    
    # Show what was logged
    print("\n" + "=" * 80)
    print("📊 Session Summary")
    print("=" * 80)
    
    # List log files
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        log_dir = claude_mpm_dir / "logs"
        print("\n📁 Log files created:")
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if file.endswith('.jsonl'):
                    file_path = Path(root) / file
                    size = file_path.stat().st_size
                    print(f"  {file_path.relative_to(claude_mpm_dir)} ({size} bytes)")

if __name__ == "__main__":
    main()