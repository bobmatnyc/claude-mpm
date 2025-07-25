#!/usr/bin/env python3
"""
Test script to demonstrate enhanced subprocess logging capabilities.
"""

import logging
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.utils.subprocess_runner import SubprocessRunner
from claude_mpm.utils.enhanced_subprocess_runner import EnhancedSubprocessRunner
from claude_mpm.utils.process import ProcessManager
from claude_mpm.utils.output import OutputFormatter
from claude_mpm.utils.terminal import TerminalManager


def setup_logging():
    """Set up comprehensive logging for testing."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/tmp/subprocess_logging_test.log')
        ]
    )


def test_subprocess_runner():
    """Test basic subprocess runner with logging."""
    print("\n=== Testing SubprocessRunner ===")
    
    runner = SubprocessRunner()
    
    # Test successful command
    result = runner.run(['echo', 'Hello, World!'])
    print(f"Success: {result.success}, Output: {result.stdout.strip()}")
    
    # Test command with error
    result = runner.run(['ls', '/nonexistent'])
    print(f"Success: {result.success}, Error output: {result.stderr.strip()}")
    
    # Test timeout
    result = runner.run_with_timeout(['sleep', '5'], timeout=1)
    print(f"Timed out: {result.timed_out}")


def test_enhanced_runner():
    """Test enhanced subprocess runner."""
    print("\n=== Testing EnhancedSubprocessRunner ===")
    
    runner = EnhancedSubprocessRunner()
    
    # Run multiple commands
    commands = [
        ['echo', 'Test 1'],
        ['python', '-c', 'print("Python output")'],
        ['ls', '-la'],
        ['cat', '/etc/hosts'],
        ['invalid-command'],
    ]
    
    for cmd in commands:
        try:
            result = runner.run(cmd)
            print(f"Command: {' '.join(cmd)} - Success: {result.success}")
        except Exception as e:
            print(f"Command: {' '.join(cmd)} - Error: {e}")
    
    # Get statistics
    stats = runner.get_statistics()
    print(f"\nStatistics: {stats}")


def test_process_manager():
    """Test process manager with lifecycle tracking."""
    print("\n=== Testing ProcessManager ===")
    
    manager = ProcessManager()
    
    # Spawn a process with comprehensive logging
    result = manager.spawn_process(
        ['python', '-c', 'import time; print("Starting"); time.sleep(1); print("Done")'],
        env={'CUSTOM_VAR': 'test_value', 'API_KEY': 'secret123'}
    )
    
    print(f"Process completed: {result.success}")
    
    # Test process tracking (if process is still running)
    import subprocess
    proc = subprocess.Popen(['sleep', '2'])
    manager.track_process(proc.pid, ['sleep', '2'], 0)
    
    # Monitor lifecycle
    lifecycle = manager.monitor_process_lifecycle(proc.pid)
    print(f"Lifecycle events: {len(lifecycle['events'])}")
    
    # Cleanup
    manager.terminate_process(proc.pid)


def test_output_formatter():
    """Test output formatter with logging."""
    print("\n=== Testing OutputFormatter ===")
    
    formatter = OutputFormatter()
    
    # Test terminal width detection
    width = formatter.get_terminal_width()
    print(f"Terminal width: {width}")
    
    # Test text formatting
    long_text = "This is a very long line that should be wrapped " * 10
    formatted = formatter.format_output(long_text, width=50, indent=4, prefix="> ")
    print(f"Formatted text:\n{formatted}")
    
    # Test progress bar
    bar_id = "test_progress"
    print("\nProgress bar test:")
    for i in range(11):
        bar = formatter.update_progress_bar(bar_id, i*10, 
                                          prefix="Processing: ",
                                          suffix=f" {i*10}%")
        print(f"\r{bar}", end='', flush=True)
        import time
        time.sleep(0.1)
    print()
    
    # Test table formatting
    headers = ["Name", "Value", "Status"]
    rows = [
        ["Process 1", "123", "Running"],
        ["Process 2", "456", "Completed"],
        ["Process 3", "789", "Failed"],
    ]
    table = formatter.format_table(headers, rows)
    print(f"\nFormatted table:\n{table}")


def test_terminal_manager():
    """Test terminal manager capabilities."""
    print("\n=== Testing TerminalManager ===")
    
    manager = TerminalManager()
    
    # Detect capabilities
    caps = manager.detect_capabilities()
    print(f"Terminal capabilities:")
    for key, value in caps.items():
        print(f"  {key}: {value}")
    
    # Get terminal size
    size = manager.get_terminal_size()
    print(f"\nTerminal size: {size[0]}x{size[1]}")
    
    # Test cursor operations (if supported)
    if caps.get('supports_cursor_control'):
        print("\nTesting cursor control...")
        manager.hide_cursor()
        import time
        time.sleep(1)
        manager.show_cursor()
        print("Cursor control test completed")


async def test_async_subprocess():
    """Test async subprocess execution."""
    print("\n=== Testing Async Subprocess ===")
    
    runner = EnhancedSubprocessRunner()
    
    # Run async command
    result = await runner.run_async(['echo', 'Async output'])
    print(f"Async result: {result.stdout.strip()}")
    
    # Run with timeout
    result = await runner.run_async(['sleep', '5'], timeout=1)
    print(f"Async timed out: {result.timed_out}")


def main():
    """Run all tests."""
    setup_logging()
    
    print("Starting subprocess logging tests...")
    print("Log file: /tmp/subprocess_logging_test.log")
    
    try:
        test_subprocess_runner()
        test_enhanced_runner()
        test_process_manager()
        test_output_formatter()
        test_terminal_manager()
        
        # Run async tests
        print("\nRunning async tests...")
        asyncio.run(test_async_subprocess())
        
    except Exception as e:
        logging.error(f"Test failed: {e}", exc_info=True)
        raise
    
    print("\nAll tests completed! Check the log file for detailed output.")


if __name__ == "__main__":
    main()