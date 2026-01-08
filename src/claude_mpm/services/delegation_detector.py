"""Delegation Pattern Detector for PM outputs.

WHY this is needed:
- Detect when PM asks user to do something manually instead of delegating
- Convert manual instructions into actionable autotodos
- Enforce delegation principle in PM workflow
- Help PM recognize delegation opportunities

DESIGN DECISION: Pattern-based detection
- Simple regex patterns to catch common delegation anti-patterns
- Extract action items from PM's output
- Format as autotodos for PM to see and delegate properly
- Non-invasive - just surfaces patterns for review

Examples of patterns to detect:
- "Make sure .env.local is in your .gitignore"
- "You'll need to run npm install"
- "Please run the tests manually"
- "Remember to update the README"
- "Don't forget to commit your changes"
"""

import re
from typing import Any, Dict, List, Tuple

from ..core.logger import get_logger

# Delegation anti-patterns with capture groups for action extraction
# Each pattern is (regex_pattern, todo_template)
# {match} in template will be replaced with captured text
USER_DELEGATION_PATTERNS: List[Tuple[str, str]] = [
    # "Make sure (to) X" → "Verify: X"
    (r"(?i)make sure (?:to |that |you )?(.+)", "Verify: {match}"),
    # "You'll/will need to X" → "Task: X"
    (r"(?i)you(?:'ll| will)? need to (.+)", "Task: {match}"),
    # "Please run/execute/do X" → "Execute: X"
    (r"(?i)please (?:run|execute|do) (.+)", "Execute: {match}"),
    # "Remember to X" → "Task: X"
    (r"(?i)remember to (.+)", "Task: {match}"),
    # "Don't forget to X" → "Task: X"
    (r"(?i)don'?t forget to (.+)", "Task: {match}"),
    # "You should/can/could X" → "Suggested: X"
    (r"(?i)you (?:should|can|could) (.+)", "Suggested: {match}"),
    # "Be sure to X" → "Task: X"
    (r"(?i)be sure to (.+)", "Task: {match}"),
    # "Don't forget X" (without 'to') → "Task: X"
    (r"(?i)don'?t forget (.+)", "Task: {match}"),
    # "You may want to X" → "Suggested: X"
    (r"(?i)you may want to (.+)", "Suggested: {match}"),
    # "It's important to X" → "Task: X"
    (r"(?i)it'?s important to (.+)", "Task: {match}"),
]


class DelegationDetector:
    """Detects delegation anti-patterns in PM outputs.

    WHY this design:
    - Pattern-based detection for common manual instruction phrases
    - Extract actionable tasks from PM's text
    - Format as autotodos for PM visibility
    - Simple and extensible (add new patterns easily)
    """

    def __init__(self):
        self.logger = get_logger("delegation_detector")

    def detect_user_delegation(self, text: str) -> List[Dict[str, Any]]:
        """Detect delegation anti-patterns in text.

        Scans text for patterns where PM is asking user to do something
        manually instead of delegating to an agent.

        Args:
            text: PM output text to scan

        Returns:
            List of detected patterns with:
                - pattern_type: Type of pattern matched
                - original_text: Original sentence matched
                - suggested_todo: Formatted todo text
                - action: Extracted action text
        """
        detections = []

        # Split into sentences for better pattern matching
        # Split on period followed by space/newline, or just newline
        # This avoids splitting on periods in filenames like .env.local
        sentences = re.split(r"(?:\.\s+|\n+)", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Try each pattern
            for pattern, todo_template in USER_DELEGATION_PATTERNS:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    # Extract the captured action
                    action = match.group(1).strip()

                    # Skip if action is too short (likely false positive)
                    if len(action) < 5:
                        continue

                    # Format todo using template
                    suggested_todo = todo_template.format(match=action)

                    # Determine pattern type from template prefix
                    pattern_type = todo_template.split(":")[0]

                    detection = {
                        "pattern_type": pattern_type,
                        "original_text": sentence.strip(),
                        "suggested_todo": suggested_todo,
                        "action": action,
                    }

                    detections.append(detection)
                    self.logger.debug(
                        f"Detected delegation pattern: {pattern_type} - {action}"
                    )

                    # Only match first pattern per sentence
                    break

        return detections

    def format_as_autotodo(self, detection: Dict[str, Any]) -> Dict[str, str]:
        """Format a detection as an autotodo.

        Args:
            detection: Detection dict from detect_user_delegation

        Returns:
            Dictionary with todo fields (content, activeForm, status)
        """
        pattern_type = detection["pattern_type"]
        suggested_todo = detection["suggested_todo"]
        action = detection["action"]

        # Create todo content
        content = f"[Delegation] {suggested_todo}"

        # Active form for in-progress display
        active_form = f"Delegating: {action[:30]}..."

        return {
            "content": content,
            "activeForm": active_form,
            "status": "pending",
            "metadata": {
                "pattern_type": pattern_type,
                "original_text": detection["original_text"],
                "action": action,
                "source": "delegation_detector",
            },
        }


# Global instance
_delegation_detector: DelegationDetector | None = None


def get_delegation_detector() -> DelegationDetector:
    """Get the global delegation detector instance.

    Returns:
        DelegationDetector instance
    """
    global _delegation_detector
    if _delegation_detector is None:
        _delegation_detector = DelegationDetector()
    return _delegation_detector
