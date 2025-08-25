#!/usr/bin/env python3
"""Test the integration of output style enforcement in the actual framework."""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.output_style_manager import OutputStyleManager


def main():
    """Test the output style manager integration."""

    print("=" * 60)
    print("OUTPUT STYLE INTEGRATION TEST")
    print("=" * 60)

    # Create and initialize the manager
    manager = OutputStyleManager()

    print(f"\n1. Claude Version: {manager.claude_version or 'Not detected'}")
    print(f"2. Supports Output Styles: {manager.supports_output_styles()}")

    if manager.supports_output_styles():
        # Extract and deploy the style
        print("\n3. Extracting output style content...")
        content = manager.extract_output_style_content()
        print(f"   - Content length: {len(content)} characters")

        print("\n4. Deploying output style...")
        deployed = manager.deploy_output_style(content)
        print(f"   - Deployment successful: {deployed}")

        # Check current settings
        print("\n5. Checking current settings...")
        if manager.settings_file.exists():
            settings = json.loads(manager.settings_file.read_text())
            active_style = settings.get("activeOutputStyle", "none")
            print(f"   - Active style: {active_style}")

            if active_style != "claude-mpm":
                print("   - WARNING: Style is not claude-mpm!")
                print("   - Attempting to enforce...")
                manager.enforce_style_periodically(force_check=True)

                # Check again
                settings = json.loads(manager.settings_file.read_text())
                active_style = settings.get("activeOutputStyle", "none")
                print(f"   - Active style after enforcement: {active_style}")

        # Log final enforcement status
        print("\n6. Final Status:")
        manager.log_enforcement_status()

        # Get summary
        print("\n7. Status Summary:")
        status = manager.get_status_summary()
        for key, value in status.items():
            print(f"   - {key}: {value}")
    else:
        print("\n3. Claude version does not support output styles")
        print("   - Output style content will be injected into framework instructions")

        # Test injectable content
        print("\n4. Getting injectable content...")
        injectable = manager.get_injectable_content()
        print(f"   - Injectable content length: {len(injectable)} characters")

    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()
