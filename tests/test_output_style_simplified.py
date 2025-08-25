#!/usr/bin/env python3
"""Test the simplified output style implementation."""

import json
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.output_style_manager import OutputStyleManager


def test_simplified_output_style():
    """Test that the simplified output style manager works correctly."""

    print("Testing Simplified Output Style Manager")
    print("=" * 50)

    # Create manager
    manager = OutputStyleManager()

    # Show status
    print(f"\nClaude Version: {manager.claude_version or 'Not detected'}")
    print(f"Supports Output Styles: {manager.supports_output_styles()}")

    # Check current settings
    settings_file = Path.home() / ".claude" / "settings.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
            current_style = settings.get("activeOutputStyle", "none")
            print(f"Current Output Style: {current_style}")
        except Exception as e:
            print(f"Could not read settings: {e}")
    else:
        print("Settings file does not exist yet")

    # If supported, test deployment
    if manager.supports_output_styles():
        print("\nDeploying output style...")

        # Extract content
        content = manager.extract_output_style_content()

        # Deploy it (this should happen once at startup)
        success = manager.deploy_output_style(content)

        if success:
            print("✅ Deployment successful")

            # Check the settings again
            if settings_file.exists():
                settings = json.loads(settings_file.read_text())
                new_style = settings.get("activeOutputStyle", "none")
                print(f"New Output Style: {new_style}")

                if new_style == "claude-mpm":
                    print("✅ Output style set correctly")
                else:
                    print(f"⚠️  Output style is {new_style}, not claude-mpm")
        else:
            print("❌ Deployment failed")
    else:
        print("\nClaude version does not support output styles")
        print("Content would be injected into framework instructions")

    # Get status summary
    print("\nStatus Summary:")
    status = manager.get_status_summary()
    for key, value in status.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 50)
    print("Simplified Implementation Notes:")
    print("- Output style is set ONCE at startup")
    print("- No periodic monitoring or enforcement")
    print("- Users can change it if they want")
    print("- System respects user's choice")


if __name__ == "__main__":
    test_simplified_output_style()
