"""Session ID management for Claude subprocess optimization."""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
from pathlib import Path

from ..core.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages session IDs for Claude subprocess reuse."""
    
    def __init__(self, session_dir: Optional[Path] = None):
        """Initialize session manager.
        
        Args:
            session_dir: Directory to store session metadata
        """
        self.session_dir = session_dir or Path.home() / ".claude-mpm" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self._load_sessions()
    
    def create_session(self, context: str = "default") -> str:
        """Create a new session ID.
        
        Args:
            context: Context identifier (e.g., "pm_orchestration", "agent_delegation")
            
        Returns:
            UUID session ID
        """
        session_id = str(uuid.uuid4())
        
        self.active_sessions[session_id] = {
            "id": session_id,
            "context": context,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "use_count": 0,
            "agents_run": []
        }
        
        self._save_sessions()
        logger.info(f"Created session {session_id} for context: {context}")
        
        return session_id
    
    def get_or_create_session(self, context: str = "default", max_age_minutes: int = 30) -> str:
        """Get existing session or create new one.
        
        Args:
            context: Context identifier
            max_age_minutes: Maximum age of session to reuse
            
        Returns:
            Session ID
        """
        # Look for existing session in context
        now = datetime.now()
        max_age = timedelta(minutes=max_age_minutes)
        
        for session_id, session_data in self.active_sessions.items():
            if session_data["context"] == context:
                last_used = datetime.fromisoformat(session_data["last_used"])
                if now - last_used < max_age:
                    # Reuse this session
                    session_data["last_used"] = now.isoformat()
                    session_data["use_count"] += 1
                    self._save_sessions()
                    logger.info(f"Reusing session {session_id} for context: {context}")
                    return session_id
        
        # No valid session found, create new one
        return self.create_session(context)
    
    def record_agent_use(self, session_id: str, agent: str, task: str):
        """Record that an agent used this session.
        
        Args:
            session_id: Session ID
            agent: Agent name
            task: Task description
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["agents_run"].append({
                "agent": agent,
                "task": task[:100],  # Truncate long tasks
                "timestamp": datetime.now().isoformat()
            })
            self.active_sessions[session_id]["last_used"] = datetime.now().isoformat()
            self._save_sessions()
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age in hours
        """
        now = datetime.now()
        max_age = timedelta(hours=max_age_hours)
        
        expired = []
        for session_id, session_data in self.active_sessions.items():
            created = datetime.fromisoformat(session_data["created_at"])
            if now - created > max_age:
                expired.append(session_id)
        
        for session_id in expired:
            del self.active_sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
        
        if expired:
            self._save_sessions()
    
    def get_recent_sessions(self, limit: int = 10, context: Optional[str] = None) -> list:
        """Get recent sessions sorted by last used time.
        
        Args:
            limit: Maximum number of sessions to return
            context: Filter by context (optional)
            
        Returns:
            List of session data dictionaries sorted by last_used descending
        """
        sessions = list(self.active_sessions.values())
        
        # Filter by context if specified
        if context:
            sessions = [s for s in sessions if s.get("context") == context]
        
        # Sort by last_used descending (most recent first)
        sessions.sort(key=lambda s: datetime.fromisoformat(s["last_used"]), reverse=True)
        
        return sessions[:limit]
    
    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by ID.
        
        Args:
            session_id: Session ID to look up
            
        Returns:
            Session data dictionary or None if not found
        """
        return self.active_sessions.get(session_id)
    
    def get_last_interactive_session(self) -> Optional[str]:
        """Get the most recently used interactive session ID.
        
        WHY: For --resume without arguments, we want to resume the last
        interactive session (context="default" for regular Claude runs).
        
        Returns:
            Session ID of most recent interactive session, or None if none found
        """
        recent_sessions = self.get_recent_sessions(limit=1, context="default")
        if recent_sessions:
            return recent_sessions[0]["id"]
        return None
    
    def _save_sessions(self):
        """Save sessions to disk."""
        session_file = self.session_dir / "active_sessions.json"
        try:
            with open(session_file, 'w') as f:
                json.dump(self.active_sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")
    
    def _load_sessions(self):
        """Load sessions from disk."""
        session_file = self.session_dir / "active_sessions.json"
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    self.active_sessions = json.load(f)
                    
                # Clean up old sessions on load
                self.cleanup_old_sessions()
            except Exception as e:
                logger.error(f"Failed to load sessions: {e}")
                self.active_sessions = {}


class OrchestrationSession:
    """Context manager for orchestration sessions."""
    
    def __init__(self, session_manager: SessionManager, context: str = "orchestration"):
        """Initialize orchestration session.
        
        Args:
            session_manager: SessionManager instance
            context: Session context
        """
        self.session_manager = session_manager
        self.context = context
        self.session_id: Optional[str] = None
    
    def __enter__(self) -> str:
        """Enter session context, return session ID."""
        self.session_id = self.session_manager.get_or_create_session(self.context)
        return self.session_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit session context."""
        # Could add cleanup here if needed
        pass


# Example usage in subprocess orchestrator:
"""
session_manager = SessionManager()

# In run_non_interactive:
with OrchestrationSession(session_manager, "pm_delegation") as session_id:
    # Run PM with session
    stdout, stderr, returncode = self.launcher.launch_oneshot(
        message=pm_prompt,
        session_id=session_id,  # First call creates context
        timeout=30
    )
    
    # Run agents with same session (reuses context)
    for agent, task in delegations:
        stdout, stderr, returncode = self.launcher.launch_oneshot(
            message=agent_prompt,
            session_id=session_id,  # Reuses PM context!
            timeout=60
        )
        session_manager.record_agent_use(session_id, agent, task)
"""