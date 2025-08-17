#!/usr/bin/env python3
"""
Response Logging Health Test Script

WHY: Response logging is critical for tracking agent interactions, but it can
fail silently due to configuration issues, YAML syntax errors, or initialization
problems. This script provides comprehensive health checks to identify and
diagnose response logging issues.

DESIGN DECISIONS:
- Tests both configuration and runtime aspects
- Simulates actual response logging flow
- Provides clear diagnostics for each failure mode
- Suggests specific fixes for identified issues
- Non-destructive testing (doesn't modify configuration)

USAGE:
    python scripts/test_response_logging_health.py
    python scripts/test_response_logging_health.py --verbose
    python scripts/test_response_logging_health.py --fix  # Auto-fix common issues
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.config import Config
from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
from claude_mpm.services.claude_session_logger import ClaudeSessionLogger
from claude_mpm.services.response_tracker import ResponseTracker


class ResponseLoggingHealthChecker:
    """Comprehensive health checker for response logging system.

    WHY: Response logging can fail at multiple points - configuration loading,
    tracker initialization, or actual logging. This class tests each component
    systematically to identify the exact failure point.
    """

    def __init__(self, verbose: bool = False, auto_fix: bool = False):
        """Initialize the health checker.

        Args:
            verbose: Enable detailed output
            auto_fix: Attempt to fix common issues automatically
        """
        self.verbose = verbose
        self.auto_fix = auto_fix
        self.results: Dict[str, Dict[str, Any]] = {}
        self.fixes_applied: list = []

    def run_all_checks(self) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
        """Run all health checks for response logging.

        Returns:
            Tuple of (all_healthy, detailed_results)
        """
        print("\n" + "=" * 60)
        print("Response Logging Health Check")
        print("=" * 60 + "\n")

        # 1. Check configuration file existence and syntax
        self._check_configuration_file()

        # 2. Check configuration loading
        self._check_configuration_loading()

        # 3. Check response tracker initialization
        self._check_response_tracker()

        # 4. Check session logger
        self._check_session_logger()

        # 5. Check hook handler integration
        self._check_hook_handler()

        # 6. Test actual response logging
        self._test_response_logging()

        # 7. Check directory permissions
        self._check_directory_permissions()

        # Calculate overall health
        all_healthy = all(
            result.get("status") == "healthy" for result in self.results.values()
        )

        return all_healthy, self.results

    def _check_configuration_file(self) -> None:
        """Check if configuration file exists and has valid syntax."""
        check_name = "Configuration File"
        print(f"Checking {check_name}...")

        config_paths = [
            Path(".claude-mpm/configuration.yaml"),
            Path(".claude-mpm/configuration.yml"),
            Path(".claude-mpm/config.yaml"),
            Path(".claude-mpm/config.yml"),
        ]

        found_config = None
        for config_path in config_paths:
            if config_path.exists():
                found_config = config_path
                break

        if not found_config:
            self.results[check_name] = {
                "status": "missing",
                "message": "No configuration file found",
                "fix": "Create .claude-mpm/configuration.yaml with response_logging section",
            }
            print(f"  ✗ No configuration file found")

            if self.auto_fix:
                self._create_default_config()
                print(f"  → Created default configuration file")
                self.fixes_applied.append("Created default configuration")
        else:
            # Check YAML syntax
            try:
                import yaml

                with open(found_config, "r") as f:
                    yaml.safe_load(f)

                self.results[check_name] = {
                    "status": "healthy",
                    "message": f"Configuration file valid: {found_config}",
                    "path": str(found_config),
                }
                print(f"  ✓ Configuration file valid: {found_config}")

            except yaml.YAMLError as e:
                self.results[check_name] = {
                    "status": "error",
                    "message": f"YAML syntax error: {e}",
                    "fix": "Fix YAML syntax errors in configuration file",
                    "path": str(found_config),
                }
                print(f"  ✗ YAML syntax error in {found_config}")
                if self.verbose:
                    print(f"    Error: {e}")

    def _check_configuration_loading(self) -> None:
        """Check if configuration loads properly."""
        check_name = "Configuration Loading"
        print(f"Checking {check_name}...")

        try:
            config = Config()

            # Check if response_logging section exists
            response_logging = config.get("response_logging", {})

            if not response_logging:
                self.results[check_name] = {
                    "status": "warning",
                    "message": "No response_logging configuration found",
                    "fix": "Add response_logging section to configuration",
                }
                print(f"  ⚠ No response_logging configuration found")

                if self.auto_fix:
                    self._add_response_logging_config()
                    print(f"  → Added response_logging configuration")
                    self.fixes_applied.append("Added response_logging configuration")
            else:
                # Check key settings
                enabled = response_logging.get("enabled", False)
                format_type = response_logging.get("format", "json")
                session_dir = response_logging.get(
                    "session_directory", ".claude-mpm/responses"
                )

                self.results[check_name] = {
                    "status": "healthy" if enabled else "disabled",
                    "message": f'Response logging {"enabled" if enabled else "disabled"}',
                    "config": {
                        "enabled": enabled,
                        "format": format_type,
                        "session_directory": session_dir,
                    },
                }

                if enabled:
                    print(f"  ✓ Configuration loaded (response logging enabled)")
                else:
                    print(f"  ⚠ Configuration loaded but response logging disabled")

                if self.verbose:
                    print(f"    Format: {format_type}")
                    print(f"    Session directory: {session_dir}")

        except Exception as e:
            self.results[check_name] = {
                "status": "error",
                "message": f"Failed to load configuration: {e}",
                "fix": "Check configuration file syntax and structure",
            }
            print(f"  ✗ Failed to load configuration: {e}")

    def _check_response_tracker(self) -> None:
        """Check if ResponseTracker initializes properly."""
        check_name = "Response Tracker"
        print(f"Checking {check_name}...")

        try:
            config = Config()
            tracker = ResponseTracker(config)

            if tracker.enabled:
                if tracker.session_logger:
                    self.results[check_name] = {
                        "status": "healthy",
                        "message": "Response tracker initialized successfully",
                        "session_logger": True,
                    }
                    print(f"  ✓ Response tracker initialized successfully")
                else:
                    self.results[check_name] = {
                        "status": "error",
                        "message": "Response tracker enabled but session logger failed",
                        "fix": "Check session directory permissions",
                    }
                    print(f"  ✗ Response tracker enabled but session logger failed")
            else:
                self.results[check_name] = {
                    "status": "disabled",
                    "message": "Response tracker disabled by configuration",
                    "fix": "Enable response_logging in configuration",
                }
                print(f"  ⚠ Response tracker disabled by configuration")

        except Exception as e:
            self.results[check_name] = {
                "status": "error",
                "message": f"Failed to initialize response tracker: {e}",
                "fix": "Check ResponseTracker dependencies and configuration",
            }
            print(f"  ✗ Failed to initialize response tracker: {e}")

    def _check_session_logger(self) -> None:
        """Check if ClaudeSessionLogger works properly."""
        check_name = "Session Logger"
        print(f"Checking {check_name}...")

        try:
            config = Config()
            response_logging = config.get("response_logging", {})
            session_dir = Path(
                response_logging.get("session_directory", ".claude-mpm/responses")
            )

            if not session_dir.is_absolute():
                session_dir = Path.cwd() / session_dir

            # Try to initialize session logger
            logger = ClaudeSessionLogger(base_dir=session_dir, config=config)

            # Check if we can create a session directory
            test_session_id = f"health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.set_session_id(test_session_id)

            # Try to log a test entry
            test_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "health_check",
                "message": "Testing response logging health",
            }

            log_path = logger.log_response(
                "test request", "test response", test_entry, "health_check"
            )

            if log_path and log_path.exists():
                self.results[check_name] = {
                    "status": "healthy",
                    "message": "Session logger working correctly",
                    "test_file": str(log_path),
                }
                print(f"  ✓ Session logger working correctly")

                # Clean up test file
                try:
                    log_path.unlink()
                    # Remove test session directory if empty
                    session_path = log_path.parent
                    if not any(session_path.iterdir()):
                        session_path.rmdir()
                except:
                    pass
            else:
                self.results[check_name] = {
                    "status": "error",
                    "message": "Session logger failed to create log file",
                    "fix": "Check directory permissions and disk space",
                }
                print(f"  ✗ Session logger failed to create log file")

        except Exception as e:
            self.results[check_name] = {
                "status": "error",
                "message": f"Session logger error: {e}",
                "fix": "Check ClaudeSessionLogger dependencies",
            }
            print(f"  ✗ Session logger error: {e}")

    def _check_hook_handler(self) -> None:
        """Check if hook handler can process responses."""
        check_name = "Hook Handler"
        print(f"Checking {check_name}...")

        try:
            handler = ClaudeHookHandler()

            # Check if response tracking is available
            if hasattr(handler, "response_tracker"):
                if handler.response_tracker and handler.response_tracker.enabled:
                    self.results[check_name] = {
                        "status": "healthy",
                        "message": "Hook handler has active response tracker",
                        "tracker_enabled": True,
                    }
                    print(f"  ✓ Hook handler has active response tracker")
                else:
                    self.results[check_name] = {
                        "status": "warning",
                        "message": "Hook handler has disabled response tracker",
                        "tracker_enabled": False,
                    }
                    print(f"  ⚠ Hook handler has disabled response tracker")
            else:
                # Check if RESPONSE_TRACKING_AVAILABLE flag is set
                from claude_mpm.hooks.claude_hooks import hook_handler

                if hook_handler.RESPONSE_TRACKING_AVAILABLE:
                    self.results[check_name] = {
                        "status": "warning",
                        "message": "Response tracking available but not initialized",
                        "fix": "Hook handler may need reinitialization",
                    }
                    print(f"  ⚠ Response tracking available but not initialized")
                else:
                    self.results[check_name] = {
                        "status": "error",
                        "message": "Response tracking not available in hook handler",
                        "fix": "Check ResponseTracker import in hook_handler.py",
                    }
                    print(f"  ✗ Response tracking not available in hook handler")

        except Exception as e:
            self.results[check_name] = {
                "status": "error",
                "message": f"Hook handler error: {e}",
                "fix": "Check hook_handler.py imports and dependencies",
            }
            print(f"  ✗ Hook handler error: {e}")

    def _test_response_logging(self) -> None:
        """Test actual response logging with a simulated delegation."""
        check_name = "Response Logging Test"
        print(f"Checking {check_name}...")

        try:
            config = Config()
            tracker = ResponseTracker(config)

            if not tracker.enabled:
                self.results[check_name] = {
                    "status": "skipped",
                    "message": "Response logging disabled, skipping test",
                }
                print(f"  ⚠ Response logging disabled, skipping test")
                return

            # Test logging a response
            test_agent = "test_agent"
            test_request = "Test request for health check"
            test_response = json.dumps(
                {
                    "task_completed": True,
                    "instructions": "Health check completed",
                    "results": {"status": "healthy"},
                    "timestamp": datetime.now().isoformat(),
                }
            )

            log_path = tracker.track_response(
                agent_name=test_agent,
                request=test_request,
                response=test_response,
                metadata={"test": True, "health_check": True},
            )

            if log_path and log_path.exists():
                # Verify content
                with open(log_path, "r") as f:
                    logged_data = json.load(f)

                if logged_data.get("agent") == test_agent:
                    self.results[check_name] = {
                        "status": "healthy",
                        "message": "Response logging working correctly",
                        "test_file": str(log_path),
                    }
                    print(f"  ✓ Response logging working correctly")

                    # Clean up test file
                    try:
                        log_path.unlink()
                    except:
                        pass
                else:
                    self.results[check_name] = {
                        "status": "error",
                        "message": "Response logged but data incorrect",
                        "fix": "Check response tracker implementation",
                    }
                    print(f"  ✗ Response logged but data incorrect")
            else:
                self.results[check_name] = {
                    "status": "error",
                    "message": "Response logging failed to create file",
                    "fix": "Check directory permissions and disk space",
                }
                print(f"  ✗ Response logging failed to create file")

        except Exception as e:
            self.results[check_name] = {
                "status": "error",
                "message": f"Response logging test failed: {e}",
                "fix": "Check response logging implementation",
            }
            print(f"  ✗ Response logging test failed: {e}")

    def _check_directory_permissions(self) -> None:
        """Check if response logging directories have proper permissions."""
        check_name = "Directory Permissions"
        print(f"Checking {check_name}...")

        try:
            config = Config()
            response_logging = config.get("response_logging", {})
            session_dir = Path(
                response_logging.get("session_directory", ".claude-mpm/responses")
            )

            if not session_dir.is_absolute():
                session_dir = Path.cwd() / session_dir

            issues = []

            # Check if directory exists
            if not session_dir.exists():
                # Try to create it
                try:
                    session_dir.mkdir(parents=True, exist_ok=True)
                    issues.append(f"Created directory: {session_dir}")
                    if self.auto_fix:
                        self.fixes_applied.append(f"Created directory {session_dir}")
                except Exception as e:
                    issues.append(f"Cannot create directory: {e}")

            # Check write permissions
            if session_dir.exists():
                if not os.access(session_dir, os.W_OK):
                    issues.append(f"Directory not writable: {session_dir}")
                    if self.auto_fix:
                        try:
                            session_dir.chmod(0o755)
                            issues.append("Fixed directory permissions")
                            self.fixes_applied.append(
                                f"Fixed permissions for {session_dir}"
                            )
                        except Exception as e:
                            issues.append(f"Cannot fix permissions: {e}")

            if not issues:
                self.results[check_name] = {
                    "status": "healthy",
                    "message": "Directory permissions correct",
                    "directory": str(session_dir),
                }
                print(f"  ✓ Directory permissions correct")
            else:
                self.results[check_name] = {
                    "status": "warning" if len(issues) == 1 else "error",
                    "message": "Directory permission issues",
                    "issues": issues,
                    "fix": f"Ensure {session_dir} exists and is writable",
                }
                print(f"  ⚠ Directory permission issues:")
                for issue in issues:
                    print(f"    • {issue}")

        except Exception as e:
            self.results[check_name] = {
                "status": "error",
                "message": f"Failed to check directory permissions: {e}",
            }
            print(f"  ✗ Failed to check directory permissions: {e}")

    def _create_default_config(self) -> None:
        """Create a default configuration file with response logging enabled."""
        config_dir = Path(".claude-mpm")
        config_dir.mkdir(exist_ok=True)

        config_file = config_dir / "configuration.yaml"

        default_config = """# Claude MPM Configuration
# Generated by response logging health check

response_logging:
  # Enable response logging
  enabled: true

  # Use async logging for better performance
  use_async: true

  # Logging format: json, syslog, or journald
  format: json

  # Directory to store session responses
  session_directory: ".claude-mpm/responses"

  # Enable compression for JSON logs
  enable_compression: false

  # Maximum queue size for async writes
  max_queue_size: 10000
"""

        config_file.write_text(default_config)

    def _add_response_logging_config(self) -> None:
        """Add response_logging section to existing configuration."""
        config_paths = [
            Path(".claude-mpm/configuration.yaml"),
            Path(".claude-mpm/configuration.yml"),
        ]

        for config_path in config_paths:
            if config_path.exists():
                import yaml

                with open(config_path, "r") as f:
                    config = yaml.safe_load(f) or {}

                if "response_logging" not in config:
                    config["response_logging"] = {
                        "enabled": True,
                        "use_async": True,
                        "format": "json",
                        "session_directory": ".claude-mpm/responses",
                        "enable_compression": False,
                        "max_queue_size": 10000,
                    }

                    with open(config_path, "w") as f:
                        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

                break

    def print_summary(self, all_healthy: bool) -> None:
        """Print a summary of the health check results."""
        print("\n" + "=" * 60)
        print("Health Check Summary")
        print("=" * 60)

        # Count statuses
        status_counts = {}
        for result in self.results.values():
            status = result.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        # Print counts
        if status_counts.get("healthy", 0) > 0:
            print(f"✓ Healthy: {status_counts['healthy']}")
        if status_counts.get("warning", 0) > 0:
            print(f"⚠ Warnings: {status_counts['warning']}")
        if status_counts.get("error", 0) > 0:
            print(f"✗ Errors: {status_counts['error']}")
        if status_counts.get("disabled", 0) > 0:
            print(f"◯ Disabled: {status_counts['disabled']}")

        # Overall status
        print("\n" + "-" * 60)
        if all_healthy:
            print("✅ Response logging is HEALTHY")
        elif status_counts.get("error", 0) > 0:
            print("❌ Response logging has ERRORS")
            print("\nSuggested fixes:")
            for check_name, result in self.results.items():
                if result.get("status") == "error" and "fix" in result:
                    print(f"  • {check_name}: {result['fix']}")
        elif status_counts.get("disabled", 0) > 0:
            print("⚠️  Response logging is DISABLED")
            print("\nTo enable: Set response_logging.enabled=true in configuration")
        else:
            print("⚠️  Response logging has WARNINGS")

        # Applied fixes
        if self.fixes_applied:
            print("\n✨ Fixes applied:")
            for fix in self.fixes_applied:
                print(f"  • {fix}")

        print()


def main():
    """Main entry point for health check script."""
    parser = argparse.ArgumentParser(
        description="Test response logging health and configuration"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--fix", action="store_true", help="Attempt to fix common issues automatically"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # Run health check
    checker = ResponseLoggingHealthChecker(verbose=args.verbose, auto_fix=args.fix)

    all_healthy, results = checker.run_all_checks()

    if args.json:
        # Output as JSON
        print(json.dumps(results, indent=2, default=str))
    else:
        # Print human-readable summary
        checker.print_summary(all_healthy)

    # Exit with appropriate code
    if all_healthy:
        return 0
    elif any(r.get("status") == "error" for r in results.values()):
        return 1
    else:
        return 2  # Warnings


if __name__ == "__main__":
    sys.exit(main())
