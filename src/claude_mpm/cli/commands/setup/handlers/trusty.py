"""Trusty (Rust) daemon setup: trusty-search, trusty-memory, trusty-analyzer.

Each `_setup_trusty_*` follows the same shape:
1. cargo-install the binary if missing.
2. Ensure the long-running daemon is up (launchd plist).
3. Register the project / palace / etc.
4. Write the ``.mcp.json`` entry (with rollback on failure).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import Any

from ....constants import SetupService
from ....shared import CommandResult
from .._shared import console
from ..mcp_config import _mcp_config_transaction

# Legacy services whose hooks should be removed when injecting trusty hooks.
# These are the predecessors of trusty-search / trusty-memory and would
# duplicate or conflict with the new daemons.
_LEGACY_SERVICES = {"kuzu-memory", "mcp-vector-search"}

# Hook specifications keyed by trusty service name. Each entry lists the
# (event, matcher, hook_dict) tuples to inject. The ``_mpm_service`` tag is
# the dedup key — re-running setup will not duplicate hooks.
_TRUSTY_HOOK_SPECS: dict[str, list[tuple[str, str, dict[str, Any]]]] = {
    "trusty-memory": [
        (
            event,
            "*",
            {
                "type": "command",
                "command": "claude-hook",
                "timeout": 15,
                "_mpm": True,
                "_mpm_service": "trusty-memory",
            },
        )
        for event in ("SessionStart", "Stop", "SubagentStop")
    ],
    "trusty-search": [
        (
            "PostToolUse",
            "Write|MultiEdit|Edit|NotebookEdit",
            {
                "type": "command",
                "command": "python3",
                "args": ["-m", "claude_mpm.hooks.trusty_index_hook"],
                "timeout": 10,
                "async": True,
                "_mpm": True,
                "_mpm_service": "trusty-search",
            },
        ),
    ],
}


class TrustyMixin:
    """Mixin: trusty-search / trusty-memory / trusty-analyzer setup."""

    # ------------------------------------------------------------------
    # Declare methods provided by McpConfigMixin at runtime via MRO.
    # These stubs satisfy Pyright without creating circular imports.
    # ------------------------------------------------------------------

    def _load_mcp_config(self) -> dict[str, Any]: ...  # pragma: no cover

    def _save_mcp_config(self, _: dict[str, Any]) -> None: ...  # pragma: no cover

    # ------------------------------------------------------------------
    # Generic Rust-binary helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _http_health_check(url: str, timeout: float = 2.0) -> bool:
        """Best-effort HTTP health probe.

        Uses urllib from the stdlib to avoid adding new dependencies. Any
        non-2xx, network error, or timeout is treated as "not healthy".
        """
        import urllib.error
        import urllib.request

        try:
            req = urllib.request.Request(url, method="GET")  # nosec B310 - localhost
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
                return 200 <= resp.status < 300
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    @staticmethod
    def _cargo_bin_path(binary_name: str) -> str:
        """Resolve a cargo-installed binary path dynamically.

        Prefers ``shutil.which`` (honors current PATH), then falls back to
        ``~/.cargo/bin/<binary>``.
        """
        resolved = shutil.which(binary_name)
        if resolved:
            return resolved
        return str(Path.home() / ".cargo" / "bin" / binary_name)

    def _install_cargo_binary(
        self, args, service: SetupService
    ) -> CommandResult | None:
        """Ensure a cargo-installed Rust binary is present.

        Returns ``None`` on success (continue setup) or an error
        :class:`CommandResult` if installation failed. All error paths emit
        a red console line with the underlying reason so users never see a
        bare "Setup failed for trusty-*" with no explanation.
        """
        from .....services.package_installer import (
            InstallAction,
            InstallerType,
            PackageInstallerService,
            get_spec,
        )

        spec = get_spec(service)
        installer = PackageInstallerService()

        force = getattr(args, "force", False)
        upgrade = getattr(args, "upgrade", False)

        if installer.is_installed(spec) and not force and not upgrade:
            console.print(f"[green]✓ {spec.base_name} already installed[/green]")
            return None

        if not shutil.which("cargo"):
            msg = (
                "cargo not found. Install Rust from https://rustup.rs/ "
                "and ensure ~/.cargo/bin is on PATH, then re-run setup."
            )
            console.print(f"[red]✗ {msg}[/red]")
            return CommandResult.error_result(msg)

        console.print(f"[cyan]Installing {spec.base_name} via cargo...[/cyan]")
        try:
            success, message = installer.install(
                spec, InstallAction.INSTALL, force=force, upgrade=upgrade
            )
        except Exception as exc:
            msg = (
                f"cargo install of {spec.base_name} raised {type(exc).__name__}: {exc}"
            )
            console.print(f"[red]✗ {msg}[/red]")
            return CommandResult.error_result(msg)
        # Silence "unused import" for InstallerType (kept for type clarity).
        _ = InstallerType
        if success:
            console.print(f"[green]✓ {message}[/green]")
            return None
        console.print(f"[red]✗ {message}[/red]")
        return CommandResult.error_result(message)

    @staticmethod
    def _write_launchd_plist(
        *,
        label: str,
        binary_path: str,
        args: list[str],
        stdout_path: str,
        stderr_path: str,
    ) -> Path:
        """Write a launchd plist for a long-running user daemon.

        Returns the plist path. Caller is responsible for ``launchctl load``.
        """
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_dir.mkdir(parents=True, exist_ok=True)
        plist_path = plist_dir / f"{label}.plist"

        # Build ProgramArguments XML
        program_args_xml = "\n".join(
            f"        <string>{binary_path}</string>"
            if i == 0
            else f"        <string>{a}</string>"
            for i, a in enumerate([binary_path, *args])
        )

        plist_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
{program_args_xml}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>30</integer>
    <key>StandardOutPath</key>
    <string>{stdout_path}</string>
    <key>StandardErrorPath</key>
    <string>{stderr_path}</string>
</dict>
</plist>
"""
        plist_path.write_text(plist_xml)
        return plist_path

    def _ensure_launchd_loaded(self, label: str, plist_path: Path) -> bool:
        """Reload a launchd plist (unload then load) without prompting.

        After load, verify the agent appears in ``launchctl list`` so we know
        the daemon will survive reboots / process crashes (the plist's
        ``KeepAlive=true`` + ``RunAtLoad=true`` is only meaningful once the
        agent is actually loaded). A green/red console line communicates the
        persistence state to the user.

        Returns True on best-effort success. Logs warnings if launchctl is
        missing (non-macOS); callers should handle that gracefully.
        """
        if not shutil.which("launchctl"):
            console.print(
                "[yellow]⚠ launchctl not found — skipping persistent daemon setup. "
                "Run the binary manually to test.[/yellow]"
            )
            return False

        # Unload first (ignore failures — plist may not be loaded yet).
        subprocess.run(
            ["launchctl", "unload", str(plist_path)],
            check=False,
            capture_output=True,
        )  # nosec B603 B607
        load_result = subprocess.run(
            ["launchctl", "load", str(plist_path)],
            check=False,
            capture_output=True,
            text=True,
        )  # nosec B603 B607
        if load_result.returncode != 0:
            console.print(
                f"[yellow]⚠ launchctl load failed for {label}: "
                f"{load_result.stderr.strip()}[/yellow]"
            )
            return False
        # Verify the agent is registered with launchd. `launchctl list <label>`
        # exits non-zero when the agent isn't loaded (which would mean it
        # won't auto-restart on crash or survive a reboot).
        list_result = subprocess.run(
            ["launchctl", "list", label],
            check=False,
            capture_output=True,
            text=True,
        )  # nosec B603 B607
        if list_result.returncode != 0:
            console.print(
                f"[yellow]⚠ launchd agent {label} loaded but not visible in "
                f"`launchctl list` — daemon may not persist across reboots.[/yellow]"
            )
            return False
        console.print(
            f"[green]✓ Loaded launchd agent: {label} (KeepAlive enabled)[/green]"
        )
        return True

    @staticmethod
    def _trusty_search_base_url() -> str:
        """Discover the running trusty-search daemon's base URL.

        Why: trusty-search #56 switched to OS-chosen dynamic ports written to
        ``~/.trusty-search/http_addr`` (format: ``host:port`` on a single
        line). Hardcoding ``127.0.0.1:7878`` makes ``claude-mpm setup
        trusty-search`` silently fail whenever the daemon picked a different
        port. This helper reads the discovery file and falls back to the
        legacy port only when the file is missing/unreadable.
        What: returns ``http://<host>:<port>``.
        Test: with ``~/.trusty-search/http_addr`` containing
        ``127.0.0.1:54321`` → returns ``http://127.0.0.1:54321``; with the
        file absent → returns ``http://127.0.0.1:7878``.
        """
        addr_file = Path.home() / ".trusty-search" / "http_addr"
        try:
            addr = addr_file.read_text(encoding="utf-8").strip()
            if addr:
                return f"http://{addr}"
        except OSError:
            pass
        return "http://127.0.0.1:7878"

    @staticmethod
    def _trusty_memory_base_url() -> str:
        """Discover the running trusty-memory daemon's base URL.

        Why: trusty-memory writes its bound address to ``~/.trusty-memory/http_addr``
        (same pattern as trusty-search). Hardcoding a port causes silent failures
        when the daemon picks a different address.
        What: reads ``~/.trusty-memory/http_addr`` and returns
        ``http://<host>:<port>``; falls back to ``http://127.0.0.1:7070``
        when the file is missing or unreadable.
        Test: with ``~/.trusty-memory/http_addr`` containing ``127.0.0.1:7070``
        → returns ``http://127.0.0.1:7070``; with the file absent →
        returns ``http://127.0.0.1:7070``.
        """
        addr_file = Path.home() / ".trusty-memory" / "http_addr"
        try:
            addr = addr_file.read_text(encoding="utf-8").strip()
            if addr:
                return f"http://{addr}"
        except OSError:
            pass
        return "http://127.0.0.1:7070"

    # ------------------------------------------------------------------
    # Hook injection (Claude Code settings.json)
    # ------------------------------------------------------------------

    @staticmethod
    def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
        """Write JSON atomically: write to a sibling temp file, then rename.

        Why atomic: settings.json is read by Claude Code on every hook
        invocation; a partial write would crash hooks until repaired.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        # Use a NamedTemporaryFile in the same directory so os.replace is
        # guaranteed to be atomic (same filesystem).
        fd, tmp_path = tempfile.mkstemp(
            prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            Path(tmp_path).replace(path)
        except Exception:
            # Best effort cleanup of temp file.
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass
            raise

    @staticmethod
    def _load_settings(path: Path) -> dict[str, Any]:
        """Load a Claude Code settings.json, returning skeleton on absence.

        Tolerates an existing file that lacks the ``hooks`` key.
        """
        if not path.exists():
            return {"hooks": {}}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Could not parse {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"{path} root is not a JSON object")
        data.setdefault("hooks", {})
        if not isinstance(data["hooks"], dict):
            raise RuntimeError(f"{path}: 'hooks' is not an object")
        return data

    def _inject_hooks_to_settings(
        self, settings_path: Path, services: list[str]
    ) -> None:
        """Inject trusty hook entries into a Claude Code settings.json.

        For each requested service:
        - Remove any hooks tagged with ``_mpm_service`` in ``_LEGACY_SERVICES``
          across all events (cleanup of predecessor hooks).
        - Add the hooks declared in ``_TRUSTY_HOOK_SPECS[service]`` to the
          matching (event, matcher) group, skipping any whose
          ``_mpm_service`` already exists in that group (idempotent).

        File handling:
        - Creates the file with ``{"hooks": {}}`` if missing.
        - Preserves all unrelated hooks (e.g. user personal scripts).
        - Writes atomically (temp file + rename).
        - Reports removals and additions via the rich console.
        """
        try:
            settings = self._load_settings(settings_path)
        except RuntimeError as exc:
            console.print(f"[yellow]⚠ Skipping {settings_path}: {exc}[/yellow]")
            return

        hooks_root: dict[str, Any] = settings["hooks"]
        removed_count = 0
        added: list[str] = []
        skipped: list[str] = []

        # ----- Removal pass: drop legacy-service hooks across all events.
        for event_name, groups in list(hooks_root.items()):
            if not isinstance(groups, list):
                continue
            new_groups: list[dict[str, Any]] = []
            for group in groups:
                if not isinstance(group, dict):
                    new_groups.append(group)
                    continue
                inner = group.get("hooks")
                if not isinstance(inner, list):
                    new_groups.append(group)
                    continue
                filtered_inner = [
                    h
                    for h in inner
                    if not (
                        isinstance(h, dict)
                        and h.get("_mpm_service") in _LEGACY_SERVICES
                    )
                ]
                dropped = len(inner) - len(filtered_inner)
                if dropped:
                    removed_count += dropped
                # Drop the entire group if its hooks list is now empty AND
                # the group only held legacy hooks (no other meaningful keys).
                if filtered_inner:
                    group["hooks"] = filtered_inner
                    new_groups.append(group)
                elif not inner:
                    new_groups.append(group)
                # else: group is empty after removal, drop it.
            if new_groups:
                hooks_root[event_name] = new_groups
            else:
                del hooks_root[event_name]

        # ----- Injection pass: add trusty hooks idempotently.
        for service in services:
            for event, matcher, hook_def in _TRUSTY_HOOK_SPECS.get(service, []):
                groups = hooks_root.setdefault(event, [])
                if not isinstance(groups, list):
                    console.print(
                        f"[yellow]⚠ {settings_path}: '{event}' is not a list — "
                        f"skipping injection.[/yellow]"
                    )
                    continue

                # Find a group with the matching matcher, or create one.
                target_group: dict[str, Any] | None = None
                for group in groups:
                    if (
                        isinstance(group, dict)
                        and group.get("matcher") == matcher
                        and isinstance(group.get("hooks"), list)
                    ):
                        target_group = group
                        break
                if target_group is None:
                    target_group = {"matcher": matcher, "hooks": []}
                    groups.append(target_group)

                inner_hooks: list[Any] = target_group["hooks"]
                tag = hook_def.get("_mpm_service")
                # Dedup by _mpm_service within the same (event, matcher) group.
                already_present = any(
                    isinstance(h, dict) and h.get("_mpm_service") == tag
                    for h in inner_hooks
                )
                if already_present:
                    skipped.append(f"{event}[{matcher}]:{tag}")
                    continue
                inner_hooks.append(hook_def)
                added.append(f"{event}[{matcher}]:{tag}")

        # ----- Write back atomically.
        try:
            self._atomic_write_json(settings_path, settings)
        except OSError as exc:
            console.print(f"[red]✗ Failed to write {settings_path}: {exc}[/red]")
            return

        # ----- Report.
        rel = str(settings_path)
        if removed_count:
            console.print(
                f"[yellow]• {rel}: removed {removed_count} legacy hook(s) "
                f"({', '.join(sorted(_LEGACY_SERVICES))})[/yellow]"
            )
        if added:
            console.print(
                f"[green]✓ {rel}: added {len(added)} hook(s): "
                f"{', '.join(added)}[/green]"
            )
        if skipped:
            console.print(
                f"[dim]• {rel}: {len(skipped)} hook(s) already present, skipped[/dim]"
            )
        if not (removed_count or added or skipped):
            console.print(f"[dim]• {rel}: no hook changes needed[/dim]")

    def _inject_trusty_hooks(self, services: list[str]) -> None:
        """Inject hooks into both project and user-level settings.

        Project settings (``./.claude/settings.json``) are only touched if
        the file already exists — we don't want to create a project-level
        config silently. User settings (``~/.claude/settings.json``) are
        created if missing because per-user hook injection is the documented
        intent of this setup step.
        """
        project_settings = Path.cwd() / ".claude" / "settings.json"
        user_settings = Path.home() / ".claude" / "settings.json"

        console.print("[cyan]Injecting trusty hooks into Claude settings...[/cyan]")

        if project_settings.exists():
            self._inject_hooks_to_settings(project_settings, services)
        else:
            console.print(
                f"[dim]• {project_settings} not found — skipping project-level "
                f"hook injection.[/dim]"
            )

        # Always inject into user settings (create if missing).
        self._inject_hooks_to_settings(user_settings, services)

    # ------------------------------------------------------------------
    # Service-specific setup methods
    # ------------------------------------------------------------------

    def _setup_trusty_search(self, args) -> CommandResult:
        """Set up trusty-search Rust hybrid code search daemon.

        Steps:
        1. Install via cargo (or cargo-binstall) if missing.
        2. Ensure daemon is running (dynamic port via
           ``~/.trusty-search/http_addr``, legacy fallback
           ``127.0.0.1:7878``); install launchd plist if down.
        3. Register/index current project.
        4. Write ``.mcp.json`` entry pointing at ``trusty-search serve``.
        """
        console.print("\n[bold cyan]Trusty Search MCP Setup[/bold cyan]")
        console.print(
            "Installs trusty-search (Rust hybrid code search daemon) and registers "
            "this project for indexed semantic + BM25 + KG search.\n"
        )

        # 1. Install binary
        install_err = self._install_cargo_binary(args, SetupService.TRUSTY_SEARCH)
        if install_err is not None:
            return install_err

        binary_path = self._cargo_bin_path("trusty-search")

        # 2. Ensure daemon running — discover address dynamically (#61).
        base_url = self._trusty_search_base_url()
        health_url = f"{base_url}/health"
        if self._http_health_check(health_url):
            console.print(
                f"[green]✓ trusty-search daemon already running at {base_url}[/green]"
            )
        else:
            console.print(
                "[cyan]Daemon not running — installing persistent launchd agent...[/cyan]"
            )
            plist_path = self._write_launchd_plist(
                label="com.bobmatnyc.trusty-search",
                binary_path=binary_path,
                args=["start"],
                stdout_path="/tmp/trusty-search.log",  # nosec B108
                stderr_path="/tmp/trusty-search-error.log",  # nosec B108
            )
            self._ensure_launchd_loaded("com.bobmatnyc.trusty-search", plist_path)

            # Give the daemon a moment to come up. It may pick a new
            # dynamic port, so re-resolve the base URL each poll iteration.
            import time

            confirmed = False
            for _ in range(10):
                time.sleep(0.5)
                base_url = self._trusty_search_base_url()
                health_url = f"{base_url}/health"
                if self._http_health_check(health_url):
                    confirmed = True
                    break
            if not confirmed:
                console.print(
                    f"[yellow]⚠ Could not confirm daemon health on "
                    f"{base_url} — continuing anyway. "
                    f"Check /tmp/trusty-search-error.log if MCP calls fail.[/yellow]"
                )

        # 3. Register & index current project
        project_root = Path.cwd()
        console.print(
            f"[cyan]Indexing project: {project_root.name} ({project_root})[/cyan]"
        )
        try:
            index_result = subprocess.run(
                [binary_path, "index", str(project_root)],
                check=False,
                timeout=120,
            )  # nosec B603 B607
            if index_result.returncode == 0:
                console.print("[green]✓ Project indexed[/green]")
            else:
                console.print(
                    f"[yellow]⚠ trusty-search index returned "
                    f"{index_result.returncode}[/yellow]"
                )
        except subprocess.TimeoutExpired:
            console.print(
                "[yellow]⚠ trusty-search index timed out after 120s — "
                "continuing; re-run `trusty-search index` later if needed.[/yellow]"
            )
        except (OSError, subprocess.SubprocessError) as exc:
            # Don't fail the whole setup because indexing hiccupped; the MCP
            # config write below is the real success criterion.
            console.print(
                f"[yellow]⚠ trusty-search index raised "
                f"{type(exc).__name__}: {exc} — continuing.[/yellow]"
            )

        # 4. Write .mcp.json entry (with rollback on failure)
        try:
            with _mcp_config_transaction():
                mcp_config = self._load_mcp_config()
                mcp_config.setdefault("mcpServers", {})
                mcp_config["mcpServers"]["trusty-search"] = {
                    "type": "stdio",
                    "command": "trusty-search",
                    "args": ["serve"],
                }
                self._save_mcp_config(mcp_config)
                console.print("[green]✓ Added trusty-search to .mcp.json[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to update .mcp.json: {e}[/red]")
            return CommandResult.error_result(f".mcp.json update failed: {e}")

        # 5. Inject PostToolUse hook into Claude settings (idempotent).
        self._inject_trusty_hooks(["trusty-search"])

        console.print(
            "\n[bold green]✓ trusty-search setup complete![/bold green]\n"
            f"  • Daemon: {base_url}\n"
            "  • MCP server: stdio via `trusty-search serve`\n"
            "  • Logs: /tmp/trusty-search.log\n"
        )
        return CommandResult.success_result("trusty-search setup complete")

    def _setup_trusty_memory(self, args) -> CommandResult:
        """Set up trusty-memory Rust AI memory daemon.

        Why: trusty-memory provides persistent AI memory palaces keyed to
        projects; without a correctly-running daemon and matching palace,
        all MCP memory calls silently fail.
        What: installs the binary, ensures the daemon is reachable via its
        HTTP API (port 7070 / dynamic via ~/.trusty-memory/http_addr), creates
        the project palace via REST if absent, wires the MCP stdio entry into
        .mcp.json, then injects claude-hook SessionStart/Stop/SubagentStop hooks.
        Test: run ``claude-mpm setup trusty-memory`` in a project directory and
        verify (a) the palace appears via GET /api/v1/palaces, (b) .mcp.json
        contains the trusty-memory entry, and (c) settings.json contains the
        SessionStart hook entry tagged with ``_mpm_service: trusty-memory``.

        Steps:
        1. Install via cargo (or cargo-binstall) if missing.
        2. Ensure daemon is running (launchd plist + HTTP health check).
        3. Create palace named after current project via HTTP API.
        4. Write ``.mcp.json`` entry pointing at ``trusty-memory-mcp-bridge``.
        5. Inject SessionStart/Stop/SubagentStop hooks via claude-hook architecture.
        """
        import json as _json
        import urllib.error
        import urllib.request

        console.print("\n[bold cyan]Trusty Memory MCP Setup[/bold cyan]")
        console.print(
            "Installs trusty-memory (Rust AI memory daemon) and creates a "
            "Memory Palace for this project.\n"
        )

        # 1. Install binary
        install_err = self._install_cargo_binary(args, SetupService.TRUSTY_MEMORY)
        if install_err is not None:
            return install_err

        binary_path = self._cargo_bin_path("trusty-memory")

        # 2. Ensure daemon running.  Prefer HTTP health check on the discovery
        #    URL; fall back to launchd if unreachable.
        base_url = self._trusty_memory_base_url()
        health_url = f"{base_url}/health"

        # NOTE: `trusty-memory status` can hang when the daemon is wedged or
        # being started; we MUST tolerate the timeout instead of letting
        # subprocess.TimeoutExpired bubble up as a generic "Command failed"
        # from BaseCommand.execute (which hides the real reason and prevents
        # remaining services from being processed).
        try:
            status_result = subprocess.run(
                [binary_path, "status"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )  # nosec B603 B607
            daemon_healthy = status_result.returncode == 0 and (
                "healthy" in status_result.stdout.lower()
                or "ok" in status_result.stdout.lower()
                or self._http_health_check(health_url)
            )
        except subprocess.TimeoutExpired:
            console.print(
                "[yellow]⚠ `trusty-memory status` timed out — assuming daemon "
                "is not healthy and will (re)load the launchd agent.[/yellow]"
            )
            daemon_healthy = self._http_health_check(health_url)

        if daemon_healthy:
            console.print(
                f"[green]✓ trusty-memory daemon already running at {base_url}[/green]"
            )
        else:
            console.print(
                "[cyan]Daemon not running — installing persistent launchd agent...[/cyan]"
            )
            plist_path = self._write_launchd_plist(
                label="com.bobmatnyc.trusty-memory",
                binary_path=binary_path,
                args=["serve"],
                stdout_path="/tmp/trusty-memory.log",  # nosec B108
                stderr_path="/tmp/trusty-memory-error.log",  # nosec B108
            )
            self._ensure_launchd_loaded("com.bobmatnyc.trusty-memory", plist_path)

            # Re-discover address after daemon start; poll until healthy.
            import time

            confirmed = False
            for _ in range(10):
                time.sleep(0.5)
                base_url = self._trusty_memory_base_url()
                health_url = f"{base_url}/health"
                if self._http_health_check(health_url):
                    confirmed = True
                    break
            if not confirmed:
                console.print(
                    f"[yellow]⚠ Could not confirm daemon health on "
                    f"{base_url} — continuing anyway. "
                    f"Check /tmp/trusty-memory-error.log if MCP calls fail.[/yellow]"
                )

        # 3. Create palace via HTTP API (the binary has no `palace` subcommand).
        palace_name = Path.cwd().name
        console.print(f"[cyan]Ensuring palace exists: {palace_name}[/cyan]")

        palaces_url = f"{base_url}/api/v1/palaces"
        palace_found = False
        try:
            req = urllib.request.Request(palaces_url, method="GET")  # nosec B310
            with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
                raw = resp.read().decode("utf-8")
                data = _json.loads(raw)
                palace_list = (
                    data if isinstance(data, list) else data.get("palaces", [])
                )
                for p in palace_list:
                    if p.get("name", "").lower() == palace_name.lower():
                        palace_found = True
                        break
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            _json.JSONDecodeError,
        ) as exc:
            console.print(
                f"[yellow]⚠ Could not list palaces ({exc}); "
                "will attempt to create anyway.[/yellow]"
            )

        if palace_found:
            console.print(f"[green]✓ Palace already exists: {palace_name}[/green]")
        else:
            try:
                body = _json.dumps(
                    {
                        "name": palace_name,
                        "description": "Claude Code session memory for project",
                    }
                ).encode("utf-8")
                req = urllib.request.Request(  # nosec B310
                    palaces_url,
                    data=body,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
                    if 200 <= resp.status < 300:
                        console.print(f"[green]✓ Created palace: {palace_name}[/green]")
                    else:
                        console.print(
                            f"[yellow]⚠ Palace creation returned HTTP {resp.status}[/yellow]"
                        )
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                console.print(
                    f"[yellow]⚠ Could not create palace '{palace_name}': {exc}[/yellow]"
                )

        # 4. Write .mcp.json entry (with rollback on failure)
        try:
            with _mcp_config_transaction():
                mcp_config = self._load_mcp_config()
                mcp_config.setdefault("mcpServers", {})
                mcp_config["mcpServers"]["trusty-memory"] = {
                    "type": "stdio",
                    "command": "trusty-memory-mcp-bridge",
                    "args": [],
                }
                self._save_mcp_config(mcp_config)
                console.print("[green]✓ Added trusty-memory to .mcp.json[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to update .mcp.json: {e}[/red]")
            return CommandResult.error_result(f".mcp.json update failed: {e}")

        # 5. Inject SessionStart/Stop/SubagentStop hooks (idempotent).
        self._inject_trusty_hooks(["trusty-memory"])

        console.print(
            "\n[bold green]✓ trusty-memory setup complete![/bold green]\n"
            f"  • Palace: {palace_name}\n"
            f"  • Daemon HTTP: {base_url}\n"
            "  • MCP server: stdio via `trusty-memory-mcp-bridge`\n"
            "  • Logs: /tmp/trusty-memory.log\n"
        )
        return CommandResult.success_result("trusty-memory setup complete")

    def _setup_trusty_analyze(self, args) -> CommandResult:
        """Set up trusty-analyzer Rust code-analysis sidecar daemon.

        The installed binary is ``trusty-analyzer`` (note the trailing "r");
        only the user-facing setup verb is ``trusty-analyze`` so it matches
        the GitHub repo name.

        Steps:
        1. Install via cargo (from git) if missing.
        2. Ensure daemon is running on http://127.0.0.1:7879 (launchd plist).
        3. Write ``.mcp.json`` entry pointing at ``trusty-analyzer mcp``.
        """
        console.print("\n[bold cyan]Trusty Analyzer MCP Setup[/bold cyan]")
        console.print(
            "Installs trusty-analyzer (Rust code-analysis sidecar daemon) and "
            "wires it into this project's .mcp.json. Sits next to trusty-search "
            "on port 7879.\n"
        )

        # 1. Install binary
        install_err = self._install_cargo_binary(args, SetupService.TRUSTY_ANALYZE)
        if install_err is not None:
            return install_err

        binary_path = self._cargo_bin_path("trusty-analyzer")

        # 2. Ensure daemon running on 7879
        health_url = "http://127.0.0.1:7879/health"
        if self._http_health_check(health_url):
            console.print("[green]✓ trusty-analyzer daemon already running[/green]")
        else:
            console.print(
                "[cyan]Daemon not running — installing persistent launchd agent...[/cyan]"
            )
            plist_path = self._write_launchd_plist(
                label="com.bobmatnyc.trusty-analyzer",
                binary_path=binary_path,
                args=["serve"],
                stdout_path="/tmp/trusty-analyzer.log",  # nosec B108
                stderr_path="/tmp/trusty-analyzer-error.log",  # nosec B108
            )
            self._ensure_launchd_loaded("com.bobmatnyc.trusty-analyzer", plist_path)

            # Give the daemon a moment to come up, then re-probe.
            import time

            for _ in range(10):
                if self._http_health_check(health_url):
                    break
                time.sleep(0.5)
            else:
                console.print(
                    "[yellow]⚠ Could not confirm daemon health on "
                    "http://127.0.0.1:7879 — continuing anyway. "
                    "Check /tmp/trusty-analyzer-error.log if MCP calls fail.[/yellow]"
                )

        # 3. Write .mcp.json entry (with rollback on failure)
        try:
            with _mcp_config_transaction():
                mcp_config = self._load_mcp_config()
                mcp_config.setdefault("mcpServers", {})
                mcp_config["mcpServers"]["trusty-analyzer"] = {
                    "type": "stdio",
                    "command": "trusty-analyzer",
                    "args": ["mcp"],
                }
                self._save_mcp_config(mcp_config)
                console.print("[green]✓ Added trusty-analyzer to .mcp.json[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to update .mcp.json: {e}[/red]")
            return CommandResult.error_result(f".mcp.json update failed: {e}")

        console.print(
            "\n[bold green]✓ trusty-analyze setup complete![/bold green]\n"
            "  • Daemon: http://127.0.0.1:7879\n"
            "  • MCP server: stdio via `trusty-analyzer mcp`\n"
            "  • Logs: /tmp/trusty-analyzer.log\n"
        )
        return CommandResult.success_result("trusty-analyze setup complete")
