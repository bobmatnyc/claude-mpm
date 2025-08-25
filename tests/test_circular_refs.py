#!/usr/bin/env python3
"""Test for circular references preventing garbage collection."""

import gc
import sys
import weakref
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Enable garbage collection debugging
gc.set_debug(gc.DEBUG_SAVEALL)

from claude_mpm.core.framework_loader import FrameworkLoader

print("Creating FrameworkLoader...")
loader = FrameworkLoader()
instructions = loader.get_framework_instructions()

# Create weak reference to track if object is collected
weak_ref = weakref.ref(loader)

print(f"Loader exists: {weak_ref() is not None}")
print(f"Instructions length: {len(instructions)}")

# Check what's referencing the loader
import sys

print(
    f"\nReference count for loader: {sys.getrefcount(loader) - 1}"
)  # -1 for the getrefcount call itself

# Get referrers
referrers = gc.get_referrers(loader)
print(f"Number of referrers: {len(referrers)}")
for i, ref in enumerate(referrers[:5]):  # Show first 5 referrers
    print(f"  Referrer {i}: {type(ref)}")
    if hasattr(ref, "__name__"):
        print(f"    Name: {ref.__name__}")

# Clear the loader
print("\nClearing loader reference...")
del loader
gc.collect()

print(f"Loader exists after del: {weak_ref() is not None}")

# Check for uncollectable garbage
garbage = gc.garbage
if garbage:
    print(f"\nUncollectable garbage found: {len(garbage)} objects")
    for obj in garbage[:5]:
        print(f"  {type(obj)}")
else:
    print("\nNo uncollectable garbage")

# Now test with multiple loaders
print("\n" + "=" * 50)
print("Testing multiple loaders...")

weak_refs = []
for i in range(3):
    loader = FrameworkLoader()
    _ = loader.get_framework_instructions()
    weak_refs.append(weakref.ref(loader))
    del loader

gc.collect()

alive_count = sum(1 for ref in weak_refs if ref() is not None)
print(f"Loaders still alive: {alive_count}/{len(weak_refs)}")

# Disable debug mode
gc.set_debug(0)
