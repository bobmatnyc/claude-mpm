"""
Manifest CLI command group — init, validate, show.

WHAT: Implements the ``claude-mpm manifest`` subcommand group with three
subcommands:

* ``init``     — scaffold ``.claude-mpm/manifest.json`` interactively or
  non-interactively.
* ``validate`` — schema-validate and preset-resolve the manifest; exits
  non-zero with a clear, actionable error on failure.
* ``show``     — load, resolve, merge, and pretty-print the effective config
  as JSON to stdout.

WHY: A dedicated CLI surface lets developers and CI pipelines interact with
the manifest system without writing Python.  The dormant-exit-0 contract is
preserved in all three subcommands — absence of ``manifest.json`` is not an
error condition.

References
----------
SPEC-MANIFEST-05~1 : docs/specs/manifest.md#SPEC-MANIFEST-05~1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

from claude_mpm.manifest.loader import find_manifest, load_manifest
from claude_mpm.manifest.resolver import PresetResolutionError
from claude_mpm.manifest.schema import ManifestValidationError, validate_manifest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Built-in preset names offered to the user during ``init``.
_BUILTIN_PRESETS: list[str] = ["default", "minimal", "enterprise"]

#: Minimum valid manifest structure.
_MIN_MANIFEST: dict[str, str] = {"version": "1.0"}


# ---------------------------------------------------------------------------
# Helper — discover the repo root
# ---------------------------------------------------------------------------


def _repo_root(start_dir: Path | None = None) -> Path:
    """Return the directory that should contain ``.claude-mpm/``.

    WHAT: Walks upward from *start_dir* (or cwd) looking for a ``.git``
    directory.  Falls back to cwd when no git root is found so the command
    works in non-git directories.

    WHY: The manifest must sit at the project root, not just wherever the
    user happens to have ``cd``'d to.  Mirroring git-root discovery is the
    most intuitive behaviour.

    Test: Create a temp dir with a ``.git`` subdirectory, call ``_repo_root``
    from a nested subdirectory; assert the returned path equals the temp dir
    root.

    :spec: SPEC-MANIFEST-05~1
    """
    current = (start_dir or Path.cwd()).resolve()
    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            # No git root — fall back to cwd.
            return (start_dir or Path.cwd()).resolve()
        current = parent


# ---------------------------------------------------------------------------
# ``manifest init``
# ---------------------------------------------------------------------------


def _cmd_init(args: argparse.Namespace) -> int:
    """Implement ``claude-mpm manifest init``.

    WHAT: Writes a minimal ``.claude-mpm/manifest.json`` at the repo root.
    Supports interactive and non-interactive (``--non-interactive`` /
    ``--yes``) modes.  Refuses to overwrite an existing ``manifest.json``
    unless ``--force`` is given.

    WHY: Providing an ``init`` command lowers the barrier to entry — users do
    not need to know the manifest JSON structure to get started.  CI pipelines
    can use the non-interactive path to scaffold manifests deterministically.

    Test: Run with ``--non-interactive --extends default`` in a temp dir;
    assert the file is created and validates against the schema.  Run a second
    time without ``--force``; assert a non-zero exit code is returned and the
    file is unchanged.

    :spec: SPEC-MANIFEST-05~1
    """
    # Determine target directory — either --path (parent dir) or repo root.
    if args.path:
        manifest_path = Path(args.path).resolve()
    else:
        root = _repo_root()
        manifest_path = root / ".claude-mpm" / "manifest.json"

    # ------------------------------------------------------------------
    # Guard against overwrite unless --force
    # ------------------------------------------------------------------
    if manifest_path.exists() and not args.force:
        print(
            f"Error: manifest already exists at {manifest_path}\n"
            "Use --force to overwrite it.",
            file=sys.stderr,
        )
        return 1

    # ------------------------------------------------------------------
    # Determine mode (interactive vs non-interactive)
    # ------------------------------------------------------------------
    non_interactive: bool = getattr(args, "non_interactive", False) or getattr(
        args, "yes", False
    )

    # ------------------------------------------------------------------
    # Gather options
    # ------------------------------------------------------------------
    extends: str | None = getattr(args, "extends", None)
    seed_agents: bool = getattr(args, "seed_agents", False)
    seed_settings: bool = getattr(args, "seed_settings", False)
    seed_services: bool = getattr(args, "seed_services", False)

    if not non_interactive and sys.stdin.isatty():
        # Interactive prompting
        extends, seed_agents, seed_settings, seed_services = _interactive_init_prompt(
            extends, seed_agents, seed_settings, seed_services
        )
    elif not non_interactive and extends is None:
        # Non-TTY but no flags — silently use defaults (non-interactive safe).
        pass

    # ------------------------------------------------------------------
    # Build manifest dict
    # ------------------------------------------------------------------
    manifest: dict = {"version": "1.0"}

    if extends and extends.lower() != "none":
        manifest["extends"] = extends

    if seed_agents:
        manifest["agents"] = {}

    if seed_settings:
        manifest["settings"] = {}

    if seed_services:
        manifest.setdefault("setup", {})["services"] = []

    # Validate before writing (fail fast if we produced something invalid).
    validate_manifest(manifest)

    # ------------------------------------------------------------------
    # Write to disk
    # ------------------------------------------------------------------
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Created {manifest_path}")
    return 0


def _interactive_init_prompt(
    extends: str | None,
    seed_agents: bool,
    seed_settings: bool,
    seed_services: bool,
) -> tuple[str | None, bool, bool, bool]:
    """Prompt the user for ``init`` options interactively.

    WHAT: Asks whether to extend a built-in preset and which empty sections to
    seed.  Returns updated values of the four option flags.

    WHY: Separating the prompt loop from ``_cmd_init`` keeps the main logic
    testable without a TTY.

    Test: This function is intentionally not called in non-interactive tests.
    Verify via manual smoke-test or a test that patches ``input()``.

    :spec: SPEC-MANIFEST-05~1
    """
    preset_choices = _BUILTIN_PRESETS + ["none"]
    print("Available presets: " + ", ".join(preset_choices))

    if extends is None:
        raw = input(
            "Extend a preset? [default/minimal/enterprise/none] (default): "
        ).strip()
        extends = raw if raw else "default"

    if extends.lower() == "none":
        extends = None

    if not seed_agents:
        raw = input("Seed empty 'agents' section? [y/N] ").strip().lower()
        seed_agents = raw in ("y", "yes")

    if not seed_settings:
        raw = input("Seed empty 'settings' section? [y/N] ").strip().lower()
        seed_settings = raw in ("y", "yes")

    if not seed_services:
        raw = input("Seed empty 'setup.services' list? [y/N] ").strip().lower()
        seed_services = raw in ("y", "yes")

    return extends, seed_agents, seed_settings, seed_services


# ---------------------------------------------------------------------------
# Internal helper — load a manifest from an explicit file path
# ---------------------------------------------------------------------------


def _load_from_explicit_path(
    manifest_path: Path,
) -> tuple[dict, dict] | None:
    """Load, validate, and optionally merge a manifest from an explicit file.

    WHAT: Reads *manifest_path*, parses JSON, validates against the schema,
    and resolves any ``extends`` preset.  Returns a ``(repo, effective)`` tuple
    on success.  Raises ``ManifestLoadError``, ``ManifestValidationError``, or
    ``PresetResolutionError`` on failure.  Returns ``None`` if the file does
    not exist (dormant).

    WHY: ``load_manifest`` discovers files by walking upward from a directory,
    which does not work when the caller provides an arbitrary explicit path via
    ``--path``.  This helper gives ``_cmd_validate`` and ``_cmd_show`` a way to
    load a manifest at any location without the discovery logic.

    Test: Pass a valid manifest path; assert a tuple is returned.
    Pass a non-existent path; assert ``None`` is returned.

    :spec: SPEC-MANIFEST-05~1
    """
    import json as _json

    from claude_mpm.manifest.loader import ManifestLoadError

    if not manifest_path.exists():
        return None

    try:
        raw_text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestLoadError(manifest_path, f"Could not read file: {exc}") from exc

    try:
        repo_manifest: dict = _json.loads(raw_text)
    except _json.JSONDecodeError as exc:
        raise ManifestLoadError(
            manifest_path,
            f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
        ) from exc

    if not isinstance(repo_manifest, dict):
        raise ManifestLoadError(
            manifest_path,
            f"Manifest root must be a JSON object, not {type(repo_manifest).__name__}.",
        )

    validate_manifest(repo_manifest)

    extends: str | None = repo_manifest.get("extends")
    if extends is not None:
        from claude_mpm.manifest.merger import deep_merge
        from claude_mpm.manifest.resolver import resolve_preset

        preset_dict = resolve_preset(extends)
        effective = deep_merge(preset_dict, repo_manifest)
        return repo_manifest, effective

    return repo_manifest, repo_manifest


# ---------------------------------------------------------------------------
# ``manifest validate``
# ---------------------------------------------------------------------------


def _cmd_validate(args: argparse.Namespace) -> int:
    """Implement ``claude-mpm manifest validate``.

    WHAT: Locates the manifest (or uses ``--path``), schema-validates it, and
    attempts to resolve the ``extends`` preset.  Exits 0 when the manifest is
    valid or absent (dormant).  Exits non-zero with a CLEAR, actionable message
    when the manifest is invalid or its preset cannot be resolved.

    WHY: CI pipelines need a zero-friction validate command that follows shell
    conventions (exit codes) so ``manifest validate`` can be dropped into any
    CI script.  Dormant is not an error — missing a manifest is a valid
    project state.

    Test: In a temp dir with no manifest, assert exit 0.  With a valid
    ``{"version": "1.0"}`` manifest, assert exit 0.  With an invalid manifest,
    assert exit 1 and a message on stderr.  With ``extends: nonexistent``,
    assert exit 1 and a message mentioning "preset".

    :spec: SPEC-MANIFEST-05~1
    """
    from claude_mpm.manifest.loader import ManifestLoadError

    if args.path:
        # Explicit path provided — load directly without directory walking.
        manifest_path = Path(args.path).resolve()
        try:
            pair = _load_from_explicit_path(manifest_path)
        except ManifestLoadError as exc:
            print(
                f"Error: Failed to load manifest at {exc.path}\n  {exc.message}",
                file=sys.stderr,
            )
            return 1
        except ManifestValidationError as exc:
            print(
                f"Error: Manifest is invalid.\n"
                f"  Path:    {exc.path}\n"
                f"  Problem: {exc.message}\n"
                f"\nFix the field '{exc.path}' in {manifest_path} and re-run.",
                file=sys.stderr,
            )
            return 1
        except PresetResolutionError as exc:
            print(
                f"Error: Cannot resolve preset '{exc.extends}'.\n"
                f"{exc}\n"
                f"\nAvailable built-in presets: {', '.join(_BUILTIN_PRESETS)}",
                file=sys.stderr,
            )
            return 1

        if pair is None:
            print(
                f"No manifest found at {manifest_path} (system dormant).",
                file=sys.stdout,
            )
            return 0

        print(f"Manifest is valid: {manifest_path}")
        return 0

    # Auto-discovery path.
    found = find_manifest(Path.cwd())
    if found is None:
        print(
            "No manifest found (.claude-mpm/manifest.json not found). "
            "System is dormant.",
        )
        return 0

    manifest_path = found
    start_dir = manifest_path.parent.parent

    # Attempt to load (parse + validate + resolve).
    try:
        load_manifest(start_dir)
    except ManifestLoadError as exc:
        print(
            f"Error: Failed to load manifest at {exc.path}\n  {exc.message}",
            file=sys.stderr,
        )
        return 1
    except ManifestValidationError as exc:
        print(
            f"Error: Manifest is invalid.\n"
            f"  Path:    {exc.path}\n"
            f"  Problem: {exc.message}\n"
            f"\nFix the field '{exc.path}' in {manifest_path} and re-run.",
            file=sys.stderr,
        )
        return 1
    except PresetResolutionError as exc:
        print(
            f"Error: Cannot resolve preset '{exc.extends}'.\n"
            f"{exc}\n"
            f"\nAvailable built-in presets: {', '.join(_BUILTIN_PRESETS)}",
            file=sys.stderr,
        )
        return 1

    print(f"Manifest is valid: {manifest_path}")
    return 0


# ---------------------------------------------------------------------------
# ``manifest show``
# ---------------------------------------------------------------------------


def _cmd_show(args: argparse.Namespace) -> int:
    """Implement ``claude-mpm manifest show``.

    WHAT: Loads, resolves, and deep-merges the manifest, then pretty-prints the
    effective configuration as JSON to stdout.  If no manifest is found, prints
    a dormant message to stderr and exits 0.

    WHY: Developers need a quick way to inspect the fully-resolved config to
    debug merge issues and understand what is active.  Sending the JSON to
    stdout (and dormant messages to stderr) lets callers pipe into ``jq`` or
    other JSON tools without interference.

    Test: In a temp dir with ``{"version": "1.0", "extends": "default"}``,
    assert exit 0 and that the output is valid JSON containing ``"version"``.
    In a dormant temp dir, assert exit 0 with no stdout.

    :spec: SPEC-MANIFEST-05~1
    """
    from claude_mpm.manifest.loader import ManifestLoadError

    if args.path:
        # Explicit path — load directly without directory walking.
        manifest_path = Path(args.path).resolve()
        try:
            pair = _load_from_explicit_path(manifest_path)
        except ManifestLoadError as exc:
            print(
                f"Error: Failed to load manifest at {exc.path}\n  {exc.message}",
                file=sys.stderr,
            )
            return 1
        except ManifestValidationError as exc:
            print(
                f"Error: Manifest is invalid.\n"
                f"  Path:    {exc.path}\n"
                f"  Problem: {exc.message}",
                file=sys.stderr,
            )
            return 1
        except PresetResolutionError as exc:
            print(
                f"Error: Cannot resolve preset '{exc.extends}'.\n{exc}",
                file=sys.stderr,
            )
            return 1

        if pair is None:
            print("No manifest found (system dormant).", file=sys.stderr)
            return 0

        _, effective = pair
        print(json.dumps(effective, indent=2))
        return 0

    # Auto-discovery path.
    found = find_manifest(Path.cwd())
    if found is None:
        print("No manifest found (system dormant).", file=sys.stderr)
        return 0
    start_dir = found.parent.parent

    try:
        result = load_manifest(start_dir)
    except ManifestLoadError as exc:
        print(
            f"Error: Failed to load manifest at {exc.path}\n  {exc.message}",
            file=sys.stderr,
        )
        return 1
    except ManifestValidationError as exc:
        print(
            f"Error: Manifest is invalid.\n"
            f"  Path:    {exc.path}\n"
            f"  Problem: {exc.message}",
            file=sys.stderr,
        )
        return 1
    except PresetResolutionError as exc:
        print(
            f"Error: Cannot resolve preset '{exc.extends}'.\n{exc}",
            file=sys.stderr,
        )
        return 1

    if result is None:
        # load_manifest returned None — defensive guard.
        print("No manifest found (system dormant).", file=sys.stderr)
        return 0

    print(json.dumps(result.effective, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Dispatcher — called by the executor
# ---------------------------------------------------------------------------


def manage_manifest(args: argparse.Namespace) -> int:
    """Dispatch ``claude-mpm manifest <subcommand>``.

    WHAT: Routes the ``args.manifest_command`` value to the appropriate
    handler (``_cmd_init``, ``_cmd_validate``, or ``_cmd_show``).  Prints
    usage and returns 1 for unknown or missing subcommands.

    WHY: A single entry point keeps executor.py simple — one ``if command ==
    "manifest"`` branch routes here, and all manifest-specific logic is
    contained in this module.

    Test: Call with a Namespace whose ``manifest_command`` is ``"validate"``;
    assert the function delegates to ``_cmd_validate``.

    :spec: SPEC-MANIFEST-05~1
    """
    subcommand: str | None = getattr(args, "manifest_command", None)

    handlers = {
        "init": _cmd_init,
        "validate": _cmd_validate,
        "show": _cmd_show,
    }

    if subcommand in handlers:
        return handlers[subcommand](args)

    # No subcommand or unknown — print help hint.
    print(
        "Usage: claude-mpm manifest <subcommand> [options]\n"
        "\n"
        "Subcommands:\n"
        "  init       Scaffold .claude-mpm/manifest.json\n"
        "  validate   Validate manifest against schema and check preset resolution\n"
        "  show       Print the fully-resolved effective configuration as JSON\n"
        "\n"
        "Run 'claude-mpm manifest <subcommand> --help' for details.",
        file=sys.stderr,
    )
    return 1
