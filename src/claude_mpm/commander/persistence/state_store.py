"""State persistence for MPM Commander.

This module handles atomic persistence and recovery of project registry
and session states to disk.
"""

import asyncio
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..frameworks.base import RegisteredInstance
from ..models import Project, ProjectState, ToolSession
from ..registry import ProjectRegistry

logger = logging.getLogger(__name__)


class StateStore:
    """Persists and recovers project registry state.

    Provides atomic writes to prevent corruption and handles graceful
    recovery from missing or corrupted files.

    Attributes:
        state_dir: Directory for state files
        projects_path: Path to projects.json
        sessions_path: Path to sessions.json

    Example:
        >>> store = StateStore(Path("~/.claude-mpm/commander"))
        >>> await store.save_projects(registry)
        >>> projects = await store.load_projects()
    """

    VERSION = "1.0"

    def __init__(self, state_dir: Path):
        """Initialize state store.

        Args:
            state_dir: Directory for state files (created if needed)
        """
        self.state_dir = state_dir.expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.projects_path = self.state_dir / "projects.json"
        self.sessions_path = self.state_dir / "sessions.json"
        self.instances_path = self.state_dir / "instances.json"

        logger.info(f"Initialized StateStore at {self.state_dir}")

    async def save_projects(self, registry: ProjectRegistry) -> None:
        """Save all projects to disk (atomic write).

        Args:
            registry: ProjectRegistry to persist

        Raises:
            IOError: If write fails
        """
        projects = registry.list_all()

        data = {
            "version": self.VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "projects": [self._serialize_project(p) for p in projects],
        }

        # Run sync I/O in executor to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None, self._atomic_write, self.projects_path, data
        )

        logger.info(f"Saved {len(projects)} projects to {self.projects_path}")

    async def load_projects(self) -> List[Project]:
        """Load projects from disk.

        Returns:
            List of Project instances (empty if file missing or corrupt)
        """
        if not self.projects_path.exists():
            logger.info("No projects file found, returning empty list")
            return []

        try:
            # Run sync I/O in executor
            data = await asyncio.get_event_loop().run_in_executor(
                None, self._read_json, self.projects_path
            )

            if data.get("version") != self.VERSION:
                logger.warning(
                    f"Version mismatch: expected {self.VERSION}, "
                    f"got {data.get('version')}"
                )

            projects = [self._deserialize_project(p) for p in data.get("projects", [])]

            logger.info(f"Loaded {len(projects)} projects from {self.projects_path}")
            return projects

        except Exception as e:
            logger.error(f"Failed to load projects: {e}", exc_info=True)
            return []

    async def save_sessions(self, sessions: Dict[str, Any]) -> None:
        """Save session states (for recovery).

        Args:
            sessions: Active ProjectSession instances by project_id

        Raises:
            IOError: If write fails
        """
        data = {
            "version": self.VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "sessions": {
                project_id: {
                    "state": session.state.value,
                    "pane_target": session.active_pane,
                    "paused_event_id": session.pause_reason,
                }
                for project_id, session in sessions.items()
            },
        }

        # Run sync I/O in executor
        await asyncio.get_event_loop().run_in_executor(
            None, self._atomic_write, self.sessions_path, data
        )

        logger.info(f"Saved {len(sessions)} sessions to {self.sessions_path}")

    async def load_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Load session states.

        Returns:
            Dict mapping project_id to session state dict
            (empty if file missing or corrupt)
        """
        if not self.sessions_path.exists():
            logger.info("No sessions file found, returning empty dict")
            return {}

        try:
            # Run sync I/O in executor
            data = await asyncio.get_event_loop().run_in_executor(
                None, self._read_json, self.sessions_path
            )

            if data.get("version") != self.VERSION:
                logger.warning(
                    f"Version mismatch: expected {self.VERSION}, "
                    f"got {data.get('version')}"
                )

            sessions = data.get("sessions", {})
            logger.info(f"Loaded {len(sessions)} sessions from {self.sessions_path}")
            return sessions

        except Exception as e:
            logger.error(f"Failed to load sessions: {e}", exc_info=True)
            return {}

    def _atomic_write(self, path: Path, data: Dict) -> None:
        """Write atomically (write to temp, then rename).

        Args:
            path: Target file path
            data: Data to serialize as JSON

        Raises:
            IOError: If write fails
        """
        # Write to temporary file in same directory
        # (ensures atomic rename works across filesystems)
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )

        try:
            with open(fd, "w") as f:
                json.dump(data, f, indent=2)

            # Atomic rename (POSIX guarantees atomicity)
            Path(tmp_path).rename(path)

            logger.debug(f"Atomically wrote to {path}")

        except Exception as e:
            # Clean up temp file on error
            try:
                Path(tmp_path).unlink()
            except Exception:  # nosec B110
                pass  # Ignore errors during cleanup
            raise OSError(f"Failed to write {path}: {e}") from e

    def _read_json(self, path: Path) -> Dict:
        """Read JSON file.

        Args:
            path: File to read

        Returns:
            Parsed JSON data

        Raises:
            IOError: If read fails
        """
        with open(path) as f:
            return json.load(f)

    def _serialize_project(self, project: Project) -> Dict[str, Any]:
        """Serialize Project to JSON-compatible dict.

        Args:
            project: Project instance

        Returns:
            JSON-serializable dict
        """
        return {
            "id": project.id,
            "path": project.path,
            "name": project.name,
            "state": project.state.value,
            "state_reason": project.state_reason,
            "config_loaded": project.config_loaded,
            "config": project.config,
            "sessions": {
                sid: self._serialize_session(session)
                for sid, session in project.sessions.items()
            },
            "created_at": project.created_at.isoformat(),
            "last_activity": project.last_activity.isoformat(),
        }

    def _serialize_session(self, session: ToolSession) -> Dict[str, Any]:
        """Serialize ToolSession to JSON-compatible dict.

        Args:
            session: ToolSession instance

        Returns:
            JSON-serializable dict
        """
        return {
            "id": session.id,
            "project_id": session.project_id,
            "runtime": session.runtime,
            "tmux_target": session.tmux_target,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "last_output_at": (
                session.last_output_at.isoformat() if session.last_output_at else None
            ),
        }

    def _deserialize_project(self, data: Dict[str, Any]) -> Project:
        """Deserialize Project from JSON dict.

        Args:
            data: Serialized project data

        Returns:
            Project instance
        """
        return Project(
            id=data["id"],
            path=data["path"],
            name=data["name"],
            state=ProjectState(data["state"]),
            state_reason=data.get("state_reason"),
            config_loaded=data.get("config_loaded", False),
            config=data.get("config"),
            sessions={
                sid: self._deserialize_session(sess)
                for sid, sess in data.get("sessions", {}).items()
            },
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
        )

    def _deserialize_session(self, data: Dict[str, Any]) -> ToolSession:
        """Deserialize ToolSession from JSON dict.

        Args:
            data: Serialized session data

        Returns:
            ToolSession instance
        """
        return ToolSession(
            id=data["id"],
            project_id=data["project_id"],
            runtime=data["runtime"],
            tmux_target=data["tmux_target"],
            status=data.get("status", "initializing"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_output_at=(
                datetime.fromisoformat(data["last_output_at"])
                if data.get("last_output_at")
                else None
            ),
        )

    # Instance persistence methods

    def save_instances(self, instances: Dict[str, RegisteredInstance]) -> None:
        """Save registered instances to disk.

        Args:
            instances: Dict mapping instance name to RegisteredInstance

        Raises:
            IOError: If write fails
        """
        data = {
            "version": self.VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "instances": {name: inst.to_dict() for name, inst in instances.items()},
        }
        self._atomic_write(self.instances_path, data)
        logger.info(f"Saved {len(instances)} instances to {self.instances_path}")

    def load_instances(self) -> Dict[str, RegisteredInstance]:
        """Load registered instances from disk.

        Returns:
            Dict mapping instance name to RegisteredInstance
            (empty if file missing or corrupt)
        """
        if not self.instances_path.exists():
            logger.info("No instances file found, returning empty dict")
            return {}

        try:
            data = self._read_json(self.instances_path)

            if data.get("version") != self.VERSION:
                logger.warning(
                    f"Version mismatch: expected {self.VERSION}, "
                    f"got {data.get('version')}"
                )

            instances = {
                name: RegisteredInstance.from_dict(inst_data)
                for name, inst_data in data.get("instances", {}).items()
            }

            logger.info(f"Loaded {len(instances)} instances from {self.instances_path}")
            return instances

        except Exception as e:
            logger.error(f"Failed to load instances: {e}", exc_info=True)
            return {}

    def register_instance(self, instance: RegisteredInstance) -> None:
        """Register a single instance (add to existing).

        Args:
            instance: RegisteredInstance to add
        """
        instances = self.load_instances()
        instances[instance.name] = instance
        self.save_instances(instances)
        logger.info(f"Registered instance '{instance.name}'")

    def unregister_instance(self, name: str) -> bool:
        """Remove an instance registration.

        Args:
            name: Instance name to remove

        Returns:
            True if instance was found and removed, False if not found
        """
        instances = self.load_instances()
        if name in instances:
            del instances[name]
            self.save_instances(instances)
            logger.info(f"Unregistered instance '{name}'")
            return True
        logger.warning(f"Instance '{name}' not found for unregistration")
        return False

    def get_registered_instance(self, name: str) -> Optional[RegisteredInstance]:
        """Get a single registered instance by name.

        Args:
            name: Instance name to look up

        Returns:
            RegisteredInstance if found, None otherwise
        """
        instances = self.load_instances()
        return instances.get(name)
