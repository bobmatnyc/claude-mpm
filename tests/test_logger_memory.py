#!/usr/bin/env python3
"""Test if loggers are causing memory retention."""

import gc
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Show all existing loggers before
print("Loggers before creating FrameworkLoader:")
for name in sorted(logging.Logger.manager.loggerDict.keys()):
    if "claude_mpm" in name:
        print(f"  {name}")

# Now create a FrameworkLoader
from claude_mpm.core.framework_loader import FrameworkLoader

loader1 = FrameworkLoader()
print("\nLoggers after creating FrameworkLoader 1:")
for name in sorted(logging.Logger.manager.loggerDict.keys()):
    if "claude_mpm" in name and "framework" in name.lower():
        print(f"  {name}")

loader2 = FrameworkLoader()
print("\nLoggers after creating FrameworkLoader 2:")
for name in sorted(logging.Logger.manager.loggerDict.keys()):
    if "claude_mpm" in name and "framework" in name.lower():
        print(f"  {name}")

# Clear loaders
del loader1
del loader2
gc.collect()

print("\nLoggers still exist after deleting loaders:")
for name in sorted(logging.Logger.manager.loggerDict.keys()):
    if "claude_mpm" in name and "framework" in name.lower():
        logger = logging.getLogger(name)
        print(f"  {name} - handlers: {len(logger.handlers)}")

print("\nTotal loggers in system:", len(logging.Logger.manager.loggerDict))
