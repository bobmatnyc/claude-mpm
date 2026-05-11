"""MCP config (``.mcp.json``) helpers and transactional rollback primitives.

Provides:
- :class:`AuthFailedError` — raised by service setup steps to trigger rollback.
- :func:`_read_mcp_json_snapshot` / :func:`_restore_mcp_json` — low-level snapshot helpers.
- :func:`_mcp_config_transaction` — context manager that rolls ``.mcp.json``
  back to its prior state if the wrapped block raises.
- :class:`McpConfigMixin` — instance methods for loading/saving ``.mcp.json``,
  mixed into :class:`SetupCommand`.

These are imported by handler mixins to keep .mcp.json edits atomic.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

from ._shared import console


class AuthFailedError(Exception):
    """Raised when an MCP server's auth/validation step fails after .mcp.json was modified.

    Used to trigger rollback of .mcp.json changes via the
    ``_mcp_config_transaction`` context manager.
    """


def _read_mcp_json_snapshot(mcp_config_path: Path) -> str | None:
    """Capture the raw contents of .mcp.json for later rollback.

    Returns:
        The raw file contents as a string, or ``None`` if the file does not
        exist. We deliberately preserve the raw bytes (including formatting,
        comments-as-keys, and trailing newlines) so the rollback restores the
        file exactly as it was.
    """
    if not mcp_config_path.exists():
        return None
    try:
        return mcp_config_path.read_text()
    except OSError as exc:
        console.print(
            f"[yellow]Warning: Could not snapshot .mcp.json for rollback: {exc}[/yellow]"
        )
        # Returning None here would cause rollback to delete the file, which
        # is unsafe. Re-raise so the transaction never opens.
        raise


def _restore_mcp_json(mcp_config_path: Path, snapshot: str | None) -> None:
    """Restore .mcp.json to a previously captured snapshot.

    Args:
        mcp_config_path: Path to .mcp.json.
        snapshot: Previously captured contents (from
            ``_read_mcp_json_snapshot``), or ``None`` if the file did not
            exist before the transaction.
    """
    try:
        if snapshot is None:
            # File didn't exist before — remove anything we created.
            if mcp_config_path.exists():
                mcp_config_path.unlink()
        else:
            mcp_config_path.write_text(snapshot)
    except OSError as exc:
        console.print(
            f"[red]Error: Failed to roll back .mcp.json: {exc}[/red]\n"
            f"[red]Manual cleanup may be required at {mcp_config_path}[/red]"
        )


@contextmanager
def _mcp_config_transaction(project_dir: Path | None = None):
    """Context manager that rolls back .mcp.json on failure.

    Captures the current state of ``<project_dir>/.mcp.json`` before yielding.
    If the wrapped block raises (typically :class:`AuthFailedError`), the file
    is restored to its prior state — including deletion if it didn't exist
    originally — and a clear message is emitted before re-raising.

    Usage::

        with _mcp_config_transaction():
            self._save_mcp_config(new_config)   # write new entry
            run_auth_flow()                      # may raise AuthFailedError

    Args:
        project_dir: Directory containing .mcp.json (defaults to CWD).
    """
    project_dir = project_dir or Path.cwd()
    mcp_config_path = project_dir / ".mcp.json"
    snapshot = _read_mcp_json_snapshot(mcp_config_path)

    try:
        yield
    except BaseException:
        _restore_mcp_json(mcp_config_path, snapshot)
        console.print(
            "[yellow]Auth failed — rolled back .mcp.json to previous state[/yellow]"
        )
        raise


class McpConfigMixin:
    """Mixin providing .mcp.json read/write helpers for :class:`SetupCommand`."""

    def _load_mcp_config(self) -> dict:
        """Load .mcp.json configuration file.

        Returns:
            Dict containing config or empty dict if file doesn't exist
        """
        mcp_config_path = Path.cwd() / ".mcp.json"

        if mcp_config_path.exists():
            try:
                with open(mcp_config_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                console.print(
                    f"[yellow]Warning: Could not read .mcp.json: {e}[/yellow]"
                )
                return {"mcpServers": {}}

        return {"mcpServers": {}}

    def _save_mcp_config(self, config: dict) -> None:
        """Save .mcp.json configuration file.

        Args:
            config: Configuration dict to save
        """
        mcp_config_path = Path.cwd() / ".mcp.json"

        try:
            with open(mcp_config_path, "w") as f:
                json.dump(config, f, indent=2)
                f.write("\n")  # Add trailing newline
        except OSError as e:
            console.print(f"[yellow]Warning: Could not write .mcp.json: {e}[/yellow]")
            raise
