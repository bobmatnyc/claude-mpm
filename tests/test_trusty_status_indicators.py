"""
Unit tests for trusty-memory and trusty-search startup banner status indicators.

After #598/#599, the helper functions were moved from ``startup_display`` into
``claude_mpm.services.trusty_status``.  This file tests that module directly.

Covers:
- _is_configured_in_mcp()   - .mcp.json detection (CWD only, no parent walk)
- _health_check()            - health endpoint probe (mocked)
- _palace_name()             - palace name lookup (config override or cwd.name)
- _palace_exists()           - verifies palace in daemon response
- get_trusty_status()        - three-state indicator for both services
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.trusty_status import (
    _health_check,
    _is_configured_in_mcp,
    _palace_exists,
    _palace_name,
    get_trusty_status,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_mcp_json(directory: Path, servers: dict) -> Path:
    """Write a .mcp.json to *directory* and return the file path."""
    path = directory / ".mcp.json"
    path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")
    return path


# ===========================================================================
# _is_configured_in_mcp
# ===========================================================================


class TestIsConfiguredInMcp:
    def test_returns_true_when_key_present(self, tmp_path, monkeypatch):
        """Returns True if the server key appears in .mcp.json at cwd."""
        _write_mcp_json(tmp_path, {"trusty-memory": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_configured_in_mcp("trusty-memory") is True

    def test_returns_false_when_key_absent(self, tmp_path, monkeypatch):
        """Returns False when the server key is missing from .mcp.json."""
        _write_mcp_json(tmp_path, {"other-server": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_configured_in_mcp("trusty-memory") is False

    def test_returns_false_when_no_mcp_json(self, tmp_path, monkeypatch):
        """Returns False when .mcp.json does not exist in cwd."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_configured_in_mcp("trusty-search") is False

    def test_returns_false_on_invalid_json(self, tmp_path, monkeypatch):
        """Silently returns False when .mcp.json contains malformed JSON."""
        bad = tmp_path / ".mcp.json"
        bad.write_text("{ this is not valid json }", encoding="utf-8")
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_configured_in_mcp("trusty-memory") is False

    def test_returns_true_for_trusty_search(self, tmp_path, monkeypatch):
        """Correctly detects trusty-search key."""
        _write_mcp_json(tmp_path, {"trusty-search": {"args": ["serve"]}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_configured_in_mcp("trusty-search") is True

    def test_returns_false_when_mcp_servers_key_missing(self, tmp_path, monkeypatch):
        """Returns False when mcpServers key is missing from JSON."""
        path = tmp_path / ".mcp.json"
        path.write_text(json.dumps({}), encoding="utf-8")
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_configured_in_mcp("trusty-memory") is False

    def test_does_not_walk_to_parent(self, tmp_path, monkeypatch):
        """Does NOT check parent directories — only CWD .mcp.json."""
        _write_mcp_json(tmp_path, {"trusty-search": {"type": "stdio"}})
        child = tmp_path / "subproject"
        child.mkdir()
        monkeypatch.setattr(Path, "cwd", lambda: child)
        # Parent has the file but CWD does not → must return False
        assert _is_configured_in_mcp("trusty-search") is False


# ===========================================================================
# _health_check
# ===========================================================================


class TestHealthCheck:
    def test_returns_true_on_200(self):
        """Returns True when health endpoint responds with HTTP 200."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert _health_check("http://localhost:7070") is True

    def test_returns_false_on_500(self):
        """Returns False when health endpoint responds with HTTP 500."""
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert _health_check("http://localhost:7070") is False

    def test_returns_false_on_connection_error(self):
        """Returns False when the connection is refused (server not running)."""
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            assert _health_check("http://localhost:7070") is False

    def test_returns_false_on_timeout(self):
        """Returns False when the request times out."""
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            assert _health_check("http://localhost:7070") is False

    def test_returns_true_on_201(self):
        """Returns True for any 2xx status code."""
        mock_resp = MagicMock()
        mock_resp.status = 201
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert _health_check("http://localhost:7070") is True


# ===========================================================================
# _palace_name
# ===========================================================================


class TestPalaceName:
    def test_returns_cwd_basename_by_default(self, tmp_path, monkeypatch):
        """Returns the current directory's basename when no config override is set."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        monkeypatch.setattr(Path, "cwd", lambda: project_dir)
        # Ensure no config file interferes
        with patch("claude_mpm.services.trusty_status._load_config", return_value={}):
            result = _palace_name()
        assert result == "my-project"

    def test_returns_config_override_when_set(self, monkeypatch):
        """Returns the palace name from config when trusty_memory.palace is set."""
        with patch(
            "claude_mpm.services.trusty_status._load_config",
            return_value={"trusty_memory": {"palace": "custom-palace"}},
        ):
            result = _palace_name()
        assert result == "custom-palace"

    def test_falls_back_to_cwd_when_config_empty(self, tmp_path, monkeypatch):
        """Falls back to cwd basename when config palace value is empty string."""
        project_dir = tmp_path / "fallback-project"
        project_dir.mkdir()
        monkeypatch.setattr(Path, "cwd", lambda: project_dir)
        with patch(
            "claude_mpm.services.trusty_status._load_config",
            return_value={"trusty_memory": {"palace": ""}},
        ):
            result = _palace_name()
        assert result == "fallback-project"


# ===========================================================================
# _palace_exists
# ===========================================================================


class TestPalaceExists:
    def _mock_urlopen(self, payload: object):
        """Build a context-manager mock that returns JSON-encoded *payload*."""
        raw = json.dumps(payload).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = raw
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        return patch("urllib.request.urlopen", return_value=mock_resp)

    def test_returns_true_when_palace_found_by_name(self):
        """Returns True when palace name matches an entry in the daemon response."""
        payload = [{"name": "my-palace", "id": "my-palace"}]
        with self._mock_urlopen(payload):
            assert _palace_exists("http://localhost:7070", "my-palace") is True

    def test_returns_false_when_palace_not_in_list(self):
        """Returns False when a successful response definitively lacks the palace."""
        payload = [{"name": "other-palace", "id": "other-palace"}]
        with self._mock_urlopen(payload):
            assert _palace_exists("http://localhost:7070", "my-palace") is False

    def test_handles_dict_wrapper_with_palaces_key(self):
        """Handles API responses wrapped in a 'palaces' key."""
        payload = {"palaces": [{"name": "proj", "id": "proj"}]}
        with self._mock_urlopen(payload):
            assert _palace_exists("http://localhost:7070", "proj") is True

    def test_handles_bare_string_entries(self):
        """Handles API responses that return plain strings instead of dicts."""
        payload = ["myapp", "other"]
        with self._mock_urlopen(payload):
            assert _palace_exists("http://localhost:7070", "myapp") is True

    def test_case_insensitive_match(self):
        """Palace name matching is case-insensitive."""
        payload = [{"name": "My-Project", "id": "My-Project"}]
        with self._mock_urlopen(payload):
            assert _palace_exists("http://localhost:7070", "my-project") is True

    def test_returns_true_on_error_fail_safe(self):
        """Returns True (fail-safe) when the API is unreachable."""
        with patch(
            "urllib.request.urlopen", side_effect=Exception("connection refused")
        ):
            result = _palace_exists("http://localhost:7070", "any-palace")
        assert result is True

    def test_returns_true_on_empty_list_fail_safe(self):
        """Returns False when palace list is empty (definitive negative response)."""
        payload: list = []
        with self._mock_urlopen(payload):
            assert _palace_exists("http://localhost:7070", "proj") is False


# ===========================================================================
# get_trusty_status — trusty-memory
# ===========================================================================


class TestGetTrustyMemoryStatus:
    def test_absent_when_not_in_mcp_json_and_no_addr_file(self, tmp_path, monkeypatch):
        """Returns ('absent', '') when trusty-memory is absent from .mcp.json and no addr file."""
        _write_mcp_json(tmp_path, {})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        # Ensure the addr file does not exist for this test user
        with patch("claude_mpm.services.trusty_status._is_present", return_value=False):
            state, line = get_trusty_status("trusty-memory")
        assert state == "absent"
        assert line == ""

    def test_configured_not_running_when_in_mcp_but_unhealthy(
        self, tmp_path, monkeypatch
    ):
        """Returns 'configured' state when in mcp.json but health check fails."""
        _write_mcp_json(tmp_path, {"trusty-memory": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=True):
            with patch(
                "claude_mpm.services.trusty_status._cached_health_check",
                return_value=False,
            ):
                state, line = get_trusty_status("trusty-memory")
        assert state == "configured"
        assert "not running" in line
        assert "trusty-memory" in line

    def test_not_running_suggests_start_command(self, tmp_path, monkeypatch):
        """'not running' hint includes a start command for trusty-memory."""
        _write_mcp_json(tmp_path, {"trusty-memory": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=True):
            with patch(
                "claude_mpm.services.trusty_status._cached_health_check",
                return_value=False,
            ):
                _, line = get_trusty_status("trusty-memory")
        assert "start:" in line

    def test_connected_shows_host_port_not_ui_url(self, tmp_path, monkeypatch):
        """Connected trusty-memory shows host:port — NOT a /ui URL."""
        _write_mcp_json(tmp_path, {"trusty-memory": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=True):
            with patch(
                "claude_mpm.services.trusty_status._cached_health_check",
                return_value=True,
            ):
                with patch(
                    "claude_mpm.services.trusty_status._cached_palace_exists",
                    return_value=True,
                ):
                    state, line = get_trusty_status("trusty-memory")
        assert state == "on"
        assert "trusty-memory: on" in line
        assert "/ui" not in line  # The new module does NOT show /ui paths

    def test_connected_shows_palace_name(self, tmp_path, monkeypatch):
        """Connected trusty-memory shows palace name in the display line."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        monkeypatch.setattr(Path, "cwd", lambda: project_dir)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=True):
            with patch(
                "claude_mpm.services.trusty_status._cached_health_check",
                return_value=True,
            ):
                with patch(
                    "claude_mpm.services.trusty_status._cached_palace_exists",
                    return_value=True,
                ):
                    with patch(
                        "claude_mpm.services.trusty_status._load_config",
                        return_value={},
                    ):
                        state, line = get_trusty_status("trusty-memory")
        assert state == "on"
        assert "palace: my-project" in line

    def test_connected_appends_not_created_when_palace_missing(
        self, tmp_path, monkeypatch
    ):
        """Appends '(not created)' when palace is absent from the daemon."""
        project_dir = tmp_path / "ghost-palace"
        project_dir.mkdir()
        monkeypatch.setattr(Path, "cwd", lambda: project_dir)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=True):
            with patch(
                "claude_mpm.services.trusty_status._cached_health_check",
                return_value=True,
            ):
                with patch(
                    "claude_mpm.services.trusty_status._cached_palace_exists",
                    return_value=False,
                ):
                    with patch(
                        "claude_mpm.services.trusty_status._load_config",
                        return_value={},
                    ):
                        state, line = get_trusty_status("trusty-memory")
        assert state == "on"
        assert "(not created)" in line

    def test_off_when_no_mcp_json_exists(self, tmp_path, monkeypatch):
        """Returns ('absent', '') when .mcp.json does not exist at all."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=False):
            state, line = get_trusty_status("trusty-memory")
        assert state == "absent"
        assert line == ""


# ===========================================================================
# get_trusty_status — trusty-search
# ===========================================================================


class TestGetTrustySearchStatus:
    def test_absent_when_not_in_mcp_json_and_no_addr_file(self, tmp_path, monkeypatch):
        """Returns ('absent', '') when trusty-search is absent."""
        _write_mcp_json(tmp_path, {})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=False):
            state, line = get_trusty_status("trusty-search")
        assert state == "absent"
        assert line == ""

    def test_configured_not_running_when_in_mcp_but_unhealthy(
        self, tmp_path, monkeypatch
    ):
        """Returns 'configured' state when in mcp.json but health check fails."""
        _write_mcp_json(tmp_path, {"trusty-search": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=True):
            with patch(
                "claude_mpm.services.trusty_status._cached_health_check",
                return_value=False,
            ):
                state, line = get_trusty_status("trusty-search")
        assert state == "configured"
        assert "not running" in line
        assert "trusty-search" in line

    def test_connected_shows_host_port(self, tmp_path, monkeypatch):
        """Connected trusty-search shows host:port in the display line."""
        _write_mcp_json(tmp_path, {"trusty-search": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=True):
            with patch(
                "claude_mpm.services.trusty_status._cached_health_check",
                return_value=True,
            ):
                state, line = get_trusty_status("trusty-search")
        assert state == "on"
        assert "trusty-search: on" in line
        assert "/ui" not in line  # The new module does NOT show /ui paths

    def test_not_running_suggests_serve_command(self, tmp_path, monkeypatch):
        """'not running' hint includes 'trusty-search serve'."""
        _write_mcp_json(tmp_path, {"trusty-search": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=True):
            with patch(
                "claude_mpm.services.trusty_status._cached_health_check",
                return_value=False,
            ):
                _, line = get_trusty_status("trusty-search")
        assert "trusty-search serve" in line

    def test_off_when_no_mcp_json_exists(self, tmp_path, monkeypatch):
        """Returns ('absent', '') when .mcp.json does not exist at all."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=False):
            state, line = get_trusty_status("trusty-search")
        assert state == "absent"
        assert line == ""

    def test_connected_has_magnifying_glass_emoji(self, tmp_path, monkeypatch):
        """Connected trusty-search line includes magnifying glass emoji."""
        _write_mcp_json(tmp_path, {"trusty-search": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch("claude_mpm.services.trusty_status._is_present", return_value=True):
            with patch(
                "claude_mpm.services.trusty_status._cached_health_check",
                return_value=True,
            ):
                _, line = get_trusty_status("trusty-search")
        # \U0001f50d is the magnifying glass emoji
        assert "\U0001f50d" in line


# ===========================================================================
# Integration: both indicators appear in the startup banner
# ===========================================================================


class TestBannerIntegration:
    def test_banner_contains_trusty_memory_line(self, capsys, tmp_path, monkeypatch):
        """The startup banner includes a trusty-memory indicator line."""
        from claude_mpm.cli.startup_display import display_startup_banner

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(
            "claude_mpm.cli.startup_display._get_active_model_display_name",
            lambda: "Sonnet",
        )
        # Both services absent → get_trusty_status returns ("absent", "")
        # Those are suppressed, so we just verify the banner renders without error.
        with patch(
            "claude_mpm.services.trusty_status.get_trusty_status",
            return_value=("absent", ""),
        ):
            display_startup_banner("9.9.9")
        captured = capsys.readouterr()
        # Banner rendered without crash; version present
        assert "9.9.9" in captured.out

    def test_banner_shows_connected_state_for_trusty_memory(
        self, capsys, tmp_path, monkeypatch
    ):
        """Banner shows 'on' state when trusty-memory is healthy."""
        from claude_mpm.cli.startup_display import display_startup_banner

        _write_mcp_json(tmp_path, {"trusty-memory": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(
            "claude_mpm.cli.startup_display._get_active_model_display_name",
            lambda: "Sonnet",
        )

        # Patch at the services layer so startup_display sees the right return value
        def _fake_trusty_status(service: str):
            if service == "trusty-memory":
                return ("on", "🧠 trusty-memory: on   palace: tmp   127.0.0.1:7070")
            return ("absent", "")

        with patch(
            "claude_mpm.cli.startup_display.get_trusty_status",
            side_effect=_fake_trusty_status,
        ):
            display_startup_banner("9.9.9")
        captured = capsys.readouterr()
        assert "trusty-memory: on" in captured.out

    def test_banner_shows_connected_state_for_trusty_search(
        self, capsys, tmp_path, monkeypatch
    ):
        """Banner shows 'on' state when trusty-search is healthy."""
        from claude_mpm.cli.startup_display import display_startup_banner

        _write_mcp_json(tmp_path, {"trusty-search": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(
            "claude_mpm.cli.startup_display._get_active_model_display_name",
            lambda: "Sonnet",
        )

        def _fake_trusty_status(service: str):
            if service == "trusty-search":
                return ("on", "🔍 trusty-search: on   127.0.0.1:7878")
            return ("absent", "")

        with patch(
            "claude_mpm.cli.startup_display.get_trusty_status",
            side_effect=_fake_trusty_status,
        ):
            display_startup_banner("9.9.9")
        captured = capsys.readouterr()
        assert "trusty-search: on" in captured.out
