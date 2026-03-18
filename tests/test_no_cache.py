#!/usr/bin/env python3
"""Test memory routing in capabilities without cache."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_no_cache():
    """Test capabilities generation without cache."""

    print("Testing Memory Routing Display (No Cache)")
    print("=" * 50)

    # Initialize framework loader
    framework_loader = FrameworkLoader()

    # Clear all caches to force regeneration
    print("\n1. Clearing all caches...")
    framework_loader.clear_all_caches()
    print("   Caches cleared")

    # Generate capabilities
    print("\n2. Generating capabilities section...")
    capabilities = framework_loader._generate_agent_capabilities_section()

    # Check for memory routing (case-insensitive to be safe)
    if "Memory Routing:" in capabilities or "memory routing:" in capabilities:
        print("   ✓ Memory routing found in capabilities!")

        # Count occurrences
        count = capabilities.count("Memory Routing:")
        print(f"   Found {count} agents with memory routing")

        # Show examples
        print("\n3. Example agents with memory routing:")

        # Find and display a few examples
        lines = capabilities.split("\n")
        current_agent = None

        for line in lines:
            if line.startswith("### "):
                # Extract agent name
                import re

                match = re.search(r"### (.+) \(`(.+)`\)", line)
                if match:
                    current_agent = match.group(2)
            elif "Memory Routing:" in line and current_agent:
                print(f"   {current_agent}: {line.strip()[:100]}...")
                current_agent = None  # Reset to avoid duplicates

    else:
        print("   ✗ No memory routing found in capabilities")

        # Show a sample to debug
        print("\n3. Sample of engineer agent section:")
        if "(`engineer`)" in capabilities:
            eng_pos = capabilities.find("(`engineer`)")
            next_agent = capabilities.find("### ", eng_pos + 1)
            if next_agent == -1:
                next_agent = eng_pos + 500
            print(capabilities[eng_pos:next_agent])

    print("\n" + "=" * 50)
    print("Test complete!")


if __name__ == "__main__":
    test_no_cache()
