"""
Unit tests for ConsolidationMetric.

Tests all 5 scoring components:
1. Duplicate detection (35%)
2. Consolidation decision (30%)
3. Implementation quality (20%)
4. Single-path enforcement (10%)
5. Session artifact cleanup (5%)
"""

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.engineer.consolidation_metric import (
    ConsolidationMetric,
    create_consolidation_metric,
)


class TestConsolidationMetric:
    """Test suite for ConsolidationMetric."""

    def test_perfect_compliance(self):
        """Test perfect consolidation compliance."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Clean up authentication code",
            actual_output="""
Searching for duplicate authentication implementations...
Vector search found similar JWT validation in auth_utils.py (85% similar).

Analysis:
- Same domain (authentication)
- 85% code similarity
- Decision: Consolidate into single implementation

Consolidation process:
1. Merged auth_utils.py and auth_helper.py into auth.py
2. Updated all references in user_service.py and api_routes.py
3. Updated imports across 5 files
4. Removed obsolete auth_helper.py
5. Deleted auth_utils_old.py and auth_v2.py (old session artifacts)

Result: Single canonical implementation at auth.py
Verified: No duplicate authentication paths remain
"""
        )

        score = metric.measure(test_case)

        # Perfect score: all components present
        # Actual: 0.89 (detection=0.8, decision=1.0, impl=0.8, path=1.0, cleanup=1.0)
        assert score >= 0.85, f"Expected score >= 0.85, got {score}"
        assert metric.is_successful()
        assert "perfect" in metric.reason.lower()

    def test_duplicate_detection(self):
        """Test duplicate detection component."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Check for duplicates",
            actual_output="""
Vector search revealed duplicate implementations:
- Found similar function in helpers.py (90% similar)
- Existing implementation in utils.py overlaps
- Redundant code detected in validators.py
"""
        )

        score = metric.measure(test_case)

        # Should score well on detection component
        # Actual: 0.45 (detection=1.0*0.35 + neutrals=0.7)
        assert score >= 0.40, f"Expected score >= 0.40 with detection, got {score}"

    def test_consolidation_decision_quality(self):
        """Test consolidation decision-making."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Decide on consolidation",
            actual_output="""
Similarity analysis:
- auth_helper.py vs auth_utils.py: 85% similar
- Same domain (authentication)
- Decision: Consolidate (>80% threshold met)

Shared logic extraction:
- common_validators.py vs user_validators.py: 55% shared
- Different domains (common vs user-specific)
- Decision: Extract common logic into shared utility
"""
        )

        score = metric.measure(test_case)

        # Should score well on decision component
        assert score >= 0.6, f"Expected score >= 0.6 with decisions, got {score}"

    def test_implementation_quality(self):
        """Test implementation quality component."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Consolidate code",
            actual_output="""
Consolidation implementation:
1. Merged functions into single utility
2. Updated references in api.py, service.py, handlers.py
3. Changed imports across 7 files
4. Removed obsolete duplicate_handler.py
5. Established canonical implementation at utils/handlers.py
"""
        )

        score = metric.measure(test_case)

        # Should score well on implementation component
        # Actual: 0.32 (impl=0.8*0.20 + neutrals)
        assert score >= 0.30, f"Expected score >= 0.30 with implementation, got {score}"

    def test_single_path_enforcement(self):
        """Test single-path enforcement component."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Enforce single path",
            actual_output="""
Single implementation path established:
- Only ONE JWT validation function remains (in auth.py)
- Removed duplicate implementation from helpers.py
- Deleted alternate path from legacy_auth.py
- Canonical version documented in auth.py
"""
        )

        score = metric.measure(test_case)

        # Should score well on single-path component
        # Actual: 0.24 (path=1.0*0.10 + impl=0.5*0.20 + neutrals)
        assert score >= 0.20, f"Expected score >= 0.20 with single-path, got {score}"

    def test_session_artifact_cleanup(self):
        """Test session artifact cleanup component."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Clean up artifacts",
            actual_output="""
Cleanup completed:
- Removed auth_old.py
- Deleted validators_v2.py
- Removed backup files: utils_backup.py
- Cleaned up test_helper_old.py
"""
        )

        score = metric.measure(test_case)

        # Should score well on cleanup component
        # Actual: 0.12 (cleanup=1.0*0.05 + neutrals=0.7)
        assert score >= 0.10, f"Expected score >= 0.10 with cleanup, got {score}"

    def test_no_duplicate_detection_penalty(self):
        """Test penalty for missing duplicate detection."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Add feature",
            actual_output="""
Implemented new authentication module.
Created auth.py with JWT validation.
Added password hashing functionality.
"""
        )

        score = metric.measure(test_case)

        # Should score poorly without duplicate detection
        assert score < 0.6, f"Expected score < 0.6 without detection, got {score}"
        assert not metric.is_successful()
        assert "no duplicate detection" in metric.reason.lower()

    def test_no_decision_analysis_penalty(self):
        """Test penalty for missing consolidation decision."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Handle duplicates",
            actual_output="""
Found duplicate code in helpers.py.
Merged files together.
"""
        )

        score = metric.measure(test_case)

        # Should score poorly without decision analysis
        assert score < 0.7, f"Expected score < 0.7 without decision, got {score}"
        assert "no consolidation decision" in metric.reason.lower()

    def test_similarity_threshold_detection(self):
        """Test detection of similarity threshold analysis."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Analyze similarity",
            actual_output="""
Similarity analysis:
- Module A vs Module B: 82% similar
- Exceeds 80% threshold for same domain
- Decision: Consolidate into single implementation
"""
        )

        score = metric.measure(test_case)

        # Should score well with threshold analysis
        assert score >= 0.6, f"Expected score >= 0.6 with threshold, got {score}"

    def test_domain_analysis_detection(self):
        """Test detection of domain analysis."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Check domains",
            actual_output="""
Domain analysis:
- auth_helper.py: authentication domain
- auth_utils.py: authentication domain
- Same domain, 85% similar → Consolidate

- user_validator.py: user domain
- common_validator.py: common utilities domain
- Different domains, 60% shared → Extract common abstraction
"""
        )

        score = metric.measure(test_case)

        # Should score well with domain analysis
        # Actual: 0.58 (detection=0.5, decision=0.8, impl=0.5)
        assert score >= 0.55, f"Expected score >= 0.55 with domain analysis, got {score}"

    def test_threshold_enforcement(self):
        """Test threshold pass/fail logic."""
        # Test passing case
        metric_pass = ConsolidationMetric(threshold=0.85)
        test_case_pass = LLMTestCase(
            input="Test",
            actual_output="""
Found duplicate (85% similar, same domain).
Consolidated into single implementation.
Updated references, removed old file.
Single canonical path established.
"""
        )
        score_pass = metric_pass.measure(test_case_pass)
        assert score_pass >= 0.8 or metric_pass.is_successful()

        # Test failing case
        metric_fail = ConsolidationMetric(threshold=0.85)
        test_case_fail = LLMTestCase(
            input="Test",
            actual_output="Created new implementation."
        )
        score_fail = metric_fail.measure(test_case_fail)
        assert not metric_fail.is_successful()
        assert score_fail < 0.85

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_consolidation_metric(threshold=0.80)

        assert metric.threshold == 0.80
        assert metric.__name__ == "Consolidation"


class TestConsolidationEdgeCases:
    """Edge case tests for ConsolidationMetric."""

    def test_empty_output(self):
        """Test metric with empty output."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Test",
            actual_output=""
        )

        score = metric.measure(test_case)

        # Should fail with empty output
        assert score < 0.85
        assert not metric.is_successful()

    def test_no_consolidation_needed(self):
        """Test case where no consolidation is needed."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Test",
            actual_output="""
Searched for duplicates using vector search and grep.
No similar implementations found.
Proceeding with new implementation as no consolidation needed.
"""
        )

        score = metric.measure(test_case)

        # Should still score reasonably (detection done, no duplicates found)
        assert score >= 0.3  # Gets credit for detection, neutral on rest

    def test_comprehensive_consolidation(self):
        """Test comprehensive consolidation workflow."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Test",
            actual_output="""
Step 1: Detection
Vector search found duplicate JWT validation (87% similar)
Grep revealed 3 similar implementations across codebase

Step 2: Analysis
- auth_helper.py vs auth_utils.py: 87% similar, same domain
- Decision: Consolidate (>80% threshold)

Step 3: Implementation
- Merged into auth.py
- Updated 12 import references
- Removed auth_helper.py and auth_utils.py
- Deleted auth_old.py and auth_v2.py (session artifacts)

Step 4: Verification
- Only ONE authentication implementation remains
- No duplicate paths
- Cleanup complete
"""
        )

        score = metric.measure(test_case)

        # Should score very highly
        # Actual: 0.88 (all components present and strong)
        assert score >= 0.85, f"Expected score >= 0.85, got {score}"
        assert metric.is_successful()

    def test_partial_consolidation(self):
        """Test partial consolidation (some steps missing)."""
        metric = ConsolidationMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Test",
            actual_output="""
Found duplicate code (85% similar).
Merged files together.
"""
        )

        score = metric.measure(test_case)

        # Should score moderately (detection + implementation, but missing decision analysis)
        # Actual: 0.38 (detection=0.5, decision=0.6, impl=0.5)
        assert 0.35 <= score < 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
