"""
Robust dependency installer with retry logic and fallback strategies.

WHY: Network issues and temporary unavailability can cause dependency installation
to fail. This module provides resilient installation with automatic retries,
fallback strategies, and clear error reporting.

DESIGN DECISION: We implement exponential backoff for retries and provide
multiple installation strategies (pip, conda, source) to maximize success rate.
"""

import re
import subprocess
import sys
import sysconfig
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.logger import get_logger

logger = get_logger(__name__)


class InstallStrategy(Enum):
    """Available installation strategies."""

    PIP = "pip"
    PIP_NO_DEPS = "pip_no_deps"
    PIP_UPGRADE = "pip_upgrade"
    PIP_INDEX_URL = "pip_index_url"
    SOURCE = "source"


@dataclass
class InstallAttempt:
    """Record of an installation attempt."""

    strategy: InstallStrategy
    package: str
    success: bool
    error: Optional[str]
    duration: float
    retry_count: int


class RobustPackageInstaller:
    """
    Robust package installer with retry logic and multiple strategies.

    WHY: This class handles the complexity of package installation in various
    environments, network conditions, and Python versions. It ensures maximum
    success rate while providing clear feedback on failures.

    DECISION: Added PEP 668 detection and handling to work with externally managed
    Python environments (like Homebrew's Python 3.13).
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        timeout: int = 300,
        use_cache: bool = True,
    ):
        """
        Initialize robust installer.

        Args:
            max_retries: Maximum number of retry attempts per package
            retry_delay: Initial delay between retries (uses exponential backoff)
            timeout: Maximum time for each installation attempt in seconds
            use_cache: Whether to use pip cache
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.use_cache = use_cache
        self.attempts: List[InstallAttempt] = []
        self.success_cache: Dict[str, bool] = {}
        self.is_pep668_managed = self._check_pep668_managed()
        self.pep668_warning_shown = False

    def install_package(
        self, package_spec: str, strategies: Optional[List[InstallStrategy]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Install a package using robust retry logic and multiple strategies.

        WHY: Single installation attempts often fail due to transient issues.
        This method tries multiple strategies with retries to maximize success.

        Args:
            package_spec: Package specification (e.g., "pandas>=2.0.0")
            strategies: List of strategies to try (defaults to sensible order)

        Returns:
            Tuple of (success, error_message)
        """
        # Check success cache first
        if package_spec in self.success_cache:
            if self.success_cache[package_spec]:
                logger.debug(f"Package {package_spec} already successfully installed")
                return True, None

        # Default strategy order
        if strategies is None:
            strategies = [
                InstallStrategy.PIP,
                InstallStrategy.PIP_UPGRADE,
                InstallStrategy.PIP_NO_DEPS,
                InstallStrategy.PIP_INDEX_URL,
            ]

        # Extract package name for special handling
        package_name = self._extract_package_name(package_spec)

        # Special handling for known problematic packages
        if self._needs_special_handling(package_name):
            strategies = self._get_special_strategies(package_name)

        # Try each strategy with retries
        for strategy in strategies:
            for retry in range(self.max_retries):
                start_time = time.time()

                # Calculate delay with exponential backoff
                if retry > 0:
                    delay = self.retry_delay * (2 ** (retry - 1))
                    logger.info(
                        f"Retry {retry}/{self.max_retries} after {delay:.1f}s delay..."
                    )
                    time.sleep(delay)

                # Attempt installation
                success, error = self._attempt_install(package_spec, strategy)
                duration = time.time() - start_time

                # Record attempt
                self.attempts.append(
                    InstallAttempt(
                        strategy=strategy,
                        package=package_spec,
                        success=success,
                        error=error,
                        duration=duration,
                        retry_count=retry,
                    )
                )

                if success:
                    logger.info(
                        f"Successfully installed {package_spec} using {strategy.value}"
                    )
                    self.success_cache[package_spec] = True
                    return True, None

                # Check if error is retryable
                if not self._is_retryable_error(error):
                    logger.warning(f"Non-retryable error for {package_spec}: {error}")
                    break

        # All attempts failed
        self.success_cache[package_spec] = False
        final_error = self._get_consolidated_error(package_spec)
        return False, final_error

    def _attempt_install(
        self, package_spec: str, strategy: InstallStrategy
    ) -> Tuple[bool, Optional[str]]:
        """
        Attempt to install a package using a specific strategy.

        Args:
            package_spec: Package specification
            strategy: Installation strategy to use

        Returns:
            Tuple of (success, error_message)
        """
        try:
            cmd = self._build_install_command(package_spec, strategy)
            logger.debug(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout, check=False
            )

            if result.returncode == 0:
                # Verify installation
                if self._verify_installation(package_spec):
                    return True, None
                return False, "Package installed but verification failed"
            error_msg = self._extract_error_message(result.stderr)
            logger.debug(f"Installation failed: {error_msg}")
            return False, error_msg

        except subprocess.TimeoutExpired:
            return False, f"Installation timed out after {self.timeout}s"
        except Exception as e:
            return False, f"Unexpected error: {e!s}"

    def _check_pep668_managed(self) -> bool:
        """
        Check if Python environment is PEP 668 externally managed.

        WHY: PEP 668 prevents pip from installing packages into system Python
        to avoid conflicts with system package managers (like Homebrew).

        Returns:
            True if PEP 668 managed, False otherwise
        """
        # Check for EXTERNALLY-MANAGED marker file
        stdlib_path = sysconfig.get_path("stdlib")
        marker_file = Path(stdlib_path) / "EXTERNALLY-MANAGED"

        if marker_file.exists():
            logger.debug(f"PEP 668 EXTERNALLY-MANAGED marker found at {marker_file}")
            return True

        # Also check parent directory (some Python installations place it there)
        parent_marker = marker_file.parent.parent / "EXTERNALLY-MANAGED"
        if parent_marker.exists():
            logger.debug(f"PEP 668 EXTERNALLY-MANAGED marker found at {parent_marker}")
            return True

        return False

    def _show_pep668_warning(self) -> None:
        """
        Show warning about PEP 668 managed environment.

        WHY: Users should understand why we're bypassing PEP 668 restrictions
        and be encouraged to use virtual environments as best practice.
        """
        if not self.pep668_warning_shown:
            logger.warning(
                "⚠️  PEP 668 MANAGED ENVIRONMENT DETECTED\n"
                "Your Python installation is marked as externally managed (PEP 668).\n"
                "This typically means you're using a system Python managed by Homebrew, apt, etc.\n"
                "\n"
                "Installing packages with --break-system-packages --user flags...\n"
                "\n"
                "RECOMMENDED: Use a virtual environment instead:\n"
                "  python -m venv .venv\n"
                "  source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate\n"
                "  pip install claude-mpm\n"
            )
            self.pep668_warning_shown = True

    def _build_install_command(
        self, package_spec: str, strategy: InstallStrategy
    ) -> List[str]:
        """
        Build the installation command for a given strategy.

        WHY: PEP 668 support added to handle externally managed Python
        environments by adding appropriate flags when needed.

        Args:
            package_spec: Package specification
            strategy: Installation strategy

        Returns:
            Command as list of arguments
        """
        base_cmd = [sys.executable, "-m", "pip", "install"]

        # Add PEP 668 bypass flags if needed
        if self.is_pep668_managed:
            self._show_pep668_warning()
            # Add flags to bypass PEP 668 restrictions
            base_cmd.extend(["--break-system-packages", "--user"])
            logger.debug(
                "Added --break-system-packages --user flags for PEP 668 environment"
            )

        # Add cache control
        if not self.use_cache:
            base_cmd.append("--no-cache-dir")

        if strategy == InstallStrategy.PIP:
            return [*base_cmd, package_spec]

        if strategy == InstallStrategy.PIP_NO_DEPS:
            return [*base_cmd, "--no-deps", package_spec]

        if strategy == InstallStrategy.PIP_UPGRADE:
            return [*base_cmd, "--upgrade", package_spec]

        if strategy == InstallStrategy.PIP_INDEX_URL:
            # Try alternative index (PyPI mirror)
            return [
                *base_cmd,
                "--index-url",
                "https://pypi.org/simple",
                "--extra-index-url",
                "https://pypi.python.org/simple",
                package_spec,
            ]

        return [*base_cmd, package_spec]

    def _extract_package_name(self, package_spec: str) -> str:
        """
        Extract package name from specification.

        Args:
            package_spec: Package specification (e.g., "pandas>=2.0.0")

        Returns:
            Package name (e.g., "pandas")
        """
        # Remove version specifiers
        match = re.match(r"^([a-zA-Z0-9_-]+)", package_spec)
        if match:
            return match.group(1)
        return package_spec

    def _needs_special_handling(self, package_name: str) -> bool:
        """
        Check if package needs special installation handling.

        Args:
            package_name: Name of the package

        Returns:
            True if package needs special handling
        """
        # Known problematic packages
        special_packages = {
            "tree-sitter-ruby",
            "tree-sitter-php",
            "tree-sitter-javascript",
            "tree-sitter-typescript",
            "tree-sitter-go",
            "tree-sitter-rust",
            "tree-sitter-java",
            "tree-sitter-cpp",
            "tree-sitter-c",
        }

        return package_name.lower() in special_packages

    def _get_special_strategies(self, package_name: str) -> List[InstallStrategy]:
        """
        Get special installation strategies for problematic packages.

        Args:
            package_name: Name of the package

        Returns:
            List of strategies to try
        """
        # For tree-sitter packages, try upgrade first (often fixes version conflicts)
        if package_name.startswith("tree-sitter-"):
            return [
                InstallStrategy.PIP_UPGRADE,
                InstallStrategy.PIP,
                InstallStrategy.PIP_INDEX_URL,
                InstallStrategy.PIP_NO_DEPS,
            ]

        return [InstallStrategy.PIP, InstallStrategy.PIP_UPGRADE]

    def _verify_installation(self, package_spec: str) -> bool:
        """
        Verify that a package was successfully installed.

        Args:
            package_spec: Package specification

        Returns:
            True if package is installed and importable
        """
        package_name = self._extract_package_name(package_spec)

        # Convert package name to import name (e.g., tree-sitter-ruby -> tree_sitter_ruby)
        import_name = package_name.replace("-", "_")

        try:
            # Check if package is installed
            import importlib.metadata

            try:
                version = importlib.metadata.version(package_name)
                logger.debug(f"Package {package_name} version {version} is installed")

                # For tree-sitter packages, don't try to import (they have C extensions)
                if package_name.startswith("tree-sitter-"):
                    return True

                # Try to import the package
                try:
                    __import__(import_name)
                    return True
                except ImportError:
                    # Some packages have different import names, that's OK
                    return True

            except importlib.metadata.PackageNotFoundError:
                return False

        except ImportError:
            # Fallback for older Python versions
            try:
                import pkg_resources

                pkg_resources.get_distribution(package_name)
                return True
            except pkg_resources.DistributionNotFound:
                return False

    def _is_retryable_error(self, error: Optional[str]) -> bool:
        """
        Determine if an error is worth retrying.

        Args:
            error: Error message

        Returns:
            True if error is retryable
        """
        if not error:
            return False

        # Retryable error patterns
        retryable_patterns = [
            "connection",
            "timeout",
            "temporary failure",
            "network",
            "unreachable",
            "could not find",
            "no matching distribution",
            "httperror",
            "http error",
            "ssl",
            "certificate",
            "readtimeout",
            "connectionerror",
        ]

        error_lower = error.lower()
        return any(pattern in error_lower for pattern in retryable_patterns)

    def _extract_error_message(self, stderr: str) -> str:
        """
        Extract meaningful error message from pip stderr.

        Args:
            stderr: Standard error output from pip

        Returns:
            Extracted error message
        """
        if not stderr:
            return "Unknown error"

        # Look for ERROR: lines
        error_lines = []
        for line in stderr.splitlines():
            if "ERROR:" in line:
                error_lines.append(line.split("ERROR:", 1)[1].strip())

        if error_lines:
            return " | ".join(error_lines)

        # Fall back to last non-empty line
        lines = [l.strip() for l in stderr.splitlines() if l.strip()]
        if lines:
            return lines[-1]

        return "Installation failed"

    def _get_consolidated_error(self, package_spec: str) -> str:
        """
        Get a consolidated error message from all attempts.

        Args:
            package_spec: Package specification that failed

        Returns:
            Consolidated error message
        """
        # Get unique error messages from attempts
        errors = set()
        for attempt in self.attempts:
            if attempt.package == package_spec and attempt.error:
                errors.add(attempt.error)

        if not errors:
            return (
                f"Failed to install {package_spec} after {len(self.attempts)} attempts"
            )

        # Format error message
        if len(errors) == 1:
            return next(iter(errors))
        return f"Multiple errors: {' | '.join(errors)}"

    def install_packages(
        self, packages: List[str], parallel: bool = False
    ) -> Tuple[List[str], List[str], Dict[str, str]]:
        """
        Install multiple packages with robust error handling.

        Args:
            packages: List of package specifications
            parallel: Whether to attempt parallel installation

        Returns:
            Tuple of (successful_packages, failed_packages, error_map)
        """
        successful = []
        failed = []
        errors = {}

        # Group packages that can be installed together
        if parallel and len(packages) > 1:
            # Try to install all at once first
            logger.info(f"Attempting batch installation of {len(packages)} packages...")
            success, error = self._attempt_batch_install(packages)

            if success:
                logger.info("Batch installation successful")
                return packages, [], {}
            logger.warning(f"Batch installation failed: {error}")
            logger.info("Falling back to individual installation...")

        # Install packages individually
        for i, package in enumerate(packages, 1):
            logger.info(f"Installing package {i}/{len(packages)}: {package}")

            success, error = self.install_package(package)

            if success:
                successful.append(package)
            else:
                failed.append(package)
                errors[package] = error or "Unknown error"

        return successful, failed, errors

    def _attempt_batch_install(self, packages: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Attempt to install multiple packages in a single pip command.

        Args:
            packages: List of package specifications

        Returns:
            Tuple of (success, error_message)
        """
        try:
            cmd = [sys.executable, "-m", "pip", "install"]

            # Add PEP 668 bypass flags if needed
            if self.is_pep668_managed:
                self._show_pep668_warning()
                cmd.extend(["--break-system-packages", "--user"])
                logger.debug("Added PEP 668 flags for batch installation")

            cmd.extend(packages)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout * 2,
                check=False,  # Longer timeout for batch
            )

            if result.returncode == 0:
                # Verify all packages
                all_verified = all(self._verify_installation(pkg) for pkg in packages)
                if all_verified:
                    return True, None
                return False, "Some packages failed verification"
            error_msg = self._extract_error_message(result.stderr)
            return False, error_msg

        except subprocess.TimeoutExpired:
            return False, "Batch installation timed out"
        except Exception as e:
            return False, f"Batch installation error: {e!s}"

    def get_report(self) -> str:
        """
        Generate a report of installation attempts.

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("INSTALLATION REPORT")
        lines.append("=" * 60)

        # Add PEP 668 status
        if self.is_pep668_managed:
            lines.append("")
            lines.append("⚠️  PEP 668 Managed Environment: YES")
            lines.append("   Installations used --break-system-packages --user flags")
            lines.append("   Consider using a virtual environment for better isolation")

        # Summary
        total_attempts = len(self.attempts)
        successful = sum(1 for a in self.attempts if a.success)
        failed = total_attempts - successful

        lines.append(f"Total attempts: {total_attempts}")
        lines.append(f"Successful: {successful}")
        lines.append(f"Failed: {failed}")
        lines.append("")

        # Details by package
        packages = {}
        for attempt in self.attempts:
            if attempt.package not in packages:
                packages[attempt.package] = []
            packages[attempt.package].append(attempt)

        for package, attempts in packages.items():
            success = any(a.success for a in attempts)
            status = "✓" if success else "✗"
            lines.append(f"{status} {package}:")

            for attempt in attempts:
                retry_str = (
                    f" (retry {attempt.retry_count})" if attempt.retry_count > 0 else ""
                )
                result = "success" if attempt.success else f"failed: {attempt.error}"
                lines.append(f"  - {attempt.strategy.value}{retry_str}: {result}")

        lines.append("=" * 60)
        return "\n".join(lines)


def install_with_retry(
    packages: List[str], max_retries: int = 3, verbose: bool = False
) -> Tuple[bool, str]:
    """
    Convenience function to install packages with retry logic.

    Args:
        packages: List of package specifications
        max_retries: Maximum retry attempts
        verbose: Whether to print verbose output

    Returns:
        Tuple of (all_success, error_message)
    """
    if verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    installer = RobustPackageInstaller(max_retries=max_retries)
    successful, failed, errors = installer.install_packages(packages)

    if verbose:
        print(installer.get_report())

    if failed:
        error_msg = f"Failed to install {len(failed)} packages: "
        error_msg += ", ".join(f"{pkg} ({errors[pkg]})" for pkg in failed)
        return False, error_msg

    return True, ""
