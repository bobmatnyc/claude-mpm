"""Tests for the message injection HTTP endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from claude_mpm.services.agents.message_endpoint import (
    DEFAULT_PORT,
    MessageEndpoint,
)

if TYPE_CHECKING:
    from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# Construction tests
# ---------------------------------------------------------------------------


class TestMessageEndpointConstruction:
    """Test MessageEndpoint instantiation with various port configurations."""

    def test_default_port(self) -> None:
        endpoint = MessageEndpoint()
        assert endpoint.port == DEFAULT_PORT

    def test_custom_port(self) -> None:
        endpoint = MessageEndpoint(port=9999)
        assert endpoint.port == 9999

    def test_env_var_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAUDE_MPM_INJECT_PORT", "8888")
        endpoint = MessageEndpoint()
        assert endpoint.port == 8888

    def test_explicit_port_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAUDE_MPM_INJECT_PORT", "8888")
        endpoint = MessageEndpoint(port=7777)
        assert endpoint.port == 7777

    def test_empty_history_on_init(self) -> None:
        endpoint = MessageEndpoint()
        assert endpoint._history == []


# ---------------------------------------------------------------------------
# App creation tests
# ---------------------------------------------------------------------------


class TestCreateApp:
    """Test that create_app returns a usable FastAPI application."""

    def test_returns_fastapi_app(self) -> None:
        from fastapi import FastAPI

        endpoint = MessageEndpoint()
        app = endpoint.create_app()
        assert isinstance(app, FastAPI)

    def test_app_has_expected_routes(self) -> None:
        endpoint = MessageEndpoint()
        app = endpoint.create_app()
        route_paths = [route.path for route in app.routes]
        assert "/status" in route_paths
        assert "/inject" in route_paths
        assert "/history" in route_paths


# ---------------------------------------------------------------------------
# Endpoint tests using TestClient
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> TestClient:
    """Create a TestClient for the message endpoint."""
    endpoint = MessageEndpoint(port=17856)
    app = endpoint.create_app()
    return TestClient(app)


@pytest.fixture()
def endpoint_with_client() -> tuple[MessageEndpoint, TestClient]:
    """Return both the endpoint instance and its test client."""
    endpoint = MessageEndpoint(port=17856)
    app = endpoint.create_app()
    return endpoint, TestClient(app)


class TestStatusEndpoint:
    """Test GET /status."""

    @patch(
        "claude_mpm.services.agents.runtime_config.get_runtime_type",
        return_value="sdk",
    )
    def test_status_returns_running(self, _mock_rt: object, client: TestClient) -> None:
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["runtime"] == "sdk"
        assert data["port"] == 17856
        assert data["history_count"] == 0

    @patch(
        "claude_mpm.services.agents.runtime_config.get_runtime_type",
        side_effect=RuntimeError("boom"),
    )
    def test_status_handles_runtime_error(
        self, _mock_rt: object, client: TestClient
    ) -> None:
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["runtime"] == "unknown"


class TestInjectEndpoint:
    """Test POST /inject."""

    @patch("claude_mpm.services.agents.runtime_bridge.execute_agent_prompt")
    def test_inject_forwards_prompt(
        self,
        mock_execute: AsyncMock,
        endpoint_with_client: tuple[MessageEndpoint, TestClient],
    ) -> None:
        _endpoint, client = endpoint_with_client
        mock_execute.return_value = {
            "text": "Result text",
            "session_id": "sess-001",
            "cost_usd": 0.005,
            "num_turns": 2,
            "duration_ms": 1500,
            "is_error": False,
            "tool_calls": [],
            "runtime": "sdk",
        }

        response = client.post(
            "/inject",
            json={"prompt": "Check PR #123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Result text"
        assert data["session_id"] == "sess-001"
        assert data["cost_usd"] == 0.005
        assert data["num_turns"] == 2
        assert data["duration_ms"] == 1500
        assert data["is_error"] is False
        assert data["runtime"] == "sdk"

        # Verify the bridge was called with correct args
        mock_execute.assert_called_once_with(
            prompt="Check PR #123",
            system_prompt=None,
            model=None,
            session_id=None,
            allowed_tools=None,
            cwd=None,
        )

    @patch("claude_mpm.services.agents.runtime_bridge.execute_agent_prompt")
    def test_inject_with_session_id(
        self,
        mock_execute: AsyncMock,
        client: TestClient,
    ) -> None:
        mock_execute.return_value = {
            "text": "Resumed",
            "session_id": "sess-002",
            "cost_usd": None,
            "num_turns": 1,
            "duration_ms": 500,
            "is_error": False,
            "tool_calls": [],
            "runtime": "cli",
        }

        response = client.post(
            "/inject",
            json={"prompt": "Continue", "session_id": "sess-001"},
        )

        assert response.status_code == 200
        assert response.json()["text"] == "Resumed"
        mock_execute.assert_called_once_with(
            prompt="Continue",
            system_prompt=None,
            model=None,
            session_id="sess-001",
            allowed_tools=None,
            cwd=None,
        )

    @patch("claude_mpm.services.agents.runtime_bridge.execute_agent_prompt")
    def test_inject_records_history(
        self,
        mock_execute: AsyncMock,
        endpoint_with_client: tuple[MessageEndpoint, TestClient],
    ) -> None:
        endpoint, client = endpoint_with_client
        mock_execute.return_value = {
            "text": "Done",
            "session_id": None,
            "cost_usd": None,
            "num_turns": 1,
            "duration_ms": 100,
            "is_error": False,
            "tool_calls": [],
            "runtime": "sdk",
        }

        client.post("/inject", json={"prompt": "Hello"})
        assert len(endpoint._history) == 1
        assert endpoint._history[0]["prompt"] == "Hello"
        assert endpoint._history[0]["runtime"] == "sdk"

    @patch("claude_mpm.services.agents.runtime_bridge.execute_agent_prompt")
    def test_inject_error_handling(
        self,
        mock_execute: AsyncMock,
        client: TestClient,
    ) -> None:
        mock_execute.side_effect = RuntimeError("SDK not available")

        response = client.post(
            "/inject",
            json={"prompt": "Will fail"},
        )

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["is_error"] is True
        assert "SDK not available" in data["error"]

    def test_inject_missing_prompt(self, client: TestClient) -> None:
        response = client.post("/inject", json={})
        assert response.status_code == 422  # Pydantic validation error


class TestHistoryEndpoint:
    """Test GET /history."""

    def test_history_empty_initially(self, client: TestClient) -> None:
        response = client.get("/history")
        assert response.status_code == 200
        data = response.json()
        assert data["history"] == []

    @patch("claude_mpm.services.agents.runtime_bridge.execute_agent_prompt")
    def test_history_after_injection(
        self,
        mock_execute: AsyncMock,
        endpoint_with_client: tuple[MessageEndpoint, TestClient],
    ) -> None:
        _endpoint, client = endpoint_with_client
        mock_execute.return_value = {
            "text": "OK",
            "session_id": None,
            "cost_usd": None,
            "num_turns": 1,
            "duration_ms": 50,
            "is_error": False,
            "tool_calls": [],
            "runtime": "sdk",
        }

        client.post("/inject", json={"prompt": "Test prompt"})

        response = client.get("/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["history"]) == 1
        assert data["history"][0]["prompt"] == "Test prompt"
