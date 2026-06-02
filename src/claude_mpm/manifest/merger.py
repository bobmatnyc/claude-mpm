"""
Manifest configuration subsystem — deep-merge implementation.

WHAT: Provides ``deep_merge(preset, repo) -> dict``, a pure function that
merges a preset manifest dict with a repo manifest dict according to the rules
defined in ``docs/design/manifest-config-system.md``: scalars and objects are
deep-merged with repo winning at the leaf level; ``setup.services`` arrays are
union-merged (preset-first, deduplicated, insertion-order-preserving); all other
arrays are replaced by the repo value when present.

WHY: Isolating merge logic in a pure, I/O-free function makes it independently
testable without any filesystem or network setup.  The caller (loader, CLI, or
future resolver) owns the I/O; this module owns only the merge semantics.
Separating ``setup.services`` from the general array-replace rule is explicit
in the design doc and must be implemented exactly here — not scattered across
callers — to guarantee consistent behaviour.

References
----------
SPEC-MANIFEST-02~1 : docs/specs/manifest.md#SPEC-MANIFEST-02~1
"""

from __future__ import annotations

import copy

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def deep_merge(preset: dict, repo: dict) -> dict:
    """Merge *preset* and *repo* manifest dicts into an effective config dict.

    WHAT: Returns a new dict produced by recursively merging *repo* on top of
    *preset* using the rules below.  Neither input is mutated.

    Rules:
    - Scalars: *repo* wins; absent keys fall back to *preset*.
    - Objects (dicts): recursive deep merge; *repo* wins at each leaf.
    - ``setup.services`` array: union of both arrays, deduplicated,
      preserving insertion order (preset entries first, then repo-only extras).
    - All other arrays: *repo* replaces *preset* entirely when *repo* specifies
      the key; *preset* value used when *repo* omits the key.

    WHY: Centralises all merge semantics in one callable so every code path
    (loader, CLI, future migration) produces identical results.

    Test: Call with ``preset={"agents": {"eng": {"model": "haiku", "color":
    "green"}}, "setup": {"services": ["svc-a"]}}`` and
    ``repo={"agents": {"eng": {"model": "sonnet"}}, "setup":
    {"services": ["svc-b"]}}``; assert ``result["agents"]["eng"]`` equals
    ``{"model": "sonnet", "color": "green"}`` and
    ``result["setup"]["services"]`` equals ``["svc-a", "svc-b"]``.

    :spec: SPEC-MANIFEST-02~1

    Parameters
    ----------
    preset:
        The resolved preset manifest dict.  May be empty.
    repo:
        The repo-level manifest dict.  May be empty.

    Returns
    -------
    dict
        The merged effective configuration.

    Raises
    ------
    TypeError
        If either argument is not a ``dict``.
    """
    if not isinstance(preset, dict):
        raise TypeError(f"preset must be a dict, got {type(preset).__name__}")
    if not isinstance(repo, dict):
        raise TypeError(f"repo must be a dict, got {type(repo).__name__}")

    # Start with a deep copy of the preset so we never mutate the input.
    result = copy.deepcopy(preset)
    _merge_into(result, repo, path=())
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _merge_into(target: dict, source: dict, path: tuple[str, ...]) -> None:
    """Recursively merge *source* into *target* in-place.

    WHAT: Iterates over every key in *source* and merges it into *target*
    in-place using the three-way dispatch: (1) dicts on both sides recurse;
    (2) arrays on both sides trigger the ``setup.services`` union check or the
    default array-replace rule; (3) all other cases copy the source value into
    target (repo wins).

    WHY: Separating the workhorse from ``deep_merge``'s entry-point allows
    ``deep_merge`` to own the initial deep-copy and type-checking while this
    function focuses purely on the recursive merge logic.  The *path* tuple
    is the minimum bookkeeping needed to identify the ``setup.services``
    special case without coupling the merge rules to the manifest schema.

    :spec: SPEC-MANIFEST-02~1
    """
    for key, source_value in source.items():
        if key not in target:
            # Key exists only in repo → copy it wholesale.
            target[key] = copy.deepcopy(source_value)
            continue

        target_value = target[key]

        # Both sides have this key — apply merge rules.
        if isinstance(target_value, dict) and isinstance(source_value, dict):
            # Both are objects → recurse.
            _merge_into(target_value, source_value, path + (key,))
        elif isinstance(target_value, list) and isinstance(source_value, list):
            # Both are arrays → check for the setup.services special case.
            if path == ("setup",) and key == "services":
                # Union merge: preset-first, then repo-only extras, deduplicated.
                target[key] = _union_merge(target_value, source_value)
            elif path == () and key == "setup":
                # Should not reach here (setup is a dict, not a list), but be safe.
                target[key] = copy.deepcopy(source_value)
            else:
                # All other arrays: repo replaces preset.
                target[key] = copy.deepcopy(source_value)
        else:
            # Scalar or type mismatch → repo wins.
            target[key] = copy.deepcopy(source_value)


def _union_merge(preset_list: list, repo_list: list) -> list:
    """Return the ordered union of *preset_list* and *repo_list*.

    WHAT: Produces a new list containing all elements of *preset_list* first,
    followed by elements of *repo_list* that were not already present in
    *preset_list*.  Preserves insertion order; deduplicates by value.

    WHY: The ``setup.services`` union rule exists so that repo authors can add
    project-specific services without losing the preset's baseline services.
    Preset-first ordering ensures the preset's services are installed before
    any repo-specific additions.

    Test: Call with ``["a", "b"]`` and ``["b", "c"]``; assert result is
    ``["a", "b", "c"]``.

    Parameters
    ----------
    preset_list:
        Entries from the preset (appear first in the result).
    repo_list:
        Entries from the repo (only novel entries appended).

    Returns
    -------
    list
        Deduplicated union with preset entries first.
    """
    seen: set = set()
    result: list = []
    for item in preset_list:
        if item not in seen:
            seen.add(item)
            result.append(item)
    for item in repo_list:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
