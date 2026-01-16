"""Tests for StateStore persistence."""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from claude_mpm.commander.models import Project, ProjectState, ToolSession
from claude_mpm.commander.persistence import StateStore
from claude_mpm.commander.project_session import ProjectSession, SessionState
from claude_mpm.commander.registry import ProjectRegistry
from claude_mpm.commander.tmux_orchestrator import TmuxOrchestrator


@pytest.fixture
def temp_state_dir():
    """Create temporary state directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def state_store(temp_state_dir):
    """Create StateStore with temp directory."""
    return StateStore(temp_state_dir)


@pytest.fixture
def sample_project():
    """Create sample project for testing."""
    return Project(
        id="test-project-123",
        path="/tmp/test-project",
        name="Test Project",
        state=ProjectState.WORKING,
        state_reason="Testing",
        config_loaded=True,
        config={"key": "value"},
        sessions={
            "sess-1": ToolSession(
                id="sess-1",
                project_id="test-project-123",
                runtime="claude-code",
                tmux_target="commander:test-cc",
                status="running",
                created_at=datetime.now(timezone.utc),
            )
        },
        created_at=datetime.now(timezone.utc),
        last_activity=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_save_projects_creates_file(state_store, sample_project):
    """Test that save_projects creates JSON file."""
    registry = ProjectRegistry()
    registry._projects[sample_project.id] = sample_project
    registry._path_index[sample_project.path] = sample_project.id

    await state_store.save_projects(registry)

    assert state_store.projects_path.exists()
    assert state_store.projects_path.is_file()


@pytest.mark.asyncio
async def test_save_load_projects_round_trip(state_store, sample_project):
    """Test save and load projects round-trip."""
    registry = ProjectRegistry()
    registry._projects[sample_project.id] = sample_project
    registry._path_index[sample_project.path] = sample_project.id

    # Save
    await state_store.save_projects(registry)

    # Load
    projects = await state_store.load_projects()

    # Verify
    assert len(projects) == 1
    loaded = projects[0]
    assert loaded.id == sample_project.id
    assert loaded.name == sample_project.name
    assert loaded.path == sample_project.path
    assert loaded.state == sample_project.state
    assert loaded.state_reason == sample_project.state_reason
    assert loaded.config_loaded == sample_project.config_loaded
    assert loaded.config == sample_project.config
    assert len(loaded.sessions) == 1
    assert "sess-1" in loaded.sessions


@pytest.mark.asyncio
async def test_load_projects_missing_file(state_store):
    """Test load_projects returns empty list when file missing."""
    projects = await state_store.load_projects()
    assert projects == []


@pytest.mark.asyncio
async def test_load_projects_corrupt_file(state_store):
    """Test load_projects handles corrupt JSON."""
    # Write invalid JSON
    state_store.projects_path.write_text("not valid json{{{")

    projects = await state_store.load_projects()
    assert projects == []


@pytest.mark.asyncio
async def test_save_sessions(state_store):
    """Test save_sessions creates file with session data."""
    project = Project(
        id="proj-1", path="/tmp/proj-1", name="Project 1", state=ProjectState.IDLE
    )
    orchestrator = TmuxOrchestrator()
    session = ProjectSession(project, orchestrator)
    session._state = SessionState.RUNNING
    session.active_pane = "commander:proj-1"
    session.pause_reason = "event-123"

    sessions = {"proj-1": session}

    await state_store.save_sessions(sessions)

    assert state_store.sessions_path.exists()

    # Verify content
    data = json.loads(state_store.sessions_path.read_text())
    assert data["version"] == StateStore.VERSION
    assert "proj-1" in data["sessions"]
    assert data["sessions"]["proj-1"]["state"] == "running"
    assert data["sessions"]["proj-1"]["pane_target"] == "commander:proj-1"
    assert data["sessions"]["proj-1"]["paused_event_id"] == "event-123"


@pytest.mark.asyncio
async def test_load_sessions(state_store):
    """Test load_sessions restores session state."""
    # Manually create sessions file
    data = {
        "version": StateStore.VERSION,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "sessions": {
            "proj-1": {
                "state": "paused",
                "pane_target": "commander:test",
                "paused_event_id": "evt-456",
            }
        },
    }
    state_store.sessions_path.write_text(json.dumps(data, indent=2))

    # Load
    sessions = await state_store.load_sessions()

    # Verify
    assert "proj-1" in sessions
    assert sessions["proj-1"]["state"] == "paused"
    assert sessions["proj-1"]["pane_target"] == "commander:test"
    assert sessions["proj-1"]["paused_event_id"] == "evt-456"


@pytest.mark.asyncio
async def test_load_sessions_missing_file(state_store):
    """Test load_sessions returns empty dict when file missing."""
    sessions = await state_store.load_sessions()
    assert sessions == {}


@pytest.mark.asyncio
async def test_atomic_write_prevents_corruption(state_store, temp_state_dir):
    """Test atomic write creates temp file then renames."""
    data = {"test": "data", "version": "1.0"}
    target = temp_state_dir / "test.json"

    # Atomic write should create temp file first
    state_store._atomic_write(target, data)

    # Verify final file exists and has correct content
    assert target.exists()
    loaded = json.loads(target.read_text())
    assert loaded == data

    # Verify no temp files left behind
    temp_files = list(temp_state_dir.glob(".test.json.*.tmp"))
    assert len(temp_files) == 0


@pytest.mark.asyncio
async def test_atomic_write_cleanup_on_error(state_store, temp_state_dir):
    """Test atomic write cleans up temp file on error."""
    target = temp_state_dir / "test.json"

    # Create invalid data that will cause JSON error
    class NonSerializable:
        pass

    data = {"test": NonSerializable()}

    with pytest.raises(IOError):
        state_store._atomic_write(target, data)

    # Verify no temp files left behind
    temp_files = list(temp_state_dir.glob(".test.json.*.tmp"))
    assert len(temp_files) == 0


@pytest.mark.asyncio
async def test_version_mismatch_warning(state_store, caplog):
    """Test version mismatch logs warning but loads data."""
    # Create file with different version
    data = {
        "version": "0.9",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "projects": [],
    }
    state_store.projects_path.write_text(json.dumps(data))

    # Load should warn but continue
    projects = await state_store.load_projects()

    assert "Version mismatch" in caplog.text
    assert projects == []


@pytest.mark.asyncio
async def test_concurrent_saves(state_store, sample_project):
    """Test concurrent saves don't corrupt data."""
    registry = ProjectRegistry()
    registry._projects[sample_project.id] = sample_project
    registry._path_index[sample_project.path] = sample_project.id

    # Run multiple saves concurrently
    tasks = [state_store.save_projects(registry) for _ in range(5)]
    await asyncio.gather(*tasks)

    # Verify data is still valid
    projects = await state_store.load_projects()
    assert len(projects) == 1
    assert projects[0].id == sample_project.id


@pytest.mark.asyncio
async def test_save_multiple_projects(state_store):
    """Test saving multiple projects."""
    registry = ProjectRegistry()

    # Create multiple projects
    for i in range(3):
        project = Project(
            id=f"proj-{i}",
            path=f"/tmp/proj-{i}",
            name=f"Project {i}",
            state=ProjectState.IDLE,
        )
        registry._projects[project.id] = project
        registry._path_index[project.path] = project.id

    await state_store.save_projects(registry)

    # Load and verify
    projects = await state_store.load_projects()
    assert len(projects) == 3
    assert {p.id for p in projects} == {"proj-0", "proj-1", "proj-2"}
