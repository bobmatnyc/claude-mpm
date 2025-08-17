#!/usr/bin/env python3
"""Example script demonstrating usage of the run-guarded command.

This script shows various ways to use the memory-guarded Claude runner
for preventing memory-related crashes during long sessions.
"""

import subprocess
import sys
from pathlib import Path

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def run_command(cmd: str, description: str = None):
    """Run a command and display the results."""
    if description:
        print(f"\n{'='*60}")
        print(f"Example: {description}")
        print(f"{'='*60}")

    print(f"Command: {cmd}\n")

    try:
        # Split command string into a list to avoid shell=True
        import shlex

        command_parts = shlex.split(cmd)
        result = subprocess.run(command_parts, capture_output=False, text=True)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Demonstrate various run-guarded usage patterns."""
    print(
        """
╔══════════════════════════════════════════════════════════════╗
║         Claude MPM - Memory-Guarded Execution Examples       ║
╚══════════════════════════════════════════════════════════════╝

This script demonstrates how to use the run-guarded command to
prevent memory-related crashes when running Claude Code.
"""
    )

    examples = [
        # Basic usage
        (
            "claude-mpm run-guarded",
            "Basic usage with default settings (18GB threshold)",
        ),
        # Custom memory threshold
        (
            "claude-mpm run-guarded --memory-threshold 16000",
            "Custom memory threshold (16GB)",
        ),
        # Faster monitoring for development
        (
            "claude-mpm run-guarded --check-interval 10 --verbose",
            "Fast monitoring (10s checks) with verbose output",
        ),
        # Production settings with more restarts
        (
            "claude-mpm run-guarded --max-restarts 10 --restart-cooldown 30",
            "Production mode with 10 restarts and 30s cooldown",
        ),
        # Minimal overhead mode
        (
            "claude-mpm run-guarded --no-state-preservation --check-interval 60",
            "Minimal overhead (no state preservation, 60s checks)",
        ),
        # With custom state directory
        (
            "claude-mpm run-guarded --state-dir /tmp/claude-state",
            "Custom state directory for preservation",
        ),
        # Show memory statistics
        (
            "claude-mpm run-guarded --show-stats --stats-interval 30",
            "Display memory statistics every 30 seconds",
        ),
        # Using configuration file
        (
            "claude-mpm run-guarded --config ~/.claude-mpm/memory-guardian.yaml",
            "Load settings from configuration file",
        ),
        # Quiet mode for automation
        (
            "claude-mpm run-guarded --quiet --max-restarts 5",
            "Quiet mode for automated/background usage",
        ),
        # With initial context
        (
            'claude-mpm run-guarded --input "Help me build a Python web application"',
            "Start with initial context/prompt",
        ),
    ]

    # Show command help (skipped if CLI not fully installed)
    # print("\nShowing command help:")
    # print("-" * 60)
    # subprocess.run("claude-mpm run-guarded --help", shell=True)

    print("\n" + "=" * 60)
    print("Example Commands (not executing, for demonstration only):")
    print("=" * 60)

    for cmd, description in examples:
        print(f"\n{description}:")
        print(f"  $ {cmd}")

    # Create example configuration file
    print("\n" + "=" * 60)
    print("Creating Example Configuration File")
    print("=" * 60)

    config_content = """# Memory Guardian Configuration Example
enabled: true
auto_start: true
persist_state: true

# Memory thresholds (in MB)
thresholds:
  warning: 14000   # 14GB - Start logging warnings
  critical: 18000  # 18GB - Trigger restart
  emergency: 21000 # 21GB - Immediate restart

# Monitoring settings
monitoring:
  check_interval: 30        # Normal check interval
  check_interval_warning: 15 # When in warning state
  check_interval_critical: 5  # When in critical state
  log_memory_stats: true
  log_interval: 60

# Restart policy
restart_policy:
  max_attempts: 5           # Maximum restarts in window
  attempt_window: 3600      # 1 hour window
  cooldown_base: 10         # Base cooldown seconds
  cooldown_multiplier: 2.0  # Exponential backoff
  cooldown_max: 300         # Max 5 minutes
  graceful_timeout: 30      # Graceful shutdown timeout
  force_kill_timeout: 10    # Force kill if graceful fails
"""

    config_path = Path.home() / ".claude-mpm" / "memory-guardian-example.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        f.write(config_content)

    print(f"Created example configuration at: {config_path}")
    print("\nYou can use this configuration with:")
    print(f"  $ claude-mpm run-guarded --config {config_path}")

    # Show memory monitoring benefits
    print("\n" + "=" * 60)
    print("Benefits of Memory-Guarded Execution")
    print("=" * 60)
    print(
        """
1. **Prevents System Crashes**: Automatically restarts Claude before
   memory usage becomes critical, preventing system-wide issues.

2. **State Preservation**: Saves conversation context before restart
   and restores it after, maintaining continuity.

3. **Configurable Thresholds**: Adjust memory limits based on your
   system's available RAM and usage patterns.

4. **Smart Restart Policy**: Exponential backoff and cooldown periods
   prevent restart loops while maintaining availability.

5. **Production Ready**: Suitable for long-running sessions, automated
   workflows, and production deployments.

6. **Monitoring & Alerts**: Real-time memory tracking with warnings
   before critical thresholds are reached.

Common Use Cases:
- Long coding sessions with large codebases
- Processing extensive documentation
- Running overnight or unattended sessions
- CI/CD pipeline integration
- Development on memory-constrained systems
"""
    )

    print("\n" + "=" * 60)
    print("Recommended Settings by Use Case")
    print("=" * 60)
    print(
        """
Development (Fast Feedback):
  --memory-threshold 12000 --check-interval 10 --max-restarts 10

Production (Stability):
  --memory-threshold 18000 --check-interval 30 --max-restarts 5

Limited Memory System (8GB RAM):
  --memory-threshold 6000 --check-interval 15 --max-restarts 3

High Memory System (32GB+ RAM):
  --memory-threshold 24000 --check-interval 60 --max-restarts 10

CI/CD Pipeline:
  --quiet --no-state-preservation --max-restarts 2
"""
    )


if __name__ == "__main__":
    main()
