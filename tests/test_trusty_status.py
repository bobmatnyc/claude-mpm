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

Palace existence verification (#598 option 1):
* memory ``on`` + palace EXISTS → ``palace: <name>`` (no ``(not created)``)
* memory ``on`` + palace MISSING → ``palace: <name> (not created)``
* palaces endpoint errors/times out → fail-safe: show the bare name WITHOUT
  ``(not created)`` (only a successful response that definitively lacks the
  palace yields the suffix — avoids false negatives)
* the existence probe uses the same ≤0.2s timeout and runs ONLY after a
  successful health check (never when not running / absent, never for search)
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
    """Ensure the module-level caches never leak between tests."""
    trusty_status._HEALTH_CACHE.clear()
    trusty_status._PALACE_CACHE.clear()
    yield
    trusty_status._HEALTH_CACHE.clear()
    trusty_status._PALACE_CACHE.clear()


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
        monkeypatch.setattr(trusty_status, "_palace_exists", lambda *_a: True)

        state, line = get_trusty_status("trusty-memory")
        assert state == "on"
        assert "trusty-memory: on" in line
        # Falls back to the default port since there is no discovery file.
        assert "127.0.0.1:7070" in line
        assert "palace: my-palace" in line
        assert "(not created)" not in line
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
        monkeypatch.setattr(trusty_status, "_palace_exists", lambda *_a: True)
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
        monkeypatch.setattr(trusty_status, "_palace_exists", lambda *_a: True)
        _, line = get_trusty_status(service)
        assert "/ui" not in line


# ---------------------------------------------------------------------------
# Palace existence verification (#598 option 1)
# ---------------------------------------------------------------------------


def _fake_palaces_resp(status: int, body: str):
    """Build a context-manager fake urllib response with ``status``/``body``."""

    class _Resp:
        def __init__(self) -> None:
            self.status = status

        def read(self) -> bytes:
            return body.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    return _Resp()


class TestPalaceExistsHelper:
    """:func:`_palace_exists` parses the confirmed /api/v1/palaces shape.

    Confirmed shape (trusty-memory daemon ``GET /api/v1/palaces`` →
    ``Json<Vec<PalaceInfo>>``): a top-level JSON array of objects, each with
    ``id`` and ``name`` string fields. Defensively we also accept an
    ``{"palaces": [...]}`` wrapper and bare-string entries.
    """

    def _patch_urlopen(self, monkeypatch, status: int, body: str) -> dict:
        import urllib.request

        seen: dict[str, object] = {}

        def _fake_urlopen(_req, timeout=None):
            seen["timeout"] = timeout
            return _fake_palaces_resp(status, body)

        monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
        return seen

    def test_top_level_array_of_objects_match_by_name(self, monkeypatch):
        body = '[{"id": "claude-mpm", "name": "claude-mpm"}]'
        self._patch_urlopen(monkeypatch, 200, body)
        assert (
            trusty_status._palace_exists("http://127.0.0.1:7070", "claude-mpm") is True
        )

    def test_match_is_case_insensitive(self, monkeypatch):
        body = '[{"id": "Claude-MPM", "name": "Claude-MPM"}]'
        self._patch_urlopen(monkeypatch, 200, body)
        assert (
            trusty_status._palace_exists("http://127.0.0.1:7070", "claude-mpm") is True
        )

    def test_match_by_id_field(self, monkeypatch):
        # name differs but id matches the resolved name.
        body = '[{"id": "claude-mpm", "name": "Some Display Name"}]'
        self._patch_urlopen(monkeypatch, 200, body)
        assert (
            trusty_status._palace_exists("http://127.0.0.1:7070", "claude-mpm") is True
        )

    def test_wrapped_palaces_key_with_string_entries(self, monkeypatch):
        # Defensive: the MCP palace_list projection emits bare strings.
        body = '{"palaces": ["claude-mpm", "other"]}'
        self._patch_urlopen(monkeypatch, 200, body)
        assert (
            trusty_status._palace_exists("http://127.0.0.1:7070", "claude-mpm") is True
        )

    def test_definitive_absence_returns_false(self, monkeypatch):
        body = '[{"id": "other-project", "name": "other-project"}]'
        self._patch_urlopen(monkeypatch, 200, body)
        assert (
            trusty_status._palace_exists("http://127.0.0.1:7070", "claude-mpm") is False
        )

    def test_empty_list_is_definitive_absence(self, monkeypatch):
        self._patch_urlopen(monkeypatch, 200, "[]")
        assert (
            trusty_status._palace_exists("http://127.0.0.1:7070", "claude-mpm") is False
        )

    def test_uses_health_timeout(self, monkeypatch):
        seen = self._patch_urlopen(monkeypatch, 200, "[]")
        trusty_status._palace_exists("http://127.0.0.1:7070", "claude-mpm")
        assert seen["timeout"] == _HEALTH_TIMEOUT_S
        assert seen["timeout"] <= 0.2

    def test_non_2xx_fails_safe_to_true(self, monkeypatch):
        # 500 → we cannot prove absence → do NOT claim "not created".
        self._patch_urlopen(monkeypatch, 500, "")
        assert (
            trusty_status._palace_exists("http://127.0.0.1:7070", "claude-mpm") is True
        )

    def test_network_error_fails_safe_to_true(self, monkeypatch):
        import urllib.request

        def _boom(*_a, **_k):
            raise OSError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", _boom)
        assert (
            trusty_status._palace_exists("http://127.0.0.1:7070", "claude-mpm") is True
        )

    def test_malformed_json_fails_safe_to_true(self, monkeypatch):
        self._patch_urlopen(monkeypatch, 200, "{ not valid json")
        assert (
            trusty_status._palace_exists("http://127.0.0.1:7070", "claude-mpm") is True
        )

    def test_unexpected_shape_fails_safe_to_true(self, monkeypatch):
        # A bare number is neither a list nor a dict → fail safe.
        self._patch_urlopen(monkeypatch, 200, "42")
        assert (
            trusty_status._palace_exists("http://127.0.0.1:7070", "claude-mpm") is True
        )


class TestPalaceExistsCache:
    """Existence result is cached by the http_addr mtime, separate from health."""

    def _setup(self, monkeypatch, tmp_path):
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_addr_file(home, "trusty-memory", "localhost:7070")
        return home, proj

    def test_repeat_existence_probe_is_cached(self, monkeypatch, tmp_path):
        self._setup(monkeypatch, tmp_path)
        calls = {"n": 0}

        def _counting(_base, _palace):
            calls["n"] += 1
            return True

        monkeypatch.setattr(trusty_status, "_palace_exists", _counting)
        trusty_status._cached_palace_exists("trusty-memory", "http://x", "claude-mpm")
        trusty_status._cached_palace_exists("trusty-memory", "http://x", "claude-mpm")
        assert calls["n"] == 1

    def test_cache_does_not_collide_with_health_cache(self, monkeypatch, tmp_path):
        """Palace cache uses a SEPARATE dict / compound key from health cache."""
        self._setup(monkeypatch, tmp_path)
        monkeypatch.setattr(trusty_status, "_palace_exists", lambda *_a: False)
        trusty_status._cached_palace_exists("trusty-memory", "http://x", "claude-mpm")
        # Health cache must remain untouched by the palace probe.
        assert trusty_status._HEALTH_CACHE == {}
        assert any("::claude-mpm" in k for k in trusty_status._PALACE_CACHE)


class TestGetStatusPalaceVerification:
    """End-to-end: the 'on' line reflects palace existence (#598 option 1)."""

    def _present_healthy_memory(self, monkeypatch, tmp_path):
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_addr_file(home, "trusty-memory", "127.0.0.1:7070")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: True)
        monkeypatch.setattr(trusty_status, "_palace_name", lambda: "claude-mpm")

    def test_palace_exists_no_suffix(self, monkeypatch, tmp_path):
        self._present_healthy_memory(monkeypatch, tmp_path)
        monkeypatch.setattr(trusty_status, "_palace_exists", lambda *_a: True)

        state, line = get_trusty_status("trusty-memory")
        assert state == "on"
        assert "palace: claude-mpm" in line
        assert "(not created)" not in line
        assert "/ui" not in line

    def test_palace_missing_shows_not_created(self, monkeypatch, tmp_path):
        self._present_healthy_memory(monkeypatch, tmp_path)
        monkeypatch.setattr(trusty_status, "_palace_exists", lambda *_a: False)

        state, line = get_trusty_status("trusty-memory")
        assert state == "on"
        assert "palace: claude-mpm (not created)" in line
        assert "/ui" not in line

    def test_probe_error_fails_safe_no_suffix(self, monkeypatch, tmp_path):
        """On a real probe failure the bare name is shown (no false negative).

        Documented semantics (#598): only a successful response that
        definitively lacks the palace yields ``(not created)``. Here the
        palaces endpoint errors, so ``_palace_exists`` returns True (fail-safe)
        and the suffix is omitted.
        """
        self._present_healthy_memory(monkeypatch, tmp_path)

        import urllib.request

        def _boom(*_a, **_k):
            raise OSError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", _boom)

        state, line = get_trusty_status("trusty-memory")
        assert state == "on"
        assert "palace: claude-mpm" in line
        assert "(not created)" not in line

    def test_existence_probe_uses_timeout_at_most_200ms(self, monkeypatch, tmp_path):
        self._present_healthy_memory(monkeypatch, tmp_path)

        import urllib.request

        seen: dict[str, object] = {}

        def _fake_urlopen(_req, timeout=None):
            seen["timeout"] = timeout
            return _fake_palaces_resp(200, "[]")

        monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
        get_trusty_status("trusty-memory")
        assert seen["timeout"] == _HEALTH_TIMEOUT_S
        assert seen["timeout"] <= 0.2

    def test_no_existence_probe_when_not_running(self, monkeypatch, tmp_path):
        """Health fails → palace probe must NOT run (zero added cost)."""
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_addr_file(home, "trusty-memory", "127.0.0.1:7070")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: False)

        def _boom(*_a, **_k):
            raise AssertionError("palace probe must not run when not running")

        monkeypatch.setattr(trusty_status, "_palace_exists", _boom)
        state, _line = get_trusty_status("trusty-memory")
        assert state == "not_running"

    def test_no_existence_probe_when_absent(self, monkeypatch, tmp_path):
        """Not opted in → neither health nor palace probe runs (zero cost)."""
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)  # no .mcp.json, no http_addr

        def _boom(*_a, **_k):
            raise AssertionError("no probe may run when absent")

        monkeypatch.setattr(trusty_status, "_health_check", _boom)
        monkeypatch.setattr(trusty_status, "_palace_exists", _boom)
        state, line = get_trusty_status("trusty-memory")
        assert (state, line) == ("absent", "")

    def test_search_never_does_palace_probe(self, monkeypatch, tmp_path):
        """trusty-search has no palace concept → existence probe never runs."""
        home = tmp_path / "home"
        proj = tmp_path / "proj"
        home.mkdir()
        proj.mkdir()
        _point_home(monkeypatch, home)
        _point_cwd(monkeypatch, proj)
        _write_addr_file(home, "trusty-search", "localhost:7878")
        monkeypatch.setattr(trusty_status, "_health_check", lambda _url: True)

        def _boom(*_a, **_k):
            raise AssertionError("search must not do a palace probe")

        monkeypatch.setattr(trusty_status, "_palace_exists", _boom)
        state, line = get_trusty_status("trusty-search")
        assert state == "on"
        assert "palace" not in line
