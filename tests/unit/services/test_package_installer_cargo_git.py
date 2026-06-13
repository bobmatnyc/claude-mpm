"""Tests for cargo-based PackageSpec install from git URLs.

WHY: The trusty-* crates are migrating to crates.io. ``_run_cargo_install``
tries the registry first and falls back to ``cargo install --git <url>``
when (a) the registry attempt returns non-zero AND (b) the spec provides a
``git_url``. These tests pin the command lines and ordering so we don't
regress in either state.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.constants import SetupService
from claude_mpm.services.package_installer import (
    InstallerType,
    PackageInstallerService,
    PackageSpec,
    get_spec,
)


def _ok_completed_process(cmd: list[str]) -> subprocess.CompletedProcess:
    """Build a successful CompletedProcess stand-in for mocked subprocess.run."""
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")


def _fail_completed_process(cmd: list[str]) -> subprocess.CompletedProcess:
    """Build a failing CompletedProcess (simulating crates.io rejection)."""
    return subprocess.CompletedProcess(
        args=cmd, returncode=1, stdout="", stderr="error: crate not found"
    )


@pytest.fixture
def installer() -> PackageInstallerService:
    return PackageInstallerService()


@pytest.mark.parametrize(
    "service,expected_git,expected_bin",
    [
        (
            SetupService.TRUSTY_SEARCH,
            "https://github.com/bobmatnyc/trusty-search.git",
            "trusty-search",
        ),
        (
            SetupService.TRUSTY_MEMORY,
            "https://github.com/bobmatnyc/trusty-memory.git",
            "trusty-memory",
        ),
        (
            SetupService.TRUSTY_ANALYZE,
            "https://github.com/bobmatnyc/trusty-analyze.git",
            "trusty-analyze",
        ),
    ],
)
def test_trusty_specs_use_git_url(
    service: SetupService, expected_git: str, expected_bin: str
) -> None:
    """All trusty-* services install from GitHub with explicit --bin."""
    spec = get_spec(service)
    assert spec.installer is InstallerType.CARGO
    assert spec.git_url == expected_git
    assert spec.bin_name == expected_bin


def test_run_cargo_install_registry_success_skips_git_fallback(
    installer: PackageInstallerService,
) -> None:
    """When the crates.io install exits 0, ``--git`` fallback must NOT run."""
    spec = get_spec(SetupService.TRUSTY_SEARCH)

    with (
        patch(
            "claude_mpm.services.package_installer.subprocess.run",
            side_effect=lambda cmd, **kw: _ok_completed_process(cmd),
        ) as run,
        patch(
            "claude_mpm.services.package_installer.shutil.which",
            # cargo-binstall present so registry attempt uses it.
            side_effect=lambda name: f"/usr/bin/{name}",
        ),
    ):
        installer._run_cargo_install(spec, force=False)

    # Exactly one subprocess.run call — the registry one.
    assert run.call_count == 1
    cmd = run.call_args_list[0][0][0]
    assert cmd == ["cargo", "binstall", "--no-confirm", "trusty-search"]


def test_run_cargo_install_registry_failure_falls_back_to_git(
    installer: PackageInstallerService,
) -> None:
    """When the crates.io install exits non-zero, retry with ``--git <url>``."""
    spec = get_spec(SetupService.TRUSTY_SEARCH)

    call_log: list[list[str]] = []

    def fake_run(cmd, **kw):
        call_log.append(list(cmd))
        # First call (registry) fails; second call (git) succeeds.
        if call_log[0] == cmd:
            return _fail_completed_process(cmd)
        return _ok_completed_process(cmd)

    with (
        patch(
            "claude_mpm.services.package_installer.subprocess.run",
            side_effect=fake_run,
        ),
        patch(
            "claude_mpm.services.package_installer.shutil.which",
            side_effect=lambda name: f"/usr/bin/{name}",
        ),
    ):
        installer._run_cargo_install(spec, force=False)

    assert len(call_log) == 2
    # 1st: registry attempt (binstall preferred when present)
    assert call_log[0] == ["cargo", "binstall", "--no-confirm", "trusty-search"]
    # 2nd: git fallback
    assert call_log[1][:4] == [
        "cargo",
        "install",
        "--git",
        "https://github.com/bobmatnyc/trusty-search.git",
    ]
    assert "--bin" in call_log[1]
    assert "trusty-search" in call_log[1]
    assert "--force" not in call_log[1]


def test_run_cargo_install_registry_failure_no_git_url_raises(
    installer: PackageInstallerService,
) -> None:
    """No git_url → registry failure raises CalledProcessError as before."""
    spec = PackageSpec(
        name="some-crate",
        binary_name="some-crate",
        installer=InstallerType.CARGO,
    )

    with (
        patch(
            "claude_mpm.services.package_installer.subprocess.run",
            side_effect=lambda cmd, **kw: _fail_completed_process(cmd),
        ),
        patch(
            "claude_mpm.services.package_installer.shutil.which",
            side_effect=lambda name: f"/usr/bin/{name}",
        ),
        pytest.raises(subprocess.CalledProcessError),
    ):
        installer._run_cargo_install(spec, force=False)


def test_run_cargo_install_force_appends_force_to_both_attempts(
    installer: PackageInstallerService,
) -> None:
    """``--force`` must apply to both registry and git fallback commands."""
    spec = get_spec(SetupService.TRUSTY_ANALYZE)

    call_log: list[list[str]] = []

    def fake_run(cmd, **kw):
        call_log.append(list(cmd))
        # Registry fails so we exercise the git fallback path too.
        if len(call_log) == 1:
            return _fail_completed_process(cmd)
        return _ok_completed_process(cmd)

    with (
        patch(
            "claude_mpm.services.package_installer.subprocess.run",
            side_effect=fake_run,
        ),
        patch(
            "claude_mpm.services.package_installer.shutil.which",
            return_value="/usr/bin/cargo",
        ),
    ):
        installer._run_cargo_install(spec, force=True)

    # 1st (registry, no binstall) gets --force
    assert "--force" in call_log[0]
    # 2nd (git fallback) gets --force AND the trusty-analyze repo
    assert "--force" in call_log[1]
    assert "https://github.com/bobmatnyc/trusty-analyze.git" in call_log[1]
    bin_idx = call_log[1].index("--bin")
    assert call_log[1][bin_idx + 1] == "trusty-analyze"


def test_run_cargo_install_without_binstall_uses_cargo_install(
    installer: PackageInstallerService,
) -> None:
    """Registry attempt falls back to plain ``cargo install`` when binstall missing."""
    spec = PackageSpec(
        name="some-crate",
        binary_name="some-crate",
        installer=InstallerType.CARGO,
    )

    def which(name: str) -> str | None:
        if name == "cargo-binstall":
            return None
        return f"/usr/bin/{name}"

    with (
        patch(
            "claude_mpm.services.package_installer.subprocess.run",
            side_effect=lambda cmd, **kw: _ok_completed_process(cmd),
        ) as run,
        patch(
            "claude_mpm.services.package_installer.shutil.which",
            side_effect=which,
        ),
    ):
        installer._run_cargo_install(spec, force=False)

    cmd = run.call_args[0][0]
    assert cmd == ["cargo", "install", "some-crate"]


# Keep a reference to MagicMock to silence "unused import" — kept available
# in case future tests need attribute-style mocks.
_ = MagicMock
