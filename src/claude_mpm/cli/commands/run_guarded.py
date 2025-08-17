from pathlib import Path

"""Run-guarded command implementation for memory-aware Claude execution.

WHY: This experimental command provides memory monitoring and automatic restart
capabilities for Claude Code sessions, preventing memory-related crashes.

DESIGN DECISION: This is kept completely separate from the main run command to
ensure stability. It extends ClaudeRunner through MemoryAwareClaudeRunner without
modifying the base implementation.

STATUS: EXPERIMENTAL - This feature is in beta and may change or have issues.
"""

import argparse
import asyncio
import os
import sys
from typing import Any, Dict, Optional

from claude_mpm.cli.utils import setup_logging
from claude_mpm.config.experimental_features import get_experimental_features
from claude_mpm.config.memory_guardian_config import (
    MemoryGuardianConfig,
    MemoryThresholds,
    MonitoringConfig,
    RestartPolicy,
    get_default_config,
)
from claude_mpm.constants import LogLevel
from claude_mpm.core.logging_config import get_logger
from claude_mpm.core.memory_aware_runner import MemoryAwareClaudeRunner

logger = get_logger(__name__)


def add_run_guarded_parser(subparsers) -> argparse.ArgumentParser:
    """Add run-guarded command parser.

    Args:
        subparsers: Subparsers object from main parser

    Returns:
        The run-guarded parser for further configuration
    """
    parser = subparsers.add_parser(
        "run-guarded",
        help="(EXPERIMENTAL) Run Claude with memory monitoring and automatic restart",
        description=(
            "⚠️  EXPERIMENTAL FEATURE\n\n"
            "Run Claude Code with memory monitoring and automatic restart capabilities. "
            "This command monitors memory usage and performs controlled restarts when "
            "thresholds are exceeded, preserving conversation state across restarts.\n\n"
            "NOTE: This is a beta feature. Use with caution in production environments."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (18GB threshold, 30s checks)
  claude-mpm run-guarded

  # Custom memory threshold (in MB)
  claude-mpm run-guarded --memory-threshold 16000

  # Faster monitoring for development
  claude-mpm run-guarded --check-interval 10

  # Limit restart attempts
  claude-mpm run-guarded --max-restarts 5

  # Disable state preservation (faster restarts)
  claude-mpm run-guarded --no-state-preservation

  # Use configuration file
  claude-mpm run-guarded --config ~/.claude-mpm/memory-guardian.yaml

Memory thresholds:
  - Warning: 80% of threshold (logs warning)
  - Critical: 100% of threshold (triggers restart)
  - Emergency: 120% of threshold (immediate restart)

State preservation:
  When enabled, the runner captures and restores:
  - Current conversation context
  - Open files and working directory
  - Environment variables
  - Recent command history
""",
    )

    # Memory monitoring options
    memory_group = parser.add_argument_group("memory monitoring")
    memory_group.add_argument(
        "--memory-threshold",
        type=float,
        default=18000,  # 18GB in MB
        help="Memory threshold in MB before restart (default: 18000MB/18GB)",
    )
    memory_group.add_argument(
        "--check-interval",
        type=int,
        default=30,
        help="Memory check interval in seconds (default: 30)",
    )
    memory_group.add_argument(
        "--warning-threshold",
        type=float,
        help="Warning threshold in MB (default: 80%% of memory threshold)",
    )
    memory_group.add_argument(
        "--emergency-threshold",
        type=float,
        help="Emergency threshold in MB (default: 120%% of memory threshold)",
    )

    # Restart policy options
    restart_group = parser.add_argument_group("restart policy")
    restart_group.add_argument(
        "--max-restarts",
        type=int,
        default=3,
        help="Maximum number of automatic restarts (default: 3)",
    )
    restart_group.add_argument(
        "--restart-cooldown",
        type=int,
        default=10,
        help="Cooldown period between restarts in seconds (default: 10)",
    )
    restart_group.add_argument(
        "--graceful-timeout",
        type=int,
        default=30,
        help="Timeout for graceful shutdown in seconds (default: 30)",
    )

    # State preservation options
    state_group = parser.add_argument_group("state preservation")
    state_group.add_argument(
        "--enable-state-preservation",
        action="store_true",
        default=True,
        dest="state_preservation",
        help="Enable state preservation across restarts (default: enabled)",
    )
    state_group.add_argument(
        "--no-state-preservation",
        action="store_false",
        dest="state_preservation",
        help="Disable state preservation for faster restarts",
    )
    state_group.add_argument(
        "--state-dir",
        type=Path,
        help="Directory for state files (default: ~/.claude-mpm/state)",
    )

    # Configuration file
    parser.add_argument(
        "--config",
        "--config-file",
        type=Path,
        dest="config_file",
        help="Path to memory guardian configuration file (YAML)",
    )

    # Monitoring display options
    display_group = parser.add_argument_group("display options")
    display_group.add_argument(
        "--quiet", action="store_true", help="Minimal output, only show critical events"
    )
    display_group.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output with detailed monitoring information",
    )
    display_group.add_argument(
        "--show-stats",
        action="store_true",
        help="Display memory statistics periodically",
    )
    display_group.add_argument(
        "--stats-interval",
        type=int,
        default=60,
        help="Statistics display interval in seconds (default: 60)",
    )

    # Claude runner options (inherited from run command)
    run_group = parser.add_argument_group("claude options")
    run_group.add_argument(
        "--no-hooks", action="store_true", help="Disable hook service"
    )
    run_group.add_argument(
        "--no-tickets", action="store_true", help="Disable automatic ticket creation"
    )
    run_group.add_argument(
        "--no-native-agents",
        action="store_true",
        help="Disable deployment of Claude Code native agents",
    )
    run_group.add_argument(
        "--websocket-port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)",
    )

    # Input/output options
    io_group = parser.add_argument_group("input/output")
    io_group.add_argument(
        "-i", "--input", type=str, help="Input text or file path for initial context"
    )
    io_group.add_argument(
        "--non-interactive", action="store_true", help="Run in non-interactive mode"
    )

    # Logging options
    logging_group = parser.add_argument_group("logging")
    logging_group.add_argument(
        "--logging",
        choices=[level.value for level in LogLevel],
        default=LogLevel.INFO.value,
        help="Logging level (default: INFO)",
    )
    logging_group.add_argument("--log-dir", type=Path, help="Custom log directory")

    # Experimental feature control
    experimental_group = parser.add_argument_group("experimental control")
    experimental_group.add_argument(
        "--accept-experimental",
        action="store_true",
        help="Accept experimental status and suppress warning",
    )
    experimental_group.add_argument(
        "--force-experimental",
        action="store_true",
        help="Force run even if experimental features are disabled",
    )

    # Claude CLI arguments
    parser.add_argument(
        "claude_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to Claude CLI",
    )

    return parser


def load_config_file(config_path: Path) -> Optional[MemoryGuardianConfig]:
    """Load memory guardian configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        MemoryGuardianConfig or None if loading failed
    """
    try:
        import yaml

        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            return None

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Create configuration from YAML data
        config = MemoryGuardianConfig()

        # Update thresholds
        if "thresholds" in config_data:
            t = config_data["thresholds"]
            config.thresholds = MemoryThresholds(
                warning=t.get("warning", config.thresholds.warning),
                critical=t.get("critical", config.thresholds.critical),
                emergency=t.get("emergency", config.thresholds.emergency),
            )

        # Update monitoring settings
        if "monitoring" in config_data:
            m = config_data["monitoring"]
            config.monitoring = MonitoringConfig(
                normal_interval=m.get(
                    "normal_interval", config.monitoring.normal_interval
                ),
                warning_interval=m.get(
                    "warning_interval", config.monitoring.warning_interval
                ),
                critical_interval=m.get(
                    "critical_interval", config.monitoring.critical_interval
                ),
                log_memory_stats=m.get(
                    "log_memory_stats", config.monitoring.log_memory_stats
                ),
                log_interval=m.get("log_interval", config.monitoring.log_interval),
            )

        # Update restart policy
        if "restart_policy" in config_data:
            r = config_data["restart_policy"]
            config.restart_policy = RestartPolicy(
                max_attempts=r.get("max_attempts", config.restart_policy.max_attempts),
                attempt_window=r.get(
                    "attempt_window", config.restart_policy.attempt_window
                ),
                initial_cooldown=r.get(
                    "initial_cooldown", config.restart_policy.initial_cooldown
                ),
                cooldown_multiplier=r.get(
                    "cooldown_multiplier", config.restart_policy.cooldown_multiplier
                ),
                max_cooldown=r.get("max_cooldown", config.restart_policy.max_cooldown),
                graceful_timeout=r.get(
                    "graceful_timeout", config.restart_policy.graceful_timeout
                ),
                force_kill_timeout=r.get(
                    "force_kill_timeout", config.restart_policy.force_kill_timeout
                ),
            )

        # Update general settings
        config.enabled = config_data.get("enabled", True)
        config.auto_start = config_data.get("auto_start", True)
        config.persist_state = config_data.get("persist_state", True)

        logger.info(f"Loaded configuration from {config_path}")
        return config

    except ImportError:
        logger.error("PyYAML not installed. Install with: pip install pyyaml")
        return None
    except Exception as e:
        logger.error(f"Failed to load configuration file: {e}")
        return None


def execute_run_guarded(args: argparse.Namespace) -> int:
    """Execute the run-guarded command.

    WHY: This is the entry point for the experimental memory-guarded execution mode.
    It checks experimental feature flags and shows appropriate warnings before
    delegating to MemoryAwareClaudeRunner.

    DESIGN DECISION: All experimental checks happen here, before any actual work,
    to ensure users are aware they're using beta functionality.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Setup logging (configures the logger already created at module level)
        setup_logging(args)

        # Check experimental features
        experimental = get_experimental_features()

        # Check if Memory Guardian is enabled
        if not experimental.is_enabled("memory_guardian") and not getattr(
            args, "force_experimental", False
        ):
            logger.error(
                "Memory Guardian is an experimental feature that is currently disabled."
            )
            print(
                "\n❌ Memory Guardian is disabled in experimental features configuration."
            )
            print("\nTo enable it:")
            print(
                "  1. Set environment variable: export CLAUDE_MPM_EXPERIMENTAL_ENABLE_MEMORY_GUARDIAN=true"
            )
            print("  2. Or use --force-experimental flag to override")
            print("  3. Or enable in ~/.claude-mpm/experimental.json")
            return 1

        # Show experimental warning unless suppressed
        if not getattr(args, "accept_experimental", False):
            # Skip prompt in non-interactive mode
            if getattr(args, "non_interactive", False):
                logger.info(
                    "Non-interactive mode: accepting experimental warning automatically"
                )
            elif experimental.should_show_warning("memory_guardian"):
                warning = experimental.get_warning("memory_guardian")
                if warning:
                    print("\n" + warning)
                    print("\nThis feature is experimental and may:")
                    print("  • Have bugs or stability issues")
                    print("  • Change significantly in future versions")
                    print("  • Not work as expected in all environments")
                    sys.stdout.flush()  # Ensure prompt is displayed before input

                    # Check if we're in a TTY environment for proper input handling
                    if not sys.stdin.isatty():
                        # In non-TTY environment (like pipes), use readline
                        print("\nContinue? [y/N]: ", end="", flush=True)
                        try:
                            response = sys.stdin.readline().strip().lower()
                            # Handle various line endings and control characters
                            response = (
                                response.replace("\r", "").replace("\n", "").strip()
                            )
                        except (EOFError, KeyboardInterrupt):
                            response = "n"
                    else:
                        # In TTY environment, use normal input()
                        try:
                            response = input("\nContinue? [y/N]: ").strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            response = "n"

                    if response != "y":
                        print("\n✅ Cancelled. Use the stable 'run' command instead.")
                        return 0
                    # Mark as accepted for this session
                    experimental.mark_accepted("memory_guardian")

        logger.info("Starting experimental run-guarded command")

        # Load configuration
        config = None
        if hasattr(args, "config_file") and args.config_file:
            config = load_config_file(args.config_file)

        if config is None:
            # Create configuration from command line arguments
            config = MemoryGuardianConfig()

            # Set thresholds
            config.thresholds.critical = args.memory_threshold

            if hasattr(args, "warning_threshold") and args.warning_threshold:
                config.thresholds.warning = args.warning_threshold
            else:
                config.thresholds.warning = args.memory_threshold * 0.8

            if hasattr(args, "emergency_threshold") and args.emergency_threshold:
                config.thresholds.emergency = args.emergency_threshold
            else:
                config.thresholds.emergency = args.memory_threshold * 1.2

            # Set monitoring settings
            config.monitoring.normal_interval = args.check_interval
            config.monitoring.log_memory_stats = (
                args.show_stats if hasattr(args, "show_stats") else False
            )

            if hasattr(args, "stats_interval"):
                config.monitoring.log_interval = args.stats_interval

            # Set restart policy
            config.restart_policy.max_attempts = args.max_restarts

            if hasattr(args, "restart_cooldown"):
                config.restart_policy.initial_cooldown = args.restart_cooldown

            if hasattr(args, "graceful_timeout"):
                config.restart_policy.graceful_timeout = args.graceful_timeout

        # Override config with CLI arguments
        if hasattr(args, "memory_threshold"):
            config.thresholds.critical = args.memory_threshold

        if hasattr(args, "check_interval"):
            config.monitoring.normal_interval = args.check_interval

        if hasattr(args, "max_restarts"):
            config.restart_policy.max_attempts = args.max_restarts

        # Check mode early to avoid unnecessary setup
        if getattr(args, "non_interactive", False):
            logger.error("Non-interactive mode not yet supported for run-guarded")
            return 1

        # Determine verbosity
        if hasattr(args, "quiet") and args.quiet:
            log_level = "WARNING"
        elif hasattr(args, "verbose") and args.verbose:
            log_level = "DEBUG"
        else:
            log_level = getattr(args, "logging", LogLevel.INFO.value)

        # Create runner
        runner = MemoryAwareClaudeRunner(
            enable_tickets=not getattr(args, "no_tickets", False),
            log_level=log_level,
            claude_args=getattr(args, "claude_args", []),
            launch_method="subprocess",  # Always subprocess for monitoring
            enable_websocket=False,  # Could be enabled in future
            websocket_port=getattr(args, "websocket_port", 8765),
            memory_config=config,
            enable_monitoring=True,
            state_dir=getattr(args, "state_dir", None),
        )

        # Deploy agents if not disabled
        if not getattr(args, "no_native_agents", False):
            if not runner.setup_agents():
                logger.warning("Failed to deploy some agents, continuing anyway")

        # Get initial context if provided
        initial_context = None
        if hasattr(args, "input") and args.input:
            if Path(args.input).exists():
                with open(args.input, "r") as f:
                    initial_context = f.read()
            else:
                initial_context = args.input

        # Run with monitoring
        runner.run_interactive_with_monitoring(
            initial_context=initial_context,
            memory_threshold=config.thresholds.critical,
            check_interval=config.monitoring.normal_interval,
            max_restarts=config.restart_policy.max_attempts,
            enable_state_preservation=getattr(args, "state_preservation", True),
        )

        return 0

    except KeyboardInterrupt:
        logger.info("Run-guarded interrupted by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Run-guarded failed: {e}", exc_info=True)
        return 1


# Convenience function for direct module execution
def main():
    """Main entry point for run-guarded command."""
    parser = argparse.ArgumentParser(description="Run Claude with memory monitoring")
    add_run_guarded_parser(parser._subparsers)
    args = parser.parse_args()
    sys.exit(execute_run_guarded(args))


if __name__ == "__main__":
    main()
