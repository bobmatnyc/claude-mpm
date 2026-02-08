#!/usr/bin/env python3
"""Patch to add usage extraction to AssistantResponse handler.

This patch enables testing whether AssistantResponse events contain
usage data by adding usage extraction code similar to Stop handler.

EXPERIMENTAL: Apply this patch to test if usage data is available
in AssistantResponse events.
"""


def generate_patch():
    """Generate patch instructions for handle_assistant_response."""
    print("\n📝 Patch Instructions for AssistantResponse Usage Extraction\n")
    print("=" * 70)
    print("File: src/claude_mpm/hooks/claude_hooks/event_handlers.py")
    print("Method: handle_assistant_response (line 1160)")
    print()
    print("Add after line 1193 (after response_text extraction):")
    print()
    print("```python")
    print("        # EXPERIMENTAL: Check if usage data is available in AssistantResponse")
    print('        if "usage" in event:')
    print("            usage_data = event['usage']")
    print("            assistant_response_data['usage'] = {")
    print("                'input_tokens': usage_data.get('input_tokens', 0),")
    print("                'output_tokens': usage_data.get('output_tokens', 0),")
    print(
        "                'cache_creation_tokens': usage_data.get('cache_creation_input_tokens', 0),"
    )
    print(
        "                'cache_read_tokens': usage_data.get('cache_read_input_tokens', 0),"
    )
    print("            }")
    print("            if DEBUG:")
    print(
        "                _log(f'AssistantResponse contains usage data: {usage_data}')"
    )
    print("```")
    print()
    print("=" * 70)
    print("\n🧪 Testing Steps:")
    print("=" * 70)
    print("1. Apply patch above to event_handlers.py")
    print("2. Restart MPM: mpm --with-dashboard")
    print("3. Enable debug: export CLAUDE_MPM_HOOK_DEBUG=true")
    print("4. Trigger Claude: echo 'test' | claude")
    print("5. Check logs: tail -f ~/.claude-mpm/logs/hook_handler.log")
    print("6. Look for: 'AssistantResponse contains usage data'")
    print()
    print("If found: ✅ AssistantResponse provides per-response token counts")
    print("If not found: ❌ Only Stop hooks provide usage data (session-level)")
    print()


if __name__ == "__main__":
    generate_patch()
