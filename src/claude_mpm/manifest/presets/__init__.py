"""
Manifest configuration subsystem — built-in preset accessor.

WHAT: Provides ``load_builtin_preset(name: str) -> dict | None`` that reads
the bundled JSON preset files (``default.json``, ``minimal.json``,
``enterprise.json``) via ``importlib.resources``.  Returns ``None`` when the
name does not match any bundled preset.

WHY: Using ``importlib.resources`` (not raw ``__file__`` path joins) ensures
the presets are loaded correctly when the package is installed as a zip-safe
wheel, where ``__file__`` paths may not exist as real filesystem entries.
The accessor is a separate module so the resolver can import it without
circular dependencies, and callers can load built-in presets directly
without going through the full resolution chain.

References
----------
SPEC-MANIFEST-04~1 : docs/specs/manifest.md#SPEC-MANIFEST-04~1
"""

from __future__ import annotations

import importlib.resources
import json

# ---------------------------------------------------------------------------
# Known built-in preset names (lower-case, no extension).
# ---------------------------------------------------------------------------

_BUILTIN_NAMES: frozenset[str] = frozenset({"default", "minimal", "enterprise"})

__all__ = ["BUILTIN_PRESET_NAMES", "load_builtin_preset"]

#: The set of built-in preset names shipped with this package.
BUILTIN_PRESET_NAMES: frozenset[str] = _BUILTIN_NAMES


def load_builtin_preset(name: str) -> dict | None:
    """Load and return the built-in preset *name* as a dict, or ``None``.

    WHAT: Reads ``<name>.json`` from the ``claude_mpm.manifest.presets``
    package directory using ``importlib.resources``.  Returns ``None`` if
    *name* is not in the set of known built-in presets.

    WHY: Centralises built-in preset loading in one place.  Using
    ``importlib.resources`` (not ``__file__``) guarantees correct behavior
    when the package is installed as a zip-safe wheel where the JSON files may
    not be accessible as real filesystem paths.

    Test: Call ``load_builtin_preset("default")``; assert the result is a
    ``dict`` with ``"version"`` key ``"1.0"``.  Call
    ``load_builtin_preset("unknown")``; assert ``None`` is returned.

    :spec: SPEC-MANIFEST-04~1

    Parameters
    ----------
    name:
        The built-in preset name (e.g. ``"default"``, ``"minimal"``,
        ``"enterprise"``).  Case-sensitive.

    Returns
    -------
    dict | None
        The parsed preset dict, or ``None`` if *name* is unknown.
    """
    if name not in _BUILTIN_NAMES:
        return None

    # importlib.resources.files() works with installed wheels and editable
    # installs alike.  The package anchor is this module's own package.
    package_ref = importlib.resources.files(__name__)
    preset_file = package_ref.joinpath(f"{name}.json")
    text = preset_file.read_text(encoding="utf-8")
    result: dict = json.loads(text)
    return result
