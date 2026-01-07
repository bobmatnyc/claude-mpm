#!/usr/bin/env python3
"""Debug hook to see what Claude actually sends."""

import json
import sys
from datetime import datetime

# Log file
log_file = "/tmp/claude-event-debug.log"


def main():
    # Read from stdin
    try:
        input_data = sys.stdin.read()

        # Log the raw input
        with open(log_file, "a") as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Raw input length: {len(input_data)} bytes\n")
            f.write(f"Raw input:\n{input_data}\n")

            # Try to parse as JSON
            try:
                parsed = json.loads(input_data)
                f.write(f"\nParsed JSON:\n{json.dumps(parsed, indent=2)}\n")

                # Log key fields
                f.write("\nKey fields detected:\n")
                for key in [
                    "hook_event_name",
                    "hook_event_type",
                    "type",
                    "event",
                    "event_type",
                ]:
                    if key in parsed:
                        f.write(f"  {key}: {parsed[key]}\n")
            except (json.JSONDecodeError, ValueError, KeyError):
                f.write("\nCould not parse as JSON\n")

        # Always return continue
        print('{"action": "continue"}')

    except Exception as e:
        with open(log_file, "a") as f:
            f.write(f"\nError: {e}\n")
        print('{"action": "continue"}')


if __name__ == "__main__":
    main()
