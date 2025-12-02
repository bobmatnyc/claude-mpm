#!/usr/bin/env python3
"""Test if file handles are being kept open."""

import gc
import sys
from pathlib import Path

import psutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def count_open_files():
    """Count open file descriptors."""
    process = psutil.Process()
    return len(process.open_files())


print(f"Initial open files: {count_open_files()}")

from claude_mpm.core.framework_loader import FrameworkLoader

# Create multiple loaders
loaders = []
for i in range(3):
    print(f"\nCreating FrameworkLoader {i + 1}...")
    loader = FrameworkLoader()
    _ = loader.get_framework_instructions()
    loaders.append(loader)
    print(f"Open files after loader {i + 1}: {count_open_files()}")

# Clear loaders
print("\nClearing loaders...")
loaders.clear()
gc.collect()
print(f"Open files after clearing: {count_open_files()}")

# Now test with SystemInstructionsService
from claude_mpm.services.system_instructions_service import SystemInstructionsService

services = []
for i in range(3):
    print(f"\nCreating SystemInstructionsService {i + 1}...")
    service = SystemInstructionsService()
    _ = service.load_system_instructions()
    services.append(service)
    print(f"Open files after service {i + 1}: {count_open_files()}")

print("\nClearing services...")
services.clear()
gc.collect()
print(f"Open files after clearing services: {count_open_files()}")
