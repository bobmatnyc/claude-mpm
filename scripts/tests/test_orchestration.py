#!/usr/bin/env python3
"""Test claude-mpm orchestration functionality."""

import sys
import time
from pathlib import Path

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from orchestration.orchestrator import MPMOrchestrator
from utils.logger import setup_logging


def test_basic_orchestration():
    """Test basic orchestration with ticket extraction."""
    print("=== Claude MPM Orchestration Test ===\n")
    
    # Set up logging
    logger = setup_logging(level="DEBUG", console_output=True)
    
    # Create orchestrator
    print("Creating orchestrator...")
    orchestrator = MPMOrchestrator(debug=True)
    
    # Start Claude subprocess
    print("Starting Claude subprocess...")
    if not orchestrator.start():
        print("❌ Failed to start Claude")
        return False
    
    print(f"✅ Claude started with PID: {orchestrator.process.pid}")
    
    # Give it a moment to initialize
    time.sleep(1)
    
    # Send test input with ticket patterns
    print("\nSending test input...")
    test_input = """
Please help me plan a simple project. Here are the tasks:
TODO: Set up project structure
TODO: Create main application file
BUG: Fix import errors in existing code
FEATURE: Add user authentication
"""
    
    orchestrator.send_input(test_input)
    
    # Collect output for a few seconds
    print("\nCollecting output...")
    output_lines = []
    start_time = time.time()
    
    while time.time() - start_time < 5:
        output = orchestrator.get_output(timeout=0.1)
        if output:
            print(f"Claude: {output}")
            output_lines.append(output)
    
    # Check extracted tickets
    print("\n=== Extracted Tickets ===")
    tickets = orchestrator.ticket_extractor.get_all_tickets()
    for ticket in tickets:
        print(f"- [{ticket['type'].upper()}] {ticket['title']}")
    
    # Get summary
    summary = orchestrator.ticket_extractor.get_summary()
    print(f"\nSummary: {summary}")
    
    # Stop orchestrator
    print("\nStopping orchestrator...")
    orchestrator.stop()
    
    print("\n✅ Test completed successfully!")
    return True


def test_framework_injection():
    """Test that framework instructions are injected."""
    print("\n=== Framework Injection Test ===\n")
    
    orchestrator = MPMOrchestrator(debug=True)
    
    # Check framework loader
    if orchestrator.framework_loader.framework_content['loaded']:
        print("✅ Framework loaded successfully")
        print(f"   Version: {orchestrator.framework_loader.framework_content['version']}")
        print(f"   Agents: {', '.join(orchestrator.framework_loader.get_agent_list())}")
    else:
        print("⚠️  Using minimal framework instructions")
    
    # Get instructions that would be injected
    instructions = orchestrator.framework_loader.get_framework_instructions()
    print(f"\nFramework instructions length: {len(instructions)} characters")
    print("First 200 characters:")
    print(instructions[:200] + "...")
    
    return True


def main():
    """Run all tests."""
    tests = [
        ("Framework Injection", test_framework_injection),
        ("Basic Orchestration", test_basic_orchestration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ {test_name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Tests completed: {passed} passed, {failed} failed")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())