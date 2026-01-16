"""Tests for ProjectRegistry.

Tests cover:
- Registration with valid/invalid paths
- Duplicate path detection
- Unregistration
- Lookup by ID and path
- Listing and filtering by state
- State updates
- Session management
- Thread safety with concurrent access
"""

import tempfile
import threading
import time
from pathlib import Path

import pytest

from claude_mpm.commander import (
    ProjectRegistry,
    ProjectState,
    ToolSession,
)


class TestProjectRegistration:
    """Tests for project registration."""

    def test_register_valid_path(self):
        """Test registering project with valid path."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)

            assert project.id is not None
            assert project.path == str(Path(tmpdir).resolve())
            assert project.name == Path(tmpdir).name
            assert project.state == ProjectState.IDLE
            assert project.config_loaded is False

    def test_register_with_custom_name(self):
        """Test registering project with custom name."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir, name="CustomName")

            assert project.name == "CustomName"

    def test_register_invalid_path_not_exists(self):
        """Test registration fails for non-existent path."""
        registry = ProjectRegistry()

        with pytest.raises(ValueError, match="Path does not exist"):
            registry.register("/nonexistent/path/12345")

    def test_register_invalid_path_not_directory(self):
        """Test registration fails for file path."""
        registry = ProjectRegistry()

        with tempfile.NamedTemporaryFile() as tmpfile:
            with pytest.raises(ValueError, match="not a directory"):
                registry.register(tmpfile.name)

    def test_register_duplicate_path(self):
        """Test registration fails for duplicate path."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            # First registration succeeds
            project1 = registry.register(tmpdir)

            # Second registration fails
            with pytest.raises(ValueError, match="already registered"):
                registry.register(tmpdir)

            # Verify first project still valid
            assert registry.get(project1.id) is not None


class TestProjectUnregistration:
    """Tests for project unregistration."""

    def test_unregister_success(self):
        """Test successful unregistration."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)
            project_id = project.id

            # Verify registered
            assert registry.get(project_id) is not None

            # Unregister
            registry.unregister(project_id)

            # Verify removed
            assert registry.get(project_id) is None
            assert registry.get_by_path(tmpdir) is None

    def test_unregister_invalid_id(self):
        """Test unregistration fails for invalid ID."""
        registry = ProjectRegistry()

        with pytest.raises(KeyError, match="not found"):
            registry.unregister("invalid-id-12345")


class TestProjectLookup:
    """Tests for project lookup operations."""

    def test_get_by_id(self):
        """Test lookup by project ID."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)

            # Successful lookup
            found = registry.get(project.id)
            assert found is not None
            assert found.id == project.id

            # Failed lookup
            assert registry.get("invalid-id") is None

    def test_get_by_path(self):
        """Test lookup by filesystem path."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)

            # Successful lookup with exact path
            found = registry.get_by_path(tmpdir)
            assert found is not None
            assert found.id == project.id

            # Successful lookup with relative path (if applicable)
            abs_path = str(Path(tmpdir).resolve())
            found_abs = registry.get_by_path(abs_path)
            assert found_abs is not None
            assert found_abs.id == project.id

            # Failed lookup
            assert registry.get_by_path("/nonexistent") is None

    def test_get_by_path_invalid(self):
        """Test lookup with invalid path returns None."""
        registry = ProjectRegistry()

        # Invalid path should return None, not raise
        assert registry.get_by_path("\x00invalid") is None


class TestProjectListing:
    """Tests for listing projects."""

    def test_list_all_empty(self):
        """Test list_all with empty registry."""
        registry = ProjectRegistry()

        assert registry.list_all() == []

    def test_list_all_multiple(self):
        """Test list_all with multiple projects."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                project1 = registry.register(tmpdir1)
                project2 = registry.register(tmpdir2)

                all_projects = registry.list_all()
                assert len(all_projects) == 2
                assert project1 in all_projects
                assert project2 in all_projects

    def test_list_by_state(self):
        """Test filtering projects by state."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                with tempfile.TemporaryDirectory() as tmpdir3:
                    project1 = registry.register(tmpdir1)
                    project2 = registry.register(tmpdir2)
                    project3 = registry.register(tmpdir3)

                    # Initially all IDLE
                    idle_projects = registry.list_by_state(ProjectState.IDLE)
                    assert len(idle_projects) == 3

                    # Change states
                    registry.update_state(project1.id, ProjectState.WORKING)
                    registry.update_state(project2.id, ProjectState.BLOCKED)

                    # Verify filtering
                    working = registry.list_by_state(ProjectState.WORKING)
                    assert len(working) == 1
                    assert working[0].id == project1.id

                    blocked = registry.list_by_state(ProjectState.BLOCKED)
                    assert len(blocked) == 1
                    assert blocked[0].id == project2.id

                    idle = registry.list_by_state(ProjectState.IDLE)
                    assert len(idle) == 1
                    assert idle[0].id == project3.id


class TestStateManagement:
    """Tests for project state management."""

    def test_update_state_success(self):
        """Test successful state update."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)
            initial_time = project.last_activity

            # Small delay to ensure timestamp changes
            time.sleep(0.01)

            # Update state
            registry.update_state(
                project.id,
                ProjectState.WORKING,
                reason="Processing work item",
            )

            # Verify state changed
            assert project.state == ProjectState.WORKING
            assert project.state_reason == "Processing work item"
            assert project.last_activity > initial_time

    def test_update_state_invalid_id(self):
        """Test state update fails for invalid ID."""
        registry = ProjectRegistry()

        with pytest.raises(KeyError, match="not found"):
            registry.update_state("invalid-id", ProjectState.WORKING)

    def test_update_state_without_reason(self):
        """Test state update without reason."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)

            registry.update_state(project.id, ProjectState.PAUSED)

            assert project.state == ProjectState.PAUSED
            assert project.state_reason is None


class TestSessionManagement:
    """Tests for tool session management."""

    def test_add_session(self):
        """Test adding session to project."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)
            initial_time = project.last_activity

            time.sleep(0.01)

            session = ToolSession(
                id="sess-123",
                project_id=project.id,
                runtime="claude-code",
                tmux_target="commander:test-cc",
            )

            registry.add_session(project.id, session)

            # Verify session added
            assert "sess-123" in project.sessions
            assert project.sessions["sess-123"] == session
            assert project.last_activity > initial_time

    def test_add_session_invalid_project(self):
        """Test adding session to invalid project fails."""
        registry = ProjectRegistry()

        session = ToolSession(
            id="sess-123",
            project_id="invalid-id",
            runtime="claude-code",
            tmux_target="commander:test-cc",
        )

        with pytest.raises(KeyError, match="not found"):
            registry.add_session("invalid-id", session)

    def test_remove_session(self):
        """Test removing session from project."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)

            session = ToolSession(
                id="sess-123",
                project_id=project.id,
                runtime="claude-code",
                tmux_target="commander:test-cc",
            )

            registry.add_session(project.id, session)
            assert "sess-123" in project.sessions

            # Remove session
            registry.remove_session(project.id, "sess-123")
            assert "sess-123" not in project.sessions

    def test_remove_session_invalid_project(self):
        """Test removing session from invalid project fails."""
        registry = ProjectRegistry()

        with pytest.raises(KeyError, match="not found"):
            registry.remove_session("invalid-id", "sess-123")

    def test_remove_session_invalid_session(self):
        """Test removing non-existent session fails."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)

            with pytest.raises(KeyError, match="Session not found"):
                registry.remove_session(project.id, "invalid-sess")


class TestActivityTracking:
    """Tests for activity timestamp tracking."""

    def test_touch(self):
        """Test touch updates last_activity."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)
            initial_time = project.last_activity

            time.sleep(0.01)

            registry.touch(project.id)

            assert project.last_activity > initial_time

    def test_touch_invalid_project(self):
        """Test touch fails for invalid project."""
        registry = ProjectRegistry()

        with pytest.raises(KeyError, match="not found"):
            registry.touch("invalid-id")


class TestThreadSafety:
    """Tests for concurrent access thread safety."""

    def test_concurrent_registration(self):
        """Test thread-safe concurrent project registration."""
        registry = ProjectRegistry()
        results = []
        errors = []

        def register_project(tmpdir):
            try:
                project = registry.register(tmpdir)
                results.append(project)
            except Exception as e:
                errors.append(e)

        # Create temporary directories
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                with tempfile.TemporaryDirectory() as tmpdir3:
                    # Register concurrently
                    threads = [
                        threading.Thread(target=register_project, args=(tmpdir1,)),
                        threading.Thread(target=register_project, args=(tmpdir2,)),
                        threading.Thread(target=register_project, args=(tmpdir3,)),
                    ]

                    for t in threads:
                        t.start()
                    for t in threads:
                        t.join()

                    # All should succeed
                    assert len(results) == 3
                    assert len(errors) == 0
                    assert len(registry.list_all()) == 3

    def test_concurrent_state_updates(self):
        """Test thread-safe concurrent state updates."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)

            def update_state_many_times():
                for i in range(100):
                    state = ProjectState.WORKING if i % 2 == 0 else ProjectState.IDLE
                    registry.update_state(project.id, state, reason=f"Update {i}")

            # Run concurrent updates
            threads = [
                threading.Thread(target=update_state_many_times) for _ in range(5)
            ]

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Should not crash, final state should be consistent
            final_state = registry.get(project.id)
            assert final_state is not None
            assert isinstance(final_state.state, ProjectState)

    def test_concurrent_session_management(self):
        """Test thread-safe concurrent session add/remove."""
        registry = ProjectRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            project = registry.register(tmpdir)

            def add_remove_sessions(thread_id):
                for i in range(50):
                    session_id = f"sess-{thread_id}-{i}"
                    session = ToolSession(
                        id=session_id,
                        project_id=project.id,
                        runtime="claude-code",
                        tmux_target=f"commander:test-{thread_id}",
                    )

                    registry.add_session(project.id, session)
                    # Small delay
                    time.sleep(0.001)
                    registry.remove_session(project.id, session_id)

            threads = [
                threading.Thread(target=add_remove_sessions, args=(i,))
                for i in range(3)
            ]

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # All sessions should be removed
            assert len(project.sessions) == 0
