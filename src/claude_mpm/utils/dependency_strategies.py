from pathlib import Path

"""
Dependency management strategies for different contexts.

This module provides smart dependency checking and installation strategies
based on the execution context and user preferences.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from ..core.logger import get_logger

logger = get_logger(__name__)


class DependencyMode(Enum):
    """Dependency checking and installation modes."""

    OFF = "off"  # No checking at all
    CHECK = "check"  # Check and warn only
    INTERACTIVE = "interactive"  # Prompt user for installation
    AUTO = "auto"  # Automatically install missing deps
    LAZY = "lazy"  # Check only when agent is invoked


class DependencyStrategy:
    """
    Smart dependency management based on context and preferences.

    This class determines the appropriate dependency strategy based on:
    - Execution environment (CI, Docker, TTY, etc.)
    - User configuration
    - Cached check results
    - Command being executed
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize dependency strategy manager.

        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path or Path.home() / ".claude-mpm" / "config.yaml"
        self.cache_path = Path.home() / ".claude-mpm" / ".dep_cache.json"
        self.mode = self._determine_mode()

    def _determine_mode(self) -> DependencyMode:
        """
        Determine the appropriate dependency mode based on context.

        Returns:
            The dependency mode to use
        """
        # Check environment variable override
        env_mode = os.environ.get("CLAUDE_MPM_DEP_MODE")
        if env_mode:
            try:
                return DependencyMode(env_mode.lower())
            except ValueError:
                logger.warning(f"Invalid CLAUDE_MPM_DEP_MODE: {env_mode}")

        # Check if in CI environment
        if self._is_ci_environment():
            logger.debug("CI environment detected - using CHECK mode")
            return DependencyMode.CHECK

        # Check if in Docker container
        if self._is_docker():
            logger.debug("Docker environment detected - using CHECK mode")
            return DependencyMode.CHECK

        # Check if non-interactive terminal
        if not self._is_interactive():
            logger.debug("Non-interactive terminal - using CHECK mode")
            return DependencyMode.CHECK

        # Load user configuration
        user_mode = self._load_user_preference()
        if user_mode:
            return user_mode

        # Default to interactive for TTY sessions
        return DependencyMode.INTERACTIVE

    def _is_ci_environment(self) -> bool:
        """Check if running in CI environment."""
        ci_indicators = [
            "CI",
            "CONTINUOUS_INTEGRATION",
            "JENKINS",
            "TRAVIS",
            "CIRCLECI",
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "BUILDKITE",
        ]
        return any(os.environ.get(var) for var in ci_indicators)

    def _is_docker(self) -> bool:
        """Check if running inside Docker container."""
        return (
            Path("/.dockerenv").exists()
            or os.environ.get("KUBERNETES_SERVICE_HOST") is not None
        )

    def _is_interactive(self) -> bool:
        """Check if running in interactive terminal."""
        return sys.stdin.isatty() and sys.stdout.isatty()

    def _load_user_preference(self) -> Optional[DependencyMode]:
        """
        Load user preference from config file.

        Returns:
            User's preferred dependency mode or None
        """
        if not self.config_path.exists():
            return None

        try:
            # Try to load YAML config
            import yaml

            with self.config_path.open() as f:
                config = yaml.safe_load(f)
                mode_str = config.get("dependency_mode")
                if mode_str:
                    return DependencyMode(mode_str)
        except Exception as e:
            logger.debug(f"Could not load config: {e}")

        return None

    def should_check_now(self, cache_ttl: int = 86400) -> bool:
        """
        Determine if dependency check should run now based on cache.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 24 hours)

        Returns:
            True if check should run, False if cached results are fresh
        """
        if self.mode == DependencyMode.OFF:
            return False

        if not self.cache_path.exists():
            return True

        try:
            with self.cache_path.open() as f:
                cache = json.load(f)
                last_check = datetime.fromisoformat(cache.get("timestamp", ""))

                # Check if cache is still valid
                if datetime.now(timezone.utc) - last_check < timedelta(
                    seconds=cache_ttl
                ):
                    logger.debug(f"Using cached dependency check from {last_check}")
                    return False

        except Exception as e:
            logger.debug(f"Cache invalid or corrupted: {e}")

        return True

    def cache_results(self, results: Dict[str, Any]) -> None:
        """
        Cache dependency check results.

        Args:
            results: Dependency check results to cache
        """
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "results": results,
            }

            with self.cache_path.open("w") as f:
                json.dump(cache_data, f, indent=2)

            logger.debug(f"Cached dependency results to {self.cache_path}")

        except Exception as e:
            logger.warning(f"Failed to cache results: {e}")

    def get_cached_results(self) -> Optional[Dict[str, Any]]:
        """
        Get cached dependency check results if available.

        Returns:
            Cached results or None
        """
        if not self.cache_path.exists():
            return None

        try:
            with self.cache_path.open() as f:
                cache = json.load(f)
                return cache.get("results")
        except Exception:
            return None

    def prompt_for_installation(self, missing_deps: list) -> str:
        """
        Prompt user for dependency installation preference.

        Args:
            missing_deps: List of missing dependencies

        Returns:
            User's choice: 'yes', 'no', 'always', 'never'
        """
        if not self._is_interactive():
            return "no"

        print(f"\n⚠️  Missing {len(missing_deps)} dependencies:")
        for dep in missing_deps[:5]:  # Show first 5
            print(f"  - {dep}")
        if len(missing_deps) > 5:
            print(f"  ... and {len(missing_deps) - 5} more")

        while True:
            sys.stdout.flush()  # Ensure prompt is displayed before input

            # Check if we're in a TTY environment for proper input handling
            if not sys.stdin.isatty():
                # In non-TTY environment (like pipes), use readline
                print(
                    "\nInstall missing dependencies? [y/N/always/never]: ",
                    end="",
                    flush=True,
                )
                try:
                    response = sys.stdin.readline().strip().lower()
                    # Handle various line endings and control characters
                    response = response.replace("\r", "").replace("\n", "").strip()
                except (EOFError, KeyboardInterrupt):
                    response = "n"
            else:
                # In TTY environment, use normal input()
                try:
                    response = (
                        input("\nInstall missing dependencies? [y/N/always/never]: ")
                        .lower()
                        .strip()
                    )
                except (EOFError, KeyboardInterrupt):
                    response = "n"

            if response in ["y", "yes"]:
                return "yes"
            if response in ["n", "no", ""]:
                return "no"
            if response == "always":
                self._save_preference(DependencyMode.AUTO)
                return "yes"
            if response == "never":
                self._save_preference(DependencyMode.OFF)
                return "no"
            print("Invalid choice. Please enter: y, n, always, or never")

    def _save_preference(self, mode: DependencyMode) -> None:
        """
        Save user's dependency mode preference.

        Args:
            mode: The dependency mode to save
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing config or create new
            config = {}
            if self.config_path.exists():
                import yaml

                with self.config_path.open() as f:
                    config = yaml.safe_load(f) or {}

            # Update dependency mode
            config["dependency_mode"] = mode.value

            # Save config
            import yaml

            with self.config_path.open("w") as f:
                yaml.dump(config, f, default_flow_style=False)

            print(f"✓ Saved preference: {mode.value}")

        except Exception as e:
            logger.error(f"Failed to save preference: {e}")


def get_smart_dependency_handler(
    command: Optional[str] = None,
) -> Tuple[DependencyMode, DependencyStrategy]:
    """
    Get the appropriate dependency handler for the current context.

    Args:
        command: The command being executed (e.g., 'run', 'agents')

    Returns:
        Tuple of (mode, strategy) to use
    """
    strategy = DependencyStrategy()

    # Override for specific commands
    if command == "agents" and "deps-" in str(sys.argv):
        # If running agents deps-* commands, don't check automatically
        return (DependencyMode.OFF, strategy)

    # Quick commands shouldn't check dependencies
    quick_commands = ["help", "version", "info", "tickets"]
    if command in quick_commands:
        return (DependencyMode.OFF, strategy)

    return (strategy.mode, strategy)


def lazy_check_agent_dependency(agent_id: str) -> bool:
    """
    Lazily check dependencies when a specific agent is invoked.

    Args:
        agent_id: The agent being invoked

    Returns:
        True if dependencies are satisfied or installed, False otherwise
    """
    from .agent_dependency_loader import AgentDependencyLoader

    logger.debug(f"Lazy checking dependencies for agent: {agent_id}")

    loader = AgentDependencyLoader(auto_install=False)
    loader.discover_deployed_agents()

    # Only check the specific agent
    if agent_id not in loader.deployed_agents:
        return True  # Agent not deployed, no deps to check

    loader.deployed_agents = {agent_id: loader.deployed_agents[agent_id]}
    loader.load_agent_dependencies()
    results = loader.analyze_dependencies()

    agent_results = results["agents"].get(agent_id, {})
    missing = agent_results.get("python", {}).get("missing", [])

    if not missing:
        return True

    # Get strategy for handling missing deps
    strategy = DependencyStrategy()

    if strategy.mode == DependencyMode.AUTO:
        logger.info(f"Auto-installing {len(missing)} dependencies for {agent_id}")
        success, _ = loader.install_missing_dependencies(missing)
        return success

    if strategy.mode == DependencyMode.INTERACTIVE:
        choice = strategy.prompt_for_installation(missing)
        if choice in ["yes"]:
            success, _ = loader.install_missing_dependencies(missing)
            return success
        return False

    # CHECK or OFF
    logger.warning(f"Agent {agent_id} missing {len(missing)} dependencies")
    return False  # Proceed anyway
