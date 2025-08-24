"""
Environment context detection for smart dependency checking.

This module determines the execution environment and whether interactive
prompting is appropriate for dependency installation.
"""

import os
import sys
from typing import Dict, Tuple

from ..core.logger import get_logger

logger = get_logger(__name__)


class EnvironmentContext:
    """
    Detects and analyzes the execution environment.

    WHY: We need to know if we're in an environment where prompting makes sense.
    Interactive prompting should only happen in TTY environments where a human
    is present. CI/CD, Docker, and non-interactive contexts should skip prompts.

    DESIGN DECISION: Use multiple indicators to detect environment type:
    - TTY presence is the primary indicator for interactivity
    - Environment variables help identify CI/CD and containerized environments
    - Command-line flags can override automatic detection
    """

    # Known CI environment variables
    CI_ENV_VARS = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS",
        "TRAVIS",
        "CIRCLECI",
        "BUILDKITE",
        "DRONE",
        "TEAMCITY_VERSION",
        "TF_BUILD",
        "CODEBUILD_BUILD_ID",
        "BITBUCKET_BUILD_NUMBER",
    ]

    # Docker/container indicators
    CONTAINER_INDICATORS = [
        "/.dockerenv",  # Docker creates this file
        "/run/.containerenv",  # Podman creates this file
    ]

    @classmethod
    def detect_execution_context(cls) -> Dict[str, bool]:
        """
        Detect the current execution context.

        Returns:
            Dictionary with context indicators:
            - is_tty: True if running in a terminal with TTY
            - is_ci: True if running in CI/CD environment
            - is_docker: True if running inside Docker container
            - is_interactive: True if interactive prompting is possible
            - is_automated: True if running in automated context (CI or scheduled)
        """
        context = {
            "is_tty": cls._detect_tty(),
            "is_ci": cls._detect_ci(),
            "is_docker": cls._detect_docker(),
            "is_interactive": False,
            "is_automated": False,
            "is_jupyter": cls._detect_jupyter(),
            "is_ssh": cls._detect_ssh(),
        }

        # Determine if we're in an automated context
        context["is_automated"] = context["is_ci"] or cls._detect_automated()

        # Interactive if TTY is available and not in automated context
        context["is_interactive"] = (
            context["is_tty"]
            and not context["is_automated"]
            and not context["is_docker"]  # Docker usually non-interactive
        )

        logger.debug(f"Environment context detected: {context}")
        return context

    @classmethod
    def _detect_tty(cls) -> bool:
        """
        Detect if we have a TTY (terminal) available.

        WHY: TTY presence is the most reliable indicator that a human
        is present and can respond to prompts.
        """
        try:
            # Check if stdin is a terminal
            has_stdin_tty = (
                sys.stdin.isatty() if hasattr(sys.stdin, "isatty") else False
            )

            # Check if stdout is a terminal (for output)
            has_stdout_tty = (
                sys.stdout.isatty() if hasattr(sys.stdout, "isatty") else False
            )

            # Both should be TTY for interactive use
            return has_stdin_tty and has_stdout_tty
        except Exception as e:
            logger.debug(f"TTY detection failed: {e}")
            return False

    @classmethod
    def _detect_ci(cls) -> bool:
        """
        Detect if running in a CI/CD environment.

        WHY: CI environments should never prompt for user input.
        They need to run fully automated without human intervention.
        """
        # Check for common CI environment variables
        for var in cls.CI_ENV_VARS:
            if os.environ.get(var):
                logger.debug(f"CI environment detected via {var}={os.environ.get(var)}")
                return True

        # Additional heuristics for CI detection
        return bool(os.environ.get("BUILD_ID") or os.environ.get("BUILD_NUMBER"))

    @classmethod
    def _detect_docker(cls) -> bool:
        """
        Detect if running inside a Docker container.

        WHY: Docker containers typically run non-interactively,
        and prompting for input often doesn't make sense.
        """
        # Check for Docker-specific files
        for indicator_file in cls.CONTAINER_INDICATORS:
            if os.path.exists(indicator_file):
                logger.debug(f"Container detected via {indicator_file}")
                return True

        # Check for container-related environment variables
        if os.environ.get("KUBERNETES_SERVICE_HOST"):
            return True

        # Check cgroup for docker/containerd references
        try:
            with open("/proc/1/cgroup") as f:
                cgroup_content = f.read()
                if "docker" in cgroup_content or "containerd" in cgroup_content:
                    return True
        except (FileNotFoundError, PermissionError):
            pass

        return False

    @classmethod
    def _detect_automated(cls) -> bool:
        """
        Detect if running in an automated context (cron, systemd, etc).

        WHY: Automated scripts should not prompt for input even if
        they technically have TTY access.
        """
        # Check for cron execution
        if os.environ.get("CRON") or not os.environ.get("TERM"):
            return True

        # Check for systemd service
        if os.environ.get("INVOCATION_ID"):  # systemd sets this
            return True

        return False

    @classmethod
    def _detect_jupyter(cls) -> bool:
        """
        Detect if running in Jupyter notebook/lab.

        WHY: Jupyter has its own interaction model and standard
        terminal prompts don't work well.
        """
        try:
            # Check for IPython/Jupyter
            get_ipython = globals().get("get_ipython")
            if get_ipython is not None:
                return True
        except:
            pass

        # Check for Jupyter-specific environment variables
        return "JPY_PARENT_PID" in os.environ

    @classmethod
    def _detect_ssh(cls) -> bool:
        """
        Detect if running over SSH.

        WHY: SSH sessions might have TTY but prompting behavior
        should be more conservative.
        """
        return "SSH_CLIENT" in os.environ or "SSH_TTY" in os.environ

    @classmethod
    def should_prompt_for_dependencies(
        cls, force_prompt: bool = False, force_skip: bool = False
    ) -> Tuple[bool, str]:
        """
        Determine if we should prompt for dependency installation.

        Args:
            force_prompt: Force prompting regardless of environment
            force_skip: Force skipping prompts regardless of environment

        Returns:
            Tuple of (should_prompt, reason_message)

        WHY: This is the main decision point for the smart dependency system.
        We want to prompt only when it makes sense and is safe to do so.
        """
        # Handle forced flags
        if force_skip:
            return False, "Prompting disabled by --no-prompt flag"
        if force_prompt:
            return True, "Prompting forced by --prompt flag"

        # Get environment context
        context = cls.detect_execution_context()

        # Decision logic with clear reasoning
        if not context["is_tty"]:
            return False, "No TTY available for interactive prompts"

        if context["is_ci"]:
            return False, "Running in CI environment - prompts disabled"

        if context["is_docker"]:
            return False, "Running in Docker container - prompts disabled"

        if context["is_automated"]:
            return False, "Running in automated context - prompts disabled"

        if context["is_jupyter"]:
            return False, "Running in Jupyter - standard prompts not supported"

        if context["is_interactive"]:
            return True, "Interactive TTY environment detected"

        # Default to not prompting if uncertain
        return False, "Environment type uncertain - prompts disabled for safety"

    @classmethod
    def get_environment_summary(cls) -> str:
        """
        Get a human-readable summary of the environment.

        Returns:
            String describing the detected environment.
        """
        context = cls.detect_execution_context()

        env_types = []
        if context["is_ci"]:
            env_types.append("CI/CD")
        if context["is_docker"]:
            env_types.append("Docker")
        if context["is_jupyter"]:
            env_types.append("Jupyter")
        if context["is_ssh"]:
            env_types.append("SSH")
        if context["is_automated"]:
            env_types.append("Automated")

        if not env_types:
            if context["is_interactive"]:
                env_types.append("Interactive Terminal")
            else:
                env_types.append("Non-interactive")

        return f"Environment: {', '.join(env_types)} (TTY: {context['is_tty']})"


def detect_execution_context() -> Dict[str, bool]:
    """
    Convenience function to detect execution context.

    Returns:
        Dictionary with context indicators.
    """
    return EnvironmentContext.detect_execution_context()


def should_prompt_for_dependencies(
    force_prompt: bool = False, force_skip: bool = False
) -> Tuple[bool, str]:
    """
    Convenience function to determine if prompting is appropriate.

    Args:
        force_prompt: Force prompting regardless of environment
        force_skip: Force skipping prompts regardless of environment

    Returns:
        Tuple of (should_prompt, reason_message)
    """
    return EnvironmentContext.should_prompt_for_dependencies(
        force_prompt=force_prompt, force_skip=force_skip
    )
