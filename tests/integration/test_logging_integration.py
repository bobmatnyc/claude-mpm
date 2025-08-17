#!/usr/bin/env python3
"""Test full logging integration with WebSocket."""

import subprocess
import sys
import threading
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_manager_with_logging():
    """Test manager mode with logging enabled."""
    print("🧪 Testing Manager Mode with WebSocket Logging")
    print("-" * 50)

    # Start claude-mpm with monitor flag
    cmd = [sys.executable, "-m", "claude_mpm", "run", "--monitor", "--logging", "DEBUG"]

    print(f"📋 Command: {' '.join(cmd)}")
    print("\n✅ Starting claude-mpm with WebSocket logging...")
    print("📊 The dashboard should show real-time log messages")
    print("\n⏸️  Press Ctrl+C to stop\n")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Monitor output
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break

            if line:
                print(f"  > {line.strip()}")

                # Look for key messages
                if "Dashboard:" in line:
                    print("\n✅ Dashboard URL found - check your browser!")
                    print("📝 Look for log messages in the Console Output section")

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
        proc.terminate()
        proc.wait()
    except Exception as e:
        print(f"\n❌ Error: {e}")


def main():
    """Run the test."""
    print("🚀 WebSocket Logging Integration Test")
    print("=" * 60)

    print("\nThis test will:")
    print("1. Start claude-mpm with --monitor flag")
    print("2. Enable DEBUG logging level")
    print("3. Stream all logs to the dashboard via WebSocket")
    print("\n" + "=" * 60)

    test_manager_with_logging()


if __name__ == "__main__":
    main()
