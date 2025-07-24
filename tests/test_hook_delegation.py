#!/usr/bin/env python3
"""Test hook integration with Task tool delegation tracking."""

import sys
import time
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestration.subprocess_orchestrator import SubprocessOrchestrator
from services.hook_service_manager import HookServiceManager


def test_delegation_hooks():
    """Test hooks during Task tool delegations."""
    print("Testing Task tool delegation with hooks...")
    
    # Initialize hook manager
    hook_manager = HookServiceManager()
    
    # Check if hook service is running
    if not hook_manager.is_available():
        print("Hook service not running. Starting it...")
        started = hook_manager.start_service()
        if not started:
            print("Failed to start hook service")
            return
        time.sleep(2)
    
    print(f"Hook service available on port {hook_manager.port}")
    
    # Initialize subprocess orchestrator (has better control over delegations)
    orchestrator = SubprocessOrchestrator(
        log_level="INFO",
        hook_manager=hook_manager
    )
    
    # Test prompt that will trigger delegations
    test_prompt = """
    You are the PM orchestrator. Please delegate these tasks:
    
    **Engineer Agent**: Create a simple hello world function in Python
    
    **QA Agent**: Write a test for the hello world function
    
    **Documentation Agent**: Document the hello world function
    
    Remember to use proper Task tool delegation format.
    """
    
    print("\nRunning orchestration with delegation tracking...")
    print("-" * 50)
    
    # Run orchestration
    orchestrator.run_non_interactive(test_prompt)
    
    print("\n" + "-" * 50)
    print("Test complete. Delegations should have triggered hooks.")
    
    # Check hook service logs
    if orchestrator.hook_client:
        health = orchestrator.hook_client.health_check()
        print(f"\nHook service status: {health.get('status', 'unknown')}")
        print(f"Hooks registered: {health.get('hooks_count', 0)}")


if __name__ == "__main__":
    test_delegation_hooks()