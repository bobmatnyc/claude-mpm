#!/usr/bin/env python3
"""
Test script for the interactive subprocess orchestrator.

This script tests the new InteractiveSubprocessOrchestrator by:
1. Creating an orchestrator instance
2. Sending a prompt that should trigger delegations
3. Verifying subprocess creation and parallel execution
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.orchestration.interactive_subprocess_orchestrator import InteractiveSubprocessOrchestrator
import logging

def test_basic_orchestration():
    """Test basic orchestration with a simple delegation."""
    print("=== Testing Interactive Subprocess Orchestrator ===\n")
    
    # Create orchestrator with INFO logging
    orchestrator = InteractiveSubprocessOrchestrator(log_level="INFO")
    
    # Test prompt that should trigger delegations
    test_prompt = """
    Create a Python function that calculates the factorial of a number,
    write comprehensive tests for it, and document it properly.
    """
    
    print(f"Test prompt: {test_prompt}\n")
    
    try:
        # Run orchestrated session
        orchestrator.run_orchestrated_session(test_prompt)
        
        # Get final status
        status = orchestrator.get_status()
        print("\n=== Final Status ===")
        print(f"Session start: {status['session_start']}")
        print(f"Active processes: {len(status['active_processes'])}")
        print(f"Extracted tickets: {len(status['extracted_tickets'])}")
        
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()

def test_delegation_detection():
    """Test delegation detection patterns."""
    print("\n=== Testing Delegation Detection ===\n")
    
    orchestrator = InteractiveSubprocessOrchestrator(log_level="WARNING")
    
    # Test various delegation patterns
    test_responses = [
        # Pattern 1: **Agent**: task
        """I'll help you with that. Let me delegate this to the appropriate agents.

**Engineer**: Create a factorial function in Python with proper error handling
**QA Agent**: Write comprehensive unit tests for the factorial function
**Documentation**: Generate detailed documentation for the factorial function""",
        
        # Pattern 2: Task Tool → Agent
        """I'll coordinate multiple agents for this task.

Task Tool → Engineer Agent: Implement the factorial function
Task Tool → QA: Create test cases
Task Tool → Documentation Agent: Write API documentation""",
        
        # Mixed patterns
        """Let me break this down:

**Engineer Agent**: Implement factorial calculation
Task Tool → QA Agent: Validate implementation with tests

Additional work:
**Documentation**: Create user guide"""
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"Test case {i}:")
        delegations = orchestrator.detect_delegations(response)
        print(f"  Found {len(delegations)} delegations:")
        for d in delegations:
            print(f"    - {d['agent']}: {d['task'][:50]}...")
        print()

def test_process_management():
    """Test process management capabilities."""
    print("\n=== Testing Process Management ===\n")
    
    orchestrator = InteractiveSubprocessOrchestrator(log_level="INFO")
    
    # Test creating a subprocess directly
    result = orchestrator.run_agent_subprocess(
        agent="Engineer",
        task="Write a simple hello world function",
        context={"language": "Python"},
        timeout=30,
        memory_limit_mb=512
    )
    
    print(f"Execution result:")
    print(f"  Success: {result.success}")
    print(f"  Agent: {result.agent_type}")
    print(f"  Execution time: {result.execution_time:.2f}s")
    print(f"  Memory usage: {result.memory_usage}")
    print(f"  Exit code: {result.exit_code}")
    
    if result.stdout:
        print(f"\nAgent response preview:")
        print(result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)

def test_parallel_execution():
    """Test parallel execution of multiple delegations."""
    print("\n=== Testing Parallel Execution ===\n")
    
    orchestrator = InteractiveSubprocessOrchestrator(log_level="INFO")
    
    # Create multiple delegations
    delegations = [
        {"agent": "Engineer", "task": "Create a function to calculate fibonacci numbers"},
        {"agent": "QA", "task": "Write tests for edge cases"},
        {"agent": "Documentation", "task": "Create API documentation"}
    ]
    
    print(f"Running {len(delegations)} delegations in parallel...")
    
    # Run in parallel
    results = orchestrator.run_parallel_delegations(delegations)
    
    print(f"\nResults:")
    for result in results:
        print(f"  {result.agent_type}: {'✓' if result.success else '✗'} ({result.execution_time:.2f}s)")
    
    # Format results
    formatted = orchestrator.format_execution_results(results)
    print(f"\nFormatted output preview:")
    lines = formatted.split('\n')[:20]
    print('\n'.join(lines))
    if len(formatted.split('\n')) > 20:
        print("...")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Run tests
    print("Starting Interactive Subprocess Orchestrator Tests\n")
    
    # Comment out tests that require actual Claude CLI
    print("Note: Full orchestration tests require Claude CLI to be installed and configured.")
    print("Running detection and management tests only...\n")
    
    test_delegation_detection()
    # test_process_management()  # Requires Claude CLI
    # test_parallel_execution()   # Requires Claude CLI
    # test_basic_orchestration()  # Requires Claude CLI
    
    print("\nTests completed!")