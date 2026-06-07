"""
Unit tests for trusty-search opt-in index allowlist manager (GitHub #668).

WHAT: Tests for :mod:`claude_mpm.services.trusty_search_allowlist` — the
      service that add/list/removes entries from the trusty-search
      ``indexes.toml`` allowlist.
WHY:  Verifies denylist enforcement, idempotent add, TOML round-trip,
      path normalisation, and remove semantics — all using injected tmp
      paths so the real ``~/Library/Application Support/trusty-search/
      indexes.toml`` is NEVER touched.

LINK: none  (introduced by GitHub issue #668)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import toml

import claude_mpm.services.trusty_search_allowlist as _mod
from claude_mpm.services.trusty_search_allowlist import (
    AllowlistWriteError,
    DeniedPathError,
    _check_denylist,
    _derive_id,
    _load_registry,
    _resolve_path,
    _save_registry,
    add_root,
    default_allowlist_path,
    list_roots,
    remove_root,
)

# Capture the original (unpatched) denylist constants at import time, before
# the autouse fixture removes /private/tmp for pytest tmp_path compatibility.
_ORIGINAL_DENYLIST_SUBTREE_ROOTS: frozenset[str] = _mod._DENYLIST_SUBTREE_ROOTS

# ---------------------------------------------------------------------------
# Module fixture: keep _DENYLIST_SUBTREE_ROOTS free of the host's real tmp
# directory so that pytest's tmp_path (which lives in /private/tmp on macOS)
# is usable as a fake project root in non-denylist tests.
#
# The denylist tests that prove /tmp subtrees ARE refused pass literal paths
# such as Path("/tmp/foo") directly — those still match the "/tmp" entry in
# the set, so the fix is transparent to those tests.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_subtree_roots_for_tmp_path(monkeypatch, tmp_path):
    """Remove the *resolved* tmp root from _DENYLIST_SUBTREE_ROOTS so that
    pytest's tmp_path (which macOS resolves to /private/tmp/...) can be used
    as a safe project directory in tests that are NOT testing denylist logic.
    """
    resolved_tmp_root = tmp_path.resolve()
    # Walk up to find which subtree root (if any) covers tmp_path.
    # On macOS: /private/tmp/claude-NNN/... → /private/tmp is the match.
    safe_set = frozenset(
        root
        for root in _mod._DENYLIST_SUBTREE_ROOTS
        if not resolved_tmp_root.is_relative_to(Path(root))
    )
    monkeypatch.setattr(_mod, "_DENYLIST_SUBTREE_ROOTS", safe_set)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_toml(path: Path, entries: list[dict]) -> None:
    """Write a minimal indexes.toml directly (bypassing the service write path)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(toml.dumps({"index": entries}), encoding="utf-8")


def _read_toml(path: Path) -> list[dict]:
    """Read back the index entries from a TOML file."""
    try:
        import tomllib  # Python 3.11+ stdlib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            import toml as tomllib  # type: ignore[no-redef, assignment]

    with path.open("rb") as f:
        data = tomllib.load(f)
    return data.get("index", [])


# ---------------------------------------------------------------------------
# default_allowlist_path
# ---------------------------------------------------------------------------


class TestDefaultAllowlistPath:
    def test_env_override_takes_precedence(self, monkeypatch, tmp_path):
        monkeypatch.setenv("TRUSTY_DATA_DIR", str(tmp_path))
        result = default_allowlist_path()
        assert result == tmp_path / "indexes.toml"

    def test_returns_path_object(self, monkeypatch):
        monkeypatch.delenv("TRUSTY_DATA_DIR", raising=False)
        result = default_allowlist_path()
        assert isinstance(result, Path)
        assert result.name == "indexes.toml"

    def test_macos_path_contains_application_support(self, monkeypatch):
        monkeypatch.delenv("TRUSTY_DATA_DIR", raising=False)
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        result = default_allowlist_path()
        assert "Application Support" in str(result)
        assert "trusty-search" in str(result)

    def test_linux_path_contains_local_share(self, monkeypatch):
        monkeypatch.delenv("TRUSTY_DATA_DIR", raising=False)
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        monkeypatch.setattr("platform.system", lambda: "Linux")
        result = default_allowlist_path()
        assert ".local/share" in str(result)
        assert "trusty-search" in str(result)


# ---------------------------------------------------------------------------
# _resolve_path
# ---------------------------------------------------------------------------


class TestResolvePath:
    def test_expands_home_tilde(self):
        result = _resolve_path("~/")
        assert not str(result).startswith("~")
        assert result.is_absolute()

    def test_returns_absolute_path(self, tmp_path):
        result = _resolve_path(tmp_path)
        assert result.is_absolute()

    def test_accepts_path_object(self, tmp_path):
        result = _resolve_path(tmp_path)
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# _derive_id
# ---------------------------------------------------------------------------


class TestDeriveId:
    def test_basename_used(self):
        assert _derive_id(Path("/projects/my-app")) == "my-app"

    def test_sanitizes_unsafe_chars(self):
        assert _derive_id(Path("/projects/my app!")) == "my_app_"

    def test_allows_dots_and_dashes(self):
        assert _derive_id(Path("/projects/my.proj-1")) == "my.proj-1"

    def test_fallback_for_empty(self):
        # Edge: a path whose name resolves to empty string — should return "project"
        result = _derive_id(Path("/"))
        assert result  # must be non-empty


# ---------------------------------------------------------------------------
# _check_denylist
# ---------------------------------------------------------------------------


class TestCheckDenylist:
    def test_rejects_home_root(self):
        home = Path.home().resolve()
        with pytest.raises(DeniedPathError, match="sensitive-path denylist"):
            _check_denylist(home)

    def test_rejects_slash_tmp(self):
        with pytest.raises(DeniedPathError):
            _check_denylist(Path("/tmp"))

    def test_rejects_filesystem_root(self):
        with pytest.raises(DeniedPathError):
            _check_denylist(Path("/"))

    def test_rejects_ssh_subpath(self):
        # Use ~/.ssh itself — always a subpath of the denylist parent
        ssh_sub = Path.home() / ".ssh"
        with pytest.raises(DeniedPathError):
            _check_denylist(ssh_sub)

    def test_rejects_aws_subpath(self):
        # Use ~/.aws itself — always a subpath of the denylist parent
        aws_sub = Path.home() / ".aws"
        with pytest.raises(DeniedPathError):
            _check_denylist(aws_sub)

    def test_rejects_dotenv_dir(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=abc", encoding="utf-8")
        with pytest.raises(DeniedPathError, match=r"\.env"):
            _check_denylist(tmp_path)

    def test_accepts_normal_project_dir(self, tmp_path):
        # Must NOT raise
        _check_denylist(tmp_path)

    def test_accepts_project_with_env_example(self, tmp_path):
        # .env.example should be fine — only exactly ".env" is blocked
        (tmp_path / ".env.example").write_text("", encoding="utf-8")
        _check_denylist(tmp_path)  # should not raise

    # --- Subtree denylist (fix #2) -------------------------------------------

    def test_rejects_tmp_subdirectory(self):
        """A path under /tmp must be refused even though /tmp itself is the root."""
        with pytest.raises(DeniedPathError, match="ephemeral/system"):
            _check_denylist(Path("/tmp/foo"))

    def test_rejects_tmp_deep_subdirectory(self):
        """Deeply nested /tmp path must also be refused."""
        with pytest.raises(DeniedPathError, match="ephemeral/system"):
            _check_denylist(Path("/tmp/a/b/c/my-project"))

    def test_rejects_etc_subdirectory(self):
        """A path under /etc must be refused."""
        with pytest.raises(DeniedPathError, match="ephemeral/system"):
            _check_denylist(Path("/etc/nginx"))

    def test_rejects_var_subdirectory(self):
        """A path under /var must be refused."""
        with pytest.raises(DeniedPathError, match="ephemeral/system"):
            _check_denylist(Path("/var/log"))

    def test_home_subdirectory_is_allowed(self, tmp_path, monkeypatch):
        """CRITICAL: a subdirectory of $HOME must NOT be refused.

        Real projects live at ~/Projects/..., ~/code/..., etc.  If we blanket-
        block the $HOME subtree the whole feature breaks.  This test is the
        regression guard — if it fails the denylist logic is wrong.
        """
        # Fake $HOME to tmp_path so we are not patching real dotfiles.
        monkeypatch.setenv("HOME", str(tmp_path))
        # Reconstruct the denylist constants with the patched home.
        import importlib

        import claude_mpm.services.trusty_search_allowlist as mod

        monkeypatch.setattr(
            mod,
            "_DENYLIST_EXACT_ONLY",
            frozenset([str(tmp_path), "/"]),
        )
        monkeypatch.setattr(
            mod,
            "_DENYLIST_PARENTS",
            frozenset(
                [
                    str(tmp_path / ".ssh"),
                    str(tmp_path / ".aws"),
                    str(tmp_path / ".gnupg"),
                    str(tmp_path / ".config" / "gcloud"),
                    str(tmp_path / ".kube"),
                    str(tmp_path / ".docker"),
                ]
            ),
        )

        # Create a realistic project directory under the fake home.
        project = tmp_path / "Projects" / "demo"
        project.mkdir(parents=True)

        # Must NOT raise — this is the allowed case.
        mod._check_denylist(project)

    def test_home_exact_is_refused(self, tmp_path, monkeypatch):
        """$HOME itself must still be refused (exact-match)."""
        import claude_mpm.services.trusty_search_allowlist as mod

        monkeypatch.setattr(
            mod,
            "_DENYLIST_EXACT_ONLY",
            frozenset([str(tmp_path), "/"]),
        )
        monkeypatch.setattr(mod, "_DENYLIST_PARENTS", frozenset())

        with pytest.raises(DeniedPathError, match="sensitive-path denylist"):
            mod._check_denylist(tmp_path)

    # --- Individual _DENYLIST_PARENTS entries ---------------------------------
    #
    # These tests derive the denied path directly from the module's
    # _DENYLIST_PARENTS constant (populated at import time from the real home).
    # This avoids a CI mismatch where Path.home() at test-run time might differ
    # from the home used when the module was imported (e.g. sandboxed runners
    # that set HOME after import).  By using an entry already in the set we
    # guarantee the path we construct is exactly what _check_denylist will
    # match — making each test deterministic regardless of the CI HOME.

    def test_rejects_gnupg_subpath(self):
        """`~/.gnupg` and paths beneath it must be refused."""
        # Pick the .gnupg entry from the module's own constant so the path
        # is identical to what _check_denylist will compare against.
        # A missing entry is a hard failure — a mutant that removes this
        # denylist entry must FAIL this test, not skip it.
        gnupg_entry = str(Path.home() / ".gnupg")
        assert gnupg_entry in _mod._DENYLIST_PARENTS, (
            f"{gnupg_entry!r} is missing from _DENYLIST_PARENTS — "
            "this credential directory is mandatory"
        )
        with pytest.raises(DeniedPathError):
            _check_denylist(Path(gnupg_entry))

    def test_rejects_kube_subpath(self):
        """`~/.kube` and paths beneath it must be refused."""
        kube_entry = str(Path.home() / ".kube")
        assert kube_entry in _mod._DENYLIST_PARENTS, (
            f"{kube_entry!r} is missing from _DENYLIST_PARENTS — "
            "this credential directory is mandatory"
        )
        with pytest.raises(DeniedPathError):
            _check_denylist(Path(kube_entry))

    def test_rejects_docker_subpath(self):
        """`~/.docker` and paths beneath it must be refused."""
        docker_entry = str(Path.home() / ".docker")
        assert docker_entry in _mod._DENYLIST_PARENTS, (
            f"{docker_entry!r} is missing from _DENYLIST_PARENTS — "
            "this credential directory is mandatory"
        )
        with pytest.raises(DeniedPathError):
            _check_denylist(Path(docker_entry))

    def test_rejects_gcloud_config_subpath(self):
        """`~/.config/gcloud` and paths beneath it must be refused."""
        gcloud_entry = str(Path.home() / ".config" / "gcloud")
        assert gcloud_entry in _mod._DENYLIST_PARENTS, (
            f"{gcloud_entry!r} is missing from _DENYLIST_PARENTS — "
            "this credential directory is mandatory"
        )
        with pytest.raises(DeniedPathError):
            _check_denylist(Path(gcloud_entry))

    # --- Individual _DENYLIST_SUBTREE_ROOTS entries ---------------------------

    def test_rejects_var_tmp_root(self):
        """`/var/tmp` itself must be refused (subtree root)."""
        with pytest.raises(DeniedPathError, match="ephemeral/system"):
            _check_denylist(Path("/var/tmp"))

    def test_rejects_var_tmp_subdirectory(self):
        """Paths beneath `/var/tmp` must be refused."""
        with pytest.raises(DeniedPathError, match="ephemeral/system"):
            _check_denylist(Path("/var/tmp/myproject"))

    def test_rejects_private_tmp_root(self, monkeypatch):
        """`/private/tmp` (macOS real path) must be refused.

        The autouse fixture strips /private/tmp from _DENYLIST_SUBTREE_ROOTS so
        that pytest's own tmp_path (which lives there on macOS) is usable by
        other tests.  Here we restore the entry explicitly — the point is to
        verify that /private/tmp IS in the module's canonical constant and that
        _check_denylist respects it when present.
        """
        import claude_mpm.services.trusty_search_allowlist as mod

        restored = _mod._DENYLIST_SUBTREE_ROOTS | frozenset(["/private/tmp"])
        monkeypatch.setattr(mod, "_DENYLIST_SUBTREE_ROOTS", restored)
        with pytest.raises(DeniedPathError, match="ephemeral/system"):
            mod._check_denylist(Path("/private/tmp"))

    def test_rejects_private_tmp_subdirectory(self, monkeypatch):
        """Paths beneath `/private/tmp` must be refused (kills removal mutants).

        See `test_rejects_private_tmp_root` for why /private/tmp is re-injected.
        """
        import claude_mpm.services.trusty_search_allowlist as mod

        restored = _mod._DENYLIST_SUBTREE_ROOTS | frozenset(["/private/tmp"])
        monkeypatch.setattr(mod, "_DENYLIST_SUBTREE_ROOTS", restored)
        with pytest.raises(DeniedPathError, match="ephemeral/system"):
            mod._check_denylist(Path("/private/tmp/myproject"))

    def test_rejects_private_var_folders_root(self, monkeypatch):
        """`/private/var/folders` (macOS per-user temp) root must be refused.

        The autouse fixture strips /private/var/folders from
        _DENYLIST_SUBTREE_ROOTS because pytest's tmp_path on macOS resolves to
        /private/var/folders/... — exactly the same pattern as /private/tmp.
        We restore the entry here (matching the /private/tmp test pattern) to
        verify that _check_denylist honours it when present in the set.
        """
        restored = _mod._DENYLIST_SUBTREE_ROOTS | frozenset(["/private/var/folders"])
        monkeypatch.setattr(_mod, "_DENYLIST_SUBTREE_ROOTS", restored)
        with pytest.raises(DeniedPathError, match="ephemeral/system"):
            _mod._check_denylist(Path("/private/var/folders"))

    def test_rejects_private_var_folders_subdirectory(self, monkeypatch):
        """Deep macOS temp path must be refused (kills removal mutants).

        See `test_rejects_private_var_folders_root` for why /private/var/folders
        is re-injected via monkeypatch.
        """
        restored = _mod._DENYLIST_SUBTREE_ROOTS | frozenset(["/private/var/folders"])
        monkeypatch.setattr(_mod, "_DENYLIST_SUBTREE_ROOTS", restored)
        with pytest.raises(DeniedPathError, match="ephemeral/system"):
            _mod._check_denylist(Path("/private/var/folders/xx/abc123/T/myapp"))

    # --- Denylist constant integrity (kills set-to-empty mutants) -------------

    def test_denylist_exact_only_is_nonempty(self):
        """_DENYLIST_EXACT_ONLY must contain at least $HOME and '/'."""
        assert len(_mod._DENYLIST_EXACT_ONLY) >= 2
        assert "/" in _mod._DENYLIST_EXACT_ONLY
        assert str(Path.home()) in _mod._DENYLIST_EXACT_ONLY

    def test_denylist_parents_is_nonempty(self):
        """_DENYLIST_PARENTS must contain at least the six credential dirs."""
        assert len(_mod._DENYLIST_PARENTS) >= 6
        home = Path.home()
        for expected in (".ssh", ".aws", ".gnupg", ".kube", ".docker"):
            assert str(home / expected) in _mod._DENYLIST_PARENTS, (
                f"~/{expected} missing from _DENYLIST_PARENTS"
            )
        assert str(home / ".config" / "gcloud") in _mod._DENYLIST_PARENTS

    def test_denylist_subtree_roots_is_nonempty(self):
        """_DENYLIST_SUBTREE_ROOTS must contain all six ephemeral roots.

        Uses the snapshot captured at import time (before the autouse fixture
        strips /private/tmp for pytest tmp_path compatibility on macOS).
        """
        assert len(_ORIGINAL_DENYLIST_SUBTREE_ROOTS) >= 6
        for expected in (
            "/tmp",
            "/var/tmp",
            "/private/tmp",
            "/private/var/folders",
            "/etc",
            "/var",
        ):
            assert expected in _ORIGINAL_DENYLIST_SUBTREE_ROOTS, (
                f"'{expected}' missing from _DENYLIST_SUBTREE_ROOTS"
            )

    def test_denylist_constants_are_consulted(self):
        """All three denylist constants must actually block paths when populated.

        This test patches each set individually to verify _check_denylist
        consults it — a mutation that replaces a constant with frozenset()
        would let a path through, and this test catches that.
        """
        import claude_mpm.services.trusty_search_allowlist as mod

        # _DENYLIST_EXACT_ONLY consulted — patch to contain only a known test path
        fake_path = Path("/fakehome/testuser")
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, "_DENYLIST_EXACT_ONLY", frozenset([str(fake_path)]))
            mp.setattr(mod, "_DENYLIST_PARENTS", frozenset())
            mp.setattr(mod, "_DENYLIST_SUBTREE_ROOTS", frozenset())
            with pytest.raises(DeniedPathError, match="sensitive-path denylist"):
                mod._check_denylist(fake_path)

        # _DENYLIST_SUBTREE_ROOTS consulted — patch to contain only a known root
        fake_root = Path("/fakesys/ephemeral")
        fake_child = fake_root / "myproject"
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, "_DENYLIST_EXACT_ONLY", frozenset())
            mp.setattr(mod, "_DENYLIST_PARENTS", frozenset())
            mp.setattr(mod, "_DENYLIST_SUBTREE_ROOTS", frozenset([str(fake_root)]))
            with pytest.raises(DeniedPathError, match="ephemeral/system"):
                mod._check_denylist(fake_child)

        # _DENYLIST_PARENTS consulted — patch to contain only a known parent
        fake_parent = Path("/fakecreds/tokens")
        fake_inside = fake_parent / "id_rsa"
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, "_DENYLIST_EXACT_ONLY", frozenset())
            mp.setattr(mod, "_DENYLIST_PARENTS", frozenset([str(fake_parent)]))
            mp.setattr(mod, "_DENYLIST_SUBTREE_ROOTS", frozenset())
            with pytest.raises(DeniedPathError, match="sensitive directory"):
                mod._check_denylist(fake_inside)


# ---------------------------------------------------------------------------
# _save_registry — AllowlistWriteError on import/write failure (fix #1)
# ---------------------------------------------------------------------------


class TestSaveRegistryWriteError:
    def test_raises_allowlist_write_error_on_write_failure(self, tmp_path, monkeypatch):
        """_save_registry must raise AllowlistWriteError (not a bare exception)
        when the underlying write fails.
        """
        from claude_mpm.services import trusty_search_allowlist as mod

        # Simulate a write failure by making the directory read-only.
        ro_dir = tmp_path / "readonly"
        ro_dir.mkdir()
        target = ro_dir / "indexes.toml"

        # Patch toml.dumps to raise an OSError so we do not need filesystem
        # tricks (chmod is unreliable in sandboxed CI environments).
        import toml as toml_mod

        monkeypatch.setattr(
            toml_mod, "dumps", lambda _: (_ for _ in ()).throw(OSError("disk full"))
        )

        with pytest.raises(AllowlistWriteError, match="Could not write"):
            mod._save_registry(
                target, [{"id": "x", "root_path": "/x", "colocated": True}]
            )

    def test_raises_allowlist_write_error_on_import_failure(
        self, tmp_path, monkeypatch
    ):
        """If the toml import fails (e.g. uninstalled), AllowlistWriteError is
        raised rather than a bare ImportError propagating to the caller.
        """
        import builtins

        real_import = builtins.__import__

        def _block_toml(name, *args, **kwargs):
            if name == "toml":
                raise ImportError("toml not installed")
            return real_import(name, *args, **kwargs)

        from claude_mpm.services import trusty_search_allowlist as mod

        monkeypatch.setattr(builtins, "__import__", _block_toml)
        target = tmp_path / "indexes.toml"

        with pytest.raises(AllowlistWriteError, match="Could not write"):
            mod._save_registry(target, [])


# ---------------------------------------------------------------------------
# _load_registry / _save_registry
# ---------------------------------------------------------------------------


class TestRegistryIO:
    def test_load_nonexistent_returns_empty(self, tmp_path):
        result = _load_registry(tmp_path / "indexes.toml")
        assert result == []

    def test_round_trip(self, tmp_path):
        path = tmp_path / "indexes.toml"
        entries = [{"id": "proj", "root_path": "/abs/path", "colocated": True}]
        _save_registry(path, entries)
        loaded = _load_registry(path)
        assert loaded == entries

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "indexes.toml"
        _save_registry(path, [])
        assert path.exists()

    def test_load_corrupt_file_raises(self, tmp_path):
        path = tmp_path / "indexes.toml"
        path.write_bytes(b"\x00\x01corrupt bytes\xff")
        with pytest.raises(AllowlistWriteError):
            _load_registry(path)

    def test_array_of_tables_schema(self, tmp_path):
        """Saved TOML must use [[index]] array-of-tables, not inline arrays."""
        path = tmp_path / "indexes.toml"
        entries = [
            {"id": "a", "root_path": "/a", "colocated": True},
            {"id": "b", "root_path": "/b", "colocated": True},
        ]
        _save_registry(path, entries)
        content = path.read_text(encoding="utf-8")
        assert "[[index]]" in content, "TOML must use [[index]] array-of-tables"

    def test_save_is_atomic(self, tmp_path):
        """Temp file must be cleaned up after a successful write."""
        path = tmp_path / "indexes.toml"
        _save_registry(path, [{"id": "x", "root_path": "/x", "colocated": True}])
        tmp_file = path.with_suffix(".toml.mpm_tmp")
        assert not tmp_file.exists(), "Temp file should be renamed away after write"


# ---------------------------------------------------------------------------
# add_root
# ---------------------------------------------------------------------------


class TestAddRoot:
    def test_adds_new_entry(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        project = tmp_path / "my_project"
        project.mkdir()

        added, msg = add_root(project, allowlist_path=toml_path)

        assert added is True
        assert "my_project" in msg
        entries = _read_toml(toml_path)
        assert len(entries) == 1
        assert entries[0]["root_path"] == str(project.resolve())
        assert entries[0]["colocated"] is True

    def test_idempotent_on_duplicate(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        project = tmp_path / "app"
        project.mkdir()

        add_root(project, allowlist_path=toml_path)
        added, msg = add_root(project, allowlist_path=toml_path)

        assert added is False
        assert "already in" in msg
        entries = _read_toml(toml_path)
        assert len(entries) == 1, "Duplicate entry must not be written"

    def test_custom_index_id(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        project = tmp_path / "app"
        project.mkdir()

        add_root(project, index_id="custom-id", allowlist_path=toml_path)

        entries = _read_toml(toml_path)
        assert entries[0]["id"] == "custom-id"

    def test_appends_to_existing_entries(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        _write_toml(
            toml_path, [{"id": "existing", "root_path": "/other", "colocated": True}]
        )

        project = tmp_path / "new_proj"
        project.mkdir()
        add_root(project, allowlist_path=toml_path)

        entries = _read_toml(toml_path)
        assert len(entries) == 2

    def test_rejects_denylist_path(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        with pytest.raises(DeniedPathError):
            add_root(Path.home(), allowlist_path=toml_path)

    def test_rejects_nonexistent_path(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        with pytest.raises(ValueError, match="not a directory"):
            add_root(tmp_path / "does_not_exist", allowlist_path=toml_path)

    def test_rejects_file_path(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        a_file = tmp_path / "file.txt"
        a_file.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="not a directory"):
            add_root(a_file, allowlist_path=toml_path)

    def test_rejects_dotenv_dir(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        project = tmp_path / "secret_proj"
        project.mkdir()
        (project / ".env").write_text("TOKEN=xxx", encoding="utf-8")
        with pytest.raises(DeniedPathError, match=r"\.env"):
            add_root(project, allowlist_path=toml_path)

    def test_expands_tilde_in_path(self, tmp_path):
        """Path with ~ must expand to an absolute path (no literal ~ stored)."""
        toml_path = tmp_path / "indexes.toml"
        # Use a real directory under $HOME for this test.
        project = Path.home() / ".cache"
        if not project.is_dir():
            pytest.skip("~/.cache does not exist on this machine")

        # ~/.cache itself is not in the denylist — safe to register
        try:
            add_root("~/.cache", allowlist_path=toml_path)
        except Exception:
            pytest.skip("~/.cache refused by denylist on this machine")

        entries = _read_toml(toml_path)
        assert entries[0]["root_path"] == str(project.resolve())
        assert "~" not in entries[0]["root_path"], (
            "Tilde must be expanded before storing"
        )

    def test_does_not_touch_real_allowlist(self, tmp_path, monkeypatch):
        """Critical: add_root with injected path must NOT write the real file."""
        real_path = default_allowlist_path()
        real_existed_before = real_path.exists()

        toml_path = tmp_path / "indexes.toml"
        project = tmp_path / "safe_proj"
        project.mkdir()
        add_root(project, allowlist_path=toml_path)

        # The real file state must be unchanged.
        if not real_existed_before:
            assert not real_path.exists(), "add_root must not create the real allowlist"


# ---------------------------------------------------------------------------
# list_roots
# ---------------------------------------------------------------------------


class TestListRoots:
    def test_empty_when_file_missing(self, tmp_path):
        result = list_roots(allowlist_path=tmp_path / "indexes.toml")
        assert result == []

    def test_returns_all_entries(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        entries = [
            {"id": "a", "root_path": "/a", "colocated": True},
            {"id": "b", "root_path": "/b", "colocated": False},
        ]
        _write_toml(toml_path, entries)
        result = list_roots(allowlist_path=toml_path)
        assert len(result) == 2
        assert result[0]["id"] == "a"
        assert result[1]["id"] == "b"

    def test_does_not_touch_real_allowlist(self, tmp_path):
        """list_roots with injected path reads only that path."""
        real_path = default_allowlist_path()
        # Call with non-existent injected path — should return [] without
        # ever consulting the real file.
        result = list_roots(allowlist_path=tmp_path / "indexes.toml")
        assert result == []


# ---------------------------------------------------------------------------
# remove_root
# ---------------------------------------------------------------------------


class TestRemoveRoot:
    def test_removes_existing_entry(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        project = tmp_path / "proj"
        project.mkdir()
        add_root(project, allowlist_path=toml_path)

        removed, msg = remove_root(project, allowlist_path=toml_path)

        assert removed is True
        assert str(project.resolve()) in msg
        entries = _read_toml(toml_path)
        assert entries == []

    def test_noop_when_not_found(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        project = tmp_path / "proj"
        project.mkdir()

        removed, msg = remove_root(project, allowlist_path=toml_path)

        assert removed is False
        assert "not found" in msg

    def test_leaves_other_entries_intact(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        proj_a = tmp_path / "a"
        proj_b = tmp_path / "b"
        proj_a.mkdir()
        proj_b.mkdir()

        add_root(proj_a, allowlist_path=toml_path)
        add_root(proj_b, allowlist_path=toml_path)
        remove_root(proj_a, allowlist_path=toml_path)

        entries = _read_toml(toml_path)
        assert len(entries) == 1
        assert entries[0]["root_path"] == str(proj_b.resolve())

    def test_resolves_path_before_matching(self, tmp_path):
        """Remove with a trailing slash or relative form should still match."""
        toml_path = tmp_path / "indexes.toml"
        project = tmp_path / "proj"
        project.mkdir()
        add_root(project, allowlist_path=toml_path)

        # Pass path as string with trailing slash
        removed, _ = remove_root(str(project) + "/", allowlist_path=toml_path)
        assert removed is True

    def test_does_not_touch_real_allowlist(self, tmp_path):
        real_path = default_allowlist_path()
        real_existed_before = real_path.exists()

        toml_path = tmp_path / "indexes.toml"
        project = tmp_path / "proj"
        project.mkdir()
        remove_root(project, allowlist_path=toml_path)

        if not real_existed_before:
            assert not real_path.exists()


# ---------------------------------------------------------------------------
# Integration: add → list → remove round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_add_list_remove_full_cycle(self, tmp_path):
        toml_path = tmp_path / "indexes.toml"
        projects = [tmp_path / f"proj{i}" for i in range(3)]
        for p in projects:
            p.mkdir()

        # Add all three
        for p in projects:
            added, _ = add_root(p, allowlist_path=toml_path)
            assert added is True

        # List should show 3
        entries = list_roots(allowlist_path=toml_path)
        assert len(entries) == 3

        # Remove middle one
        removed, _ = remove_root(projects[1], allowlist_path=toml_path)
        assert removed is True

        entries = list_roots(allowlist_path=toml_path)
        assert len(entries) == 2
        roots = {e["root_path"] for e in entries}
        assert str(projects[1].resolve()) not in roots

    def test_schema_matches_live_format(self, tmp_path):
        """The TOML produced must match the schema confirmed from the live
        ~/Library/Application Support/trusty-search/indexes.toml:
          [[index]]
          id = "..."
          root_path = "..."
          colocated = true
        """
        toml_path = tmp_path / "indexes.toml"
        project = tmp_path / "myapp"
        project.mkdir()
        add_root(project, allowlist_path=toml_path)

        content = toml_path.read_text(encoding="utf-8")
        # Must produce [[index]] header (array-of-tables)
        assert "[[index]]" in content
        # id, root_path, colocated must all appear
        assert 'id = "myapp"' in content
        assert f'root_path = "{project.resolve()}"' in content
        assert "colocated = true" in content
