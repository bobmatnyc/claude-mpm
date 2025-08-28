#!/usr/bin/env python3
"""Test that dashboard Code tab fixes are working."""

import subprocess
import time

print("Testing dashboard Code tab fixes...")
print("=" * 50)

# Start dashboard
print("\n1. Starting dashboard...")
proc = subprocess.Popen(
    ["./scripts/claude-mpm", "--use-venv", "dashboard", "start", "--port", "8765"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

time.sleep(5)  # Wait for startup

print("2. Dashboard should be running at http://localhost:8765")
print("3. Open the dashboard and go to the Code tab")
print("\nVerify the following fixes:")
print("  ✓ Code tree should discover only from the working directory")
print("  ✓ Not from the root directory")
print("  ✓ Nodes should have proper spacing in both layouts")
print("  ✓ Text labels should not overlap in radial layout")
print("\nPress Ctrl+C to stop the dashboard when done testing...")

try:
    proc.wait()
except KeyboardInterrupt:
    print("\n\nStopping dashboard...")
    proc.terminate()
    time.sleep(1)
    proc.kill()
    print("Dashboard stopped.")