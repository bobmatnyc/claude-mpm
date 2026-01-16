"""Detection patterns for various event types in tool output."""

import re
from typing import List, Tuple

from ..models.events import EventType

# Pattern format: (compiled_regex, event_type)

DECISION_PATTERNS: List[Tuple[re.Pattern, EventType]] = [
    (
        re.compile(
            r"Which (?:option|approach|method) (?:would you|do you) prefer\?", re.I
        ),
        EventType.DECISION_NEEDED,
    ),
    (
        re.compile(
            r"Should I (?:proceed|continue|use|implement) (?:with )?(.+)\?", re.I
        ),
        EventType.DECISION_NEEDED,
    ),
    (re.compile(r"Do you want me to (.+)\?", re.I), EventType.DECISION_NEEDED),
    (
        re.compile(r"Please choose:?\s*\n(?:\s*\d+[\.\)]\s*.+\n?)+", re.I | re.M),
        EventType.DECISION_NEEDED,
    ),
    (
        re.compile(r"Options:?\s*\n(?:\s*[-•]\s*.+\n?)+", re.I | re.M),
        EventType.DECISION_NEEDED,
    ),
    (re.compile(r"\(y/n\)\??", re.I), EventType.DECISION_NEEDED),
    (re.compile(r"\[Y/n\]", re.I), EventType.DECISION_NEEDED),
    (re.compile(r"\[yes/no\]", re.I), EventType.DECISION_NEEDED),
    (re.compile(r"Select an option:", re.I), EventType.DECISION_NEEDED),
]

APPROVAL_PATTERNS: List[Tuple[re.Pattern, EventType]] = [
    (
        re.compile(r"This will (?:delete|remove|overwrite|modify) (.+)", re.I),
        EventType.APPROVAL,
    ),
    (re.compile(r"Are you sure you want to (.+)\?", re.I), EventType.APPROVAL),
    (re.compile(r"This action cannot be undone", re.I), EventType.APPROVAL),
    (re.compile(r"Warning: This will (.+)", re.I), EventType.APPROVAL),
    (re.compile(r"Do you want to allow (.+)\?", re.I), EventType.APPROVAL),
    (re.compile(r"Permanently delete", re.I), EventType.APPROVAL),
]

ERROR_PATTERNS: List[Tuple[re.Pattern, EventType]] = [
    (re.compile(r"Traceback \(most recent call last\):", re.I), EventType.ERROR),
    (re.compile(r"(\w+Error): (.+)", re.I), EventType.ERROR),
    (re.compile(r"(\w+Exception): (.+)", re.I), EventType.ERROR),
    (re.compile(r"^Error: (.+)", re.I | re.M), EventType.ERROR),
    (re.compile(r"^Failed: (.+)", re.I | re.M), EventType.ERROR),
    (re.compile(r"^FATAL: (.+)", re.I | re.M), EventType.ERROR),
    (re.compile(r"Permission denied", re.I), EventType.ERROR),
    (re.compile(r"Access denied", re.I), EventType.ERROR),
    (re.compile(r"(?:File|Directory) not found", re.I), EventType.ERROR),
    (re.compile(r"Connection refused", re.I), EventType.ERROR),
    (re.compile(r"Timeout(?:Error)?", re.I), EventType.ERROR),
    (re.compile(r"✗", re.I), EventType.ERROR),  # Claude Code error indicator
]

COMPLETION_PATTERNS: List[Tuple[re.Pattern, EventType]] = [
    (
        re.compile(r"(?:Done|Complete|Finished|Success)[\.\!]?\s*$", re.I | re.M),
        EventType.TASK_COMPLETE,
    ),
    (re.compile(r"Successfully (.+)", re.I), EventType.TASK_COMPLETE),
    (
        re.compile(r"I(?:'ve| have) (?:completed|finished|done) (.+)", re.I),
        EventType.TASK_COMPLETE,
    ),
    (re.compile(r"Task (?:complete|finished)", re.I), EventType.TASK_COMPLETE),
]

CLARIFICATION_PATTERNS: List[Tuple[re.Pattern, EventType]] = [
    (
        re.compile(
            r"Could you (?:please )?(?:clarify|explain|provide more details)", re.I
        ),
        EventType.CLARIFICATION,
    ),
    (re.compile(r"I need more information about", re.I), EventType.CLARIFICATION),
    (re.compile(r"What do you mean by", re.I), EventType.CLARIFICATION),
    (re.compile(r"Can you be more specific", re.I), EventType.CLARIFICATION),
]

# Patterns to ignore (inside code blocks, etc.)
CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```", re.M)
INLINE_CODE_PATTERN = re.compile(r"`[^`]+`")

ALL_PATTERNS = {
    "decision": DECISION_PATTERNS,
    "approval": APPROVAL_PATTERNS,
    "error": ERROR_PATTERNS,
    "completion": COMPLETION_PATTERNS,
    "clarification": CLARIFICATION_PATTERNS,
}
