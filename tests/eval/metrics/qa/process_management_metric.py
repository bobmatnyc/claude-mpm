"""
Process Management Metric for QA Agent Testing.

This metric evaluates QA Agent compliance with process lifecycle management:
- Pre-flight checks (inspects package.json, verifies test commands)
- Post-execution verification (verifies clean process state after tests)
- Hanging process detection (detects hanging/stuck test processes)
- Orphaned process cleanup (cleans up orphaned node/vitest processes)

Scoring Algorithm (weighted):
1. Pre-Flight Checks (40%): Inspects package.json, verifies test commands
2. Post-Execution Verification (35%): Verifies clean process state
3. Hanging Process Detection (15%): Detects hanging/stuck processes
4. Orphaned Process Cleanup (10%): Cleans up orphaned processes

Threshold: 0.9 (90% compliance required)

Example:
    metric = ProcessManagementMetric(threshold=0.9)
    test_case = LLMTestCase(
        input="Run tests and verify process cleanup",
        actual_output='''Before running tests, checking package.json test script...
        Test script: "vitest run" - safe, non-interactive mode.
        Running tests...
        Tests complete. Verifying process state with ps aux | grep vitest...
        No hanging vitest processes detected.
        Verified clean process state - no orphaned node processes.'''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class ProcessManagementMetric(BaseMetric):
    """
    DeepEval metric for QA Agent process management compliance.

    Evaluates:
    1. Pre-flight checks (inspects package.json, verifies test commands)
    2. Post-execution verification (verifies clean process state)
    3. Hanging process detection (detects stuck processes)
    4. Orphaned process cleanup (cleans up node/vitest processes)

    Scoring:
    - 1.0: Perfect compliance (pre-flight, post-execution verification, cleanup)
    - 0.9-0.99: Good compliance (pre-flight and verification done)
    - 0.7-0.89: Acceptable (basic process checks)
    - 0.0-0.69: Poor (no process management)
    """

    # Pre-flight check patterns
    PREFLIGHT_PATTERNS: List[str] = [
        r'package\.json',
        r'test\s+script',
        r'before\s+running',
        r'inspect(?:ed|ing)',
        r'check(?:ed|ing).*(?:package\.json|test\s+command)',
        r'verif(?:y|ied|ying).*(?:test\s+script|command)',
        r'review(?:ed|ing).*package\.json',
        r'safe.*mode',
        r'non-interactive'
    ]

    # Post-execution verification patterns
    POST_EXECUTION_PATTERNS: List[str] = [
        r'ps\s+aux',
        r'verif(?:y|ied|ying)',
        r'clean',
        r'no\s+hanging',
        r'after\s+tests?',
        r'process\s+state',
        r'check(?:ed|ing).*process',
        r'no\s+orphaned',
        r'tests?\s+complete.*verif(?:y|ied|ying)'
    ]

    # Hanging process detection patterns
    HANGING_DETECTION_PATTERNS: List[str] = [
        r'hanging',
        r'stuck',
        r'timeout',
        r'not\s+responding',
        r'detect(?:ed|ing).*hang',
        r'check(?:ed|ing).*hanging',
        r'no\s+hanging\s+process',
        r'still\s+running'
    ]

    # Cleanup patterns
    CLEANUP_PATTERNS: List[str] = [
        r'killed?',
        r'terminat(?:e|ed|ing)',
        r'clean(?:ed)?\s+up',
        r'orphaned',
        r'pkill',
        r'kill.*process',
        r'removed?\s+orphaned',
        r'cleanup'
    ]

    def __init__(self, threshold: float = 0.9):
        """
        Initialize ProcessManagementMetric.

        Args:
            threshold: Minimum score to pass (default: 0.9 for 90% compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Process Management"

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
        Measure process management compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output

        # Calculate component scores
        preflight_score = self._score_preflight_checks(output)
        post_execution_score = self._score_post_execution_verification(output)
        hanging_detection_score = self._score_hanging_detection(output)
        cleanup_score = self._score_cleanup(output)

        # Weighted average
        final_score = (
            preflight_score * 0.40 +
            post_execution_score * 0.35 +
            hanging_detection_score * 0.15 +
            cleanup_score * 0.10
        )

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            preflight_score,
            post_execution_score,
            hanging_detection_score,
            cleanup_score,
            output
        )
        epsilon = 1e-9
        self._success = final_score >= (self.threshold - epsilon)

        return final_score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure (delegates to sync)."""
        return self.measure(test_case)

    # ========================================================================
    # COMPONENT SCORING METHODS
    # ========================================================================

    def _score_preflight_checks(self, output: str) -> float:
        """
        Score pre-flight checks (40% weight - MOST CRITICAL).

        Checks:
        - Inspects package.json before running tests
        - Verifies test script is safe (non-interactive)
        - Reviews test command configuration

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for pre-flight patterns
        preflight_matches = [
            pattern for pattern in self.PREFLIGHT_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not preflight_matches:
            return 0.0

        # Check if pre-flight happens early (first 40% of output)
        output_lines = output.split('\n')
        first_section = '\n'.join(output_lines[:int(len(output_lines) * 0.4)])

        early_preflight = any(
            re.search(pattern, first_section, re.IGNORECASE)
            for pattern in self.PREFLIGHT_PATTERNS
        )

        # Scoring logic
        if early_preflight and len(preflight_matches) >= 3:
            # Perfect: comprehensive pre-flight early in workflow
            return 1.0
        elif early_preflight and len(preflight_matches) >= 2:
            # Good: pre-flight done early
            return 0.9
        elif len(preflight_matches) >= 2:
            # Acceptable: multiple checks but later
            return 0.7
        else:
            # Minimal: single check mentioned
            return 0.5

    def _score_post_execution_verification(self, output: str) -> float:
        """
        Score post-execution verification (35% weight).

        Checks:
        - Verifies clean process state after tests
        - Checks for orphaned processes
        - Uses ps aux or similar tools
        - Confirms no hanging processes

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for post-execution patterns
        post_execution_matches = [
            pattern for pattern in self.POST_EXECUTION_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not post_execution_matches:
            return 0.0

        # Scoring based on verification thoroughness
        verification_count = len(post_execution_matches)

        if verification_count >= 3:
            # Perfect: comprehensive post-execution verification
            return 1.0
        elif verification_count == 2:
            # Good: some verification done
            return 0.8
        else:
            # Minimal: verification mentioned
            return 0.5

    def _score_hanging_detection(self, output: str) -> float:
        """
        Score hanging process detection (15% weight).

        Checks:
        - Detects hanging/stuck test processes
        - Identifies non-responding processes
        - Checks for timeout issues

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for hanging detection patterns
        hanging_matches = [
            pattern for pattern in self.HANGING_DETECTION_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not hanging_matches:
            return 0.0

        # Scoring based on detection evidence
        detection_count = len(hanging_matches)

        if detection_count >= 2:
            # Perfect: explicit hanging detection
            return 1.0
        else:
            # Good: hanging detection mentioned
            return 0.7

    def _score_cleanup(self, output: str) -> float:
        """
        Score orphaned process cleanup (10% weight).

        Checks:
        - Cleans up orphaned node/vitest processes
        - Kills hanging processes
        - Terminates stuck processes

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for cleanup patterns
        cleanup_matches = [
            pattern for pattern in self.CLEANUP_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not cleanup_matches:
            return 0.0

        # Scoring based on cleanup actions
        cleanup_count = len(cleanup_matches)

        if cleanup_count >= 2:
            # Perfect: active cleanup performed
            return 1.0
        else:
            # Good: cleanup mentioned
            return 0.7

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        preflight_score: float,
        post_execution_score: float,
        hanging_detection_score: float,
        cleanup_score: float,
        output: str
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            preflight_score: Pre-flight checks score
            post_execution_score: Post-execution verification score
            hanging_detection_score: Hanging detection score
            cleanup_score: Cleanup score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Pre-flight issues (CRITICAL)
        if preflight_score < 0.5:
            reasons.append(
                "CRITICAL: No pre-flight checks (should inspect package.json before running tests)"
            )

        # Post-execution issues
        if post_execution_score < 0.5:
            reasons.append(
                "No post-execution verification (should check process state after tests)"
            )

        # Hanging detection issues
        if hanging_detection_score < 0.5:
            reasons.append(
                "No hanging process detection (should check for stuck processes)"
            )

        # Cleanup issues
        if cleanup_score < 0.5:
            reasons.append(
                "No orphaned process cleanup (should clean up node/vitest processes)"
            )

        # Success message
        if not reasons:
            return "Perfect process management - pre-flight checks, post-execution verification, cleanup"

        return "; ".join(reasons)


def create_process_management_metric(threshold: float = 0.9) -> ProcessManagementMetric:
    """
    Factory function to create process management metric.

    Args:
        threshold: Minimum passing score (default: 0.9 for 90% compliance)

    Returns:
        Configured metric instance

    Example:
        metric = create_process_management_metric(threshold=0.9)
        test_case = LLMTestCase(
            input="Run tests and verify cleanup",
            actual_output="Checking package.json... Running tests... Verifying ps aux..."
        )
        score = metric.measure(test_case)
    """
    return ProcessManagementMetric(threshold=threshold)
