#!/usr/bin/env python3
"""Simulate the startup sequence to test configuration loading behavior."""

import logging
import sys
from io import StringIO
from pathlib import Path

# Add parent directory to path to import claude_mpm
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Capture all log output
log_capture = StringIO()

# Set up logging to capture all messages
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.StreamHandler(log_capture)],
)


def count_success_messages(log_output):
    """Count how many times the success message appears."""
    lines = log_output.split("\n")
    return sum(1 for line in lines if "✓ Successfully loaded configuration" in line)


def simulate_service_startup():
    """Simulate multiple services starting up and loading config."""
    # Reset for clean test

    Config.reset_singleton()

    print("\n=== Simulating Service Startup Sequence ===\n")

    # Simulate different services initializing
    services = [
        "BaseService",
        "HookService",
        "ResponseTracker",
        "MemoryManager",
        "AgentDeployment",
        "RunnerConfiguration",
        "EventAggregator",
        "SessionLogger",
        "ProjectAnalyzer",
        "UnifiedConfig",
    ]

    configs = []
    for service_name in services:
        print(f"[{service_name}] Initializing...")
        config = Config()
        configs.append(config)
        print(f"[{service_name}] Config loaded: {id(config)}")

    # Verify all configs are the same instance
    first_id = id(configs[0])
    all_same = all(id(c) == first_id for c in configs)

    print(f"\n✓ All configs are same instance: {all_same}")
    print(f"  Instance ID: {first_id}")

    # Check log output for duplicate messages
    log_output = log_capture.getvalue()
    success_count = count_success_messages(log_output)

    print("\n=== Log Analysis ===")
    print(f"Success messages found: {success_count}")

    # Show relevant log lines
    print("\nRelevant log lines:")
    for line in log_output.split("\n"):
        if any(
            keyword in line
            for keyword in [
                "Successfully loaded",
                "Creating new Config",
                "Reusing existing Config",
                "Config already initialized",
            ]
        ):
            # Extract just the message part
            if " - INFO - " in line:
                msg = line.split(" - INFO - ", 1)[1]
                print(f"  INFO: {msg}")
            elif " - DEBUG - " in line:
                msg = line.split(" - DEBUG - ", 1)[1]
                print(f"  DEBUG: {msg}")

    return success_count


def main():
    """Run the simulation."""
    print("=" * 70)
    print("Configuration Loading Simulation Test")
    print("=" * 70)

    success_count = simulate_service_startup()

    print("\n" + "=" * 70)
    print("RESULTS:")

    if success_count == 0:
        print(
            "✓ No configuration file found (expected if no .claude-mpm/configuration.yaml)"
        )
        result = True
    elif success_count == 1:
        print("✓ SUCCESS: Configuration success message appeared exactly ONCE!")
        result = True
    else:
        print(
            f"✗ FAILURE: Configuration success message appeared {success_count} times!"
        )
        result = False

    print("=" * 70)

    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
