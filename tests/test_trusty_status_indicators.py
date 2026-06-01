"""
Unit tests for trusty-memory and trusty-search startup banner status indicators.

Covers:
- _is_server_in_mcp_json()    - .mcp.json detection
- _http_health_check()         - health endpoint probe (mocked)
- _get_trusty_memory_palace()  - palace name lookup (mocked)
- _get_trusty_memory_status()  - three-state indicator
- _get_trusty_search_status()  - three-state indicator
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.claude_mpm.cli.startup_display import (
    _get_trusty_memory_palace,
    _get_trusty_memory_status,
    _get_trusty_search_status,
    _http_health_check,
    _is_server_in_mcp_json,
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
# _is_server_in_mcp_json
# ===========================================================================


class TestIsServerInMcpJson:
    def test_returns_true_when_key_present(self, tmp_path, monkeypatch):
        """Returns True if the server key appears in .mcp.json at cwd."""
        _write_mcp_json(tmp_path, {"trusty-memory": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_server_in_mcp_json("trusty-memory") is True

    def test_returns_false_when_key_absent(self, tmp_path, monkeypatch):
        """Returns False when the server key is missing from .mcp.json."""
        _write_mcp_json(tmp_path, {"other-server": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_server_in_mcp_json("trusty-memory") is False

    def test_returns_false_when_no_mcp_json(self, tmp_path, monkeypatch):
        """Returns False when .mcp.json does not exist in cwd or parent."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_server_in_mcp_json("trusty-search") is False

    def test_returns_false_on_invalid_json(self, tmp_path, monkeypatch):
        """Silently returns False when .mcp.json contains malformed JSON."""
        bad = tmp_path / ".mcp.json"
        bad.write_text("{ this is not valid json }", encoding="utf-8")
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_server_in_mcp_json("trusty-memory") is False

    def test_falls_back_to_parent_directory(self, tmp_path, monkeypatch):
        """Searches one level up if .mcp.json is absent from cwd."""
        _write_mcp_json(tmp_path, {"trusty-search": {"type": "stdio"}})
        child = tmp_path / "subproject"
        child.mkdir()
        monkeypatch.setattr(Path, "cwd", lambda: child)
        assert _is_server_in_mcp_json("trusty-search") is True

    def test_returns_true_for_trusty_search(self, tmp_path, monkeypatch):
        """Correctly detects trusty-search key."""
        _write_mcp_json(tmp_path, {"trusty-search": {"args": ["serve"]}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_server_in_mcp_json("trusty-search") is True

    def test_returns_false_when_mcp_servers_key_missing(self, tmp_path, monkeypatch):
        """Returns False when mcpServers key is missing from JSON."""
        path = tmp_path / ".mcp.json"
        path.write_text(json.dumps({}), encoding="utf-8")
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        assert _is_server_in_mcp_json("trusty-memory") is False


# ===========================================================================
# _http_health_check
# ===========================================================================


class TestHttpHealthCheck:
    def test_returns_true_on_200(self):
        """Returns True when health endpoint responds with HTTP 200."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert _http_health_check("http://localhost:7070/health") is True

    def test_returns_false_on_500(self):
        """Returns False when health endpoint responds with HTTP 500."""
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert _http_health_check("http://localhost:7070/health") is False

    def test_returns_false_on_connection_error(self):
        """Returns False when the connection is refused (server not running)."""
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            assert _http_health_check("http://localhost:7070/health") is False

    def test_returns_false_on_timeout(self):
        """Returns False when the request times out."""
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            assert _http_health_check("http://localhost:7070/health") is False

    def test_returns_true_on_201(self):
        """Returns True for any 2xx status code."""
        mock_resp = MagicMock()
        mock_resp.status = 201
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert _http_health_check("http://localhost:7070/health") is True


# ===========================================================================
# _get_trusty_memory_palace
# ===========================================================================


class TestGetTrustyMemoryPalace:
    def _mock_urlopen(self, payload: object):
        """Build a context-manager mock that returns JSON-encoded *payload*."""
        raw = json.dumps(payload).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = raw
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        return patch("urllib.request.urlopen", return_value=mock_resp)

    def test_exact_match_on_cwd_name(self, tmp_path, monkeypatch):
        """Prefers palace whose name exactly matches cwd basename."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path / "my-project")
        payload = [{"name": "My-Project"}, {"name": "other"}]
        with self._mock_urlopen(payload):
            result = _get_trusty_memory_palace("http://localhost:7070")
        assert result == "My-Project"

    def test_substring_match_fallback(self, tmp_path, monkeypatch):
        """Falls back to substring match when no exact match found."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path / "claude-mpm")
        payload = [{"name": "other-palace"}, {"name": "claude-mpm-notes"}]
        with self._mock_urlopen(payload):
            result = _get_trusty_memory_palace("http://localhost:7070")
        assert result == "claude-mpm-notes"

    def test_returns_first_palace_when_no_name_match(self, tmp_path, monkeypatch):
        """Returns first palace name when nothing matches the project name."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path / "xyz")
        payload = [{"name": "alpha"}, {"name": "beta"}]
        with self._mock_urlopen(payload):
            result = _get_trusty_memory_palace("http://localhost:7070")
        assert result == "alpha"

    def test_handles_string_list(self, tmp_path, monkeypatch):
        """Handles API responses that return a plain list of strings."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path / "myapp")
        payload = ["myapp", "other"]
        with self._mock_urlopen(payload):
            result = _get_trusty_memory_palace("http://localhost:7070")
        assert result == "myapp"

    def test_handles_dict_with_palaces_key(self, tmp_path, monkeypatch):
        """Handles API responses that wrap the list in a 'palaces' key."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path / "proj")
        payload = {"palaces": [{"name": "proj"}, {"name": "other"}]}
        with self._mock_urlopen(payload):
            result = _get_trusty_memory_palace("http://localhost:7070")
        assert result == "proj"

    def test_returns_none_on_error(self):
        """Returns None gracefully when the API is unreachable."""
        with patch(
            "urllib.request.urlopen", side_effect=Exception("connection refused")
        ):
            result = _get_trusty_memory_palace("http://localhost:7070")
        assert result is None

    def test_returns_none_on_empty_list(self, tmp_path, monkeypatch):
        """Returns None when the palace list is empty."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path / "proj")
        with self._mock_urlopen([]):
            result = _get_trusty_memory_palace("http://localhost:7070")
        assert result is None


# ===========================================================================
# _get_trusty_memory_status
# ===========================================================================


class TestGetTrustyMemoryStatus:
    def test_off_when_not_in_mcp_json(self, tmp_path, monkeypatch):
        """Shows 'off' when trusty-memory is absent from .mcp.json."""
        _write_mcp_json(tmp_path, {})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = _get_trusty_memory_status()
        assert "trusty-memory: off" in result

    def test_not_running_when_in_config_but_unhealthy(self, tmp_path, monkeypatch):
        """Shows 'not running' when server is configured but health check fails."""
        _write_mcp_json(tmp_path, {"trusty-memory": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch(
            "src.claude_mpm.cli.startup_display._http_health_check", return_value=False
        ):
            result = _get_trusty_memory_status()
        assert "not running" in result
        assert "trusty-memory" in result

    def test_connected_shows_ui_url(self, tmp_path, monkeypatch):
        """Shows UI URL when server is connected."""
        _write_mcp_json(tmp_path, {"trusty-memory": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch(
            "src.claude_mpm.cli.startup_display._http_health_check", return_value=True
        ):
            with patch(
                "src.claude_mpm.cli.startup_display._get_trusty_memory_palace",
                return_value=None,
            ):
                result = _get_trusty_memory_status()
        assert "http://localhost:7070/ui" in result
        assert "trusty-memory: on" in result

    def test_connected_shows_palace_name(self, tmp_path, monkeypatch):
        """Shows palace name when server is connected and palace found."""
        _write_mcp_json(tmp_path, {"trusty-memory": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch(
            "src.claude_mpm.cli.startup_display._http_health_check", return_value=True
        ):
            with patch(
                "src.claude_mpm.cli.startup_display._get_trusty_memory_palace",
                return_value="my-palace",
            ):
                result = _get_trusty_memory_status()
        assert "palace: my-palace" in result
        assert "http://localhost:7070/ui" in result

    def test_connected_omits_palace_when_none(self, tmp_path, monkeypatch):
        """Omits palace section when lookup returns None."""
        _write_mcp_json(tmp_path, {"trusty-memory": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch(
            "src.claude_mpm.cli.startup_display._http_health_check", return_value=True
        ):
            with patch(
                "src.claude_mpm.cli.startup_display._get_trusty_memory_palace",
                return_value=None,
            ):
                result = _get_trusty_memory_status()
        assert "palace:" not in result
        assert "trusty-memory: on" in result

    def test_not_running_suggests_start_command(self, tmp_path, monkeypatch):
        """'not running' hint includes a start command."""
        _write_mcp_json(tmp_path, {"trusty-memory": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch(
            "src.claude_mpm.cli.startup_display._http_health_check", return_value=False
        ):
            result = _get_trusty_memory_status()
        assert "start:" in result

    def test_off_when_no_mcp_json_exists(self, tmp_path, monkeypatch):
        """Shows 'off' when .mcp.json does not exist at all."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = _get_trusty_memory_status()
        assert "trusty-memory: off" in result


# ===========================================================================
# _get_trusty_search_status
# ===========================================================================


class TestGetTrustySearchStatus:
    def test_off_when_not_in_mcp_json(self, tmp_path, monkeypatch):
        """Shows 'off' when trusty-search is absent from .mcp.json."""
        _write_mcp_json(tmp_path, {})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = _get_trusty_search_status()
        assert "trusty-search: off" in result

    def test_not_running_when_in_config_but_unhealthy(self, tmp_path, monkeypatch):
        """Shows 'not running' when server is configured but health check fails."""
        _write_mcp_json(tmp_path, {"trusty-search": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch(
            "src.claude_mpm.cli.startup_display._http_health_check", return_value=False
        ):
            result = _get_trusty_search_status()
        assert "not running" in result
        assert "trusty-search" in result

    def test_connected_shows_ui_url(self, tmp_path, monkeypatch):
        """Shows UI URL when trusty-search is connected."""
        _write_mcp_json(tmp_path, {"trusty-search": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch(
            "src.claude_mpm.cli.startup_display._http_health_check", return_value=True
        ):
            result = _get_trusty_search_status()
        assert "http://127.0.0.1:7878/ui" in result
        assert "trusty-search: on" in result

    def test_not_running_suggests_serve_command(self, tmp_path, monkeypatch):
        """'not running' hint includes 'trusty-search serve'."""
        _write_mcp_json(tmp_path, {"trusty-search": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch(
            "src.claude_mpm.cli.startup_display._http_health_check", return_value=False
        ):
            result = _get_trusty_search_status()
        assert "trusty-search serve" in result

    def test_off_when_no_mcp_json_exists(self, tmp_path, monkeypatch):
        """Shows 'off' when .mcp.json does not exist at all."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = _get_trusty_search_status()
        assert "trusty-search: off" in result

    def test_connected_has_brain_icon(self, tmp_path, monkeypatch):
        """Connected trusty-search line includes magnifying glass emoji."""
        _write_mcp_json(tmp_path, {"trusty-search": {"type": "stdio"}})
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        with patch(
            "src.claude_mpm.cli.startup_display._http_health_check", return_value=True
        ):
            result = _get_trusty_search_status()
        # \U0001f50d is the magnifying glass emoji
        assert "\U0001f50d" in result


# ===========================================================================
# Integration: both indicators appear in the startup banner
# ===========================================================================


class TestBannerIntegration:
    def test_banner_contains_trusty_memory_line(self, capsys, tmp_path, monkeypatch):
        """The startup banner includes a trusty-memory indicator line."""
        from src.claude_mpm.cli.startup_display import display_startup_banner

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(
            "src.claude_mpm.cli.startup_display._get_active_model_display_name",
            lambda: "Sonnet",
        )
        # Both servers absent from .mcp.json → expect 'off' lines
        display_startup_banner("9.9.9")
        captured = capsys.readouterr()
        assert "trusty-memory" in captured.out

    def test_banner_contains_trusty_search_line(self, capsys, tmp_path, monkeypatch):
        """The startup banner includes a trusty-search indicator line."""
        from src.claude_mpm.cli.startup_display import display_startup_banner

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(
            "src.claude_mpm.cli.startup_display._get_active_model_display_name",
            lambda: "Sonnet",
        )
        display_startup_banner("9.9.9")
        captured = capsys.readouterr()
        assert "trusty-search" in captured.out

    def test_banner_shows_connected_state(self, capsys, tmp_path, monkeypatch):
        """Banner shows 'on' state when both servers are healthy."""
        from src.claude_mpm.cli.startup_display import display_startup_banner

        _write_mcp_json(
            tmp_path,
            {
                "trusty-memory": {"type": "stdio"},
                "trusty-search": {"type": "stdio"},
            },
        )
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(
            "src.claude_mpm.cli.startup_display._get_active_model_display_name",
            lambda: "Sonnet",
        )
        with patch(
            "src.claude_mpm.cli.startup_display._http_health_check", return_value=True
        ):
            with patch(
                "src.claude_mpm.cli.startup_display._get_trusty_memory_palace",
                return_value=None,
            ):
                display_startup_banner("9.9.9")
        captured = capsys.readouterr()
        assert "trusty-memory: on" in captured.out
        assert "trusty-search: on" in captured.out
