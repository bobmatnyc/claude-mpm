#!/usr/bin/env python3
"""Test hook integration with orchestrator."""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestration.system_prompt_orchestrator import SystemPromptOrchestrator
from services.hook_service_manager import HookServiceManager


def test_hook_integration():
    """Test that hooks are called during orchestration."""
    print("Testing hook integration with SystemPromptOrchestrator...")
    
    # Initialize hook manager
    hook_manager = HookServiceManager()
    
    # Check if hook service is running
    if not hook_manager.is_available():
        print("Hook service not running. Starting it...")
        started = hook_manager.start_service()
        if not started:
            print("Failed to start hook service")
            return
        # Give it time to start
        time.sleep(2)
    
    print(f"Hook service available on port {hook_manager.port}")
    
    # Initialize orchestrator with hook manager
    orchestrator = SystemPromptOrchestrator(
        log_level="INFO",
        hook_manager=hook_manager
    )
    
    # Check if hook client was initialized
    if orchestrator.hook_client:
        print("✓ Hook client initialized successfully")
    else:
        print("✗ Hook client not initialized")
        return
    
    # Test non-interactive mode (easier to test)
    print("\nTesting non-interactive mode with hooks...")
    print("-" * 50)
    
    # Run a simple command
    orchestrator.run_non_interactive("What is 2+2? Please be brief.")
    
    print("\n" + "-" * 50)
    print("Test complete. Check logs for hook calls.")
    
    # Show hook service info
    info = hook_manager.get_service_info()
    print(f"\nHook service info:")
    print(f"  URL: {info['url']}")
    print(f"  PID: {info.get('pid', 'Unknown')}")
    print(f"  Running: {hook_manager.is_available()}")


if __name__ == "__main__":
    test_hook_integration()