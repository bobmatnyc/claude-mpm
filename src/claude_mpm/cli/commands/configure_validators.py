"""Validation utilities for configure command.

WHY: Centralizes argument validation and input parsing logic.
Separates validation concerns from business logic.

DESIGN: Pure validation functions without side effects.
"""

from argparse import Namespace
from typing import List, Optional


def validate_args(args: Namespace) -> Optional[str]:
    """Validate command arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        Error message if validation fails, None otherwise
    """
    # Check for conflicting direct navigation options
    nav_options = [
        getattr(args, "agents", False),
        getattr(args, "templates", False),
        getattr(args, "behaviors", False),
        getattr(args, "startup", False),
        getattr(args, "version_info", False),
    ]
    if sum(nav_options) > 1:
        return "Only one direct navigation option can be specified at a time"

    # Check for conflicting non-interactive options
    if getattr(args, "enable_agent", None) and getattr(args, "disable_agent", None):
        return "Cannot enable and disable agents at the same time"

    return None


def parse_id_selection(selection: str, max_id: int) -> List[int]:
    """Parse ID selection string (e.g., '1,3,5' or '1-4').

    Args:
        selection: User selection string
        max_id: Maximum valid ID

    Returns:
        List of selected IDs (sorted)

    Raises:
        ValueError: If selection is invalid
    """
    ids = set()
    parts = selection.split(",")

    for part in parts:
        part = part.strip()
        if "-" in part:
            # Range selection
            start, end = part.split("-")
            start_id = int(start.strip())
            end_id = int(end.strip())
            if start_id < 1 or end_id > max_id or start_id > end_id:
                raise ValueError(f"Invalid range: {part}")
            ids.update(range(start_id, end_id + 1))
        else:
            # Single ID
            id_num = int(part)
            if id_num < 1 or id_num > max_id:
                raise ValueError(f"Invalid ID: {id_num}")
            ids.add(id_num)

    return sorted(ids)
