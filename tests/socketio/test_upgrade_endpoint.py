"""
Unit tests for the POST /api/upgrade HTTP endpoint.

Tests the upgrade_handler that was added to SocketIOServerCore._setup_http_api()
to wire the "Update now" dashboard button to SelfUpgradeService.perform_upgrade().

WHY: Issue #446 - the dashboard "Update now" button was firing a POST that 404'd
because the backend had no /api/upgrade route.  These tests verify the three key
paths through the new handler:
  1. No update info available (network failure / None return)
  2. Already on latest version (update_available == False)
  3. Successful upgrade
  4. Failed upgrade (non-zero subprocess return)
  5. Unexpected exception → 500 JSON
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(body: dict | None = None) -> MagicMock:
    """Return a minimal aiohttp Request mock."""
    req = MagicMock()
    req.json = AsyncMock(return_value=body or {})
    return req


def _extract_json(response: MagicMock) -> dict:
    """Pull the JSON payload out of an aiohttp json_response mock."""
    # web.json_response is patched to a MagicMock; grab the positional arg
    return response.call_args[0][0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUpgradeEndpoint:
    """Test POST /api/upgrade endpoint behaviour."""

    @pytest.fixture()
    def core(self):
        """Return a SocketIOServerCore with a real aiohttp app (no real server)."""
        # Only import if socketio / aiohttp are available
        pytest.importorskip("aiohttp")
        pytest.importorskip("socketio")

        from aiohttp import web

        from claude_mpm.services.socketio.server.core import SocketIOServerCore

        c = SocketIOServerCore(host="localhost", port=9999)
        c.app = web.Application()
        return c

    # ------------------------------------------------------------------
    # Helper: locate the upgrade handler after _setup_http_api is called
    # ------------------------------------------------------------------

    def _get_upgrade_handler(self, core):
        """Call _setup_http_api and return the registered upgrade handler."""
        # We need to patch web.json_response so it stays inspectable
        # _setup_http_api registers closures on self.app.router; we look them up
        # by calling the internal method with a mocked router.
        handlers: dict[str, object] = {}

        original_add_post = core.app.router.add_post
        original_add_get = core.app.router.add_get

        def capturing_add_post(path, handler):
            handlers[path] = handler
            original_add_post(path, handler)

        def capturing_add_get(path, handler):
            handlers[path] = handler
            original_add_get(path, handler)

        with (
            patch.object(core.app.router, "add_post", side_effect=capturing_add_post),
            patch.object(core.app.router, "add_get", side_effect=capturing_add_get),
        ):
            core._setup_http_api()

        return handlers["/api/upgrade"]

    # ------------------------------------------------------------------
    # Test 1: check_for_update returns None
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_upgrade_returns_error_when_no_update_info(self, core):
        """If check_for_update() returns None, respond with success=False."""
        from aiohttp import web

        handler = self._get_upgrade_handler(core)

        mock_service = MagicMock()
        mock_service.check_for_update = AsyncMock(return_value=None)

        with (
            patch(
                "claude_mpm.services.socketio.server.core.SelfUpgradeService",
                return_value=mock_service,
                create=True,
            ),
            patch(
                "aiohttp.web.json_response", side_effect=web.json_response
            ) as mock_jr,
        ):
            # Patch the import inside the closure
            with patch.dict(
                "sys.modules",
                {
                    "claude_mpm.services.self_upgrade_service": MagicMock(
                        SelfUpgradeService=MagicMock(return_value=mock_service)
                    )
                },
            ):
                req = _make_request()
                resp = await handler(req)

        assert resp.status == 200
        import json

        body = json.loads(resp.body)
        assert body["success"] is False
        assert "error" in body

    # ------------------------------------------------------------------
    # Test 2: already on latest version
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_upgrade_already_latest(self, core):
        """If update_available is False, return success=True with 'already latest' msg."""
        from aiohttp import web

        handler = self._get_upgrade_handler(core)

        update_info = {
            "update_available": False,
            "current": "6.2.61",
            "latest": "6.2.61",
            "upgrade_command": "pip install --upgrade claude-mpm",
        }
        mock_service = MagicMock()
        mock_service.check_for_update = AsyncMock(return_value=update_info)

        with patch.dict(
            "sys.modules",
            {
                "claude_mpm.services.self_upgrade_service": MagicMock(
                    SelfUpgradeService=MagicMock(return_value=mock_service)
                )
            },
        ):
            req = _make_request()
            resp = await handler(req)

        assert resp.status == 200
        import json

        body = json.loads(resp.body)
        assert body["success"] is True
        assert (
            "6.2.61" in body.get("message", "") or body.get("new_version") == "6.2.61"
        )

    # ------------------------------------------------------------------
    # Test 3: successful upgrade
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_upgrade_success(self, core):
        """Happy path: perform_upgrade returns (True, msg) → success response."""
        handler = self._get_upgrade_handler(core)

        update_info = {
            "update_available": True,
            "current": "6.2.60",
            "latest": "6.2.61",
            "upgrade_command": "pip install --upgrade claude-mpm==6.2.61",
        }
        mock_service = MagicMock()
        mock_service.check_for_update = AsyncMock(return_value=update_info)
        mock_service.perform_upgrade = MagicMock(
            return_value=(True, "Successfully upgraded to v6.2.61")
        )

        with patch.dict(
            "sys.modules",
            {
                "claude_mpm.services.self_upgrade_service": MagicMock(
                    SelfUpgradeService=MagicMock(return_value=mock_service)
                )
            },
        ):
            req = _make_request()
            resp = await handler(req)

        import json

        body = json.loads(resp.body)
        assert body["success"] is True
        assert body.get("new_version") == "6.2.61"
        assert (
            "upgrade" in body.get("message", "").lower()
            or "success" in body.get("message", "").lower()
        )

    # ------------------------------------------------------------------
    # Test 4: upgrade fails (non-zero subprocess exit)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_upgrade_failure(self, core):
        """If perform_upgrade returns (False, msg), respond with success=False."""
        handler = self._get_upgrade_handler(core)

        update_info = {
            "update_available": True,
            "current": "6.2.60",
            "latest": "6.2.61",
            "upgrade_command": "pip install --upgrade claude-mpm==6.2.61",
        }
        mock_service = MagicMock()
        mock_service.check_for_update = AsyncMock(return_value=update_info)
        mock_service.perform_upgrade = MagicMock(
            return_value=(False, "Upgrade failed: pip returned code 1")
        )

        with patch.dict(
            "sys.modules",
            {
                "claude_mpm.services.self_upgrade_service": MagicMock(
                    SelfUpgradeService=MagicMock(return_value=mock_service)
                )
            },
        ):
            req = _make_request()
            resp = await handler(req)

        import json

        body = json.loads(resp.body)
        assert body["success"] is False
        assert "error" in body

    # ------------------------------------------------------------------
    # Test 5: unexpected exception → 500
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_upgrade_unexpected_exception(self, core):
        """Unexpected exceptions must return 500 with success=False."""
        handler = self._get_upgrade_handler(core)

        mock_service = MagicMock()
        mock_service.check_for_update = AsyncMock(
            side_effect=RuntimeError("network down")
        )

        with patch.dict(
            "sys.modules",
            {
                "claude_mpm.services.self_upgrade_service": MagicMock(
                    SelfUpgradeService=MagicMock(return_value=mock_service)
                )
            },
        ):
            req = _make_request()
            resp = await handler(req)

        import json

        body = json.loads(resp.body)
        assert resp.status == 500
        assert body["success"] is False
        assert "error" in body
