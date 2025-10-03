from pathlib import Path

"""Experimental features configuration for Claude MPM.

WHY: This module manages experimental and beta features, providing a centralized
way to control feature flags and display appropriate warnings to users.

DESIGN DECISION: Use a simple configuration class with static defaults that can
be overridden through environment variables or config files. This allows for
gradual rollout of experimental features while maintaining stability in production.
"""

import json
import os
from typing import ClassVar, Dict, Optional


class ExperimentalFeatures:
    """Manages experimental feature flags and warnings.

    WHY: Experimental features need special handling to ensure users understand
    they are using beta functionality that may change or have issues.

    DESIGN DECISION: Use environment variables for quick override during development,
    but also support configuration files for persistent settings.
    """

    # Default feature flags
    DEFAULTS: ClassVar[Dict[str, bool]] = {
        "enable_mcp_gateway": False,  # MCP Gateway is experimental
        "enable_advanced_aggregation": False,  # Advanced aggregation features
        "show_experimental_warnings": True,  # Show warnings for experimental features
        "require_experimental_acceptance": True,  # Require explicit acceptance
    }

    # Warning messages for experimental features
    WARNINGS: ClassVar[Dict[str, str]] = {
        "mcp_gateway": (
            "⚠️  EXPERIMENTAL FEATURE: MCP Gateway is in early access.\n"
            "   Tool integration may be unstable. Not recommended for production use."
        ),
        "advanced_aggregation": (
            "⚠️  EXPERIMENTAL FEATURE: Advanced aggregation is under development.\n"
            "   Results may vary. Please verify outputs manually."
        ),
    }

    def __init__(self, config_file: Optional[Path] = None):
        """Initialize experimental features configuration.

        Args:
            config_file: Optional path to configuration file
        """
        self._features = self.DEFAULTS.copy()
        self._config_file = config_file
        self._load_configuration()
        self._apply_environment_overrides()

    def _load_configuration(self):
        """Load configuration from file if it exists.

        WHY: Allow persistent configuration of experimental features without
        requiring environment variables to be set every time.
        """
        if self._config_file and self._config_file.exists():
            try:
                with self._config_file.open() as f:
                    config = json.load(f)
                    experimental = config.get("experimental_features", {})
                    self._features.update(experimental)
            except Exception:
                # Silently ignore configuration errors for experimental features
                pass

    def _apply_environment_overrides(self):
        """Apply environment variable overrides.

        WHY: Environment variables provide a quick way to enable/disable features
        during development and testing without modifying configuration files.

        Format: CLAUDE_MPM_EXPERIMENTAL_<FEATURE_NAME>=true/false
        """
        for key in self._features:
            env_key = f"CLAUDE_MPM_EXPERIMENTAL_{key.upper()}"
            if env_key in os.environ:
                value = os.environ[env_key].lower()
                self._features[key] = value in ("true", "1", "yes", "on")

    def is_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled.

        Args:
            feature: Feature name (without 'enable_' prefix)

        Returns:
            True if the feature is enabled
        """
        key = f"enable_{feature}" if not feature.startswith("enable_") else feature
        return self._features.get(key, False)

    def get_warning(self, feature: str) -> Optional[str]:
        """Get warning message for a feature.

        Args:
            feature: Feature name

        Returns:
            Warning message or None if no warning exists
        """
        return self.WARNINGS.get(feature)

    def should_show_warning(self, feature: str) -> bool:
        """Check if warning should be shown for a feature.

        Args:
            feature: Feature name

        Returns:
            True if warning should be displayed
        """
        if not self._features.get("show_experimental_warnings", True):
            return False

        # Check if user has already accepted this feature
        accepted_file = Path.home() / ".claude-mpm" / ".experimental_accepted"
        if accepted_file.exists():
            try:
                with accepted_file.open() as f:
                    accepted = json.load(f)
                    if feature in accepted.get("features", []):
                        return False
            except Exception:
                pass

        return True

    def mark_accepted(self, feature: str):
        """Mark a feature as accepted by the user.

        WHY: Once a user accepts the experimental status, we don't need to
        warn them every time they use the feature.

        Args:
            feature: Feature name to mark as accepted
        """
        accepted_file = Path.home() / ".claude-mpm" / ".experimental_accepted"
        accepted_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            if accepted_file.exists():
                with accepted_file.open() as f:
                    data = json.load(f)
            else:
                data = {"features": [], "timestamp": {}}

            if feature not in data["features"]:
                data["features"].append(feature)
                data["timestamp"][feature] = os.environ.get(
                    "CLAUDE_MPM_TIMESTAMP", str(Path.cwd())
                )

            with accepted_file.open("w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            # Silently ignore errors in acceptance tracking
            pass

    def requires_acceptance(self) -> bool:
        """Check if experimental features require explicit acceptance.

        Returns:
            True if acceptance is required
        """
        return self._features.get("require_experimental_acceptance", True)

    def get_all_features(self) -> Dict[str, bool]:
        """Get all feature flags and their current values.

        Returns:
            Dictionary of feature flags and their values
        """
        return self._features.copy()


# Global instance for easy access
_experimental_features = None


def get_experimental_features(
    config_file: Optional[Path] = None,
) -> ExperimentalFeatures:
    """Get the global experimental features instance.

    WHY: Provide a singleton-like access pattern to experimental features
    configuration to ensure consistency across the application.

    Args:
        config_file: Optional configuration file path

    Returns:
        ExperimentalFeatures instance
    """
    global _experimental_features
    if _experimental_features is None:
        # Check for config file in standard locations
        if config_file is None:
            for path in [
                Path.cwd() / ".claude-mpm" / "experimental.json",
                Path.home() / ".claude-mpm" / "experimental.json",
            ]:
                if path.exists():
                    config_file = path
                    break

        _experimental_features = ExperimentalFeatures(config_file)

    return _experimental_features
