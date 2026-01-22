"""MCP Service Registry for claude-mpm.

This module provides a registry of known MCP services with their
installation, configuration, and runtime requirements.

WHY: Centralizes MCP service definitions to enable enable/disable/list
operations with automatic configuration generation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar


class InstallMethod(str, Enum):
    """Installation method for MCP services."""

    UVX = "uvx"
    PIPX = "pipx"
    NPX = "npx"
    PIP = "pip"


@dataclass(frozen=True)
class MCPServiceDefinition:
    """Definition of an MCP service with all configuration requirements.

    Attributes:
        name: Unique service identifier (e.g., "kuzu-memory")
        package: PyPI/npm package name for installation
        install_method: How to install (uvx, pipx, npx, pip)
        command: Command to run the service
        args: Default command arguments
        required_env: Environment variables that must be set
        optional_env: Environment variables that may be set
        description: Human-readable description
        env_defaults: Default values for optional env vars
        enabled_by_default: Whether service is enabled by default
    """

    name: str
    package: str
    install_method: InstallMethod
    command: str
    args: list[str] = field(default_factory=list)
    required_env: list[str] = field(default_factory=list)
    optional_env: list[str] = field(default_factory=list)
    description: str = ""
    env_defaults: dict[str, str] = field(default_factory=dict)
    enabled_by_default: bool = False
    oauth_provider: str | None = None  # "google", "microsoft", etc.
    oauth_scopes: list[str] = field(default_factory=list)  # OAuth scopes if applicable


class MCPServiceRegistry:
    """Registry of known MCP services.

    Provides service lookup, configuration generation, and
    enable/disable state management.
    """

    # Registry of all known MCP services
    SERVICES: ClassVar[dict[str, MCPServiceDefinition]] = {}

    @classmethod
    def register(cls, service: MCPServiceDefinition) -> None:
        """Register a service definition."""
        cls.SERVICES[service.name] = service

    @classmethod
    def get(cls, name: str) -> MCPServiceDefinition | None:
        """Get a service definition by name."""
        return cls.SERVICES.get(name)

    @classmethod
    def list_all(cls) -> list[MCPServiceDefinition]:
        """List all registered services."""
        return list(cls.SERVICES.values())

    @classmethod
    def list_names(cls) -> list[str]:
        """List all registered service names."""
        return list(cls.SERVICES.keys())

    @classmethod
    def exists(cls, name: str) -> bool:
        """Check if a service exists in the registry."""
        return name in cls.SERVICES

    @classmethod
    def get_default_enabled(cls) -> list[MCPServiceDefinition]:
        """Get services that are enabled by default."""
        return [s for s in cls.SERVICES.values() if s.enabled_by_default]

    @classmethod
    def generate_config(
        cls,
        service: MCPServiceDefinition,
        env_overrides: dict[str, str] | None = None,
    ) -> dict:
        """Generate MCP configuration for a service.

        Args:
            service: The service definition
            env_overrides: Environment variable overrides

        Returns:
            Configuration dict suitable for .mcp.json or ~/.claude.json
        """
        env = {}

        # Add required env vars (must be provided or have defaults)
        for var in service.required_env:
            if env_overrides and var in env_overrides:
                env[var] = env_overrides[var]
            elif var in service.env_defaults:
                env[var] = service.env_defaults[var]
            # If required and not provided, leave it out - caller should validate

        # Add optional env vars if provided or have defaults
        for var in service.optional_env:
            if env_overrides and var in env_overrides:
                env[var] = env_overrides[var]
            elif var in service.env_defaults:
                env[var] = service.env_defaults[var]

        config: dict = {
            "command": service.command,
            "args": service.args.copy(),
        }

        if env:
            config["env"] = env

        return config

    @classmethod
    def validate_env(
        cls, service: MCPServiceDefinition, env: dict[str, str]
    ) -> tuple[bool, list[str]]:
        """Validate that all required env vars are provided.

        Args:
            service: The service definition
            env: Environment variables to validate

        Returns:
            Tuple of (is_valid, list of missing required vars)
        """
        missing = []
        for var in service.required_env:
            if var not in env and var not in service.env_defaults:
                missing.append(var)
        return len(missing) == 0, missing


# ============================================================================
# Service Definitions
# ============================================================================

# KuzuMemory - Project memory and context management
KUZU_MEMORY = MCPServiceDefinition(
    name="kuzu-memory",
    package="kuzu-memory",
    install_method=InstallMethod.UVX,
    command="uvx",
    args=["kuzu-memory"],
    required_env=[],
    optional_env=["KUZU_DB_PATH", "KUZU_LOG_LEVEL"],
    description="Project memory and context management with graph database",
    env_defaults={},
    enabled_by_default=True,
)

# MCP Ticketer - Ticket and project management
MCP_TICKETER = MCPServiceDefinition(
    name="mcp-ticketer",
    package="mcp-ticketer",
    install_method=InstallMethod.UVX,
    command="uvx",
    args=["mcp-ticketer"],
    required_env=[],
    optional_env=["TICKETER_BACKEND", "GITHUB_TOKEN", "LINEAR_API_KEY"],
    description="Ticket and project management integration",
    env_defaults={},
    enabled_by_default=True,
)

# MCP Vector Search - Code semantic search
MCP_VECTOR_SEARCH = MCPServiceDefinition(
    name="mcp-vector-search",
    package="mcp-vector-search",
    install_method=InstallMethod.UVX,
    command="uvx",
    args=["mcp-vector-search"],
    required_env=[],
    optional_env=["VECTOR_SEARCH_INDEX_PATH"],
    description="Semantic code search with vector embeddings",
    env_defaults={},
    enabled_by_default=True,
)

# Google Workspace MCP - Google Drive, Docs, Sheets integration
# Package: https://pypi.org/project/workspace-mcp/
GOOGLE_WORKSPACE_MCP = MCPServiceDefinition(
    name="workspace-mcp",
    package="workspace-mcp",
    install_method=InstallMethod.UVX,
    command="uvx",
    args=["workspace-mcp", "--tool-tier", "core"],
    required_env=["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"],
    optional_env=[
        "OAUTHLIB_INSECURE_TRANSPORT",
        "USER_GOOGLE_EMAIL",
        "GOOGLE_PSE_API_KEY",
        "GOOGLE_PSE_ENGINE_ID",
    ],
    description="Google Workspace integration (Gmail, Calendar, Drive, Docs, Sheets, Slides)",
    env_defaults={"OAUTHLIB_INSECURE_TRANSPORT": "1"},
    enabled_by_default=False,
    oauth_provider="google",
    oauth_scopes=[
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/spreadsheets",
    ],
)

# MCP GitHub - GitHub repository integration (future)
MCP_GITHUB = MCPServiceDefinition(
    name="mcp-github",
    package="@modelcontextprotocol/server-github",
    install_method=InstallMethod.NPX,
    command="npx",
    args=["-y", "@modelcontextprotocol/server-github"],
    required_env=["GITHUB_PERSONAL_ACCESS_TOKEN"],
    optional_env=[],
    description="GitHub repository integration",
    env_defaults={},
    enabled_by_default=False,
)

# MCP Filesystem - Local filesystem access (future)
MCP_FILESYSTEM = MCPServiceDefinition(
    name="mcp-filesystem",
    package="@modelcontextprotocol/server-filesystem",
    install_method=InstallMethod.NPX,
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem"],
    required_env=[],
    optional_env=["FILESYSTEM_ROOT_PATH"],
    description="Local filesystem access and management",
    env_defaults={},
    enabled_by_default=False,
)

# MCP Skillset - Skills and knowledge management
MCP_SKILLSET = MCPServiceDefinition(
    name="mcp-skillset",
    package="mcp-skillset",
    install_method=InstallMethod.UVX,
    command="uvx",
    args=["mcp-skillset"],
    required_env=[],
    optional_env=["SKILLSET_PATH", "SKILLSET_LOG_LEVEL"],
    description="Skills and knowledge management for Claude",
    env_defaults={},
    enabled_by_default=True,
)


# Register all services
def _register_builtin_services() -> None:
    """Register all built-in service definitions."""
    services = [
        KUZU_MEMORY,
        MCP_TICKETER,
        MCP_VECTOR_SEARCH,
        GOOGLE_WORKSPACE_MCP,
        MCP_GITHUB,
        MCP_FILESYSTEM,
        MCP_SKILLSET,
    ]
    for service in services:
        MCPServiceRegistry.register(service)


# Auto-register on module import
_register_builtin_services()
