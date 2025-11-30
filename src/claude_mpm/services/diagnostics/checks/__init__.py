"""
Diagnostic checks for claude-mpm doctor command.

WHY: Modular checks allow for easy extension and testing of individual
diagnostic components.
"""

from .agent_check import AgentCheck
from .agent_sources_check import AgentSourcesCheck
from .base_check import BaseDiagnosticCheck
from .claude_code_check import ClaudeCodeCheck
from .common_issues_check import CommonIssuesCheck
from .configuration_check import ConfigurationCheck
from .filesystem_check import FilesystemCheck
from .installation_check import InstallationCheck
from .instructions_check import InstructionsCheck
from .mcp_check import MCPCheck
from .mcp_services_check import MCPServicesCheck
from .monitor_check import MonitorCheck
from .skill_sources_check import SkillSourcesCheck
from .startup_log_check import StartupLogCheck

__all__ = [
    "AgentCheck",
    "AgentSourcesCheck",
    "BaseDiagnosticCheck",
    "ClaudeCodeCheck",
    "CommonIssuesCheck",
    "ConfigurationCheck",
    "FilesystemCheck",
    "InstallationCheck",
    "InstructionsCheck",
    "MCPCheck",
    "MCPServicesCheck",
    "MonitorCheck",
    "SkillSourcesCheck",
    "StartupLogCheck",
]
