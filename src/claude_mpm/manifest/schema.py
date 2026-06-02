"""
Manifest configuration subsystem — JSON schema and validation.

WHAT: Provides the canonical JSON Schema (draft-07) dict for manifest v1.0 and
a ``validate_manifest`` function that raises a clear, actionable
``ManifestValidationError`` when a manifest dict violates the schema.  Pure
module; performs no I/O.

WHY: Centralising the schema in one importable Python dict gives the loader,
the CLI, and test fixtures a single source of truth.  Using ``jsonschema``
(already a transitive dependency) avoids adding new installation cost.
Allowing additional top-level properties keeps the format forward-compatible:
older versions of claude-mpm can load manifests written for newer versions
without validation failures, provided the known fields are valid.

References
----------
SPEC-MANIFEST-03~1 : docs/specs/manifest.md#SPEC-MANIFEST-03~1
"""

from __future__ import annotations

import jsonschema  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class ManifestValidationError(ValueError):
    """Raised when a manifest dict fails JSON-schema validation.

    WHAT: Wraps a ``jsonschema.ValidationError`` and exposes ``path`` (the
    dot-separated JSON pointer to the offending key) and ``message`` (a
    human-readable description of the constraint that was violated).

    WHY: A distinct exception type lets callers catch manifest validation
    failures precisely, without accidentally swallowing unrelated ``ValueError``
    exceptions from other parts of the system.

    :spec: SPEC-MANIFEST-03~1
    """

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"Manifest validation error at '{path}': {message}")


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

#: JSON Schema draft-07 for manifest v1.0.
#:
#: Top-level keys:
#:   version  (required, enum ["1.0"])
#:   extends  (optional string, min length 1)
#:   agents   (optional object whose values are objects)
#:   hooks    (optional object whose values are arrays of strings)
#:   settings (optional free-form object)
#:   setup    (optional object with optional "services" string-array)
#:
#: Additional top-level properties are allowed so that future keys do not
#: break validation on older claude-mpm installations.
MANIFEST_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "claude-mpm manifest",
    "description": "Repo-level manifest configuration for claude-mpm.",
    "type": "object",
    "required": ["version"],
    "additionalProperties": True,
    "properties": {
        "version": {
            "type": "string",
            "enum": ["1.0"],
            "description": "Schema version. Currently only '1.0' is valid.",
        },
        "extends": {
            "type": "string",
            "minLength": 1,
            "description": (
                "Name or path of the preset to extend. "
                "See docs/design/manifest-config-system.md for resolution order."
            ),
        },
        "agents": {
            "type": "object",
            "description": (
                "Agent overrides keyed by agent name. "
                "Values are partial agent-config objects deep-merged onto the preset."
            ),
            "additionalProperties": {
                "type": "object",
                "additionalProperties": True,
            },
        },
        "hooks": {
            "type": "object",
            "description": (
                "Hook event definitions. Keys are event names "
                "(e.g. 'PreToolUse'), values are arrays of command strings."
            ),
            "additionalProperties": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "settings": {
            "type": "object",
            "description": "Arbitrary settings deep-merged into the resolved configuration.",
            "additionalProperties": True,
        },
        "setup": {
            "type": "object",
            "description": "Automated setup directives run by 'claude-mpm setup'.",
            "additionalProperties": True,
            "properties": {
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "MCP service names to install. "
                        "Union-merged with preset services."
                    ),
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------


def validate_manifest(data: dict) -> None:
    """Validate *data* against the manifest JSON schema.

    WHAT: Accepts a parsed manifest dict and raises ``ManifestValidationError``
    if it violates the schema.  Returns ``None`` on success.

    WHY: Providing a single validation entry point means every caller (loader,
    CLI, tests) uses the same schema and the same error type, preventing
    inconsistent validation behaviour across the codebase.

    Test: Pass a minimal ``{"version": "1.0"}``; assert no exception is raised.
    Pass ``{}``; assert ``ManifestValidationError`` is raised with ``path``
    containing ``"version"``.

    :spec: SPEC-MANIFEST-03~1

    Parameters
    ----------
    data:
        A parsed manifest dict to validate.

    Raises
    ------
    ManifestValidationError
        When *data* fails schema validation.  The exception carries ``path``
        (dot-separated JSON path to the offending key) and ``message``
        (human-readable description of the violated constraint).
    """
    try:
        jsonschema.validate(data, MANIFEST_SCHEMA)
    except jsonschema.ValidationError as exc:
        # Build a dot-separated path string from the deque of path components.
        path_parts = list(exc.absolute_path)
        path_str = ".".join(str(p) for p in path_parts) if path_parts else "<root>"
        raise ManifestValidationError(path=path_str, message=exc.message) from exc
