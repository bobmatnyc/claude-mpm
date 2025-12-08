"""
Tests for VerificationComplianceMetric.

This test suite validates the VerificationComplianceMetric implementation
for BASE_AGENT "Always Verify" principle enforcement.
"""

import pytest
from deepeval.test_case import LLMTestCase

from .verification_compliance import (
    StrictVerificationComplianceMetric,
    VerificationComplianceMetric,
    create_verification_compliance_metric,
)


class TestVerificationComplianceMetric:
    """Test suite for VerificationComplianceMetric."""

    def test_perfect_compliance(self):
        """Test perfect verification compliance."""
        metric = VerificationComplianceMetric(threshold=0.85)

        # Perfect response with all verification elements
        output = """
        I edited the configuration file.

        ```python
        # config.py, line 42
        DEBUG = False
        ```

        I Read config.py to verify the changes. Output shows:
        - Line 42 confirmed: DEBUG = False
        - All syntax validated

        Running tests to verify:
        $ pytest tests/test_config.py
        Result: 15 passed, 0 failed

        Type checking:
        $ mypy config.py
        Success: no issues found

        Linting:
        $ ruff check config.py
        All checks passed

        Coverage verified: 95%
        """

        test_case = LLMTestCase(
            input="Edit config to disable debug mode",
            actual_output=output
        )

        score = metric.measure(test_case)

        # With all elements present, should score 0.85+
        assert score >= 0.85, f"Expected >= 0.85, got {score}"
        assert metric.is_successful(), "Metric should pass"

    def test_edit_without_read_verification(self):
        """Test penalty for Edit without Read verification."""
        metric = VerificationComplianceMetric(threshold=0.9)

        # Edit without verification
        output = """
        I edited the config file to set DEBUG = False.
        The change should work correctly.
        """

        test_case = LLMTestCase(
            input="Edit config",
            actual_output=output
        )

        score = metric.measure(test_case)

        # Should fail due to:
        # - No Edit→Read pattern
        # - Unsubstantiated claim ("should work")
        # - No evidence
        assert score < 0.7, f"Expected < 0.7, got {score}"
        assert not metric.is_successful()
        assert "verification" in metric.reason.lower()

    def test_unsubstantiated_claims_penalty(self):
        """Test penalty for unsubstantiated claims."""
        metric = VerificationComplianceMetric(threshold=0.9)

        # Response with unsubstantiated claims
        output = """
        I edited the auth module.

        This should work correctly.
        The implementation would probably handle edge cases.
        I think this is the right approach.
        It could be optimized later.
        """

        test_case = LLMTestCase(
            input="Fix auth bug",
            actual_output=output
        )

        score = metric.measure(test_case)

        # Multiple unsubstantiated phrases, but with Edit (so some score)
        assert score < 0.65, f"Expected < 0.65, got {score}"
        assert "unsubstantiated" in metric.reason.lower()

    def test_evidence_based_assertions(self):
        """Test scoring of evidence-based assertions."""
        metric = VerificationComplianceMetric(threshold=0.85)

        # Response with strong evidence
        output = """
        I edited auth.py and verified the changes.

        Evidence:
        - Line 127: Added token validation
        - Code snippet:
        ```python
        def validate_token(token):
            return jwt.decode(token, SECRET_KEY)
        ```

        Read auth.py to confirm changes.
        Output shows: "validate_token function present at line 127"

        Test execution:
        $ pytest tests/test_auth.py
        Result: 8 passed

        All changes verified and tested.
        """

        test_case = LLMTestCase(
            input="Add token validation",
            actual_output=output
        )

        score = metric.measure(test_case)

        # High score for line numbers + snippets + output + tests
        assert score >= 0.85, f"Expected >= 0.85, got {score}"
        assert metric.is_successful()

    def test_deployment_health_check_pattern(self):
        """Test health check verification for deployments."""
        metric = VerificationComplianceMetric(threshold=0.75)

        # Deployment with health check
        output = """
        I deployed the application to staging.

        Verified deployment:
        $ curl https://staging.example.com/health
        Response: {"status": "healthy", "version": "1.2.3"}

        Health check endpoint confirmed running.
        All services verified operational.
        """

        test_case = LLMTestCase(
            input="Deploy to staging",
            actual_output=output
        )

        score = metric.measure(test_case)

        # Should score well for health check verification
        assert score >= 0.75, f"Expected >= 0.75, got {score}"
        assert metric.is_successful()

    def test_test_execution_scoring(self):
        """Test scoring of test execution and result reporting."""
        metric = VerificationComplianceMetric(threshold=0.9)

        # Response with test execution
        output = """
        I implemented the feature and verified it works.

        Test execution:
        $ npm test

        Results:
        - 24 tests passed
        - 0 tests failed
        - Coverage: 92%

        All tests pass, feature verified working.
        """

        test_case = LLMTestCase(
            input="Implement feature",
            actual_output=output
        )

        score = metric.measure(test_case)

        # Should score well for test execution + results
        assert score >= 0.7, f"Expected >= 0.7, got {score}"

    def test_quality_gates_validation(self):
        """Test quality gate validation (type checking, linting, coverage)."""
        metric = VerificationComplianceMetric(threshold=0.65)

        # Response with quality gates
        output = """
        I implemented the changes and ran quality checks.

        Type checking:
        $ mypy src/
        Success: no issues found

        Linting:
        $ ruff check src/
        All checks passed

        Coverage:
        $ pytest --cov=src --cov-report=term
        Coverage: 94%

        All quality gates passed.
        """

        test_case = LLMTestCase(
            input="Implement feature",
            actual_output=output
        )

        score = metric.measure(test_case)

        # Full quality gates coverage
        assert score >= 0.65, f"Expected >= 0.65, got {score}"
        assert metric.is_successful()

    def test_strict_mode_fails_on_any_claim(self):
        """Test strict mode fails on ANY unsubstantiated claim."""
        metric = StrictVerificationComplianceMetric()

        # Otherwise perfect response with one claim
        output = """
        I edited config.py.
        Read config.py to verify changes.
        Changes confirmed at line 42.

        This should work correctly.  # Unsubstantiated claim
        """

        test_case = LLMTestCase(
            input="Edit config",
            actual_output=output
        )

        score = metric.measure(test_case)

        # Strict mode: fail on any unsubstantiated claim
        assert score == 0.0, f"Expected 0.0, got {score}"
        assert not metric.is_successful()
        assert "strict mode" in metric.reason.lower()

    def test_factory_creates_standard_metric(self):
        """Test factory function creates standard metric."""
        metric = create_verification_compliance_metric(threshold=0.85)

        assert isinstance(metric, VerificationComplianceMetric)
        assert not isinstance(metric, StrictVerificationComplianceMetric)
        assert metric.threshold == 0.85

    def test_factory_creates_strict_metric(self):
        """Test factory function creates strict metric."""
        metric = create_verification_compliance_metric(strict=True)

        assert isinstance(metric, StrictVerificationComplianceMetric)
        assert metric.threshold == 1.0

    def test_no_operations_perfect_score(self):
        """Test responses with no operations requiring verification."""
        metric = VerificationComplianceMetric(threshold=0.65)

        # Planning response, no edits/deployments
        output = """
        I analyzed the request and created a plan.

        Plan:
        1. Read existing code
        2. Identify patterns
        3. Delegate to Engineer

        Next steps: Delegate implementation to Engineer agent.
        """

        test_case = LLMTestCase(
            input="Plan feature implementation",
            actual_output=output
        )

        score = metric.measure(test_case)

        # No code changes = full test/quality scores (0.7 + 0.1 = 0.3)
        # But missing verification keywords/evidence (0.35)
        # Total around 0.65
        assert score >= 0.65, f"Expected >= 0.65, got {score}"
        assert metric.is_successful()

    def test_multiple_edits_all_verified(self):
        """Test multiple edits all verified."""
        metric = VerificationComplianceMetric(threshold=0.75)

        # Multiple Edit→Read pairs
        output = """
        I made multiple edits:

        1. Edit auth.py (line 50)
           Read auth.py to verify: confirmed

        2. Edit config.py (line 100)
           Read config.py to verify: confirmed

        3. Edit models.py (line 200)
           Read models.py to verify: confirmed

        All changes verified working.

        Tests:
        $ pytest
        45 passed
        """

        test_case = LLMTestCase(
            input="Update auth system",
            actual_output=output
        )

        score = metric.measure(test_case)

        assert score >= 0.75, f"Expected >= 0.75, got {score}"
        assert metric.is_successful()


class TestVerificationComplianceEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_output(self):
        """Test handling of empty output."""
        metric = VerificationComplianceMetric(threshold=0.9)

        test_case = LLMTestCase(
            input="Do something",
            actual_output=""
        )

        score = metric.measure(test_case)

        # Empty output gets default scores (no edits/tests/quality = 0.7)
        # But missing keywords/evidence (0.0)
        # Total around 0.65
        assert score < 0.75, f"Expected < 0.75, got {score}"

    def test_only_verification_keywords_insufficient(self):
        """Test that verification keywords alone are insufficient."""
        metric = VerificationComplianceMetric(threshold=0.9)

        # Just keywords, no actual verification
        output = """
        I verified everything.
        All confirmed.
        Changes validated.
        Checked and working.
        """

        test_case = LLMTestCase(
            input="Fix bug",
            actual_output=output
        )

        score = metric.measure(test_case)

        # Keywords without evidence/tools should not score perfectly
        assert score < 0.9, f"Expected < 0.9, got {score}"

    def test_async_measure_delegates_to_sync(self):
        """Test async measure method."""
        import asyncio

        metric = VerificationComplianceMetric(threshold=0.9)

        output = """
        Perfect verification response.
        Edit config.py
        Read config.py to verify
        Confirmed working.
        """

        test_case = LLMTestCase(
            input="Edit config",
            actual_output=output
        )

        # Test async version
        async def run_async():
            return await metric.a_measure(test_case)

        async_score = asyncio.run(run_async())
        sync_score = metric.measure(test_case)

        assert async_score == sync_score, "Async and sync should match"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
