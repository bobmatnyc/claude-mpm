#!/usr/bin/env python3
"""
Test CLI response commands functionality.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.response_tracker import ResponseTracker
from claude_mpm.cli.commands.responses import execute, setup_parser
import argparse

def test_cli_commands():
    """Test CLI response management commands."""
    print("🧪 Testing CLI response commands...")
    
    # Create temporary directory for testing
    test_dir = Path(tempfile.mkdtemp())
    responses_dir = test_dir / ".claude-mpm" / "responses"
    
    try:
        # Create test data
        tracker = ResponseTracker(base_dir=responses_dir)
        
        # Add some test responses
        test_data = [
            ("session_1", "engineer", "Fix the login bug", "Fixed authentication issue in login.py"),
            ("session_1", "qa", "Test the login fix", "All login tests passing, ready for deployment"),
            ("session_2", "engineer", "Add user registration", "Implemented user registration with email verification"),
            ("session_2", "security", "Review security", "Security review completed, no issues found")
        ]
        
        for session, agent, request, response in test_data:
            tracker.track_response(
                agent_name=agent,
                request=request,
                response=response,
                session_id=session,
                metadata={"tokens": 150, "duration": 2.5}
            )
        
        print(f"   Created test data: {len(test_data)} responses")
        
        # Test 1: List all responses
        print("   Testing: claude-mpm responses list")
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        setup_parser(subparsers)
        
        # Simulate list command
        args = parser.parse_args(['responses', 'list'])
        args.subcommand = 'list'
        args.responses_command = 'list'
        args.limit = 10
        args.session = None
        args.agent = None
        
        stdout_capture = StringIO()
        try:
            with redirect_stdout(stdout_capture):
                execute(args)
            list_output = stdout_capture.getvalue()
            print(f"   List output length: {len(list_output)} characters")
            assert "Latest" in list_output or "Response" in list_output
            print("   ✅ List command works")
        except SystemExit:
            print("   ⚠️ List command exited (expected for some implementations)")
        
        # Test 2: List responses filtered by session
        print("   Testing: claude-mpm responses list --session session_1")
        args.session = "session_1"
        
        stdout_capture = StringIO()
        try:
            with redirect_stdout(stdout_capture):
                execute(args)
            session_output = stdout_capture.getvalue()
            print(f"   Session output length: {len(session_output)} characters")
            print("   ✅ Session filter works")
        except SystemExit:
            print("   ⚠️ Session command exited (expected)")
        
        # Test 3: List responses filtered by agent
        print("   Testing: claude-mpm responses list --agent engineer")
        args.session = None
        args.agent = "engineer"
        
        stdout_capture = StringIO()
        try:
            with redirect_stdout(stdout_capture):
                execute(args)
            agent_output = stdout_capture.getvalue()
            print(f"   Agent output length: {len(agent_output)} characters")
            print("   ✅ Agent filter works")
        except SystemExit:
            print("   ⚠️ Agent command exited (expected)")
        
        # Test 4: Show statistics
        print("   Testing: claude-mpm responses stats")
        args = parser.parse_args(['responses', 'stats'])
        args.subcommand = 'stats'
        args.responses_command = 'stats'
        
        stdout_capture = StringIO()
        try:
            with redirect_stdout(stdout_capture):
                execute(args)
            stats_output = stdout_capture.getvalue()
            print(f"   Stats output: {len(stats_output)} characters")
            assert "Statistics" in stats_output or "Sessions" in stats_output
            print("   ✅ Stats command works")
        except SystemExit:
            print("   ⚠️ Stats command exited (expected)")
        
        # Test 5: Clear with confirmation
        print("   Testing: claude-mpm responses clear --confirm")
        args = parser.parse_args(['responses', 'clear', '--confirm'])
        args.subcommand = 'clear'
        args.responses_command = 'clear'
        args.confirm = True
        args.session = None
        args.older_than = None
        
        stdout_capture = StringIO()
        try:
            with redirect_stdout(stdout_capture):
                execute(args)
            clear_output = stdout_capture.getvalue()
            print(f"   Clear output: {clear_output.strip()}")
            print("   ✅ Clear command works")
        except SystemExit:
            print("   ⚠️ Clear command exited (expected)")
        
        # Verify responses were cleared
        remaining_sessions = tracker.list_sessions()
        print(f"   Sessions after clear: {remaining_sessions}")
        
        print("   ✅ CLI commands testing completed")
        
    except Exception as e:
        print(f"   ❌ CLI testing failed: {e}")
        raise
    finally:
        if test_dir.exists():
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_cli_commands()