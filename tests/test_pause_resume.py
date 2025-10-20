#!/usr/bin/env python3
"""
Quick test script for pause/resume functionality.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.session_pause_manager import SessionPauseManager
from claude_mpm.cli.commands.session_resume_manager import SessionResumeManager


def test_pause_resume():
    """Test pause and resume functionality."""

    # Use current directory
    project_path = Path.cwd()

    print("=" * 80)
    print("TESTING PAUSE/RESUME FUNCTIONALITY")
    print("=" * 80)

    # Test 1: Pause session
    print("\n[TEST 1] Testing session pause...")
    pause_manager = SessionPauseManager(project_path)

    result = pause_manager.pause_session(
        conversation_summary="Testing pause/resume feature implementation",
        accomplishments=[
            "Created SessionPauseManager",
            "Created SessionResumeManager",
            "Enhanced mpm_init.py with handlers",
            "Updated parser with subcommands",
        ],
        next_steps=["Test functionality", "Create documentation", "Add to changelog"],
    )

    if result["status"] == "success":
        print("✓ Pause successful!")
        print(f"  Session ID: {result['session_id']}")
        print(f"  Session file: {result['session_file']}")
        print(f"  Git commit created: {result['git_commit_created']}")

        # Verify file was created
        session_file = Path(result["session_file"])
        if session_file.exists():
            print("✓ Session file exists and is readable")

            # Display session state
            with open(session_file) as f:
                session_state = json.load(f)

            print("\nSession State Preview:")
            print(f"  - Paused at: {session_state['paused_at']}")
            print(f"  - Summary: {session_state['conversation']['summary']}")
            print(
                f"  - Accomplishments: {len(session_state['conversation']['accomplishments'])}"
            )
            print(f"  - Next steps: {len(session_state['conversation']['next_steps'])}")
            print(
                f"  - Git branch: {session_state['git_context'].get('branch', 'N/A')}"
            )
            print(
                f"  - Recent commits: {len(session_state['git_context'].get('recent_commits', []))}"
            )
        else:
            print("✗ Session file not found!")
            return False
    else:
        print(f"✗ Pause failed: {result.get('message')}")
        return False

    # Test 2: Resume session
    print("\n[TEST 2] Testing session resume...")
    resume_manager = SessionResumeManager(project_path)

    result = resume_manager.resume_session()

    if result["status"] == "success":
        print("✓ Resume successful!")

        session_state = result["session_state"]
        changes = result["changes"]

        print(f"  - Session ID: {session_state['session_id']}")
        print(f"  - Changes detected: {len(changes.get('warnings', []))}")
        print(f"  - New commits: {changes.get('new_commits_count', 0)}")
        print(f"  - Branch changed: {changes.get('branch_changed', False)}")

        if changes.get("warnings"):
            print("\n  Warnings:")
            for warning in changes["warnings"]:
                print(f"    ⚠️  {warning}")

    else:
        print(f"✗ Resume failed: {result.get('message')}")
        return False

    # Test 3: List sessions
    print("\n[TEST 3] Testing session listing...")
    sessions = resume_manager.list_available_sessions()
    print(f"✓ Found {len(sessions)} paused session(s)")

    for idx, session in enumerate(sessions, 1):
        print(f"  [{idx}] {session['session_id']}")
        print(f"      Paused: {session['paused_at']}")
        print(f"      Summary: {session['summary'][:60]}...")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED! ✓")
    print("=" * 80)

    return True


if __name__ == "__main__":
    try:
        success = test_pause_resume()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
