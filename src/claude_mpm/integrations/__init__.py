"""Integration utilities for claude-mpm.

This module provides:
- Core integration framework (manifest, credentials, client, generator)
- Platform-specific integrations (Notion, Confluence, etc.)

Example:
    from claude_mpm.integrations.core import (
        IntegrationManifest,
        CredentialManager,
        IntegrationClient,
        IntegrationGenerator,
    )
"""

from .core import (
    AuthConfig,
    CredentialDefinition,
    CredentialManager,
    HealthCheck,
    IntegrationClient,
    IntegrationGenerator,
    IntegrationManifest,
    MCPConfig,
    Operation,
    OperationParameter,
)

__all__ = [
    "AuthConfig",
    "CredentialDefinition",
    "CredentialManager",
    "HealthCheck",
    "IntegrationClient",
    "IntegrationGenerator",
    "IntegrationManifest",
    "MCPConfig",
    "Operation",
    "OperationParameter",
]
