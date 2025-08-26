#!/usr/bin/env python3
"""Test for duplicate configuration messages at runtime."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up verbose logging to see all messages
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)


def main():
    """Test runtime configuration loading."""
    print("=" * 70)
    print("TESTING RUNTIME CONFIGURATION LOADING")
    print("=" * 70)

    # Ensure we have a config file to load
    config_dir = Path.cwd() / ".claude-mpm"
    if not config_dir.exists():
        print(f"Creating {config_dir} for testing...")
        config_dir.mkdir(parents=True)

    config_file = config_dir / "configuration.yaml"
    if not config_file.exists():
        print(f"Creating test config at {config_file}...")
        config_file.write_text(
            """
response_logging:
  enabled: true
  format: json
"""
        )

    print("\nImporting and initializing various services that use Config...\n")

    # Import Config directly
    print("1. Importing Config directly...")

    config1 = Config()
    print(f"   Config instance ID: {id(config1)}")

    # Import a service that uses Config
    print("\n2. Importing HookService...")
    from claude_mpm.services.hook_service import HookService

    HookService()

    # Import another service
    print("\n3. Importing EventAggregator...")
    from claude_mpm.services.event_aggregator import EventAggregator

    EventAggregator()

    # Import another service that might use Config
    print("\n4. Importing ResponseLoggingManager...")
    from claude_mpm.logging.response_logging import ResponseLoggingManager

    ResponseLoggingManager()

    # Try getting Config again
    print("\n5. Getting Config instance again...")
    config2 = Config()
    print(f"   Config instance ID: {id(config2)}")
    print(f"   Same instance? {id(config1) == id(config2)}")

    print("\n" + "=" * 70)
    print("VERIFICATION:")
    print(f"Config._success_logged: {Config._success_logged}")
    print(f"Config._initialized: {Config._initialized}")
    print(f"All instances are same: {id(config1) == id(config2)}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
