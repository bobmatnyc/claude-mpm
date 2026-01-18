"""Project registry for MPM Commander.

This module provides thread-safe registration and management of projects,
including state tracking, session management, and path indexing.
"""

import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .models import Project, ProjectState, ToolSession

logger = logging.getLogger(__name__)


class ProjectRegistry:
    """Thread-safe registry for managing projects.

    Maintains an in-memory registry of all active projects with:
    - Unique project IDs (UUIDs)
    - Path-based indexing for fast lookup
    - Thread-safe access with RLock
    - State management and session tracking

    Example:
        >>> registry = ProjectRegistry()
        >>> project = registry.register("/Users/masa/Projects/my-app")
        >>> project.id
        'a3f2c1d4-...'
        >>> registry.update_state(project.id, ProjectState.WORKING)
        >>> registry.get(project.id).state
        <ProjectState.WORKING: 'working'>
    """

    def __init__(self):
        """Initialize empty registry with thread-safe lock."""
        self._projects: Dict[str, Project] = {}
        self._path_index: Dict[str, str] = {}  # path -> project_id
        self._lock = threading.RLock()
        logger.info("Initialized ProjectRegistry")

    def register(
        self, path: str, name: Optional[str] = None, project_id: Optional[str] = None
    ) -> Project:
        """Register a new project.

        Creates a new project with unique UUID (or user-provided ID) and adds it to registry.
        Path must be a valid directory and cannot already be registered.

        Args:
            path: Absolute filesystem path to project directory
            name: Optional human-readable name (defaults to directory name)
            project_id: Optional project identifier (UUID generated if omitted)

        Returns:
            Newly created Project instance

        Raises:
            ValueError: If path is invalid, not a directory, or already registered

        Example:
            >>> registry = ProjectRegistry()
            >>> project = registry.register("/Users/masa/Projects/my-app")
            >>> project.name
            'my-app'
            >>> project.state
            <ProjectState.IDLE: 'idle'>
        """
        with self._lock:
            # Validate path exists and is directory
            path_obj = Path(path)
            try:
                if not path_obj.exists():
                    raise ValueError(f"Path does not exist: {path}")
                if not path_obj.is_dir():
                    raise ValueError(f"Path is not a directory: {path}")
            except (OSError, PermissionError) as e:
                raise ValueError(f"Cannot access path: {path}") from e

            # Resolve to absolute path for consistency
            abs_path = str(path_obj.resolve())

            # Check for duplicate registration
            if abs_path in self._path_index:
                existing_id = self._path_index[abs_path]
                raise ValueError(
                    f"Project already registered at path: {abs_path} "
                    f"(project_id: {existing_id})"
                )

            # Derive name from directory if not provided
            if name is None:
                name = path_obj.name

            # Generate unique project ID if not provided
            if project_id is None:
                project_id = str(uuid.uuid4())
            elif project_id in self._projects:
                raise ValueError(f"Project ID already exists: {project_id}")

            # Create project instance
            project = Project(
                id=project_id,
                path=abs_path,
                name=name,
                state=ProjectState.IDLE,
            )

            # Register in both indexes
            self._projects[project_id] = project
            self._path_index[abs_path] = project_id

            logger.info(
                "Registered project: id=%s, path=%s, name=%s",
                project_id,
                abs_path,
                name,
            )

            return project

    def unregister(self, project_id: str) -> None:
        """Remove project from registry.

        Removes project from both ID and path indexes.

        Args:
            project_id: Unique project identifier

        Raises:
            KeyError: If project_id not found

        Example:
            >>> registry = ProjectRegistry()
            >>> project = registry.register("/tmp/test-project")
            >>> registry.unregister(project.id)
            >>> registry.get(project.id) is None
            True
        """
        with self._lock:
            if project_id not in self._projects:
                raise KeyError(f"Project not found: {project_id}")

            project = self._projects[project_id]

            # Remove from both indexes
            del self._projects[project_id]
            del self._path_index[project.path]

            logger.info(
                "Unregistered project: id=%s, path=%s",
                project_id,
                project.path,
            )

    def get(self, project_id: str) -> Optional[Project]:
        """Get project by ID.

        Args:
            project_id: Unique project identifier

        Returns:
            Project instance or None if not found

        Example:
            >>> registry = ProjectRegistry()
            >>> project = registry.register("/tmp/test")
            >>> registry.get(project.id).name
            'test'
            >>> registry.get("invalid-id") is None
            True
        """
        with self._lock:
            return self._projects.get(project_id)

    def get_by_path(self, path: str) -> Optional[Project]:
        """Get project by filesystem path.

        Resolves path to absolute before lookup.

        Args:
            path: Filesystem path to project

        Returns:
            Project instance or None if not found

        Example:
            >>> registry = ProjectRegistry()
            >>> project = registry.register("/tmp/test")
            >>> found = registry.get_by_path("/tmp/test")
            >>> found.id == project.id
            True
        """
        with self._lock:
            # Resolve to absolute path for consistent lookup
            try:
                abs_path = str(Path(path).resolve())
            except (OSError, ValueError):
                # Invalid path
                return None

            project_id = self._path_index.get(abs_path)
            if project_id is None:
                return None

            return self._projects.get(project_id)

    def list_all(self) -> List[Project]:
        """List all registered projects.

        Returns:
            List of all Project instances (may be empty)

        Example:
            >>> registry = ProjectRegistry()
            >>> registry.register("/tmp/proj1")
            >>> registry.register("/tmp/proj2")
            >>> len(registry.list_all())
            2
        """
        with self._lock:
            return list(self._projects.values())

    def list_by_state(self, state: ProjectState) -> List[Project]:
        """List projects in specific state.

        Args:
            state: ProjectState to filter by

        Returns:
            List of projects in given state (may be empty)

        Example:
            >>> registry = ProjectRegistry()
            >>> p1 = registry.register("/tmp/proj1")
            >>> p2 = registry.register("/tmp/proj2")
            >>> registry.update_state(p1.id, ProjectState.WORKING)
            >>> working = registry.list_by_state(ProjectState.WORKING)
            >>> len(working)
            1
            >>> working[0].id == p1.id
            True
        """
        with self._lock:
            return [p for p in self._projects.values() if p.state == state]

    def update_state(
        self,
        project_id: str,
        state: ProjectState,
        reason: Optional[str] = None,
    ) -> None:
        """Update project state.

        Updates both state and optional reason, and touches last_activity.

        Args:
            project_id: Unique project identifier
            state: New ProjectState
            reason: Optional state reason (e.g., error message)

        Raises:
            KeyError: If project_id not found

        Example:
            >>> registry = ProjectRegistry()
            >>> project = registry.register("/tmp/test")
            >>> registry.update_state(
            ...     project.id,
            ...     ProjectState.ERROR,
            ...     reason="Connection timeout"
            ... )
            >>> project.state
            <ProjectState.ERROR: 'error'>
            >>> project.state_reason
            'Connection timeout'
        """
        with self._lock:
            if project_id not in self._projects:
                raise KeyError(f"Project not found: {project_id}")

            project = self._projects[project_id]
            old_state = project.state

            project.state = state
            project.state_reason = reason
            project.last_activity = datetime.now(timezone.utc)

            logger.info(
                "State change: project=%s, %s -> %s, reason=%s",
                project_id,
                old_state.value,
                state.value,
                reason,
            )

    def add_session(self, project_id: str, session: ToolSession) -> None:
        """Add session to project.

        Adds tool session to project's session dict and updates last_activity.

        Args:
            project_id: Unique project identifier
            session: ToolSession to add

        Raises:
            KeyError: If project_id not found

        Example:
            >>> registry = ProjectRegistry()
            >>> project = registry.register("/tmp/test")
            >>> session = ToolSession(
            ...     id="sess-123",
            ...     project_id=project.id,
            ...     runtime="claude-code",
            ...     tmux_target="commander:test-cc"
            ... )
            >>> registry.add_session(project.id, session)
            >>> len(project.sessions)
            1
        """
        with self._lock:
            if project_id not in self._projects:
                raise KeyError(f"Project not found: {project_id}")

            project = self._projects[project_id]
            project.sessions[session.id] = session
            project.last_activity = datetime.now(timezone.utc)

            logger.info(
                "Added session: project=%s, session=%s, runtime=%s",
                project_id,
                session.id,
                session.runtime,
            )

    def remove_session(self, project_id: str, session_id: str) -> None:
        """Remove session from project.

        Removes tool session from project's session dict and updates last_activity.

        Args:
            project_id: Unique project identifier
            session_id: Session ID to remove

        Raises:
            KeyError: If project_id not found or session_id not in project

        Example:
            >>> registry = ProjectRegistry()
            >>> project = registry.register("/tmp/test")
            >>> session = ToolSession(
            ...     id="sess-123",
            ...     project_id=project.id,
            ...     runtime="claude-code",
            ...     tmux_target="commander:test-cc"
            ... )
            >>> registry.add_session(project.id, session)
            >>> registry.remove_session(project.id, session.id)
            >>> len(project.sessions)
            0
        """
        with self._lock:
            if project_id not in self._projects:
                raise KeyError(f"Project not found: {project_id}")

            project = self._projects[project_id]

            if session_id not in project.sessions:
                raise KeyError(f"Session not found in project: {session_id}")

            del project.sessions[session_id]
            project.last_activity = datetime.now(timezone.utc)

            logger.info(
                "Removed session: project=%s, session=%s",
                project_id,
                session_id,
            )

    def touch(self, project_id: str) -> None:
        """Update last_activity timestamp.

        Args:
            project_id: Unique project identifier

        Raises:
            KeyError: If project_id not found

        Example:
            >>> import time
            >>> registry = ProjectRegistry()
            >>> project = registry.register("/tmp/test")
            >>> old_time = project.last_activity
            >>> time.sleep(0.01)
            >>> registry.touch(project.id)
            >>> project.last_activity > old_time
            True
        """
        with self._lock:
            if project_id not in self._projects:
                raise KeyError(f"Project not found: {project_id}")

            project = self._projects[project_id]
            project.last_activity = datetime.now(timezone.utc)

            logger.debug("Touched project: %s", project_id)
