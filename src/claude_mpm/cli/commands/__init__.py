"""
CLI commands for claude-mpm.

WHY: This package contains individual command implementations, organized into
separate modules for better maintainability and code organization.
"""

from .agent_manager import manage_agent_manager
from .agents import manage_agents
from .aggregate import aggregate_command
from .analyze import analyze_command
from .analyze_code import AnalyzeCodeCommand
from .cleanup import cleanup_memory
from .config import manage_config
from .configure import manage_configure
from .debug import manage_debug
from .doctor import run_doctor
from .info import show_info
from .mcp import manage_mcp
from .memory import manage_memory
from .monitor import manage_monitor
from .run import run_session
from .tickets import list_tickets, manage_tickets

__all__ = [
    "AnalyzeCodeCommand",
    "aggregate_command",
    "analyze_command",
    "cleanup_memory",
    "list_tickets",
    "manage_agent_manager",
    "manage_agents",
    "manage_config",
    "manage_configure",
    "manage_debug",
    "manage_mcp",
    "manage_memory",
    "manage_monitor",
    # 'run_guarded_session',  # Excluded from default exports (experimental)
    "manage_tickets",
    "run_doctor",
    "run_session",
    "show_info",
]
