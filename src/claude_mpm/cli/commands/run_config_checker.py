"""Configuration checking functionality for run commands.

This module provides configuration health checking and memory validation.
Extracted from run.py to reduce complexity and improve maintainability.
"""

import os
from pathlib import Path

from ...core.config import Config


class RunConfigChecker:
    """Handles configuration checking for run commands."""

    def __init__(self, logger):
        """Initialize the config checker."""
        self.logger = logger

    def check_claude_json_memory(self, args):
        """Check .claude.json file size and warn about memory issues.

        WHY: Large .claude.json files (>500KB) cause significant memory issues when
        using --resume. Claude Desktop loads the entire conversation history into
        memory, leading to 2GB+ memory consumption.
        """
        try:
            # Only check if --resume is being used
            if not getattr(args, "resume", False):
                return

            claude_json_path = Path.cwd() / ".claude.json"
            if not claude_json_path.exists():
                self.logger.debug("No .claude.json file found")
                return

            file_size = claude_json_path.stat().st_size

            def format_size(size_bytes):
                """Format file size in human readable format."""
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.1f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.1f} MB"

            # Warn if file is larger than 500KB
            if file_size > 500 * 1024:  # 500KB threshold
                print(
                    f"\n⚠️  WARNING: Large .claude.json file detected ({format_size(file_size)})"
                )
                print("   This may cause memory issues when using --resume")
                print(
                    "   💡 Consider running 'claude-mpm cleanup-memory' to archive old conversations\n"
                )
                # Just warn, don't block execution

            self.logger.info(f".claude.json size: {format_size(file_size)}")

        except Exception as e:
            self.logger.warning(f"Failed to check .claude.json size: {e}")
            # Just warn, don't block execution

    def check_configuration_health(self):
        """Check configuration health at startup and warn about issues.

        WHY: Configuration errors can cause silent failures, especially for response
        logging. This function proactively checks configuration at startup and warns
        users about any issues, providing actionable guidance.

        DESIGN DECISIONS:
        - Non-blocking: Issues are logged as warnings, not errors
        - Actionable: Provides specific commands to fix issues
        - Focused: Only checks critical configuration that affects runtime
        """
        try:
            config = Config()

            # Check response logging configuration
            response_logging = config.get("response_logging", {})
            if response_logging.get("enabled", False):
                log_dir = response_logging.get("directory")
                if log_dir:
                    log_path = Path(log_dir)
                    if not log_path.exists():
                        self.logger.warning(
                            f"Response logging directory does not exist: {log_path}"
                        )
                        print(f"⚠️  Response logging directory missing: {log_path}")
                        print(f"   Run: mkdir -p {log_path}")
                    elif not log_path.is_dir():
                        self.logger.warning(
                            f"Response logging path is not a directory: {log_path}"
                        )
                        print(
                            f"⚠️  Response logging path is not a directory: {log_path}"
                        )
                    elif not os.access(log_path, os.W_OK):
                        self.logger.warning(
                            f"Response logging directory is not writable: {log_path}"
                        )
                        print(
                            f"⚠️  Response logging directory is not writable: {log_path}"
                        )
                        print(f"   Run: chmod 755 {log_path}")

            # Check agent deployment configuration
            agent_deployment = config.get("agent_deployment", {})
            excluded_agents = agent_deployment.get("excluded_agents", [])
            if excluded_agents:
                self.logger.info(f"Agent exclusions configured: {excluded_agents}")

            # Check memory management configuration
            memory_config = config.get("memory_management", {})
            if memory_config.get("auto_cleanup", False):
                cleanup_threshold = memory_config.get("cleanup_threshold_mb", 100)
                if cleanup_threshold < 50:
                    self.logger.warning(
                        f"Memory cleanup threshold very low: {cleanup_threshold}MB"
                    )
                    print(
                        f"⚠️  Memory cleanup threshold is very low: {cleanup_threshold}MB"
                    )
                    print(f"   Consider increasing to at least 50MB")

            # Check for common configuration issues
            self._check_common_config_issues(config)

        except Exception as e:
            self.logger.warning(f"Configuration health check failed: {e}")
            # Don't block execution for config check failures

    def _check_common_config_issues(self, config):
        """Check for common configuration issues."""
        try:
            import os

            # Check if config file exists and is readable
            config_file = config.config_file
            if config_file and Path(config_file).exists():
                if not os.access(config_file, os.R_OK):
                    self.logger.warning(
                        f"Configuration file is not readable: {config_file}"
                    )
                    print(f"⚠️  Configuration file is not readable: {config_file}")
                    print(f"   Run: chmod 644 {config_file}")

            # Check for deprecated configuration keys
            deprecated_keys = ["legacy_mode", "old_agent_format", "deprecated_logging"]

            for key in deprecated_keys:
                if config.get(key) is not None:
                    self.logger.warning(f"Deprecated configuration key found: {key}")
                    print(f"⚠️  Deprecated configuration key: {key}")
                    print(f"   Consider removing this key from your configuration")

        except Exception as e:
            self.logger.debug(f"Common config issues check failed: {e}")
            # Don't propagate errors from this check
