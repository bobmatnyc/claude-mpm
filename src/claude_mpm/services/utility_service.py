from pathlib import Path

"""Utility service for various helper functions.

This service handles:
1. Agent delegation detection
2. Session event logging
3. Text processing utilities
4. Pattern matching utilities

Extracted from ClaudeRunner to follow Single Responsibility Principle.
"""

import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from claude_mpm.core.base_service import BaseService
from claude_mpm.services.core.interfaces import UtilityServiceInterface


class UtilityService(BaseService, UtilityServiceInterface):
    """Service for utility functions and helper methods."""

    def __init__(self):
        """Initialize the utility service."""
        super().__init__(name="utility_service")

    async def _initialize(self) -> None:
        """Initialize the service. No special initialization needed."""

    async def _cleanup(self) -> None:
        """Cleanup service resources. No cleanup needed."""

    def contains_delegation(self, text: str) -> bool:
        """Check if text contains signs of agent delegation.

        Args:
            text: Text to check for delegation patterns

        Returns:
            bool: True if delegation patterns are found
        """
        # Look for common delegation patterns
        delegation_patterns = [
            "Task(",
            "subagent_type=",
            "delegating to",
            "asking the",
            "engineer agent",
            "qa agent",
            "documentation agent",
            "research agent",
            "security agent",
            "ops agent",
            "version_control agent",
            "data_engineer agent",
        ]

        text_lower = text.lower()
        return any(pattern.lower() in text_lower for pattern in delegation_patterns)

    def extract_agent_from_response(self, text: str) -> Optional[str]:
        """Try to extract agent name from delegation response.

        Args:
            text: Response text to extract agent name from

        Returns:
            Optional[str]: Extracted agent name or None if not found
        """
        # Pattern 1: subagent_type="agent_name"
        match = re.search(r'subagent_type=["\']([^"\']*)["\'\)]', text)
        if match:
            return match.group(1)

        # Pattern 2: "engineer agent" etc
        agent_names = [
            "engineer",
            "qa",
            "documentation",
            "research",
            "security",
            "ops",
            "version_control",
            "data_engineer",
        ]
        text_lower = text.lower()
        for agent in agent_names:
            if f"{agent} agent" in text_lower or f"agent: {agent}" in text_lower:
                return agent

        return None

    def log_session_event(self, log_file: Optional[Path], event_data: Dict[str, Any]):
        """Log an event to the session log file.

        Args:
            log_file: Path to the session log file
            event_data: Event data to log
        """
        if not log_file:
            return

        try:
            log_entry = {"timestamp": datetime.now().isoformat(), **event_data}

            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        except OSError as e:
            self.logger.debug(f"IO error logging session event: {e}")
        except Exception as e:
            self.logger.debug(f"Failed to log session event: {e}")

    def validate_prompt(self, prompt: str) -> bool:
        """Validate that a prompt is not empty and properly formatted.

        Args:
            prompt: Prompt to validate

        Returns:
            bool: True if prompt is valid
        """
        if not prompt or not prompt.strip():
            return False

        # Check for minimum length
        return not len(prompt.strip()) < 3

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename by removing invalid characters.

        Args:
            filename: Filename to sanitize

        Returns:
            str: Sanitized filename
        """
        # Remove invalid characters for filenames
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "_")

        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(" .")

        # Ensure filename is not empty
        if not sanitized:
            sanitized = "untitled"

        return sanitized

    def format_error_message(self, error: Exception, context: str = "") -> str:
        """Format an error message with context.

        Args:
            error: Exception to format
            context: Optional context information

        Returns:
            str: Formatted error message
        """
        error_type = type(error).__name__
        error_msg = str(error)

        if context:
            return f"{context}: {error_type}: {error_msg}"
        return f"{error_type}: {error_msg}"

    def truncate_text(
        self, text: str, max_length: int = 100, suffix: str = "..."
    ) -> str:
        """Truncate text to a maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length before truncation
            suffix: Suffix to add when truncating

        Returns:
            str: Truncated text
        """
        if len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    def parse_key_value_pairs(self, text: str) -> Dict[str, str]:
        """Parse key=value pairs from text.

        Args:
            text: Text containing key=value pairs

        Returns:
            Dict[str, str]: Parsed key-value pairs
        """
        pairs = {}

        # Look for key=value patterns
        pattern = r'(\w+)=(["\']?)([^"\'\s]*)\2'
        matches = re.findall(pattern, text)

        for key, _quote, value in matches:
            pairs[key] = value

        return pairs

    def get_service_status(self) -> Dict[str, Any]:
        """Get current utility service status.

        Returns:
            Dict[str, Any]: Service status information
        """
        return {
            "service_available": True,
            "delegation_detection": True,
            "session_logging": True,
            "text_processing": True,
            "pattern_matching": True,
        }

    # Implementation of abstract methods from UtilityServiceInterface

    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return (
            f"{size:.1f} {units[unit_index]}"
            if unit_index > 0
            else f"{int(size)} {units[unit_index]}"
        )

    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        if minutes < 60:
            return (
                f"{minutes}m {remaining_seconds}s"
                if remaining_seconds > 0
                else f"{minutes}m"
            )
        hours = int(minutes // 60)
        remaining_minutes = int(minutes % 60)
        return (
            f"{hours}h {remaining_minutes}m" if remaining_minutes > 0 else f"{hours}h"
        )

    def generate_unique_id(self, prefix: str = "") -> str:
        """Generate a unique identifier."""
        unique_id = str(uuid.uuid4())
        return f"{prefix}_{unique_id}" if prefix else unique_id

    def validate_path(self, path: Path) -> Tuple[bool, Optional[str]]:
        """Validate a filesystem path."""
        try:
            if not isinstance(path, Path):
                return False, "Path must be a Path object"
            path_str = str(path)
            if not path_str or path_str.isspace():
                return False, "Path cannot be empty"
            return True, None
        except Exception as e:
            return False, f"Path validation error: {e!s}"
