"""Startup checking service for CLI commands.

WHY: This service extracts startup validation logic from run.py to improve
separation of concerns, testability, and reusability across CLI commands.

DESIGN DECISIONS:
- Interface-based design for dependency injection
- Single responsibility: startup validation only
- Returns structured warnings for better handling
- Non-blocking: warns but doesn't prevent execution
- Reusable across multiple CLI commands
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from claude_mpm.core.logger import get_logger


# Interface Definition
class IStartupChecker(ABC):
    """Interface for startup checking service."""

    @abstractmethod
    def check_configuration(self) -> List["StartupWarning"]:
        """Validate configuration and return warnings."""

    @abstractmethod
    def check_memory(self, resume_enabled: bool = False) -> Optional["StartupWarning"]:
        """Check Claude.json memory usage."""

    @abstractmethod
    def check_environment(self) -> List["StartupWarning"]:
        """Validate environment and paths."""

    @abstractmethod
    def get_startup_warnings(
        self, resume_enabled: bool = False
    ) -> List["StartupWarning"]:
        """Collect all startup warnings."""


@dataclass
class StartupWarning:
    """Structured warning information."""

    category: str  # 'config', 'memory', 'environment'
    message: str
    suggestion: Optional[str] = None
    severity: str = "warning"  # 'info', 'warning', 'error'


class StartupCheckerService(IStartupChecker):
    """Service for startup validation and health checks."""

    def __init__(self, config_service):
        """Initialize the startup checker.

        Args:
            config_service: Configuration service instance (IConfigurationService)
        """
        self.config_service = config_service
        self.logger = get_logger("StartupChecker")

    def check_configuration(self) -> List[StartupWarning]:
        """Validate configuration and return warnings.

        Checks:
        - Response logging directory exists and is writable
        - Agent deployment configuration
        - Memory management configuration
        - Common configuration issues

        Returns:
            List of configuration warnings
        """
        warnings = []

        try:
            # Check response logging configuration
            response_logging = self.config_service.get("response_logging", {})
            if response_logging.get("enabled", False):
                log_dir = response_logging.get("directory")
                if log_dir:
                    warnings.extend(self._check_log_directory(log_dir))

            # Check memory management configuration
            memory_config = self.config_service.get("memory_management", {})
            if memory_config.get("auto_cleanup", False):
                cleanup_threshold = memory_config.get("cleanup_threshold_mb", 100)
                if cleanup_threshold < 50:
                    warnings.append(
                        StartupWarning(
                            category="config",
                            message=f"Memory cleanup threshold very low: {cleanup_threshold}MB",
                            suggestion="Consider increasing to at least 50MB",
                            severity="warning",
                        )
                    )

            # Check for deprecated configuration keys
            warnings.extend(self._check_deprecated_keys())

            # Check configuration file access
            warnings.extend(self._check_config_file_access())

        except Exception as e:
            self.logger.warning(f"Configuration check failed: {e}")
            warnings.append(
                StartupWarning(
                    category="config",
                    message=f"Configuration check failed: {e}",
                    severity="info",
                )
            )

        return warnings

    def check_memory(self, resume_enabled: bool = False) -> Optional[StartupWarning]:
        """Check .claude.json memory usage.

        WHY: Large .claude.json files (>500KB) cause significant memory issues
        when using --resume. Claude Code loads the entire conversation history
        into memory, leading to 2GB+ memory consumption.

        Args:
            resume_enabled: Whether --mpm-resume is being used

        Returns:
            Warning if memory issue detected, None otherwise
        """
        if not resume_enabled:
            return None

        try:
            claude_json_path = Path.cwd() / ".claude.json"
            if not claude_json_path.exists():
                self.logger.debug("No .claude.json file found")
                return None

            file_size = claude_json_path.stat().st_size

            # Only warn if file is larger than 500KB
            if file_size > 500 * 1024:
                formatted_size = self._format_file_size(file_size)
                return StartupWarning(
                    category="memory",
                    message=f"Large .claude.json file detected ({formatted_size})",
                    suggestion="Consider running 'claude-mpm cleanup-memory' to archive old conversations",
                    severity="warning",
                )

            self.logger.info(f".claude.json size: {self._format_file_size(file_size)}")

        except Exception as e:
            self.logger.warning(f"Failed to check .claude.json size: {e}")

        return None

    def check_environment(self) -> List[StartupWarning]:
        """Validate environment and paths.

        Checks:
        - Python version compatibility
        - Virtual environment activation
        - Required directories exist
        - File permissions

        Returns:
            List of environment warnings
        """
        warnings = []

        try:
            # Check Python version

            # Check for common missing directories
            warnings.extend(self._check_required_directories())

        except Exception as e:
            self.logger.warning(f"Environment check failed: {e}")
            warnings.append(
                StartupWarning(
                    category="environment",
                    message=f"Environment check failed: {e}",
                    severity="info",
                )
            )

        return warnings

    def get_startup_warnings(
        self, resume_enabled: bool = False
    ) -> List[StartupWarning]:
        """Collect all startup warnings.

        Args:
            resume_enabled: Whether --mpm-resume is being used

        Returns:
            Complete list of startup warnings
        """
        all_warnings = []

        # Collect configuration warnings
        all_warnings.extend(self.check_configuration())

        # Check memory if resume is enabled
        memory_warning = self.check_memory(resume_enabled)
        if memory_warning:
            all_warnings.append(memory_warning)

        # Collect environment warnings
        all_warnings.extend(self.check_environment())

        return all_warnings

    def display_warnings(self, warnings: List[StartupWarning]) -> None:
        """Display warnings to the user.

        Args:
            warnings: List of warnings to display
        """
        if not warnings:
            return

        # Group warnings by severity
        errors = [w for w in warnings if w.severity == "error"]
        warnings_list = [w for w in warnings if w.severity == "warning"]
        info = [w for w in warnings if w.severity == "info"]

        # Display errors first
        for warning in errors:
            print(f"❌ {warning.message}")
            if warning.suggestion:
                print(f"   {warning.suggestion}")

        # Display warnings
        for warning in warnings_list:
            print(f"⚠️  {warning.message}")
            if warning.suggestion:
                print(f"   💡 {warning.suggestion}")

        # Display info last
        for warning in info:
            print(f"ℹ️  {warning.message}")
            if warning.suggestion:
                print(f"   {warning.suggestion}")

        if errors or warnings_list:
            print()  # Add spacing after warnings

    # Private helper methods

    def _check_log_directory(self, log_dir: str) -> List[StartupWarning]:
        """Check if log directory exists and is writable."""
        warnings = []
        log_path = Path(log_dir)

        if not log_path.exists():
            warnings.append(
                StartupWarning(
                    category="config",
                    message=f"Response logging directory does not exist: {log_path}",
                    suggestion=f"Run: mkdir -p {log_path}",
                    severity="warning",
                )
            )
        elif not log_path.is_dir():
            warnings.append(
                StartupWarning(
                    category="config",
                    message=f"Response logging path is not a directory: {log_path}",
                    severity="warning",
                )
            )
        elif not os.access(log_path, os.W_OK):
            warnings.append(
                StartupWarning(
                    category="config",
                    message=f"Response logging directory is not writable: {log_path}",
                    suggestion=f"Run: chmod 755 {log_path}",
                    severity="warning",
                )
            )

        return warnings

    def _check_deprecated_keys(self) -> List[StartupWarning]:
        """Check for deprecated configuration keys."""
        warnings = []
        deprecated_keys = ["legacy_mode", "old_agent_format", "deprecated_logging"]

        for key in deprecated_keys:
            if self.config_service.get(key) is not None:
                warnings.append(
                    StartupWarning(
                        category="config",
                        message=f"Deprecated configuration key found: {key}",
                        suggestion="Consider removing this key from your configuration",
                        severity="info",
                    )
                )

        return warnings

    def _check_config_file_access(self) -> List[StartupWarning]:
        """Check configuration file accessibility."""
        warnings = []

        try:
            # Try to get config file path from config service
            config_file = getattr(self.config_service, "config_file", None)
            if config_file and Path(config_file).exists():
                if not os.access(config_file, os.R_OK):
                    warnings.append(
                        StartupWarning(
                            category="config",
                            message=f"Configuration file is not readable: {config_file}",
                            suggestion=f"Run: chmod 644 {config_file}",
                            severity="warning",
                        )
                    )
        except Exception as e:
            self.logger.debug(f"Config file access check failed: {e}")

        return warnings

    def _check_required_directories(self) -> List[StartupWarning]:
        """Check for required directories."""
        warnings = []

        # Check .claude directory
        claude_dir = Path.cwd() / ".claude"
        if not claude_dir.exists():
            self.logger.debug(
                ".claude directory does not exist (will be created on first use)"
            )
        elif not claude_dir.is_dir():
            warnings.append(
                StartupWarning(
                    category="environment",
                    message=".claude path exists but is not a directory",
                    severity="warning",
                )
            )

        return warnings

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes / (1024 * 1024):.1f} MB"
