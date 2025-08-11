#!/usr/bin/env python3
"""
Test CLI Session Logging with Real Commands

Test session logging integration with actual claude-mpm CLI commands.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime


def clear_session_env_vars():
    """Clear all session-related environment variables."""
    env_vars = ['CLAUDE_SESSION_ID', 'ANTHROPIC_SESSION_ID', 'SESSION_ID']
    for var in env_vars:
        if var in os.environ:
            del os.environ[var]


def run_claude_mpm_command(command, session_id=None, timeout=30):
    """Run a claude-mpm command with optional session ID."""
    clear_session_env_vars()
    
    # Prepare environment
    env = os.environ.copy()
    if session_id:
        env['CLAUDE_SESSION_ID'] = session_id
    
    # Run command
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=Path.cwd()
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Command timed out',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -2
        }


def test_version_command():
    """Test version command with session logging."""
    print("Testing version command with session logging")
    print("-" * 50)
    
    session_id = f"cli_version_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run version command
    result = run_claude_mpm_command("./claude-mpm --version", session_id)
    
    print(f"Session ID: {session_id}")
    print(f"Command success: {'✓' if result['success'] else '✗'}")
    print(f"Output: {result['stdout'].strip()}")
    
    if result['stderr']:
        print(f"Errors: {result['stderr']}")
    
    # Check if session directory was created (might not be for simple commands)
    session_dir = Path.cwd() / "docs" / "responses" / session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"Responses logged: {len(files)}")
    else:
        print("No session directory created (expected for version command)")
    
    print()


def test_help_command():
    """Test help command with session logging."""
    print("Testing help command with session logging")
    print("-" * 50)
    
    session_id = f"cli_help_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run help command
    result = run_claude_mpm_command("./claude-mpm --help", session_id)
    
    print(f"Session ID: {session_id}")
    print(f"Command success: {'✓' if result['success'] else '✗'}")
    print(f"Output length: {len(result['stdout'])} chars")
    
    if result['stderr']:
        print(f"Errors: {result['stderr']}")
    
    # Check for session logging
    session_dir = Path.cwd() / "docs" / "responses" / session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"Responses logged: {len(files)}")
    else:
        print("No session directory created (expected for help command)")
    
    print()


def test_run_command_simple():
    """Test run command with a simple instruction."""
    print("Testing run command with simple instruction and session logging")
    print("-" * 60)
    
    session_id = f"cli_run_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run a simple command
    instruction = "List the files in the current directory"
    command = f'./claude-mpm run -i "{instruction}" --non-interactive'
    
    print(f"Session ID: {session_id}")
    print(f"Command: {command}")
    
    result = run_claude_mpm_command(command, session_id, timeout=60)
    
    print(f"Command success: {'✓' if result['success'] else '✗'}")
    print(f"Return code: {result['returncode']}")
    
    if result['stdout']:
        print(f"Output length: {len(result['stdout'])} chars")
        print("Output preview:")
        print(result['stdout'][:200] + "..." if len(result['stdout']) > 200 else result['stdout'])
    
    if result['stderr']:
        print(f"Errors: {result['stderr']}")
    
    # Check for session logging
    session_dir = Path.cwd() / "docs" / "responses" / session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"Responses logged: {len(files)}")
        
        if files:
            # Examine the first response
            with open(files[0], 'r') as f:
                data = json.load(f)
                agent = data['metadata'].get('agent', 'unknown')
                request_summary = data['request_summary']
                response_length = len(data['response'])
                
                print(f"First response:")
                print(f"  Agent: {agent}")
                print(f"  Request: {request_summary[:60]}...")
                print(f"  Response length: {response_length} chars")
    else:
        print("No session directory created")
    
    print()


def test_agents_command():
    """Test agents command with session logging."""
    print("Testing agents command with session logging")
    print("-" * 50)
    
    session_id = f"cli_agents_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run agents command
    command = "./claude-mpm agents"
    result = run_claude_mpm_command(command, session_id)
    
    print(f"Session ID: {session_id}")
    print(f"Command success: {'✓' if result['success'] else '✗'}")
    
    if result['stdout']:
        print(f"Output length: {len(result['stdout'])} chars")
    
    if result['stderr']:
        print(f"Errors: {result['stderr']}")
    
    # Check for session logging
    session_dir = Path.cwd() / "docs" / "responses" / session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"Responses logged: {len(files)}")
    else:
        print("No session directory created (expected for agents command)")
    
    print()


def test_session_persistence():
    """Test session persistence across multiple commands."""
    print("Testing session persistence across multiple commands")
    print("-" * 60)
    
    session_id = f"cli_persistence_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    commands = [
        "./claude-mpm --version",
        "./claude-mpm --help",
        "./claude-mpm agents"
    ]
    
    print(f"Persistent session ID: {session_id}")
    
    for i, command in enumerate(commands, 1):
        print(f"\nCommand {i}: {command}")
        result = run_claude_mpm_command(command, session_id)
        
        print(f"  Success: {'✓' if result['success'] else '✗'}")
        
        # Small delay between commands
        time.sleep(1)
    
    # Check final session directory
    session_dir = Path.cwd() / "docs" / "responses" / session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"\nTotal responses logged across all commands: {len(files)}")
        
        for file in files:
            print(f"  {file.name}")
    else:
        print("\nNo persistent session directory found")
    
    print()


def test_no_session_id():
    """Test CLI commands without session ID (should use fallback)."""
    print("Testing CLI commands without session ID (fallback behavior)")
    print("-" * 60)
    
    clear_session_env_vars()
    
    # Run command without session ID
    command = "./claude-mpm --version"
    result = run_claude_mpm_command(command, session_id=None)
    
    print(f"Command without session ID: {command}")
    print(f"Command success: {'✓' if result['success'] else '✗'}")
    
    # Check if any session directories were created with timestamp pattern
    responses_dir = Path.cwd() / "docs" / "responses"
    if responses_dir.exists():
        # Look for recent timestamp-based sessions
        now = datetime.now()
        recent_sessions = []
        
        for session_dir in responses_dir.iterdir():
            if session_dir.is_dir() and session_dir.name.startswith('session_'):
                # Parse timestamp from directory name
                try:
                    timestamp_str = session_dir.name.replace('session_', '')
                    session_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    
                    # Check if created within last minute
                    if (now - session_time).total_seconds() < 60:
                        recent_sessions.append(session_dir.name)
                except ValueError:
                    continue
        
        if recent_sessions:
            print(f"Fallback sessions created: {recent_sessions}")
        else:
            print("No fallback sessions created (expected for version command)")
    else:
        print("No responses directory found")
    
    print()


def test_error_handling():
    """Test error handling in CLI with session logging."""
    print("Testing error handling in CLI with session logging")
    print("-" * 60)
    
    session_id = f"cli_error_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run an invalid command
    command = "./claude-mpm invalid-command-that-does-not-exist"
    result = run_claude_mpm_command(command, session_id)
    
    print(f"Session ID: {session_id}")
    print(f"Invalid command: {command}")
    print(f"Command failed (expected): {'✓' if not result['success'] else '✗'}")
    print(f"Return code: {result['returncode']}")
    
    if result['stderr']:
        print(f"Error message: {result['stderr'].strip()}")
    
    # Check if session directory was created despite error
    session_dir = Path.cwd() / "docs" / "responses" / session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"Responses logged despite error: {len(files)}")
    else:
        print("No session directory created for error case (expected)")
    
    print()


if __name__ == "__main__":
    print("CLI Session Logging Real Commands Test")
    print("=" * 70)
    
    # Make sure we're in the right directory
    if not Path("./claude-mpm").exists():
        print("ERROR: claude-mpm script not found in current directory")
        sys.exit(1)
    
    test_version_command()
    test_help_command()
    test_agents_command()
    test_session_persistence()
    test_no_session_id()
    test_error_handling()
    
    # Note: Commented out the run command test as it may take longer
    # and require actual agent processing
    # test_run_command_simple()
    
    print("=" * 70)
    print("CLI real commands test complete!")
    print("Note: Most CLI commands may not trigger session logging")
    print("      as they don't involve agent responses.")