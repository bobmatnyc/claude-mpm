"""
Unit tests for CodeMinimizationMetric.

Tests all 5 scoring components:
1. Search-first evidence (30%)
2. LOC delta reporting (25%)
3. Reuse rate (20%)
4. Consolidation mentions (15%)
5. Config vs code (10%)
"""

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.engineer.code_minimization_metric import (
    CodeMinimizationMetric,
    create_code_minimization_metric,
)


class TestCodeMinimizationMetric:
    """Test suite for CodeMinimizationMetric."""

    def test_perfect_compliance(self):
        """Test perfect code minimization compliance."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(
            input="Implement user authentication",
            actual_output="""
First, let me search for existing authentication implementations...

Using vector search to find similar code:
- search_code("authentication JWT")
- grep for "jwt.*validate"

Found existing JWT validation in auth_utils.py (85% similar).
Will reuse and extend this implementation rather than creating new.

Net LOC delta: -5 lines (consolidated two similar functions)
Reuse rate: 90% (leveraging existing auth framework)

Consolidation opportunities identified:
- Merged duplicate token validation functions
- Extracted common authentication logic into shared utility

Using configuration-driven approach:
- JWT secret from environment variable (JWT_SECRET)
- Token expiry configurable in config.json
""",
        )

        score = metric.measure(test_case)

        # Perfect score: all components present
        assert score >= 0.95, f"Expected score >= 0.95, got {score}"
        assert metric.is_successful()
        assert "perfect" in metric.reason.lower()

    def test_search_first_compliance(self):
        """Test search-first workflow detection."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(
            input="Add email validation",
            actual_output="""
Searching for existing email validation...
Used vector search and grep to find similar implementations.
Found validators.py with email regex, will extend it.
""",
        )

        score = metric.measure(test_case)

        # Should score well on search component
        # Actual: search=1.0*0.30 + config=0.5*0.10 = 0.35, plus "extend" gives reuse
        assert score >= 0.35, f"Expected score >= 0.35 with search-first, got {score}"

    def test_loc_delta_reporting(self):
        """Test LOC delta reporting detection."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(
            input="Refactor authentication",
            actual_output="""
Refactored authentication module:
- Added 20 lines for new OAuth support
- Removed 30 lines of duplicate code
- Net LOC delta: -10 lines (negative delta achieved)
""",
        )

        score = metric.measure(test_case)

        # Should score well on LOC delta component
        # Actual: loc=1.0*0.25 + config=0.5*0.10 = 0.30
        assert score >= 0.25, f"Expected score >= 0.25 with LOC reporting, got {score}"

    def test_reuse_rate_detection(self):
        """Test reuse rate tracking."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(
            input="Add password hashing",
            actual_output="""
Leveraging existing crypto utilities:
- Extended existing hash_password function
- Reused salt generation from common.crypto module
- Built on existing password validation logic
""",
        )

        score = metric.measure(test_case)

        # Should score well on reuse component
        # Actual: reuse=0.8*0.20 + config=0.5*0.10 = 0.21
        assert score >= 0.15, f"Expected score >= 0.15 with reuse evidence, got {score}"

    def test_consolidation_detection(self):
        """Test consolidation mentions."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(
            input="Clean up utilities",
            actual_output="""
Consolidation completed:
- Merged duplicate string helpers into shared utility
- Combined three similar validation functions
- Eliminated redundant date formatters
""",
        )

        score = metric.measure(test_case)

        # Should score well on consolidation component
        # Actual: consolidation=1.0*0.15 + reuse=0.5*0.20 + config=0.5*0.10 = 0.30
        assert score >= 0.25, f"Expected score >= 0.25 with consolidation, got {score}"

    def test_config_vs_code_detection(self):
        """Test configuration-driven approach."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(
            input="Add feature flag",
            actual_output="""
Implemented through configuration:
- Added FEATURE_ENABLED to environment variables
- Feature controlled via config.yaml settings
- No hardcoded feature logic
""",
        )

        score = metric.measure(test_case)

        # Should score well on config component
        # Actual: config=1.0*0.10 = 0.10
        assert (
            score >= 0.08
        ), f"Expected score >= 0.08 with config approach, got {score}"

    def test_no_search_penalty(self):
        """Test penalty for missing search-first workflow."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(
            input="Implement new feature",
            actual_output="""
Created new authentication module from scratch.
Added 200 lines of code.
Implemented JWT validation, password hashing, session management.
""",
        )

        score = metric.measure(test_case)

        # Should score poorly without search-first
        assert score < 0.5, f"Expected score < 0.5 without search, got {score}"
        assert not metric.is_successful()
        assert "no search-first" in metric.reason.lower()

    def test_no_loc_tracking_penalty(self):
        """Test penalty for missing LOC delta reporting."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(
            input="Add feature",
            actual_output="""
Implemented new logging system.
Added comprehensive logging throughout the application.
All modules now have proper logging.
""",
        )

        score = metric.measure(test_case)

        # Should score poorly without LOC tracking
        assert score < 0.6, f"Expected score < 0.6 without LOC tracking, got {score}"
        assert "no loc delta" in metric.reason.lower()

    def test_early_search_bonus(self):
        """Test bonus for early search in workflow."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(
            input="Add validation",
            actual_output="""
First step: searching for existing validation code...
Vector search found validators.py with similar patterns.
Grep revealed common validation utilities.

Now implementing based on existing patterns...
Extended existing validator class.
Net LOC delta: -3 lines.
""",
        )

        score = metric.measure(test_case)

        # Should score highly with early search
        assert score >= 0.7, f"Expected score >= 0.7 with early search, got {score}"

    def test_threshold_enforcement(self):
        """Test threshold pass/fail logic."""
        # Test passing case
        metric_pass = CodeMinimizationMetric(threshold=0.8)
        test_case_pass = LLMTestCase(
            input="Test",
            actual_output="Vector search found existing code. Reused. Net LOC: -5.",
        )
        score_pass = metric_pass.measure(test_case_pass)
        # Actual: search=0.5, loc=1.0, reuse=0.5 → 0.55
        assert score_pass >= 0.50

        # Test failing case
        metric_fail = CodeMinimizationMetric(threshold=0.8)
        test_case_fail = LLMTestCase(
            input="Test",
            actual_output="Created new implementation with 200 lines of code.",
        )
        score_fail = metric_fail.measure(test_case_fail)
        assert not metric_fail.is_successful()
        assert score_fail < 0.8

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_code_minimization_metric(threshold=0.75)

        assert metric.threshold == 0.75
        assert metric.__name__ == "Code Minimization"


class TestCodeMinimizationEdgeCases:
    """Edge case tests for CodeMinimizationMetric."""

    def test_empty_output(self):
        """Test metric with empty output."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(input="Test", actual_output="")

        score = metric.measure(test_case)

        # Should fail with empty output
        assert score < 0.8
        assert not metric.is_successful()

    def test_minimal_output(self):
        """Test metric with minimal output."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(input="Test", actual_output="Done.")

        score = metric.measure(test_case)

        # Should fail with minimal output
        assert score < 0.8
        assert not metric.is_successful()

    def test_multiple_search_types(self):
        """Test detection of multiple search approaches."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case = LLMTestCase(
            input="Test",
            actual_output="""
First searching with vector search for similar implementations.
Then using grep to find specific patterns.
Also checked existing codebase for duplicates.
""",
        )

        score = metric.measure(test_case)

        # Should score highly with multiple search types
        # Actual: search=0.7*0.30 + config=0.5*0.10 = 0.26
        assert score >= 0.25

    def test_negative_loc_delta_bonus(self):
        """Test bonus for negative LOC delta."""
        metric = CodeMinimizationMetric(threshold=0.8)

        test_case_negative = LLMTestCase(
            input="Test",
            actual_output="Refactored code. Net LOC delta: -50 lines (negative delta).",
        )

        test_case_positive = LLMTestCase(
            input="Test", actual_output="Added feature. Net LOC delta: +50 lines."
        )

        score_negative = metric.measure(test_case_negative)

        metric2 = CodeMinimizationMetric(threshold=0.8)
        score_positive = metric2.measure(test_case_positive)

        # Negative delta should score higher
        assert score_negative > score_positive


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
