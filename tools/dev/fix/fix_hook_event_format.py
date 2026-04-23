#!/usr/bin/env python3
"""Fix hook event format issues - make handler more flexible."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def patch_hook_handler():
    """Patch the hook handler to be more flexible with event formats."""

    handler_path = (
        Path(__file__).parent.parent
        / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    )

    print("Patching hook handler to accept multiple event formats...")

    # Read the current handler
    content = handler_path.read_text()

    # Find the _route_event method
    old_routing = '''    def _route_event(self, event: dict) -> None:
        """
        Route event to appropriate handler based on type.

        WHY: Centralized routing reduces complexity and makes
        it easier to add new event types.

        Args:
            event: Hook event dictionary
        """
        hook_type = event.get("hook_event_name", "unknown")'''

    new_routing = '''    def _route_event(self, event: dict) -> None:
        """
        Route event to appropriate handler based on type.

        WHY: Centralized routing reduces complexity and makes
        it easier to add new event types.

        Args:
            event: Hook event dictionary
        """
        # Try multiple field names for compatibility
        hook_type = (
            event.get("hook_event_name") or
            event.get("event") or
            event.get("type") or
            event.get("event_type") or
            event.get("hook_event_type") or
            "unknown"
        )

        # Log the actual event structure for debugging
        if DEBUG and hook_type == "unknown":
            print(f"Unknown event format, keys: {list(event.keys())}", file=sys.stderr)
            print(f"Event sample: {str(event)[:200]}", file=sys.stderr)'''

    if old_routing in content:
        content = content.replace(old_routing, new_routing)
        handler_path.write_text(content)
        print("✅ Patched _route_event to accept multiple event formats")
        return True
    print("⚠️ Could not find exact match, trying alternative patch...")

    # Try a simpler patch
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if 'hook_type = event.get("hook_event_name", "unknown")' in line:
            lines[i] = """        # Try multiple field names for compatibility
        hook_type = (
            event.get("hook_event_name") or
            event.get("event") or
            event.get("type") or
            event.get("event_type") or
            event.get("hook_event_type") or
            "unknown"
        )"""
            handler_path.write_text("\n".join(lines))
            print("✅ Applied alternative patch")
            return True

    print("❌ Could not patch hook handler")
    return False


def add_debug_logging():
    """Add more debug logging to capture actual event format."""

    handler_path = (
        Path(__file__).parent.parent
        / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    )
    content = handler_path.read_text()

    # Add debug output right after reading event
    old_parse = """            return json.loads(event_data)
        except (json.JSONDecodeError, ValueError) as e:"""

    new_parse = """            parsed = json.loads(event_data)
            # Debug: Log the actual event format we receive
            if DEBUG:
                print(f"Received event with keys: {list(parsed.keys())}", file=sys.stderr)
                for key in ['hook_event_name', 'event', 'type', 'event_type']:
                    if key in parsed:
                        print(f"  {key} = '{parsed[key]}'", file=sys.stderr)
            return parsed
        except (json.JSONDecodeError, ValueError) as e:"""

    if old_parse in content:
        content = content.replace(old_parse, new_parse)
        handler_path.write_text(content)
        print("✅ Added debug logging for event format")
        return True

    return False


def main():
    """Main entry point."""
    print("=" * 60)
    print("Fixing Hook Event Format Issues")
    print("=" * 60)

    # Apply patches
    success = patch_hook_handler()

    if add_debug_logging():
        success = True

    if success:
        print("\n✅ Patches applied successfully!")
        print("\nNext steps:")
        print("1. The hook handler will now accept multiple event formats")
        print("2. Debug logging will show the actual event format")
        print("3. Try using Claude tools and check /tmp/claude-mpm-hook-error.log")
        print("4. The dashboard should start showing events")
    else:
        print("\n❌ Failed to apply patches")
        print("Please check the hook handler manually")


if __name__ == "__main__":
    main()
