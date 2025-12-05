"""
Instruction Faithfulness Metric for PM Agent Evaluation.

This metric evaluates how faithfully the PM agent follows the instructions
defined in PM_INSTRUCTIONS.md, specifically:
- Delegation discipline (no direct implementation)
- Evidence-based assertions (no unverified claims)
- File tracking requirements
- Circuit breaker compliance
"""

from typing import Any, Dict, List

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from ..utils.pm_response_parser import PMResponseParser


class InstructionFaithfulnessMetric(BaseMetric):
    """
    Custom DeepEval metric for PM instruction compliance.

    Evaluates:
    1. Tool usage violations (Edit/Write/Bash for implementation)
    2. Investigation violations (multiple Read, Grep/Glob usage)
    3. Assertion quality (evidence-based vs unverified)
    4. Delegation correctness (Task tool usage)

    Scoring:
    - 1.0: Perfect compliance, no violations
    - 0.8-0.99: Minor violations (1-2 unverified assertions)
    - 0.6-0.79: Moderate violations (delegation lapses)
    - 0.0-0.59: Major violations (implementation, forbidden tools)
    """

    def __init__(
        self,
        threshold: float = 0.85,
        strict_mode: bool = False,
        include_async: bool = True
    ):
        """
        Initialize InstructionFaithfulnessMetric.

        Args:
            threshold: Minimum score to pass (default: 0.85)
            strict_mode: If True, any violation fails the test
            include_async: Support async evaluation
        """
        self.threshold = threshold
        self.strict_mode = strict_mode
        self.include_async = include_async
        self.parser = PMResponseParser()

    @property
    def __name__(self) -> str:
        return "Instruction Faithfulness"

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure instruction faithfulness score.

        Args:
            test_case: DeepEval test case with actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        # Parse PM response
        analysis = self.parser.parse(test_case.actual_output)

        # Calculate individual scores
        tool_usage_score = self._score_tool_usage(analysis.tools_used)
        evidence_score = analysis.evidence_quality_score
        delegation_score = analysis.delegation_correctness_score
        violation_penalty = self._calculate_violation_penalty(analysis.violations)

        # Weighted average
        base_score = (
            tool_usage_score * 0.3 +
            evidence_score * 0.3 +
            delegation_score * 0.4
        )

        # Apply violation penalty
        final_score = max(0.0, base_score - violation_penalty)

        # Store for reporting
        self.score = final_score
        self.reason = self._generate_reason(analysis, final_score)
        self.success = final_score >= self.threshold

        return final_score

    def _score_tool_usage(self, tools_used: List) -> float:
        """
        Score tool usage compliance.

        Penalties for:
        - Edit/Write tools (implementation)
        - Multiple Read calls (investigation)
        - Grep/Glob tools (investigation)
        - mcp-ticketer tools (should delegate to ticketing)
        """
        score = 1.0

        for tool in tools_used:
            if tool.tool_name in ["Edit", "Write"]:
                score -= 0.3  # Major penalty for implementation

            if tool.tool_name in ["Grep", "Glob"]:
                score -= 0.2  # Penalty for investigation

            if tool.tool_name == "mcp_ticketer":
                score -= 0.3  # Major penalty for direct ticketing tool usage

        # Count Read tools (one is allowed for context)
        read_count = sum(1 for t in tools_used if t.tool_name == "Read")
        if read_count > 1:
            score -= 0.1 * (read_count - 1)  # Penalty for multiple reads

        return max(0.0, score)

    def _calculate_violation_penalty(self, violations: List[str]) -> float:
        """
        Calculate penalty based on circuit breaker violations.

        Each violation type has a specific penalty weight.
        """
        penalty = 0.0

        for violation in violations:
            if "Circuit Breaker #1" in violation:
                penalty += 0.3  # Implementation violation
            elif "Circuit Breaker #2" in violation:
                penalty += 0.2  # Investigation violation
            elif "Circuit Breaker #3" in violation:
                penalty += 0.15  # Unverified assertion
            elif "Circuit Breaker #6" in violation:
                penalty += 0.3  # Ticketing tool misuse
            else:
                penalty += 0.1  # Generic violation

        return penalty

    def _generate_reason(self, analysis, score: float) -> str:
        """Generate human-readable reason for the score."""
        reasons = []

        if analysis.violations:
            reasons.append(
                f"Found {len(analysis.violations)} circuit breaker violations"
            )

        if analysis.evidence_quality_score < 1.0:
            unverified = sum(1 for a in analysis.assertions if not a.has_evidence)
            reasons.append(
                f"{unverified} unverified assertions found"
            )

        if analysis.delegation_correctness_score < 1.0:
            reasons.append("Delegation issues detected")

        tool_violations = [
            t for t in analysis.tools_used
            if t.tool_name in ["Edit", "Write", "mcp_ticketer"]
        ]
        if tool_violations:
            tool_names = [t.tool_name for t in tool_violations]
            reasons.append(
                f"Forbidden tools used: {', '.join(set(tool_names))}"
            )

        if not reasons:
            return "Perfect instruction compliance - no violations found"

        return "; ".join(reasons)

    def is_successful(self) -> bool:
        """Check if metric passes threshold."""
        return self.success

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure (delegates to sync version)."""
        return self.measure(test_case)


class StrictInstructionFaithfulnessMetric(InstructionFaithfulnessMetric):
    """
    Strict variant that fails on ANY violation.

    Use for critical compliance checks where zero tolerance is required.
    """

    def __init__(self, threshold: float = 1.0):
        super().__init__(threshold=threshold, strict_mode=True)

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure with strict mode - any violation returns 0.0.
        """
        analysis = self.parser.parse(test_case.actual_output)

        # In strict mode, any violation = failure
        if analysis.violations:
            self.score = 0.0
            self.reason = (
                f"STRICT MODE FAILURE: {len(analysis.violations)} violations found. "
                f"First violation: {analysis.violations[0]}"
            )
            self.success = False
            return 0.0

        # No violations - use normal scoring
        return super().measure(test_case)


def create_instruction_faithfulness_metric(
    threshold: float = 0.85,
    strict: bool = False
) -> InstructionFaithfulnessMetric:
    """
    Factory function to create instruction faithfulness metric.

    Args:
        threshold: Minimum passing score
        strict: Use strict mode (fail on any violation)

    Returns:
        Configured metric instance
    """
    if strict:
        return StrictInstructionFaithfulnessMetric(threshold=threshold)
    return InstructionFaithfulnessMetric(threshold=threshold)
