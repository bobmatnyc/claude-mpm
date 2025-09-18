#!/usr/bin/env python3
"""
Live Dashboard Test Script
Tests the dashboard with real Claude MPM events by executing actual commands
"""

import subprocess
import sys
import time


def run_claude_mpm_command(command):
    """Run a claude-mpm command and capture output"""
    print(f"🚀 Running: {command}")
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=10, check=False
        )
        if result.returncode == 0:
            print(f"✅ Success: {command}")
        else:
            print(f"❌ Failed: {command}")
            print(f"   Error: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print(f"⏱️ Timeout: {command}")
    except Exception as e:
        print(f"❌ Error running {command}: {e}")

    # Give monitor time to process events
    time.sleep(0.5)


def main():
    print("=" * 60)
    print("Claude MPM Dashboard Live Test")
    print("=" * 60)
    print("\nThis script will run actual Claude MPM commands to generate")
    print("events that should appear in your dashboard.\n")

    # Check if monitor is running
    print("1️⃣ Checking if monitor is running...")
    run_claude_mpm_command("./scripts/claude-mpm monitor status")

    # Run various commands that should generate events
    print("\n2️⃣ Running test commands to generate events...\n")

    # These commands will generate hook events that should be captured
    commands = [
        "./scripts/claude-mpm --version",
        "./scripts/claude-mpm agent list",
        "./scripts/claude-mpm memory status",
        "./scripts/claude-mpm ticket list --limit 5",
    ]

    for cmd in commands:
        run_claude_mpm_command(cmd)
        time.sleep(1)  # Space out commands

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60)
    print("\n📊 Check your dashboard at http://localhost:5173/dashboard.html")
    print("   You should see events in the Events tab from these commands.")
    print("\n💡 Note: File operations (Read, Write, Edit) will only appear")
    print("   when running actual Claude MPM agent delegations that perform")
    print("   file operations, not from these CLI commands.")


if __name__ == "__main__":
    main()
