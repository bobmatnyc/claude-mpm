"""Autonomous setup handlers — delegate to a tool's own ``<binary> setup``.

Two strategies live here:

* :meth:`AutonomousSetupMixin._run_autonomous_setup` — declarative path used by
  services registered in :data:`AUTONOMOUS_SETUP_SERVICES`.
* :meth:`AutonomousSetupMixin._try_autonomous_setup_fallback` — open-world
  fallback for unknown service names that happen to be binaries on PATH with
  a working ``setup`` subcommand.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from pathlib import Path

from ...shared import CommandResult
from ._shared import console


class AutonomousSetupMixin:
    """Mixin providing declarative + fallback autonomous setup paths."""

    def _run_autonomous_setup(
        self, service_name: str, config: dict, args
    ) -> CommandResult:
        """Run setup for a service registered in AUTONOMOUS_SETUP_SERVICES.

        Steps:
        1. Optionally install the package via PackageInstallerService if
           config["install_spec"] is set.
        2. Exec `<binary> setup`, inheriting stdio so the tool can prompt
           the user interactively.
        3. Return success/error based on exit code.

        Args:
            service_name: Human-readable service identifier (for messages).
            config: Entry from AUTONOMOUS_SETUP_SERVICES with keys:
                    binary, install_spec, mcp_server_name.
            args: Namespace with optional force/upgrade attributes.

        Returns:
            CommandResult indicating success or failure.
        """
        binary: str = config["binary"]
        install_spec = config.get("install_spec")
        mcp_server_name = config.get("mcp_server_name")

        try:
            # Step 1: optional package installation.
            if install_spec is not None:
                from ....services.package_installer import (
                    InstallAction,
                    PackageInstallerService,
                    get_spec,
                )

                installer = PackageInstallerService()
                spec = get_spec(install_spec)
                force = getattr(args, "force", False)
                upgrade = getattr(args, "upgrade", False)

                console.print(f"[cyan]Checking {service_name} installation...[/cyan]")
                if installer.is_installed(spec) and not force and not upgrade:
                    console.print(f"[green]✓ {service_name} already installed[/green]")
                else:
                    console.print("[cyan]Detecting installation method...[/cyan]")
                    success, message = installer.install(
                        spec, InstallAction.INSTALL, force=force, upgrade=upgrade
                    )
                    if success:
                        console.print(f"[green]✓ {message}[/green]")
                    else:
                        return CommandResult.error_result(message)

            # Step 2: delegate to the tool's own setup command.
            console.print(f"\n[cyan]Running {binary} setup...[/cyan]")
            result = subprocess.run(
                [binary, "setup"],
                check=False,
            )  # nosec B603 B607 — inherit stdio for interactive prompts

            if result.returncode == 0:
                console.print(
                    f"[green]✓ {service_name} configured successfully[/green]"
                )

                # Step 3: optionally register in .mcp.json.
                if mcp_server_name:
                    try:
                        from ..oauth import _ensure_mcp_configured

                        _ensure_mcp_configured(mcp_server_name, Path.cwd())
                    except Exception as exc:
                        console.print(
                            f"[yellow]Warning: could not update .mcp.json: {exc}[/yellow]"
                        )

                return CommandResult.success_result(f"{service_name} setup completed")

            console.print(
                f"[yellow]{service_name} setup completed with non-zero exit ({result.returncode})[/yellow]"
            )
            return CommandResult.success_result(
                f"{service_name} setup completed with warnings"
            )

        except FileNotFoundError:
            console.print(
                f"[red]{binary} not found. Install {service_name} first.[/red]"
            )
            return CommandResult.error_result(f"{binary} not installed")
        except Exception as exc:
            console.print(f"[red]Failed to setup {service_name}: {exc}[/red]")
            return CommandResult.error_result(f"Failed to setup {service_name}: {exc}")

    def _try_autonomous_setup_fallback(
        self,
        service_name: str,
        _args,
        force: bool = False,
    ) -> CommandResult:
        """Open-world fallback: try `<service_name> setup` if the binary exists.

        If the binary is found in PATH and responds to `setup --help` without
        crashing (exit code 0 or 1), we delegate automatically.  This allows
        new tools to work without any code changes to SetupCommand.

        Args:
            service_name: Name of the service (also used as the binary name).
            args: Namespace (unused but kept for consistent signature).
            force: If True, skip already-configured check and re-run setup.

        Returns:
            CommandResult — error if the binary is absent or not setup-capable.
        """
        _ = _args  # args passed by caller dispatch; not used in this implementation
        binary = service_name  # Convention: binary name == service name.

        # Check if service is already configured (unless force=True).
        if not force:
            try:
                from claude_mpm.services.setup_registry import SetupRegistry

                registry = SetupRegistry()
                if registry.get_service(service_name) is not None:
                    console.print(
                        f"[green]✓ {service_name} is already configured[/green]"
                    )
                    return CommandResult.success_result(
                        f"{service_name} already configured"
                    )
            except Exception:  # nosec B110
                pass  # Registry lookup is non-fatal; continue to setup.

        if not shutil.which(binary):
            return CommandResult.error_result(f"Unknown service: {service_name}")

        # Probe whether the binary accepts a `setup` subcommand.
        probe = subprocess.run(
            [binary, "setup", "--help"],
            capture_output=True,
            check=False,
        )  # nosec B603 B607
        if probe.returncode not in (0, 1):
            # Binary exists but has no `setup` subcommand or crashed.
            return CommandResult.error_result(f"Unknown service: {service_name}")

        console.print(f"[cyan]Auto-detected '{binary} setup' — delegating...[/cyan]")
        result = subprocess.run(
            [binary, "setup"],
            check=False,
        )  # nosec B603 B607 — inherit stdio for interactive prompts

        if result.returncode == 0:
            console.print(f"[green]✓ {service_name} setup completed[/green]")
            # Record successful setup in the registry.
            try:
                from claude_mpm.services.setup_registry import SetupRegistry

                registry = SetupRegistry()
                registry.add_service(
                    name=service_name,
                    service_type="cli",
                    version="unknown",
                    tools=[],
                )
            except Exception:  # nosec B110
                pass  # Registry recording is non-fatal.
            return CommandResult.success_result(f"{service_name} setup completed")

        return CommandResult.error_result(
            f"{service_name} setup exited with code {result.returncode}"
        )
