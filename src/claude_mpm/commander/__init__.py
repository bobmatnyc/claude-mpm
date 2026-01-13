"""MPM Commander - Multi-Project Orchestration.

This module provides the core infrastructure for managing multiple projects
with isolated state, work queues, and tool sessions.

Key Components:
    - ProjectRegistry: Thread-safe project management
    - Project models: Data structures for state and sessions
    - TmuxOrchestrator: Tmux session and pane management
    - Config loading: .claude-mpm/ directory configuration
    - CommanderDaemon: Main daemon process for orchestration
    - ProjectSession: Per-project lifecycle management

Example:
    >>> from claude_mpm.commander import ProjectRegistry
    >>> registry = ProjectRegistry()
    >>> project = registry.register("/path/to/project")
    >>> registry.update_state(project.id, ProjectState.WORKING)
"""

from claude_mpm.commander.config import DaemonConfig
from claude_mpm.commander.config_loader import load_project_config
from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models import (
    Project,
    ProjectState,
    ThreadMessage,
    ToolSession,
)
from claude_mpm.commander.project_session import ProjectSession, SessionState
from claude_mpm.commander.registry import ProjectRegistry
from claude_mpm.commander.tmux_orchestrator import (
    TmuxNotFoundError,
    TmuxOrchestrator,
)

__all__ = [
    "CommanderDaemon",
    "DaemonConfig",
    "Project",
    "ProjectRegistry",
    "ProjectSession",
    "ProjectState",
    "SessionState",
    "ThreadMessage",
    "TmuxNotFoundError",
    "TmuxOrchestrator",
    "ToolSession",
    "load_project_config",
]
