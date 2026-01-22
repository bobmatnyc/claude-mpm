#!/usr/bin/env python3
"""Context Usage Tracker Example.

Demonstrates how to use ContextUsageTracker to monitor cumulative
token usage across Claude Code hook invocations.

Usage:
    python examples/context_usage_tracker_example.py
"""

from pathlib import Path

from claude_mpm.services.infrastructure import ContextUsageTracker


def main():
    """Demonstrate ContextUsageTracker functionality."""
    print("=" * 70)
    print("Context Usage Tracker Demo")
    print("=" * 70)
    print()

    # Initialize tracker
    tracker = ContextUsageTracker(project_path=Path.cwd())
    print(f"Initialized tracker at: {tracker.state_file}")
    print()

    # Simulate hook invocations with token updates
    print("Simulating Claude Code hook invocations...")
    print("-" * 70)

    # Hook 1: Initial code analysis
    print("\n[Hook 1] Code analysis request")
    state = tracker.update_usage(input_tokens=15000, output_tokens=3000)
    print(f"  Input: 15,000 | Output: 3,000")
    print(
        f"  Cumulative: {state.cumulative_input_tokens + state.cumulative_output_tokens:,} tokens"
    )
    print(f"  Usage: {state.percentage_used:.1f}%")
    print(f"  Threshold: {state.threshold_reached or 'None'}")

    # Hook 2: Implementation with caching
    print("\n[Hook 2] Implementation request (with cache)")
    state = tracker.update_usage(
        input_tokens=25000,
        output_tokens=8000,
        cache_creation=5000,
        cache_read=3000,
    )
    print(f"  Input: 25,000 | Output: 8,000 | Cache Read: 3,000")
    print(
        f"  Cumulative: {state.cumulative_input_tokens + state.cumulative_output_tokens:,} tokens"
    )
    print(f"  Usage: {state.percentage_used:.1f}%")
    print(f"  Threshold: {state.threshold_reached or 'None'}")

    # Hook 3: Large refactoring task
    print("\n[Hook 3] Large refactoring request")
    state = tracker.update_usage(input_tokens=40000, output_tokens=12000)
    print(f"  Input: 40,000 | Output: 12,000")
    print(
        f"  Cumulative: {state.cumulative_input_tokens + state.cumulative_output_tokens:,} tokens"
    )
    print(f"  Usage: {state.percentage_used:.1f}%")
    print(f"  Threshold: {state.threshold_reached or 'None'}")

    # Hook 4: Documentation generation
    print("\n[Hook 4] Documentation generation")
    state = tracker.update_usage(input_tokens=30000, output_tokens=10000)
    print(f"  Input: 30,000 | Output: 10,000")
    print(
        f"  Cumulative: {state.cumulative_input_tokens + state.cumulative_output_tokens:,} tokens"
    )
    print(f"  Usage: {state.percentage_used:.1f}%")
    print(f"  Threshold: {state.threshold_reached or 'None'}")

    # Check for auto-pause
    print()
    print("-" * 70)
    if tracker.should_auto_pause():
        print("⚠️  AUTO-PAUSE TRIGGERED - Context budget at 90%+")
        print("   Recommendation: Pause session and create resume point")
    else:
        remaining_pct = 90.0 - state.percentage_used
        print(f"✓  Context budget healthy ({remaining_pct:.1f}% until auto-pause)")

    # Display usage summary
    print()
    print("=" * 70)
    print("Usage Summary")
    print("=" * 70)
    summary = tracker.get_usage_summary()

    print(f"\nSession ID: {summary['session_id']}")
    print(f"Total Tokens: {summary['total_tokens']:,} / {summary['budget']:,}")
    print(f"Usage: {summary['percentage_used']:.2f}%")
    print(f"Threshold: {summary['threshold_reached'] or 'None'}")
    print(f"Auto-Pause Active: {summary['auto_pause_active']}")

    print("\nBreakdown:")
    breakdown = summary["breakdown"]
    print(f"  Input Tokens:          {breakdown['input_tokens']:,}")
    print(f"  Output Tokens:         {breakdown['output_tokens']:,}")
    print(f"  Cache Creation Tokens: {breakdown['cache_creation_tokens']:,}")
    print(f"  Cache Read Tokens:     {breakdown['cache_read_tokens']:,}")

    print(f"\nLast Updated: {summary['last_updated']}")

    # Show threshold levels
    print()
    print("=" * 70)
    print("Threshold Levels")
    print("=" * 70)
    print()
    for name, percentage in tracker.THRESHOLDS.items():
        tokens = int(tracker.CONTEXT_BUDGET * percentage)
        status = "✓" if state.percentage_used < (percentage * 100) else "⚠️"
        print(
            f"{status} {name.upper():12} - {percentage * 100:.0f}% ({tokens:,} tokens)"
        )

    # Demonstrate session reset
    print()
    print("=" * 70)
    print("Session Management")
    print("=" * 70)
    print()
    print("Resetting session to start fresh tracking...")
    tracker.reset_session("new-session-demo")
    new_state = tracker.get_current_state()
    print(f"New session ID: {new_state.session_id}")
    print(f"Usage reset to: {new_state.percentage_used:.1f}%")
    print()


if __name__ == "__main__":
    main()
