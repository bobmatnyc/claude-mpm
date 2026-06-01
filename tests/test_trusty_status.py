"""Unit tests for trusty daemon connection status (GitHub #598).

Covers the scoped design after the presence-signal fix:
* not opted in (no .mcp.json entry, no http_addr file) → suppressed (empty
  line) AND the health probe is never called (zero cost)
* present via .mcp.json entry ONLY (no http_addr file, binary name irrelevant)
  + health OK → ``on`` line — this is the exact regression that was broken when
  the gate was ``shutil.which`` and the launched binary was a bridge/wrapper
* present via http_addr file ONLY → probed
* present + health fail + in .mcp.json → ``configured`` / ``not running``
* present + health fail + not in .mcp.json → ``not_running`` / ``not running``
* NO ``/ui`` substring ever appears
* the ≤0.2s timeout is actually passed to the probe
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.claude_mpm.services import trusty_status
from src.claude_mpm.services.trusty_status import (
    _HEALTH_TIMEOUT_S,
    get_trusty_status,
)


@pytest.fixture(autouse=True)
def _clear_health_cache():
    """Ensure the module-level health cache never leaks between tests."""
    trusty_status._HEALTH_CACHE.clear()
    yield
    trusty_status._HEALTH_CACHE.clear()


def _point_home(monkeypatch, tmp_path: Path) -> None:
    """Point ``Path.home()`` at an isolated tmp dir (no discovery files yet)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)


def _point_cwd(monkeypatch, tmp_path: Path) -> None:
    """Point ``Path.cwd()`` at an isolated tmp dir (no .mcp.json yet)."""
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)


def _write_addr_file(tmp_path: Path, service: str, addr: str) -> None:
    """Write a ``~/.trusty-<service>/http_addr`` discovery file under tmp_path."""
    addr_dir = tmp_path / f".{service}"
    addr_dir.mkdir(parents=True, exist_ok=True)
    (addr_dir / "http_addr").write_text(addr, encoding="utf-8")


def _write_mcp_json(tmp_path: Path, *services: str) -> None:
    """Write a CWD ``.mcp.json`` listing ``services`` in ``mcpServers``.

    Each command intentionally uses a NON-matching binary name (a bridge) to
    prove the presence signal does not depend on the binary name.
    """
    import json

    servers = {svc: {"command": f"{svc}-mcp-bridge"} for svc in services}
    (tmp_path / ".mcp.json").write_text(
        json.dumps({"mcpServers": servers}), encoding="utf-8"
    )


class TestNotOptedIn:
    """Cold-path short-circuit: no .mcp.json entry AND no http_addr → nothing."""

    @pytest.mark.parametrize("service", ["trusty-memory", "trusty-search"])
    def test_neither_signal_renders_nothing(self, monkeypatch, tmp_path, service):
        # Isolated home (no discovery file) and isolated cwd (no .mcp.json).
        _point_home(monkeypatch, tmp_path / "home")
        _point_cwd(monkeypatch, tmp_path / "proj")
        (tmp_path / "home").mkdir()
        (tmp_path / "proj").mkdir()

        state, line = get_trusty_status(service)
        assert state == "absent"
        assert line == ""

    def test_neither_signal_does_not_probe_health(self, monkeypatch, tmp_path):
        """No presence signal → no HTTP probe should happen (zero cost)."""
        _point_home(monkeypatch, tmp_path / "home")
        _point_cwd(monkeypatch, tmp_path / "proj")
        (tmp_path / "home").mkdir()
        (tmp_path / "proj").mkdir()

        def _boom(*_args, **_kwargs):
            raise AssertionError("health check must not run when not opted in")

        monkeypatch.setattr(trusty_status, "_health_check", _boom)
        state, line = get_trusty_status("trusty-memory")
        assert (state, line) == ("absent", "")


class TestPresentViaMcpJsonOnly:
    """Regression for #598: present via .mcp.json with NO http_addr file.

    Previously suppressed because the gate was ``shutil.which("trusty-memory")``
    while the launched binary is ``trusty-memory-mcp-bridge`` (name mismatch).
    """

    def test_memory_mcp_only_health_ok_renders_on(self, monkeypatch, tmp_path):
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)  # no http_addr file written
        _point_cwd(monkeypatch, proj)
        _write_mcp_json(proj, "trusty-memory")  # binary name is a bridge, not matching
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: True)
        monkeypatch.setattr(trusty_status, "_palace_name", lambda: "my-palace")

        state, line = get_trusty_status("trusty-memory")
        assert state == "on"
        assert "trusty-memory: on" in line
        # Falls back to the default port since there is no discovery file.
        assert "127.0.0.1:7070" in line
        assert "palace: my-palace" in line
        assert "/ui" not in line

    def test_memory_mcp_only_no_http_addr_file_on_disk(self, monkeypatch, tmp_path):
        """Guard: the regression scenario truly has NO discovery file."""
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_mcp_json(proj, "trusty-memory")

        assert not (home / ".trusty-memory" / "http_addr").exists()
        assert trusty_status._is_present("trusty-memory") is True


class TestPresentViaHttpAddrOnly:
    """Present via http_addr discovery file only (no .mcp.json entry)."""

    def test_search_addr_only_health_ok_renders_on(self, monkeypatch, tmp_path):
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)  # no .mcp.json
        _write_addr_file(home, "trusty-search", "localhost:7878")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: True)

        state, line = get_trusty_status("trusty-search")
        assert state == "on"
        assert "trusty-search: on" in line
        assert "localhost:7878" in line
        assert "palace" not in line
        assert "/ui" not in line

    def test_addr_only_uses_actual_dynamic_port(self, monkeypatch, tmp_path):
        """The actual host:port from http_addr is used, not the default port."""
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_addr_file(home, "trusty-search", "127.0.0.1:54321")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: True)

        state, line = get_trusty_status("trusty-search")
        assert state == "on"
        assert "127.0.0.1:54321" in line
        assert "7878" not in line

    def test_health_probed_against_correct_base_url(self, monkeypatch, tmp_path):
        """The /health endpoint is built from the discovered base URL."""
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_addr_file(home, "trusty-memory", "127.0.0.1:9999")

        seen: dict[str, str] = {}

        def _capture(base_url: str) -> bool:
            seen["base_url"] = base_url
            return True

        monkeypatch.setattr(trusty_status, "_health_check", _capture)
        monkeypatch.setattr(trusty_status, "_palace_name", lambda: "p")
        get_trusty_status("trusty-memory")
        assert seen["base_url"] == "http://127.0.0.1:9999"


class TestHealthFail:
    """Present + /health fail → ``not running``."""

    def test_fail_in_mcp_json_state_configured(self, monkeypatch, tmp_path):
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_mcp_json(proj, "trusty-memory")
        _write_addr_file(home, "trusty-memory", "localhost:7070")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: False)

        state, line = get_trusty_status("trusty-memory")
        assert state == "configured"
        assert "not running" in line
        assert "(start: trusty-memory ...)" in line
        assert "/ui" not in line

    def test_fail_addr_only_not_in_mcp_json_still_not_running(
        self, monkeypatch, tmp_path
    ):
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)  # no .mcp.json → not configured
        _write_addr_file(home, "trusty-search", "localhost:7878")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: False)

        state, line = get_trusty_status("trusty-search")
        assert state == "not_running"
        assert "not running" in line
        assert "(start: trusty-search serve)" in line
        assert "off" not in line  # never a bare "off" line
        assert "/ui" not in line


class TestPresenceSignal:
    """:func:`_is_present` OR semantics across the two filesystem signals."""

    def test_present_via_mcp_only(self, monkeypatch, tmp_path):
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_mcp_json(proj, "trusty-memory")
        assert trusty_status._is_present("trusty-memory") is True
        assert trusty_status._is_present("trusty-search") is False

    def test_present_via_addr_only(self, monkeypatch, tmp_path):
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_addr_file(home, "trusty-search", "localhost:7878")
        assert trusty_status._is_present("trusty-search") is True
        assert trusty_status._is_present("trusty-memory") is False

    def test_absent_when_neither(self, monkeypatch, tmp_path):
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        assert trusty_status._is_present("trusty-memory") is False
        assert trusty_status._is_present("trusty-search") is False


class TestMcpConfigRead:
    """.mcp.json read behavior (signal #1 helper)."""

    def test_configured_when_present(self, monkeypatch, tmp_path):
        _point_cwd(monkeypatch, tmp_path)
        (tmp_path / ".mcp.json").write_text(
            '{"mcpServers": {"trusty-memory": {"command": "trusty-memory-mcp-bridge"}}}',
            encoding="utf-8",
        )
        assert trusty_status._is_configured_in_mcp("trusty-memory") is True
        assert trusty_status._is_configured_in_mcp("trusty-search") is False

    def test_not_configured_when_missing_file(self, monkeypatch, tmp_path):
        _point_cwd(monkeypatch, tmp_path)
        assert trusty_status._is_configured_in_mcp("trusty-memory") is False

    def test_not_configured_when_malformed_json(self, monkeypatch, tmp_path):
        _point_cwd(monkeypatch, tmp_path)
        (tmp_path / ".mcp.json").write_text("{ not valid json", encoding="utf-8")
        assert trusty_status._is_configured_in_mcp("trusty-memory") is False


class TestHealthTimeout:
    """The probe must use a hard ≤0.2s timeout."""

    def test_timeout_constant_is_at_most_200ms(self):
        assert _HEALTH_TIMEOUT_S <= 0.2

    def test_timeout_passed_to_urlopen(self, monkeypatch):
        """_health_check passes _HEALTH_TIMEOUT_S to urllib.request.urlopen."""
        import urllib.request

        seen: dict[str, float] = {}

        class _FakeResp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

        def _fake_urlopen(_req, timeout=None):
            seen["timeout"] = timeout
            return _FakeResp()

        monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
        assert trusty_status._health_check("http://127.0.0.1:7070") is True
        assert seen["timeout"] == _HEALTH_TIMEOUT_S
        assert seen["timeout"] <= 0.2

    def test_health_check_never_raises(self, monkeypatch):
        import urllib.request

        def _boom(*_a, **_k):
            raise OSError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", _boom)
        # Must swallow the error and return False, not raise.
        assert trusty_status._health_check("http://127.0.0.1:7070") is False


class TestHealthCache:
    """Probe result is cached by the http_addr file mtime."""

    def test_repeat_probe_is_cached(self, monkeypatch, tmp_path):
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_addr_file(home, "trusty-search", "localhost:7878")

        calls = {"n": 0}

        def _counting(_url: str) -> bool:
            calls["n"] += 1
            return True

        monkeypatch.setattr(trusty_status, "_health_check", _counting)
        get_trusty_status("trusty-search")
        get_trusty_status("trusty-search")
        # Same mtime → second call served from cache.
        assert calls["n"] == 1


class TestNoUiSubstring:
    """Guarantee: no rendered line ever contains '/ui'."""

    @pytest.mark.parametrize("service", ["trusty-memory", "trusty-search"])
    @pytest.mark.parametrize("healthy", [True, False])
    def test_no_ui_in_any_state(self, monkeypatch, tmp_path, service, healthy):
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_addr_file(home, service, "localhost:7070")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: healthy)
        monkeypatch.setattr(trusty_status, "_palace_name", lambda: "p")
        _, line = get_trusty_status(service)
        assert "/ui" not in line
