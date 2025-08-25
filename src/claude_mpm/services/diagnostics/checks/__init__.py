"""
Diagnostic checks for claude-mpm doctor command.

WHY: Modular checks allow for easy extension and testing of individual
diagnostic components.
"""

from .agent_check import AgentCheck
from .base_check import BaseDiagnosticCheck
from .claude_desktop_check import ClaudeDesktopCheck
from .common_issues_check import CommonIssuesCheck
from .configuration_check import ConfigurationCheck
from .filesystem_check import FilesystemCheck
from .installation_check import InstallationCheck
from .instructions_check import InstructionsCheck
from .mcp_check import MCPCheck
from .monitor_check import MonitorCheck
from .startup_log_check import StartupLogCheck

__all__ = [
    "AgentCheck",
    "BaseDiagnosticCheck",
    "ClaudeDesktopCheck",
    "CommonIssuesCheck",
    "ConfigurationCheck",
    "FilesystemCheck",
    "InstallationCheck",
    "InstructionsCheck",
    "MCPCheck",
    "MonitorCheck",
    "StartupLogCheck",
]
