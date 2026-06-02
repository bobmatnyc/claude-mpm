"""
tests/test_manifest_setup_integration.py — Unit tests for manifest-driven setup
integration (SPEC-MANIFEST-06~1).

WHAT: Exercises ``ManifestSetupMixin._run_manifest_services`` and the
``SetupCommand.run`` integration path across six key scenarios:
(1) dormant when no manifest present,
(2) services dispatched when manifest is present,
(3) already-configured services are skipped without --force,
(4) already-configured services are re-configured with --force,
(5) per-service fail-soft (one failure does not abort the rest),
(6) union-merge sanity (services from preset + repo are both attempted).

WHY: The manifest-driven setup path is the final acceptance criterion for
issue #460.  Idempotency, fail-soft behavior, and the dormant gate are
critical correctness properties that must be regression-tested.

References
----------
SPEC-MANIFEST-06~1 : docs/specs/manifest.md#SPEC-MANIFEST-06~1
SPEC-MANIFEST-01~1 : docs/specs/manifest.md#SPEC-MANIFEST-01~1
SPEC-MANIFEST-02~1 : docs/specs/manifest.md#SPEC-MANIFEST-02~1
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.commands.setup import ManifestSetupMixin, SetupCommand
from claude_mpm.cli.shared import CommandResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(directory: Path, content: dict) -> Path:
    """Write .claude-mpm/manifest.json in *directory* and return its path."""
    manifest_dir = directory / ".claude-mpm"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / "manifest.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


def _make_args(**kwargs) -> Namespace:
    """Return an argparse Namespace with sensible defaults for setup."""
    defaults: dict = {
        "force": False,
        "upgrade": False,
        "no_launch": True,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


# ---------------------------------------------------------------------------
# ManifestSetupMixin — isolated unit tests
# ---------------------------------------------------------------------------


class TestManifestSetupMixinDormant:
    """Verify dormant behaviour when no manifest is present."""

    def test_returns_none_when_no_manifest(self, tmp_path, monkeypatch):
        """No manifest → _run_manifest_services returns None (dormant).

        WHAT: With a working directory containing no .claude-mpm/manifest.json,
        calling ``_run_manifest_services`` must return ``None``, indicating the
        system is dormant.

        WHY: The dormant-unless-detected contract (SPEC-MANIFEST-06~1) requires
        that absence of a manifest leaves the caller's behaviour unchanged.

        Test: Patch load_manifest to return None (no file found); assert None.
        """
        mixin = ManifestSetupMixin()

        with (
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.load_manifest",
                return_value=None,
            ),
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.Path"
            ) as mock_path_cls,
        ):
            mock_path_cls.cwd.return_value = tmp_path
            result = mixin._run_manifest_services(_make_args())

        assert result is None, "Expected None (dormant) when no manifest found"

    def test_returns_none_when_load_manifest_is_none(self):
        """load_manifest=None (import failure) → dormant (None returned).

        WHY: If the manifest package is not importable, the setup command must
        remain fully functional for users who have not opted in.
        """
        mixin = ManifestSetupMixin()

        with patch(
            "claude_mpm.cli.commands.setup.manifest_integration.load_manifest",
            None,  # simulate failed import
        ):
            result = mixin._run_manifest_services(_make_args())

        assert result is None, "Expected dormant when load_manifest is None"


class TestManifestSetupMixinWithServices:
    """Verify service dispatch when manifest is present."""

    def _make_manifest_result(self, services: list[str]) -> MagicMock:
        """Create a mock ManifestResult with the given services list."""
        result = MagicMock()
        result.path = Path("/tmp/test/.claude-mpm/manifest.json")
        result.effective = {
            "version": "1.0",
            "setup": {"services": services},
        }
        return result

    def test_dispatches_each_service(self, tmp_path, monkeypatch):
        """Each service in setup.services is dispatched exactly once.

        WHAT: With a manifest listing two services, ``_run_manifest_services``
        calls ``_dispatch_service`` once per service, passing the service name
        and a Namespace with force/upgrade/no_launch attributes.

        WHY: The dispatch loop is the primary behavior; verifying call count and
        arguments confirms the contract (SPEC-MANIFEST-06~1).

        Test: Mock ``_dispatch_service`` to return success; verify two calls
        with the correct service names.
        """
        manifest_result = self._make_manifest_result(["svc-a", "svc-b"])

        dispatched: list[str] = []

        class _TestMixin(ManifestSetupMixin):
            def _dispatch_service(self, service_name, service_args):
                dispatched.append(service_name)
                return CommandResult.success_result(f"{service_name} ok")

            def _is_service_configured(self, service_name):
                return False  # nothing pre-configured

        mixin = _TestMixin()

        with (
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.load_manifest",
                return_value=manifest_result,
            ),
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.Path"
            ) as mock_path_cls,
        ):
            mock_path_cls.cwd.return_value = tmp_path

            result = mixin._run_manifest_services(_make_args())

        assert result is not None
        assert result.success
        assert dispatched == ["svc-a", "svc-b"]

    def test_empty_services_returns_success(self, tmp_path):
        """Manifest with empty setup.services returns success without dispatching.

        WHY: An empty services list is valid; the command should complete
        without error and report nothing was configured.
        """
        manifest_result = self._make_manifest_result([])

        dispatched: list[str] = []

        class _TestMixin(ManifestSetupMixin):
            def _dispatch_service(self, service_name, service_args):
                dispatched.append(service_name)
                return CommandResult.success_result("ok")

        mixin = _TestMixin()

        with (
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.load_manifest",
                return_value=manifest_result,
            ),
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.Path"
            ) as mock_path_cls,
        ):
            mock_path_cls.cwd.return_value = tmp_path

            result = mixin._run_manifest_services(_make_args())

        assert result is not None
        assert result.success
        assert dispatched == []


class TestManifestSetupMixinIdempotency:
    """Verify already-configured services are skipped / re-run with --force."""

    def _make_manifest_result(self, services: list[str]) -> MagicMock:
        result = MagicMock()
        result.path = Path("/tmp/test/.claude-mpm/manifest.json")
        result.effective = {"version": "1.0", "setup": {"services": services}}
        return result

    def test_skips_already_configured_without_force(self, tmp_path):
        """Already-configured service is skipped when --force is not given.

        WHAT: When ``SetupRegistry.get_service`` returns a non-None entry for a
        service AND ``force=False``, the service is NOT dispatched.  The result
        is still a success (skipping is not an error).

        WHY: Idempotency (SPEC-MANIFEST-06~1) makes repeated runs safe in CI.

        Test: Patch _is_service_configured to return True for svc-a; verify
        _dispatch_service is never called for svc-a.
        """
        manifest_result = self._make_manifest_result(["svc-a", "svc-b"])
        dispatched: list[str] = []

        class _TestMixin(ManifestSetupMixin):
            def _dispatch_service(self, service_name, service_args):
                dispatched.append(service_name)
                return CommandResult.success_result(f"{service_name} ok")

            def _is_service_configured(self, service_name):
                return service_name == "svc-a"  # svc-a already configured

        mixin = _TestMixin()

        with (
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.load_manifest",
                return_value=manifest_result,
            ),
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.Path"
            ) as mock_path_cls,
        ):
            mock_path_cls.cwd.return_value = tmp_path

            result = mixin._run_manifest_services(_make_args(force=False))

        assert result is not None
        assert result.success
        assert "svc-a" not in dispatched, "svc-a should be skipped (already configured)"
        assert "svc-b" in dispatched, "svc-b should be dispatched (not configured)"

    def test_force_re_configures_already_configured(self, tmp_path):
        """--force causes already-configured services to be re-configured.

        WHAT: When ``force=True``, all services are dispatched regardless of the
        registry state.

        WHY: ``--force`` is the explicit opt-in for credential rotation or
        reinstallation scenarios.

        Test: Patch _is_service_configured to return True for all services;
        set force=True; verify all are dispatched.
        """
        manifest_result = self._make_manifest_result(["svc-a", "svc-b"])
        dispatched: list[str] = []

        class _TestMixin(ManifestSetupMixin):
            def _dispatch_service(self, service_name, service_args):
                dispatched.append(service_name)
                return CommandResult.success_result(f"{service_name} ok")

            def _is_service_configured(self, service_name):
                return True  # both already configured

        mixin = _TestMixin()

        with (
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.load_manifest",
                return_value=manifest_result,
            ),
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.Path"
            ) as mock_path_cls,
        ):
            mock_path_cls.cwd.return_value = tmp_path

            result = mixin._run_manifest_services(_make_args(force=True))

        assert result is not None
        assert result.success
        assert "svc-a" in dispatched
        assert "svc-b" in dispatched


class TestManifestSetupMixinFailSoft:
    """Verify per-service fail-soft: one failure does not abort the rest."""

    def _make_manifest_result(self, services: list[str]) -> MagicMock:
        result = MagicMock()
        result.path = Path("/tmp/test/.claude-mpm/manifest.json")
        result.effective = {"version": "1.0", "setup": {"services": services}}
        return result

    def test_continues_after_failed_service(self, tmp_path):
        """A failed service does not abort dispatch of subsequent services.

        WHAT: When the first service fails (returns error CommandResult), the
        remaining services are still dispatched.

        WHY: SPEC-MANIFEST-06~1 requires fail-soft per service — one broken
        MCP server should not prevent other project services from being set up.

        Test: Three services; first returns error; verify second and third
        are still dispatched; overall result reflects partial success.
        """
        manifest_result = self._make_manifest_result(
            ["fail-svc", "ok-svc-a", "ok-svc-b"]
        )
        dispatched: list[str] = []

        class _TestMixin(ManifestSetupMixin):
            def _dispatch_service(self, service_name, service_args):
                dispatched.append(service_name)
                if service_name == "fail-svc":
                    return CommandResult.error_result("injected failure")
                return CommandResult.success_result(f"{service_name} ok")

            def _is_service_configured(self, service_name):
                return False

        mixin = _TestMixin()

        with (
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.load_manifest",
                return_value=manifest_result,
            ),
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.Path"
            ) as mock_path_cls,
        ):
            mock_path_cls.cwd.return_value = tmp_path

            result = mixin._run_manifest_services(_make_args())

        assert result is not None
        # Partial success: two succeeded, one failed → overall success
        assert result.success
        assert "fail-svc" in dispatched
        assert "ok-svc-a" in dispatched
        assert "ok-svc-b" in dispatched

    def test_all_failed_returns_error(self, tmp_path):
        """When ALL services fail, the result is an error CommandResult.

        WHAT: SPEC-MANIFEST-06~1 specifies that the exit code is non-zero only
        when all attempted services failed.

        Test: Three services all returning error; assert result.success is False.
        """
        manifest_result = self._make_manifest_result(["s1", "s2", "s3"])
        dispatched: list[str] = []

        class _TestMixin(ManifestSetupMixin):
            def _dispatch_service(self, service_name, service_args):
                dispatched.append(service_name)
                return CommandResult.error_result(f"{service_name} failed")

            def _is_service_configured(self, service_name):
                return False

        mixin = _TestMixin()

        with (
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.load_manifest",
                return_value=manifest_result,
            ),
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.Path"
            ) as mock_path_cls,
        ):
            mock_path_cls.cwd.return_value = tmp_path

            result = mixin._run_manifest_services(_make_args())

        assert result is not None
        assert not result.success, "All failed → overall error result expected"
        assert len(dispatched) == 3, "All three services should have been attempted"

    def test_exception_in_dispatch_does_not_abort(self, tmp_path):
        """An exception raised by a dispatch handler is caught (fail-soft).

        WHAT: Even if ``_dispatch_service`` raises an uncaught exception for one
        service, the remaining services are still processed.

        WHY: Defense-in-depth: the fail-soft loop catches both error results
        and unexpected exceptions.
        """
        manifest_result = self._make_manifest_result(["boom-svc", "safe-svc"])
        dispatched: list[str] = []

        class _TestMixin(ManifestSetupMixin):
            def _dispatch_service(self, service_name, service_args):
                dispatched.append(service_name)
                if service_name == "boom-svc":
                    raise RuntimeError("unexpected boom")
                return CommandResult.success_result("ok")

            def _is_service_configured(self, service_name):
                return False

        mixin = _TestMixin()

        with (
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.load_manifest",
                return_value=manifest_result,
            ),
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.Path"
            ) as mock_path_cls,
        ):
            mock_path_cls.cwd.return_value = tmp_path

            result = mixin._run_manifest_services(_make_args())

        assert result is not None
        # boom-svc failed, safe-svc succeeded → partial success
        assert result.success
        assert "boom-svc" in dispatched
        assert "safe-svc" in dispatched


class TestManifestSetupMixinUnionMerge:
    """Verify union-merge sanity: services from preset + repo are both attempted."""

    def test_union_merged_services_all_dispatched(self, tmp_path):
        """Services union-merged from preset and repo are all dispatched.

        WHAT: When a manifest uses ``extends`` and the merger produces a union
        of preset + repo services (SPEC-MANIFEST-02~1), all unique services in
        the merged list are attempted.

        WHY: Union-merge is a key design invariant.  The setup integration must
        not lose preset services by only reading the repo manifest.

        Test: Provide a manifest_result.effective with a services list that
        represents the already-merged union (["preset-svc", "repo-svc"]),
        verify both are dispatched.
        """
        # Simulate the result of deep_merge(preset, repo) where:
        # preset services = ["preset-svc"]
        # repo services   = ["repo-svc"]
        # merged          = ["preset-svc", "repo-svc"]  (union, dedup)
        manifest_result = MagicMock()
        manifest_result.path = Path("/tmp/test/.claude-mpm/manifest.json")
        manifest_result.effective = {
            "version": "1.0",
            "setup": {"services": ["preset-svc", "repo-svc"]},
        }

        dispatched: list[str] = []

        class _TestMixin(ManifestSetupMixin):
            def _dispatch_service(self, service_name, service_args):
                dispatched.append(service_name)
                return CommandResult.success_result(f"{service_name} ok")

            def _is_service_configured(self, service_name):
                return False

        mixin = _TestMixin()

        with (
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.load_manifest",
                return_value=manifest_result,
            ),
            patch(
                "claude_mpm.cli.commands.setup.manifest_integration.Path"
            ) as mock_path_cls,
        ):
            mock_path_cls.cwd.return_value = tmp_path

            result = mixin._run_manifest_services(_make_args())

        assert result is not None
        assert result.success
        assert "preset-svc" in dispatched
        assert "repo-svc" in dispatched
        assert len(dispatched) == 2, "No duplicates expected in dispatched list"


# ---------------------------------------------------------------------------
# SetupCommand.run integration — dormant path unchanged
# ---------------------------------------------------------------------------


class TestSetupCommandRunIntegration:
    """Verify SetupCommand.run preserves existing behavior without a manifest."""

    def test_no_manifest_no_services_shows_help(self):
        """Without a manifest and without services, SetupCommand.run shows help.

        WHAT: When no services are given on the command line AND no manifest is
        present, ``run()`` shows help and returns success — the original behavior.

        WHY: The manifest integration must be completely transparent to users who
        have not opted in.
        """
        cmd = SetupCommand()
        args = Namespace(
            parsed_services=[],
            global_options={},
            force=False,
            upgrade=False,
            no_launch=True,
            provider=None,
        )

        with (
            patch.object(
                cmd, "_run_manifest_services", return_value=None
            ) as mock_manifest,
            patch.object(cmd, "_show_help") as mock_help,
        ):
            result = cmd.run(args)

        mock_manifest.assert_called_once_with(args)
        mock_help.assert_called_once()
        assert result.success

    def test_manifest_present_runs_manifest_services(self):
        """With a manifest, SetupCommand.run delegates to manifest integration.

        WHAT: When ``_run_manifest_services`` returns a non-None result, ``run``
        returns that result directly without calling ``_show_help``.

        WHY: The manifest result is the complete handling for this case.
        """
        cmd = SetupCommand()
        args = Namespace(
            parsed_services=[],
            global_options={},
            force=False,
            upgrade=False,
            no_launch=True,
            provider=None,
        )
        expected = CommandResult.success_result("manifest done")

        with (
            patch.object(
                cmd, "_run_manifest_services", return_value=expected
            ) as mock_manifest,
            patch.object(cmd, "_show_help") as mock_help,
        ):
            result = cmd.run(args)

        mock_manifest.assert_called_once_with(args)
        mock_help.assert_not_called()
        assert result is expected

    def test_explicit_services_bypass_manifest(self):
        """Explicit services on the command line bypass manifest auto-run.

        WHAT: When ``parsed_services`` is non-empty, ``_run_manifest_services``
        is never called.  Explicit service lists always win.

        WHY: SPEC-MANIFEST-06~1 specifies that manifest auto-run is only
        triggered when no explicit services are given.
        """
        cmd = SetupCommand()
        args = Namespace(
            parsed_services=[{"name": "slack-mpm", "options": {}}],
            global_options={},
            force=False,
            upgrade=False,
            no_launch=True,
            provider=None,
        )

        with (
            patch.object(cmd, "_run_manifest_services") as mock_manifest,
            patch.object(
                cmd,
                "_dispatch_service",
                return_value=CommandResult.success_result("ok"),
            ),
        ):
            cmd.run(args)

        mock_manifest.assert_not_called()


# ---------------------------------------------------------------------------
# _is_service_configured — isolated unit test
# ---------------------------------------------------------------------------


class TestIsServiceConfigured:
    """Verify SetupRegistry integration for idempotency check."""

    def test_returns_true_when_registry_has_entry(self):
        """Returns True when SetupRegistry.get_service returns non-None.

        Test: Patch SetupRegistry to return a non-empty dict; assert True.
        """
        import claude_mpm.cli.commands.setup.manifest_integration as mi

        mixin = ManifestSetupMixin()
        mock_reg = MagicMock()
        mock_reg.get_service.return_value = {"type": "cli"}
        mock_reg_cls = MagicMock(return_value=mock_reg)

        original = mi.SetupRegistry
        try:
            mi.SetupRegistry = mock_reg_cls
            assert mixin._is_service_configured("my-service") is True
            mock_reg.get_service.assert_called_once_with("my-service")
        finally:
            mi.SetupRegistry = original

    def test_returns_false_when_registry_returns_none(self):
        """Returns False when SetupRegistry.get_service returns None.

        Test: Patch SetupRegistry to return None; assert False.
        """
        import claude_mpm.cli.commands.setup.manifest_integration as mi

        mixin = ManifestSetupMixin()
        mock_reg = MagicMock()
        mock_reg.get_service.return_value = None
        mock_reg_cls = MagicMock(return_value=mock_reg)

        original = mi.SetupRegistry
        try:
            mi.SetupRegistry = mock_reg_cls
            assert mixin._is_service_configured("unknown-service") is False
        finally:
            mi.SetupRegistry = original

    def test_returns_false_on_registry_exception(self):
        """Returns False (not raise) when SetupRegistry raises.

        WHY: Registry lookup is non-fatal; a missing or corrupt registry
        must not prevent setup from running.
        """
        import claude_mpm.cli.commands.setup.manifest_integration as mi

        mixin = ManifestSetupMixin()

        def _raise(*args, **kwargs):
            raise OSError("no disk space")

        original = mi.SetupRegistry
        try:
            mi.SetupRegistry = _raise  # type: ignore[assignment]
            assert mixin._is_service_configured("any-service") is False
        finally:
            mi.SetupRegistry = original


# ---------------------------------------------------------------------------
# End-to-end: real manifest file on disk
# ---------------------------------------------------------------------------


class TestEndToEndWithRealManifest:
    """End-to-end test using a real manifest file written to a tmp_path."""

    def test_real_manifest_services_dispatched(self, tmp_path):
        """With a real manifest.json on disk, services are dispatched correctly.

        WHAT: Writes a real .claude-mpm/manifest.json to tmp_path, sets cwd,
        and runs _run_manifest_services.  Verifies that the services listed in
        the manifest are dispatched.

        WHY: Verifies the full loading path (JSON read → schema validate →
        ManifestResult → services list) in integration.
        """
        _write_manifest(
            tmp_path,
            {
                "version": "1.0",
                "setup": {"services": ["real-svc-alpha", "real-svc-beta"]},
            },
        )

        dispatched: list[str] = []

        class _TestMixin(ManifestSetupMixin):
            def _dispatch_service(self, service_name, service_args):
                dispatched.append(service_name)
                return CommandResult.success_result(f"{service_name} ok")

            def _is_service_configured(self, service_name):
                return False

        mixin = _TestMixin()

        with patch(
            "claude_mpm.cli.commands.setup.manifest_integration.Path"
        ) as mock_path_cls:
            mock_path_cls.cwd.return_value = tmp_path

            result = mixin._run_manifest_services(_make_args())

        assert result is not None
        assert result.success
        assert set(dispatched) == {"real-svc-alpha", "real-svc-beta"}

    def test_no_manifest_file_returns_none(self, tmp_path):
        """No .claude-mpm/manifest.json → _run_manifest_services returns None.

        WHY: Dormant gate for the real file-based path.
        """
        dispatched: list[str] = []

        class _TestMixin(ManifestSetupMixin):
            def _dispatch_service(self, service_name, service_args):
                dispatched.append(service_name)
                return CommandResult.success_result("ok")

        mixin = _TestMixin()

        with patch(
            "claude_mpm.cli.commands.setup.manifest_integration.Path"
        ) as mock_path_cls:
            mock_path_cls.cwd.return_value = tmp_path

            result = mixin._run_manifest_services(_make_args())

        assert result is None, "Expected None when no manifest present"
        assert dispatched == [], "No services should be dispatched when dormant"
