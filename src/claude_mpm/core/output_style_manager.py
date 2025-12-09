"""Output style management for Claude MPM.

This module handles:
1. Claude version detection
2. Output style extraction from framework instructions
3. One-time deployment to Claude Code >= 1.0.83 at startup
4. Fallback injection for older versions
5. Support for multiple output styles (professional and teaching modes)

The output style is set once at startup and not monitored or enforced after that.
Users can change it if they want, and the system will respect their choice.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Literal, Optional, TypedDict, cast

from ..utils.imports import safe_import

# Import with fallback support
get_logger = safe_import("claude_mpm.core.logger", "core.logger", ["get_logger"])

# Global cache for Claude version to avoid duplicate detection/logging
_CACHED_CLAUDE_VERSION: Optional[str] = None
_VERSION_DETECTED: bool = False

# Output style types
OutputStyleType = Literal["professional", "teaching"]


class StyleConfig(TypedDict):
    """Configuration for an output style."""

    source: Path
    target: Path
    name: str


class OutputStyleManager:
    """Manages output style deployment and version-based handling.

    Supports two output styles:
    - professional: Default Claude MPM style (claude-mpm.md)
    - teaching: Adaptive teaching mode (claude-mpm-teach.md)
    """

    def __init__(self) -> None:
        """Initialize the output style manager."""
        self.logger = get_logger("output_style_manager")  # type: ignore[misc]
        self.claude_version = self._detect_claude_version()

        # Deploy to ~/.claude/styles/ directory (NOT output-styles/)
        self.output_style_dir = Path.home() / ".claude" / "styles"
        self.settings_file = Path.home() / ".claude" / "settings.json"

        # Style definitions
        self.styles: Dict[str, StyleConfig] = {
            "professional": StyleConfig(
                source=Path(__file__).parent.parent
                / "agents"
                / "CLAUDE_MPM_OUTPUT_STYLE.md",
                target=self.output_style_dir / "claude-mpm.md",
                name="claude-mpm",
            ),
            "teaching": StyleConfig(
                source=Path(__file__).parent.parent
                / "agents"
                / "CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md",
                target=self.output_style_dir / "claude-mpm-teach.md",
                name="claude-mpm-teach",
            ),
        }

        # Default style path (for backward compatibility)
        self.output_style_path = self.styles["professional"]["target"]
        self.mpm_output_style_path = self.styles["professional"]["source"]

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

    def extract_output_style_content(
        self, framework_loader: Any = None, style: OutputStyleType = "professional"
    ) -> str:
        """
        Read output style content from style source file.

        Args:
            framework_loader: Optional framework loader (kept for compatibility, not used)
            style: Style type to extract ("professional" or "teaching")

        Returns:
            Complete output style content from file
        """
        style_config = self.styles[style]
        source_path = style_config["source"]

        if source_path.exists():
            content = source_path.read_text()
            self.logger.info(
                f"Read {style} style from {source_path.name} ({len(content)} chars)"
            )
            return content

        # Fallback error
        error_msg = f"{style} style not found at {source_path}"
        self.logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    def save_output_style(
        self, content: str, style: OutputStyleType = "professional"
    ) -> Path:
        """
        Save output style content to source file.

        Args:
            content: The formatted output style content
            style: Style type to save ("professional" or "teaching")

        Returns:
            Path to the saved file
        """
        try:
            style_config = self.styles[style]
            source_path = style_config["source"]

            # Ensure the parent directory exists
            source_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the content
            source_path.write_text(content, encoding="utf-8")
            self.logger.info(f"Saved {style} style to {source_path}")

            return source_path
        except Exception as e:
            self.logger.error(f"Failed to save {style} style: {e}")
            raise

    def deploy_output_style(
        self,
        content: Optional[str] = None,
        style: OutputStyleType = "professional",
        activate: bool = True,
    ) -> bool:
        """
        Deploy output style to Claude Code if version >= 1.0.83.
        Deploys the style file and optionally activates it.

        Args:
            content: The output style content to deploy (if None, reads from source)
            style: Style type to deploy ("professional" or "teaching")
            activate: Whether to activate the style after deployment

        Returns:
            True if deployed successfully, False otherwise
        """
        if not self.supports_output_styles():
            self.logger.info(
                f"Claude version {self.claude_version or 'unknown'} does not support output styles"
            )
            return False

        try:
            style_config = self.styles[style]
            target_path = style_config["target"]
            style_name = style_config["name"]

            # If content not provided, read from source
            if content is None:
                content = self.extract_output_style_content(style=style)

            # Ensure styles directory exists
            self.output_style_dir.mkdir(parents=True, exist_ok=True)

            # Write the output style file
            target_path.write_text(content, encoding="utf-8")
            self.logger.info(f"Deployed {style} style to {target_path}")

            # Activate the style if requested
            if activate:
                self._activate_output_style(style_name)

            return True

        except Exception as e:
            self.logger.error(f"Failed to deploy {style} style: {e}")
            return False

    def _activate_output_style(self, style_name: str = "claude-mpm") -> bool:
        """
        Update Claude Code settings to activate a specific output style.

        Args:
            style_name: Name of the style to activate (e.g., "claude-mpm", "claude-mpm-teach")

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

            # Update active output style if different
            if current_style != style_name:
                settings["activeOutputStyle"] = style_name

                # Ensure settings directory exists
                self.settings_file.parent.mkdir(parents=True, exist_ok=True)

                # Write updated settings
                self.settings_file.write_text(
                    json.dumps(settings, indent=2), encoding="utf-8"
                )

                self.logger.info(
                    f"✅ Activated {style_name} output style (was: {current_style or 'none'})"
                )
            else:
                self.logger.debug(f"{style_name} output style already active")

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

    def get_injectable_content(
        self, framework_loader: Any = None, style: OutputStyleType = "professional"
    ) -> str:
        """
        Get output style content for injection into instructions (for Claude < 1.0.83).

        This returns a simplified version without YAML frontmatter, suitable for
        injection into the framework instructions.

        Args:
            framework_loader: Optional FrameworkLoader instance to reuse loaded content
            style: Style type to extract ("professional" or "teaching")

        Returns:
            Simplified output style content for injection
        """
        # Extract the same content but without YAML frontmatter
        full_content = self.extract_output_style_content(framework_loader, style=style)

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

    def deploy_all_styles(self, activate_default: bool = True) -> Dict[str, bool]:
        """
        Deploy all available output styles to Claude Code.

        Args:
            activate_default: Whether to activate the professional style after deployment

        Returns:
            Dictionary mapping style names to deployment success status
        """
        results: Dict[str, bool] = {}

        for style_type_key in self.styles:
            # Deploy without activation
            # Cast is safe because we know self.styles keys are OutputStyleType
            style_type = cast("OutputStyleType", style_type_key)
            success = self.deploy_output_style(style=style_type, activate=False)
            results[style_type] = success

        # Activate the default style if requested
        if activate_default and results.get("professional", False):
            self._activate_output_style("claude-mpm")

        return results

    def deploy_teaching_style(self, activate: bool = False) -> bool:
        """
        Deploy the teaching style specifically.

        Args:
            activate: Whether to activate the teaching style after deployment

        Returns:
            True if deployed successfully, False otherwise
        """
        return self.deploy_output_style(style="teaching", activate=activate)

    def list_available_styles(self) -> Dict[str, Dict[str, str]]:
        """
        List all available output styles with their metadata.

        Returns:
            Dictionary mapping style types to their configuration
        """
        available_styles = {}

        for style_type, config in self.styles.items():
            source_exists = config["source"].exists()
            target_exists = config["target"].exists()

            available_styles[style_type] = {
                "name": config["name"],
                "source_path": str(config["source"]),
                "target_path": str(config["target"]),
                "source_exists": str(source_exists),
                "deployed": str(target_exists),
            }

        return available_styles
