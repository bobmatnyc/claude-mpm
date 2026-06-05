"""
trusty-search opt-in index allowlist manager.

WHAT: Read, write, and query the trusty-search ``indexes.toml`` registry so
      MPM can add/list/remove project roots on explicit user request only.
WHY:  trusty-search is moving to an opt-in indexing model (trusty-tools#767).
      A directory is indexed only if explicitly present in the allowlist.
      MPM is the component that writes that config — but ONLY when the user
      asks; no auto-indexing of cwd/worktrees/transient directories.

Schema (confirmed from PersistedIndex in
  trusty-tools/crates/trusty-search/src/service/persistence.rs
and the live ~/Library/Application Support/trusty-search/indexes.toml)::

    [[index]]
    id = "my-project"          # derived from root_path basename (or user-supplied)
    root_path = "/abs/path"    # absolute, resolved path to the project root
    colocated = true           # store index data inside <root_path>/.trusty-search/
    # All remaining fields are optional:
    # include_docs = true      # default true — omitted when true to keep TOML compact
    # respect_gitignore = true # default true — omitted when true
    # lexical_only = false     # default false — omitted when false
    # skip_kg = false          # default false — omitted when false
    # include_paths = []       # subtree restrictions
    # exclude_globs = []       # glob exclusions
    # extensions = []          # extension allow-list
    # domain_terms = []        # intent-classifier vocabulary
    # path_filter = []         # subdirectory glob filter

Location note: on macOS the live path is
  ~/Library/Application Support/trusty-search/indexes.toml
(``dirs::data_local_dir()`` in Rust maps to Application Support on macOS).
The TRUSTY_DATA_DIR env var overrides this; once trusty-tools#767 ships the
location may move to ``~/.config/trusty-search/indexes.toml`` — callers use
:func:`default_allowlist_path` so the change only needs to land here.

References
----------
LINK: none  (feature introduced in this PR, spec lives in GitHub issue #668)
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Sensitive path denylist
# ---------------------------------------------------------------------------

# Literal paths whose parents (or themselves) must never be indexed.
_DENYLIST_PARENTS: frozenset[str] = frozenset(
    [
        str(Path.home() / ".ssh"),
        str(Path.home() / ".aws"),
        str(Path.home() / ".gnupg"),
        str(Path.home() / ".config" / "gcloud"),
        str(Path.home() / ".kube"),
        str(Path.home() / ".docker"),
    ]
)

# Top-level paths that are themselves forbidden (and whose sub-paths inherit).
_DENYLIST_ROOTS: frozenset[str] = frozenset(
    [
        str(Path.home()),  # $HOME itself
        "/tmp",  # nosec B108 — we're BLOCKING /tmp from indexing, not using it
        "/",
        "/etc",
        "/var",
    ]
)


class DeniedPathError(Exception):
    """Raised when a path is in the denylist."""


class AllowlistWriteError(OSError):
    """Raised when the allowlist file cannot be written."""


def default_allowlist_path() -> Path:
    """Return the platform-appropriate path to the trusty-search indexes.toml.

    WHAT: Resolves ``TRUSTY_DATA_DIR`` env var first, then falls back to the
    OS-appropriate data directory (``~/Library/Application Support/trusty-search``
    on macOS, ``~/.local/share/trusty-search`` on Linux).
    WHY:  Mirrors the Rust ``data_dir()`` function in
    ``trusty-search/src/service/persistence.rs`` so MPM writes to the exact
    same file the daemon reads.  Using ``platformdirs`` (or its equivalent via
    stdlib ``pathlib``) avoids hard-coding the macOS path.

    Note: once trusty-tools#767 ships the location may change to
    ``~/.config/trusty-search/indexes.toml``.  Update this function then.
    """
    override = os.environ.get("TRUSTY_DATA_DIR", "")
    if override:
        return Path(override) / "indexes.toml"

    # Mirrors dirs::data_local_dir() in Rust:
    #   macOS  → ~/Library/Application Support
    #   Linux  → ~/.local/share
    #   Windows→ %APPDATA%/Local
    import platform

    system = platform.system()
    if system == "Darwin":
        data_dir = Path.home() / "Library" / "Application Support" / "trusty-search"
    elif system == "Windows":
        appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or ""
        data_dir = (
            Path(appdata) / "trusty-search"
            if appdata
            else Path.home() / "trusty-search"
        )
    else:
        # Linux / other POSIX
        xdg_data = os.environ.get("XDG_DATA_HOME", "")
        base = Path(xdg_data) if xdg_data else Path.home() / ".local" / "share"
        data_dir = base / "trusty-search"

    return data_dir / "indexes.toml"


def _resolve_path(raw: str | Path) -> Path:
    """Expand user home, resolve symlinks, and return an absolute path.

    WHAT: Applies expanduser + resolve to normalize any user-supplied path to
    its canonical absolute form so the daemon's root_path comparisons work.
    WHY:  The daemon stores and compares resolved paths; a relative or symlink
    path would create a duplicate that never matches.
    """
    p = Path(raw).expanduser()
    try:
        resolved = p.resolve()
    except (OSError, RuntimeError):
        resolved = p.absolute()
    return resolved


def _derive_id(path: Path) -> str:
    """Derive a safe index ID from the directory name.

    WHAT: Returns the basename of the path, sanitized to ``[A-Za-z0-9._-]``
    only (matching trusty-search's ``sanitize_id``).
    WHY:  The daemon uses the id as both a lookup key and a filesystem path
    component; unsafe characters would break either.
    """
    raw = path.name or path.parts[-1] if path.parts else "project"
    return re.sub(r"[^A-Za-z0-9._-]", "_", raw) or "project"


def _check_denylist(resolved: Path) -> None:
    """Raise DeniedPathError if *resolved* is a forbidden path.

    WHAT: Checks the resolved path against:
      1. Exact denylist roots ($HOME, /tmp, /, /etc, /var).
      2. Parent-tree denylist (~/.ssh, ~/.aws, etc.).
      3. Any directory containing a .env file at its top level.
    WHY:  Prevents accidental indexing of credential stores, temp dirs, and
    directories that expose secrets via .env files to the search index.
    """
    resolved_str = str(resolved)

    # 1. Exact denylist roots
    if resolved_str in _DENYLIST_ROOTS:
        raise DeniedPathError(
            f"Refusing to index '{resolved_str}': this path is in the "
            "sensitive-path denylist (home directory, /tmp, or a system root). "
            "Choose a specific project subdirectory instead."
        )

    # Also refuse anything whose resolved string IS a denylist root's string
    # (handles trailing-slash variants)
    for root in _DENYLIST_ROOTS:
        if resolved_str.rstrip("/") == root.rstrip("/"):
            raise DeniedPathError(
                f"Refusing to index '{resolved_str}': matches the denylist root "
                f"'{root}'. Choose a specific project subdirectory instead."
            )

    # 2. Parent-tree denylist
    for denied_parent in _DENYLIST_PARENTS:
        try:
            resolved.relative_to(denied_parent)
            # If we get here the path is inside denied_parent
            raise DeniedPathError(
                f"Refusing to index '{resolved_str}': the path is inside the "
                f"sensitive directory '{denied_parent}'. "
                "This directory likely contains credentials or secret keys."
            )
        except ValueError:
            pass  # not relative — OK

    # 3. .env file guard
    env_file = resolved / ".env"
    try:
        if env_file.exists():
            raise DeniedPathError(
                f"Refusing to index '{resolved_str}': a '.env' file was found "
                "at the top level of this directory. Indexing it would expose "
                "secrets to trusty-search. Remove or gitignore the .env file "
                "and retry, or use --exclude '.env' via trusty-search directly."
            )
    except (OSError, PermissionError):
        pass  # cannot stat — do not block on permission errors


# ---------------------------------------------------------------------------
# TOML read/write helpers (using stdlib ``tomllib`` + ``toml`` for write)
# ---------------------------------------------------------------------------


def _load_registry(path: Path) -> list[dict]:
    """Read indexes.toml and return the list of ``[[index]]`` entries.

    WHAT: Parses the TOML file and returns the ``index`` array as a list of
    plain dicts.  Returns an empty list when the file does not exist.
    WHY:  ``tomllib`` (Python 3.11+ stdlib) is used for reading — it is
    zero-dependency.  The ``toml`` package (project dep) handles writing.

    :raises AllowlistWriteError: if the file exists but is unreadable/corrupt.
    """
    if not path.exists():
        return []
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            import toml as tomllib  # type: ignore[no-redef, assignment]

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception as exc:
        raise AllowlistWriteError(
            f"Could not read trusty-search allowlist at {path}: {exc}"
        ) from exc
    entries = data.get("index", [])
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict)]


def _save_registry(path: Path, entries: list[dict]) -> None:
    """Write *entries* back to *path* as ``[[index]]`` array-of-tables TOML.

    WHAT: Serialises the entry list using the ``toml`` package (a project dep).
    Writes atomically via a sibling temp file + rename so the daemon never
    sees a half-written file.
    WHY:  The ``toml`` library produces spec-compliant output with proper
    ``[[index]]`` array-of-tables that the Rust serde deserialiser expects.
    """
    import toml

    data: dict = {"index": entries}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".toml.mpm_tmp")
        serialized = toml.dumps(data)
        tmp.write_text(serialized, encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        raise AllowlistWriteError(
            f"Could not write trusty-search allowlist at {path}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def add_root(
    raw_path: str | Path,
    *,
    index_id: str | None = None,
    allowlist_path: Path | None = None,
) -> tuple[bool, str]:
    """Add a directory root to the trusty-search opt-in allowlist.

    WHAT: Resolves and validates *raw_path*, checks the denylist, then writes
    an ``[[index]]`` entry to the allowlist TOML.  Idempotent: adding an
    existing root (same resolved path) is a no-op.
    WHY:  MPM must only write the allowlist on EXPLICIT user request.  This
    function is only ever called from the CLI ``search-index add`` command —
    never from startup, hooks, or any other automatic path.

    Args:
        raw_path:       Directory to register (will be expanded + resolved).
        index_id:       Override the derived index ID.  Defaults to the
                        directory basename.
        allowlist_path: Override the allowlist file location (used in tests;
                        defaults to :func:`default_allowlist_path`).

    Returns:
        ``(added, message)`` where *added* is ``True`` when a new entry was
        written, ``False`` when the entry already existed (idempotent no-op).

    Raises:
        DeniedPathError:     if the path is in the denylist.
        ValueError:          if the path is not a directory.
        AllowlistWriteError: if the TOML file cannot be read or written.
    """
    resolved = _resolve_path(raw_path)

    # Must be (or become) a real directory.
    if not resolved.is_dir():
        raise ValueError(
            f"'{raw_path}' is not a directory (resolved: '{resolved}'). "
            "trusty-search can only index directories."
        )

    _check_denylist(resolved)

    index_id = index_id or _derive_id(resolved)
    resolved_str = str(resolved)

    allowlist = allowlist_path or default_allowlist_path()
    entries = _load_registry(allowlist)

    # Idempotency check: same root_path → no-op
    for entry in entries:
        if entry.get("root_path") == resolved_str:
            return (
                False,
                f"'{resolved_str}' is already in the trusty-search allowlist "
                f"(id: {entry.get('id', '?')}).",
            )

    new_entry: dict = {
        "id": index_id,
        "root_path": resolved_str,
        "colocated": True,
    }
    entries.append(new_entry)
    _save_registry(allowlist, entries)
    return (
        True,
        f"Added '{resolved_str}' to the trusty-search allowlist (id: {index_id}).",
    )


def list_roots(
    *,
    allowlist_path: Path | None = None,
) -> list[dict]:
    """Return all index entries from the trusty-search allowlist.

    WHAT: Reads the TOML file and returns the full list of ``[[index]]`` dicts.
    Returns an empty list when the file does not exist.
    WHY:  Provides a read-only view of what trusty-search will index so users
    can verify their opt-in registrations without invoking the daemon.

    Args:
        allowlist_path: Override the allowlist file location (used in tests).

    Returns:
        List of entry dicts, each with at least ``id`` and ``root_path`` keys.
    """
    allowlist = allowlist_path or default_allowlist_path()
    return _load_registry(allowlist)


def remove_root(
    raw_path: str | Path,
    *,
    allowlist_path: Path | None = None,
) -> tuple[bool, str]:
    """Remove a directory root from the trusty-search opt-in allowlist.

    WHAT: Resolves *raw_path* and removes any ``[[index]]`` entry whose
    ``root_path`` matches the resolved path.  No-op when no matching entry
    exists.
    WHY:  Lets users un-register a project cleanly without manually editing
    the TOML file.

    Args:
        raw_path:       Directory to remove (will be expanded + resolved).
        allowlist_path: Override the allowlist file location (used in tests).

    Returns:
        ``(removed, message)`` where *removed* is ``True`` when an entry was
        deleted, ``False`` when no matching entry was found.

    Raises:
        AllowlistWriteError: if the TOML file cannot be read or written.
    """
    resolved = _resolve_path(raw_path)
    resolved_str = str(resolved)

    allowlist = allowlist_path or default_allowlist_path()
    entries = _load_registry(allowlist)

    original_count = len(entries)
    kept = [e for e in entries if e.get("root_path") != resolved_str]

    if len(kept) == original_count:
        return (
            False,
            f"'{resolved_str}' was not found in the trusty-search allowlist.",
        )

    _save_registry(allowlist, kept)
    return (True, f"Removed '{resolved_str}' from the trusty-search allowlist.")
