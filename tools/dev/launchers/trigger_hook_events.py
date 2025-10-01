#!/usr/bin/env python3
"""
Trigger hook events for manual dashboard testing.

This script runs MPM commands that will generate hook events,
which should be visible in the dashboard at http://localhost:8765/dashboard
"""

import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


def trigger_mpm_command(prompt, delay=3):
    """Trigger an MPM command that should generate hook events."""
    logger.info(f"🎯 Triggering MPM command: {prompt}")

    command = [
        "python",
        "-m",
        "claude_mpm.cli.main",
        "run",
        "-i",
        prompt,
        "--non-interactive",
    ]

    logger.info(f"🚀 Running: {' '.join(command)}")

    try:
        # Run command in background
        process = subprocess.Popen(
            command,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        logger.info(f"📊 Command started with PID: {process.pid}")
        logger.info(f"⏳ Waiting {delay} seconds for events to be generated...")

        # Wait for specified delay
        time.sleep(delay)

        # Check if process is still running
        if process.poll() is None:
            logger.info("🔄 Command still running...")
            # Let it continue for a bit more
            try:
                stdout, stderr = process.communicate(timeout=10)
                logger.info(
                    f"✅ Command completed with return code: {process.returncode}"
                )
                if stdout:
                    logger.info(f"📄 Output: {stdout[:200]}...")
                if stderr:
                    logger.info(f"⚠️ Errors: {stderr[:200]}...")
            except subprocess.TimeoutExpired:
                logger.warning("⏰ Command still running after timeout")
                process.terminate()
        else:
            stdout, stderr = process.communicate()
            logger.info(f"✅ Command completed with return code: {process.returncode}")
            if stdout:
                logger.info(f"📄 Output: {stdout[:200]}...")
            if stderr:
                logger.info(f"⚠️ Errors: {stderr[:200]}...")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to run command: {e}")
        return False


def main():
    """Run hook event triggers for manual testing."""
    logger.info("🚀 Starting hook event trigger test...")
    logger.info("=" * 60)

    # Check server availability first
    import requests

    try:
        requests.get("http://localhost:8765/socket.io/", timeout=2)
        logger.info("✅ Socket.IO server is running")
    except Exception:
        logger.error("❌ Socket.IO server not available at localhost:8765")
        logger.error("   Please ensure the server is running with:")
        logger.error("   python scripts/start_persistent_socketio_server.py")
        return False

    logger.info("🌐 Dashboard URL: http://localhost:8765/dashboard")
    logger.info("📋 INSTRUCTIONS:")
    logger.info("   1. Open the dashboard URL in your browser")
    logger.info("   2. Click 'Connect' to connect to Socket.IO server")
    logger.info("   3. Watch the events appear as we trigger MPM commands")
    logger.info("   4. Look for user_prompt, pre_tool, and post_tool events")
    logger.info("-" * 60)

    input("🔶 Press Enter when you have the dashboard open and connected...")

    # Trigger different types of hook events
    test_commands = [
        "List the current directory contents",
        "Create a simple test file with current timestamp",
        "Check the git status of this repository",
    ]

    for i, command in enumerate(test_commands, 1):
        logger.info(f"\n📢 TEST {i}/3: {command}")
        logger.info("👀 Watch the dashboard for new events...")

        success = trigger_mpm_command(command, delay=5)
        if success:
            logger.info("✅ Command triggered successfully")
        else:
            logger.warning("⚠️ Command trigger failed")

        if i < len(test_commands):
            input("\n🔶 Press Enter to continue to next test...")

    logger.info("\n" + "=" * 60)
    logger.info("🎉 Hook event trigger test completed!")
    logger.info("📊 You should have seen the following in the dashboard:")
    logger.info("   - user_prompt events when commands started")
    logger.info("   - pre_tool events before tool usage")
    logger.info("   - post_tool events after tool completion")
    logger.info("📝 If events appeared, the complete flow is working!")
    logger.info("   Hook runs → Socket.IO server receives → Dashboard displays")
    logger.info("=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
