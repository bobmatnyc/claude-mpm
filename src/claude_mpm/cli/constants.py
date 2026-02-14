"""
CLI constants and enums for claude-mpm.

WHY: Avoid magic strings throughout the CLI codebase.
"""

from enum import Enum


class SetupFlag(str, Enum):
    """Flags for the setup command."""

    NO_LAUNCH = "no_launch"
    NO_BROWSER = "no_browser"
    FORCE = "force"
    OAUTH_SERVICE = "oauth_service"

    def __str__(self) -> str:
        return self.value

    @property
    def cli_flag(self) -> str:
        """Return the CLI flag format (e.g., --no-launch)."""
        return f"--{self.value.replace('_', '-')}"


class SetupService(str, Enum):
    """Valid services for the setup command."""

    SLACK = "slack"
    GWORKSPACE_MCP = "gworkspace-mcp"
    OAUTH = "oauth"
    KUZU_MEMORY = "kuzu-memory"
    MCP_VECTOR_SEARCH = "mcp-vector-search"
    MCP_SKILLSET = "mcp-skillset"
    MCP_TICKETER = "mcp-ticketer"
    NOTION = "notion"
    CONFLUENCE = "confluence"

    def __str__(self) -> str:
        return self.value


# Global flags that can appear without a preceding service
GLOBAL_SETUP_FLAGS = {SetupFlag.NO_LAUNCH}

# Flags that require a value
VALUE_FLAGS = {SetupFlag.OAUTH_SERVICE}
