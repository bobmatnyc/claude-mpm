"""Tests for cargo-based PackageSpec install from git URLs.

WHY: The trusty-* crates are not published to crates.io yet, so they must
be installed via ``cargo install --git <url>``. These tests pin the
command line that ``_run_cargo_install`` produces so we don't regress.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from claude_mpm.cli.constants import SetupService
from claude_mpm.services.package_installer import (
    InstallerType,
    PackageInstallerService,
    PackageSpec,
    get_spec,
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
            "trusty-analyzer",
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


def test_run_cargo_install_with_git_url_passes_git_flag(
    installer: PackageInstallerService,
) -> None:
    """When git_url is set, cargo install --git takes precedence over binstall."""
    spec = get_spec(SetupService.TRUSTY_SEARCH)

    with (
        patch("claude_mpm.services.package_installer.subprocess.run") as run,
        patch(
            "claude_mpm.services.package_installer.shutil.which",
            # cargo-binstall *is* present, but git installs must still use plain cargo.
            side_effect=lambda name: f"/usr/bin/{name}",
        ),
    ):
        installer._run_cargo_install(spec, force=False)

    cmd = run.call_args[0][0]
    assert cmd[:4] == [
        "cargo",
        "install",
        "--git",
        "https://github.com/bobmatnyc/trusty-search.git",
    ]
    assert "--bin" in cmd
    assert "trusty-search" in cmd
    assert "--force" not in cmd


def test_run_cargo_install_force_appends_force_flag(
    installer: PackageInstallerService,
) -> None:
    """Upgrade/reinstall paths must pass --force to cargo."""
    spec = get_spec(SetupService.TRUSTY_ANALYZE)

    with (
        patch("claude_mpm.services.package_installer.subprocess.run") as run,
        patch(
            "claude_mpm.services.package_installer.shutil.which",
            return_value="/usr/bin/cargo",
        ),
    ):
        installer._run_cargo_install(spec, force=True)

    cmd = run.call_args[0][0]
    assert "--force" in cmd
    # trusty-analyze repo, but trusty-analyzer binary.
    assert "https://github.com/bobmatnyc/trusty-analyze.git" in cmd
    bin_idx = cmd.index("--bin")
    assert cmd[bin_idx + 1] == "trusty-analyzer"


def test_run_cargo_install_without_git_uses_binstall_when_available(
    installer: PackageInstallerService,
) -> None:
    """Registry installs prefer cargo-binstall when present."""
    spec = PackageSpec(
        name="some-crate",
        binary_name="some-crate",
        installer=InstallerType.CARGO,
    )

    with (
        patch("claude_mpm.services.package_installer.subprocess.run") as run,
        patch(
            "claude_mpm.services.package_installer.shutil.which",
            side_effect=lambda name: f"/usr/bin/{name}",
        ),
    ):
        installer._run_cargo_install(spec, force=False)

    cmd = run.call_args[0][0]
    assert cmd == ["cargo", "binstall", "--no-confirm", "some-crate"]


def test_run_cargo_install_without_git_falls_back_to_cargo_install(
    installer: PackageInstallerService,
) -> None:
    """Registry installs fall back to ``cargo install`` when binstall missing."""
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
        patch("claude_mpm.services.package_installer.subprocess.run") as run,
        patch(
            "claude_mpm.services.package_installer.shutil.which",
            side_effect=which,
        ),
    ):
        installer._run_cargo_install(spec, force=False)

    cmd = run.call_args[0][0]
    assert cmd == ["cargo", "install", "some-crate"]
