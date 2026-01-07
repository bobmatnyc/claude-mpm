#!/usr/bin/env python3
"""Example usage of IncrementalPauseManager for auto-pause workflow.

This demonstrates how to integrate IncrementalPauseManager with
ContextUsageTracker to implement intelligent auto-pause behavior.

Typical workflow:
1. Monitor context usage with ContextUsageTracker
2. When 90% threshold is crossed, start incremental pause
3. Record actions during wind-down period
4. Finalize pause when session ends or user decides to continue
"""

from pathlib import Path

from claude_mpm.services.cli import IncrementalPauseManager
from claude_mpm.services.infrastructure import ContextUsageTracker


def example_auto_pause_workflow():
    """Demonstrate typical auto-pause workflow."""

    # Initialize services
    project_path = Path.cwd()
    tracker = ContextUsageTracker(project_path)
    pause_manager = IncrementalPauseManager(project_path)

    print("=== Auto-Pause Workflow Example ===\n")

    # Simulate API calls building up context
    print("1. Simulating API calls...")

    # First call: 30k input, 5k output
    state = tracker.update_usage(input_tokens=30000, output_tokens=5000)
    print(f"   After call 1: {state.percentage_used:.1f}% context used")

    # Second call: 40k input, 10k output
    state = tracker.update_usage(input_tokens=40000, output_tokens=10000)
    print(f"   After call 2: {state.percentage_used:.1f}% context used")

    # Third call: 50k input, 15k output - crosses 90% threshold
    state = tracker.update_usage(input_tokens=50000, output_tokens=15000)
    print(f"   After call 3: {state.percentage_used:.1f}% context used")

    # Fourth call: 30k input, 10k output - exceeds 90%!
    state = tracker.update_usage(input_tokens=30000, output_tokens=10000)
    print(f"   After call 4: {state.percentage_used:.1f}% context used")
    print()

    # Check if auto-pause should be triggered
    if tracker.should_auto_pause() and not pause_manager.is_pause_active():
        print("2. Auto-pause threshold exceeded (90%+)!")
        print("   Starting incremental pause to capture wind-down actions...\n")

        # Start incremental pause
        session_id = pause_manager.start_incremental_pause(
            context_percentage=state.percentage_used / 100,
            initial_state=state.__dict__,
        )
        print(f"   Pause started: {session_id}\n")

    # Simulate continued actions during wind-down
    if pause_manager.is_pause_active():
        print("3. Recording actions during wind-down period:\n")

        # User performs a few more actions before deciding to pause
        pause_manager.append_action(
            action_type="tool_call",
            action_data={"tool": "Read", "path": "/src/main.py", "lines": 150},
            context_percentage=0.91,
        )
        print("   - Tool call: Read /src/main.py (150 lines)")

        pause_manager.append_action(
            action_type="assistant_response",
            action_data={"summary": "Analyzed code structure and identified issues"},
            context_percentage=0.92,
        )
        print("   - Assistant: Analyzed code structure")

        pause_manager.append_action(
            action_type="tool_call",
            action_data={"tool": "Grep", "pattern": "TODO", "results": 5},
            context_percentage=0.93,
        )
        print("   - Tool call: Grep for TODOs (5 results)")

        pause_manager.append_action(
            action_type="assistant_response",
            action_data={"summary": "Listed outstanding tasks from TODO comments"},
            context_percentage=0.93,
        )
        print("   - Assistant: Listed outstanding tasks\n")

        # Get summary before finalizing
        summary = pause_manager.get_pause_summary()
        print("4. Pause summary:")
        print(f"   - Session ID: {summary['session_id']}")
        print(f"   - Actions recorded: {summary['action_count']}")
        print(
            f"   - Context range: {summary['context_range'][0]:.1%} -> {summary['context_range'][1]:.1%}"
        )
        print(f"   - Duration: {summary['duration_seconds']} seconds\n")

        # Finalize pause with full snapshot
        print("5. Finalizing pause with full snapshot...\n")
        final_path = pause_manager.finalize_pause(create_full_snapshot=True)

        print(f"   ✓ Session finalized: {final_path}")
        print(f"   ✓ Files created:")
        print(f"     - {final_path.stem}.json (machine-readable)")
        print(f"     - {final_path.stem}.yaml (human-readable)")
        print(f"     - {final_path.stem}.md (documentation)")
        print(f"     - {final_path.stem}-incremental.jsonl (action log)")
        print()

    print("=== Workflow Complete ===\n")


def example_discard_pause():
    """Demonstrate discarding a pause without finalizing."""

    pause_manager = IncrementalPauseManager()

    print("=== Discard Pause Example ===\n")

    # Start pause
    session_id = pause_manager.start_incremental_pause(
        context_percentage=0.90, initial_state={"test": "data"}
    )
    print(f"Pause started: {session_id}")

    # Record some actions
    pause_manager.append_action(
        action_type="tool_call", action_data={"tool": "Read"}, context_percentage=0.91
    )
    print("Recorded 1 action")

    # User decides to continue instead of pausing
    print("User decides to continue working...\n")

    # Discard the pause
    pause_manager.discard_pause()
    print("✓ Pause discarded (no session files created)")

    print()


def example_resume_from_pause():
    """Demonstrate how to resume from a paused session."""

    sessions_dir = Path.cwd() / ".claude-mpm" / "sessions"

    print("=== Resume from Pause Example ===\n")

    # Read LATEST-SESSION.txt to find most recent pause
    latest_file = sessions_dir / "LATEST-SESSION.txt"

    if latest_file.exists():
        content = latest_file.read_text()
        print("Latest session info:")
        print(content)
        print()

        # Extract session ID from content
        for line in content.split("\n"):
            if line.startswith("Latest Session:"):
                session_id = line.split(":")[1].strip()
                break

        # Read markdown documentation
        md_file = sessions_dir / f"{session_id}.md"
        if md_file.exists():
            print(f"To resume, read: {md_file}")
            print()
            print("First few lines:")
            print("-" * 60)
            lines = md_file.read_text().split("\n")
            for line in lines[:15]:
                print(line)
            print("-" * 60)
    else:
        print("No previous sessions found")

    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "discard":
            example_discard_pause()
        elif sys.argv[1] == "resume":
            example_resume_from_pause()
        else:
            print("Usage: python incremental_pause_usage.py [discard|resume]")
    else:
        example_auto_pause_workflow()
