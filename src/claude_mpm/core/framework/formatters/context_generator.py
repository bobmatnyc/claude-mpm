"""Temporal and user context generator for framework instructions."""

import getpass
import locale
import os
import platform
import time as time_module
from datetime import datetime, timezone
from pathlib import Path

from claude_mpm.core.logging_utils import get_logger


class ContextGenerator:
    """Generates temporal and user context for better PM awareness."""

    def __init__(self):
        """Initialize the context generator."""
        self.logger = get_logger("context_generator")

    def generate_temporal_user_context(self) -> str:
        """Generate enhanced temporal and user context for better PM awareness.

        Returns:
            Formatted context string with datetime, user, and system information
        """
        context_lines = ["\n\n## Temporal & User Context\n"]

        try:
            # Get current datetime with timezone awareness
            now = datetime.now(timezone.utc)

            # Try to get timezone info - fallback to UTC offset if timezone name not available
            try:
                if hasattr(time_module, "tzname"):
                    tz_name = time_module.tzname[time_module.daylight]
                    tz_offset = time_module.strftime("%z")
                    if tz_offset:
                        # Format UTC offset properly (e.g., -0800 to -08:00)
                        tz_offset = (
                            f"{tz_offset[:3]}:{tz_offset[3:]}"
                            if len(tz_offset) >= 4
                            else tz_offset
                        )
                        tz_info = f"{tz_name} (UTC{tz_offset})"
                    else:
                        tz_info = tz_name
                else:
                    tz_info = "Local Time"
            except Exception:
                tz_info = "Local Time"

            # Format datetime components
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            day_name = now.strftime("%A")

            context_lines.append(
                f"**Current DateTime**: {date_str} {time_str} {tz_info}\n"
            )
            context_lines.append(f"**Day**: {day_name}\n")

        except Exception as e:
            # Fallback to basic date if enhanced datetime fails
            self.logger.debug(f"Error generating enhanced datetime context: {e}")
            context_lines.append(
                f"**Today's Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
            )

        # Get user information
        self._add_user_context(context_lines)

        # Get system information
        self._add_system_context(context_lines)

        # Get environment information
        self._add_environment_context(context_lines)

        # Add instruction for applying context
        context_lines.append(
            "\nApply temporal and user awareness to all tasks, "
            "decisions, and interactions.\n"
        )
        context_lines.append(
            "Use this context for personalized responses and "
            "time-sensitive operations.\n"
        )

        return "".join(context_lines)

    def _add_user_context(self, context_lines: list) -> None:
        """Add user information to context.

        Args:
            context_lines: List to append context lines to
        """
        try:
            # Get user information with safe fallbacks
            username = None

            # Try multiple methods to get username
            methods = [
                lambda: os.environ.get("USER"),
                lambda: os.environ.get("USERNAME"),  # Windows fallback
                lambda: getpass.getuser(),
            ]

            for method in methods:
                try:
                    username = method()
                    if username:
                        break
                except Exception:
                    continue

            if username:
                context_lines.append(f"**User**: {username}\n")

                # Add home directory if available
                try:
                    home_dir = Path("~").expanduser()
                    if home_dir and home_dir != "~":
                        context_lines.append(f"**Home Directory**: {home_dir}\n")
                except Exception:
                    pass

        except Exception as e:
            # User detection is optional, don't fail
            self.logger.debug(f"Could not detect user information: {e}")

    def _add_system_context(self, context_lines: list) -> None:
        """Add system information to context.

        Args:
            context_lines: List to append context lines to
        """
        try:
            # Get system information
            system_info = platform.system()
            if system_info:
                # Enhance system name for common platforms
                system_names = {
                    "Darwin": "Darwin (macOS)",
                    "Linux": "Linux",
                    "Windows": "Windows",
                }
                system_display = system_names.get(system_info, system_info)
                context_lines.append(f"**System**: {system_display}\n")

                # Add platform version if available
                try:
                    platform_version = platform.release()
                    if platform_version:
                        context_lines.append(
                            f"**System Version**: {platform_version}\n"
                        )
                except Exception:
                    pass

        except Exception as e:
            # System info is optional
            self.logger.debug(f"Could not detect system information: {e}")

    def _add_environment_context(self, context_lines: list) -> None:
        """Add environment information to context.

        Args:
            context_lines: List to append context lines to
        """
        try:
            # Add current working directory
            cwd = Path.cwd()
            if cwd:
                context_lines.append(f"**Working Directory**: {cwd}\n")
        except Exception:
            pass

        try:
            # Add locale information if available
            current_locale = locale.getlocale()
            if current_locale and current_locale[0]:
                context_lines.append(f"**Locale**: {current_locale[0]}\n")
        except Exception:
            # Locale is optional
            pass
