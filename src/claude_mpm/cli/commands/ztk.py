"""``claude-mpm ztk`` command family: status, update, and currency checks.

WHY a dedicated command (vs auto-download at runtime):
- Fetching a binary is a NETWORK + privileged operation. Doing it silently on
  the Bash hot path or at startup would block sessions and surprise users.
- This command makes the update EXPLICIT and MANUAL by default. It re-runs the
  same ``scripts/download_ztk_binaries.sh`` the release process uses, with the
  version PINNED in ``claude_mpm/bin/ztk_version.txt`` (the single source of
  truth shared with the Makefile) — so an update is deterministic/reproducible.

What is automatic vs manual:
- AUTOMATIC: at startup, claude-mpm detects the installed ztk version (cached by
  binary fingerprint) and surfaces ``on (vX.Y.Z)`` / ``outdated`` in the banner.
  No network call, no download.
- MANUAL: ``claude-mpm ztk update`` fetches the pinned binary. ``claude-mpm ztk
  check`` performs an OPT-IN, cached (24h), failure-tolerant query of the latest
  GitHub release tag — never blocks, never errors if GitHub is unreachable.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

_ZTK_REPO = "codejunkie99/ztk"
_LATEST_CACHE = Path.home() / ".claude-mpm" / "ztk-latest-cache.json"
_LATEST_TTL = timedelta(hours=24)
_LATEST_TIMEOUT_S = 4.0


def _download_script() -> Path:
    """Locate scripts/download_ztk_binaries.sh relative to the repo root.

    Resolution: walk up from this file until a ``scripts/`` dir is found. For
    installed wheels this script is not shipped, so we report a clear message.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "scripts" / "download_ztk_binaries.sh"
        if candidate.is_file():
            return candidate
    return Path("scripts/download_ztk_binaries.sh")


def _fetch_latest_release_tag(*, use_cache: bool = True) -> str | None:
    """Return the latest ztk release tag from GitHub, cached + failure-tolerant.

    OFF the hot path: only called by ``ztk check`` / ``ztk update --latest``.
    The result is cached to ``~/.claude-mpm/ztk-latest-cache.json`` for 24h (per
    the CLAUDE.md TTL cache pattern). ANY network/parse failure returns None
    without raising, so GitHub being unreachable never blocks or errors.
    """
    if use_cache:
        cached = _read_latest_cache()
        if cached is not None:
            return cached

    url = f"https://api.github.com/repos/{_ZTK_REPO}/releases/latest"
    # Defense-in-depth: the URL is a fixed https constant, but assert the scheme
    # explicitly so a future edit can never smuggle in file:/ or a custom scheme.
    if not url.startswith("https://"):
        return None
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(  # nosec B310 — https asserted; fixed GitHub host
            req, timeout=_LATEST_TIMEOUT_S
        ) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tag = data.get("tag_name")
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
    if isinstance(tag, str) and tag:
        _write_latest_cache(tag)
        return tag
    return None


def _read_latest_cache() -> str | None:
    try:
        data = json.loads(_LATEST_CACHE.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(data["fetched_at"])
        if datetime.now(UTC) - ts < _LATEST_TTL:
            return data.get("tag")
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return None
    return None


def _write_latest_cache(tag: str) -> None:
    try:
        _LATEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _LATEST_CACHE.write_text(
            json.dumps({"tag": tag, "fetched_at": datetime.now(UTC).isoformat()}),
            encoding="utf-8",
        )
    except OSError:
        pass  # cache is best-effort; never fail the command over it


def _print_status() -> int:
    from claude_mpm.hooks.ztk_hook import ztk_status_detail

    detail = ztk_status_detail()
    active = detail["active"]
    installed = detail["installed_version"] or "unknown"
    required = detail["required_version"] or "unknown"
    currency = detail["currency"]

    print(f"ztk active:    {'yes' if active else 'no'}  ({detail['reason']})")
    print(f"installed:     {installed}")
    print(f"required:      {required}")
    print(f"currency:      {currency}")
    if detail.get("path"):
        print(f"path:          {detail['path']}")
    if currency == "outdated":
        print(
            "\n→ Outdated. Run 'claude-mpm ztk update' to refresh the bundled binary."
        )
    return 0


def _run_update(tag: str) -> int:
    script = _download_script()
    if not script.is_file():
        print(
            f"Cannot find {script} — the download script is not shipped in "
            "installed wheels. Reinstall claude-mpm to refresh the bundled "
            "ztk binary, or run 'make download-ztk' from a source checkout.",
            file=sys.stderr,
        )
        return 1
    print(f"Fetching ztk {tag} via {script.name}...")
    try:
        # fixed argv (no shell), bundled trusted release script; `tag` is the
        # pinned manifest version or a GitHub-provided release tag.
        proc = subprocess.run(  # nosec B603
            ["bash", str(script), tag],
            check=False,
        )
    except OSError as exc:
        print(f"Failed to run download script: {exc}", file=sys.stderr)
        return 1
    if proc.returncode != 0:
        print(f"Download script exited {proc.returncode}.", file=sys.stderr)
        return proc.returncode
    print(f"ztk {tag} installed. Restart claude-mpm to pick up the new binary.")
    return 0


def run_ztk(args: argparse.Namespace) -> int:
    """Dispatch ``claude-mpm ztk <subcommand>``."""
    from claude_mpm.hooks.ztk_hook import _read_required_version

    subcommand = getattr(args, "ztk_command", None) or "status"

    if subcommand == "status":
        return _print_status()

    if subcommand == "check":
        required = _read_required_version() or "unknown"
        latest = _fetch_latest_release_tag()
        print(f"pinned (required): {required}")
        if latest is None:
            print(
                "latest (GitHub):   unavailable "
                "(network unreachable or no releases — non-fatal)"
            )
        else:
            print(f"latest (GitHub):   {latest}")
            if latest != required:
                print(
                    f"\n→ A newer ztk ({latest}) is available upstream. The pinned "
                    f"version is {required}; bump ZTK_VERSION in the Makefile + "
                    "ztk_version.txt to adopt it in the next release."
                )
        return 0

    if subcommand == "update":
        # Default: install the PINNED version (reproducible). --latest opts into
        # the newest upstream release (still explicit, still cached lookup).
        tag = _read_required_version()
        if getattr(args, "latest", False):
            latest = _fetch_latest_release_tag(use_cache=False)
            if latest is None:
                print(
                    "Could not determine latest release (GitHub unreachable). "
                    "Falling back to pinned version.",
                    file=sys.stderr,
                )
            else:
                tag = latest
        if not tag:
            print(
                "No pinned ztk version found (missing ztk_version.txt manifest).",
                file=sys.stderr,
            )
            return 1
        return _run_update(tag)

    print(f"Unknown ztk subcommand: {subcommand}", file=sys.stderr)
    return 1


def add_ztk_parser(subparsers) -> None:
    """Register the ``ztk`` command group (status / check / update)."""
    parser = subparsers.add_parser(
        "ztk",
        help="Manage the bundled ztk binary (status, version check, update)",
        description=(
            "Inspect and maintain the ztk shell-compression binary.\n\n"
            "  status  Show active state + installed/required version + currency\n"
            "  check   Compare pinned version against latest GitHub release "
            "(cached 24h, network-failure tolerant)\n"
            "  update  Fetch the pinned ztk binary (or --latest) via the "
            "release download script"
        ),
    )
    ztk_sub = parser.add_subparsers(dest="ztk_command", metavar="<subcommand>")

    ztk_sub.add_parser("status", help="Show ztk status, version, and currency")
    ztk_sub.add_parser(
        "check", help="Check pinned version against latest GitHub release (cached)"
    )
    update_parser = ztk_sub.add_parser(
        "update", help="Download the pinned ztk binary (or --latest)"
    )
    update_parser.add_argument(
        "--latest",
        action="store_true",
        help="Fetch the latest upstream release instead of the pinned version",
    )

    parser.set_defaults(command="ztk")
