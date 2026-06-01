"""Unit tests for trusty daemon connection status (GitHub #598).

Covers the scoped design:
* binary absent → suppressed (empty line)
* binary present + health OK → ``on`` line with correct host:port (+ palace for memory)
* binary present + health fail + in .mcp.json → ``not running``
* binary present + health fail + not in .mcp.json → ``not running``
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


def _setup_addr_file(monkeypatch, tmp_path: Path, service: str, addr: str) -> None:
    """Point ``Path.home()`` at tmp_path and write a discovery file."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    addr_dir = tmp_path / f".{service}"
    addr_dir.mkdir(parents=True, exist_ok=True)
    (addr_dir / "http_addr").write_text(addr, encoding="utf-8")


class TestBinaryAbsent:
    """Cold-path short-circuit: binary not on PATH renders nothing."""

    def test_memory_absent_renders_nothing(self, monkeypatch):
        monkeypatch.setattr(trusty_status.shutil, "which", lambda _: None)
        state, line = get_trusty_status("trusty-memory")
        assert state == "absent"
        assert line == ""

    def test_search_absent_renders_nothing(self, monkeypatch):
        monkeypatch.setattr(trusty_status.shutil, "which", lambda _: None)
        state, line = get_trusty_status("trusty-search")
        assert state == "absent"
        assert line == ""

    def test_absent_does_not_probe_health(self, monkeypatch):
        """When binary absent, no HTTP probe should happen (zero cost)."""
        monkeypatch.setattr(trusty_status.shutil, "which", lambda _: None)

        def _boom(*_args, **_kwargs):
            raise AssertionError("health check must not run when binary absent")

        monkeypatch.setattr(trusty_status, "_health_check", _boom)
        state, line = get_trusty_status("trusty-memory")
        assert (state, line) == ("absent", "")


class TestHealthOk:
    """Binary present + /health OK → ``on`` line."""

    def test_memory_on_includes_host_port_and_palace(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            trusty_status.shutil, "which", lambda _: "/usr/bin/trusty-memory"
        )
        _setup_addr_file(monkeypatch, tmp_path, "trusty-memory", "localhost:7070")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: True)
        monkeypatch.setattr(trusty_status, "_palace_name", lambda: "my-palace")

        state, line = get_trusty_status("trusty-memory")
        assert state == "on"
        assert "trusty-memory: on" in line
        assert "localhost:7070" in line
        assert "palace: my-palace" in line
        assert "/ui" not in line

    def test_search_on_includes_host_port_no_palace(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            trusty_status.shutil, "which", lambda _: "/usr/bin/trusty-search"
        )
        _setup_addr_file(monkeypatch, tmp_path, "trusty-search", "localhost:7878")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: True)

        state, line = get_trusty_status("trusty-search")
        assert state == "on"
        assert "trusty-search: on" in line
        assert "localhost:7878" in line
        assert "palace" not in line
        assert "/ui" not in line

    def test_on_uses_actual_dynamic_port(self, monkeypatch, tmp_path):
        """The actual host:port from http_addr is used, not the default port."""
        monkeypatch.setattr(
            trusty_status.shutil, "which", lambda _: "/usr/bin/trusty-search"
        )
        _setup_addr_file(monkeypatch, tmp_path, "trusty-search", "127.0.0.1:54321")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: True)

        state, line = get_trusty_status("trusty-search")
        assert state == "on"
        assert "127.0.0.1:54321" in line
        assert "7878" not in line

    def test_health_probed_against_correct_base_url(self, monkeypatch, tmp_path):
        """The /health endpoint is built from the discovered base URL."""
        monkeypatch.setattr(
            trusty_status.shutil, "which", lambda _: "/usr/bin/trusty-memory"
        )
        _setup_addr_file(monkeypatch, tmp_path, "trusty-memory", "127.0.0.1:9999")

        seen: dict[str, str] = {}

        def _capture(base_url: str) -> bool:
            seen["base_url"] = base_url
            return True

        monkeypatch.setattr(trusty_status, "_health_check", _capture)
        monkeypatch.setattr(trusty_status, "_palace_name", lambda: "p")
        get_trusty_status("trusty-memory")
        assert seen["base_url"] == "http://127.0.0.1:9999"


class TestHealthFail:
    """Binary present + /health fail → ``not running``."""

    def test_fail_in_mcp_json_state_configured(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            trusty_status.shutil, "which", lambda _: "/usr/bin/trusty-memory"
        )
        _setup_addr_file(monkeypatch, tmp_path, "trusty-memory", "localhost:7070")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: False)
        monkeypatch.setattr(trusty_status, "_is_configured_in_mcp", lambda _s: True)

        state, line = get_trusty_status("trusty-memory")
        assert state == "configured"
        assert "not running" in line
        assert "(start: trusty-memory ...)" in line
        assert "/ui" not in line

    def test_fail_not_in_mcp_json_still_not_running(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            trusty_status.shutil, "which", lambda _: "/usr/bin/trusty-search"
        )
        _setup_addr_file(monkeypatch, tmp_path, "trusty-search", "localhost:7878")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: False)
        monkeypatch.setattr(trusty_status, "_is_configured_in_mcp", lambda _s: False)

        state, line = get_trusty_status("trusty-search")
        assert state == "not_running"
        assert "not running" in line
        assert "(start: trusty-search serve)" in line
        assert "off" not in line  # never a bare "off" line
        assert "/ui" not in line


class TestMcpConfigRead:
    """.mcp.json read behavior."""

    def test_configured_when_present(self, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        (tmp_path / ".mcp.json").write_text(
            '{"mcpServers": {"trusty-memory": {"command": "x"}}}',
            encoding="utf-8",
        )
        assert trusty_status._is_configured_in_mcp("trusty-memory") is True
        assert trusty_status._is_configured_in_mcp("trusty-search") is False

    def test_not_configured_when_missing_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert trusty_status._is_configured_in_mcp("trusty-memory") is False

    def test_not_configured_when_malformed_json(self, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
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
        monkeypatch.setattr(
            trusty_status.shutil, "which", lambda _: "/usr/bin/trusty-search"
        )
        _setup_addr_file(monkeypatch, tmp_path, "trusty-search", "localhost:7878")

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
        monkeypatch.setattr(
            trusty_status.shutil, "which", lambda _: f"/usr/bin/{service}"
        )
        _setup_addr_file(monkeypatch, tmp_path, service, "localhost:7070")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: healthy)
        monkeypatch.setattr(trusty_status, "_palace_name", lambda: "p")
        monkeypatch.setattr(trusty_status, "_is_configured_in_mcp", lambda _s: False)
        _, line = get_trusty_status(service)
        assert "/ui" not in line
