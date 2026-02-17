"""MCP Service Registry for claude-mpm.

This module provides a registry of known MCP services with their
installation, configuration, and runtime requirements.

WHY: Centralizes MCP service definitions to enable enable/disable/list
operations with automatic configuration generation.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar


class InstallMethod(str, Enum):
    """Installation method for MCP services."""

    UVX = "uvx"
    PIPX = "pipx"
    NPX = "npx"
    PIP = "pip"
    INTERNAL = "internal"  # Internal server, installed via console script


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
    package: str | None  # None for internal servers
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


def _load_env_from_files(var_names: list[str]) -> dict[str, str]:
    """Load environment variables from .env.local and .env files.

    Checks in priority order:
    1. Current environment variables (os.environ)
    2. .env.local in current directory
    3. .env in current directory

    Args:
        var_names: List of environment variable names to look for

    Returns:
        Dict of found environment variables and their values
    """
    result: dict[str, str] = {}

    # Check environment variables first
    for var in var_names:
        if var in os.environ:
            result[var] = os.environ[var]

    # Check .env files for remaining vars
    remaining = [v for v in var_names if v not in result]
    if not remaining:
        return result

    for env_file in [".env.local", ".env"]:
        env_path = Path.cwd() / env_file
        if env_path.exists():
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key in remaining and key not in result:
                                result[key] = value
            except Exception:  # nosec B110 - intentionally ignore .env file read errors
                pass

    return result


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
        load_from_env_files: bool = True,
    ) -> dict:
        """Generate MCP configuration for a service.

        Args:
            service: The service definition
            env_overrides: Environment variable overrides
            load_from_env_files: If True, auto-load from .env.local/.env

        Returns:
            Configuration dict suitable for .mcp.json or ~/.claude.json
        """
        env: dict[str, str] = {}

        # Auto-load from .env files if enabled
        if load_from_env_files:
            all_vars = service.required_env + service.optional_env
            env_from_files = _load_env_from_files(all_vars)
            env.update(env_from_files)

        # Apply explicit overrides (highest priority)
        if env_overrides:
            env.update(env_overrides)

        # Apply defaults for any remaining missing vars
        for var in service.required_env + service.optional_env:
            if var not in env and var in service.env_defaults:
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
# Package: https://pypi.org/project/gworkspace-mcp/ (v0.1.2+)
# Entry points: 'workspace' or 'gworkspace-mcp'
GOOGLE_WORKSPACE_MCP = MCPServiceDefinition(
    name="gworkspace-mcp",  # Canonical service name (matches package)
    package="gworkspace-mcp",  # PyPI package name
    install_method=InstallMethod.UVX,
    command="gworkspace-mcp",  # Entry point command (installed by package)
    args=[],  # No additional args needed (tool-tier removed)
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
        "https://www.googleapis.com/auth/tasks",
    ],
)

# Slack User Proxy - Internal MCP server for Slack user token operations
SLACK_USER_PROXY = MCPServiceDefinition(
    name="slack-user-proxy",
    package=None,  # Internal server
    install_method=InstallMethod.INTERNAL,
    command="slack-user-proxy",
    args=[],
    required_env=["SLACK_OAUTH_CLIENT_ID", "SLACK_OAUTH_CLIENT_SECRET"],
    optional_env=[],
    description="Slack user proxy for channels, messages, DMs, and search",
    enabled_by_default=False,
    oauth_provider="slack",
    oauth_scopes=[
        "channels:read",
        "channels:history",
        "groups:read",
        "groups:history",
        "im:read",
        "im:history",
        "mpim:read",
        "mpim:history",
        "chat:write",
        "users:read",
        "users:read.email",
        "team:read",
        "search:read",
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

# Notion MCP - Official Notion integration
# Package: https://www.npmjs.com/package/@notionhq/notion-mcp-server
NOTION_MCP = MCPServiceDefinition(
    name="notion-mcp",
    package=None,  # Internal server
    install_method=InstallMethod.INTERNAL,
    command="notion-mcp",
    args=[],
    required_env=["NOTION_API_KEY"],
    optional_env=["NOTION_DATABASE_ID"],
    description="Notion integration for databases, pages, and content with markdown import",
    enabled_by_default=False,
)

# Confluence - Internal MCP server for Confluence operations
CONFLUENCE_MCP = MCPServiceDefinition(
    name="confluence-mcp",
    package=None,  # Internal server
    install_method=InstallMethod.INTERNAL,
    command="confluence-mcp",
    args=[],
    required_env=["CONFLUENCE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN"],
    optional_env=[],
    description="Confluence integration for pages, spaces, and content with markdown import",
    enabled_by_default=False,
)

# MCP LSP - Language Server Protocol integration for code intelligence
# Package: https://www.npmjs.com/package/@axivo/mcp-lsp
MCP_LSP = MCPServiceDefinition(
    name="mcp-lsp",
    package="@axivo/mcp-lsp",
    install_method=InstallMethod.NPX,
    command="npx",
    args=["-y", "@axivo/mcp-lsp"],
    required_env=["LSP_FILE_PATH"],
    optional_env=[],
    description="Language Server Protocol integration for code intelligence (40+ tools)",
    enabled_by_default=False,
)


# Register all services
def _register_builtin_services() -> None:
    """Register all built-in service definitions."""
    services = [
        KUZU_MEMORY,
        MCP_TICKETER,
        MCP_VECTOR_SEARCH,
        GOOGLE_WORKSPACE_MCP,
        SLACK_USER_PROXY,
        MCP_GITHUB,
        MCP_FILESYSTEM,
        MCP_SKILLSET,
        NOTION_MCP,
        CONFLUENCE_MCP,
        MCP_LSP,
    ]
    for service in services:
        MCPServiceRegistry.register(service)


# Auto-register on module import
_register_builtin_services()
