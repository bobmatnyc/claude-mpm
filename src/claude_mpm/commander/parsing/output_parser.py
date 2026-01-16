"""Parse tool output and detect events."""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..events.manager import EventManager
from ..models.events import EventType
from .extractor import (
    extract_action_details,
    extract_error_context,
    extract_options,
    strip_code_blocks,
)
from .patterns import ALL_PATTERNS

logger = logging.getLogger(__name__)

# ANSI escape code pattern
ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


@dataclass
class ParseResult:
    """Result of parsing output."""

    event_type: EventType
    title: str
    content: str
    options: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None
    match_start: int = 0
    match_end: int = 0


class OutputParser:
    """Parses tool output and detects events.

    Detects various event types including:
    - Decisions needed (with option extraction)
    - Approvals required (with action details)
    - Errors (with context)
    - Task completions
    - Clarifications needed

    Features:
    - ANSI escape code stripping
    - Code block exclusion (avoid false positives)
    - Overlap deduplication
    - Option extraction from various formats
    - Integration with EventManager
    """

    def __init__(self, event_manager: Optional[EventManager] = None):
        """Initialize parser.

        Args:
            event_manager: Optional EventManager for automatic event creation
        """
        self.event_manager = event_manager
        self._patterns = ALL_PATTERNS

    def strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes.

        Args:
            text: Text potentially containing ANSI codes

        Returns:
            Text with ANSI codes removed
        """
        return ANSI_ESCAPE.sub("", text)

    def parse(
        self,
        content: str,
        project_id: str,
        session_id: Optional[str] = None,
        create_events: bool = True,
    ) -> List[ParseResult]:
        """Parse output and detect all events.

        Args:
            content: Output content to parse
            project_id: Project identifier for event creation
            session_id: Optional session identifier
            create_events: Whether to create events via EventManager

        Returns:
            List of ParseResult objects for all detected events
        """
        results: List[ParseResult] = []

        # Clean content
        clean_content = self.strip_ansi(content)

        # Strip code blocks for pattern matching
        matchable_content = strip_code_blocks(clean_content)

        # Check each pattern category
        for category, patterns in self._patterns.items():
            for pattern, event_type in patterns:
                for match in pattern.finditer(matchable_content):
                    result = self._create_result(
                        event_type=event_type,
                        match=match,
                        original_content=clean_content,
                        matchable_content=matchable_content,
                    )
                    if result:
                        results.append(result)

        # Deduplicate overlapping results
        results = self._deduplicate(results)

        # Create events if manager provided and flag set
        if self.event_manager and create_events:
            for result in results:
                self.event_manager.create(
                    project_id=project_id,
                    session_id=session_id,
                    event_type=result.event_type,
                    title=result.title,
                    content=result.content,
                    options=result.options,
                    context=result.context,
                )

        logger.debug("Parsed %d events from output", len(results))
        return results

    def _create_result(
        self,
        event_type: EventType,
        match: re.Match,
        original_content: str,
        matchable_content: str,
    ) -> Optional[ParseResult]:
        """Create a ParseResult from a pattern match.

        Args:
            event_type: Type of event detected
            match: Regex match object
            original_content: Original content (with code blocks)
            matchable_content: Content with code blocks stripped

        Returns:
            ParseResult if valid, None otherwise
        """
        matched_text = match.group(0)
        options = None
        context = {}

        # Generate title and extract context based on event type
        if event_type == EventType.ERROR:
            title = self._extract_error_title(matched_text)
            context = extract_error_context(
                original_content, match.start(), match.end()
            )
        elif event_type == EventType.DECISION_NEEDED:
            title = "Decision needed"
            # Look ahead for options (up to 500 chars)
            options = extract_options(
                original_content[match.start() : match.start() + 500]
            )
            context = {"options_detected": len(options) if options else 0}
        elif event_type == EventType.APPROVAL:
            title = "Approval required"
            context = extract_action_details(original_content, match)
            options = ["Yes", "No"]
        elif event_type == EventType.TASK_COMPLETE:
            title = "Task completed"
        elif event_type == EventType.CLARIFICATION:
            title = "Clarification needed"
        else:
            title = f"{event_type.value} detected"

        return ParseResult(
            event_type=event_type,
            title=title,
            content=matched_text[:500],  # Truncate long matches
            options=options
            if event_type in (EventType.DECISION_NEEDED, EventType.APPROVAL)
            else None,
            context=context,
            match_start=match.start(),
            match_end=match.end(),
        )

    def _extract_error_title(self, matched_text: str) -> str:
        """Extract a concise error title.

        Args:
            matched_text: Text that matched the error pattern

        Returns:
            Concise error title (max 80 chars)
        """
        # Try to get the error type and message
        error_match = re.search(
            r"(\w+(?:Error|Exception)): (.+?)(?:\n|$)", matched_text
        )
        if error_match:
            error_type = error_match.group(1)
            error_msg = error_match.group(2)[:50]
            return f"{error_type}: {error_msg}"

        # Fallback to first line
        first_line = matched_text.split("\n")[0].strip()
        return first_line[:80] if first_line else "Error detected"

    def _deduplicate(self, results: List[ParseResult]) -> List[ParseResult]:
        """Remove duplicate or overlapping results.

        When results overlap, keep the one with higher priority.
        Priority order: ERROR > APPROVAL > DECISION > CLARIFICATION > COMPLETION

        Args:
            results: List of ParseResult objects to deduplicate

        Returns:
            Deduplicated list of ParseResult objects
        """
        if not results:
            return results

        # Sort by position
        sorted_results = sorted(results, key=lambda r: r.match_start)

        # Priority order (lower index = higher priority)
        priority_order = [
            EventType.ERROR,
            EventType.APPROVAL,
            EventType.DECISION_NEEDED,
            EventType.CLARIFICATION,
            EventType.TASK_COMPLETE,
        ]

        deduped: List[ParseResult] = []
        for result in sorted_results:
            # Check if overlaps with any existing result
            overlaps = False
            for existing in deduped:
                if (
                    result.match_start < existing.match_end
                    and result.match_end > existing.match_start
                ):
                    # Overlap detected - keep higher priority
                    result_priority = (
                        priority_order.index(result.event_type)
                        if result.event_type in priority_order
                        else 99
                    )
                    existing_priority = (
                        priority_order.index(existing.event_type)
                        if existing.event_type in priority_order
                        else 99
                    )

                    if result_priority < existing_priority:
                        deduped.remove(existing)
                    else:
                        overlaps = True
                    break

            if not overlaps:
                deduped.append(result)

        return deduped
