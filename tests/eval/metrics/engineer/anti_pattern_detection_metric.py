"""
Anti-Pattern Detection Metric for Engineer Agent Testing.

This metric evaluates Engineer Agent compliance with anti-pattern avoidance:
- No mock data in production code (mock/dummy/placeholder only in tests)
- No silent fallbacks (explicit error handling, no silent failures)
- Explicit error propagation (errors logged and raised)
- Acceptable fallback justification (config defaults, graceful degradation)

Scoring Algorithm (weighted):
1. No Mock Data in Production (40%): Ensures no mock/dummy data in production code
2. No Silent Fallbacks (30%): Ensures explicit error handling, no silent failures
3. Explicit Error Propagation (20%): Validates errors are logged and raised
4. Acceptable Fallback Justification (10%): When fallbacks exist, are they justified?

Threshold: 0.9 (90% compliance required - strict anti-pattern enforcement)

Example:
    metric = AntiPatternDetectionMetric(threshold=0.9)
    test_case = LLMTestCase(
        input="Implement API client",
        actual_output='''def fetch_data(url):
            try:
                response = requests.get(url)
                return response.json()
            except RequestException as e:
                logger.error(f"API call failed: {e}")
                raise APIError("Failed to fetch data") from e'''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class AntiPatternDetectionMetric(BaseMetric):
    """
    DeepEval metric for Engineer Agent anti-pattern detection compliance.

    Evaluates:
    1. No mock data in production code (mock/dummy only in test files)
    2. No silent fallbacks (explicit errors, no silent failures)
    3. Explicit error propagation (log + raise, not swallow)
    4. Acceptable fallback justification (config defaults, documented)

    Scoring:
    - 1.0: Perfect compliance (no anti-patterns, proper error handling)
    - 0.9-0.99: Minor issues (one small anti-pattern)
    - 0.7-0.89: Moderate issues (some anti-patterns present)
    - 0.0-0.69: Major violations (mock data in production, silent failures)
    """

    # Mock data anti-patterns (NEGATIVE - flag if found in production)
    MOCK_DATA_PATTERNS: List[str] = [
        r'\bmock_\w+\s*=',
        r'\bdummy_\w+\s*=',
        r'\bplaceholder_\w+\s*=',
        r'\bfake_\w+\s*=',
        r'return\s+\{.*["\']mock["\']',
        r'return\s+\{.*["\']dummy["\']',
        r'return\s+\{.*["\']placeholder["\']',
        r'return.*"mock_\w+"',
        r'return.*"dummy_\w+"',
        r'api_key.*=.*["\']mock',
        r'token.*=.*["\']fake',
        r'password.*=.*["\']test'
    ]

    # Production code indicators
    PRODUCTION_CODE_PATTERNS: List[str] = [
        r'def\s+\w+\s*\(',  # Function definition
        r'class\s+\w+',  # Class definition
        r'async\s+def',  # Async function
        r'import\s+',  # Import statements
        r'from\s+.*import'
    ]

    # Test file indicators (mock data OK in tests)
    TEST_FILE_PATTERNS: List[str] = [
        r'test_\w+\.py',
        r'conftest\.py',
        r'@pytest',
        r'@mock',
        r'unittest\.TestCase',
        r'describe\s*\(',
        r'it\s*\(',
        r'def\s+test_'
    ]

    # Silent fallback anti-patterns
    SILENT_FALLBACK_PATTERNS: List[str] = [
        r'except.*:\s*pass',
        r'except.*:\s*return\s+None',
        r'except.*:\s*return\s+\{\}',
        r'except.*:\s*return\s+\[\]',
        r'except.*:\s*return\s+""',
        r'except.*:\s*return\s+False',
        r'if\s+.*error.*:\s*return\s+None',
        r'if\s+.*fail.*:\s*return\s+None',
        r'try.*except.*pass(?!\s*#)',  # Allow pass with comment
        r'except.*:\s*continue'
    ]

    # Explicit error propagation patterns (POSITIVE)
    ERROR_PROPAGATION_PATTERNS: List[str] = [
        r'raise\s+\w+Error',
        r'raise\s+.*from\s+',
        r'logger\.error\(',
        r'logger\.exception\(',
        r'log\.error\(',
        r'logging\.error\(',
        r'raise\s+(?!.*#\s*type:)',  # Generic raise (not type comment)
        r'throw\s+new\s+Error',  # JavaScript
        r'throw\s+\w+Error'  # JavaScript
    ]

    # Acceptable fallback patterns (POSITIVE - justified fallbacks)
    ACCEPTABLE_FALLBACK_PATTERNS: List[str] = [
        r'(?:config|default).*=.*getenv\(.*,\s*["\']?\w+',  # Config with default
        r'default\s*=',
        r'graceful\s+degradation',
        r'documented\s+fallback',
        r'documented\s+default',
        r'feature\s+flag',
        r'A/B\s+test',
        r'fallback.*(?:logged|documented|explicit)',
        r'(?:if|when)\s+.*unavailable.*(?:use|return)\s+default'
    ]

    # Logging patterns (required for fallbacks)
    LOGGING_PATTERNS: List[str] = [
        r'logger\.\w+\(',
        r'logging\.\w+\(',
        r'log\.\w+\(',
        r'console\.(?:log|warn|error)\(',
        r'print\(.*(?:error|warning|fail)'
    ]

    def __init__(self, threshold: float = 0.9):
        """
        Initialize AntiPatternDetectionMetric.

        Args:
            threshold: Minimum score to pass (default: 0.9 for 90% compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Anti-Pattern Detection"

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
        Measure anti-pattern detection compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output

        # Calculate component scores
        mock_data_score = self._score_no_mock_data_in_production(output)
        silent_fallback_score = self._score_no_silent_fallbacks(output)
        error_propagation_score = self._score_explicit_error_propagation(output)
        fallback_justification_score = self._score_acceptable_fallback_justification(output)

        # Weighted average
        final_score = (
            mock_data_score * 0.40 +
            silent_fallback_score * 0.30 +
            error_propagation_score * 0.20 +
            fallback_justification_score * 0.10
        )

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            mock_data_score,
            silent_fallback_score,
            error_propagation_score,
            fallback_justification_score,
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

    def _score_no_mock_data_in_production(self, output: str) -> float:
        """
        Score no mock data in production compliance (40% weight).

        Checks:
        - Detects mock/dummy/placeholder data patterns
        - Determines if code is production or test code
        - Penalizes mock data in production, allows in tests

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check if this is test code
        is_test_code = any(
            re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            for pattern in self.TEST_FILE_PATTERNS
        )

        # Check for mock data patterns
        mock_data_matches = [
            pattern for pattern in self.MOCK_DATA_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        ]

        # Check if production code is present
        is_production_code = any(
            re.search(pattern, output, re.MULTILINE)
            for pattern in self.PRODUCTION_CODE_PATTERNS
        )

        # Scoring logic
        if not mock_data_matches:
            # Perfect: no mock data found
            return 1.0
        elif is_test_code:
            # Perfect: mock data in test code is acceptable
            return 1.0
        elif is_production_code and mock_data_matches:
            # Severe penalty: mock data in production code
            return 0.0
        else:
            # Neutral: can't determine context
            return 0.7

    def _score_no_silent_fallbacks(self, output: str) -> float:
        """
        Score no silent fallbacks compliance (30% weight).

        Checks:
        - Detects silent failure patterns (except: pass, return None)
        - Ensures errors are not swallowed silently
        - Requires explicit error handling

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for silent fallback patterns
        silent_fallback_matches = [
            pattern for pattern in self.SILENT_FALLBACK_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        ]

        # Check for logging (mitigates silent fallbacks)
        has_logging = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.LOGGING_PATTERNS
        )

        # Scoring logic
        if not silent_fallback_matches:
            # Perfect: no silent fallbacks detected
            return 1.0
        elif has_logging and len(silent_fallback_matches) <= 1:
            # Acceptable: fallback with logging (documented degradation)
            return 0.7
        elif len(silent_fallback_matches) >= 3:
            # Severe penalty: multiple silent fallbacks
            return 0.0
        else:
            # Moderate penalty: some silent fallbacks
            return 0.4

    def _score_explicit_error_propagation(self, output: str) -> float:
        """
        Score explicit error propagation compliance (20% weight).

        Checks:
        - Detects raise statements, error logging
        - Ensures errors are propagated (raise/throw)
        - Validates logging before raising

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for error propagation patterns
        error_propagation_matches = [
            pattern for pattern in self.ERROR_PROPAGATION_PATTERNS
            if re.search(pattern, output, re.MULTILINE)
        ]

        # Check for logging
        has_logging = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.LOGGING_PATTERNS
        )

        # Scoring logic
        if len(error_propagation_matches) >= 2 and has_logging:
            # Perfect: multiple error propagations with logging
            return 1.0
        elif error_propagation_matches:
            # Good: error propagation present
            return 0.8
        elif has_logging:
            # Acceptable: logging present even if no raise
            return 0.6
        else:
            # Neutral: no error handling detected (may not be applicable)
            return 0.7

    def _score_acceptable_fallback_justification(self, output: str) -> float:
        """
        Score acceptable fallback justification (10% weight).

        Checks:
        - When fallbacks exist, are they justified?
        - Config defaults, documented fallbacks, graceful degradation
        - Feature flags, A/B tests with explicit documentation

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for acceptable fallback patterns
        acceptable_fallback_matches = [
            pattern for pattern in self.ACCEPTABLE_FALLBACK_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        # Check if fallbacks are present at all
        has_fallbacks = bool(
            re.search(r'fallback|default|degradation', output, re.IGNORECASE)
        )

        # Scoring logic
        if not has_fallbacks:
            # Neutral: no fallbacks needed
            return 0.8
        elif acceptable_fallback_matches:
            # Perfect: justified fallbacks
            return 1.0
        else:
            # Penalty: fallbacks without justification
            return 0.3

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        mock_data_score: float,
        silent_fallback_score: float,
        error_propagation_score: float,
        fallback_justification_score: float,
        output: str
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            mock_data_score: Mock data compliance score
            silent_fallback_score: Silent fallback compliance score
            error_propagation_score: Error propagation score
            fallback_justification_score: Fallback justification score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Mock data issues
        if mock_data_score < 0.5:
            mock_matches = [
                pattern for pattern in self.MOCK_DATA_PATTERNS
                if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            ]
            if mock_matches:
                reasons.append(
                    f"Mock data detected in production code (found {len(mock_matches)} instances)"
                )

        # Silent fallback issues
        if silent_fallback_score < 0.5:
            silent_matches = [
                pattern for pattern in self.SILENT_FALLBACK_PATTERNS
                if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            ]
            if silent_matches:
                reasons.append(
                    f"Silent fallback patterns detected ({len(silent_matches)} instances - should log errors explicitly)"
                )

        # Error propagation issues
        if error_propagation_score < 0.5:
            reasons.append(
                "Insufficient error propagation (should raise exceptions and log errors)"
            )

        # Fallback justification issues
        if fallback_justification_score < 0.5:
            reasons.append(
                "Fallbacks present without justification (should document config defaults or graceful degradation)"
            )

        # Success message
        if not reasons:
            return "Perfect anti-pattern compliance - no mock data, explicit error handling, justified fallbacks"

        return "; ".join(reasons)


def create_anti_pattern_detection_metric(threshold: float = 0.9) -> AntiPatternDetectionMetric:
    """
    Factory function to create anti-pattern detection metric.

    Args:
        threshold: Minimum passing score (default: 0.9 for 90% compliance)

    Returns:
        Configured metric instance

    Example:
        metric = create_anti_pattern_detection_metric(threshold=0.9)
        test_case = LLMTestCase(
            input="Implement API client",
            actual_output='''try:
                response = api.get(url)
            except APIError as e:
                logger.error(f"API failed: {e}")
                raise'''
        )
        score = metric.measure(test_case)
    """
    return AntiPatternDetectionMetric(threshold=threshold)
