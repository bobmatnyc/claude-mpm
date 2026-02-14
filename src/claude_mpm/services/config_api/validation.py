"""Input validation utilities for config API handlers.

Provides shared validation functions to prevent path traversal and
other injection attacks in agent/skill deployment endpoints.
"""

import re
from pathlib import Path
from typing import Tuple

# Names must start with an alphanumeric character and contain only
# alphanumeric characters, hyphens, and underscores.
SAFE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def validate_safe_name(name: str, entity_type: str) -> Tuple[bool, str]:
    """Validate that *name* is safe for use in filesystem paths.

    Two-layer defence:
    1. Regex format check -- rejects ``/``, ``\\``, ``..``, and any
       character outside ``[a-zA-Z0-9_-]``.
    2. The caller should additionally perform a resolved-path containment
       check after constructing the full path (see
       ``validate_path_containment``).

    Args:
        name: The agent or skill name to validate.
        entity_type: Human-readable entity label used in the error
            message (e.g. ``"agent"`` or ``"skill"``).

    Returns:
        A ``(is_valid, error_message)`` tuple.  When valid the error
        message is an empty string.
    """
    if not name:
        return False, f"{entity_type} name must not be empty"

    if not SAFE_NAME_PATTERN.match(name):
        return (
            False,
            f"Invalid {entity_type} name: must contain only "
            "alphanumeric characters, hyphens, and underscores",
        )

    return True, ""


def validate_path_containment(
    constructed_path: Path, parent_dir: Path, entity_type: str
) -> Tuple[bool, str]:
    """Verify that *constructed_path* resolves within *parent_dir*.

    This catches symlink tricks and edge cases that the regex alone
    cannot prevent.

    Args:
        constructed_path: The full filesystem path built from user input.
        parent_dir: The directory the path must remain inside.
        entity_type: Human-readable label for error messages.

    Returns:
        A ``(is_valid, error_message)`` tuple.
    """
    try:
        resolved = constructed_path.resolve()
        parent_resolved = parent_dir.resolve()
        if (
            not str(resolved).startswith(str(parent_resolved) + "/")
            and resolved != parent_resolved
        ):
            return (
                False,
                f"Invalid {entity_type} name",
            )
    except (OSError, ValueError):
        return False, f"Invalid {entity_type} name"

    return True, ""
