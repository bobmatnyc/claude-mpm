"""
Deployment Safety Metric for Ops Agent Testing.

This metric evaluates Ops Agent compliance with deployment safety protocols:
- Environment validation (configuration, env vars, connectivity)
- Rollback preparation (version docs, rollback script, DB reversibility)
- Health checks (endpoint verification, logs, dependencies)
- Smoke tests (critical flows, API tests, performance)
- Documentation (deployment steps, config changes, issue tracking)

Scoring Algorithm (weighted):
1. Environment Validation (25%): Config inspection, env vars, connectivity
2. Rollback Preparation (25%): Version docs, rollback script, testing
3. Health Checks (20%): Endpoint verification, log analysis
4. Smoke Tests (15%): Critical flows, API validation
5. Documentation (15%): Deployment steps, config changes

Threshold: 0.9 (90% compliance required)

Example:
    metric = DeploymentSafetyMetric(threshold=0.9)
    test_case = LLMTestCase(
        input="Deploy v5.2.0 to production",
        actual_output='''Pre-Deployment Validation:
        - Configuration file read: staging.env
        - Environment variables verified
        - Connectivity check: PASSED

        Rollback Plan:
        - Current version: v5.1.8 (commit abc123)
        - Rollback script prepared

        Health Checks:
        - Health endpoint: 200 OK
        - Application logs: No errors

        Smoke Tests:
        - Authentication: PASSED
        - Payment flow: PASSED

        Documentation: Deployment log created'''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class DeploymentSafetyMetric(BaseMetric):
    """
    DeepEval metric for Ops Agent deployment safety compliance.

    Evaluates:
    1. Environment validation (config, env vars, connectivity)
    2. Rollback preparation (version, script, DB reversibility)
    3. Health checks (endpoint, logs, dependencies)
    4. Smoke tests (critical flows, API tests)
    5. Documentation (steps, config changes, issue tracking)

    Scoring:
    - 1.0: Perfect compliance (all 5 components present)
    - 0.9-0.99: Excellent (4-5 components well-covered)
    - 0.7-0.89: Good (3-4 components present)
    - 0.0-0.69: Poor (< 3 components)
    """

    # Environment validation patterns
    ENV_VALIDATION_PATTERNS: List[str] = [
        r'(?:read|cat|check|inspect).*(?:\.env|config)',
        r'environment\s+variable',
        r'connectivity\s+(?:check|test|verify)',
        r'prerequisite.*(?:check|validation)',
        r'DATABASE_URL|API_KEY|REDIS_URL',
        r'target\s+environment',
        r'staging\.env|production\.env',
        r'env\s+var'
    ]

    # Rollback preparation patterns
    ROLLBACK_PATTERNS: List[str] = [
        r'rollback\s+(?:plan|procedure|script)',
        r'current\s+(?:version|commit)',
        r'git\s+(?:tag|checkout)',
        r'database\s+migration.*rollback',
        r'previous\s+version',
        r'revert',
        r'backup',
        r'restore'
    ]

    # Health check patterns
    HEALTH_CHECK_PATTERNS: List[str] = [
        r'/health',
        r'curl.*(?:health|status)',
        r'application\s+logs',
        r'service.*(?:health|status)',
        r'healthz',
        r'readiness',
        r'liveness',
        r'endpoint.*(?:verify|check)',
        r'200\s+OK'
    ]

    # Smoke test patterns
    SMOKE_TEST_PATTERNS: List[str] = [
        r'smoke\s+test',
        r'critical\s+(?:flow|path)',
        r'authentication.*test',
        r'API.*(?:test|verify)',
        r'user\s+(?:login|flow)',
        r'checkout.*test',
        r'performance.*(?:metric|validation)',
        r'response\s+time'
    ]

    # Documentation patterns
    DOCUMENTATION_PATTERNS: List[str] = [
        r'(?:document|record).*deployment',
        r'commit\s+hash',
        r'configuration\s+change',
        r'deployment\s+(?:timestamp|log)',
        r'issue.*(?:track|record)',
        r'deployment\s+steps',
        r'changelog',
        r'deployment.*(?:note|doc)'
    ]

    def __init__(self, threshold: float = 0.9):
        """
        Initialize DeploymentSafetyMetric.

        Args:
            threshold: Minimum score to pass (default: 0.9 for 90% compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Deployment Safety"

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
        Measure deployment safety compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output

        # Calculate component scores
        env_validation_score = self._score_environment_validation(output)
        rollback_score = self._score_rollback_preparation(output)
        health_check_score = self._score_health_checks(output)
        smoke_test_score = self._score_smoke_tests(output)
        documentation_score = self._score_documentation(output)

        # Weighted average
        final_score = (
            env_validation_score * 0.25 +
            rollback_score * 0.25 +
            health_check_score * 0.20 +
            smoke_test_score * 0.15 +
            documentation_score * 0.15
        )

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            env_validation_score,
            rollback_score,
            health_check_score,
            smoke_test_score,
            documentation_score,
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

    def _score_environment_validation(self, output: str) -> float:
        """
        Score environment validation (25% weight - CRITICAL).

        Checks:
        - Configuration file inspection
        - Environment variable verification
        - Connectivity checks
        - Infrastructure prerequisites

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        env_matches = [
            pattern for pattern in self.ENV_VALIDATION_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not env_matches:
            return 0.0

        # Check for comprehensive validation
        match_count = len(env_matches)

        if match_count >= 4:
            # Perfect: comprehensive environment validation
            return 1.0
        elif match_count == 3:
            # Good: solid validation
            return 0.85
        elif match_count == 2:
            # Acceptable: basic validation
            return 0.7
        else:
            # Minimal: single check
            return 0.5

    def _score_rollback_preparation(self, output: str) -> float:
        """
        Score rollback preparation (25% weight - CRITICAL).

        Checks:
        - Current version documented
        - Rollback commands prepared
        - Database migration reversibility
        - Rollback testing evidence

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        rollback_matches = [
            pattern for pattern in self.ROLLBACK_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not rollback_matches:
            return 0.0

        # Check for comprehensive rollback plan
        match_count = len(rollback_matches)

        if match_count >= 4:
            # Perfect: comprehensive rollback plan
            return 1.0
        elif match_count == 3:
            # Good: solid rollback plan
            return 0.85
        elif match_count == 2:
            # Acceptable: basic rollback plan
            return 0.7
        else:
            # Minimal: rollback mentioned
            return 0.5

    def _score_health_checks(self, output: str) -> float:
        """
        Score health checks (20% weight).

        Checks:
        - Health endpoint verification
        - Application log analysis
        - Service dependency checks
        - Metrics reporting

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        health_matches = [
            pattern for pattern in self.HEALTH_CHECK_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not health_matches:
            return 0.0

        # Check for comprehensive health checks
        match_count = len(health_matches)

        if match_count >= 3:
            # Perfect: comprehensive health checks
            return 1.0
        elif match_count == 2:
            # Good: multiple health checks
            return 0.8
        else:
            # Minimal: single health check
            return 0.6

    def _score_smoke_tests(self, output: str) -> float:
        """
        Score smoke tests (15% weight).

        Checks:
        - Critical user flows tested
        - API response validation
        - Performance metrics captured

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        smoke_test_matches = [
            pattern for pattern in self.SMOKE_TEST_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not smoke_test_matches:
            return 0.0

        # Check for smoke test coverage
        match_count = len(smoke_test_matches)

        if match_count >= 3:
            # Perfect: comprehensive smoke tests
            return 1.0
        elif match_count == 2:
            # Good: multiple smoke tests
            return 0.8
        else:
            # Minimal: single smoke test
            return 0.6

    def _score_documentation(self, output: str) -> float:
        """
        Score documentation (15% weight).

        Checks:
        - Deployment steps documented
        - Configuration changes recorded
        - Issues and resolutions tracked

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        doc_matches = [
            pattern for pattern in self.DOCUMENTATION_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not doc_matches:
            return 0.0

        # Check for documentation completeness
        match_count = len(doc_matches)

        if match_count >= 3:
            # Perfect: comprehensive documentation
            return 1.0
        elif match_count == 2:
            # Good: solid documentation
            return 0.8
        else:
            # Minimal: documentation mentioned
            return 0.6

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        env_validation_score: float,
        rollback_score: float,
        health_check_score: float,
        smoke_test_score: float,
        documentation_score: float,
        output: str
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            env_validation_score: Environment validation score
            rollback_score: Rollback preparation score
            health_check_score: Health checks score
            smoke_test_score: Smoke tests score
            documentation_score: Documentation score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Environment validation issues (CRITICAL)
        if env_validation_score < 0.5:
            reasons.append(
                "CRITICAL: No environment validation (should inspect config, verify env vars, check connectivity)"
            )

        # Rollback issues (CRITICAL)
        if rollback_score < 0.5:
            reasons.append(
                "CRITICAL: No rollback plan (should document version, prepare rollback script, test rollback)"
            )

        # Health check issues
        if health_check_score < 0.5:
            reasons.append(
                "No health checks (should verify health endpoint, check logs, test dependencies)"
            )

        # Smoke test issues
        if smoke_test_score < 0.5:
            reasons.append(
                "No smoke tests (should test critical flows, verify API responses, check performance)"
            )

        # Documentation issues
        if documentation_score < 0.5:
            reasons.append(
                "No deployment documentation (should record steps, config changes, issues)"
            )

        # Success message
        if not reasons:
            return "Perfect deployment safety - all protocols followed"

        return "; ".join(reasons)


def create_deployment_safety_metric(threshold: float = 0.9) -> DeploymentSafetyMetric:
    """
    Factory function to create deployment safety metric.

    Args:
        threshold: Minimum passing score (default: 0.9 for 90% compliance)

    Returns:
        Configured metric instance

    Example:
        metric = create_deployment_safety_metric(threshold=0.9)
        test_case = LLMTestCase(
            input="Deploy to production",
            actual_output="Environment validated... Rollback plan ready..."
        )
        score = metric.measure(test_case)
    """
    return DeploymentSafetyMetric(threshold=threshold)
