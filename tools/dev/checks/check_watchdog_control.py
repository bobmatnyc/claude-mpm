#!/usr/bin/env python3
"""
Check how watchdog is controlled in the codebase and if it can be disabled.
"""

import subprocess
from pathlib import Path


def find_watchdog_control():
    """Find where watchdog is initialized and controlled."""
    print("=" * 60)
    print("🔍 WATCHDOG CONTROL ANALYSIS")
    print("=" * 60)

    # Check for watchdog initialization
    print("\n1. Looking for watchdog initialization...")

    try:
        # Find where Observer is initialized
        result = subprocess.run(
            ["grep", "-n", "Observer()", "-r", "src/"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        if result.stdout:
            print("   Found Observer initialization:")
            for line in result.stdout.strip().split("\n")[:5]:
                print(f"      {line}")
        else:
            print("   ✅ No direct Observer() initialization found")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Check for watchdog start calls
    print("\n2. Looking for observer.start() calls...")

    try:
        result = subprocess.run(
            ["grep", "-n", "observer.start\\|self.observer.start", "-r", "src/"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        if result.stdout:
            print("   Found observer.start() calls:")
            for line in result.stdout.strip().split("\n")[:5]:
                print(f"      {line}")
        else:
            print("   ✅ No observer.start() calls found")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Check for modification tracker usage
    print("\n3. Checking AgentModificationTracker usage...")

    try:
        result = subprocess.run(
            [
                "grep",
                "-n",
                "AgentModificationTracker\\|modification_tracker",
                "-r",
                "src/",
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        if result.stdout:
            lines = result.stdout.strip().split("\n")
            print(f"   Found {len(lines)} references to AgentModificationTracker")

            # Show unique files
            files = set()
            for line in lines:
                if ":" in line:
                    file_path = line.split(":")[0]
                    files.add(file_path)

            print("   Files using modification tracker:")
            for f in list(files)[:10]:
                print(f"      {f}")

        else:
            print("   ✅ No modification tracker references found")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Check for environment variable checks
    print("\n4. Looking for environment variable checks...")

    env_vars = [
        "CLAUDE_MPM_NO_WATCH",
        "NO_WATCH",
        "DISABLE_WATCH",
        "DISABLE_AUTO_RELOAD",
        "WATCHDOG_ENABLED",
        "NO_FILE_WATCH",
    ]

    for var in env_vars:
        try:
            result = subprocess.run(
                ["grep", "-n", var, "-r", "src/"],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                check=False,
            )

            if result.stdout:
                print(f"   ⚠️  Found {var} checks:")
                for line in result.stdout.strip().split("\n")[:3]:
                    print(f"      {line}")

        except Exception:
            pass

    print("\n5. Checking if --monitor flag affects watchdog...")

    try:
        # Look for monitor flag handling
        result = subprocess.run(
            [
                "grep",
                "-n",
                "-A5",
                "-B5",
                "args.monitor\\|--monitor",
                "src/claude_mpm/cli/commands/run.py",
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        if result.stdout:
            print("   Found --monitor flag handling in run.py")
            # Check if it affects watchdog
            if (
                "watchdog" in result.stdout.lower()
                or "observer" in result.stdout.lower()
            ):
                print("   ⚠️  --monitor flag may interact with watchdog!")
            else:
                print("   ✅ --monitor flag doesn't seem to control watchdog")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("📊 ANALYSIS SUMMARY")
    print("=" * 60)

    print("\n🔧 POTENTIAL SOLUTIONS:")
    print("\n1. Add environment variable check to disable watchdog:")
    print("   In modification_tracker.py, check for CLAUDE_MPM_NO_WATCH")
    print("   and skip observer.start() if set")

    print("\n2. Add --no-watch flag to run command:")
    print("   Modify run.py to accept --no-watch and pass to services")

    print("\n3. Disable watchdog when --monitor is used:")
    print("   Auto-disable file watching in monitor mode")

    print("\n💡 RECOMMENDED FIX:")
    print("   Set environment variable before running:")
    print("   export CLAUDE_MPM_NO_WATCH=1")
    print("   claude-mpm run --monitor")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    find_watchdog_control()
