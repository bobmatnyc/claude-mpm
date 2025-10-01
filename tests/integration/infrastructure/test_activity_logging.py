#!/usr/bin/env python3
"""Test the activity logging configuration and setup."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.models.agent_session import AgentSession
from claude_mpm.services.event_aggregator import EventAggregator


def test_configuration():
    """Test configuration is correct."""
    print("=" * 60)
    print("Testing Activity Logging Configuration")
    print("=" * 60)

    config = Config()

    # Check old response logging is disabled
    assert not config.get(
        "response_logging.enabled", True
    ), "Response logging should be disabled"
    assert not config.get(
        "response_tracking.enabled", True
    ), "Response tracking should be disabled"
    print("✅ Old response logging disabled")

    # Check event aggregator is enabled
    assert config.get(
        "event_aggregator.enabled", False
    ), "Event aggregator should be enabled"
    print("✅ Event aggregator enabled")

    # Check activity directory
    activity_dir = config.get("event_aggregator.activity_directory", "")
    assert (
        activity_dir == ".claude-mpm/activity"
    ), f"Activity directory should be .claude-mpm/activity, got {activity_dir}"
    print(f"✅ Activity directory: {activity_dir}")

    return True


def test_aggregator_initialization():
    """Test aggregator initializes with correct directory."""
    print("\nTesting Aggregator Initialization")
    print("-" * 40)

    # Create aggregator
    aggregator = EventAggregator(save_dir=None)  # Should use config

    # Check save directory
    expected_dir = Path.cwd() / ".claude-mpm" / "activity"
    assert (
        aggregator.save_dir == expected_dir
    ), f"Save dir should be {expected_dir}, got {aggregator.save_dir}"
    print(f"✅ Save directory: {aggregator.save_dir}")

    # Check directory was created
    assert aggregator.save_dir.exists(), "Activity directory should be created"
    print("✅ Activity directory created")

    return True


def test_session_saving():
    """Test that sessions will be saved to activity directory."""
    print("\nTesting Session Saving")
    print("-" * 40)

    # Create a test session
    session = AgentSession(
        session_id="test_activity_session", start_time=datetime.now(timezone.utc)
    )
    session.working_directory = "/test/dir"
    session.initial_prompt = "Test activity logging"

    # Add a test event
    session.add_event(
        event_type="UserPromptSubmit",
        data={"prompt": "Test activity logging"},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Save to activity directory
    activity_dir = Path.cwd() / ".claude-mpm" / "activity"
    activity_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_test_activity_session.json"
    filepath = activity_dir / filename

    # Save session
    session_data = session.to_dict()
    with filepath.open("w") as f:
        json.dump(session_data, f, indent=2, default=str)

    # Verify file exists
    assert filepath.exists(), f"Session file should exist at {filepath}"
    print(f"✅ Test session saved to: {filepath.name}")

    # Clean up test file
    filepath.unlink()
    print("✅ Test file cleaned up")

    return True


def main():
    """Run all tests."""
    try:
        # Run tests
        test_configuration()
        test_aggregator_initialization()
        test_session_saving()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\nActivity logging is properly configured:")
        print("- Response logging: DISABLED")
        print("- Event aggregator: ENABLED")
        print("- Activity directory: .claude-mpm/activity/")
        print("\nTo start activity logging, run:")
        print("  python scripts/start_activity_logging.py")
        print("\nOr use the CLI:")
        print("  claude-mpm aggregate start")

        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
