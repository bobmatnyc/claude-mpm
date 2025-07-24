"""
Version Control Services - Modular services for Git and version management.

This package provides modular services for the Version Control Agent including:
- Git operations management
- Semantic versioning
- Branch strategy implementation
- Conflict resolution
"""

from .git_operations import (
    GitOperationsManager,
    GitBranchInfo,
    GitOperationResult,
    GitOperationError,
)

from .semantic_versioning import (
    SemanticVersionManager,
    SemanticVersion,
    VersionBumpType,
    VersionMetadata,
    ChangeAnalysis,
)

from .branch_strategy import (
    BranchStrategyManager,
    BranchStrategyType,
    BranchType,
    BranchWorkflow,
    BranchNamingRule,
    BranchLifecycleRule,
)

from .conflict_resolution import (
    ConflictResolutionManager,
    ConflictType,
    ResolutionStrategy,
    FileConflict,
    ConflictResolution,
    ConflictAnalysis,
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
