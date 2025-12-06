"""
Coverage Quality Metric for QA Agent Testing.

This metric evaluates QA Agent compliance with coverage analysis best practices:
- Coverage tool usage (nyc, istanbul, c8, vitest --coverage, jest --coverage)
- Critical path focus (prioritizes uncovered critical paths over 100% coverage)
- Memory-efficient analysis (limits file reads, uses grep for discovery)
- High-impact test prioritization (focuses on important tests)

Scoring Algorithm (weighted):
1. Coverage Tool Usage (35%): Uses appropriate coverage tools
2. Critical Path Focus (30%): Prioritizes uncovered critical paths
3. Memory-Efficient Analysis (20%): Uses grep, limits file reads
4. High-Impact Test Prioritization (15%): Focuses on high-impact tests

Threshold: 0.85 (85% compliance required)

Example:
    metric = CoverageQualityMetric(threshold=0.85)
    test_case = LLMTestCase(
        input="Analyze test coverage",
        actual_output='''Running coverage analysis with: vitest run --coverage
        Coverage report shows 78% overall. Focusing on uncovered critical paths:
        - Authentication flow (0% coverage)
        - Payment processing (45% coverage)
        Using grep to find untested critical functions rather than reading all files.
        Prioritizing high-impact tests for auth and payment flows.'''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class CoverageQualityMetric(BaseMetric):
    """
    DeepEval metric for QA Agent coverage analysis quality.

    Evaluates:
    1. Coverage tool usage (nyc, istanbul, c8, vitest --coverage)
    2. Critical path focus (prioritizes uncovered critical paths)
    3. Memory-efficient analysis (grep, limited file reads)
    4. High-impact test prioritization (focuses on important tests)

    Scoring:
    - 1.0: Perfect compliance (coverage tools, critical path focus, memory-efficient)
    - 0.85-0.99: Good compliance (coverage analysis with some optimization)
    - 0.7-0.84: Acceptable (basic coverage analysis)
    - 0.0-0.69: Poor (no coverage analysis or inefficient approach)
    """

    # Coverage tool patterns
    COVERAGE_TOOL_PATTERNS: List[str] = [
        r'coverage',
        r'nyc',
        r'istanbul',
        r'c8',
        r'--coverage',
        r'coverage\s+report',
        r'vitest.*--coverage',
        r'jest.*--coverage',
        r'npm\s+run\s+coverage',
        r'coverage\s+analysis'
    ]

    # Critical path focus patterns
    CRITICAL_PATH_PATTERNS: List[str] = [
        r'critical\s+path',
        r'uncovered',
        r'high\s+priority',
        r'important\s+functions?',
        r'key\s+functionality',
        r'core\s+logic',
        r'business\s+critical',
        r'focus(?:ed|ing)?\s+on',
        r'prioritiz(?:e|ed|ing)',
        r'most\s+important'
    ]

    # Memory-efficient analysis patterns
    MEMORY_EFFICIENT_PATTERNS: List[str] = [
        r'grep',
        r'limited?',
        r'sample',
        r'\d+-\d+\s+files?',
        r'representative',
        r'select(?:ed|ing)',
        r'targeted',
        r'specific\s+files?',
        r'avoid(?:ed|ing)\s+reading\s+all',
        r'efficient\s+analysis'
    ]

    # High-impact test prioritization patterns
    PRIORITIZATION_PATTERNS: List[str] = [
        r'high-impact',
        r'prioritiz(?:e|ed|ing)',
        r'focus\s+on',
        r'most\s+important',
        r'critical\s+tests?',
        r'essential\s+tests?',
        r'key\s+tests?',
        r'important\s+tests?',
        r'priority\s+tests?'
    ]

    def __init__(self, threshold: float = 0.85):
        """
        Initialize CoverageQualityMetric.

        Args:
            threshold: Minimum score to pass (default: 0.85 for 85% compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Coverage Quality"

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
        Measure coverage quality compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output

        # Calculate component scores
        coverage_tool_score = self._score_coverage_tool_usage(output)
        critical_path_score = self._score_critical_path_focus(output)
        memory_efficient_score = self._score_memory_efficient_analysis(output)
        prioritization_score = self._score_test_prioritization(output)

        # Weighted average
        final_score = (
            coverage_tool_score * 0.35 +
            critical_path_score * 0.30 +
            memory_efficient_score * 0.20 +
            prioritization_score * 0.15
        )

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            coverage_tool_score,
            critical_path_score,
            memory_efficient_score,
            prioritization_score,
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

    def _score_coverage_tool_usage(self, output: str) -> float:
        """
        Score coverage tool usage (35% weight).

        Checks:
        - Uses coverage tools (nyc, istanbul, c8, vitest --coverage)
        - Generates coverage reports
        - Analyzes coverage data

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for coverage tool patterns
        tool_matches = [
            pattern for pattern in self.COVERAGE_TOOL_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not tool_matches:
            return 0.0

        # Scoring based on coverage tool usage depth
        tool_count = len(tool_matches)

        if tool_count >= 3:
            # Perfect: comprehensive coverage tool usage
            return 1.0
        elif tool_count == 2:
            # Good: coverage tools used
            return 0.9
        else:
            # Minimal: coverage mentioned
            return 0.6

    def _score_critical_path_focus(self, output: str) -> float:
        """
        Score critical path focus (30% weight).

        Checks:
        - Prioritizes uncovered critical paths
        - Focuses on high-priority areas
        - Identifies important functions/logic
        - Doesn't chase 100% coverage blindly

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for critical path patterns
        critical_matches = [
            pattern for pattern in self.CRITICAL_PATH_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not critical_matches:
            return 0.0

        # Scoring based on critical path focus depth
        critical_count = len(critical_matches)

        if critical_count >= 3:
            # Perfect: strong critical path focus
            return 1.0
        elif critical_count == 2:
            # Good: critical path considered
            return 0.8
        else:
            # Minimal: critical path mentioned
            return 0.5

    def _score_memory_efficient_analysis(self, output: str) -> float:
        """
        Score memory-efficient analysis (20% weight).

        Checks:
        - Uses grep for file discovery
        - Limits file reads (3-5 files, representative sample)
        - Avoids reading all files
        - Targeted analysis approach

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for memory-efficient patterns
        efficient_matches = [
            pattern for pattern in self.MEMORY_EFFICIENT_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not efficient_matches:
            return 0.0

        # Scoring based on memory efficiency evidence
        efficient_count = len(efficient_matches)

        if efficient_count >= 2:
            # Perfect: clearly memory-efficient approach
            return 1.0
        else:
            # Good: some efficiency consideration
            return 0.7

    def _score_test_prioritization(self, output: str) -> float:
        """
        Score high-impact test prioritization (15% weight).

        Checks:
        - Prioritizes high-impact tests
        - Focuses on most important tests
        - Identifies critical/essential tests

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for prioritization patterns
        priority_matches = [
            pattern for pattern in self.PRIORITIZATION_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not priority_matches:
            return 0.0

        # Scoring based on prioritization evidence
        priority_count = len(priority_matches)

        if priority_count >= 2:
            # Perfect: clear prioritization strategy
            return 1.0
        else:
            # Good: prioritization mentioned
            return 0.7

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        coverage_tool_score: float,
        critical_path_score: float,
        memory_efficient_score: float,
        prioritization_score: float,
        output: str
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            coverage_tool_score: Coverage tool usage score
            critical_path_score: Critical path focus score
            memory_efficient_score: Memory-efficient analysis score
            prioritization_score: Test prioritization score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Coverage tool issues
        if coverage_tool_score < 0.5:
            reasons.append(
                "No coverage tool usage (should use nyc, istanbul, c8, or vitest --coverage)"
            )

        # Critical path issues
        if critical_path_score < 0.5:
            reasons.append(
                "No critical path focus (should prioritize uncovered critical paths)"
            )

        # Memory efficiency issues
        if memory_efficient_score < 0.5:
            reasons.append(
                "No memory-efficient analysis (should use grep, limit file reads)"
            )

        # Prioritization issues
        if prioritization_score < 0.5:
            reasons.append(
                "No test prioritization (should focus on high-impact tests)"
            )

        # Success message
        if not reasons:
            return "Perfect coverage quality - tools used, critical path focus, memory-efficient, prioritized"

        return "; ".join(reasons)


def create_coverage_quality_metric(threshold: float = 0.85) -> CoverageQualityMetric:
    """
    Factory function to create coverage quality metric.

    Args:
        threshold: Minimum passing score (default: 0.85 for 85% compliance)

    Returns:
        Configured metric instance

    Example:
        metric = create_coverage_quality_metric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze test coverage",
            actual_output="Running vitest --coverage... Focusing on uncovered critical paths..."
        )
        score = metric.measure(test_case)
    """
    return CoverageQualityMetric(threshold=threshold)
