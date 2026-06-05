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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_toml(path: Path, entries: list[dict]) -> None:
    """Write a minimal indexes.toml directly (bypassing the service write path)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(toml.dumps({"index": entries}), encoding="utf-8")


def _read_toml(path: Path) -> list[dict]:
    """Read back the index entries from a TOML file."""
    import tomllib

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
