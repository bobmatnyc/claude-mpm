"""
Manifest configuration subsystem for claude-mpm.

WHAT: Exposes the public surface of the manifest package:
``find_manifest``, ``load_manifest``, ``ManifestResult``,
``ManifestLoadError``, ``ManifestValidationError``, ``deep_merge``,
``validate_manifest``, and ``MANIFEST_SCHEMA``.

WHY: A single import point lets callers write
``from claude_mpm.manifest import load_manifest`` without knowing which
sub-module owns each symbol.  Internal module structure can change without
breaking external callers.

References
----------
SPEC-MANIFEST-01~1 : docs/specs/manifest.md#SPEC-MANIFEST-01~1
SPEC-MANIFEST-02~1 : docs/specs/manifest.md#SPEC-MANIFEST-02~1
SPEC-MANIFEST-03~1 : docs/specs/manifest.md#SPEC-MANIFEST-03~1
"""

from __future__ import annotations

from claude_mpm.manifest.loader import (
    ManifestLoadError,
    ManifestResult,
    find_manifest,
    load_manifest,
)
from claude_mpm.manifest.merger import deep_merge
from claude_mpm.manifest.schema import (
    MANIFEST_SCHEMA,
    ManifestValidationError,
    validate_manifest,
)

__all__ = [
    "MANIFEST_SCHEMA",
    "ManifestLoadError",
    "ManifestResult",
    "ManifestValidationError",
    "deep_merge",
    "find_manifest",
    "load_manifest",
    "validate_manifest",
]
