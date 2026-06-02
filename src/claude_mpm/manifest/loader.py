"""
Manifest configuration subsystem — detection-gated loader.

WHAT: Provides ``find_manifest(start_dir) -> Path | None`` to locate the
manifest file by walking up the directory hierarchy, and
``load_manifest(start_dir, preset_resolver=None) -> ManifestResult | None`` as
the primary entry point.  Returns ``None`` immediately when no manifest file is
found (the "dormant unless detected" contract).  When the file is present,
parses JSON, validates against the schema, and optionally merges a preset via an
injectable resolver callable.

WHY: Returning ``None`` (not an empty default) when no manifest file exists
keeps the system completely transparent to projects that have not opted in — no
warnings, no defaults, no changed behaviour.  The injectable ``preset_resolver``
parameter creates a clean seam so PR2 (preset resolution) can plug in without
rewriting this module.  Walking upward from ``start_dir`` mirrors ``git`` and
``tsconfig.json`` discovery conventions.

References
----------
SPEC-MANIFEST-01~1 : docs/specs/manifest.md#SPEC-MANIFEST-01~1
SPEC-MANIFEST-02~1 : docs/specs/manifest.md#SPEC-MANIFEST-02~1
SPEC-MANIFEST-03~1 : docs/specs/manifest.md#SPEC-MANIFEST-03~1
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from claude_mpm.manifest.merger import deep_merge
from claude_mpm.manifest.schema import ManifestValidationError, validate_manifest

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Public exceptions
# ---------------------------------------------------------------------------


class ManifestLoadError(OSError):
    """Raised when a manifest file exists but cannot be read or parsed.

    WHAT: Wraps lower-level ``json.JSONDecodeError`` or ``OSError`` exceptions
    and provides a human-readable ``message`` attribute pointing to the file
    and the problem.

    WHY: A distinct exception type allows callers (CLI, setup) to distinguish
    "file not found" (returns ``None``) from "file found but broken" (raises
    ``ManifestLoadError``), without catching broad ``Exception`` or ``OSError``.

    :spec: SPEC-MANIFEST-01~1
    """

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"Failed to load manifest at '{path}': {message}")


# Re-export so callers can import everything from the loader.
__all__ = [
    "ManifestLoadError",
    "ManifestResult",
    "ManifestValidationError",
    "find_manifest",
    "load_manifest",
]

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManifestResult:
    """Immutable result object returned by ``load_manifest`` on success.

    WHAT: Carries the raw repo manifest dict, the effective (merged) config dict
    (equal to ``repo`` when no preset was resolved), the absolute path to the
    manifest file, and a flag indicating whether a preset was merged.

    WHY: A dataclass (not a plain dict) lets callers pattern-match on the result
    type, use type checkers, and access fields by name without magic string keys.
    ``frozen=True`` prevents accidental mutation by callers.

    :spec: SPEC-MANIFEST-01~1
    """

    #: The raw repo-level manifest as parsed from disk.
    repo: dict
    #: The merged effective config.  Equals ``repo`` when no preset was applied.
    effective: dict
    #: Absolute path to the manifest file that was loaded.
    path: Path
    #: True when a preset was resolved and merged into ``effective``.
    preset_merged: bool = field(default=False)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

#: Relative path from a repo root to the manifest file.
_MANIFEST_RELATIVE = Path(".claude-mpm") / "manifest.json"


def find_manifest(start_dir: Path | str) -> Path | None:
    """Locate the manifest file by walking up from *start_dir*.

    WHAT: Searches *start_dir* and each ancestor directory for
    ``.claude-mpm/manifest.json``.  Returns the absolute ``Path`` to the first
    match, or ``None`` if no manifest is found anywhere in the hierarchy.

    WHY: Walking upward mirrors ``git`` and ``tsconfig.json`` conventions so
    that ``load_manifest`` can be called from any sub-directory of a project.

    Test: Create a temp dir with ``.claude-mpm/manifest.json``, call
    ``find_manifest`` from a sub-directory; assert the returned path points to
    the manifest file.  Call from a directory with no manifest; assert ``None``.

    :spec: SPEC-MANIFEST-01~1

    Parameters
    ----------
    start_dir:
        The directory from which to start searching.

    Returns
    -------
    Path | None
        Absolute path to the manifest, or ``None`` if not found.
    """
    current = Path(start_dir).resolve()
    while True:
        candidate = current / _MANIFEST_RELATIVE
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            # Reached the filesystem root without finding a manifest.
            return None
        current = parent


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_manifest(
    start_dir: Path | str,
    preset_resolver: Callable[[str], dict] | None = None,
) -> ManifestResult | None:
    """Load, validate, and optionally merge the manifest for the given project.

    WHAT: Returns ``None`` when no ``.claude-mpm/manifest.json`` is found
    (the dormant-unless-present contract).  When the file is found: parses JSON,
    validates against the schema, and returns a ``ManifestResult``.  If
    ``extends`` is present AND ``preset_resolver`` is provided, calls the
    resolver and deep-merges the preset under the repo manifest.

    WHY: Single entry point for all manifest-aware code so every caller benefits
    from the same validation and merge semantics.  The injectable
    ``preset_resolver`` keeps PR1 self-contained while leaving a clean seam for
    PR2 to plug in real preset resolution without changing this function's
    signature or callers.

    Test: In a temp dir without a manifest, assert ``None`` is returned.
    In a temp dir with a valid ``{"version": "1.0"}`` manifest, assert a
    ``ManifestResult`` is returned with ``repo["version"] == "1.0"``.
    With a malformed JSON file, assert ``ManifestLoadError`` is raised.
    With ``extends`` set and a resolver provided, assert the resolver is called
    and the result contains merged keys from both preset and repo.

    :spec: SPEC-MANIFEST-01~1

    Parameters
    ----------
    start_dir:
        Directory from which to begin searching for the manifest.
    preset_resolver:
        Optional callable ``(extends_name: str) -> dict`` that returns the
        preset manifest dict.  When ``None`` and ``extends`` is set in the
        manifest, the repo manifest is returned unmerged with no error raised
        (PR2 will supply the real resolver).

    Returns
    -------
    ManifestResult | None
        ``None`` when no manifest file is found.
        ``ManifestResult`` when a valid manifest is loaded.

    Raises
    ------
    ManifestLoadError
        When the manifest file exists but contains invalid JSON or cannot be read.
    ManifestValidationError
        When the manifest file contains valid JSON but fails schema validation.
    """
    # -- DORMANT CHECK (must be first) ---------------------------------------
    manifest_path = find_manifest(start_dir)
    if manifest_path is None:
        # No manifest present → system remains completely dormant.
        return None

    # -- PARSE ----------------------------------------------------------------
    try:
        raw_text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestLoadError(
            manifest_path,
            f"Could not read file: {exc}",
        ) from exc

    try:
        repo_manifest: dict = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ManifestLoadError(
            manifest_path,
            f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
        ) from exc

    if not isinstance(repo_manifest, dict):
        raise ManifestLoadError(
            manifest_path,
            f"Manifest root must be a JSON object, not {type(repo_manifest).__name__}.",
        )

    # -- VALIDATE -------------------------------------------------------------
    validate_manifest(repo_manifest)

    # -- PRESET RESOLUTION (injectable seam) ----------------------------------
    extends: str | None = repo_manifest.get("extends")

    if extends is not None and preset_resolver is not None:
        # PR2 plugs in here: resolve and merge the preset.
        preset_dict = preset_resolver(extends)
        effective = deep_merge(preset_dict, repo_manifest)
        return ManifestResult(
            repo=repo_manifest,
            effective=effective,
            path=manifest_path,
            preset_merged=True,
        )

    # No resolver (or no extends) → return the raw repo manifest unmerged.
    # Callers that need preset resolution should provide a preset_resolver.
    return ManifestResult(
        repo=repo_manifest,
        effective=repo_manifest,
        path=manifest_path,
        preset_merged=False,
    )
