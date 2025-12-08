"""
Audience Awareness Metric for Documentation Agent Testing.

This metric evaluates Documentation Agent compliance with audience adaptation:
- Audience targeting (35%): Clear audience statements, appropriate depth
- Technical depth (30%): Matches audience expertise level
- Context adaptation (20%): Public vs internal documentation
- Prerequisites (15%): Clear prerequisite knowledge statements
- Maintenance bonus (+10%): Version info, deprecation warnings

Scoring Algorithm (weighted):
1. Audience Targeting (35%): Detects audience statements, checks consistency
2. Technical Depth (30%): Validates depth matches audience (dev vs user)
3. Context Adaptation (20%): Checks for internal references in public docs
4. Prerequisites (15%): Detects prerequisite statements and links
5. Maintenance Bonus (+10%): Version info, last updated, deprecation warnings

Threshold: 0.80 (80% compliance required)

Example:
    metric = AudienceAwarenessMetric(threshold=0.80)
    test_case = LLMTestCase(
        input="Document the WebSocket API for senior engineers",
        actual_output='''# WebSocket Connection Management

        **Audience**: Senior Engineers
        **Prerequisites**: Familiarity with WebSocket protocol (RFC 6455)

        ## Architecture Overview
        We chose a connection pool with heartbeat monitoring to optimize
        resource usage under load.

        ```typescript
        class ConnectionPool {
          private heartbeatInterval = 30_000; // RFC 6455 recommendation
          // ...
        }
        ```

        **Version**: 2.1.0
        **Last Updated**: December 6, 2025
        '''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class AudienceAwarenessMetric(BaseMetric):
    """
    DeepEval metric for Documentation Agent audience awareness compliance.

    Evaluates:
    1. Audience targeting (35%): Clear audience statements, consistent depth
    2. Technical depth (30%): Appropriate complexity for audience
    3. Context adaptation (20%): Public vs internal appropriateness
    4. Prerequisites (15%): Clear prerequisite knowledge statements
    5. Maintenance bonus (+10%): Version info, deprecation warnings

    Scoring:
    - 1.0: Perfect compliance (all components well-covered)
    - 0.80-0.99: Excellent (threshold pass)
    - 0.65-0.79: Good (below threshold)
    - 0.0-0.64: Poor (significant gaps)
    """

    # Audience targeting patterns (35% weight)
    AUDIENCE_STATEMENT_PATTERNS: List[str] = [
        r'\*\*Audience\*\*:',
        r'This (?:guide|documentation|doc) is for',
        r'Intended for',
        r'Target audience:',
        r'For (?:developers|engineers|users|administrators)',
        r'Skill Level:',
    ]

    # Technical depth indicators - developer-focused
    DEVELOPER_DEPTH_PATTERNS: List[str] = [
        r'## Architecture',
        r'Design Decision',
        r'Trade-offs?:',
        r'```(?:typescript|python|go|rust|java|c\+\+)',
        r'class \w+',
        r'function \w+',
        r'interface \w+',
        r'RFC \d+',
        r'algorithm:',
        r'complexity:',
        r'O\(\w+\)',  # Big-O notation
    ]

    # Technical depth indicators - user-focused
    USER_DEPTH_PATTERNS: List[str] = [
        r'Step \d+:',
        r'Click (?:the|on)',
        r'Navigate to',
        r'!\[Screenshot\]',
        r'Select (?:the|from)',
        r'Choose',
        r'How to',
        r'button',
        r'menu',
        r'dropdown',
    ]

    # Context adaptation - internal references (negative for public docs)
    INTERNAL_CONTEXT_PATTERNS: List[str] = [
        r'k8s-(?:prod|staging)',
        r'#oncall-',
        r'#team-',
        r'\.internal\b',
        r'JIRA:',
        r'Runbook:',
        r'Slack channel:',
        r'our team',
        r'internal tool',
        r'company\s+(?:wiki|docs)',
        r'@company\.com',
    ]

    # Context adaptation - public references (positive for public docs)
    PUBLIC_CONTEXT_PATTERNS: List[str] = [
        r'Contact (?:support|sales)@',
        r'https://(?:docs|api|developer)\.example\.com',
        r'GitHub Issues:',
        r'community forum',
        r'Stack Overflow',
        r'public API',
        r'open[- ]source',
    ]

    # Prerequisite patterns (15% weight)
    PREREQUISITE_PATTERNS: List[str] = [
        r'\*\*Prerequisites\*\*:',
        r'## Prerequisites',
        r'Required Knowledge:',
        r'You should (?:know|understand|be familiar with)',
        r'Familiarity with',
        r'Before you begin',
        r'Assumes knowledge of',
        r'This guide assumes',
    ]

    PREREQUISITE_LINKS_PATTERNS: List[str] = [
        r'\[.*\]\(http.*\)',  # Markdown links
        r'See \[.*\]',
        r'Learn more:',
        r'Reference:',
    ]

    # Maintenance patterns (bonus +10%)
    VERSION_INFO_PATTERNS: List[str] = [
        r'\*\*Version\*\*:',
        r'## Version',
        r'Last Updated:',
        r'Updated:',
        r'Tested with:',
        r'Since v\d+\.\d+',
        r'API Version:',
        r'v\d+\.\d+\.\d+',
    ]

    DEPRECATION_PATTERNS: List[str] = [
        r'⚠️\s*Deprecated',
        r'DEPRECATED',
        r'Removed in v\d+',
        r'Legacy',
        r'No longer supported',
        r'Migration Guide:',
    ]

    def __init__(self, threshold: float = 0.80):
        """
        Initialize AudienceAwarenessMetric.

        Args:
            threshold: Minimum score to pass (default: 0.80 for 80% compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Audience Awareness"

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
        Measure audience awareness compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.10 (with bonus)
        """
        output = test_case.actual_output

        # Calculate component scores
        audience_targeting_score = self._score_audience_targeting(output)
        technical_depth_score = self._score_technical_depth(output)
        context_adaptation_score = self._score_context_adaptation(output)
        prerequisites_score = self._score_prerequisites(output)
        maintenance_bonus = self._score_maintenance(output)

        # Weighted average (base score)
        base_score = (
            audience_targeting_score * 0.35 +
            technical_depth_score * 0.30 +
            context_adaptation_score * 0.20 +
            prerequisites_score * 0.15
        )

        # Add maintenance bonus (up to +10%)
        final_score = base_score + maintenance_bonus

        # Cap at 1.0 for threshold comparison
        capped_score = min(final_score, 1.0)

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            audience_targeting_score,
            technical_depth_score,
            context_adaptation_score,
            prerequisites_score,
            maintenance_bonus,
            output
        )
        epsilon = 1e-9
        self._success = capped_score >= (self.threshold - epsilon)

        return final_score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure (delegates to sync)."""
        return self.measure(test_case)

    # ========================================================================
    # COMPONENT SCORING METHODS
    # ========================================================================

    def _score_audience_targeting(self, output: str) -> float:
        """
        Score audience targeting (35% weight - HIGHEST).

        Detects:
        - Audience statements: "Audience:", "For developers"
        - Consistency: No mixed developer/user indicators
        - Clear targeting upfront

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for explicit audience statement
        audience_stated = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.AUDIENCE_STATEMENT_PATTERNS
        )

        # Check for developer indicators
        dev_indicators = sum(
            1 for pattern in self.DEVELOPER_DEPTH_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        )

        # Check for user indicators
        user_indicators = sum(
            1 for pattern in self.USER_DEPTH_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        # Check for mixed indicators (negative)
        has_mixed_indicators = dev_indicators > 0 and user_indicators > 0

        # Scoring logic
        if audience_stated and not has_mixed_indicators:
            # Clear audience statement + consistent depth
            return 1.0
        if audience_stated and has_mixed_indicators:
            # Audience stated but mixed signals
            return 0.8
        if not audience_stated and not has_mixed_indicators:
            # No statement but consistent depth (implied audience)
            return 0.6
        # Mixed signals, no clear audience
        return 0.3

    def _score_technical_depth(self, output: str) -> float:
        """
        Score technical depth adaptation (30% weight).

        Detects:
        - Developer docs: Architecture, design decisions, code examples
        - User docs: Step-by-step instructions, UI elements
        - Appropriate depth for stated audience

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        dev_indicators = sum(
            1 for pattern in self.DEVELOPER_DEPTH_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        )

        user_indicators = sum(
            1 for pattern in self.USER_DEPTH_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        # Check if audience is explicitly stated
        is_developer_doc = any(
            re.search(r'(?:developer|engineer|architect)', output, re.IGNORECASE)
            for _ in [1]  # Check once
        )

        is_user_doc = any(
            re.search(r'(?:user|end[- ]user|customer)', output, re.IGNORECASE)
            for _ in [1]
        )

        # Score based on depth appropriateness
        if is_developer_doc and dev_indicators >= 3:
            # Developer doc with appropriate depth
            return 1.0
        if is_user_doc and user_indicators >= 3:
            # User doc with appropriate depth
            return 1.0
        if dev_indicators >= 3 and user_indicators == 0:
            # Clearly developer-focused (implied)
            return 0.8
        if user_indicators >= 3 and dev_indicators == 0:
            # Clearly user-focused (implied)
            return 0.8
        if dev_indicators > 0 and user_indicators > 0:
            # Mixed depth (might be intentional for dual audience)
            return 0.6
        # No clear depth indicators
        return 0.4

    def _score_context_adaptation(self, output: str) -> float:
        """
        Score context adaptation (20% weight).

        Detects:
        - Internal references (negative for public docs): k8s-prod, #oncall
        - Public references (positive for public docs): GitHub Issues
        - Appropriate context for audience

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        internal_matches = sum(
            1 for pattern in self.INTERNAL_CONTEXT_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        public_matches = sum(
            1 for pattern in self.PUBLIC_CONTEXT_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        # Determine if this is likely a public or internal doc
        # (Based on presence of internal/public indicators)
        total_context = internal_matches + public_matches

        if total_context == 0:
            # No context indicators - neutral (might be okay)
            return 0.7

        # Check for context violations
        if internal_matches > 0 and public_matches > 0:
            # Mixed context (might be intentional or violation)
            return 0.6
        if internal_matches > 0:
            # Internal doc - check if it's marked as such
            is_marked_internal = re.search(
                r'(?:internal|private|team-only)',
                output,
                re.IGNORECASE
            )
            if is_marked_internal:
                return 1.0  # Correctly marked internal
            return 0.5  # Internal references without marking
        if public_matches > 0:
            # Public doc - good
            return 1.0
        return 0.7  # Neutral

    def _score_prerequisites(self, output: str) -> float:
        """
        Score prerequisites statement (15% weight).

        Detects:
        - Prerequisite statements: "Prerequisites:", "Required Knowledge"
        - Links to prerequisite resources
        - Clear skill level statements

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        prereq_statements = sum(
            1 for pattern in self.PREREQUISITE_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        )

        prereq_links = sum(
            1 for pattern in self.PREREQUISITE_LINKS_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        total_prereqs = prereq_statements + prereq_links

        if total_prereqs >= 3:
            return 1.0  # Clear prerequisites with links
        if total_prereqs == 2:
            return 0.8  # Prerequisites stated, some links
        if total_prereqs == 1:
            return 0.6  # Minimal prerequisites
        return 0.3  # No prerequisites stated

    def _score_maintenance(self, output: str) -> float:
        """
        Score maintenance adherence bonus (+10% maximum).

        Detects:
        - Version information: "Version:", "Last Updated"
        - Deprecation warnings: "⚠️ Deprecated"
        - API version tracking

        Args:
            output: Agent output text

        Returns:
            Bonus score from 0.0 to 0.10
        """
        version_matches = sum(
            1 for pattern in self.VERSION_INFO_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        deprecation_matches = sum(
            1 for pattern in self.DEPRECATION_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        total_maintenance = version_matches + deprecation_matches

        if total_maintenance >= 3:
            return 0.10  # Comprehensive version tracking + deprecation
        if total_maintenance == 2:
            return 0.05  # Some version info
        return 0.0  # No version tracking

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        audience_targeting_score: float,
        technical_depth_score: float,
        context_adaptation_score: float,
        prerequisites_score: float,
        maintenance_bonus: float,
        output: str
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            audience_targeting_score: Audience targeting component score
            technical_depth_score: Technical depth component score
            context_adaptation_score: Context adaptation component score
            prerequisites_score: Prerequisites component score
            maintenance_bonus: Maintenance bonus score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Audience targeting issues
        if audience_targeting_score < 0.5:
            reasons.append(
                "No clear audience targeting (should state: 'Audience: Developers' or 'For end users')"
            )
        elif audience_targeting_score < 0.7:
            reasons.append(
                "Unclear audience or mixed signals (separate developer and user docs)"
            )

        # Technical depth issues
        if technical_depth_score < 0.5:
            reasons.append(
                "Technical depth mismatch (developer docs need architecture/code, user docs need steps/screenshots)"
            )
        elif technical_depth_score < 0.7:
            reasons.append(
                "Inconsistent technical depth (maintain consistent level throughout)"
            )

        # Context adaptation issues
        if context_adaptation_score < 0.5:
            reasons.append(
                "Context violation detected (avoid internal references like 'k8s-prod', '#oncall' in public docs)"
            )
        elif context_adaptation_score < 0.7:
            reasons.append(
                "Mixed internal/public context (clarify if doc is internal or public)"
            )

        # Prerequisites issues
        if prerequisites_score < 0.5:
            reasons.append(
                "Missing prerequisites (should state required knowledge: 'Prerequisites: Familiarity with REST APIs')"
            )
        elif prerequisites_score < 0.7:
            reasons.append(
                "Limited prerequisites (add links to prerequisite resources)"
            )

        # Maintenance feedback
        if maintenance_bonus < 0.05:
            reasons.append(
                "No version tracking (add: 'Version: 2.0', 'Last Updated: 2025-12-06', deprecation warnings)"
            )

        # Success message
        if not reasons:
            return "Perfect audience awareness - clear targeting, appropriate depth, proper context, prerequisites stated"

        return "; ".join(reasons)


def create_audience_awareness_metric(threshold: float = 0.80) -> AudienceAwarenessMetric:
    """
    Factory function to create audience awareness metric.

    Args:
        threshold: Minimum passing score (default: 0.80 for 80% compliance)

    Returns:
        Configured metric instance

    Example:
        metric = create_audience_awareness_metric(threshold=0.80)
        test_case = LLMTestCase(
            input="Document WebSocket API",
            actual_output="**Audience**: Senior Engineers\\n**Prerequisites**: RFC 6455..."
        )
        score = metric.measure(test_case)
    """
    return AudienceAwarenessMetric(threshold=threshold)
