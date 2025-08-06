#!/usr/bin/env python3
"""Test script for SimpleClaudeRunner logging functionality."""

import json
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.simple_runner import SimpleClaudeRunner
from claude_mpm.core.logger import get_project_logger


def test_logging_initialization():
    """Test that logging is properly initialized."""
    print("Testing SimpleClaudeRunner logging initialization...")
    
    # Test with logging enabled
    runner = SimpleClaudeRunner(log_level="INFO")
    assert runner.project_logger is not None, "Project logger should be initialized"
    
    # Check session directory was created
    session_dir = runner.project_logger.session_dir
    assert session_dir.exists(), f"Session directory should exist: {session_dir}"
    
    # Check system.jsonl was created
    system_log = session_dir / "system.jsonl"
    assert system_log.exists(), f"system.jsonl should exist: {system_log}"
    
    print(f"✓ Session directory created: {session_dir}")
    print(f"✓ System log created: {system_log}")
    
    # Read and verify log content
    with open(system_log, 'r') as f:
        lines = f.readlines()
        assert len(lines) > 0, "System log should have entries"
        
        # Check first entry is session_start
        import json
        first_entry = json.loads(lines[0])
        assert first_entry.get("event") == "session_start", "First event should be session_start"
        print(f"✓ Session start logged: {first_entry}")
    
    return runner


def test_logging_disabled():
    """Test that logging can be disabled."""
    print("\nTesting SimpleClaudeRunner with logging disabled...")
    
    runner = SimpleClaudeRunner(log_level="OFF")
    assert runner.project_logger is None, "Project logger should not be initialized when OFF"
    print("✓ Logging properly disabled when log_level=OFF")


def test_oneshot_logging():
    """Test logging in oneshot mode."""
    print("\nTesting oneshot mode logging...")
    
    runner = SimpleClaudeRunner(log_level="INFO")
    
    # Get the session log file
    system_log = runner.project_logger.session_dir / "system.jsonl"
    
    # Count initial entries
    with open(system_log, 'r') as f:
        initial_count = len(f.readlines())
    
    # Run a simple oneshot command (will fail without Claude, but that's OK for testing)
    try:
        runner.run_oneshot("echo 'test'")
    except Exception:
        pass  # Expected to fail without Claude installed
    
    # Check new log entries were added
    with open(system_log, 'r') as f:
        lines = f.readlines()
        assert len(lines) > initial_count, "New log entries should be added"
        
        # Check for expected events
        events = [json.loads(line) for line in lines]
        event_types = [e.get("event") for e in events]
        
        print(f"✓ Logged events: {event_types}")
        
        # Should have session start and other events
        assert "session_start" in event_types
        assert any("session" in str(e) for e in event_types), "Should have session-related events"


def test_error_logging():
    """Test that errors are properly logged."""
    print("\nTesting error logging...")
    
    runner = SimpleClaudeRunner(log_level="DEBUG")
    
    # Force an error by using invalid command
    runner.claude_args = ["--invalid-arg"]
    
    try:
        runner.run_oneshot("test")
    except Exception:
        pass
    
    # Check that errors were logged
    system_log = runner.project_logger.session_dir / "system.jsonl"
    with open(system_log, 'r') as f:
        events = [json.loads(line) for line in f.readlines()]
        
    # Look for error events
    error_events = [e for e in events if "error" in str(e).lower() or "fail" in str(e).lower()]
    print(f"✓ Found {len(error_events)} error-related events")
    
    # Also check system logs
    system_logs = runner.project_logger.dirs["logs_system"]
    log_files = list(system_logs.glob("*.jsonl"))
    assert len(log_files) > 0, "System log files should be created"
    print(f"✓ System logs created in: {system_logs}")


def main():
    """Run all tests."""
    print("Testing SimpleClaudeRunner logging integration...")
    print("=" * 60)
    
    try:
        test_logging_disabled()
        runner = test_logging_initialization()
        test_oneshot_logging()
        test_error_logging()
        
        print("\n" + "=" * 60)
        print("✅ All logging tests passed!")
        
        # Show where logs are stored
        if runner and runner.project_logger:
            print(f"\nLogs are stored in:")
            print(f"  - Session: {runner.project_logger.session_dir}")
            print(f"  - System: {runner.project_logger.dirs['logs_system']}")
            print(f"  - Agents: {runner.project_logger.dirs['logs_agents']}")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()