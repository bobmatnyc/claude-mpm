#!/usr/bin/env python3
"""
Subprocess Improvements Demo for claude-mpm

This script demonstrates the subprocess improvements implemented in the
feat/subprocess-improvements-demo branch, showcasing:

1. Unified subprocess handling via SubprocessRunner utility
2. Enhanced timeout handling with graceful termination
3. Comprehensive error handling and recovery
4. Integration with ClaudeLauncher for Claude-specific operations
5. Async subprocess execution capabilities
6. Context manager for managed processes

The improvements significantly reduce code duplication across the codebase
by providing a consistent interface for all subprocess operations.
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

# Add the src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.utils.subprocess_runner import (
    SubprocessRunner, 
    SubprocessResult,
    OutputMode,
    quick_run,
    quick_run_with_timeout,
    quick_run_async
)
from claude_mpm.core.claude_launcher import ClaudeLauncher, LaunchMode
from claude_mpm.core.logger import get_logger


# Set up logging for the demo
logger = get_logger("subprocess_demo")


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")


def print_result(result: SubprocessResult):
    """Print subprocess result in a formatted way."""
    print(f"Command: {' '.join(result.command)}")
    print(f"Return code: {result.returncode}")
    print(f"Execution time: {result.execution_time:.2f}s")
    print(f"Success: {result.success}")
    if result.timed_out:
        print("⏱️  Command timed out!")
    if result.error:
        print(f"❌ Error: {result.error}")
    if result.stdout:
        print(f"📤 Stdout:\n{result.stdout}")
    if result.stderr:
        print(f"📥 Stderr:\n{result.stderr}")
    print()


def demo_basic_subprocess():
    """Demonstrate basic subprocess execution."""
    print_section("1. Basic Subprocess Execution")
    
    # Create a SubprocessRunner instance
    runner = SubprocessRunner()
    
    # Example 1: Simple command
    print("Example 1: List current directory")
    result = runner.run(['ls', '-la'])
    print_result(result)
    
    # Example 2: Command with environment variables
    print("\nExample 2: Echo with custom environment")
    custom_env = {'DEMO_VAR': 'Hello from subprocess!'}
    result = runner.run(
        ['bash', '-c', 'echo "DEMO_VAR=$DEMO_VAR"'], 
        env=custom_env
    )
    print_result(result)
    
    # Example 3: Working directory change
    print("\nExample 3: Run command in different directory")
    result = runner.run(['pwd'], cwd='/tmp')
    print_result(result)
    
    # Example 4: Quick run convenience function
    print("\nExample 4: Using quick_run convenience function")
    result = quick_run(['echo', 'Quick and easy!'])
    print_result(result)


def demo_timeout_handling():
    """Demonstrate timeout handling improvements."""
    print_section("2. Timeout Handling Improvements")
    
    runner = SubprocessRunner()
    
    # Example 1: Command that completes before timeout
    print("Example 1: Command completes within timeout")
    result = runner.run_with_timeout(['sleep', '1'], timeout=2.0)
    print_result(result)
    
    # Example 2: Command that times out
    print("\nExample 2: Command exceeds timeout (graceful termination)")
    result = runner.run_with_timeout(['sleep', '5'], timeout=2.0)
    print_result(result)
    
    # Example 3: Using quick timeout function
    print("\nExample 3: Quick timeout function")
    result = quick_run_with_timeout(
        ['bash', '-c', 'echo "Starting..."; sleep 3; echo "Done!"'], 
        timeout=1.0
    )
    print_result(result)


def demo_error_handling():
    """Demonstrate enhanced error handling."""
    print_section("3. Enhanced Error Handling")
    
    runner = SubprocessRunner()
    
    # Example 1: Non-existent command
    print("Example 1: Non-existent command")
    result = runner.run(['this-command-does-not-exist'])
    print_result(result)
    
    # Example 2: Command that returns non-zero exit code
    print("\nExample 2: Command with non-zero exit code")
    result = runner.run(['bash', '-c', 'exit 42'])
    print_result(result)
    
    # Example 3: Command with stderr output
    print("\nExample 3: Command with stderr output")
    result = runner.run(['bash', '-c', 'echo "Error!" >&2; exit 1'])
    print_result(result)


def demo_output_modes():
    """Demonstrate different output capture modes."""
    print_section("4. Output Capture Modes")
    
    runner = SubprocessRunner()
    
    # Create a command that produces both stdout and stderr
    test_command = [
        'bash', '-c', 
        'echo "This is stdout"; echo "This is stderr" >&2'
    ]
    
    # Example 1: Separate output (default)
    print("Example 1: Separate stdout and stderr")
    result = runner.capture_output(test_command, mode=OutputMode.SEPARATE)
    print_result(result)
    
    # Example 2: Combined output
    print("\nExample 2: Combined output")
    result = runner.capture_output(test_command, mode=OutputMode.COMBINED)
    print_result(result)
    
    # Example 3: Stdout only
    print("\nExample 3: Stdout only")
    result = runner.capture_output(test_command, mode=OutputMode.STDOUT_ONLY)
    print_result(result)
    
    # Example 4: Stderr only
    print("\nExample 4: Stderr only")
    result = runner.capture_output(test_command, mode=OutputMode.STDERR_ONLY)
    print_result(result)


async def demo_async_execution():
    """Demonstrate asynchronous subprocess execution."""
    print_section("5. Asynchronous Subprocess Execution")
    
    runner = SubprocessRunner()
    
    # Example 1: Single async command
    print("Example 1: Single async command")
    result = await runner.run_async(['echo', 'Async execution!'])
    print_result(result)
    
    # Example 2: Multiple async commands in parallel
    print("\nExample 2: Parallel async execution")
    start_time = time.time()
    
    # Run three sleep commands in parallel
    tasks = [
        runner.run_async(['bash', '-c', f'sleep 1; echo "Task {i} complete"'])
        for i in range(1, 4)
    ]
    
    results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    print(f"Total execution time: {total_time:.2f}s (should be ~1s, not 3s)")
    
    for i, result in enumerate(results, 1):
        print(f"\nTask {i} result:")
        print_result(result)
    
    # Example 3: Async with timeout
    print("\nExample 3: Async execution with timeout")
    result = await runner.run_async(['sleep', '5'], timeout=2.0)
    print_result(result)
    
    # Example 4: Quick async function
    print("\nExample 4: Quick async function")
    result = await quick_run_async(['echo', 'Quick async!'])
    print_result(result)


def demo_managed_process():
    """Demonstrate managed process context manager."""
    print_section("6. Managed Process Context Manager")
    
    runner = SubprocessRunner()
    
    # Example 1: Interactive process management
    print("Example 1: Managed process with automatic cleanup")
    
    try:
        with runner.managed_process(
            ['bash', '-c', 'for i in {1..5}; do echo "Line $i"; sleep 0.5; done'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        ) as proc:
            # Read a few lines
            for i in range(3):
                line = proc.stdout.readline()
                print(f"Read: {line.strip()}")
            
            print("Exiting context (process will be terminated)...")
            # Process will be automatically terminated when exiting the context
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nProcess terminated gracefully!")


def demo_claude_launcher_integration():
    """Demonstrate ClaudeLauncher integration with subprocess improvements."""
    print_section("7. ClaudeLauncher Integration")
    
    try:
        # Initialize ClaudeLauncher
        launcher = ClaudeLauncher(model="opus", skip_permissions=True)
        
        print("ClaudeLauncher initialized successfully!")
        print(f"Claude executable found at: {launcher.claude_path}")
        
        # Example 1: Build command for different modes
        print("\nExample 1: Command building for different modes")
        
        interactive_cmd = launcher.build_command(mode=LaunchMode.INTERACTIVE)
        print(f"Interactive mode: {' '.join(interactive_cmd)}")
        
        print_cmd = launcher.build_command(mode=LaunchMode.PRINT)
        print(f"Print mode: {' '.join(print_cmd)}")
        
        system_prompt_cmd = launcher.build_command(
            mode=LaunchMode.SYSTEM_PROMPT,
            system_prompt="You are a helpful assistant."
        )
        print(f"System prompt mode: {' '.join(system_prompt_cmd)}")
        
        # Example 2: One-shot execution with timeout
        print("\nExample 2: One-shot Claude execution with timeout")
        print("(Note: This requires Claude CLI to be installed)")
        
        # This would actually call Claude if installed
        # For demo purposes, we'll show the pattern
        print("Pattern: launcher.launch_oneshot('Hello Claude!', timeout=30)")
        print("This would send a message to Claude and return the response")
        
    except RuntimeError as e:
        print(f"⚠️  Claude CLI not found: {e}")
        print("Install Claude CLI to see full integration")


def demo_shell_execution():
    """Demonstrate shell command execution (with security warnings)."""
    print_section("8. Shell Command Execution")
    
    runner = SubprocessRunner()
    
    print("⚠️  WARNING: Shell execution can be a security risk!")
    print("Only use with trusted input!\n")
    
    # Example: Safe shell command
    print("Example: Complex shell pipeline (safe)")
    result = runner.run_shell(
        'echo "Hello World" | tr "[:lower:]" "[:upper:]" | sed "s/WORLD/SUBPROCESS/"'
    )
    print_result(result)


def demo_real_world_patterns():
    """Demonstrate real-world usage patterns from the codebase."""
    print_section("9. Real-World Usage Patterns")
    
    runner = SubprocessRunner()
    
    # Pattern 1: Git operations (common in version control agent)
    print("Pattern 1: Git operations with error handling")
    result = runner.run(['git', 'status', '--porcelain'])
    if result.success:
        if result.stdout.strip():
            print("Working directory has changes:")
            print(result.stdout)
        else:
            print("Working directory is clean")
    else:
        print(f"Git command failed: {result.stderr}")
    
    # Pattern 2: Python script execution (common in testing)
    print("\nPattern 2: Python script execution")
    result = runner.run([
        sys.executable, '-c', 
        'import sys; print(f"Python {sys.version.split()[0]}")'
    ])
    print_result(result)
    
    # Pattern 3: npm operations (common in deployment)
    print("\nPattern 3: Package manager operations")
    result = runner.run_with_timeout(['npm', '--version'], timeout=5.0)
    if result.success:
        print(f"npm version: {result.stdout.strip()}")
    else:
        print("npm not found or command failed")
    
    # Pattern 4: Health checks with retries
    print("\nPattern 4: Health check with retry pattern")
    max_retries = 3
    for attempt in range(max_retries):
        result = runner.run_with_timeout(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 'http://localhost:8080'],
            timeout=2.0
        )
        if result.success and result.stdout.strip() == '200':
            print(f"Health check passed on attempt {attempt + 1}")
            break
        else:
            print(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(1)


def main():
    """Run all demonstrations."""
    print("🚀 Claude-MPM Subprocess Improvements Demo")
    print("==========================================")
    print("This demo showcases the subprocess improvements that reduce")
    print("code duplication and provide consistent error handling.\n")
    
    # Run synchronous demos
    demo_basic_subprocess()
    demo_timeout_handling()
    demo_error_handling()
    demo_output_modes()
    demo_shell_execution()
    demo_real_world_patterns()
    
    # Run async demos
    print("\n" + "="*60)
    print(" Running Async Demonstrations")
    print("="*60)
    asyncio.run(demo_async_execution())
    
    # Managed process demo
    demo_managed_process()
    
    # Claude launcher integration
    demo_claude_launcher_integration()
    
    print("\n✅ Demo completed successfully!")
    print("\nKey Improvements Demonstrated:")
    print("1. Unified subprocess interface via SubprocessRunner")
    print("2. Consistent timeout handling across all operations")
    print("3. Comprehensive error handling and recovery")
    print("4. Multiple output capture modes for flexibility")
    print("5. Async subprocess support for parallel execution")
    print("6. Context managers for resource management")
    print("7. Integration with ClaudeLauncher for Claude operations")
    print("8. Real-world patterns from the codebase")


if __name__ == "__main__":
    main()