#!/usr/bin/env python3
"""Verify if AssistantResponse hook events contain token usage data.

This script analyzes hook handler logs to check if AssistantResponse events
include the 'usage' field needed for token tracking.

Usage:
    1. Enable debug logging: export CLAUDE_MPM_HOOK_DEBUG=true
    2. Trigger Claude interaction (any prompt)
    3. Run this script: python3 verify_assistant_response_usage.py
"""

import json
import os
from datetime import datetime
from pathlib import Path


def find_hook_logs():
    """Find hook handler log file."""
    log_dir = Path.home() / ".claude-mpm" / "logs"
    if not log_dir.exists():
        return None

    # Look for hook_handler.log
    log_file = log_dir / "hook_handler.log"
    if log_file.exists():
        return log_file

    return None


def analyze_assistant_response_events(log_file):
    """Analyze AssistantResponse events in log file."""
    print(f"Analyzing log file: {log_file}\n")

    if not log_file.exists():
        print(f"❌ Log file not found: {log_file}")
        print("\nTroubleshooting:")
        print("1. Enable debug: export CLAUDE_MPM_HOOK_DEBUG=true")
        print("2. Trigger Claude interaction")
        print("3. Check log location: ~/.claude-mpm/logs/hook_handler.log")
        return

    try:
        content = log_file.read_text()
    except Exception as e:
        print(f"❌ Failed to read log file: {e}")
        return

    if not content.strip():
        print("❌ Log file is empty")
        print("\nActions:")
        print("1. Verify debug mode: echo $CLAUDE_MPM_HOOK_DEBUG")
        print("2. Trigger a Claude interaction")
        print("3. Re-run this script")
        return

    # Search for AssistantResponse events
    lines = content.split("\n")
    assistant_response_count = 0
    has_usage_field = False

    print("=" * 60)
    print("SEARCHING FOR AssistantResponse EVENTS")
    print("=" * 60)

    for i, line in enumerate(lines):
        if "AssistantResponse" in line:
            assistant_response_count += 1
            print(f"\n[Event {assistant_response_count}] Line {i + 1}:")
            print(f"  {line[:200]}")

            # Check next 20 lines for usage field
            context = "\n".join(lines[i : i + 20])
            if '"usage"' in context or "'usage'" in context:
                has_usage_field = True
                print("  ✅ USAGE FIELD FOUND!")

                # Extract usage data
                for j in range(i, min(i + 20, len(lines))):
                    if "usage" in lines[j].lower():
                        print(f"    {lines[j].strip()}")

    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    print(f"AssistantResponse events found: {assistant_response_count}")
    print(f"Usage field present: {'✅ YES' if has_usage_field else '❌ NO'}")

    if assistant_response_count == 0:
        print("\n⚠️  NO AssistantResponse EVENTS FOUND")
        print("\nPossible reasons:")
        print("1. Debug logging not enabled")
        print("2. No Claude interactions since enabling debug")
        print("3. Log file from before debug was enabled")
        print("\nNext steps:")
        print("1. export CLAUDE_MPM_HOOK_DEBUG=true")
        print("2. Run a simple Claude prompt: echo 'hello' | claude")
        print("3. Re-run this script")

    elif not has_usage_field:
        print("\n❌ CONFIRMED: AssistantResponse does NOT contain usage field")
        print("\nThis confirms that token usage is NOT available from:")
        print("  - Stop hooks")
        print("  - AssistantResponse hooks")
        print("\nRequired action:")
        print("  - Investigate Claude Code internal API")
        print("  - Check for alternative hook events")
        print("  - Request Claude Code enhancement")

    else:
        print("\n✅ SUCCESS: AssistantResponse CONTAINS usage data!")
        print("\nNext steps:")
        print("1. Update event_handlers.py to extract usage from AssistantResponse")
        print("2. Emit token_usage_updated events from AssistantResponse handler")
        print("3. Test token tracking dashboard")

    print("\n" + "=" * 60)


def main():
    print("\n🔍 Token Usage Source Verification\n")

    # Check if debug mode is enabled
    debug_enabled = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "false").lower() == "true"
    print(f"Debug mode: {'✅ ENABLED' if debug_enabled else '❌ DISABLED'}")

    if not debug_enabled:
        print("\n⚠️  Warning: Debug logging is not enabled")
        print("Enable with: export CLAUDE_MPM_HOOK_DEBUG=true")
        print("Then trigger a Claude interaction before running this script\n")

    # Find log file
    log_file = find_hook_logs()
    if not log_file:
        print("\n❌ No hook handler logs found")
        print("Expected location: ~/.claude-mpm/logs/hook_handler.log")
        print("\nActions:")
        print("1. Enable debug: export CLAUDE_MPM_HOOK_DEBUG=true")
        print("2. Trigger Claude: echo 'test' | claude")
        print("3. Re-run this script")
        return

    print(f"Log file: {log_file}")
    print(f"Size: {log_file.stat().st_size} bytes")
    print(f"Modified: {datetime.fromtimestamp(log_file.stat().st_mtime)}\n")

    # Analyze events
    analyze_assistant_response_events(log_file)


if __name__ == "__main__":
    main()
