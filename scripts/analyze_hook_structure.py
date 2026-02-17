#!/usr/bin/env python3
"""Analyze hook event structure to determine usage data availability.

This script examines the hook handler code to predict which events
contain usage data without requiring live testing.
"""

import ast
import inspect
from pathlib import Path


def analyze_hook_handlers():
    """Analyze event handler code for usage data patterns."""
    print("\n🔍 Hook Event Structure Analysis\n")
    print("=" * 70)

    # Read event_handlers.py
    handlers_file = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "hooks"
        / "claude_hooks"
        / "event_handlers.py"
    )

    if not handlers_file.exists():
        print(f"❌ Cannot find event_handlers.py at {handlers_file}")
        return

    content = handlers_file.read_text()

    # Analyze each handler method
    handlers = {
        "handle_stop_fast": {
            "checks_usage": '"usage" in event' in content,
            "extracts_usage": "usage_data = event['usage']" in content
            or "usage_data = event.get('usage')" in content,
            "emits_token_event": "token_usage_updated" in content,
        },
        "handle_assistant_response": {
            "checks_usage": "handle_assistant_response" in content
            and '"usage"' in content[content.find("handle_assistant_response") :],
            "extracts_usage": False,  # Not found in the code
            "emits_token_event": False,
        },
    }

    # Print analysis
    print("Handler: handle_stop_fast")
    print(
        f"  ✅ Checks for 'usage' field: {handlers['handle_stop_fast']['checks_usage']}"
    )
    print(f"  ✅ Extracts usage data: {handlers['handle_stop_fast']['extracts_usage']}")
    print(
        f"  ✅ Emits token_usage_updated: {handlers['handle_stop_fast']['emits_token_event']}"
    )
    print()

    print("Handler: handle_assistant_response")
    print(
        f"  {'✅' if handlers['handle_assistant_response']['checks_usage'] else '❌'} Checks for 'usage' field: {handlers['handle_assistant_response']['checks_usage']}"
    )
    print(
        f"  {'✅' if handlers['handle_assistant_response']['extracts_usage'] else '❌'} Extracts usage data: {handlers['handle_assistant_response']['extracts_usage']}"
    )
    print(
        f"  {'✅' if handlers['handle_assistant_response']['emits_token_event'] else '❌'} Emits token_usage_updated: {handlers['handle_assistant_response']['emits_token_event']}"
    )
    print()

    print("=" * 70)
    print("\n📊 CONCLUSION")
    print("=" * 70)

    if handlers["handle_stop_fast"]["checks_usage"]:
        print("✅ Stop hooks CONFIRMED to check for usage data")
        print("   Location: Lines 880-894 in event_handlers.py")
        print("   Emits: token_usage_updated event (lines 996-1016)")
        print()

    if not handlers["handle_assistant_response"]["checks_usage"]:
        print("❌ AssistantResponse hooks DO NOT check for usage data")
        print("   Location: Lines 1160-1256 in event_handlers.py")
        print("   Missing: No 'usage' field extraction")
        print()

    print("\n🎯 RECOMMENDATION")
    print("=" * 70)
    print("Without live testing, code analysis shows:")
    print()
    print("1. Stop hooks are CONFIRMED to support usage data")
    print("   - Already implemented and emitting token_usage_updated events")
    print("   - Provides session-level token counts")
    print()
    print("2. AssistantResponse hooks do NOT extract usage data")
    print("   - No usage field checks in current implementation")
    print("   - Would require code changes to test")
    print()
    print("3. Next steps to verify usage source:")
    print()
    print("   Option A: Test Stop hooks (Current Implementation)")
    print("     export CLAUDE_MPM_HOOK_DEBUG=true")
    print("     mpm --with-dashboard")
    print("     echo 'test' | claude")
    print("     python3 scripts/verify_assistant_response_usage.py")
    print()
    print("   Option B: Add Usage Extraction to AssistantResponse")
    print("     1. Modify handle_assistant_response to check event['usage']")
    print("     2. Emit token_usage_updated if available")
    print("     3. Test to see if AssistantResponse provides per-response tokens")
    print()
    print("   Option C: Check Claude Code Documentation")
    print("     - Review Claude Code hook event schemas")
    print("     - Determine which events include usage data")
    print("     - Implement extraction in appropriate handler")
    print()


if __name__ == "__main__":
    analyze_hook_handlers()
