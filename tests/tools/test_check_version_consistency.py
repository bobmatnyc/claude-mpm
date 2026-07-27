"""Tests for tools/dev/checks/check_version_consistency.py.

Regression test for GitHub issue #947: the pre-publish version-consistency
check was a silent no-op since ~v4.3.3 for two stacked reasons:

1. ``Makefile`` invoked a path that no longer existed
   (``scripts/check_version_consistency.py`` was renamed to
   ``tools/dev/checks/check_version_consistency.py`` in commit
   ``f4be0f25a``) and swallowed the resulting non-zero exit with
   ``|| echo "... (non-blocking)"``.
2. Even after repointing the Makefile, ``get_project_root()`` used
   ``Path(__file__).parent.parent`` which, from the script's new location
   at ``tools/dev/checks/``, resolves to ``tools/dev`` instead of the repo
   root — every version file lookup silently returned ``None`` and the
   check reported "all consistent" vacuously.

These tests load the script directly (it lives under ``tools/``, not the
installed package) and verify: (a) ``get_project_root`` resolves to the
actual repo root, (b) the check fails when version files genuinely
disagree, and (c) the check passes when they agree.
"""

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "dev"
    / "checks"
    / "check_version_consistency.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "check_version_consistency", _SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def module():
    return _load_module()


def test_get_project_root_resolves_to_repo_root(module):
    """get_project_root() must resolve to the actual repository root, not
    tools/dev. This is the second-order bug from #947: after fixing the
    Makefile path, the script itself still needed four .parent hops."""
    root = module.get_project_root()

    assert root == _SCRIPT_PATH.resolve().parent.parent.parent.parent
    # Sanity check: the resolved root should actually look like the repo
    # root (contains pyproject.toml), not an intermediate directory like
    # tools/ or tools/dev/.
    assert (root / "pyproject.toml").exists()
    assert root.name not in {"dev", "checks", "tools"}


@pytest.fixture
def fake_repo(tmp_path):
    """Build a minimal project tree with version files under the script's
    expected layout, and return a helper to write consistent/inconsistent
    versions."""

    def _write(
        version="1.2.3",
        src_version="1.2.3",
        pyproject_version="1.2.3",
        package_json_version="1.2.3",
    ):
        (tmp_path / "VERSION").write_text(f"{version}\n")

        src_dir = tmp_path / "src" / "claude_mpm"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "VERSION").write_text(f"{src_version}\n")

        (tmp_path / "pyproject.toml").write_text(
            f'[project]\nname = "claude-mpm"\nversion = "{pyproject_version}"\n'
        )

        (tmp_path / "package.json").write_text(
            json.dumps({"name": "claude-mpm", "version": package_json_version})
        )

        return tmp_path

    return _write


def test_check_fails_on_genuine_mismatch(module, fake_repo, monkeypatch):
    """The check must actually fail (return False) when version sources
    disagree -- proving it can gate a release, not just print vacuously."""
    root = fake_repo(
        version="6.5.82",
        src_version="6.5.82",
        pyproject_version="6.5.82",
        package_json_version="6.5.81",  # deliberately mismatched
    )
    monkeypatch.setattr(module, "get_project_root", lambda: root)

    assert module.check_version_consistency() is False


def test_check_passes_when_consistent(module, fake_repo, monkeypatch):
    """The check must pass (return True) when all version sources agree."""
    root = fake_repo(
        version="6.5.82",
        src_version="6.5.82",
        pyproject_version="6.5.82",
        package_json_version="6.5.82",
    )
    monkeypatch.setattr(module, "get_project_root", lambda: root)

    assert module.check_version_consistency() is True


def test_main_exits_nonzero_on_mismatch(module, fake_repo, monkeypatch):
    """main() must sys.exit(1) on mismatch -- this is what makes `make
    pre-publish-checks` (without the old `|| echo` swallow) actually fail."""
    root = fake_repo(
        version="1.0.0",
        src_version="1.0.0",
        pyproject_version="1.0.0",
        package_json_version="2.0.0",
    )
    monkeypatch.setattr(module, "get_project_root", lambda: root)

    with pytest.raises(SystemExit) as exc_info:
        module.main()

    assert exc_info.value.code == 1


def test_main_exits_zero_when_consistent(module, fake_repo, monkeypatch):
    root = fake_repo(
        version="1.0.0",
        src_version="1.0.0",
        pyproject_version="1.0.0",
        package_json_version="1.0.0",
    )
    monkeypatch.setattr(module, "get_project_root", lambda: root)

    with pytest.raises(SystemExit) as exc_info:
        module.main()

    assert exc_info.value.code == 0
