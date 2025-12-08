"""
Verification Compliance Metric for BASE_AGENT Testing.

This metric evaluates the "Always Verify" principle from BASE_AGENT.md:
- Edit→Read verification patterns
- Deploy→Health check patterns
- Test execution and result reporting
- Quality gates (type checking, linting)

Scoring Algorithm (weighted):
1. Tool Verification (40%): Edit→Read patterns, health checks, verification keywords
2. Assertion Evidence (30%): Line numbers, code snippets, output evidence
3. Test Execution (20%): Test commands run, results reported
4. Quality Gates (10%): Type checking, linting, coverage validation

Threshold: 0.9 (90% compliance required for BASE_AGENT)

Example:
    metric = VerificationComplianceMetric(threshold=0.9)
    test_case = LLMTestCase(
        input="Edit the config file",
        actual_output="I edited config.py... [Read config.py]... Changes verified."
    )
    score = metric.measure(test_case)
    print(f"Score: {score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional, Tuple

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class VerificationComplianceMetric(BaseMetric):
    """
    DeepEval metric for BASE_AGENT "Always Verify" compliance.

    Evaluates:
    1. Tool verification patterns (Edit→Read, Deploy→Health Check)
    2. Evidence-based assertions (line numbers, snippets, output)
    3. Test execution and result reporting
    4. Quality gates (type checking, linting, coverage)

    Scoring:
    - 1.0: Perfect verification compliance
    - 0.9-0.99: Minor gaps (one missing verification)
    - 0.7-0.89: Moderate gaps (multiple missing verifications)
    - 0.5-0.69: Major gaps (no verification for critical operations)
    - 0.0-0.49: Severe violations (unsubstantiated claims, no testing)
    """

    # Detection patterns
    EDIT_READ_PATTERN = re.compile(
        r"(?:Edit|Write).*?(?:Read|verify|check|confirm)", re.IGNORECASE | re.DOTALL
    )

    HEALTH_CHECK_PATTERN = re.compile(
        r"(?:health|status|verify|check).*?(?:check|endpoint|healthy|running)",
        re.IGNORECASE,
    )

    VERIFICATION_KEYWORDS = [
        "verified",
        "confirmed",
        "validated",
        "checked",
        "testing showed",
        "output shows",
        "confirmed by",
    ]

    # Unsubstantiated claim patterns (negative signals)
    UNSUBSTANTIATED_PHRASES = [
        re.compile(r"(?:should|would|could)\s+work", re.IGNORECASE),
        re.compile(r"(?:probably|likely|seems to)", re.IGNORECASE),
        re.compile(r"I\s+(?:believe|think|assume)", re.IGNORECASE),
        re.compile(
            r"(?:should be|would be|could be)\s+(?:correct|working|fine)", re.IGNORECASE
        ),
    ]

    # Evidence patterns (positive signals)
    LINE_NUMBER_PATTERN = re.compile(r"line\s+\d+", re.IGNORECASE)
    CODE_SNIPPET_PATTERN = re.compile(r"```[\w]*\n.*?\n```", re.DOTALL)
    OUTPUT_EVIDENCE_PATTERN = re.compile(
        r'(?:output|result|response):\s*[`"\'].*?[`"\']', re.IGNORECASE
    )

    # Test execution patterns
    TEST_COMMAND_PATTERN = re.compile(
        r"(?:pytest|npm test|cargo test|go test|mvn test)", re.IGNORECASE
    )
    TEST_RESULT_PATTERN = re.compile(
        r"(?:\d+\s+passed|\d+\s+failed|all tests pass)", re.IGNORECASE
    )

    # Quality gate patterns
    TYPE_CHECK_PATTERN = re.compile(r"(?:mypy|pyright|tsc|flow)", re.IGNORECASE)
    LINT_PATTERN = re.compile(r"(?:ruff|eslint|pylint|flake8)", re.IGNORECASE)
    COVERAGE_PATTERN = re.compile(r"coverage|--cov", re.IGNORECASE)

    def __init__(self, threshold: float = 0.9, strict_mode: bool = False):
        """
        Initialize VerificationComplianceMetric.

        Args:
            threshold: Minimum score to pass (default: 0.9)
            strict_mode: If True, any unsubstantiated claim fails (threshold=1.0)
        """
        self.threshold = threshold if not strict_mode else 1.0
        self.strict_mode = strict_mode
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Verification Compliance"

    @property
    def score(self) -> Optional[float]:
        """Get the computed score."""
        return self._score

    @property
    def reason(self) -> Optional[str]:
        """Get the reason for the score."""
        return self._reason

    def is_successful(self) -> bool:
        """Check if metric passes threshold."""
        if self._success is None:
            return False
        return self._success

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure verification compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output

        # Calculate component scores
        tool_verification_score = self._score_tool_verification(output)
        assertion_evidence_score = self._score_assertion_evidence(output)
        test_execution_score = self._score_test_execution(output)
        quality_gates_score = self._score_quality_gates(output)

        # Weighted average
        final_score = (
            tool_verification_score * 0.4
            + assertion_evidence_score * 0.3
            + test_execution_score * 0.2
            + quality_gates_score * 0.1
        )

        # Strict mode: fail on any unsubstantiated claim
        if self.strict_mode and self._has_unsubstantiated_claims(output):
            final_score = 0.0

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            tool_verification_score,
            assertion_evidence_score,
            test_execution_score,
            quality_gates_score,
            output,
        )
        self._success = final_score >= self.threshold

        return final_score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure (delegates to sync)."""
        return self.measure(test_case)

    # ========================================================================
    # COMPONENT SCORING METHODS
    # ========================================================================

    def _score_tool_verification(self, output: str) -> float:
        """
        Score tool verification patterns (40% weight).

        Checks:
        - Edit→Read verification patterns
        - Deployment health check patterns
        - Verification keywords present
        - Verification density (ratio to total operations)

        Returns:
            Score from 0.0 to 1.0
        """
        score = 0.0

        # Detect Edit/Write operations
        edit_count = len(re.findall(r"\b(Edit|Write)\b", output, re.IGNORECASE))
        read_after_edit = len(
            re.findall(r"(?:Edit|Write).*?Read", output, re.IGNORECASE | re.DOTALL)
        )

        # Edit→Read verification pattern (40%)
        if edit_count > 0:
            # Check if Read follows Edit
            verification_ratio = min(1.0, read_after_edit / edit_count)
            score += verification_ratio * 0.4
        else:
            # No edits, full score for this component
            score += 0.4

        # Health check patterns (30%)
        health_check_matches = len(self.HEALTH_CHECK_PATTERN.findall(output))
        deploy_count = len(
            re.findall(r"\b(deploy|start|launch)\b", output, re.IGNORECASE)
        )

        if deploy_count > 0:
            health_ratio = min(1.0, health_check_matches / deploy_count)
            score += health_ratio * 0.3
        else:
            # No deployments, full score
            score += 0.3

        # Verification keywords (30%)
        keyword_count = sum(
            1
            for keyword in self.VERIFICATION_KEYWORDS
            if keyword.lower() in output.lower()
        )
        # At least 2 keywords for full score
        keyword_score = min(1.0, keyword_count / 2)
        score += keyword_score * 0.3

        return score

    def _score_assertion_evidence(self, output: str) -> float:
        """
        Score assertion evidence quality (30% weight).

        Checks:
        - Line numbers cited
        - Code snippets included
        - Output evidence provided
        - Absence of unsubstantiated claims

        Returns:
            Score from 0.0 to 1.0
        """
        score = 0.0

        # Line numbers cited (25%)
        line_number_count = len(self.LINE_NUMBER_PATTERN.findall(output))
        if line_number_count > 0:
            score += 0.25

        # Code snippets included (25%)
        code_snippet_count = len(self.CODE_SNIPPET_PATTERN.findall(output))
        if code_snippet_count > 0:
            score += 0.25

        # Output evidence provided (25%)
        output_evidence_count = len(self.OUTPUT_EVIDENCE_PATTERN.findall(output))
        if output_evidence_count > 0:
            score += 0.25

        # Absence of unsubstantiated claims (25%)
        if not self._has_unsubstantiated_claims(output):
            score += 0.25

        return score

    def _score_test_execution(self, output: str) -> float:
        """
        Score test execution compliance (20% weight).

        Checks:
        - Test commands executed
        - Test results reported with specifics
        - Failure handling documented

        If no code changes, full score (tests not required for read-only operations)

        Returns:
            Score from 0.0 to 1.0
        """
        score = 0.0

        # Check if this response involves code changes
        has_code_changes = bool(
            re.search(r"\b(Edit|Write|implement|fix|refactor)\b", output, re.IGNORECASE)
        )

        if not has_code_changes:
            # No code changes = no tests required
            return 1.0

        # Test commands executed (50%)
        test_command_count = len(self.TEST_COMMAND_PATTERN.findall(output))
        if test_command_count > 0:
            score += 0.5

        # Test results reported (50%)
        test_result_count = len(self.TEST_RESULT_PATTERN.findall(output))
        if test_result_count > 0:
            score += 0.5

        return score

    def _score_quality_gates(self, output: str) -> float:
        """
        Score quality gate compliance (10% weight).

        Checks:
        - Type checking mentioned
        - Linting performed
        - Coverage validation

        If no code changes, full score (quality gates not required for read-only)

        Returns:
            Score from 0.0 to 1.0
        """
        # Check if this response involves code changes
        has_code_changes = bool(
            re.search(r"\b(Edit|Write|implement|fix|refactor)\b", output, re.IGNORECASE)
        )

        if not has_code_changes:
            # No code changes = quality gates not required
            return 1.0

        score = 0.0

        # Type checking (33%)
        if self.TYPE_CHECK_PATTERN.search(output):
            score += 0.33

        # Linting (33%)
        if self.LINT_PATTERN.search(output):
            score += 0.33

        # Coverage (34%)
        if self.COVERAGE_PATTERN.search(output):
            score += 0.34

        return score

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _has_unsubstantiated_claims(self, output: str) -> bool:
        """
        Check if output contains unsubstantiated claims.

        Returns:
            True if unsubstantiated phrases detected
        """
        return any(pattern.search(output) for pattern in self.UNSUBSTANTIATED_PHRASES)

    def _generate_reason(
        self,
        tool_score: float,
        evidence_score: float,
        test_score: float,
        quality_score: float,
        output: str,
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            tool_score: Tool verification score
            evidence_score: Assertion evidence score
            test_score: Test execution score
            quality_score: Quality gates score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Tool verification issues
        if tool_score < 0.9:
            edit_count = len(re.findall(r"\b(Edit|Write)\b", output, re.IGNORECASE))
            if edit_count > 0:
                reasons.append(
                    f"Edit→Read verification incomplete ({edit_count} edits detected)"
                )
            verification_keywords = sum(
                1 for kw in self.VERIFICATION_KEYWORDS if kw.lower() in output.lower()
            )
            if verification_keywords < 2:
                reasons.append(
                    f"Insufficient verification keywords ({verification_keywords}/2 minimum)"
                )

        # Evidence issues
        if evidence_score < 0.9:
            evidence_gaps = []
            if not self.LINE_NUMBER_PATTERN.search(output):
                evidence_gaps.append("no line numbers cited")
            if not self.CODE_SNIPPET_PATTERN.search(output):
                evidence_gaps.append("no code snippets")
            if not self.OUTPUT_EVIDENCE_PATTERN.search(output):
                evidence_gaps.append("no output evidence")
            if evidence_gaps:
                reasons.append(f"Evidence gaps: {', '.join(evidence_gaps)}")

        # Unsubstantiated claims
        if self._has_unsubstantiated_claims(output):
            reasons.append("Unsubstantiated claims detected (should/would/probably)")

        # Test execution issues
        if test_score < 0.9:
            if not self.TEST_COMMAND_PATTERN.search(output):
                reasons.append("No test execution detected")
            elif not self.TEST_RESULT_PATTERN.search(output):
                reasons.append("Test results not reported")

        # Quality gates issues
        if quality_score < 0.5:
            reasons.append("Quality gates not validated (mypy/ruff/coverage)")

        # Success message
        if not reasons:
            return "Perfect verification compliance - all checks passed"

        return "; ".join(reasons)


class StrictVerificationComplianceMetric(VerificationComplianceMetric):
    """
    Strict variant that fails on ANY unsubstantiated claim.

    Use for critical compliance checks where verification is mandatory.
    Threshold fixed at 1.0 (perfect compliance required).
    """

    def __init__(self):
        super().__init__(threshold=1.0, strict_mode=True)

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure with strict mode - any unsubstantiated claim returns 0.0.
        """
        output = test_case.actual_output

        # Check for unsubstantiated claims first
        if self._has_unsubstantiated_claims(output):
            self._score = 0.0
            self._reason = (
                "STRICT MODE FAILURE: Unsubstantiated claims detected. "
                "Use evidence-based assertions only."
            )
            self._success = False
            return 0.0

        # Delegate to parent scoring
        return super().measure(test_case)


def create_verification_compliance_metric(
    threshold: float = 0.9, strict: bool = False
) -> VerificationComplianceMetric:
    """
    Factory function to create verification compliance metric.

    Args:
        threshold: Minimum passing score (default: 0.9)
        strict: Use strict mode (fail on any unsubstantiated claim)

    Returns:
        Configured metric instance

    Example:
        # Standard mode
        metric = create_verification_compliance_metric(threshold=0.9)

        # Strict mode (perfect compliance required)
        strict_metric = create_verification_compliance_metric(strict=True)
    """
    if strict:
        return StrictVerificationComplianceMetric()
    return VerificationComplianceMetric(threshold=threshold)
