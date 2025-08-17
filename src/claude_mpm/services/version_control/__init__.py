"""
Version Control Services - Modular services for Git and version management.

This package provides modular services for the Version Control Agent including:
- Git operations management
- Semantic versioning
- Branch strategy implementation
- Conflict resolution
"""

from .branch_strategy import (
    BranchLifecycleRule,
    BranchNamingRule,
    BranchStrategyManager,
    BranchStrategyType,
    BranchType,
    BranchWorkflow,
)
from .conflict_resolution import (
    ConflictAnalysis,
    ConflictResolution,
    ConflictResolutionManager,
    ConflictType,
    FileConflict,
    ResolutionStrategy,
)
from .git_operations import (
    GitBranchInfo,
    GitOperationError,
    GitOperationResult,
    GitOperationsManager,
)
from .semantic_versioning import (
    ChangeAnalysis,
    SemanticVersion,
    SemanticVersionManager,
    VersionBumpType,
    VersionMetadata,
)

__all__ = [
    # Git Operations
    "GitOperationsManager",
    "GitBranchInfo",
    "GitOperationResult",
    "GitOperationError",
    # Semantic Versioning
    "SemanticVersionManager",
    "SemanticVersion",
    "VersionBumpType",
    "VersionMetadata",
    "ChangeAnalysis",
    # Branch Strategy
    "BranchStrategyManager",
    "BranchStrategyType",
    "BranchType",
    "BranchWorkflow",
    "BranchNamingRule",
    "BranchLifecycleRule",
    # Conflict Resolution
    "ConflictResolutionManager",
    "ConflictType",
    "ResolutionStrategy",
    "FileConflict",
    "ConflictResolution",
    "ConflictAnalysis",
]
