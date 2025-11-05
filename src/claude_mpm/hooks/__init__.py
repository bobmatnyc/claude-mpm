"""Hook system for claude-mpm."""

from .base_hook import BaseHook, HookContext, HookResult, HookType
from .failure_learning import (
    FailureDetectionHook,
    FixDetectionHook,
    LearningExtractionHook,
    get_failure_detection_hook,
    get_fix_detection_hook,
    get_learning_extraction_hook,
)
from .kuzu_enrichment_hook import KuzuEnrichmentHook, get_kuzu_enrichment_hook
from .kuzu_memory_hook import KuzuMemoryHook, get_kuzu_memory_hook
from .kuzu_response_hook import KuzuResponseHook, get_kuzu_response_hook
from .session_resume_hook import (
    SessionResumeStartupHook,
    get_session_resume_hook,
    trigger_session_resume_check,
)

__all__ = [
    "BaseHook",
    "FailureDetectionHook",
    "FixDetectionHook",
    "HookContext",
    "HookResult",
    "HookType",
    "KuzuEnrichmentHook",
    "KuzuMemoryHook",
    "KuzuResponseHook",
    "LearningExtractionHook",
    "SessionResumeStartupHook",
    "get_failure_detection_hook",
    "get_fix_detection_hook",
    "get_kuzu_enrichment_hook",
    "get_kuzu_memory_hook",
    "get_kuzu_response_hook",
    "get_learning_extraction_hook",
    "get_session_resume_hook",
    "trigger_session_resume_check",
]
