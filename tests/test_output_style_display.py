#!/usr/bin/env python3
"""Test script to verify output style information display."""

import logging
import sys

sys.path.insert(0, "src")

# Setup logging to show INFO messages
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def test_framework_loader():
    """Test framework loader output style initialization."""
    print("\n" + "=" * 60)
    print("Testing Framework Loader Output Style Info")
    print("=" * 60)

    from claude_mpm.core.framework_loader import FrameworkLoader

    # Initialize framework loader
    loader = FrameworkLoader()

    # Trigger output style initialization
    instructions = loader.get_framework_instructions()
    print(f"\n✅ Framework instructions generated ({len(instructions)} chars)")

    # Check output style manager status
    if loader.output_style_manager:
        status = loader.output_style_manager.get_status_summary()
        print("\nOutput Style Status Summary:")
        print("-" * 30)
        for key, value in status.items():
            print(f"  {key}: {value}")
    else:
        print("\n❌ Output style manager not initialized")


def test_output_style_manager():
    """Test output style manager directly."""
    print("\n" + "=" * 60)
    print("Testing Output Style Manager")
    print("=" * 60)

    from claude_mpm.core.output_style_manager import OutputStyleManager

    # Create output style manager
    osm = OutputStyleManager()

    # Display version info
    print(f"\nClaude Code Version: {osm.claude_version or 'Not detected'}")
    print(f"Supports Output Styles: {'Yes' if osm.supports_output_styles() else 'No'}")

    # Get and display status summary
    status = osm.get_status_summary()
    print("\nDetailed Status:")
    print("-" * 30)
    for key, value in status.items():
        print(f"  {key}: {value}")

    # Check file locations
    print("\nFile Locations:")
    print(f"  Output style file: {osm.output_style_path}")
    print(f"  Settings file: {osm.settings_file}")
    print(f"  MPM style source: {osm.mpm_output_style_path}")


def test_interactive_session_display():
    """Test interactive session welcome message with output style info."""
    print("\n" + "=" * 60)
    print("Testing Interactive Session Display")
    print("=" * 60)

    from claude_mpm.core.claude_runner import ClaudeRunner
    from claude_mpm.core.interactive_session import InteractiveSession

    # Create a runner with correct parameters
    runner = ClaudeRunner(enable_tickets=True, log_level="INFO", claude_args=[])

    # Create interactive session
    session = InteractiveSession(runner)

    # Get output style info
    output_style_info = session._get_output_style_info()

    if output_style_info:
        print(f"\n✅ Output style info for display: {output_style_info}")
    else:
        print("\n⚠️ No output style info available for display")

    # Display the welcome message
    print("\nWelcome Message Preview:")
    print("-" * 30)
    session._display_welcome_message()


if __name__ == "__main__":
    # Run all tests
    test_output_style_manager()
    test_framework_loader()
    test_interactive_session_display()

    print("\n" + "=" * 60)
    print("✅ All output style display tests complete!")
    print("=" * 60)
