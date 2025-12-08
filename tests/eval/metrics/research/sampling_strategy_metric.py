"""
Sampling Strategy Metric for Research Agent Testing.

This metric evaluates whether the Research Agent uses strategic discovery and
sampling instead of brute-force reading of all files.

Scoring Algorithm (weighted components):
1. Discovery Tools (30%): grep/glob usage for file discovery
2. Pattern Extraction (25%): Synthesizes patterns/structure from findings
3. Strategic Sampling (25%): Representative samples vs exhaustive reads
4. Executive Summary (20%): High-level summary/overview present

Threshold: 0.85 (85% compliance required)

Example:
    metric = SamplingStrategyMetric(threshold=0.85)
    test_case = LLMTestCase(
        input="What is the architecture of this codebase?",
        actual_output='''I'll analyze the codebase architecture.

        *Uses Glob to discover files*
        *Uses Grep to search for patterns*

        Found 45 Python files across 3 main modules.

        Key patterns identified:
        - Service-oriented architecture with DI containers
        - Repository pattern for data access
        - Event-driven communication

        Representative samples:
        - src/services/user_service.py (service layer example)
        - src/repositories/base.py (repository pattern)

        Executive Summary:
        The codebase follows a clean architecture with separation of concerns.
        Service layer handles business logic, repositories manage data access.
        '''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class SamplingStrategyMetric(BaseMetric):
    """
    DeepEval metric for Research Agent sampling strategy compliance.

    Evaluates:
    1. Discovery tools usage (grep, glob, search)
    2. Pattern extraction and synthesis
    3. Strategic sampling approach
    4. Executive summary presence

    Scoring:
    - 1.0: Excellent strategic research (all components present)
    - 0.85-0.99: Good strategic approach (minor gaps)
    - 0.60-0.84: Some strategic elements (missing components)
    - 0.0-0.59: Poor strategy (brute force or minimal analysis)
    """

    # Discovery tool patterns (30% weight)
    DISCOVERY_PATTERNS = [
        r'\b(?:grep|Grep)\b',
        r'\b(?:glob|Glob)\b',
        r'search(?:ing|ed)?\s+for',
        r'find(?:ing)?\s+files',
        r'discover(?:ing|ed)?',
        r'scan(?:ning|ned)?',
    ]

    # Pattern extraction indicators (25% weight)
    PATTERN_EXTRACTION = [
        r'pattern\s*(?:s|:)',
        r'structure',
        r'architecture',
        r'design\s+pattern',
        r'identified\s+(?:the\s+)?(?:following|patterns)',
        r'key\s+(?:patterns|structures)',
        r'common\s+(?:pattern|approach)',
    ]

    # Strategic sampling indicators (25% weight)
    STRATEGIC_PATTERNS = [
        r'representative\s+sample',
        r'key\s+(?:files|examples)',
        r'strategic(?:ally)?',
        r'focused\s+on',
        r'selected\s+(?:files|examples)',
        r'sample\s+(?:files|from)',
        r'example\s+(?:files|implementation)',
    ]

    # Executive summary indicators (20% weight)
    SUMMARY_PATTERNS = [
        r'(?:executive\s+)?summary',
        r'overview',
        r'key\s+findings',
        r'conclusion',
        r'in\s+summary',
        r'to\s+summarize',
        r'overall',
        r'high-level',
    ]

    # Anti-patterns (negative signals)
    ANTI_PATTERNS = [
        r'reading\s+all',
        r'exhaustive',
        r'every\s+single',
        r'complete\s+list\s+of\s+all',
        r'processed\s+all\s+files',
        r'read\s+(?:all|every)',
    ]

    def __init__(self, threshold: float = 0.85):
        """
        Initialize SamplingStrategyMetric.

        Args:
            threshold: Minimum score to pass (default: 0.85 for high compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Sampling Strategy"

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
        Measure sampling strategy compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output

        # Calculate component scores
        discovery_score = self._score_discovery_tools(output)
        pattern_score = self._score_pattern_extraction(output)
        sampling_score = self._score_strategic_sampling(output)
        summary_score = self._score_executive_summary(output)
        anti_pattern_penalty = self._detect_anti_patterns(output)

        # Weighted average with anti-pattern penalty
        base_score = (
            discovery_score * 0.30 +
            pattern_score * 0.25 +
            sampling_score * 0.25 +
            summary_score * 0.20
        )

        # Apply penalty (reduce by up to 50% if anti-patterns detected)
        final_score = base_score * (1.0 - anti_pattern_penalty * 0.5)

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            discovery_score,
            pattern_score,
            sampling_score,
            summary_score,
            anti_pattern_penalty
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

    def _score_discovery_tools(self, output: str) -> float:
        """
        Score discovery tools usage (30% weight).

        Checks for grep, glob, search, find patterns in output.

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        matches = 0
        total_patterns = len(self.DISCOVERY_PATTERNS)

        for pattern in self.DISCOVERY_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                matches += 1

        # At least 2 different discovery patterns = full score
        # 1 pattern = partial score
        if matches >= 2:
            return 1.0
        if matches == 1:
            return 0.5
        return 0.0

    def _score_pattern_extraction(self, output: str) -> float:
        """
        Score pattern extraction and synthesis (25% weight).

        Checks for pattern identification, structure analysis, architecture.

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        matches = 0
        total_patterns = len(self.PATTERN_EXTRACTION)

        for pattern in self.PATTERN_EXTRACTION:
            if re.search(pattern, output, re.IGNORECASE):
                matches += 1

        # At least 2 pattern extraction indicators = full score
        # 1 indicator = partial score
        if matches >= 2:
            return 1.0
        if matches == 1:
            return 0.6
        return 0.0

    def _score_strategic_sampling(self, output: str) -> float:
        """
        Score strategic sampling approach (25% weight).

        Checks for representative samples, strategic selection, focused approach.

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        matches = 0
        total_patterns = len(self.STRATEGIC_PATTERNS)

        for pattern in self.STRATEGIC_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                matches += 1

        # At least 2 strategic sampling indicators = full score
        # 1 indicator = partial score
        if matches >= 2:
            return 1.0
        if matches == 1:
            return 0.6
        return 0.0

    def _score_executive_summary(self, output: str) -> float:
        """
        Score executive summary presence (20% weight).

        Checks for summary, overview, key findings, conclusion.

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        matches = 0
        total_patterns = len(self.SUMMARY_PATTERNS)

        for pattern in self.SUMMARY_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                matches += 1

        # At least 1 summary indicator = full score
        # (Summaries often use same keywords multiple times)
        if matches >= 1:
            return 1.0
        return 0.0

    def _detect_anti_patterns(self, output: str) -> float:
        """
        Detect anti-patterns that indicate brute force approach.

        Returns penalty factor from 0.0 (no penalty) to 1.0 (max penalty).

        Args:
            output: Agent output text

        Returns:
            Penalty factor (0.0 = no penalty, 1.0 = max penalty)
        """
        anti_pattern_count = 0

        for pattern in self.ANTI_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                anti_pattern_count += 1

        # Each anti-pattern adds 0.2 penalty (max 1.0)
        return min(anti_pattern_count * 0.2, 1.0)

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        discovery_score: float,
        pattern_score: float,
        sampling_score: float,
        summary_score: float,
        anti_pattern_penalty: float
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            discovery_score: Discovery tools score
            pattern_score: Pattern extraction score
            sampling_score: Strategic sampling score
            summary_score: Executive summary score
            anti_pattern_penalty: Anti-pattern penalty factor

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Check each component
        if discovery_score < 1.0:
            if discovery_score == 0.0:
                reasons.append("No discovery tools detected (missing grep/glob/search)")
            else:
                reasons.append("Limited discovery tools usage (expected 2+, found 1)")

        if pattern_score < 1.0:
            if pattern_score == 0.0:
                reasons.append("No pattern extraction detected (missing structure/architecture analysis)")
            else:
                reasons.append("Limited pattern extraction (expected 2+ indicators)")

        if sampling_score < 1.0:
            if sampling_score == 0.0:
                reasons.append("No strategic sampling detected (missing representative samples)")
            else:
                reasons.append("Limited strategic sampling (expected 2+ indicators)")

        if summary_score < 1.0:
            reasons.append("No executive summary or overview present")

        if anti_pattern_penalty > 0.0:
            penalty_pct = int(anti_pattern_penalty * 100)
            reasons.append(
                f"Anti-patterns detected: brute-force indicators (penalty: {penalty_pct}%)"
            )

        # Success message
        if not reasons:
            return "Excellent strategic research - all components present"

        return "; ".join(reasons)


def create_sampling_strategy_metric(threshold: float = 0.85) -> SamplingStrategyMetric:
    """
    Factory function to create sampling strategy metric.

    Args:
        threshold: Minimum passing score (default: 0.85)

    Returns:
        Configured metric instance

    Example:
        metric = create_sampling_strategy_metric(threshold=0.85)
        test_case = LLMTestCase(...)
        score = metric.measure(test_case)
    """
    return SamplingStrategyMetric(threshold=threshold)
