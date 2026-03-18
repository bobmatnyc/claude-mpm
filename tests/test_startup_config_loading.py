#!/usr/bin/env python3
"""Test to verify configuration loading during startup."""

import io
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def capture_startup_logs():
    """Capture logs during a simulated startup process."""

    # Create a string buffer to capture logs
    log_buffer = io.StringIO()

    # Configure logging to capture everything
    handler = logging.StreamHandler(log_buffer)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    # Get root logger and add our handler
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Import and initialize ClaudeRunner to simulate startup
    from claude_mpm.core.claude_runner import ClaudeRunner

    try:
        print("Simulating ClaudeRunner startup...")

        # Create runner (it creates its own container internally)
        ClaudeRunner(
            enable_tickets=False,
            log_level="OFF",
            claude_args=[],
            launch_method="exec",
            enable_websocket=False,
            websocket_port=8765,
        )

        print("ClaudeRunner created successfully")

    except Exception as e:
        print(f"Error during startup: {e}")

    # Get the captured logs
    log_contents = log_buffer.getvalue()

    # Clean up
    root_logger.removeHandler(handler)

    return log_contents


def analyze_config_loading(logs):
    """Analyze the captured logs for configuration loading patterns."""

    lines = logs.split("\n")

    # Count specific patterns
    config_loads = []
    singleton_creates = []
    singleton_reuses = []

    for i, line in enumerate(lines):
        if "Successfully loaded configuration from" in line:
            config_loads.append((i, line))
        elif "Creating new Config singleton instance" in line:
            singleton_creates.append((i, line))
        elif "Reusing existing Config singleton instance" in line:
            singleton_reuses.append((i, line))

    print("\n=== Configuration Loading Analysis ===\n")

    print(f"Configuration file loaded: {len(config_loads)} time(s)")
    for idx, (line_no, line) in enumerate(config_loads, 1):
        print(f"  {idx}. Line {line_no}: {line.strip()}")

    print(f"\nSingleton created: {len(singleton_creates)} time(s)")
    for idx, (line_no, line) in enumerate(singleton_creates, 1):
        print(f"  {idx}. Line {line_no}: {line.strip()}")

    print(f"\nSingleton reused: {len(singleton_reuses)} time(s)")
    for idx, (line_no, line) in enumerate(singleton_reuses, 1):
        print(f"  {idx}. Line {line_no}: {line.strip()}")

    # Check for service initialization patterns
    service_inits = []
    for line in lines:
        if any(
            service in line.lower()
            for service in [
                "memory_hook_service",
                "agent_capabilities_service",
                "system_instructions_service",
                "subprocess_launcher_service",
                "version_service",
                "command_handler_service",
                "session_management_service",
            ]
        ) and ("initializ" in line.lower() or "creating" in line.lower()):
            service_inits.append(line)

    if service_inits:
        print(f"\n=== Service Initializations ({len(service_inits)}) ===")
        for line in service_inits[:10]:  # Show first 10
            print(f"  - {line.strip()}")

    # Verdict
    print("\n=== Verdict ===")
    if len(config_loads) > 1:
        print("❌ ISSUE CONFIRMED: Configuration file is being loaded multiple times!")
        print(f"   Expected: 1 load, Actual: {len(config_loads)} loads")
        return False
    if len(config_loads) == 1:
        print("✅ Configuration is loaded exactly once (correct behavior)")
        if len(singleton_reuses) > 0:
            print(
                f"✅ Singleton is being reused {len(singleton_reuses)} times (correct behavior)"
            )
        return True
    print("⚠️  No configuration loading detected")
    return None


if __name__ == "__main__":
    print("=== Testing Configuration Loading During Startup ===\n")

    # Capture logs during startup
    logs = capture_startup_logs()

    # Analyze the logs
    result = analyze_config_loading(logs)

    # Save logs for inspection
    log_file = Path("startup_config_logs.txt")
    with log_file.open("w") as f:
        f.write(logs)
    print(f"\nFull logs saved to: {log_file}")

    # Exit with appropriate code
    if result is False:
        sys.exit(1)
    elif result is None:
        sys.exit(2)
    else:
        sys.exit(0)
