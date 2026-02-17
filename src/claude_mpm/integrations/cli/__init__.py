"""CLI commands for integrations (ISS-0011).

This module provides CLI commands for managing API integrations,
including listing, adding, removing, and configuring integrations.

Example:
    # List available integrations
    claude-mpm integrate list

    # Add integration from catalog
    claude-mpm integrate add jsonplaceholder

    # Remove integration
    claude-mpm integrate remove jsonplaceholder
"""

from .integrate import IntegrationManager, manage_integrations

__all__ = [
    "IntegrationManager",
    "manage_integrations",
]
