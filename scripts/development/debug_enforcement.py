#!/usr/bin/env python3
"""Debug the enforcement mechanism."""

import json
import logging
import sys
from pathlib import Path

# Setup logging to see all messages
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.output_style_manager import OutputStyleManager


def main():
    print("=" * 60)
    print("DEBUG ENFORCEMENT")
    print("=" * 60)

    # Create manager
    manager = OutputStyleManager()

    # Check initial state
    settings_file = Path.home() / ".claude" / "settings.json"
    if settings_file.exists():
        settings = json.loads(settings_file.read_text())
        print(f"\nInitial style: {settings.get('activeOutputStyle')}")

    # Change style
    print("\nChanging style to 'verbose'...")
    settings["activeOutputStyle"] = "verbose"
    settings_file.write_text(json.dumps(settings, indent=2))

    # Verify change
    settings = json.loads(settings_file.read_text())
    print(f"Style after change: {settings.get('activeOutputStyle')}")

    # Try to enforce
    print("\n--- CALLING enforce_style_periodically ---")
    result = manager.enforce_style_periodically(force_check=True)
    print(f"Enforcement result: {result}")

    # Check final state
    settings = json.loads(settings_file.read_text())
    print(f"\nFinal style: {settings.get('activeOutputStyle')}")

    # Now test _activate_output_style directly
    print("\n--- CALLING _activate_output_style directly ---")

    # Change style again
    settings["activeOutputStyle"] = "minimal"
    settings_file.write_text(json.dumps(settings, indent=2))
    print("Changed style to: minimal")

    # Call activate directly
    result = manager._activate_output_style(force=True)
    print(f"Activation result: {result}")

    # Check final
    settings = json.loads(settings_file.read_text())
    print(f"Final style: {settings.get('activeOutputStyle')}")


if __name__ == "__main__":
    main()
