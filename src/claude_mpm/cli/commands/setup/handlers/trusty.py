"""Trusty (Rust) daemon setup: trusty-search, trusty-memory, trusty-analyzer.

Each `_setup_trusty_*` follows the same shape:
1. cargo-install the binary if missing.
2. Ensure the long-running daemon is up (launchd plist).
3. Register the project / palace / etc.
4. Write the ``.mcp.json`` entry (with rollback on failure).
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from pathlib import Path

from ....constants import SetupService
from ....shared import CommandResult
from .._shared import console
from ..mcp_config import _mcp_config_transaction


class TrustyMixin:
    """Mixin: trusty-search / trusty-memory / trusty-analyzer setup."""

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
        :class:`CommandResult` if installation failed.
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
            console.print(
                "[red]✗ cargo not found. Install Rust from https://rustup.rs/ "
                "and ensure ~/.cargo/bin is on PATH, then re-run setup.[/red]"
            )
            return CommandResult.error_result("cargo is required for Rust binaries")

        console.print(f"[cyan]Installing {spec.base_name} via cargo...[/cyan]")
        success, message = installer.install(
            spec, InstallAction.INSTALL, force=force, upgrade=upgrade
        )
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
        console.print(f"[green]✓ Loaded launchd agent: {label}[/green]")
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
        index_result = subprocess.run(
            [binary_path, "index", str(project_root)],
            check=False,
            capture_output=True,
            text=True,
        )  # nosec B603 B607
        if index_result.returncode == 0:
            console.print("[green]✓ Project indexed[/green]")
        else:
            console.print(
                f"[yellow]⚠ trusty-search index returned "
                f"{index_result.returncode}: {index_result.stderr.strip()}[/yellow]"
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

        console.print(
            "\n[bold green]✓ trusty-search setup complete![/bold green]\n"
            f"  • Daemon: {base_url}\n"
            "  • MCP server: stdio via `trusty-search serve`\n"
            "  • Logs: /tmp/trusty-search.log\n"
        )
        return CommandResult.success_result("trusty-search setup complete")

    def _setup_trusty_memory(self, args) -> CommandResult:
        """Set up trusty-memory Rust AI memory daemon.

        Steps:
        1. Install via cargo (or cargo-binstall) if missing.
        2. Ensure daemon is running (launchd plist).
        3. Create palace named after current project directory.
        4. Write ``.mcp.json`` entry pointing at ``trusty-memory serve --mcp``.
        """
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

        # 2. Ensure daemon running. trusty-memory exposes `status` rather than
        #    a documented /health endpoint; use the CLI for detection.
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
            or self._http_health_check("http://127.0.0.1:3038/health")
        )

        if daemon_healthy:
            console.print("[green]✓ trusty-memory daemon already running[/green]")
        else:
            console.print(
                "[cyan]Daemon not running — installing persistent launchd agent...[/cyan]"
            )
            plist_path = self._write_launchd_plist(
                label="com.bobmatnyc.trusty-memory",
                binary_path=binary_path,
                args=["serve", "--http", "127.0.0.1:3038"],
                stdout_path="/tmp/trusty-memory.log",  # nosec B108
                stderr_path="/tmp/trusty-memory-error.log",  # nosec B108
            )
            self._ensure_launchd_loaded("com.bobmatnyc.trusty-memory", plist_path)

        # 3. Create palace (named after project directory)
        palace_name = Path.cwd().name
        console.print(f"[cyan]Ensuring palace exists: {palace_name}[/cyan]")
        # `palace new` is idempotent-ish; we tolerate "already exists" by
        # falling back to `palace info`.
        new_result = subprocess.run(
            [binary_path, "palace", "new", palace_name],
            check=False,
            capture_output=True,
            text=True,
        )  # nosec B603 B607
        if new_result.returncode == 0:
            console.print(f"[green]✓ Created palace: {palace_name}[/green]")
        else:
            info_result = subprocess.run(
                [binary_path, "palace", "info", "--palace", palace_name],
                check=False,
                capture_output=True,
                text=True,
            )  # nosec B603 B607
            if info_result.returncode == 0:
                console.print(f"[green]✓ Palace already exists: {palace_name}[/green]")
            else:
                console.print(
                    f"[yellow]⚠ Could not create or verify palace: "
                    f"{new_result.stderr.strip() or info_result.stderr.strip()}[/yellow]"
                )

        # 4. Write .mcp.json entry (with rollback on failure)
        try:
            with _mcp_config_transaction():
                mcp_config = self._load_mcp_config()
                mcp_config.setdefault("mcpServers", {})
                mcp_config["mcpServers"]["trusty-memory"] = {
                    "type": "stdio",
                    "command": "trusty-memory",
                    "args": ["serve", "--mcp", "--palace", palace_name],
                }
                self._save_mcp_config(mcp_config)
                console.print("[green]✓ Added trusty-memory to .mcp.json[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to update .mcp.json: {e}[/red]")
            return CommandResult.error_result(f".mcp.json update failed: {e}")

        console.print(
            "\n[bold green]✓ trusty-memory setup complete![/bold green]\n"
            f"  • Palace: {palace_name}\n"
            "  • Daemon HTTP: http://127.0.0.1:3038\n"
            "  • MCP server: stdio via `trusty-memory serve --mcp`\n"
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
