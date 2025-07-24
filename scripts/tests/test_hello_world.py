#!/usr/bin/env python3
"""Test hello world with claude-mpm to verify prompt injection."""

import subprocess
import sys
import os
from pathlib import Path
import time

def main():
    """Run claude-mpm with hello world prompt and log everything."""
    
    print("=== Claude MPM Hello World Test ===\n")
    
    # Set up paths
    test_dir = Path.cwd()  # Use current working directory for test
    claude_mpm_path = Path(__file__).parent.parent.parent
    run_script = claude_mpm_path / "scripts" / "run_mpm.py"
    
    # Create prompt file
    prompt_file = test_dir / "hello_prompt.txt"
    prompt_file.write_text("Please respond with exactly 'Hello World' and nothing else.")
    
    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = str(claude_mpm_path / "src")
    env["CLAUDE_MPM_DEBUG"] = "1"
    
    # Run claude-mpm
    print(f"Running: python {run_script} --debug run")
    print(f"Working directory: {test_dir}")
    print(f"Prompt: {prompt_file.read_text()}")
    print("-" * 60)
    
    # Start the process
    process = subprocess.Popen(
        [sys.executable, str(run_script), "--debug", "run"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(test_dir),
        env=env
    )
    
    # Send the prompt
    stdout, _ = process.communicate(input=prompt_file.read_text())
    
    # Print output
    print("\n=== Output ===")
    print(stdout)
    
    # Check for prompt logs
    prompt_log_dir = Path.home() / ".claude-mpm" / "prompts"
    if prompt_log_dir.exists():
        print("\n=== Saved Prompts ===")
        for prompt_log in sorted(prompt_log_dir.glob("prompt_*.txt")):
            print(f"\nPrompt file: {prompt_log.name}")
            print(f"Size: {prompt_log.stat().st_size} bytes")
            print("First 500 chars:")
            print("-" * 40)
            print(prompt_log.read_text()[:500] + "...")
            print("-" * 40)
    else:
        print("\nNo prompt logs found at:", prompt_log_dir)
    
    # Check session logs
    session_log_dir = Path.home() / ".claude-mpm" / "sessions"
    if session_log_dir.exists():
        print("\n=== Session Logs ===")
        for session_log in sorted(session_log_dir.glob("session_*.json")):
            print(f"Session log: {session_log.name}")

if __name__ == "__main__":
    main()