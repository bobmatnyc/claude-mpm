from pathlib import Path

"""Framework source directory detection utilities.

WHY: This module provides utilities to detect if we're in the framework source directory
to prevent accidental overwrites of the template files during deployment.
"""

from typing import List, Tuple


def is_framework_source_directory(path: Path) -> Tuple[bool, List[str]]:
    """
    Check if the given path is the framework source directory.

    WHY: We need to prevent deployment to the framework source directory itself
    to avoid overwriting template files.

    Args:
        path: Path to check

    Returns:
        Tuple of (is_framework_source, list of detected markers)
    """
    markers = []

    # Check for framework source markers
    if (path / "src" / "claude_mpm").exists():
        markers.append("src/claude_mpm")

    if (path / "pyproject.toml").exists():
        markers.append("pyproject.toml")

    if (path / "src" / "claude_mpm" / "agents" / "INSTRUCTIONS.md").exists():
        markers.append("framework INSTRUCTIONS.md template")

    # If we have multiple markers, it's likely the framework source
    is_framework = len(markers) >= 2

    return is_framework, markers
