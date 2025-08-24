"""
Dependency management utilities for claude-mpm.

WHY: This module handles automatic installation of optional dependencies
like Socket.IO monitoring tools. It ensures users can run --monitor without
manual dependency setup.

DESIGN DECISION: We use subprocess to install packages in the same environment
that's running claude-mpm, respecting virtual environments and user setups.
"""

import subprocess
import sys
from typing import List, Optional, Tuple

from ..core.logger import get_logger


def check_dependency(package_name: str, import_name: Optional[str] = None) -> bool:
    """
    Check if a Python package is installed and importable.

    WHY: We need to verify if optional dependencies are available before
    attempting to use them. This prevents ImportError crashes.

    DESIGN DECISION: We use importlib.util.find_spec() which is more reliable
    than try/except import because it doesn't execute module code.

    Args:
        package_name: Name of the package (e.g., 'python-socketio')
        import_name: Name to import (e.g., 'socketio'). Defaults to package_name.

    Returns:
        bool: True if package is available, False otherwise
    """
    if import_name is None:
        import_name = package_name.replace("-", "_")

    try:
        import importlib.util

        spec = importlib.util.find_spec(import_name)
        return spec is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def install_packages(packages: List[str], logger=None) -> Tuple[bool, str]:
    """
    Install Python packages using pip in the current environment.

    WHY: Users should not need to manually install optional dependencies.
    This function handles automatic installation while respecting the current
    Python environment (including virtual environments).

    DESIGN DECISION: We use subprocess to call pip instead of importlib
    because pip installation needs to be done in the same environment
    that's running the application.

    Args:
        packages: List of package names to install
        logger: Optional logger for output

    Returns:
        Tuple[bool, str]: (success, error_message_if_failed)
    """
    if logger is None:
        logger = get_logger("dependency_manager")

    try:
        # Use the same Python executable that's running this script
        cmd = [sys.executable, "-m", "pip", "install", *packages]

        logger.info(f"Installing packages: {packages}")
        logger.debug(f"Running command: {' '.join(cmd)}")

        # Run pip install with proper error handling
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,  # 5 minute timeout for installation
        )

        if result.returncode == 0:
            logger.info(f"Successfully installed packages: {packages}")
            return True, ""
        error_msg = f"pip install failed with return code {result.returncode}"
        if result.stderr:
            error_msg += f": {result.stderr.strip()}"
        logger.error(error_msg)
        return False, error_msg

    except subprocess.TimeoutExpired:
        error_msg = "Package installation timed out after 5 minutes"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Failed to install packages: {e}"
        logger.error(error_msg)
        return False, error_msg


def ensure_socketio_dependencies(logger=None) -> Tuple[bool, str]:
    """
    Ensure Socket.IO dependencies are installed for monitoring features.

    WHY: Socket.IO dependencies (python-socketio, aiohttp, python-engineio) are now
    core dependencies and should be installed automatically with claude-mpm.
    This function verifies they are available and provides helpful error messages
    if something went wrong during installation.

    DESIGN DECISION: We still check each dependency individually to provide
    specific error messages if any are missing, which helps with troubleshooting
    installation issues.

    Args:
        logger: Optional logger for output

    Returns:
        Tuple[bool, str]: (success, error_message_if_failed)
    """
    if logger is None:
        logger = get_logger("dependency_manager")

    # Define required packages for Socket.IO monitoring
    required_packages = [
        ("python-socketio", "socketio"),
        ("aiohttp", "aiohttp"),
        ("python-engineio", "engineio"),
    ]

    missing_packages = []

    # Check which packages are missing
    for package_name, import_name in required_packages:
        if not check_dependency(package_name, import_name):
            missing_packages.append(package_name)
            logger.debug(f"Missing dependency: {package_name}")

    if not missing_packages:
        logger.debug("All Socket.IO dependencies are already installed")
        return True, ""

    # Install missing packages (should be rare since they're now core dependencies)
    logger.warning(
        f"Socket.IO dependencies are missing despite being core dependencies: {missing_packages}"
    )
    logger.info(f"Attempting to install missing dependencies: {missing_packages}")
    success, error_msg = install_packages(missing_packages, logger)

    if success:
        # Verify installation worked
        for package_name, import_name in required_packages:
            if not check_dependency(package_name, import_name):
                error_msg = (
                    f"Package {package_name} was installed but is not importable"
                )
                logger.error(error_msg)
                return False, error_msg

        logger.info("Socket.IO dependencies installed and verified successfully")
        return True, ""
    return False, error_msg


def get_pip_freeze_output() -> List[str]:
    """
    Get the output of 'pip freeze' for debugging dependency issues.

    WHY: When dependency installation fails, we need to help users
    understand what packages are installed and what might be conflicting.

    Returns:
        List[str]: List of installed packages from pip freeze
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0:
            return result.stdout.strip().split("\n")
        return [f"pip freeze failed: {result.stderr}"]

    except Exception as e:
        return [f"Failed to get pip freeze output: {e}"]


def check_virtual_environment() -> Tuple[bool, str]:
    """
    Check if we're running in a virtual environment.

    WHY: Installation behavior might differ between virtual environments
    and system Python. This helps with debugging and user guidance.

    Returns:
        Tuple[bool, str]: (is_virtual_env, environment_info)
    """
    # Check for virtual environment indicators
    in_venv = (
        (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
        or hasattr(sys, "real_prefix")
        or (hasattr(sys, "prefix") and "conda" in sys.prefix.lower())
    )

    if in_venv:
        venv_path = getattr(sys, "prefix", "unknown")
        return True, f"Virtual environment: {venv_path}"
    return False, f"System Python: {sys.prefix}"
