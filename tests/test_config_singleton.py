#!/usr/bin/env python3
"""Test script to verify Config singleton behavior."""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging to see all messages
logging.basicConfig(
    level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s"
)


def test_config_singleton():
    """Test that Config truly behaves as a singleton."""

    print("=== Testing Config Singleton Behavior ===\n")

    # First instance
    print("Creating first Config instance...")
    config1 = Config()
    print(f"Config1 ID: {id(config1)}")
    print(f"Config1._instance ID: {id(Config._instance)}")
    print(f"Config._initialized: {Config._initialized}")

    # Second instance
    print("\nCreating second Config instance...")
    config2 = Config()
    print(f"Config2 ID: {id(config2)}")
    print(f"Config2._instance ID: {id(Config._instance)}")
    print(f"Config._initialized: {Config._initialized}")

    # Third instance
    print("\nCreating third Config instance...")
    config3 = Config()
    print(f"Config3 ID: {id(config3)}")

    # Verify they are the same
    print("\n=== Singleton Verification ===")
    print(f"config1 is config2: {config1 is config2}")
    print(f"config2 is config3: {config2 is config3}")
    print(f"All are same instance: {config1 is config2 is config3}")

    # Test that modifications are shared
    print("\n=== Testing Shared State ===")
    config1.set("test_key", "test_value")
    print(f"config1.get('test_key'): {config1.get('test_key')}")
    print(f"config2.get('test_key'): {config2.get('test_key')}")
    print(f"config3.get('test_key'): {config3.get('test_key')}")

    return config1 is config2 is config3


def test_service_config_usage():
    """Test how services are using Config."""
    print("\n=== Testing Service Config Usage ===\n")

    # Import services that use Config
    from claude_mpm.services.hook_service import HookService

    # Get initial config instance
    initial_config = Config()
    initial_id = id(initial_config)
    print(f"Initial Config ID: {initial_id}")

    # Create service (it creates Config internally)
    print("\nCreating HookService...")
    service = HookService()
    service_config_id = id(service.config)
    print(f"HookService.config ID: {service_config_id}")
    print(f"Same as initial? {initial_id == service_config_id}")

    # Create another service
    print("\nCreating another HookService...")
    service2 = HookService()
    service2_config_id = id(service2.config)
    print(f"HookService2.config ID: {service2_config_id}")
    print(f"Same as initial? {initial_id == service2_config_id}")
    print(f"Same as service1? {service_config_id == service2_config_id}")


if __name__ == "__main__":
    # Test singleton behavior
    is_singleton = test_config_singleton()

    # Test service usage
    test_service_config_usage()

    if is_singleton:
        print("\n✅ Config singleton is working correctly!")
    else:
        print("\n❌ Config singleton is NOT working correctly!")
        sys.exit(1)
