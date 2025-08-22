#!/usr/bin/env python3
"""Test script to verify response logging is working correctly."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Enable debug mode
os.environ["CLAUDE_MPM_HOOK_DEBUG"] = "true"

from claude_mpm.utils.config_manager import ConfigurationManager as ConfigManager
from claude_mpm.services.response_tracker import ResponseTracker


def test_response_logging():
    """Test that response logging is configured and working."""

    print("=" * 60)
    print("RESPONSE LOGGING TEST")
    print("=" * 60)

    # Load configuration
    config = Config()

    # Check response logging settings
    print("\n1. Checking configuration...")
    response_logging_enabled = config.get("response_logging.enabled", False)
    response_tracking_enabled = config.get("response_tracking.enabled", False)

    print(f"   response_logging.enabled: {response_logging_enabled}")
    print(f"   response_tracking.enabled: {response_tracking_enabled}")

    if not (response_logging_enabled or response_tracking_enabled):
        print("   ❌ Response logging is DISABLED in configuration")
        print(
            "   To enable, set 'response_logging.enabled: true' or 'response_tracking.enabled: true'"
        )
        return False
    else:
        print("   ✅ Response logging is ENABLED")

    # Check response directory
    print("\n2. Checking response directory...")
    response_dir = Path(
        config.get("response_logging.session_directory", ".claude-mpm/responses")
    )
    if not response_dir.is_absolute():
        response_dir = Path.cwd() / response_dir

    print(f"   Directory: {response_dir}")
    if response_dir.exists():
        print(f"   ✅ Directory exists")

        # List recent response files
        response_files = list(response_dir.glob("**/*.json"))
        if response_files:
            print(f"   Found {len(response_files)} response files")

            # Show last 5 files
            recent_files = sorted(
                response_files, key=lambda f: f.stat().st_mtime, reverse=True
            )[:5]
            print("\n   Recent response files:")
            for f in recent_files:
                size = f.stat().st_size
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                print(f"   - {f.name} ({size} bytes, modified: {mtime})")
        else:
            print("   ⚠️ No response files found yet")
    else:
        print(f"   ⚠️ Directory does not exist (will be created on first response)")

    # Test response tracker
    print("\n3. Testing ResponseTracker...")
    try:
        tracker = ResponseTracker(config=config)

        if tracker.is_enabled():
            print("   ✅ ResponseTracker initialized and enabled")

            # Test tracking a response
            test_session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            test_file = tracker.track_response(
                agent_name="test_agent",
                request="Test request for response logging verification",
                response="Test response successfully logged",
                session_id=test_session_id,
                metadata={"test": True, "timestamp": datetime.now().isoformat()},
            )

            if test_file and test_file.exists():
                print(f"   ✅ Test response logged to: {test_file.name}")

                # Read and verify the content
                with open(test_file, "r") as f:
                    content = json.load(f)
                    if (
                        content.get("request")
                        == "Test request for response logging verification"
                    ):
                        print("   ✅ Response content verified")
                    else:
                        print("   ❌ Response content mismatch")
            else:
                print("   ❌ Failed to create test response file")
        else:
            print("   ❌ ResponseTracker is disabled")

    except Exception as e:
        print(f"   ❌ ResponseTracker error: {e}")
        import traceback

        traceback.print_exc()

    # Check hook handler integration
    print("\n4. Checking hook handler integration...")
    hook_handler_path = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "hooks"
        / "claude_hooks"
        / "hook_handler.py"
    )
    if hook_handler_path.exists():
        with open(hook_handler_path, "r") as f:
            content = f.read()

        has_stop_tracking = (
            "_handle_stop_fast" in content
            and "response_tracker.track_response" in content
        )
        has_subagent_tracking = (
            "_handle_subagent_stop_fast" in content
            and "response_tracker.track_response" in content
        )

        if has_stop_tracking:
            print("   ✅ Stop event response tracking implemented")
        else:
            print("   ❌ Stop event response tracking NOT found")

        if has_subagent_tracking:
            print("   ✅ SubagentStop event response tracking implemented")
        else:
            print("   ❌ SubagentStop event response tracking NOT found")
    else:
        print("   ❌ Hook handler not found")

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("Response logging should be working if all checks passed.")
    print("To see logs in action:")
    print("1. Run: export CLAUDE_MPM_HOOK_DEBUG=true")
    print("2. Start claude-mpm in interactive mode")
    print("3. Run a command or delegate to an agent")
    print("4. Check .claude-mpm/responses/ for new files")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_response_logging()
    sys.exit(0 if success else 1)