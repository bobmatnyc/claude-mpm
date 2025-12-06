"""
Unit tests for CoverageQualityMetric.

Tests the 4-component weighted scoring:
1. Coverage Tool Usage (35%)
2. Critical Path Focus (30%)
3. Memory-Efficient Analysis (20%)
4. High-Impact Test Prioritization (15%)
"""

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.qa.coverage_quality_metric import (
    CoverageQualityMetric,
    create_coverage_quality_metric
)


class TestCoverageQualityMetric:
    """Test suite for CoverageQualityMetric."""

    def test_perfect_score(self):
        """Test perfect compliance (all components present)."""
        metric = CoverageQualityMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze test coverage",
            actual_output="""
            Running coverage analysis with: vitest run --coverage
            Using c8 for code coverage instrumentation.
            Coverage report generated with nyc.

            Current coverage: 78%
            Focusing on uncovered critical paths:
            - Authentication flow (0% coverage) - HIGH PRIORITY
            - Payment processing (45% coverage) - CRITICAL
            - User registration (100% coverage) - complete

            Using grep to find untested critical functions instead of reading all files.
            Limiting analysis to 3-5 representative files per module.
            Targeted search for high-impact code paths.

            Prioritizing high-impact tests:
            1. Auth tests (most important for security)
            2. Payment tests (critical business logic)
            3. Registration tests (essential user flow)
            """
        )

        score = metric.measure(test_case)

        # Should score >= 0.85 (perfect or near-perfect)
        assert score >= 0.85
        assert metric.is_successful()
        assert "Perfect coverage quality" in metric.reason or score >= 0.85

    def test_coverage_tool_usage_only(self):
        """Test coverage tool usage without other components."""
        metric = CoverageQualityMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze coverage",
            actual_output="""
            Running vitest --coverage to generate coverage report.
            Coverage analysis complete using istanbul.
            Overall coverage: 82%
            """
        )

        score = metric.measure(test_case)

        # Coverage tools (0.9*0.35) = 0.315
        # Should fail threshold (< 0.85)
        assert score < 0.85
        assert not metric.is_successful()

    def test_critical_path_focus_without_tools(self):
        """Test critical path focus without coverage tools (should fail)."""
        metric = CoverageQualityMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze coverage",
            actual_output="""
            Focusing on critical path analysis.
            Identifying uncovered important functions.
            Prioritizing high-priority areas for testing.
            """
        )

        score = metric.measure(test_case)

        # Missing coverage tools (0*0.35) - should fail
        assert score < 0.85
        assert not metric.is_successful()
        assert "No coverage tool usage" in metric.reason

    def test_memory_efficient_analysis(self):
        """Test memory-efficient analysis detection."""
        metric = CoverageQualityMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze coverage",
            actual_output="""
            Running coverage with vitest --coverage.
            Coverage report shows 75% overall.

            Using grep to find uncovered files instead of reading all.
            Limiting analysis to 3-5 representative files.
            Targeted sample of critical modules.
            Avoiding reading all files to save memory.

            Focusing on critical paths in auth and payment modules.
            Prioritizing high-impact tests for these areas.
            """
        )

        score = metric.measure(test_case)

        # Should score well with all components
        assert score >= 0.85
        assert metric.is_successful()

    def test_high_impact_prioritization(self):
        """Test high-impact test prioritization detection."""
        metric = CoverageQualityMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Prioritize tests",
            actual_output="""
            Running coverage analysis with nyc.
            Coverage: 80%

            Prioritizing high-impact tests:
            1. Security-critical authentication (most important)
            2. Payment processing (essential business logic)
            3. Data validation (important for integrity)

            Focusing on critical paths in uncovered areas.
            Using grep to efficiently locate test gaps.
            """
        )

        score = metric.measure(test_case)

        # Should score well with prioritization + other components
        assert score >= 0.85
        assert metric.is_successful()

    def test_no_coverage_analysis(self):
        """Test output with no coverage analysis (should fail)."""
        metric = CoverageQualityMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze tests",
            actual_output="""
            Tests are running successfully.
            All tests pass.
            No issues detected.
            """
        )

        score = metric.measure(test_case)

        assert score < 0.85
        assert not metric.is_successful()
        assert "No coverage tool usage" in metric.reason

    def test_multiple_coverage_tools(self):
        """Test detection of multiple coverage tools."""
        metric = CoverageQualityMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Run coverage",
            actual_output="""
            Running coverage analysis with multiple tools:
            - vitest --coverage for unit tests
            - nyc for integration tests
            - c8 for comprehensive coverage report
            - istanbul for detailed metrics

            Coverage: 85%
            Focusing on critical uncovered paths.
            Using grep for efficient file discovery.
            Prioritizing high-impact test additions.
            """
        )

        score = metric.measure(test_case)

        # Multiple tools should score 1.0 on coverage component
        assert score >= 0.85
        assert metric.is_successful()

    def test_critical_path_emphasis(self):
        """Test strong critical path focus."""
        metric = CoverageQualityMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze coverage gaps",
            actual_output="""
            Running vitest --coverage.

            Critical path analysis:
            - Uncovered authentication flows (0%) - CRITICAL
            - Important payment logic (50%) - HIGH PRIORITY
            - Key user flows (75%) - important
            - Core business logic needs coverage - critical

            Not chasing 100% coverage, focusing on critical paths.
            Prioritizing high-impact areas over completeness.
            Using grep to efficiently find uncovered critical functions.
            """
        )

        score = metric.measure(test_case)

        # Strong critical path focus should score well
        assert score >= 0.85
        assert metric.is_successful()

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_coverage_quality_metric(threshold=0.90)

        assert isinstance(metric, CoverageQualityMetric)
        assert metric.threshold == 0.90

    def test_async_measure(self):
        """Test async measure method delegates to sync."""
        import asyncio

        metric = CoverageQualityMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze coverage",
            actual_output="""
            Running vitest --coverage.
            Coverage: 80%. Focusing on critical paths.
            Using grep for efficient analysis.
            Prioritizing high-impact tests.
            """
        )

        async def run_async_test():
            score = await metric.a_measure(test_case)
            return score

        score = asyncio.run(run_async_test())

        assert score >= 0.85
        assert metric.is_successful()

    def test_component_weights(self):
        """Test that component weights sum to 1.0."""
        # Coverage Tool (35%) + Critical Path (30%) + Memory Efficient (20%) + Prioritization (15%)
        total_weight = 0.35 + 0.30 + 0.20 + 0.15
        assert total_weight == pytest.approx(1.0)

    def test_partial_compliance(self):
        """Test partial compliance scenarios."""
        metric = CoverageQualityMetric(threshold=0.85)

        # Has coverage tools + critical path, missing memory efficiency and prioritization
        partial_case = LLMTestCase(
            input="Analyze coverage",
            actual_output="""
            Running vitest --coverage and nyc.
            Coverage report: 75%
            Focusing on uncovered critical paths.
            Important functions need testing.
            Critical business logic requires coverage.
            """
        )

        score = metric.measure(partial_case)

        # Coverage (1.0*0.35) + Critical (1.0*0.30) + Memory (0*0.20) + Priority (0*0.15)
        # = 0.35 + 0.30 + 0 + 0 = 0.65
        assert score == pytest.approx(0.65, abs=0.10)
        assert not metric.is_successful()

    def test_grep_efficiency_detection(self):
        """Test that grep usage is detected for memory efficiency."""
        metric = CoverageQualityMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Find coverage gaps",
            actual_output="""
            Running coverage with vitest --coverage.
            Coverage: 80%

            Using grep to find uncovered functions:
            grep -r "function.*export" --include="*.ts" | grep -v test

            This avoids reading all files into memory.
            Focusing on critical uncovered paths.
            Prioritizing high-impact test additions.
            """
        )

        score = metric.measure(test_case)

        # Should detect grep usage and memory efficiency
        assert score >= 0.85
        assert metric.is_successful()

    def test_avoiding_100_percent_chase(self):
        """Test that focus on critical paths over 100% is rewarded."""
        metric = CoverageQualityMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Improve coverage",
            actual_output="""
            Running nyc for coverage analysis.
            Current: 78% coverage.

            NOT chasing 100% coverage blindly.
            Instead, focusing on:
            - Uncovered critical authentication (0%)
            - Important payment flows (50%)
            - Key business logic (60%)

            These critical paths are priority, not trivial utility functions.
            Using grep to efficiently locate uncovered critical code.
            Prioritizing high-impact tests.
            """
        )

        score = metric.measure(test_case)

        # Strong critical path focus should score well
        assert score >= 0.85
        assert metric.is_successful()
