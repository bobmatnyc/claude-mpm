#!/usr/bin/env python3
"""
Cleanup script for orphaned hook handler processes.

This script can be run periodically to clean up any hook_handler.py
processes that have been running for too long and are likely orphaned.
"""

import sys
import time
from pathlib import Path

# Add the src directory to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import psutil

from claude_mpm.utils.subprocess_utils import (
    cleanup_orphaned_processes,
)


def main():
    """Main cleanup function."""
    print("🧹 Claude MPM Hook Handler Cleanup")
    print("=" * 50)

    # First, show current hook handler processes
    hook_processes = []
    for process in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            cmdline = " ".join(process.info["cmdline"] or [])
            if "hook_handler.py" in cmdline:
                age_minutes = (time.time() - process.info["create_time"]) / 60
                hook_processes.append(
                    {
                        "pid": process.info["pid"],
                        "age_minutes": age_minutes,
                        "cmdline": cmdline,
                    }
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    print(f"📊 Found {len(hook_processes)} hook handler processes:")
    for proc in hook_processes:
        status = (
            "🟢 Recent"
            if proc["age_minutes"] < 5
            else "🟡 Old" if proc["age_minutes"] < 60 else "🔴 Orphaned"
        )
        print(f"  {status} PID {proc['pid']}: {proc['age_minutes']:.1f} minutes old")

    if not hook_processes:
        print("✅ No hook handler processes found")
        return

    # Clean up processes older than 5 minutes (likely orphaned)
    print("\n🧹 Cleaning up processes older than 5 minutes...")
    cleanup_count = cleanup_orphaned_processes("hook_handler.py", max_age_hours=5 / 60)

    if cleanup_count > 0:
        print(f"✅ Cleaned up {cleanup_count} orphaned processes")
    else:
        print("✅ No orphaned processes to clean up")

    # Show remaining processes
    remaining = []
    for process in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            cmdline = " ".join(process.info["cmdline"] or [])
            if "hook_handler.py" in cmdline:
                age_minutes = (time.time() - process.info["create_time"]) / 60
                remaining.append(
                    {"pid": process.info["pid"], "age_minutes": age_minutes}
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    print(f"\n📈 {len(remaining)} processes remaining:")
    for proc in remaining:
        print(f"  🟢 PID {proc['pid']}: {proc['age_minutes']:.1f} minutes old")


if __name__ == "__main__":
    main()
