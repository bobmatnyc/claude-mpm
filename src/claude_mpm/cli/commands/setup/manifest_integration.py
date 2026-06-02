"""
Manifest-driven setup integration for ``claude-mpm setup``.

WHAT: Provides ``ManifestSetupMixin`` which is composed into ``SetupCommand``.
When ``claude-mpm setup`` is invoked without explicit service names, this mixin
detects a ``.claude-mpm/manifest.json`` in the working directory, loads and
resolves it, and auto-runs each service listed in the merged
``setup.services`` array through the existing ``_dispatch_service`` path.
Returns ``None`` (dormant) when no manifest is present, delegating control back
to the caller for the original help-display behavior.

WHY: The manifest system must remain dormant for projects that have not opted in.
Reusing ``_dispatch_service`` means all future service additions are automatically
available to manifest-driven setup without code changes here.  Idempotency via
``SetupRegistry`` makes repeated ``claude-mpm setup`` invocations safe in CI.
Per-service fail-soft ensures one broken service cannot block the rest.

References
----------
SPEC-MANIFEST-06~1 : docs/specs/manifest.md#SPEC-MANIFEST-06~1
SPEC-MANIFEST-01~1 : docs/specs/manifest.md#SPEC-MANIFEST-01~1
SPEC-MANIFEST-02~1 : docs/specs/manifest.md#SPEC-MANIFEST-02~1
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from ...shared import CommandResult
from ._shared import console

# ---------------------------------------------------------------------------
# Module-level imports from the manifest and registry packages.
# Placed at module level (not inside methods) so test code can patch them via
# ``patch("claude_mpm.cli.commands.setup.manifest_integration.load_manifest")``
# and similar targets.  Both imports are guarded with a try/except so the
# module remains importable even if the packages are unavailable.
# ---------------------------------------------------------------------------

try:
    from claude_mpm.manifest import load_manifest
except ImportError:  # pragma: no cover — only absent in abnormal installs
    load_manifest = None  # type: ignore[assignment]

try:
    from claude_mpm.services.setup_registry import SetupRegistry
except ImportError:  # pragma: no cover
    SetupRegistry = None  # type: ignore[assignment,misc]


class ManifestSetupMixin:
    """Mixin that adds manifest-driven auto-setup to ``SetupCommand``.

    WHAT: Adds ``_run_manifest_services(args)`` which is the entry point called
    by ``SetupCommand.run`` when no explicit services were given on the command
    line.  Dormant (returns ``None``) when no manifest file is present.

    WHY: Composed as a mixin so the manifest integration can be tested
    independently of the full ``SetupCommand`` dependency graph.

    :spec: SPEC-MANIFEST-06~1
    """

    def _is_service_configured(self, service_name: str) -> bool:
        """Check whether a service is already recorded in the SetupRegistry.

        WHAT: Returns ``True`` when ``SetupRegistry.get_service(service_name)``
        is not ``None``.  Returns ``False`` when the registry is unavailable
        (import error, I/O error) so the caller falls through to configure the
        service rather than silently skipping it.

        WHY: The registry lookup is best-effort; a missing or corrupt registry
        file must not prevent setup from running.

        Test: Patch ``SetupRegistry`` to return a non-None entry and assert
        ``True``; patch to return ``None`` and assert ``False``; patch to raise
        and assert ``False``.

        :spec: SPEC-MANIFEST-06~1

        Parameters
        ----------
        service_name:
            The service identifier to look up (e.g. ``"kuzu-memory"``).

        Returns
        -------
        bool
            ``True`` if the service is already configured, ``False`` otherwise.
        """
        try:
            if SetupRegistry is None:
                return False
            registry = SetupRegistry()
            return registry.get_service(service_name) is not None
        except Exception:  # nosec B110 — registry lookup is non-fatal
            return False

    def _run_manifest_services(self, args: Namespace) -> CommandResult | None:
        """Load the manifest and auto-run each service in ``setup.services``.

        WHAT: Entry point called by ``SetupCommand.run`` when no explicit
        services were given.  Returns ``None`` (dormant sentinel) when no
        ``.claude-mpm/manifest.json`` is found so the caller can fall through
        to its original help-display path.  When a manifest is present, reads
        the merged ``setup.services`` list, skips already-configured services
        (unless ``--force``), dispatches each remaining service through the
        existing ``_dispatch_service`` method, and returns a ``CommandResult``
        summarising the outcome.

        WHY: The dormant-unless-detected contract requires that ``None`` is
        returned (not an empty success) when there is no manifest, so the
        caller can distinguish "no manifest" from "manifest with empty
        services list".  Reusing ``_dispatch_service`` means this path
        inherits all handler and open-world-fallback logic automatically.

        Test:
        - No manifest in cwd → returns ``None``.
        - Manifest present with no ``setup.services`` key → success, no services
          attempted.
        - Manifest present, services listed → ``_dispatch_service`` called once
          per service; ``CommandResult.success`` when at least one succeeds.
        - Service already in registry + no ``--force`` → skipped, not dispatched.
        - Service in registry + ``--force`` → dispatched anyway.
        - One service raises → others still attempted; summary reflects failure.

        :spec: SPEC-MANIFEST-06~1
        :spec: SPEC-MANIFEST-01~1
        :spec: SPEC-MANIFEST-02~1

        Parameters
        ----------
        args:
            Parsed argument namespace; ``force`` attribute is read for the
            idempotency override.

        Returns
        -------
        CommandResult | None
            ``None`` — no manifest found (caller should show help or default
            behaviour).
            ``CommandResult`` — manifest found; result reflects success/partial/
            failure over the listed services.
        """
        # -- DORMANT CHECK ----------------------------------------------------
        if load_manifest is None:
            # Manifest package not importable — remain dormant.
            return None  # pragma: no cover

        cwd = Path.cwd()
        try:
            manifest_result = load_manifest(cwd)
        except Exception as exc:
            # Manifest found but broken — report error and abort.
            console.print(f"[red]Failed to load manifest: {exc}[/red]")
            return CommandResult.error_result(f"Manifest load error: {exc}")

        if manifest_result is None:
            # No manifest file present — system stays dormant.
            return None

        # -- READ SERVICES FROM EFFECTIVE CONFIG ------------------------------
        effective = manifest_result.effective
        setup_block: dict = effective.get("setup", {})
        services: list[str] = setup_block.get("services", [])

        if not services:
            console.print(
                "[dim]Manifest found but setup.services is empty — nothing to do.[/dim]"
            )
            return CommandResult.success_result("No manifest services to configure")

        force: bool = getattr(args, "force", False)

        console.print(
            f"\n[bold cyan]Manifest found at {manifest_result.path}[/bold cyan]"
        )
        console.print(
            f"[cyan]Auto-configuring {len(services)} service(s) from manifest...[/cyan]\n"
        )

        # -- PER-SERVICE DISPATCH (fail-soft) ---------------------------------
        results: list[tuple[str, str, CommandResult]] = []
        # statuses: "configured", "skipped", "failed"

        for service_name in services:
            # Idempotency: skip if already configured and not --force.
            if not force and self._is_service_configured(service_name):
                console.print(
                    f"[green]✓ {service_name} already configured (skipping)[/green]"
                )
                results.append(
                    (service_name, "skipped", CommandResult.success_result("skipped"))
                )
                continue

            console.print(
                f"[bold cyan]Setting up {service_name} (from manifest)...[/bold cyan]"
            )

            try:
                service_args = Namespace(force=force, upgrade=False, no_launch=True)
                result = self._dispatch_service(service_name, service_args)  # type: ignore[attr-defined]
            except Exception as exc:
                # Fail-soft: capture exception, continue with next service.
                console.print(
                    f"[red]✗ {service_name} raised an unexpected error: {exc}[/red]"
                )
                result = CommandResult.error_result(f"{service_name} raised: {exc}")

            if result.success:
                console.print(f"[green]✓ {service_name} setup complete![/green]")
                results.append((service_name, "configured", result))
            else:
                console.print(f"[red]✗ Setup failed for {service_name}[/red]")
                results.append((service_name, "failed", result))

        # -- SUMMARY ----------------------------------------------------------
        configured = [r for r in results if r[1] == "configured"]
        skipped = [r for r in results if r[1] == "skipped"]
        failed = [r for r in results if r[1] == "failed"]

        console.print("")
        if configured:
            console.print(
                f"[green]✓ {len(configured)} service(s) configured[/green]",
                style="bold",
            )
        if skipped:
            console.print(
                f"[dim]  {len(skipped)} service(s) skipped (already configured)[/dim]"
            )
        if failed:
            failed_names = ", ".join(r[0] for r in failed)
            console.print(
                f"[red]✗ {len(failed)} service(s) failed: {failed_names}[/red]",
                style="bold",
            )

        # Exit non-zero only if every attempted (non-skipped) service failed.
        attempted = [r for r in results if r[1] != "skipped"]
        if attempted and all(r[1] == "failed" for r in attempted):
            return CommandResult.error_result(
                f"All {len(attempted)} manifest service(s) failed"
            )

        return CommandResult.success_result(
            f"Manifest setup: {len(configured)} configured, "
            f"{len(skipped)} skipped, {len(failed)} failed"
        )
