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
    UPGRADE = "upgrade"
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
    BRAVE_SEARCH = "brave-search"
    TAVILY = "tavily"
    FIRECRAWL = "firecrawl"

    def __str__(self) -> str:
        return self.value


class MCPConfigKey(str, Enum):
    """Keys used in .mcp.json configuration files."""

    MCP_SERVERS = "mcpServers"
    TYPE = "type"
    COMMAND = "command"
    ARGS = "args"
    ENV = "env"

    def __str__(self) -> str:
        return self.value


class MCPServerType(str, Enum):
    """MCP server types."""

    STDIO = "stdio"

    def __str__(self) -> str:
        return self.value


class MCPBinary(str, Enum):
    """MCP server binary/command names (installed executables)."""

    GOOGLE_WORKSPACE = "gworkspace-mcp"
    KUZU_MEMORY = "kuzu-memory"
    MCP_TICKETER = "mcp-ticketer"
    MCP_VECTOR_SEARCH = "mcp-vector-search"
    MCP_SKILLSET = "mcp-skillset"

    def __str__(self) -> str:
        return self.value


class MCPSubcommand(str, Enum):
    """Common MCP subcommands."""

    MCP = "mcp"
    SETUP = "setup"

    def __str__(self) -> str:
        return self.value


class TicketStatus(str, Enum):
    """Ticket/issue status values."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    TESTING = "testing"
    CLOSED = "closed"
    ALL = "all"

    def __str__(self) -> str:
        return self.value


# Global flags that can appear without a preceding service
GLOBAL_SETUP_FLAGS = {SetupFlag.NO_LAUNCH}

# Flags that require a value
VALUE_FLAGS = {SetupFlag.OAUTH_SERVICE}
