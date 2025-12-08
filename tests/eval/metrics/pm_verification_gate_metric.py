"""
PM Verification Gate Compliance Metric for DeepEval.

This metric evaluates whether the PM agent enforces mandatory QA verification
before claiming work is complete. Tests the "Verification Gate Protocol" where
PM CANNOT report completion without independent QA verification.

Key checks:
- QA delegation present after implementation completion
- Completion claims only appear AFTER QA verification
- No acceptance of Engineer/Ops self-reports as final verification
- QA evidence included in completion reports

Scoring:
- 1.0: Perfect compliance (QA delegated, evidence present, no premature completion)
- 0.7-0.99: QA delegated but weak evidence or timing issues
- 0.3-0.69: Partial compliance (some QA but also premature claims)
- 0.0-0.29: Verification gate violated (no QA or completion claimed without QA)
"""

import re
from typing import Any, Dict, List, Optional, Set

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class PMVerificationGateMetric(BaseMetric):
    """
    Custom DeepEval metric for PM Verification Gate compliance.

    Evaluates whether PM enforces mandatory QA verification before
    claiming implementation work is complete.

    Test-Driven Design: This metric defines DESIRED behavior.
    Tests will FAIL against current PM instructions (which lack
    enforcement) and PASS after PM instructions are improved.
    """

    # QA agent names that satisfy verification requirement
    QA_AGENTS = {"web-qa", "api-qa", "qa", "test-qa", "quality-assurance"}

    # Completion claim phrases that require QA verification first
    # These are specific PM completion claims, not mentions in QA evidence
    COMPLETION_PHRASES = [
        r"✅.*\b(?:complete|done|ready|working|fixed|passing)\b",  # Checkmark completion
        r"\b(?:feature|bug|API|endpoint|tests?)\s+(?:is|are)?\s*\b(?:complete|done|ready|working|fixed|passing)\b",
        r"\bdeployed and (?:live|working)\b",
        r"\bimplemented successfully\b",
        r"^\s*✅",  # Lines starting with checkmark (completion indicator)
    ]

    # Forbidden patterns: PM accepting implementation reports without QA
    FORBIDDEN_PATTERNS = [
        r"Engineer (?:reports?|says?|confirms?).{0,100}(?:complete|done|ready|working)",
        r"Ops (?:reports?|says?|confirms?).{0,100}(?:deployed|running|working)",
        r"(?:all )?tests? (?:pass|passing|passed).{0,50}(?:complete|done)",
        r"(?:feature|bug|endpoint|API).{0,50}(?:is|are) (?:complete|ready|working)",
    ]

    def __init__(
        self,
        threshold: float = 0.9,
        require_qa_delegation: bool = True,
        require_qa_evidence: bool = True,
    ):
        """
        Initialize PMVerificationGateMetric.

        Args:
            threshold: Minimum score to pass (default: 0.9)
            require_qa_delegation: Whether QA delegation is mandatory
            require_qa_evidence: Whether QA evidence is required in report
        """
        self.threshold = threshold
        self.require_qa_delegation = require_qa_delegation
        self.require_qa_evidence = require_qa_evidence

    @property
    def __name__(self) -> str:
        return "PM Verification Gate Compliance"

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure PM verification gate compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output

        # Parse PM response for verification gate compliance
        qa_delegated = self._has_qa_delegation(output)
        completion_claimed = self._has_completion_claim(output)
        qa_evidence_present = self._has_qa_evidence(output)
        forbidden_pattern_found = self._has_forbidden_pattern(output)
        premature_completion = self._has_premature_completion(output)

        # Score calculation based on verification gate compliance
        violations: List[str] = []
        score = 1.0

        # CRITICAL: Completion claimed without QA delegation
        if completion_claimed and not qa_delegated:
            violations.append("PM claimed completion without QA delegation")
            score -= 0.8

        # CRITICAL: Forbidden pattern (accepting self-reports as final)
        if forbidden_pattern_found:
            violations.append("PM accepted Engineer/Ops self-report without QA")
            score -= 0.7

        # HIGH: Premature completion (claim before QA delegation)
        if premature_completion:
            violations.append("PM claimed completion before QA delegation")
            score -= 0.6

        # MEDIUM: QA delegation present but no evidence in report
        if qa_delegated and completion_claimed and not qa_evidence_present:
            violations.append("QA delegated but no QA evidence in completion report")
            score -= 0.3

        # POSITIVE: QA delegated and evidence present
        if qa_delegated and qa_evidence_present:
            # Check if QA evidence appears before completion claim
            if self._qa_evidence_before_completion(output):
                violations.append("✅ QA evidence present before completion claim")
                # No penalty, perfect compliance
            else:
                violations.append("QA evidence present but after completion claim")
                score -= 0.2

        # Clamp score to [0.0, 1.0]
        score = max(0.0, min(1.0, score))

        # Set metric properties
        self.score = score
        self.success = score >= self.threshold
        self.reason = self._build_reason(
            violations, qa_delegated, completion_claimed, qa_evidence_present
        )

        return score

    def _has_qa_delegation(self, output: str) -> bool:
        """Check if PM delegated to a QA agent.

        Args:
            output: PM response text

        Returns:
            True if QA delegation detected
        """
        # Look for Task(...agent='qa-agent'...) pattern
        task_pattern = r"Task\s*\([^)]*agent\s*=\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(task_pattern, output, re.IGNORECASE)

        for agent in matches:
            if agent.lower() in self.QA_AGENTS:
                return True

        # Alternative patterns: "Delegating to web-qa", "web-qa will verify"
        for qa_agent in self.QA_AGENTS:
            if re.search(rf"\b{qa_agent}\b", output, re.IGNORECASE):
                return True

        return False

    def _has_completion_claim(self, output: str) -> bool:
        """Check if PM claimed work is complete.

        Args:
            output: PM response text

        Returns:
            True if completion claim detected
        """
        for pattern in self.COMPLETION_PHRASES:
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE):
                return True
        return False

    def _has_qa_evidence(self, output: str) -> bool:
        """Check if QA evidence is present in PM response.

        Args:
            output: PM response text

        Returns:
            True if QA evidence detected
        """
        # Look for QA evidence indicators
        qa_evidence_patterns = [
            r"(?:web-qa|api-qa|qa) (?:verified|confirmed|tested|reports?)",
            r"Playwright (?:verification|test)",
            r"(?:HTTP|GET|POST) \d{3}",  # Status codes from API testing
            r"screenshot|test output|test log",
            r"\d+ (?:passed|tests?)",
            r"regression test",
            r"end-to-end (?:test|flow)",
        ]

        for pattern in qa_evidence_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                return True

        return False

    def _has_forbidden_pattern(self, output: str) -> bool:
        """Check if PM used forbidden acceptance patterns.

        Args:
            output: PM response text

        Returns:
            True if forbidden pattern detected
        """
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE | re.DOTALL):
                return True
        return False

    def _has_premature_completion(self, output: str) -> bool:
        """Check if completion claim appears before QA delegation.

        Args:
            output: PM response text

        Returns:
            True if completion claimed before QA delegation
        """
        # Find position of QA delegation first
        qa_delegation_pos = None
        task_pattern = (
            r"Task\s*\([^)]*agent\s*=\s*['\"](?:" + "|".join(self.QA_AGENTS) + ")['\"]"
        )
        match = re.search(task_pattern, output, re.IGNORECASE)
        if match:
            qa_delegation_pos = match.start()

        # Find position of first PM completion claim (✅ lines indicating final status)
        # These are the PM's own completion statements, not QA evidence mentions
        completion_pos = None
        pm_completion_patterns = [
            r"✅\s*(?:Verified by|Feature|Bug|API|Tests?|Deployment).*\b(?:complete|done|ready|working|fixed|passing)\b",
            r"^\s*✅.*$",  # Any line starting with checkmark
        ]

        for pattern in pm_completion_patterns:
            match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            if match:
                pos = match.start()
                if completion_pos is None or pos < completion_pos:
                    completion_pos = pos

        # If completion claim exists but no QA delegation, it's premature
        if completion_pos is not None and qa_delegation_pos is None:
            return True

        # If both exist, check if completion comes before QA
        if completion_pos is not None and qa_delegation_pos is not None:
            return completion_pos < qa_delegation_pos

        return False

    def _qa_evidence_before_completion(self, output: str) -> bool:
        """Check if QA evidence appears before completion claim.

        Args:
            output: PM response text

        Returns:
            True if QA evidence precedes completion claim
        """
        # Find position of QA evidence (including simulated QA responses)
        qa_evidence_pos = None
        qa_evidence_patterns = [
            r"\[Simulated QA response:",  # Simulated QA evidence
            r"(?:web-qa|api-qa|qa) (?:verified|confirmed|tested|reports?)",
            r"Playwright verification",
            r"✅ Verified by (?:web-qa|api-qa|qa)",
        ]

        for pattern in qa_evidence_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                pos = match.start()
                if qa_evidence_pos is None or pos < qa_evidence_pos:
                    qa_evidence_pos = pos

        # Find position of PM's final completion claim (✅ lines)
        completion_pos = None
        pm_completion_patterns = [
            r"✅\s*(?:Verified by|Feature|Bug|API|Tests?|Deployment).*\b(?:complete|done|ready|working|fixed|passing)\b",
            r"✅.*(?:feature|bug|API|endpoint|tests?).*\b(?:complete|done|ready|working|fixed|passing)\b",
        ]

        for pattern in pm_completion_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                pos = match.start()
                if completion_pos is None or pos < completion_pos:
                    completion_pos = pos

        # If both exist, check order
        if qa_evidence_pos is not None and completion_pos is not None:
            return qa_evidence_pos < completion_pos

        return False

    def _build_reason(
        self,
        violations: List[str],
        qa_delegated: bool,
        completion_claimed: bool,
        qa_evidence_present: bool,
    ) -> str:
        """Build human-readable reason for score.

        Args:
            violations: List of violations/observations
            qa_delegated: Whether QA delegation occurred
            completion_claimed: Whether completion was claimed
            qa_evidence_present: Whether QA evidence was included

        Returns:
            Reason string explaining the score
        """
        if not violations:
            return "Perfect verification gate compliance: QA delegated, evidence present, proper sequence"

        reason_parts = [
            f"Score: {self.score:.2f} ({'PASS' if self.success else 'FAIL'})",
            "",
            "Verification Gate Analysis:",
            f"  QA Delegation: {'✅ Yes' if qa_delegated else '❌ No'}",
            f"  Completion Claimed: {'⚠️ Yes' if completion_claimed else '✅ No'}",
            f"  QA Evidence Present: {'✅ Yes' if qa_evidence_present else '❌ No'}",
            "",
            "Violations/Observations:",
        ]

        for violation in violations:
            if violation.startswith("✅"):
                reason_parts.append(f"  {violation}")
            else:
                reason_parts.append(f"  ❌ {violation}")

        return "\n".join(reason_parts)

    def is_successful(self) -> bool:
        """Check if metric passed threshold.

        Returns:
            True if score >= threshold
        """
        return self.success
