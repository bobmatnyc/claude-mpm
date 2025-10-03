#!/usr/bin/env python3
"""
Fix script to prevent watchdog from causing dashboard disconnections.

This script creates a patch that disables watchdog when running with --monitor flag
or when CLAUDE_MPM_NO_WATCH environment variable is set.
"""

import sys
from pathlib import Path


def create_patch():
    """Create a patch file to fix the watchdog issue."""

    print("=" * 60)
    print("🔧 WATCHDOG DISCONNECTION FIX")
    print("=" * 60)
    print("\nThis script will create a patch to prevent watchdog from")
    print("causing dashboard disconnections when using --monitor mode.\n")

    # Find the modification tracker file
    tracker_file = Path("src/claude_mpm/services/agents/registry/modification_tracker.py")

    if not tracker_file.exists():
        print(f"❌ Could not find {tracker_file}")
        print("   Please run this script from the claude-mpm root directory")
        return False

    print(f"✅ Found modification tracker at: {tracker_file}")

    # Read the current file
    with open(tracker_file) as f:
        content = f.read()

    # Check if already patched
    if "CLAUDE_MPM_NO_WATCH" in content:
        print("\n⚠️  File appears to already be patched!")
        print("   The CLAUDE_MPM_NO_WATCH check is already present.")
        return True

    # Create the patch
    patch_content = '''
# PATCH: Added environment variable check to disable watchdog
# This prevents dashboard disconnections when using --monitor mode
# Set CLAUDE_MPM_NO_WATCH=1 to disable file watching
def _should_enable_watchdog(self) -> bool:
    """Check if watchdog monitoring should be enabled."""
    # Check environment variable
    if os.environ.get('CLAUDE_MPM_NO_WATCH', '').lower() in ('1', 'true', 'yes'):
        self.logger.info("Watchdog monitoring disabled by CLAUDE_MPM_NO_WATCH environment variable")
        return False

    # Check if running in monitor mode (passed via service initialization)
    if hasattr(self, '_monitor_mode') and self._monitor_mode:
        self.logger.info("Watchdog monitoring disabled in monitor mode")
        return False

    return True
'''

    # Find where to insert the patch - look for the start_monitoring method
    if "def start_monitoring" in content:
        print("\n📝 Creating patched version...")

        # Add the helper method before start_monitoring
        import_idx = content.find("from watchdog.observers import Observer")
        if import_idx != -1:
            # Add os import if not present
            if "import os" not in content[:import_idx]:
                content = content[:import_idx] + "import os\n" + content[import_idx:]

        # Find the start_monitoring method and modify it
        start_monitoring_idx = content.find("def start_monitoring")
        if start_monitoring_idx != -1:
            # Insert the helper method before start_monitoring
            method_start = content.rfind("\n", 0, start_monitoring_idx)
            if method_start != -1:
                # Insert the new method
                content = content[:method_start] + "\n" + patch_content + content[method_start:]

                # Now modify start_monitoring to check the flag
                # Find the observer.start() call
                observer_start_idx = content.find("self.observer.start()", start_monitoring_idx)
                if observer_start_idx != -1:
                    # Find the line start
                    line_start = content.rfind("\n", 0, observer_start_idx) + 1
                    indent = len(content[line_start:observer_start_idx]) - len(content[line_start:observer_start_idx].lstrip())
                    indent_str = content[line_start:line_start + indent]

                    # Replace the observer.start() with conditional check
                    content[line_start:content.find("\n", observer_start_idx)]
                    new_lines = f'''{indent_str}# Check if watchdog should be enabled
{indent_str}if self._should_enable_watchdog():
{indent_str}    self.observer.start()
{indent_str}    self.logger.info("File system monitoring started")
{indent_str}else:
{indent_str}    self.logger.info("File system monitoring disabled")'''

                    content = content[:line_start] + new_lines + content[content.find("\n", observer_start_idx):]

                    print("✅ Patch created successfully!")
                else:
                    print("❌ Could not find observer.start() call")
                    return False
        else:
            print("❌ Could not find start_monitoring method")
            return False
    else:
        print("❌ Could not find start_monitoring method in file")
        return False

    # Save backup
    backup_file = tracker_file.with_suffix('.py.backup')
    print(f"\n📦 Creating backup at: {backup_file}")
    with open(backup_file, 'w') as f, open(tracker_file) as orig:
        f.write(orig.read())

    # Write patched file
    print(f"💾 Writing patched file to: {tracker_file}")
    with open(tracker_file, 'w') as f:
        f.write(content)

    print("\n✅ Patch applied successfully!")

    return True


def create_wrapper_script():
    """Create a wrapper script to run claude-mpm with watchdog disabled."""

    wrapper_content = '''#!/bin/bash
# Wrapper script to run claude-mpm with watchdog disabled
# This prevents dashboard disconnections when using --monitor

export CLAUDE_MPM_NO_WATCH=1
echo "🔧 Running claude-mpm with watchdog disabled (CLAUDE_MPM_NO_WATCH=1)"
exec claude-mpm "$@"
'''

    wrapper_file = Path("claude-mpm-no-watch")
    print(f"\n📝 Creating wrapper script: {wrapper_file}")

    with open(wrapper_file, 'w') as f:
        f.write(wrapper_content)

    # Make executable
    wrapper_file.chmod(0o755)

    print(f"✅ Wrapper script created: {wrapper_file}")
    print("   Use: ./claude-mpm-no-watch run --monitor")

    return True


def test_fix():
    """Test if the fix works."""

    print("\n" + "=" * 60)
    print("🧪 TESTING FIX")
    print("=" * 60)

    print("\nTo test the fix:")
    print("1. Run with environment variable:")
    print("   CLAUDE_MPM_NO_WATCH=1 claude-mpm run --monitor")
    print("\n2. Or use the wrapper script:")
    print("   ./claude-mpm-no-watch run --monitor")
    print("\n3. Then run the diagnostic script:")
    print("   python diagnose_disconnections.py 60")
    print("\n4. Check if server restarts are eliminated")

    print("\n" + "=" * 60)


def main():
    """Main function."""

    # Check if we're in the right directory
    if not Path("src/claude_mpm").exists():
        print("❌ Error: Please run this script from the claude-mpm root directory")
        sys.exit(1)

    print("This script will:")
    print("1. Patch modification_tracker.py to respect CLAUDE_MPM_NO_WATCH")
    print("2. Create a wrapper script for easy usage")
    print("3. Provide testing instructions\n")

    response = input("Continue? (y/N): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        return

    # Apply patch
    if not create_patch():
        print("\n❌ Failed to apply patch")
        sys.exit(1)

    # Create wrapper
    create_wrapper_script()

    # Show testing instructions
    test_fix()

    print("\n✅ Fix complete!")
    print("\n⚠️  IMPORTANT: The fix modifies modification_tracker.py")
    print("   A backup was created at modification_tracker.py.backup")
    print("   To revert: cp src/claude_mpm/services/agents/registry/modification_tracker.py.backup src/claude_mpm/services/agents/registry/modification_tracker.py")


if __name__ == "__main__":
    main()
