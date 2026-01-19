"""Tests for MPM Commander REST API.

This module tests all API endpoints using FastAPI's TestClient.
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from claude_mpm.commander.api.app import app
from claude_mpm.commander.models import ProjectState


@pytest.fixture
def client():
    """Create test client for API."""
    # Use context manager to trigger lifespan events
    with TestClient(app) as client:
        yield client


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for test projects."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def clear_registry():
    """Clear registry before each test."""
    # Access registry from app.state
    if hasattr(app.state, "registry") and app.state.registry is not None:
        # Clear all projects
        for project in app.state.registry.list_all():
            try:
                app.state.registry.unregister(project.id)
            except KeyError:
                pass
    yield


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns status and version."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestProjectEndpoints:
    """Test project management endpoints."""

    def test_list_projects_empty(self, client, clear_registry):
        """Test listing projects when none registered."""
        response = client.get("/api/projects")
        assert response.status_code == 200
        assert response.json() == []

    def test_register_project_success(self, client, clear_registry, temp_project_dir):
        """Test registering a valid project."""
        response = client.post(
            "/api/projects",
            json={"path": temp_project_dir, "name": "Test Project"},
        )
        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert data["path"] == str(Path(temp_project_dir).resolve())
        assert data["name"] == "Test Project"
        assert data["state"] == "idle"
        assert data["state_reason"] is None
        assert data["sessions"] == []
        assert data["pending_events_count"] == 0
        assert "created_at" in data
        assert "last_activity" in data

    def test_register_project_invalid_path(self, client, clear_registry):
        """Test registering project with invalid path."""
        response = client.post(
            "/api/projects",
            json={"path": "/nonexistent/path"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_PATH"

    def test_register_project_duplicate(self, client, clear_registry, temp_project_dir):
        """Test registering same path twice."""
        # Register first time
        response1 = client.post(
            "/api/projects",
            json={"path": temp_project_dir},
        )
        assert response1.status_code == 201

        # Try to register again
        response2 = client.post(
            "/api/projects",
            json={"path": temp_project_dir},
        )
        assert response2.status_code == 409
        data = response2.json()
        assert data["detail"]["error"]["code"] == "PROJECT_ALREADY_EXISTS"

    def test_list_projects_with_projects(
        self, client, clear_registry, temp_project_dir
    ):
        """Test listing projects after registering some."""
        # Register project
        client.post("/api/projects", json={"path": temp_project_dir})

        # List projects
        response = client.get("/api/projects")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["path"] == str(Path(temp_project_dir).resolve())

    def test_get_project_success(self, client, clear_registry, temp_project_dir):
        """Test getting project by ID."""
        # Register project
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]

        # Get project
        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id

    def test_get_project_not_found(self, client, clear_registry):
        """Test getting nonexistent project."""
        response = client.get("/api/projects/nonexistent-id")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_unregister_project_success(self, client, clear_registry, temp_project_dir):
        """Test unregistering a project."""
        # Register project
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]

        # Unregister
        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/projects/{project_id}")
        assert get_response.status_code == 404

    def test_unregister_project_not_found(self, client, clear_registry):
        """Test unregistering nonexistent project."""
        response = client.delete("/api/projects/nonexistent-id")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_pause_project(self, client, clear_registry, temp_project_dir):
        """Test pausing a project."""
        # Register project
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]

        # Pause project
        response = client.post(f"/api/projects/{project_id}/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "paused"
        assert "paused" in data["state_reason"].lower()

    def test_resume_project(self, client, clear_registry, temp_project_dir):
        """Test resuming a paused project."""
        # Register and pause project
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]
        client.post(f"/api/projects/{project_id}/pause")

        # Resume project
        response = client.post(f"/api/projects/{project_id}/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "idle"
        assert "resumed" in data["state_reason"].lower()


class TestSessionEndpoints:
    """Test session management endpoints."""

    def test_list_sessions_empty(self, client, clear_registry, temp_project_dir):
        """Test listing sessions when none exist."""
        # Register project
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]

        # List sessions
        response = client.get(f"/api/projects/{project_id}/sessions")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_sessions_project_not_found(self, client, clear_registry):
        """Test listing sessions for nonexistent project."""
        response = client.get("/api/projects/nonexistent-id/sessions")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "PROJECT_NOT_FOUND"

    @pytest.mark.skipif(
        not hasattr(app.state, "tmux")
        or app.state.tmux is None
        or not hasattr(app.state.tmux, "session_exists")
        or not app.state.tmux.session_exists(),
        reason="Requires tmux session",
    )
    def test_create_session_success(self, client, clear_registry, temp_project_dir):
        """Test creating a session."""
        # Register project
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]

        # Create session
        response = client.post(
            f"/api/projects/{project_id}/sessions",
            json={"runtime": "claude-code"},
        )
        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert data["project_id"] == project_id
        assert data["runtime"] == "claude-code"
        assert "tmux_target" in data
        assert data["status"] == "initializing"
        assert "created_at" in data

    def test_create_session_invalid_runtime(
        self, client, clear_registry, temp_project_dir
    ):
        """Test creating session with invalid runtime."""
        # Register project
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]

        # Try to create session with invalid runtime
        response = client.post(
            f"/api/projects/{project_id}/sessions",
            json={"runtime": "invalid-runtime"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_RUNTIME"

    def test_create_session_project_not_found(self, client, clear_registry):
        """Test creating session for nonexistent project."""
        response = client.post(
            "/api/projects/nonexistent-id/sessions",
            json={"runtime": "claude-code"},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "PROJECT_NOT_FOUND"

    @pytest.mark.skipif(
        not hasattr(app.state, "tmux")
        or app.state.tmux is None
        or not hasattr(app.state.tmux, "session_exists")
        or not app.state.tmux.session_exists(),
        reason="Requires tmux session",
    )
    def test_stop_session_success(self, client, clear_registry, temp_project_dir):
        """Test stopping a session."""
        # Register project and create session
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]

        sess_response = client.post(
            f"/api/projects/{project_id}/sessions",
            json={"runtime": "claude-code"},
        )
        session_id = sess_response.json()["id"]

        # Stop session
        response = client.delete(f"/api/sessions/{session_id}")
        assert response.status_code == 204

        # Verify session is gone
        list_response = client.get(f"/api/projects/{project_id}/sessions")
        sessions = list_response.json()
        assert len(sessions) == 0

    def test_stop_session_not_found(self, client, clear_registry):
        """Test stopping nonexistent session."""
        response = client.delete("/api/sessions/nonexistent-id")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "SESSION_NOT_FOUND"


class TestMessageEndpoints:
    """Test message and thread endpoints."""

    def test_get_thread_empty(self, client, clear_registry, temp_project_dir):
        """Test getting thread when no messages exist."""
        # Register project
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]

        # Get thread
        response = client.get(f"/api/projects/{project_id}/thread")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_thread_project_not_found(self, client, clear_registry):
        """Test getting thread for nonexistent project."""
        response = client.get("/api/projects/nonexistent-id/thread")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_send_message_success(self, client, clear_registry, temp_project_dir):
        """Test sending a message."""
        # Register project
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]

        # Send message
        response = client.post(
            f"/api/projects/{project_id}/messages",
            json={"content": "Test message"},
        )
        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert data["role"] == "user"
        assert data["content"] == "Test message"
        assert "timestamp" in data

    def test_send_message_with_session(self, client, clear_registry, temp_project_dir):
        """Test sending message with session ID."""
        # Register project
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]

        # Send message
        response = client.post(
            f"/api/projects/{project_id}/messages",
            json={"content": "Test message", "session_id": "sess-123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == "sess-123"

    def test_send_message_project_not_found(self, client, clear_registry):
        """Test sending message to nonexistent project."""
        response = client.post(
            "/api/projects/nonexistent-id/messages",
            json={"content": "Test message"},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_thread_with_messages(self, client, clear_registry, temp_project_dir):
        """Test thread contains sent messages."""
        # Register project
        reg_response = client.post("/api/projects", json={"path": temp_project_dir})
        project_id = reg_response.json()["id"]

        # Send messages
        client.post(
            f"/api/projects/{project_id}/messages",
            json={"content": "Message 1"},
        )
        client.post(
            f"/api/projects/{project_id}/messages",
            json={"content": "Message 2"},
        )

        # Get thread
        response = client.get(f"/api/projects/{project_id}/thread")
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 2
        assert messages[0]["content"] == "Message 1"
        assert messages[1]["content"] == "Message 2"
