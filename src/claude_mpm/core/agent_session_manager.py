"""Agent-specific session management for performance optimization."""

import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from ..core.logger import get_logger

logger = get_logger(__name__)


class AgentSessionManager:
    """Manages separate sessions for each agent type to avoid context pollution."""

    def __init__(
        self, session_dir: Optional[Path] = None, max_sessions_per_agent: int = 3
    ):
        """Initialize agent session manager.

        Args:
            session_dir: Directory to store session metadata
            max_sessions_per_agent: Maximum concurrent sessions per agent type
        """
        self.session_dir = session_dir or Path.home() / ".claude-mpm" / "agent_sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.max_sessions_per_agent = max_sessions_per_agent

        # Sessions organized by agent type
        self.agent_sessions: Dict[str, Dict[str, Dict]] = defaultdict(dict)
        self.session_locks: Dict[str, bool] = {}  # Track which sessions are in use

        self._load_sessions()

    def get_agent_session(
        self, agent_type: str, create_if_missing: bool = True
    ) -> Optional[str]:
        """Get or create a session for a specific agent type.

        Args:
            agent_type: Type of agent (e.g., "engineer", "qa", "documentation")
            create_if_missing: Whether to create a new session if none available

        Returns:
            Session ID or None
        """
        agent_type = agent_type.lower()

        # Find an available session for this agent
        for session_id, session_data in self.agent_sessions[agent_type].items():
            if not self.session_locks.get(session_id, False):
                # Check if session is still fresh (not too old)
                created = datetime.fromisoformat(session_data["created_at"])
                if datetime.now() - created < timedelta(hours=1):
                    # Use this session
                    self.session_locks[session_id] = True
                    session_data["last_used"] = datetime.now().isoformat()
                    session_data["use_count"] += 1
                    logger.info(f"Reusing session {session_id} for {agent_type} agent")
                    return session_id

        # No available session, create new one if allowed
        if (
            create_if_missing
            and len(self.agent_sessions[agent_type]) < self.max_sessions_per_agent
        ):
            return self.create_agent_session(agent_type)

        return None

    def create_agent_session(self, agent_type: str) -> str:
        """Create a new session for a specific agent type.

        Args:
            agent_type: Type of agent

        Returns:
            New session ID
        """
        session_id = str(uuid.uuid4())
        agent_type = agent_type.lower()

        session_data = {
            "id": session_id,
            "agent_type": agent_type,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "use_count": 0,
            "tasks_completed": [],
        }

        self.agent_sessions[agent_type][session_id] = session_data
        self.session_locks[session_id] = True
        self._save_sessions()

        logger.info(f"Created new session {session_id} for {agent_type} agent")
        return session_id

    def release_session(self, session_id: str):
        """Release a session back to the pool.

        Args:
            session_id: Session to release
        """
        if session_id in self.session_locks:
            self.session_locks[session_id] = False
            logger.debug(f"Released session {session_id}")

    def record_task(self, session_id: str, task: str, success: bool = True):
        """Record a task completion for a session.

        Args:
            session_id: Session ID
            task: Task description
            success: Whether task completed successfully
        """
        # Find which agent this session belongs to
        for _agent_type, sessions in self.agent_sessions.items():
            if session_id in sessions:
                sessions[session_id]["tasks_completed"].append(
                    {
                        "task": task[:100],  # Truncate long tasks
                        "timestamp": datetime.now().isoformat(),
                        "success": success,
                    }
                )
                self._save_sessions()
                break

    def cleanup_old_sessions(self, max_age_hours: int = 4):
        """Remove sessions older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours
        """
        now = datetime.now()
        max_age = timedelta(hours=max_age_hours)

        for agent_type in list(self.agent_sessions.keys()):
            expired = []
            for session_id, session_data in self.agent_sessions[agent_type].items():
                created = datetime.fromisoformat(session_data["created_at"])
                if now - created > max_age:
                    expired.append(session_id)

            for session_id in expired:
                del self.agent_sessions[agent_type][session_id]
                if session_id in self.session_locks:
                    del self.session_locks[session_id]
                logger.info(f"Cleaned up expired {agent_type} session: {session_id}")

        if any(self.agent_sessions.values()):
            self._save_sessions()

    def get_session_stats(self) -> Dict[str, Dict]:
        """Get statistics about current sessions.

        Returns:
            Stats by agent type
        """
        stats = {}
        for agent_type, sessions in self.agent_sessions.items():
            active = sum(1 for sid in sessions if self.session_locks.get(sid, False))
            total_tasks = sum(len(s["tasks_completed"]) for s in sessions.values())

            stats[agent_type] = {
                "total_sessions": len(sessions),
                "active_sessions": active,
                "available_sessions": len(sessions) - active,
                "total_tasks_completed": total_tasks,
            }

        return stats

    def initialize_agent_session(self, agent_type: str, session_id: str) -> str:
        """Initialize a session with agent-specific context.

        Args:
            agent_type: Type of agent
            session_id: Session ID to initialize

        Returns:
            Initialization prompt for the agent
        """
        # This prompt establishes the agent's identity for the session
        initialization_prompts = {
            "engineer": "You are the Engineer Agent. Your role is code implementation and development. Confirm with 'Engineer Agent ready.'",
            "qa": "You are the QA Agent. Your role is testing and quality assurance. Confirm with 'QA Agent ready.'",
            "documentation": "You are the Documentation Agent. Your role is creating and maintaining documentation. Confirm with 'Documentation Agent ready.'",
            "research": "You are the Research Agent. Your role is investigation and analysis. Confirm with 'Research Agent ready.'",
            "security": "You are the Security Agent. Your role is security analysis and protection. Confirm with 'Security Agent ready.'",
            "ops": "You are the Ops Agent. Your role is deployment and operations. Confirm with 'Ops Agent ready.'",
            "data_engineer": "You are the Data Engineer Agent. Your role is data management and processing. Confirm with 'Data Engineer Agent ready.'",
            "version_control": "You are the Version Control Agent. Your role is Git operations and version management. Confirm with 'Version Control Agent ready.'",
        }

        return initialization_prompts.get(
            agent_type.lower(),
            f"You are the {agent_type} Agent. Confirm with '{agent_type} Agent ready.'",
        )

    def _save_sessions(self):
        """Save sessions to disk."""
        session_file = self.session_dir / "agent_sessions.json"
        try:
            data = {
                "agent_sessions": dict(self.agent_sessions),
                "updated_at": datetime.now().isoformat(),
            }
            with open(session_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save agent sessions: {e}")

    def _load_sessions(self):
        """Load sessions from disk."""
        session_file = self.session_dir / "agent_sessions.json"
        if session_file.exists():
            try:
                with open(session_file) as f:
                    data = json.load(f)
                    self.agent_sessions = defaultdict(
                        dict, data.get("agent_sessions", {})
                    )

                # Clean up old sessions on load
                self.cleanup_old_sessions()
            except Exception as e:
                logger.error(f"Failed to load agent sessions: {e}")
                self.agent_sessions = defaultdict(dict)


# Example usage in SubprocessOrchestrator:
"""
class SubprocessOrchestrator:
    def __init__(self, ...):
        self.agent_session_manager = AgentSessionManager()
        # Pre-warm common agent sessions on startup
        self._prewarm_agent_sessions()

    def _prewarm_agent_sessions(self):
        '''Pre-warm sessions for common agents.'''
        common_agents = ['engineer', 'qa', 'documentation']
        for agent in common_agents:
            session_id = self.agent_session_manager.create_agent_session(agent)
            # Initialize the session with agent identity
            init_prompt = self.agent_session_manager.initialize_agent_session(agent, session_id)
            self.launcher.launch_oneshot(
                message=init_prompt,
                session_id=session_id,
                timeout=10
            )
            self.agent_session_manager.release_session(session_id)

    def run_subprocess(self, agent: str, task: str) -> Tuple[str, float, int]:
        # Get a session for this agent type
        session_id = self.agent_session_manager.get_agent_session(agent)

        try:
            # Create agent prompt (without role definition since session knows)
            prompt = f'''
## Current Task
{task}

## Response Format
Provide a clear, structured response that completes the requested task.
'''

            # Run with agent-specific session
            stdout, stderr, returncode = self.launcher.launch_oneshot(
                message=prompt,
                session_id=session_id,  # Reuses agent-specific context!
                timeout=60
            )

            # Record task completion
            self.agent_session_manager.record_task(session_id, task, returncode == 0)

        finally:
            # Release session back to pool
            self.agent_session_manager.release_session(session_id)
"""
