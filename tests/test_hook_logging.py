#!/usr/bin/env python3
"""Test script to verify project-specific hook logging."""

import json
import os
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_hook_logging():
    """Test hook logging with proper event format."""
    print("=== Testing Project-Specific Hook Logging ===")
    
    # Create test event in Claude Code format
    test_event = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "test-session-123",
        "cwd": str(Path.cwd()),  # Use current directory as project
        "prompt": "/mpm status test"
    }
    
    # Path to hook handler
    hook_handler_path = Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    
    print(f"Hook handler: {hook_handler_path}")
    print(f"Project directory: {test_event['cwd']}")
    print(f"Event: {json.dumps(test_event, indent=2)}")
    
    # Run the hook handler with event data
    env = os.environ.copy()
    env['CLAUDE_MPM_LOG_LEVEL'] = 'DEBUG'
    env['PYTHONPATH'] = str(Path(__file__).parent.parent / "src")
    
    result = subprocess.run(
        [sys.executable, str(hook_handler_path)],
        input=json.dumps(test_event),
        capture_output=True,
        text=True,
        env=env
    )
    
    print(f"\nExit code: {result.returncode}")
    if result.stdout:
        print(f"Stdout: {result.stdout}")
    if result.stderr:
        print(f"Stderr: {result.stderr}")
    
    # Check for project-specific log files
    project_log_dir = Path(test_event['cwd']) / ".claude-mpm" / "logs"
    print(f"\nChecking for logs in: {project_log_dir}")
    
    if project_log_dir.exists():
        log_files = list(project_log_dir.glob("hooks_*.log"))
        if log_files:
            print(f"Found {len(log_files)} hook log file(s):")
            for log_file in sorted(log_files):
                print(f"\n--- {log_file.name} ---")
                with open(log_file) as f:
                    print(f.read())
        else:
            print("No hook log files found")
    else:
        print(f"Project log directory doesn't exist: {project_log_dir}")
    
    # Also test PreToolUse and PostToolUse
    print("\n=== Testing PreToolUse ===")
    pre_event = {
        "hook_event_name": "PreToolUse", 
        "session_id": "test-session-123",
        "cwd": str(Path.cwd()),
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/test.txt"}
    }
    
    result = subprocess.run(
        [sys.executable, str(hook_handler_path)],
        input=json.dumps(pre_event),
        capture_output=True,
        text=True,
        env=env
    )
    print(f"PreToolUse exit code: {result.returncode}")
    
    print("\n=== Testing PostToolUse ===")
    post_event = {
        "hook_event_name": "PostToolUse",
        "session_id": "test-session-123", 
        "cwd": str(Path.cwd()),
        "tool_name": "Read",
        "tool_output": "File contents here...",
        "exit_code": 0
    }
    
    result = subprocess.run(
        [sys.executable, str(hook_handler_path)],
        input=json.dumps(post_event),
        capture_output=True,
        text=True,
        env=env
    )
    print(f"PostToolUse exit code: {result.returncode}")
    
    print("\n=== Testing Stop ===")
    stop_event = {
        "hook_event_name": "Stop",
        "session_id": "test-session-123",
        "cwd": str(Path.cwd()),
        "reason": "user_request"
    }
    
    result = subprocess.run(
        [sys.executable, str(hook_handler_path)],
        input=json.dumps(stop_event),
        capture_output=True,
        text=True,
        env=env
    )
    print(f"Stop exit code: {result.returncode}")
    
    print("\n=== Testing SubagentStop ===")
    subagent_event = {
        "hook_event_name": "SubagentStop",
        "session_id": "test-session-123",
        "cwd": str(Path.cwd()),
        "agent_type": "research",
        "agent_id": "research-001",
        "reason": "task_complete"
    }
    
    result = subprocess.run(
        [sys.executable, str(hook_handler_path)],
        input=json.dumps(subagent_event),
        capture_output=True,
        text=True,
        env=env
    )
    print(f"SubagentStop exit code: {result.returncode}")
    
    # Check for updated log file
    print("\n=== Final Log Check ===")
    if project_log_dir.exists():
        log_files = list(project_log_dir.glob("hooks_*.log"))
        if log_files:
            print(f"\n--- {log_files[0].name} (last 20 lines) ---")
            with open(log_files[0]) as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.rstrip())

if __name__ == "__main__":
    test_hook_logging()