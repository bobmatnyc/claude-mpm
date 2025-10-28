#!/usr/bin/env python3
"""Debug hook event format - capture what Claude is actually sending."""

import json
import sys

# Ensure we can import claude_mpm
sys.path.insert(0, "/Users/masa/Projects/claude-mpm/src")


def main():
    """Main entry point that mimics the hook handler's stdin reading."""
    debug_file = "/tmp/claude-hook-debug.json"

    print("DEBUG: Reading from stdin...", file=sys.stderr)

    # Read the raw input that Claude sends
    try:
        raw_input = sys.stdin.read()

        # Save raw input for analysis
        with open(debug_file, "w") as f:
            f.write(raw_input)

        print(f"DEBUG: Raw input saved to {debug_file}", file=sys.stderr)
        print(f"DEBUG: Raw input length: {len(raw_input)}", file=sys.stderr)

        # Try to parse as JSON
        if raw_input.strip():
            try:
                event_data = json.loads(raw_input)
                print("DEBUG: Successfully parsed JSON", file=sys.stderr)
                print(f"DEBUG: Event keys: {list(event_data.keys())}", file=sys.stderr)

                # Check for the hook_event_name field
                if "hook_event_name" in event_data:
                    print(
                        f"DEBUG: hook_event_name = '{event_data['hook_event_name']}'",
                        file=sys.stderr,
                    )
                else:
                    print("DEBUG: NO hook_event_name field found!", file=sys.stderr)

                # Check other potential fields
                for field in ["event", "type", "event_type", "hook_event_type"]:
                    if field in event_data:
                        print(
                            f"DEBUG: Found {field} = '{event_data[field]}'",
                            file=sys.stderr,
                        )

                # Log the full structure
                print("DEBUG: Full event structure:", file=sys.stderr)
                print(json.dumps(event_data, indent=2), file=sys.stderr)

                # Now process normally
                from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

                handler = ClaudeHookHandler()
                handler.process_event(event_data)

            except json.JSONDecodeError as e:
                print(f"DEBUG: Failed to parse JSON: {e}", file=sys.stderr)
                print(f"DEBUG: Raw input was: {raw_input[:200]!r}", file=sys.stderr)
        else:
            print("DEBUG: Empty input received", file=sys.stderr)

    except Exception as e:
        print(f"DEBUG: Error reading stdin: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)

    # Always return continue to not block Claude
    print(json.dumps({"action": "continue"}))


if __name__ == "__main__":
    main()
