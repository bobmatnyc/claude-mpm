#!/usr/bin/env python3
"""Debug path detection logic."""

from pathlib import Path

# Simulate what happens in paths.py
file_path = Path("/Users/masa/Projects/claude-mpm/src/claude_mpm/config/paths.py")
print(f"File path: {file_path}")
print(f"Resolved: {file_path.resolve()}")
print("\nParents:")

for i, parent in enumerate(file_path.resolve().parents):
    print(f"  Level {i}: {parent}")

print("\nChecking for markers:")
markers = ["pyproject.toml", "setup.py", "VERSION", ".git"]

for parent in file_path.resolve().parents:
    found = [m for m in markers if (parent / m).exists()]
    if found:
        print(f"✓ Found markers at {parent}: {found}")
        print("  This should be the project root!")
        break
    else:
        print(f"✗ No markers at {parent}")
