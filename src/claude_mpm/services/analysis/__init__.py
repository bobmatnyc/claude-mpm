"""
Analysis services for Claude MPM.

Provides postmortem analysis, error improvement suggestions, and code clone detection.
"""

from .clone_detector import (
    CloneDetector,
    CloneReport,
    RefactoringSuggestion,
    SimilarityReport,
)
from .postmortem_service import (
    ActionType,
    ErrorAnalysis,
    ErrorCategory,
    ImprovementAction,
    PostmortemReport,
    PostmortemService,
    get_postmortem_service,
)

__all__ = [
    "ActionType",
    "CloneDetector",
    "CloneReport",
    "ErrorAnalysis",
    "ErrorCategory",
    "ImprovementAction",
    "PostmortemReport",
    "PostmortemService",
    "RefactoringSuggestion",
    "SimilarityReport",
    "get_postmortem_service",
]
