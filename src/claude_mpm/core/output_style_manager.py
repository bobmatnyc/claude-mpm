"""Output style management for Claude MPM.

This module handles:
1. Claude version detection
2. Output style extraction from framework instructions
3. One-time deployment to Claude Code >= 1.0.83 at startup
4. Fallback injection for older versions

The output style is set once at startup and not monitored or enforced after that.
Users can change it if they want, and the system will respect their choice.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional

from ..utils.imports import safe_import

# Import with fallback support
get_logger = safe_import("claude_mpm.core.logger", "core.logger", ["get_logger"])

# Global cache for Claude version to avoid duplicate detection/logging
_CACHED_CLAUDE_VERSION: Optional[str] = None
_VERSION_DETECTED: bool = False


class OutputStyleManager:
    """Manages output style deployment and version-based handling."""

    def __init__(self):
        """Initialize the output style manager."""
        self.logger = get_logger("output_style_manager")
        self.claude_version = self._detect_claude_version()
        self.output_style_dir = Path.home() / ".claude" / "output-styles"
        self.output_style_path = self.output_style_dir / "claude-mpm.md"
        self.settings_file = Path.home() / ".claude" / "settings.json"

        # Cache the output style content path
        self.mpm_output_style_path = (
            Path(__file__).parent.parent / "agents" / "OUTPUT_STYLE.md"
        )

    def _detect_claude_version(self) -> Optional[str]:
        """
        Detect Claude Code version by running 'claude --version'.
        Uses global cache to avoid duplicate detection and logging.

        Returns:
            Version string (e.g., "1.0.82") or None if Claude not found
        """
        global _CACHED_CLAUDE_VERSION, _VERSION_DETECTED

        # Return cached version if already detected
        if _VERSION_DETECTED:
            return _CACHED_CLAUDE_VERSION

        try:
            # Run claude --version command
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode != 0:
                self.logger.warning(f"Claude command failed: {result.stderr}")
                _VERSION_DETECTED = True
                _CACHED_CLAUDE_VERSION = None
                return None

            # Parse version from output
            # Expected format: "Claude 1.0.82" or similar
            version_output = result.stdout.strip()
            version_match = re.search(r"(\d+\.\d+\.\d+)", version_output)

            if version_match:
                version = version_match.group(1)
                # Only log on first detection
                self.logger.info(f"Detected Claude version: {version}")
                _CACHED_CLAUDE_VERSION = version
                _VERSION_DETECTED = True
                return version
            self.logger.warning(f"Could not parse version from: {version_output}")
            _VERSION_DETECTED = True
            _CACHED_CLAUDE_VERSION = None
            return None

        except FileNotFoundError:
            self.logger.info("Claude Code not found in PATH")
            _VERSION_DETECTED = True
            _CACHED_CLAUDE_VERSION = None
            return None
        except subprocess.TimeoutExpired:
            self.logger.warning("Claude version check timed out")
            _VERSION_DETECTED = True
            _CACHED_CLAUDE_VERSION = None
            return None
        except Exception as e:
            self.logger.warning(f"Error detecting Claude version: {e}")
            _VERSION_DETECTED = True
            _CACHED_CLAUDE_VERSION = None
            return None

    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            -1 if version1 < version2
            0 if version1 == version2
            1 if version1 > version2
        """
        try:
            v1_parts = [int(x) for x in version1.split(".")]
            v2_parts = [int(x) for x in version2.split(".")]

            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            for i in range(max_len):
                if v1_parts[i] < v2_parts[i]:
                    return -1
                if v1_parts[i] > v2_parts[i]:
                    return 1
            return 0
        except Exception as e:
            self.logger.warning(f"Error comparing versions: {e}")
            return -1

    def supports_output_styles(self) -> bool:
        """
        Check if Claude Code supports output styles (>= 1.0.83).

        Returns:
            True if Claude version >= 1.0.83, False otherwise
        """
        if not self.claude_version:
            return False

        return self._compare_versions(self.claude_version, "1.0.83") >= 0

    def should_inject_content(self) -> bool:
        """
        Check if output style content should be injected into instructions.

        Returns:
            True if Claude version < 1.0.83 or not detected, False otherwise
        """
        return not self.supports_output_styles()

    def extract_output_style_content(self, framework_loader=None) -> str:
        """
        Read output style content from OUTPUT_STYLE.md.

        Args:
            framework_loader: Optional framework loader (kept for compatibility, not used)

        Returns:
            Complete output style content from file
        """
        # Always read from the complete OUTPUT_STYLE.md file
        if self.mpm_output_style_path.exists():
            content = self.mpm_output_style_path.read_text()
            self.logger.info(f"Read OUTPUT_STYLE.md directly ({len(content)} chars)")
            return content
        # Fallback error
        error_msg = f"OUTPUT_STYLE.md not found at {self.mpm_output_style_path}"
        self.logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    def save_output_style(self, content: str) -> Path:
        """
        Save output style content to OUTPUT_STYLE.md.

        Args:
            content: The formatted output style content

        Returns:
            Path to the saved file
        """
        try:
            # Ensure the parent directory exists
            self.mpm_output_style_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the content
            self.mpm_output_style_path.write_text(content, encoding="utf-8")
            self.logger.info(f"Saved output style to {self.mpm_output_style_path}")

            return self.mpm_output_style_path
        except Exception as e:
            self.logger.error(f"Failed to save output style: {e}")
            raise

    def deploy_output_style(self, content: str) -> bool:
        """
        Deploy output style to Claude Code if version >= 1.0.83.
        Deploys the style file and activates it once.

        Args:
            content: The output style content to deploy

        Returns:
            True if deployed successfully, False otherwise
        """
        if not self.supports_output_styles():
            self.logger.info(
                f"Claude version {self.claude_version or 'unknown'} does not support output styles"
            )
            return False

        try:
            # Ensure output-styles directory exists
            self.output_style_dir.mkdir(parents=True, exist_ok=True)

            # Write the output style file
            self.output_style_path.write_text(content, encoding="utf-8")
            self.logger.info(f"Deployed output style to {self.output_style_path}")

            # Activate the claude-mpm style
            self._activate_output_style()

            return True

        except Exception as e:
            self.logger.error(f"Failed to deploy output style: {e}")
            return False

    def _activate_output_style(self) -> bool:
        """
        Update Claude Code settings to activate the claude-mpm output style.
        Sets activeOutputStyle to "claude-mpm" once at startup.

        Returns:
            True if activated successfully, False otherwise
        """
        try:
            # Load existing settings or create new
            settings = {}
            if self.settings_file.exists():
                try:
                    settings = json.loads(self.settings_file.read_text())
                except json.JSONDecodeError:
                    self.logger.warning(
                        "Could not parse existing settings.json, using defaults"
                    )

            # Check current active style
            current_style = settings.get("activeOutputStyle")

            # Update active output style to claude-mpm if not already set
            if current_style != "claude-mpm":
                settings["activeOutputStyle"] = "claude-mpm"

                # Ensure settings directory exists
                self.settings_file.parent.mkdir(parents=True, exist_ok=True)

                # Write updated settings
                self.settings_file.write_text(
                    json.dumps(settings, indent=2), encoding="utf-8"
                )

                self.logger.info(
                    f"✅ Activated claude-mpm output style (was: {current_style or 'none'})"
                )
            else:
                self.logger.debug("Claude MPM output style already active")

            return True

        except Exception as e:
            self.logger.warning(f"Failed to update settings: {e}")
            return False

    def get_status_summary(self) -> Dict[str, str]:
        """
        Get a summary of the output style status.

        Returns:
            Dictionary with status information
        """
        status = {
            "claude_version": self.claude_version or "Not detected",
            "supports_output_styles": "Yes" if self.supports_output_styles() else "No",
            "deployment_mode": "Not initialized",
            "active_style": "Unknown",
            "file_status": "Not checked",
        }

        if self.supports_output_styles():
            status["deployment_mode"] = "Output style deployment"

            # Check if file exists
            if self.output_style_path.exists():
                status["file_status"] = "Deployed"
            else:
                status["file_status"] = "Pending deployment"

            # Check active style
            if self.settings_file.exists():
                try:
                    settings = json.loads(self.settings_file.read_text())
                    status["active_style"] = settings.get("activeOutputStyle", "none")
                except Exception:
                    status["active_style"] = "Error reading settings"
        else:
            status["deployment_mode"] = "Framework injection"
            status["file_status"] = "N/A (legacy mode)"
            status["active_style"] = "N/A (legacy mode)"

        return status

    def get_injectable_content(self, framework_loader=None) -> str:
        """
        Get output style content for injection into instructions (for Claude < 1.0.83).

        This returns a simplified version without YAML frontmatter, suitable for
        injection into the framework instructions.

        Args:
            framework_loader: Optional FrameworkLoader instance to reuse loaded content

        Returns:
            Simplified output style content for injection
        """
        # Extract the same content but without YAML frontmatter
        full_content = self.extract_output_style_content(framework_loader)

        # Remove YAML frontmatter
        lines = full_content.split("\n")
        if lines[0] == "---":
            # Find the closing ---
            for i in range(1, len(lines)):
                if lines[i] == "---":
                    # Skip frontmatter and empty lines after it
                    content_start = i + 1
                    while (
                        content_start < len(lines) and not lines[content_start].strip()
                    ):
                        content_start += 1
                    return "\n".join(lines[content_start:])

        # If no frontmatter found, return as-is
        return full_content
