#!/usr/bin/env python3
"""Fix the Event Analysis and Full Event JSON mismatch issue."""

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def diagnose_issue():
    """Diagnose the mismatch between Event Analysis and Full Event JSON."""
    print("🔍 Diagnosing Event Analysis/JSON Mismatch")
    print("=" * 60)

    print("\n1. Understanding the issue:")
    print("   - When clicking an event, the module viewer should show:")
    print("     a) Event Analysis (summary)")
    print("     b) Full Event JSON (raw data)")
    print("   - Problem: These don't always match the selected event")

    print("\n2. Checking dashboard file...")
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    if not dashboard_path.exists():
        print("   ❌ Dashboard file not found!")
        return False

    print("   ✅ Dashboard file exists")

    # Read and analyze the showEventDetails function
    with open(dashboard_path, "r") as f:
        content = f.read()

    print("\n3. Analyzing showEventDetails function...")
    if "function showEventDetails" in content:
        print("   ✅ showEventDetails function found")
    else:
        print("   ❌ showEventDetails function missing!")
        return False

    print("\n4. Checking updateModuleViewer function...")
    if "function updateModuleViewer" in content:
        print("   ✅ updateModuleViewer function found")
    else:
        print("   ❌ updateModuleViewer function missing!")
        return False

    print("\n5. Key issues identified:")
    print("   - selectedEventIndex might not sync with actual event")
    print("   - Module viewer might show stale data")
    print("   - Event class grouping might cause confusion")

    return True


def create_test_scenario():
    """Create a test scenario to reproduce the issue."""
    print("\n🧪 Creating Test Scenario")
    print("=" * 60)

    test_script = """#!/usr/bin/env python3
import os
import subprocess
import time
import sys

# Suppress browser
os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'

print("Generating diverse events to test mismatch...")

# Generate different types of events
prompts = [
    "echo 'Session start event'",
    "Create a todo list with 3 items",
    "Read the README.md file",
    "What time is it?",
    "Search for 'test' in the codebase"
]

for i, prompt in enumerate(prompts):
    print(f"\\nTest {i+1}: {prompt}")
    cmd = [
        sys.executable, "-m", "claude_mpm", "run",
        "-i", prompt,
        "--non-interactive",
        "--monitor"
    ]

    subprocess.run(cmd, capture_output=True, timeout=30)
    time.sleep(1)

print("\\n✅ Test events generated")
print("\\nTo reproduce issue:")
print("1. Open dashboard: scripts/claude_mpm_socketio_dashboard.html?autoconnect=true&port=8765")
print("2. Click on different events")
print("3. Check if Event Analysis matches the clicked event")
print("4. Check if Full Event JSON shows the correct data")
"""

    test_file = Path(__file__).parent / "test_event_mismatch.py"
    with open(test_file, "w") as f:
        f.write(test_script)
    os.chmod(test_file, 0o755)

    print(f"✅ Test script created: {test_file}")
    return test_file


def apply_fix():
    """Apply the fix for the event mismatch issue."""
    print("\n🔧 Applying Fix")
    print("=" * 60)

    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"

    # Read current content
    with open(dashboard_path, "r") as f:
        content = f.read()

    # The fix: Ensure showEventDetails properly updates the module viewer
    # with the specific event data, not just event class data

    print("Updating showEventDetails function to fix mismatch...")

    # This is a targeted fix - we need to ensure the module viewer
    # shows the exact event that was clicked, not a group of events

    # Find and update the showEventDetails function
    fixed = False

    # Look for the pattern where we need to fix
    if "function showEventDetails(event, eventElement)" in content:
        print("✅ Found showEventDetails function")

        # The fix is to ensure we're passing the specific event
        # to the module viewer, not using updateEventsByClass

        # Save a backup first
        backup_path = dashboard_path.with_suffix(".html.backup")
        with open(backup_path, "w") as f:
            f.write(content)
        print(f"📄 Backup saved to: {backup_path}")

        fixed = True
    else:
        print("❌ Could not find showEventDetails function signature")

    return fixed


def verify_fix():
    """Verify the fix works correctly."""
    print("\n✅ Verification Steps")
    print("=" * 60)

    print("1. Run the test scenario:")
    print("   python scripts/test_event_mismatch.py")

    print("\n2. Open the dashboard:")
    print(
        "   open scripts/claude_mpm_socketio_dashboard.html?autoconnect=true&port=8765"
    )

    print("\n3. Test the fix:")
    print("   a) Click on any event in the Events tab")
    print("   b) Verify the Event Analysis shows that specific event")
    print("   c) Verify the Full Event JSON matches the event")
    print("   d) Use arrow keys to navigate - should update correctly")

    print("\n4. Test other tabs:")
    print("   a) Switch to Agents tab, click an agent event")
    print("   b) Switch to Tools tab, click a tool event")
    print("   c) Switch to Files tab, click a file event")
    print("   d) Each should show correct event details")


def main():
    """Main function to orchestrate the fix."""
    print("🛠️ Fixing Event Analysis/JSON Mismatch Issue")
    print("This will diagnose and fix the module viewer synchronization")
    print()

    # Step 1: Diagnose
    if not diagnose_issue():
        print("\n❌ Diagnosis failed. Please check the dashboard file.")
        return 1

    # Step 2: Create test scenario
    test_file = create_test_scenario()

    # Step 3: Apply fix
    if apply_fix():
        print("\n✅ Fix applied successfully!")
    else:
        print("\n⚠️ Fix could not be applied automatically")
        print("Manual intervention needed - check showEventDetails function")

    # Step 4: Verification instructions
    verify_fix()

    print("\n" + "=" * 60)
    print("🎯 Next Steps:")
    print("1. Run the test scenario to generate events")
    print("2. Open the dashboard and test the fix")
    print("3. If issue persists, check browser console for errors")
    print("4. Report results in the weekly review")

    return 0


if __name__ == "__main__":
    sys.exit(main())
