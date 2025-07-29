"""
Agent models package.

WHY: This package centralizes all data models used for agent management,
providing a single source of truth for data structures across the system.
"""

from .agent_definition import (
    AgentDefinition,
    AgentMetadata,
    AgentType,
    AgentSection,
    AgentWorkflow,
    AgentPermissions
)

__all__ = [
    'AgentDefinition',
    'AgentMetadata',
    'AgentType',
    'AgentSection',
    'AgentWorkflow',
    'AgentPermissions'
]