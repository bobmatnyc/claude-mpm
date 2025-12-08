"""
Consolidation Metric for Engineer Agent Testing.

This metric evaluates Engineer Agent compliance with consolidation protocol:
- Duplicate detection (searching for existing similar code)
- Consolidation decision-making (>80% similarity same domain, >50% different domain)
- Implementation quality (proper consolidation protocol followed)
- Single-path enforcement (only ONE implementation path)
- Session artifact cleanup (removing old versions, backups)

Scoring Algorithm (weighted):
1. Duplicate Detection (35%): Evidence of searching for duplicates
2. Consolidation Decision (30%): Correct decision-making for found duplicates
3. Implementation Quality (20%): Proper consolidation protocol followed
4. Single-Path Enforcement (10%): Ensures only ONE implementation path
5. Session Artifact Cleanup (5%): Removes old versions and backups

Threshold: 0.85 (85% compliance required - strict)

Example:
    metric = ConsolidationMetric(threshold=0.85)
    test_case = LLMTestCase(
        input="Implement JWT validation",
        actual_output='''Found duplicate JWT validation in auth_utils.py (85% similar).
        Same domain, consolidating into single implementation.
        Removed old auth_helper.py. Single canonical path established.'''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class ConsolidationMetric(BaseMetric):
    """
    DeepEval metric for Engineer Agent consolidation protocol compliance.

    Evaluates:
    1. Duplicate detection (searching for similar functions/files)
    2. Consolidation decision quality (>80% same domain, >50% shared logic)
    3. Implementation quality (merge protocol, reference updates)
    4. Single-path enforcement (one implementation per feature)
    5. Session artifact cleanup (removing _old, _v2, _backup files)

    Scoring:
    - 1.0: Perfect compliance (duplicates found, consolidated, cleanup done)
    - 0.85-0.99: Good compliance (duplicates handled, proper decisions)
    - 0.7-0.84: Acceptable (some consolidation, minor issues)
    - 0.0-0.69: Poor (no duplicate detection, multiple paths remain)
    """

    # Duplicate detection patterns
    DUPLICATE_DETECTION_PATTERNS: List[str] = [
        r"found\s+duplicate",
        r"similar\s+(?:function|implementation|code)",
        r"existing\s+implementation",
        r"already\s+exists",
        r"redundant\s+(?:code|function|implementation)",
        r"duplicate\s+(?:code|logic|function)",
        r"same\s+(?:functionality|logic|implementation)",
        r"identical\s+(?:to|function|code)",
        r"(?:\d+)%\s+similar",
        r"overlap(?:ping)?.*(?:code|functionality)",
        r"vector\s+search.*found\s+(?:similar|existing)",
    ]

    # Consolidation decision patterns
    DECISION_PATTERNS: List[str] = [
        r">?\s*80%\s+(?:similar|similarity)",
        r">?\s*50%\s+(?:shared|similar)",
        r"same\s+domain",
        r"different\s+domain",
        r"consolidat(?:e|ing)",
        r"merge\s+(?:into|with)",
        r"extract\s+common",
        r"shared\s+(?:utility|abstraction)",
        r"decision.*consolidat",
        r"should\s+(?:consolidate|merge|combine)",
    ]

    # Implementation quality patterns
    IMPLEMENTATION_PATTERNS: List[str] = [
        r"consolidat(?:ed|ing)",
        r"merged.*into",
        r"single\s+implementation",
        r"unified",
        r"update(?:d|ing)?\s+(?:references|imports|calls)",
        r"removed?\s+(?:obsolete|deprecated|old)",
        r"canonical\s+(?:version|implementation)",
        r"extract(?:ed|ing)\s+(?:common|shared)",
        r"shared\s+(?:utility|helper|module)",
        r"consolidation\s+(?:complete|done)",
    ]

    # Single-path enforcement patterns
    SINGLE_PATH_PATTERNS: List[str] = [
        r"(?:one|single|only)\s+implementation",
        r"single\s+(?:path|source|canonical)",
        r"removed?\s+(?:duplicate|old|alternate)",
        r"deleted?\s+(?:redundant|duplicate)",
        r"only\s+(?:one|single)\s+(?:way|path|implementation)",
        r"canonical\s+(?:implementation|version)",
        r"eliminated\s+(?:alternate|duplicate)\s+path",
        r"no\s+(?:duplicate|alternate)\s+paths?",
    ]

    # Session artifact cleanup patterns
    CLEANUP_PATTERNS: List[str] = [
        r"removed?\s+_old",
        r"deleted?\s+_v\d+",
        r"removed?\s+_backup",
        r"cleanup\s+(?:old|obsolete|deprecated)",
        r"deleted?\s+(?:orphaned|stale|old)",
        r"removed?\s+(?:legacy|deprecated)",
        r"cleanup\s+(?:complete|done)",
        r"no\s+(?:orphaned|stale)\s+files?",
    ]

    def __init__(self, threshold: float = 0.85):
        """
        Initialize ConsolidationMetric.

        Args:
            threshold: Minimum score to pass (default: 0.85 for 85% compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Consolidation"

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
        Measure consolidation compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output

        # Calculate component scores
        detection_score = self._score_duplicate_detection(output)
        decision_score = self._score_consolidation_decision(output)
        implementation_score = self._score_implementation_quality(output)
        single_path_score = self._score_single_path_enforcement(output)
        cleanup_score = self._score_session_artifact_cleanup(output)

        # Weighted average
        final_score = (
            detection_score * 0.35
            + decision_score * 0.30
            + implementation_score * 0.20
            + single_path_score * 0.10
            + cleanup_score * 0.05
        )

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            detection_score,
            decision_score,
            implementation_score,
            single_path_score,
            cleanup_score,
            output,
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

    def _score_duplicate_detection(self, output: str) -> float:
        """
        Score duplicate detection compliance (35% weight).

        Checks:
        - Searches for existing similar code
        - Uses vector search, grep, file comparisons
        - Identifies duplicate functionality

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Count duplicate detection patterns
        detection_matches = [
            pattern
            for pattern in self.DUPLICATE_DETECTION_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not detection_matches:
            # No duplicate detection mentioned
            return 0.0

        # Check for search tools used
        search_tool_patterns = [
            r"vector\s+search",
            r"search_code",
            r"grep",
            r"find.*similar",
            r"search(?:ing|ed)?\s+for\s+(?:duplicate|similar|existing)",
        ]

        has_search_tools = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in search_tool_patterns
        )

        # Scoring logic
        if len(detection_matches) >= 3 and has_search_tools:
            # Perfect: comprehensive duplicate detection with tools
            return 1.0
        if len(detection_matches) >= 2 or has_search_tools:
            # Good: multiple detection patterns or tool usage
            return 0.8
        # Minimal: duplicate mentioned but not thoroughly searched
        return 0.5

    def _score_consolidation_decision(self, output: str) -> float:
        """
        Score consolidation decision quality (30% weight).

        Checks:
        - Correct decision-making (>80% similarity → consolidate)
        - Domain analysis (same vs different domain)
        - Proper consolidation vs extraction decisions

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for decision patterns
        decision_matches = [
            pattern
            for pattern in self.DECISION_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not decision_matches:
            return 0.0

        # Check for proper similarity thresholds
        similarity_patterns = [
            r">?\s*80%\s+(?:similar|similarity)",
            r">?\s*50%\s+(?:shared|similar)",
            r"(\d+)%\s+(?:similar|similarity)",
        ]

        has_similarity_analysis = any(
            re.search(pattern, output, re.IGNORECASE) for pattern in similarity_patterns
        )

        # Check for domain analysis
        domain_patterns = [r"same\s+domain", r"different\s+domain", r"cross-domain"]

        has_domain_analysis = any(
            re.search(pattern, output, re.IGNORECASE) for pattern in domain_patterns
        )

        # Scoring logic
        if has_similarity_analysis and has_domain_analysis:
            # Perfect: thorough analysis with thresholds and domain
            return 1.0
        if has_similarity_analysis or has_domain_analysis:
            # Good: some analysis done
            return 0.8
        if len(decision_matches) >= 2:
            # Acceptable: decision made but not quantified
            return 0.6
        # Minimal: decision mentioned
        return 0.4

    def _score_implementation_quality(self, output: str) -> float:
        """
        Score implementation quality (20% weight).

        Checks:
        - Consolidation protocol followed (merge, update refs, remove old)
        - Proper consolidation execution
        - Reference updates documented

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Count implementation patterns
        implementation_matches = [
            pattern
            for pattern in self.IMPLEMENTATION_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not implementation_matches:
            return 0.0

        # Check for reference updates
        reference_update_patterns = [
            r"update(?:d|ing)?\s+(?:references|imports|calls)",
            r"changed?\s+(?:imports|references)",
            r"modified?\s+(?:calls|imports)",
        ]

        has_reference_updates = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in reference_update_patterns
        )

        # Scoring logic
        if len(implementation_matches) >= 3 and has_reference_updates:
            # Perfect: comprehensive consolidation with reference updates
            return 1.0
        if len(implementation_matches) >= 2:
            # Good: consolidation done with some documentation
            return 0.8
        # Minimal: consolidation mentioned
        return 0.5

    def _score_single_path_enforcement(self, output: str) -> float:
        """
        Score single-path enforcement (10% weight).

        Checks:
        - Ensures only ONE implementation path
        - Removes alternate/duplicate implementations
        - Establishes canonical version

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for single-path patterns
        single_path_matches = [
            pattern
            for pattern in self.SINGLE_PATH_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not single_path_matches:
            # Neutral score if not applicable (no consolidation needed)
            return 0.7

        # Scoring based on enforcement clarity
        if len(single_path_matches) >= 2:
            # Perfect: explicit single-path enforcement
            return 1.0
        # Good: single-path mentioned
        return 0.8

    def _score_session_artifact_cleanup(self, output: str) -> float:
        """
        Score session artifact cleanup (5% weight).

        Checks:
        - Removes _old, _v2, _backup files
        - Cleans up orphaned session files
        - No stale implementations left behind

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
            # Neutral score if not applicable
            return 0.7

        # Perfect score if cleanup done
        return 1.0

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        detection_score: float,
        decision_score: float,
        implementation_score: float,
        single_path_score: float,
        cleanup_score: float,
        output: str,
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            detection_score: Duplicate detection score
            decision_score: Consolidation decision score
            implementation_score: Implementation quality score
            single_path_score: Single-path enforcement score
            cleanup_score: Session artifact cleanup score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Detection issues
        if detection_score < 0.5:
            reasons.append(
                "No duplicate detection evidence (should search for similar code first)"
            )

        # Decision issues
        if decision_score < 0.5:
            reasons.append(
                "No consolidation decision analysis (should apply >80% same domain, >50% shared logic criteria)"
            )

        # Implementation issues
        if implementation_score < 0.5:
            reasons.append(
                "Consolidation protocol not followed (should merge, update references, remove old)"
            )

        # Single-path issues (only flag if consolidation was done)
        if single_path_score < 0.7 and detection_score >= 0.5:
            reasons.append(
                "Single-path enforcement unclear (should ensure only ONE implementation)"
            )

        # Cleanup issues (only flag if consolidation was done)
        if cleanup_score < 0.7 and detection_score >= 0.5:
            reasons.append(
                "Session artifact cleanup not mentioned (should remove _old, _v2, _backup files)"
            )

        # Success message
        if not reasons:
            return "Perfect consolidation compliance - duplicates detected, correct decisions, proper implementation"

        return "; ".join(reasons)


def create_consolidation_metric(threshold: float = 0.85) -> ConsolidationMetric:
    """
    Factory function to create consolidation metric.

    Args:
        threshold: Minimum passing score (default: 0.85 for 85% compliance)

    Returns:
        Configured metric instance

    Example:
        metric = create_consolidation_metric(threshold=0.85)
        test_case = LLMTestCase(
            input="Implement user authentication",
            actual_output="Found duplicate auth in helpers.py (85% similar), consolidating..."
        )
        score = metric.measure(test_case)
    """
    return ConsolidationMetric(threshold=threshold)
