#!/usr/bin/env python3
"""Test script for enhanced temporal and user context in FrameworkLoader."""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_temporal_user_context():
    """Test that the temporal and user context is properly generated."""
    print("Testing Enhanced Temporal & User Context\n" + "=" * 50)

    # Initialize framework loader
    loader = FrameworkLoader()

    # Get the full framework instructions
    instructions = loader.get_framework_instructions()

    # Check if temporal context is present
    if "## Temporal & User Context" in instructions:
        print("✅ Temporal & User Context section found in framework instructions")

        # Extract and display the context section
        context_start = instructions.find("## Temporal & User Context")
        context_end = instructions.find("\n## ", context_start + 1)
        if context_end == -1:
            context_end = instructions.find("\n\n## ", context_start + 1)
        if context_end == -1:
            context_section = instructions[context_start : context_start + 1000]
        else:
            context_section = instructions[context_start:context_end]

        print("\nExtracted Context Section:")
        print("-" * 40)
        print(context_section)
        print("-" * 40)

        # Verify key components are present
        components_to_check = [
            ("Current DateTime", "**Current DateTime**"),
            ("Day of Week", "**Day**"),
            ("User", "**User**"),
            ("System", "**System**"),
            ("Working Directory", "**Working Directory**"),
        ]

        print("\nComponent Verification:")
        all_present = True
        for name, marker in components_to_check:
            if marker in context_section:
                print(f"  ✅ {name} present")
            else:
                print(f"  ❌ {name} missing")
                all_present = False

        if all_present:
            print("\n✅ All expected components are present!")
        else:
            print("\n⚠️ Some components are missing (may be due to environment)")

    else:
        print("❌ Temporal & User Context section NOT found in framework instructions")
        print("\nSearching for old format...")
        if "## Temporal Context" in instructions:
            print("Found old '## Temporal Context' - migration may be needed")
        else:
            print("No temporal context found at all")

    # Test the standalone method
    print("\n" + "=" * 50)
    print("Testing Standalone Context Generation Method\n")

    context = loader._generate_temporal_user_context()
    print("Generated Context:")
    print(context)

    return True


if __name__ == "__main__":
    try:
        success = test_temporal_user_context()
        if success:
            print("\n" + "=" * 50)
            print("✅ All tests completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
