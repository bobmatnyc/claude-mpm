"""
Git Operations Service Package
================================

Provides Git operations abstraction for PR workflow automation.
Used by agent-improver and skills-manager agents.
"""

from .git_operations_service import (
    GitAuthenticationError,
    GitConflictError,
    GitOperationError,
    GitOperationsService,
)

__all__ = [
    "GitAuthenticationError",
    "GitConflictError",
    "GitOperationError",
    "GitOperationsService",
]
