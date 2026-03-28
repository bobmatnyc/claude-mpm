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
import subprocess  # nosec B404
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from ..utils.imports import safe_import

# Import with fallback support
get_logger = safe_import("claude_mpm.core.logger", "core.logger", ["get_logger"])

# Global cache for Claude version to avoid duplicate detection/logging
_CACHED_CLAUDE_VERSION: str | None = None
_VERSION_DETECTED: bool = False

# Output style types
OutputStyleType = Literal[
    "professional", "teaching", "research", "founders"
]  # "founders" is deprecated, use "research"


# Reverse mapping from outputStyle IDs (settings.json) to OutputStyleType keys.
# Used by get_output_style_for_injection() and SDK/session code.
_STYLE_ID_TO_TYPE: dict[str, str] = {
    "claude_mpm": "professional",
    "claude_mpm_teacher": "teaching",
    "claude_mpm_research": "research",
}

_logger = safe_import("claude_mpm.core.logger", "core.logger", ["get_logger"])


def get_output_style_for_injection() -> str | None:
    """Load the configured output style content for injection into system prompts.

    Reads ``outputStyle`` from ``~/.claude/settings.json``, maps it to an
    ``OutputStyleType``, and returns the style content (without YAML
    frontmatter) via ``OutputStyleManager.get_injectable_content()``.

    This is the single source of truth for output-style injection logic,
    used by both ``SessionWorker`` and ``SDKAgentRunner``.

    Returns:
        The style content string, or ``None`` if no style is configured or
        the style file cannot be read.
    """
    try:
        settings_path = Path.home() / ".claude" / "settings.json"
        if not settings_path.exists():
            return None

        settings = json.loads(settings_path.read_text())
        style_id = settings.get("outputStyle")
        if not style_id:
            return None

        style_type = _STYLE_ID_TO_TYPE.get(style_id)
        if style_type is None:
            _log = _logger("output_style_manager")  # type: ignore[misc]
            _log.debug("Unknown output style '%s', skipping injection", style_id)
            return None

        manager = OutputStyleManager()
        content = manager.get_injectable_content(style=style_type)  # type: ignore[arg-type]
        if content:
            _log = _logger("output_style_manager")  # type: ignore[misc]
            _log.debug(
                "Loaded output style '%s' (%s) for injection",
                style_id,
                style_type,
            )
        return content
    except Exception:
        return None


class StyleConfig(TypedDict):
    """Configuration for an output style."""

    source: Path
    target: Path
    name: str


class OutputStyleManager:
    """Manages output style deployment and version-based handling.

    Supports three output styles:
    - professional: Default Claude MPM style (claude-mpm.md)
    - teaching: Adaptive teaching mode (claude-mpm-teacher.md)
    - research: Codebase research mode for founders, PMs, and developers (claude-mpm-research.md)
    """

    def __init__(self) -> None:
        """Initialize the output style manager."""
        self.logger = get_logger("output_style_manager")  # type: ignore[misc]
        self.claude_version = self._detect_claude_version()

        # Deploy to ~/.claude/output-styles/ directory (official Claude Code location)
        self.output_style_dir = Path.home() / ".claude" / "output-styles"
        self.settings_file = Path.home() / ".claude" / "settings.json"

        # Style definitions
        self.styles: dict[str, StyleConfig] = {
            "professional": StyleConfig(
                source=Path(__file__).parent.parent
                / "agents"
                / "CLAUDE_MPM_OUTPUT_STYLE.md",
                target=self.output_style_dir / "claude-mpm.md",
                name="Claude MPM",
            ),
            "teaching": StyleConfig(
                source=Path(__file__).parent.parent
                / "agents"
                / "CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md",
                target=self.output_style_dir / "claude-mpm-teacher.md",
                name="Claude MPM Teacher",
            ),
            "research": StyleConfig(
                source=Path(__file__).parent.parent
                / "agents"
                / "CLAUDE_MPM_RESEARCH_OUTPUT_STYLE.md",
                target=self.output_style_dir / "claude-mpm-research.md",
                name="Claude MPM Research",
            ),
            # Backward compatibility alias (deprecated)
            "founders": StyleConfig(
                source=Path(__file__).parent.parent
                / "agents"
                / "CLAUDE_MPM_RESEARCH_OUTPUT_STYLE.md",
                target=self.output_style_dir / "claude-mpm-research.md",
                name="Claude MPM Research",
            ),
        }

        # Default style path (for backward compatibility)
        self.output_style_path = self.styles["professional"]["target"]
        self.mpm_output_style_path = self.styles["professional"]["source"]

    def _detect_claude_version(self) -> str | None:
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
            result = subprocess.run(  # nosec B603 B607
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
        content: str | None = None,
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

            # Check if this is a fresh install (file doesn't exist yet)
            is_fresh_install = not target_path.exists()

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
                self._activate_output_style(
                    style_name, is_fresh_install=is_fresh_install
                )

            return True

        except Exception as e:
            self.logger.error(f"Failed to deploy {style} style: {e}")
            return False

    # Mapping from display names to Claude Code's outputStyle IDs (frontmatter `name:` field)
    _STYLE_ID_MAP: dict = {
        "Claude MPM": "claude_mpm",
        "Claude MPM Teacher": "claude_mpm_teacher",
        "Claude MPM Research": "claude_mpm_research",
    }

    def _activate_output_style(
        self, style_name: str = "Claude MPM", is_fresh_install: bool = False
    ) -> bool:
        """
        Update Claude Code settings to activate a specific output style.

        Writes the native Claude Code ``outputStyle`` key (matching the frontmatter
        ``name:`` field in the style file) so that Claude Code actually applies the
        style. Migrates away from the legacy ``activeOutputStyle`` key to prevent
        synchronization issues.

        Only activates the style if:
        1. No active style is currently set (first deployment), OR
        2. This is a fresh install (style file didn't exist before deployment)

        This preserves user preferences if they've manually changed their active style.

        Args:
            style_name: Display name of the style (e.g., "Claude MPM", "Claude MPM Teacher")
            is_fresh_install: Whether this is a fresh install (style file didn't exist before)

        Returns:
            True if activated successfully, False otherwise
        """
        try:
            # Resolve the frontmatter `name:` value that Claude Code uses as the style ID
            style_id = self._STYLE_ID_MAP.get(
                style_name, style_name.lower().replace(" ", "_")
            )

            # Load existing settings or create new
            settings = {}
            if self.settings_file.exists():
                try:
                    settings = json.loads(self.settings_file.read_text())
                except json.JSONDecodeError:
                    self.logger.warning(
                        "Could not parse existing settings.json, using defaults"
                    )

            # Migrate from dual-key model: check both keys but prefer outputStyle
            current_style = settings.get("outputStyle")
            legacy_style = settings.get("activeOutputStyle")

            # Track if we're migrating from legacy
            is_migrating_from_legacy = (
                current_style is None and legacy_style is not None
            )

            # If only legacy key exists, we'll migrate it
            if is_migrating_from_legacy:
                self.logger.info(f"Migrating legacy activeOutputStyle: {legacy_style}")
                migrated_style_id = (
                    self._STYLE_ID_MAP.get(
                        legacy_style, legacy_style.lower().replace(" ", "_")
                    )
                    if isinstance(legacy_style, str)
                    else legacy_style
                )
                current_style = migrated_style_id

            # Only set outputStyle if:
            # 1. No active style is set (first deployment), OR
            # 2. Current style is "default" (not a real user preference), OR
            # 3. This is a fresh install (file didn't exist before deployment)
            should_activate = (
                current_style is None or current_style == "default" or is_fresh_install
            )

            # Special case: If we're migrating from legacy, preserve the migrated style
            # unless it's a fresh install (which means we should reset to default)
            if is_migrating_from_legacy and not is_fresh_install:
                # Write the migrated style, don't force the default
                settings["outputStyle"] = current_style

                # Clean up legacy key
                del settings["activeOutputStyle"]
                self.logger.debug(
                    "Removed legacy activeOutputStyle key during migration"
                )

                # Ensure settings directory exists
                self.settings_file.parent.mkdir(parents=True, exist_ok=True)

                # Write updated settings
                self.settings_file.write_text(
                    json.dumps(settings, indent=2), encoding="utf-8"
                )

                self.logger.info(
                    f"✅ Migrated to outputStyle: {current_style} (was activeOutputStyle: {legacy_style})"
                )
            elif is_fresh_install or (should_activate and current_style != style_id):
                # Normal activation logic for new deployments
                settings["outputStyle"] = style_id

                # Clean up legacy key to prevent future synchronization issues
                if "activeOutputStyle" in settings:
                    del settings["activeOutputStyle"]
                    self.logger.debug(
                        "Removed legacy activeOutputStyle key during activation"
                    )

                # Ensure settings directory exists
                self.settings_file.parent.mkdir(parents=True, exist_ok=True)

                # Write updated settings
                self.settings_file.write_text(
                    json.dumps(settings, indent=2), encoding="utf-8"
                )

                self.logger.info(
                    f"✅ Activated {style_name} output style (id={style_id}, was: {current_style or 'none'})"
                )
            else:
                # Even if we're not changing the active style, clean up legacy key if present
                if "activeOutputStyle" in settings:
                    del settings["activeOutputStyle"]
                    self.settings_file.write_text(
                        json.dumps(settings, indent=2), encoding="utf-8"
                    )
                    self.logger.debug("Cleaned up legacy activeOutputStyle key")

                self.logger.debug(
                    f"Preserving user preference: {current_style or 'none'} "
                    f"(skipping activation of {style_name})"
                )

            return True

        except Exception as e:
            self.logger.warning(f"Failed to update settings: {e}")
            return False

    def get_status_summary(self) -> dict[str, str]:
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
                    status["active_style"] = settings.get("outputStyle", "none")
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

    def deploy_all_styles(self, activate_default: bool = True) -> dict[str, bool]:
        """
        Deploy all available output styles to Claude Code.

        Args:
            activate_default: Whether to activate the professional style after deployment

        Returns:
            Dictionary mapping style names to deployment success status
        """
        results: dict[str, bool] = {}

        # Check if professional style exists BEFORE deployment
        # This determines if this is a fresh install
        professional_style_existed = self.styles["professional"]["target"].exists()

        for style_type_key in self.styles:
            # Deploy without activation
            # Cast is safe because we know self.styles keys are OutputStyleType
            style_type = cast("OutputStyleType", style_type_key)
            success = self.deploy_output_style(style=style_type, activate=False)
            results[style_type] = success

        # Activate the default style if requested AND deployment succeeded
        if activate_default and results.get("professional", False):
            file_fresh_install = not professional_style_existed

            # Check for existing preferences (both native and legacy)
            existing_preference = None
            has_settings_file = False
            if self.settings_file.exists():
                has_settings_file = True
                try:
                    settings = json.loads(self.settings_file.read_text())
                    existing_preference = settings.get("outputStyle") or settings.get(
                        "activeOutputStyle"
                    )
                except json.JSONDecodeError:
                    pass

            # Determine the activation strategy:
            # 1. True fresh install: No files AND no settings -> Activate default
            # 2. File deleted but settings exist: Reset to default (user deleted files intentionally)
            # 3. Migration case: Files didn't exist but settings do -> Preserve/migrate setting
            # 4. Normal case: Files exist, maybe settings -> Only set if no preference

            if file_fresh_install and not has_settings_file:
                # True fresh install: no files, no settings
                self._activate_output_style("Claude MPM", is_fresh_install=True)
            elif file_fresh_install and has_settings_file and existing_preference:
                # Check if this is a migration case vs file deletion case
                # Migration case: preference is a known MPM style (exact match or mappable)
                known_mpm_styles = {
                    "Claude MPM",
                    "claude_mpm",
                    "Claude MPM Teacher",
                    "claude_mpm_teacher",
                    "Claude MPM Research",
                    "claude_mpm_research",
                }

                if existing_preference in known_mpm_styles:
                    # Migration case: settings exist with known MPM style but files don't exist yet
                    # Preserve the user's original style choice
                    self._activate_output_style(
                        existing_preference, is_fresh_install=False
                    )
                else:
                    # File deletion case: user had custom style but files were deleted
                    # Reset to default as files were intentionally removed
                    self._activate_output_style("Claude MPM", is_fresh_install=True)
            elif file_fresh_install and has_settings_file:
                # File deletion case: settings exist but no preference or default
                self._activate_output_style("Claude MPM", is_fresh_install=True)
            # Normal case: files exist, check preferences
            elif existing_preference is None or existing_preference == "default":
                self._activate_output_style("Claude MPM", is_fresh_install=False)
            else:
                # Existing preference, just clean up dual keys
                self._activate_output_style("Claude MPM", is_fresh_install=False)

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

    def list_available_styles(self) -> dict[str, dict[str, str]]:
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
