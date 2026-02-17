"""Core integration components for the mpm-integrate feature.

This module provides the foundational components for API integrations:
- manifest: Integration manifest parsing and validation
- credentials: Credential management with .env wizard
- client: REST and GraphQL HTTP client
- generator: Agent and skill file generation
- mcp_generator: MCP server generation

Example usage:
    from claude_mpm.integrations.core import (
        IntegrationManifest,
        CredentialManager,
        IntegrationClient,
        IntegrationGenerator,
        MCPServerGenerator,
    )

    # Load and validate manifest
    manifest = IntegrationManifest.from_yaml(Path("integration.yaml"))
    errors = manifest.validate()

    # Manage credentials
    creds = CredentialManager()
    api_key = creds.get("API_KEY")

    # Make API calls
    async with IntegrationClient(manifest, credentials) as client:
        result = await client.call_operation("list_users")

    # Generate agent/skill files
    generator = IntegrationGenerator()
    agent_content = generator.generate_agent(manifest)

    # Generate MCP server
    mcp_gen = MCPServerGenerator()
    server_path = mcp_gen.write_server(manifest, manifest_path, output_dir)
"""

from .client import IntegrationClient
from .credentials import CredentialManager
from .generator import IntegrationGenerator
from .manifest import (
    AuthConfig,
    CredentialDefinition,
    HealthCheck,
    IntegrationManifest,
    MCPConfig,
    Operation,
    OperationParameter,
)
from .mcp_generator import MCPServerGenerator

__all__ = [
    "AuthConfig",
    "CredentialDefinition",
    "CredentialManager",
    "HealthCheck",
    "IntegrationClient",
    "IntegrationGenerator",
    "IntegrationManifest",
    "MCPConfig",
    "MCPServerGenerator",
    "Operation",
    "OperationParameter",
]
