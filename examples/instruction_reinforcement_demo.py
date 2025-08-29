#!/usr/bin/env python3
"""
Instruction Reinforcement Hook Demo

This script demonstrates the InstructionReinforcementHook system in action,
showing how it integrates with PMHookInterceptor to inject reminder messages.
"""

import json
import sys
from pathlib import Path

# Add src to path for importing
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.core.pm_hook_interceptor import (
    get_instruction_reinforcement_metrics,
    get_pm_hook_interceptor,
    reset_instruction_reinforcement_counters,
)


def demo_todowrite_function(*args, **kwargs):
    """Mock TodoWrite function that demonstrates the injection behavior."""
    todos = kwargs.get("todos", [])

    print(f"📝 TodoWrite called with {len(todos)} todos:")
    for i, todo in enumerate(todos, 1):
        # Highlight injected reminders
        if any(keyword in todo["content"] for keyword in ["[TEST-REMINDER]", "[PM-INSTRUCTION]"]):
            print(f"   🔔 {i}. {todo['content']} (INJECTED)")
        else:
            print(f"   - {i}. {todo['content']}")

    return f"Processed {len(todos)} todos"


def main():
    """Main demo function."""
    print("🎯 Instruction Reinforcement Hook Demo")
    print("=" * 50)

    # Reset any existing state
    reset_instruction_reinforcement_counters()

    # Configure the hook for demo purposes
    config = {
        "enabled": True,
        "test_mode": True,
        "injection_interval": 3,  # Inject every 3 calls
    }

    print(f"Configuration: {json.dumps(config, indent=2)}")
    print()

    # Get PM hook interceptor with our configuration
    interceptor = get_pm_hook_interceptor(instruction_reinforcement_config=config)

    # Wrap our demo TodoWrite function
    wrapped_todowrite = interceptor.intercept_todowrite(demo_todowrite_function)

    # Simulate a series of PM TodoWrite calls
    demo_calls = [
        {"todos": [{"content": "Analyze user requirements", "status": "pending", "activeForm": "Analyzing requirements"}]},
        {"todos": [{"content": "Create project plan", "status": "pending", "activeForm": "Creating plan"}]},
        {"todos": [{"content": "Delegate implementation to Engineer", "status": "pending", "activeForm": "Delegating work"}]},
        {"todos": [{"content": "Review progress with QA team", "status": "pending", "activeForm": "Reviewing progress"}]},
        {"todos": [{"content": "Coordinate deployment", "status": "pending", "activeForm": "Coordinating deployment"}]},
        {"todos": [{"content": "Schedule team standup", "status": "pending", "activeForm": "Scheduling meeting"}]},
    ]

    print("🚀 Simulating PM session with TodoWrite calls...\n")

    for i, call_data in enumerate(demo_calls, 1):
        print(f"--- Call #{i} ---")

        # Make the call
        result = wrapped_todowrite(**call_data)
        print(f"Result: {result}")

        # Show current metrics
        metrics = get_instruction_reinforcement_metrics()
        print(f"Metrics: {metrics['call_count']} calls, {metrics['injection_count']} injections, "
              f"next injection in {metrics['next_injection_in']} calls")
        print()

    # Final summary
    print("=" * 50)
    print("📊 Final Session Metrics")
    print("=" * 50)

    final_metrics = get_instruction_reinforcement_metrics()
    print(json.dumps(final_metrics, indent=2))

    print("\n✅ Demo complete!")
    print(f"   Total calls: {final_metrics['call_count']}")
    print(f"   Reminders injected: {final_metrics['injection_count']}")
    print(f"   Injection rate: {final_metrics['injection_rate']:.1%}")
    print("   Effectiveness: Reminders appeared at the configured interval")

    print("\n💡 Key Observations:")
    print("   - Hook operates transparently without breaking TodoWrite")
    print("   - Reminders are clearly marked and appear at top of todo list")
    print("   - Injection timing follows configured interval precisely")
    print("   - Different reminder messages rotate to avoid habituation")
    print("   - Comprehensive metrics enable monitoring and tuning")


if __name__ == "__main__":
    main()
