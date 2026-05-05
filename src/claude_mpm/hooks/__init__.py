"""Hook system for claude-mpm."""

from . import context_circuit_breaker, permission_policy
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
from .message_check_hook import get_message_check_hook, message_check_hook
from .permission_policy import evaluate as evaluate_permission
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
    "context_circuit_breaker",
    "evaluate_permission",
    "get_failure_detection_hook",
    "get_fix_detection_hook",
    "get_kuzu_enrichment_hook",
    "get_kuzu_memory_hook",
    "get_kuzu_response_hook",
    "get_learning_extraction_hook",
    "get_message_check_hook",
    "get_session_resume_hook",
    "message_check_hook",
    "permission_policy",
    "trigger_session_resume_check",
]
