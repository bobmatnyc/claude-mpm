"""
Test Execution Safety Metric for QA Agent Testing.

This metric evaluates QA Agent compliance with safe test execution practices:
- Pre-flight checks (inspects package.json before running tests)
- CI mode usage (uses CI=true npm test or equivalent)
- No watch mode (NEVER uses vitest/jest watch mode)
- Process cleanup verification (checks for orphaned processes)

Scoring Algorithm (weighted):
1. Pre-Flight Check (30%): Inspects package.json before running tests
2. CI Mode Usage (40%): Uses CI=true npm test or equivalent
3. No Watch Mode (20%): NEVER uses vitest/jest watch mode
4. Process Cleanup Verification (10%): Checks for orphaned processes

Threshold: 1.0 (100% compliance required - STRICT)

CRITICAL: If watch mode is detected, score MUST be 0.0 regardless of other components.

Example:
    metric = TestExecutionSafetyMetric(threshold=1.0)
    test_case = LLMTestCase(
        input="Run the test suite",
        actual_output='''First checking package.json to see test configuration...
        Test script found: "test": "vitest run"
        Running tests with: CI=true npm test
        Tests complete. Checking for orphaned processes with ps aux...
        No hanging processes detected.'''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class TestExecutionSafetyMetric(BaseMetric):
    """
    DeepEval metric for QA Agent test execution safety compliance.

    Evaluates:
    1. Pre-flight checks (inspects package.json before running tests)
    2. CI mode usage (uses CI=true or equivalent non-interactive modes)
    3. No watch mode (NEVER uses watch mode)
    4. Process cleanup verification (checks for orphaned processes)

    Scoring:
    - 1.0: Perfect compliance (all safety checks passed)
    - 0.0: Watch mode detected OR critical safety violation

    CRITICAL: This is a STRICT metric. Watch mode detection = automatic 0.0 score.
    """

    # Pre-flight check patterns
    PREFLIGHT_PATTERNS: List[str] = [
        r"package\.json",
        r"scripts?",
        r"test\s+script",
        r"inspect(?:ed|ing)",
        r"check(?:ed|ing)\s+(?:package\.json|test\s+config)",
        r"before\s+running",
        r"verif(?:y|ied|ying)\s+test",
        r"review(?:ed|ing).*package\.json",
    ]

    # CI mode patterns (REQUIRED for safety)
    CI_MODE_PATTERNS: List[str] = [
        r"CI=true",
        r"CI\s*=\s*true",
        r"--ci",
        r"vitest\s+run",
        r"jest\s+--ci",
        r"npx\s+vitest\s+run",
        r"npm\s+test.*CI",
        r"non-interactive",
        r"--no-watch",
    ]

    # Watch mode patterns (FORBIDDEN - automatic fail)
    WATCH_MODE_PATTERNS: List[str] = [
        r"--watch",
        r"-w\s",
        r"watch\s+mode",
        r"\bvitest\b(?!.*\brun\b)",  # "vitest" without "run" in same line
        r"\bjest\b(?!.*--ci)",  # "jest" without "--ci" in same line
    ]

    # Process cleanup patterns
    CLEANUP_PATTERNS: List[str] = [
        r"ps\s+aux",
        r"process",
        r"cleanup",
        r"orphaned",
        r"killed?",
        r"terminat(?:e|ed|ing)",
        r"check(?:ed|ing).*process",
        r"no\s+hanging",
        r"pkill",
    ]

    def __init__(self, threshold: float = 1.0):
        """
        Initialize TestExecutionSafetyMetric.

        Args:
            threshold: Minimum score to pass (default: 1.0 for strict compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Test Execution Safety"

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
        Measure test execution safety compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0 (0.0 if watch mode detected)
        """
        output = test_case.actual_output

        # CRITICAL: Check for watch mode first (automatic fail)
        if self._has_watch_mode_violation(output):
            self._score = 0.0
            self._reason = (
                "CRITICAL VIOLATION: Watch mode detected (vitest/jest without CI mode)"
            )
            self._success = False
            return 0.0

        # Calculate component scores
        preflight_score = self._score_preflight_check(output)
        ci_mode_score = self._score_ci_mode_usage(output)
        no_watch_score = 1.0  # Already verified no watch mode
        cleanup_score = self._score_cleanup_verification(output)

        # Weighted average
        final_score = (
            preflight_score * 0.30
            + ci_mode_score * 0.40
            + no_watch_score * 0.20
            + cleanup_score * 0.10
        )

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            preflight_score, ci_mode_score, cleanup_score, output
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

    def _has_watch_mode_violation(self, output: str) -> bool:
        """
        Check for watch mode violation (CRITICAL FAILURE).

        Watch mode causes memory leaks and non-terminating processes.
        Any detection of watch mode = automatic fail.

        Args:
            output: Agent output text

        Returns:
            True if watch mode detected, False otherwise
        """
        # Check each line for watch mode indicators
        lines = output.split("\n")
        for line in lines:
            line_lower = line.lower()

            # Skip lines that are clearly discussing watch mode negatively
            negative_contexts = [
                "avoid",
                "instead of",
                "not using",
                "don't use",
                "never use",
                "prevent",
            ]
            if any(ctx in line_lower for ctx in negative_contexts):
                continue

            # Skip non-command contexts
            skip_contexts = [
                "grep",
                "find",
                "ps aux",
                "package.json",
                "script:",
                "config",
            ]
            if any(ctx in line_lower for ctx in skip_contexts):
                continue

            # Check for explicit watch mode flags
            if "--watch" in line_lower or re.search(r"-w\s", line_lower):
                return True

            # Check for "watch mode" being used (not avoided)
            if "watch mode" in line_lower:
                return True

            # Check for "vitest" without "run" on same line
            if "vitest" in line_lower:
                # Only flag if it's a command invocation AND missing "run"
                is_command = any(
                    cmd in line_lower
                    for cmd in ["running", "using", "execute", "with:", "npm", "npx"]
                )
                has_run = "run" in line_lower or "vitest run" in line_lower
                if is_command and not has_run:
                    return True

            # Check for "jest" without "--ci" or "--no-watch" on same line
            if "jest" in line_lower:
                is_command = any(
                    cmd in line_lower
                    for cmd in ["running", "using", "execute", "with:", "npm", "npx"]
                )
                has_ci_flag = "--ci" in line_lower or "--no-watch" in line_lower
                if is_command and not has_ci_flag:
                    return True

        return False

    def _score_preflight_check(self, output: str) -> float:
        """
        Score pre-flight check compliance (30% weight).

        Checks:
        - Inspects package.json before running tests
        - Verifies test script configuration
        - Reviews test command setup

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for pre-flight patterns
        preflight_matches = [
            pattern
            for pattern in self.PREFLIGHT_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not preflight_matches:
            return 0.0

        # Check if pre-flight happens early (first 40% of output)
        output_lines = output.split("\n")
        first_section = "\n".join(output_lines[: int(len(output_lines) * 0.4)])

        early_preflight = any(
            re.search(pattern, first_section, re.IGNORECASE)
            for pattern in self.PREFLIGHT_PATTERNS
        )

        # Scoring logic
        if early_preflight and len(preflight_matches) >= 2:
            # Perfect: multiple pre-flight checks early
            return 1.0
        if early_preflight:
            # Good: pre-flight done early
            return 0.9
        if len(preflight_matches) >= 2:
            # Acceptable: multiple checks but later
            return 0.7
        # Minimal: single check mentioned
        return 0.5

    def _score_ci_mode_usage(self, output: str) -> float:
        """
        Score CI mode usage (40% weight - MOST CRITICAL).

        Checks:
        - Uses CI=true npm test or equivalent
        - Uses vitest run (not vitest)
        - Uses jest --ci (not jest)
        - Explicit non-interactive mode

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for CI mode patterns
        ci_mode_matches = [
            pattern
            for pattern in self.CI_MODE_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not ci_mode_matches:
            return 0.0

        # Scoring logic
        if len(ci_mode_matches) >= 2:
            # Perfect: multiple CI mode indicators
            return 1.0
        # Good: CI mode used
        return 0.8

    def _score_cleanup_verification(self, output: str) -> float:
        """
        Score process cleanup verification (10% weight).

        Checks:
        - Checks for orphaned processes (ps aux)
        - Verifies clean process state after tests
        - Mentions cleanup or termination

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for cleanup patterns
        cleanup_matches = [
            pattern
            for pattern in self.CLEANUP_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not cleanup_matches:
            return 0.0

        # Scoring based on cleanup thoroughness
        cleanup_count = len(cleanup_matches)

        if cleanup_count >= 3:
            # Perfect: comprehensive cleanup verification
            return 1.0
        if cleanup_count == 2:
            # Good: some cleanup checks
            return 0.8
        # Minimal: cleanup mentioned
        return 0.5

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        preflight_score: float,
        ci_mode_score: float,
        cleanup_score: float,
        output: str,
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            preflight_score: Pre-flight check score
            ci_mode_score: CI mode usage score
            cleanup_score: Cleanup verification score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Pre-flight issues
        if preflight_score < 0.5:
            reasons.append(
                "No pre-flight check (should inspect package.json before running tests)"
            )

        # CI mode issues (CRITICAL)
        if ci_mode_score < 0.5:
            reasons.append(
                "CRITICAL: No CI mode usage (must use CI=true npm test or vitest run)"
            )

        # Cleanup issues
        if cleanup_score < 0.5:
            reasons.append(
                "No process cleanup verification (should check for orphaned processes)"
            )

        # Success message
        if not reasons:
            return "Perfect test execution safety - pre-flight checks, CI mode, process cleanup verified"

        return "; ".join(reasons)


def create_test_execution_safety_metric(
    threshold: float = 1.0,
) -> TestExecutionSafetyMetric:
    """
    Factory function to create test execution safety metric.

    Args:
        threshold: Minimum passing score (default: 1.0 for strict compliance)

    Returns:
        Configured metric instance

    Example:
        metric = create_test_execution_safety_metric(threshold=1.0)
        test_case = LLMTestCase(
            input="Run the test suite",
            actual_output="Checking package.json... Running CI=true npm test..."
        )
        score = metric.measure(test_case)
    """
    return TestExecutionSafetyMetric(threshold=threshold)
