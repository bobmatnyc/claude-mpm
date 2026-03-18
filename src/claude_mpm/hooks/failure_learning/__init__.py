#!/usr/bin/env python3
"""
Failure-Learning Hook System
=============================

Automatic learning extraction from failure-fix cycles.

WHY: When tasks fail and agents fix them, valuable knowledge is created. This
hook system automatically captures failures, detects fixes, and extracts learnings
without requiring manual intervention.

Components:
- FailureDetectionHook (priority 85): Detects task failures from tool outputs
- FixDetectionHook (priority 87): Matches successful executions with failures
- LearningExtractionHook (priority 89): Synthesizes and persists learnings

Integration:
The hooks work together as a chain:
1. Tool executes and fails → FailureDetectionHook records failure
2. User or agent makes changes
3. Tool executes and succeeds → FixDetectionHook detects fix
4. Fix matched with failure → LearningExtractionHook creates learning
5. Learning written to agent memory file

Usage:
    from claude_mpm.hooks.failure_learning import (
        get_failure_detection_hook,
        get_fix_detection_hook,
        get_learning_extraction_hook,
    )

    # Register hooks with hook service
    hook_service.register_hook(get_failure_detection_hook())
    hook_service.register_hook(get_fix_detection_hook())
    hook_service.register_hook(get_learning_extraction_hook())
"""

from .failure_detection_hook import FailureDetectionHook, get_failure_detection_hook
from .fix_detection_hook import FixDetectionHook, get_fix_detection_hook
from .learning_extraction_hook import (
    LearningExtractionHook,
    get_learning_extraction_hook,
)

__all__ = [
    # Hooks
    "FailureDetectionHook",
    "FixDetectionHook",
    "LearningExtractionHook",
    # Factory functions
    "get_failure_detection_hook",
    "get_fix_detection_hook",
    "get_learning_extraction_hook",
]
