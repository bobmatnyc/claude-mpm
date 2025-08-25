#!/usr/bin/env python3
"""Test script to demonstrate the duplicate configuration loading message issue."""

import logging
import sys
from pathlib import Path

# Setup logging to see what's happening
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_multiple_config_instances():
    """Test creating multiple Config instances to see the duplicate logging."""
    print("Creating first Config instance...")
    config1 = Config()
    print(f"Config1 instance id: {id(config1)}")

    print("\nCreating second Config instance...")
    config2 = Config()
    print(f"Config2 instance id: {id(config2)}")

    print("\nCreating third Config instance...")
    config3 = Config()
    print(f"Config3 instance id: {id(config3)}")

    # Verify they are the same instance (singleton)
    print(f"\nAll instances are the same? {config1 is config2 is config3}")

    print("\nConfig status:")
    status = config1.get_configuration_status()
    print(f"Loaded from: {status['loaded_from']}")
    print(f"Valid: {status['valid']}")


if __name__ == "__main__":
    test_multiple_config_instances()
