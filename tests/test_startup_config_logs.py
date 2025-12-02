#!/usr/bin/env python3
"""Test script to simulate service startup and check for duplicate config messages."""

import logging
import sys
from pathlib import Path

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_service_initialization():
    """Test initializing multiple services to see if duplicate messages appear."""

    print("=== Simulating service initialization sequence ===\n")

    # Import services that might create Config instances
    from claude_mpm.services.hook_service import HookService
    from claude_mpm.services.runner_configuration_service import (
        RunnerConfigurationService,
    )
    from claude_mpm.services.subprocess_launcher_service import (
        SubprocessLauncherService,
    )

    print("1. Creating RunnerConfigurationService...")
    RunnerConfigurationService()

    print("\n2. Creating HookService...")
    HookService()

    print("\n3. Creating SubprocessLauncherService...")
    SubprocessLauncherService()

    print("\n4. Creating another Config instance directly...")
    config = Config()

    print("\n5. Checking configuration status...")
    status = config.get_configuration_status()
    print(f"Config loaded from: {status['loaded_from']}")
    print(f"Config valid: {status['valid']}")

    print("\n=== Test complete ===")


if __name__ == "__main__":
    test_service_initialization()
