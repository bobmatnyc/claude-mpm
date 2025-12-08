"""
Code Minimization Metric for Engineer Agent Testing.

This metric evaluates Engineer Agent compliance with code minimization mandate:
- Search-first workflow (vector search, grep before implementation)
- LOC delta reporting (mentions net lines added/removed)
- Reuse rate tracking (leveraging existing code)
- Consolidation opportunities (identifying duplicate code)
- Config vs code approach (solving through configuration)

Scoring Algorithm (weighted):
1. Search-First Evidence (30%): Detects vector search/grep before implementation
2. LOC Delta Reporting (25%): Mentions net lines added/removed
3. Reuse Rate (20%): References leveraging existing code
4. Consolidation Mentions (15%): Identifies opportunities to delete code
5. Config vs Code (10%): Solves through configuration when possible

Threshold: 0.8 (80% compliance required)

Example:
    metric = CodeMinimizationMetric(threshold=0.8)
    test_case = LLMTestCase(
        input="Implement user authentication",
        actual_output='''First searching for existing auth implementations...
        Found existing JWT validation, will reuse. Net LOC delta: -5 lines.
        Consolidated two similar functions into shared utility.'''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional, Tuple

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class CodeMinimizationMetric(BaseMetric):
    """
    DeepEval metric for Engineer Agent code minimization protocol compliance.

    Evaluates:
    1. Search-first workflow (vector search, grep before creating)
    2. LOC delta awareness (reporting net lines added/removed)
    3. Reuse rate (leveraging existing code vs creating new)
    4. Consolidation opportunities (identifying duplicate elimination)
    5. Configuration-driven approach (config vs code)

    Scoring:
    - 1.0: Perfect compliance (search-first, negative LOC, high reuse)
    - 0.8-0.99: Good compliance (search done, LOC tracked, some reuse)
    - 0.6-0.79: Acceptable (some search, LOC mentioned)
    - 0.0-0.59: Poor (no search, adding code without considering reuse)
    """

    # Search-first patterns
    SEARCH_PATTERNS: List[str] = [
        r'vector\s+search',
        r'search_code',
        r'mcp__mcp-vector-search',
        r'grep\s+(?:for|.*pattern)',
        r'search(?:ing|ed)?\s+(?:for|existing|codebase)',
        r'find.*existing',
        r'looked\s+for',
        r'checking\s+for\s+existing',
        r'before\s+implementing',
        r'first.*search',
        r'discover(?:ing|ed)?\s+existing'
    ]

    # LOC delta patterns
    LOC_DELTA_PATTERNS: List[str] = [
        r'net\s+(?:LOC|lines)',
        r'added\s+\d+\s+lines?',
        r'removed\s+\d+\s+lines?',
        r'LOC\s+delta',
        r'negative\s+delta',
        r'zero\s+net\s+lines?',
        r'\+\d+/-\d+\s+lines?',
        r'[-+]\d+\s+lines?',
        r'no\s+new\s+lines?',
        r'reduced.*lines?',
        r'eliminated.*lines?'
    ]

    # Reuse patterns
    REUSE_PATTERNS: List[str] = [
        r'extend(?:ed|ing)?',
        r'leverage\s+existing',
        r'reuse',
        r'build\s+on',
        r'enhance\s+existing',
        r'modify\s+existing',
        r'use\s+existing',
        r'found\s+(?:and\s+)?(?:used|reused)',
        r'already\s+(?:has|have|exists)',
        r'share(?:d)?\s+(?:utility|function|code)',
        r'common\s+(?:code|logic|function)'
    ]

    # Consolidation patterns
    CONSOLIDATION_PATTERNS: List[str] = [
        r'consolidat(?:e|ed|ing)',
        r'merge(?:d|ing)?',
        r'combine(?:d|ing)?',
        r'eliminate\s+duplicate',
        r'remove(?:d|ing)?\s+(?:redundant|duplicate|old)',
        r'unified',
        r'single\s+implementation',
        r'deleted\s+(?:old|duplicate|redundant)',
        r'extract(?:ed|ing)?\s+common',
        r'shared\s+(?:utility|helper|function)'
    ]

    # Config vs code patterns
    CONFIG_PATTERNS: List[str] = [
        r'configuration',
        r'config\s+file',
        r'settings',
        r'environment\s+variable',
        r'\.env',
        r'config\.(?:json|yaml|yml|toml)',
        r'data-driven',
        r'configurable',
        r'setting\s+in\s+config',
        r'through\s+configuration'
    ]

    def __init__(self, threshold: float = 0.8):
        """
        Initialize CodeMinimizationMetric.

        Args:
            threshold: Minimum score to pass (default: 0.8 for 80% compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Code Minimization"

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
        Measure code minimization compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output

        # Calculate component scores
        search_score = self._score_search_first(output)
        loc_delta_score = self._score_loc_delta_reporting(output)
        reuse_score = self._score_reuse_rate(output)
        consolidation_score = self._score_consolidation(output)
        config_score = self._score_config_vs_code(output)

        # Weighted average
        final_score = (
            search_score * 0.30 +
            loc_delta_score * 0.25 +
            reuse_score * 0.20 +
            consolidation_score * 0.15 +
            config_score * 0.10
        )

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            search_score,
            loc_delta_score,
            reuse_score,
            consolidation_score,
            config_score,
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

    def _score_search_first(self, output: str) -> float:
        """
        Score search-first workflow compliance (30% weight).

        Checks:
        - Detects vector search, grep, or search patterns
        - Should search before implementing new code
        - Rewards early search mentions

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for search patterns
        search_matches = [
            pattern for pattern in self.SEARCH_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not search_matches:
            return 0.0

        # Check if search happens early (first 30% of output)
        output_lines = output.split('\n')
        first_third = '\n'.join(output_lines[:len(output_lines)//3])

        early_search = any(
            re.search(pattern, first_third, re.IGNORECASE)
            for pattern in self.SEARCH_PATTERNS
        )

        # Scoring logic
        if early_search and len(search_matches) >= 2:
            # Perfect: multiple search types early in workflow
            return 1.0
        if early_search:
            # Good: search done early
            return 0.9
        if len(search_matches) >= 2:
            # Acceptable: multiple searches but later
            return 0.7
        # Minimal: search mentioned but not emphasized
        return 0.5

    def _score_loc_delta_reporting(self, output: str) -> float:
        """
        Score LOC delta reporting (25% weight).

        Checks:
        - Mentions net lines added/removed
        - Reports LOC delta, negative delta preferred
        - Quantifies code changes

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for LOC delta patterns
        has_loc_delta = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.LOC_DELTA_PATTERNS
        )

        if not has_loc_delta:
            return 0.0

        # Check for negative delta (removed more than added)
        negative_delta_patterns = [
            r'negative\s+delta',
            r'removed\s+\d+\s+lines?',
            r'reduced.*\d+\s+lines?',
            r'eliminated.*\d+\s+lines?',
            r'net.*-\d+',
            r'zero\s+net\s+lines?'
        ]

        has_negative_delta = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in negative_delta_patterns
        )

        # Scoring logic
        if has_negative_delta:
            # Perfect: negative LOC delta (ideal outcome)
            return 1.0
        # Good: LOC delta tracked even if positive
        return 0.7

    def _score_reuse_rate(self, output: str) -> float:
        """
        Score reuse rate compliance (20% weight).

        Checks:
        - References leveraging existing code
        - Extends or enhances rather than creating new
        - Mentions shared utilities or common code

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Count reuse patterns
        reuse_matches = [
            pattern for pattern in self.REUSE_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not reuse_matches:
            return 0.0

        # Scoring based on number of reuse mentions
        reuse_count = len(reuse_matches)

        if reuse_count >= 3:
            # Perfect: multiple reuse strategies
            return 1.0
        if reuse_count == 2:
            # Good: some reuse
            return 0.8
        # Minimal: single reuse mention
        return 0.5

    def _score_consolidation(self, output: str) -> float:
        """
        Score consolidation mentions (15% weight).

        Checks:
        - Identifies duplicate code opportunities
        - Consolidates, merges, or combines code
        - Removes redundant implementations

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for consolidation patterns
        consolidation_matches = [
            pattern for pattern in self.CONSOLIDATION_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not consolidation_matches:
            return 0.0

        # Scoring based on consolidation actions
        consolidation_count = len(consolidation_matches)

        if consolidation_count >= 2:
            # Perfect: active consolidation with evidence
            return 1.0
        # Good: consolidation mentioned
        return 0.7

    def _score_config_vs_code(self, output: str) -> float:
        """
        Score config vs code approach (10% weight).

        Checks:
        - Solves through configuration when possible
        - Uses environment variables, config files
        - Data-driven vs hardcoded solutions

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for config patterns
        has_config = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.CONFIG_PATTERNS
        )

        if not has_config:
            # Neutral score if no config mentioned (not always applicable)
            return 0.5

        # Perfect score if config-driven approach used
        return 1.0

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        search_score: float,
        loc_delta_score: float,
        reuse_score: float,
        consolidation_score: float,
        config_score: float,
        output: str
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            search_score: Search-first score
            loc_delta_score: LOC delta reporting score
            reuse_score: Reuse rate score
            consolidation_score: Consolidation score
            config_score: Config vs code score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Search-first issues
        if search_score < 0.5:
            reasons.append(
                "No search-first evidence (should use vector search/grep before implementing)"
            )

        # LOC delta issues
        if loc_delta_score < 0.5:
            reasons.append(
                "No LOC delta reporting (should mention net lines added/removed)"
            )

        # Reuse issues
        if reuse_score < 0.5:
            reasons.append(
                "No reuse evidence (should leverage existing code vs creating new)"
            )

        # Consolidation issues
        if consolidation_score < 0.5:
            reasons.append(
                "No consolidation opportunities identified (should look for duplicate elimination)"
            )

        # Config issues (only flag if truly missing, not neutral)
        if config_score < 0.5 and config_score > 0.0:
            reasons.append(
                "Could consider configuration-driven approach"
            )

        # Success message
        if not reasons:
            return "Perfect code minimization compliance - search-first, LOC tracking, high reuse"

        return "; ".join(reasons)


def create_code_minimization_metric(threshold: float = 0.8) -> CodeMinimizationMetric:
    """
    Factory function to create code minimization metric.

    Args:
        threshold: Minimum passing score (default: 0.8 for 80% compliance)

    Returns:
        Configured metric instance

    Example:
        metric = create_code_minimization_metric(threshold=0.8)
        test_case = LLMTestCase(
            input="Implement user authentication",
            actual_output="Searching for existing auth... found JWT validator, will reuse..."
        )
        score = metric.measure(test_case)
    """
    return CodeMinimizationMetric(threshold=threshold)
