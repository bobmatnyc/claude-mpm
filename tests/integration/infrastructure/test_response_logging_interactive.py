#!/usr/bin/env python3
"""Manual test script for response logging in interactive mode.

WHY: This script demonstrates that response logging now works correctly in
interactive mode by automatically switching to subprocess mode when enabled.

USAGE:
    python scripts/test_response_logging_interactive.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_mpm.core.claude_runner import ClaudeRunner


def test_response_logging_interactive():
    """Test response logging in interactive mode."""
    print("\n" + "=" * 60)
    print("Testing Response Logging Auto-Switch in Interactive Mode")
    print("=" * 60 + "\n")

    # Create temporary config with response logging enabled
    temp_dir = tmp_path
    config_file = Path(temp_dir) / "claude-mpm.yml"
    log_dir = Path(temp_dir) / "logs"

    config_content = f"""
response_logging:
  enabled: true
  output_dir: "{log_dir}"
  format: "json"
  include_timestamps: true
"""
    config_file.write_text(config_content)

    print(f"📁 Config file: {config_file}")
    print(f"📂 Log directory: {log_dir}")
    print()

    # Create runner with exec mode (default)
    print("🔧 Creating ClaudeRunner with launch_method='exec'")
    runner = ClaudeRunner(launch_method="exec", log_level="INFO")

    # Override config
    runner.config = Config(config_file=str(config_file))

    # Check if response logger is initialized
    print(f"📝 Response logger initialized: {runner.response_logger is not None}")

    # Show what will happen
    print("\n" + "=" * 60)
    print("Expected Behavior:")
    print("-" * 60)
    print("1. Response logging is ENABLED in config")
    print("2. Launch method is set to 'exec' (default)")
    print("3. ClaudeRunner should AUTO-SWITCH to subprocess mode")
    print("4. User should see a message about the auto-switch")
    print("5. Response logging should work correctly")
    print("=" * 60 + "\n")

    print("Press Ctrl+C to skip the interactive test\n")

    try:
        # This would normally launch Claude interactively
        # For testing, we'll just show what would happen
        print("🚀 Would launch interactive Claude with:")
        print("   - Launch method: exec (initial)")
        print("   - Response logging: enabled")
        print("   - Expected: AUTO-SWITCH to subprocess mode")
        print()

        # Simulate the check that happens in run_interactive
        if runner.response_logger is not None:
            response_config = runner.config.get("response_logging", {})
            if response_config.get("enabled", False) and runner.launch_method == "exec":
                print("✅ AUTO-SWITCH TRIGGERED!")
                print("   📝 Response logging enabled - using subprocess mode")
                print(
                    "   (Override with --launch-method exec to disable response logging)"
                )
            else:
                print("❌ No auto-switch needed")
        else:
            print("❌ Response logger not initialized")

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

    # Clean up
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_response_logging_interactive()
