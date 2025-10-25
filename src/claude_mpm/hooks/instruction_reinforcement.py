"""
Instruction Reinforcement Hook for PM Delegation Compliance

This hook monitors PM behavior for delegation violations and provides
escalating warnings when the PM attempts to implement instead of delegate.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from claude_mpm.core.enums import OperationResult
from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class ViolationType(Enum):
    """Types of PM delegation violations"""

    EDIT_ATTEMPT = "Edit/Write/MultiEdit"
    BASH_IMPLEMENTATION = "Bash for implementation"
    FILE_CREATION = "Direct file creation"
    TEST_EXECUTION = "Test execution"
    DEPLOYMENT = "Deployment operation"
    CODE_WRITING = "Code writing"


@dataclass
class Violation:
    """Record of a delegation violation"""

    violation_type: ViolationType
    context: str
    timestamp: float
    severity_level: int


class InstructionReinforcementHook:
    """
    Monitors PM messages for delegation violations and provides corrective feedback.

    Circuit breaker pattern implementation to prevent PM from implementing
    instead of delegating work to appropriate agents.
    """

    def __init__(self):
        self.violation_count = 0
        self.violations: List[Violation] = []

        # Patterns that indicate PM is attempting forbidden actions
        self.forbidden_patterns = [
            # Direct implementation language - EXPANDED
            (
                r"I'll\s+(fix|create|write|implement|code|build|update|generate|modify|set\s+up|configure|optimize|rewrite|run|test|deploy|push|analyze|review|setup)",
                ViolationType.CODE_WRITING,
            ),
            (
                r"I'm\s+(fix|create|write|implement|code|build|update|generate|modify)",
                ViolationType.CODE_WRITING,
            ),
            (
                r"Let\s+me\s+(edit|write|modify|create|update|fix|run|execute|commit|refactor|configure|set\s+up|review)",
                ViolationType.EDIT_ATTEMPT,
            ),
            (
                r"I\s+will\s+(implement|code|build|create|write|update|fix)",
                ViolationType.CODE_WRITING,
            ),
            (
                r"I'm\s+(going\s+to|about\s+to)\s+(fix|create|write|implement|update|modify)",
                ViolationType.CODE_WRITING,
            ),
            # Common honeypot phrases
            (
                r"Here's\s+(the|my|an?)\s+(implementation|code|SQL|query|solution|analysis|fix)",
                ViolationType.CODE_WRITING,
            ),
            (
                r"The\s+(query|code|implementation|solution)\s+(would\s+be|is)",
                ViolationType.CODE_WRITING,
            ),
            (r"I\s+(found|identified)\s+(these\s+)?issues", ViolationType.CODE_WRITING),
            # Deployment and setup patterns
            (
                r"Setting\s+up\s+(the\s+)?(authentication|containers|environment|docker)",
                ViolationType.DEPLOYMENT,
            ),
            (r"Deploying\s+(to|the)", ViolationType.DEPLOYMENT),
            (r"I'll\s+(deploy|push|host|launch)", ViolationType.DEPLOYMENT),
            # Tool usage patterns - EXPANDED
            (r"Using\s+(Edit|Write|MultiEdit)\s+tool", ViolationType.EDIT_ATTEMPT),
            (r"<invoke\s+name=\"(Edit|Write|MultiEdit)\"", ViolationType.EDIT_ATTEMPT),
            (
                r"Running\s+(bash\s+command|git\s+commit|npm|yarn|python|node|go|tests|pytest)",
                ViolationType.BASH_IMPLEMENTATION,
            ),
            (r"Executing\s+(tests|test\s+suite|pytest)", ViolationType.TEST_EXECUTION),
            # Testing patterns - EXPANDED
            (
                r"(Testing|I'll\s+test|Let\s+me\s+test)\s+(the\s+)?(payment|API|endpoint)",
                ViolationType.TEST_EXECUTION,
            ),
            (
                r"I'll\s+(run|execute|verify)\s+(the\s+)?(tests|test\s+suite|endpoint)",
                ViolationType.TEST_EXECUTION,
            ),
            (r"pytest|npm\s+test|yarn\s+test|go\s+test", ViolationType.TEST_EXECUTION),
            # File operation patterns - EXPANDED
            (
                r"Creating\s+(new\s+|a\s+|the\s+)?(file|YAML|README|workflow)",
                ViolationType.FILE_CREATION,
            ),
            (r"Writing\s+to\s+file", ViolationType.FILE_CREATION),
            (
                r"Updating\s+(the\s+)?(code|component|queries)",
                ViolationType.CODE_WRITING,
            ),
            (
                r"I'll\s+(update|modify)\s+(the\s+)?(component|code|React)",
                ViolationType.CODE_WRITING,
            ),
        ]

        # Patterns for correct delegation behavior - EXPANDED
        self.delegation_patterns = [
            r"delegat(e|ing)\s+(to|this)",
            r"Task\s+tool",
            r"(asking|request|have|use)\s+\w+\s+agent",
            r"requesting\s+\w+\s+to",
            r"will\s+(have|ask|request)\s+\w+\s+agent",
            r"I'll\s+(have|ask|request|delegate)",
            r"the\s+\w+\s+agent\s+(will|can|should)",
        ]

    def detect_violation_intent(
        self, message: str
    ) -> Optional[Tuple[ViolationType, str]]:
        """
        Check message for patterns indicating PM violation intent.

        Args:
            message: The PM's message to analyze

        Returns:
            Tuple of (ViolationType, matched_text) if violation detected, None otherwise
        """
        message_lower = message.lower()

        # Check for forbidden patterns
        for pattern, violation_type in self.forbidden_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                # Check if this is actually a delegation (false positive check)
                is_delegation = any(
                    re.search(
                        del_pattern,
                        message_lower[max(0, match.start() - 50) : match.end() + 50],
                    )
                    for del_pattern in self.delegation_patterns
                )

                if not is_delegation:
                    return (violation_type, match.group(0))

        return None

    def escalate_warning(self) -> str:
        """
        Generate escalating warning message based on violation count.

        Returns:
            Warning message with appropriate severity
        """
        if self.violation_count == 1:
            return (
                "⚠️ DELEGATION REMINDER: PM must delegate ALL implementation work.\n"
                "Use the Task tool to delegate to the appropriate agent."
            )
        if self.violation_count == 2:
            return (
                "🚨 DELEGATION WARNING: Critical PM violation detected!\n"
                "You MUST delegate implementation work. Do NOT use Edit/Write/Bash for implementation.\n"
                "Next violation will result in session failure."
            )
        if self.violation_count == 3:
            return (
                "❌ CRITICAL DELEGATION FAILURE: Multiple PM violations detected.\n"
                "PM has repeatedly attempted to implement instead of delegate.\n"
                "Session integrity compromised. All work must be delegated to agents."
            )
        return (
            f"❌❌❌ SEVERE VIOLATION (Count: {self.violation_count}): PM continues to violate delegation rules.\n"
            "MANDATORY: Use Task tool to delegate ALL implementation to appropriate agents.\n"
            "Current session may need to be terminated and restarted."
        )

    def check_message(self, message: str) -> Optional[Dict[str, any]]:
        """
        Check a PM message for violations and return feedback if needed.

        Args:
            message: The PM's message to check

        Returns:
            Dictionary with violation details and correction, or None if compliant
        """
        violation_result = self.detect_violation_intent(message)

        if violation_result:
            violation_type, context = violation_result
            self.violation_count += 1

            # Record the violation
            import time

            violation = Violation(
                violation_type=violation_type,
                context=context,
                timestamp=time.time(),
                severity_level=min(self.violation_count, 4),
            )
            self.violations.append(violation)

            # Generate corrective feedback
            warning = self.escalate_warning()

            # Determine which agent should handle this
            agent_mapping = {
                ViolationType.EDIT_ATTEMPT: "Engineer",
                ViolationType.CODE_WRITING: "Engineer",
                ViolationType.BASH_IMPLEMENTATION: "Engineer or Ops",
                ViolationType.FILE_CREATION: "Engineer or Documentation",
                ViolationType.TEST_EXECUTION: "QA",
                ViolationType.DEPLOYMENT: "Ops",
            }

            suggested_agent = agent_mapping.get(violation_type, "appropriate agent")

            # Clean up context for task suggestion
            clean_context = (
                context.replace("I will ", "")
                .replace("I'll ", "")
                .replace("Let me ", "")
            )

            return {
                "violation_detected": True,
                "violation_count": self.violation_count,
                "violation_type": violation_type.value,
                "context": context,
                "warning": warning,
                "correction": f"MUST delegate to {suggested_agent} using Task tool",
                "suggested_task": f"Task: Please {clean_context}",
                "severity": min(self.violation_count, 4),
            }

        return None

    def get_violation_summary(self) -> Dict[str, any]:
        """
        Get a summary of all violations in the session.

        Returns:
            Dictionary with violation statistics and details
        """
        if not self.violations:
            return {
                "total_violations": 0,
                "status": OperationResult.SUCCESS,
                "message": "No PM delegation violations detected",
            }

        violation_types = {}
        for v in self.violations:
            vtype = v.violation_type.value
            violation_types[vtype] = violation_types.get(vtype, 0) + 1

        status = (
            OperationResult.ERROR
            if self.violation_count < 3
            else OperationResult.FAILED
        )

        return {
            "total_violations": self.violation_count,
            "status": status,
            "violation_types": violation_types,
            "most_recent": self.violations[-1].context if self.violations else None,
            "recommendation": (
                "Review PM delegation training"
                if self.violation_count > 2
                else "Continue monitoring"
            ),
        }

    def reset(self):
        """Reset violation tracking for a new session"""
        self.violation_count = 0
        self.violations = []
