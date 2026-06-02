"""
Manifest configuration subsystem — preset resolver.

WHAT: Provides ``resolve_preset(extends: str) -> dict`` that resolves a preset
name or path from a repo manifest's ``extends`` field by trying four sources in
priority order (FIRST MATCH WINS):

1. **Local path** — if *extends* starts with ``./`` or ``/``, load that JSON
   file.  Relative paths (``./``) are resolved against the current working
   directory.
2. **User preset directory** — ``~/.claude-mpm/presets/<name>.json``.
3. **Package entry point** — ``importlib.metadata.entry_points(group=
   "claude_mpm.presets")`` with key equal to *name*.  The entry point must be
   callable and return ``dict``.
4. **Built-in presets** — JSON files bundled inside this package
   (``default``, ``minimal``, ``enterprise``), loaded via
   ``claude_mpm.manifest.presets.load_builtin_preset``.

Each resolved dict is schema-validated before being returned.  If no source
matches, a ``PresetResolutionError`` is raised listing all sources tried.

WHY: Separating resolution from loading keeps the loader module simple and
testable.  The injectable seam in ``loader.py`` (``preset_resolver`` parameter)
allows tests to stub the resolver without touching the loader.  The four-step
order mirrors common tooling conventions (local > user > installed > built-in)
so that more specific overrides always win over more general ones.

References
----------
SPEC-MANIFEST-04~1 : docs/specs/manifest.md#SPEC-MANIFEST-04~1
SPEC-MANIFEST-03~1 : docs/specs/manifest.md#SPEC-MANIFEST-03~1
"""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

from claude_mpm.manifest.presets import load_builtin_preset
from claude_mpm.manifest.schema import validate_manifest

# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class PresetResolutionError(LookupError):
    """Raised when a preset name cannot be resolved from any source.

    WHAT: Carries a human-readable ``message`` attribute listing all resolution
    sources that were tried, so the user can diagnose the problem.

    WHY: A distinct exception type allows callers to distinguish "preset not
    found" from other ``LookupError`` / ``KeyError`` exceptions that might arise
    elsewhere in the system.

    :spec: SPEC-MANIFEST-04~1
    """

    def __init__(self, extends: str, tried: list[str]) -> None:
        self.extends = extends
        self.tried = tried
        tried_str = "\n  - ".join(tried)
        super().__init__(
            f"Could not resolve preset '{extends}'. Sources tried:\n  - {tried_str}"
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

__all__ = ["PresetResolutionError", "resolve_preset"]


def resolve_preset(extends: str) -> dict:
    """Resolve the preset identified by *extends* and return its manifest dict.

    WHAT: Tries four resolution sources in order — local path, user preset
    directory, package entry point, built-in presets — and returns the first
    match.  The resolved dict is schema-validated before being returned.

    WHY: Centralising all resolution logic here keeps the loader simple and
    every caller benefits from the same validation and error reporting.  The
    four-step order mirrors common tooling conventions (local > user > installed
    > built-in).

    Test: Pass ``"default"``; assert a dict with ``version == "1.0"`` is
    returned.  Pass an unknown name; assert ``PresetResolutionError`` is raised
    listing all sources tried.  Pass a ``./path.json`` pointing to a valid JSON
    file; assert that file is loaded.

    :spec: SPEC-MANIFEST-04~1

    Parameters
    ----------
    extends:
        The value of the ``extends`` field from the repo manifest.  May be a
        local path (starts with ``./`` or ``/``), a user-preset name, an entry-
        point key, or a built-in preset name.

    Returns
    -------
    dict
        The resolved and schema-validated preset manifest dict.

    Raises
    ------
    PresetResolutionError
        When no resolution source produces a match.
    ManifestValidationError
        When a resolved preset fails schema validation.
    """
    tried: list[str] = []

    # ------------------------------------------------------------------
    # Step 1: Local path
    # ------------------------------------------------------------------
    if extends.startswith("./") or extends.startswith("/"):
        source_label = f"local path: {extends}"
        tried.append(source_label)
        preset_path = (
            Path(extends).resolve()
            if extends.startswith("/")
            else (Path.cwd() / extends).resolve()
        )
        if preset_path.is_file():
            return _load_and_validate_json(preset_path, source_label)
        # Local path given but file not found → fail immediately with a clear
        # message rather than falling through to other sources, since the
        # user was explicit about wanting this exact file.
        raise PresetResolutionError(extends, tried)

    # ------------------------------------------------------------------
    # Step 2: User preset directory
    # ------------------------------------------------------------------
    user_preset_path = Path.home() / ".claude-mpm" / "presets" / f"{extends}.json"
    source_label = f"user preset directory: {user_preset_path}"
    tried.append(source_label)
    if user_preset_path.is_file():
        return _load_and_validate_json(user_preset_path, source_label)

    # ------------------------------------------------------------------
    # Step 3: Package entry point
    # ------------------------------------------------------------------
    source_label = f"entry point group 'claude_mpm.presets', key '{extends}'"
    tried.append(source_label)
    ep_result = _try_entry_point(extends)
    if ep_result is not None:
        _validate_preset(ep_result, source_label)
        return ep_result

    # ------------------------------------------------------------------
    # Step 4: Built-in presets
    # ------------------------------------------------------------------
    source_label = f"built-in preset: '{extends}'"
    tried.append(source_label)
    builtin = load_builtin_preset(extends)
    if builtin is not None:
        _validate_preset(builtin, source_label)
        return builtin

    # Nothing matched.
    raise PresetResolutionError(extends, tried)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_and_validate_json(path: Path, source_label: str) -> dict:
    """Read *path* as JSON, validate as a manifest, and return the dict.

    WHAT: Reads the file, parses JSON, and calls ``validate_manifest``.
    Wraps I/O or JSON parse errors in ``PresetResolutionError``.

    WHY: Centralises the read-parse-validate triple so all file-based sources
    share the same error handling path.

    :spec: SPEC-MANIFEST-04~1
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PresetResolutionError(
            str(path), [f"{source_label}: could not read file: {exc}"]
        ) from exc

    try:
        data: dict = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PresetResolutionError(
            str(path),
            [
                f"{source_label}: invalid JSON at line {exc.lineno},"
                f" column {exc.colno}: {exc.msg}"
            ],
        ) from exc

    if not isinstance(data, dict):
        raise PresetResolutionError(
            str(path),
            [f"{source_label}: preset root must be a JSON object"],
        )

    _validate_preset(data, source_label)
    return data


def _validate_preset(data: dict, source_label: str) -> None:
    """Validate *data* against the manifest schema.

    WHAT: Calls ``validate_manifest``; if it raises, wraps the error message
    with the source label for better diagnostics.

    WHY: All preset sources must produce a valid manifest dict.  Centralising
    validation here prevents callers from forgetting to validate.

    NOTE: Multi-level extends chains (a preset that itself has ``extends``) are
    OUT OF SCOPE for this implementation — optional feature O1, deferred.  If
    the resolved preset contains an ``extends`` key, it is ignored here.
    TODO(O1): When multi-level chaining is implemented, recurse into
    ``resolve_preset(data["extends"])`` here and deep-merge before returning.

    :spec: SPEC-MANIFEST-04~1
    """
    # May raise ManifestValidationError; let it propagate — the caller asked
    # for a valid preset, so an invalid shape is a hard error.
    validate_manifest(data)


def _try_entry_point(name: str) -> dict | None:
    """Attempt to resolve *name* from the ``claude_mpm.presets`` entry-point group.

    WHAT: Uses ``importlib.metadata.entry_points`` to enumerate all registered
    ``claude_mpm.presets`` entry points, finds the one whose key matches *name*,
    loads and calls it as ``get_manifest() -> dict``, and returns the result.
    Returns ``None`` if no matching entry point is found.

    WHY: Entry points are the standard Python extension mechanism for
    auto-discoverable plugins.  Third-party preset packages (e.g.
    ``claude-mpm-duetto``) register under this group so no path configuration
    is needed.

    :spec: SPEC-MANIFEST-04~1
    """
    try:
        eps = importlib.metadata.entry_points(group="claude_mpm.presets")
    except Exception:
        return None

    for ep in eps:
        if ep.name == name:
            try:
                func = ep.load()
                result = func()
                if isinstance(result, dict):
                    return result
            except Exception:
                pass

    return None
