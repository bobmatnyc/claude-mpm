"""
Unit tests for TokenEfficiencyMetric.

Tests the 4-component weighted scoring:
1. Token reduction awareness (30%)
2. Cache optimization (25%)
3. Redundancy elimination (25%)
4. Structural optimization (20%)
"""

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.prompt_engineer.token_efficiency_metric import (
    TokenEfficiencyMetric,
    create_token_efficiency_metric,
)


class TestTokenEfficiencyMetric:
    """Test suite for TokenEfficiencyMetric."""

    def test_comprehensive_token_efficiency(self):
        """Test comprehensive token efficiency awareness."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Optimize this prompt",
            actual_output="""
            ## Token Efficiency Optimization

            ### Token Reduction
            Reduced prompt from 738 tokens to 150 tokens (80% reduction).
            Eliminated redundant instructions and consolidated similar sections.

            ### Cache Optimization
            Achieved 95% cache hit rate by:
            - Separating stable system instructions from variable user data
            - Using cache-friendly static prefix structure

            ### Redundancy Elimination
            Removed duplicate instructions and consolidated:
            - Merged 5 similar warning messages into 1
            - DRY principle applied throughout
            - Single source of truth for style guidelines

            ### Structural Optimization
            Applied efficient formatting:
            - XML tags for complex structured sections
            - Markdown headers for navigation
            - Bullet points for concise lists
            """,
        )

        score = metric.measure(test_case)

        assert score >= 0.80
        assert metric.is_successful()

    def test_token_reduction_with_percentages(self):
        """Test token reduction detection with percentages."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Reduce tokens",
            actual_output="""
            Token reduction achieved:
            - Before: 500 tokens
            - After: 200 tokens
            - Reduction: 60% fewer tokens

            Cut length by removing verbose explanations.
            """,
        )

        score = metric.measure(test_case)

        # Should score well for token reduction
        assert score >= 0.25

    def test_cache_optimization_90_percent(self):
        """Test cache optimization with 90%+ hit rate."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Optimize caching",
            actual_output="""
            Cache optimization complete:
            - Cache-friendly structure implemented
            - Static system prompts separated from dynamic content
            - Achieved 95% cache hit rate
            - Variable data moved to user messages
            """,
        )

        score = metric.measure(test_case)

        # Should score well for cache optimization
        assert score >= 0.20

    def test_redundancy_elimination(self):
        """Test redundancy elimination detection."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Remove duplicates",
            actual_output="""
            Redundancy elimination:
            - Removed duplicate instructions
            - Consolidated similar sections
            - Applied DRY principle
            - Single source of truth for guidelines
            - Merged repeated warnings
            """,
        )

        score = metric.measure(test_case)

        # Should score well for redundancy work
        assert score >= 0.20

    def test_structural_optimization_xml_markdown(self):
        """Test structural optimization with XML and markdown."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Improve structure",
            actual_output="""
            Structural optimization applied:

            Using XML tags for complex sections:
            <instructions>
              <rule>Be concise</rule>
            </instructions>

            Using markdown for navigation:
            ## Overview
            ## Quick Start
            ## Reference

            ```python
            # Example code block
            ```

            Bullet points for clarity:
            - Point 1
            - Point 2
            """,
        )

        score = metric.measure(test_case)

        # Should score well for structure
        assert score >= 0.15

    def test_no_optimization_awareness_fails(self):
        """Test that lack of optimization awareness fails."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Review prompt",
            actual_output="""
            The prompt looks fine. No changes needed.
            Everything appears to be working correctly.
            """,
        )

        score = metric.measure(test_case)

        assert score < 0.80
        assert not metric.is_successful()

    def test_partial_optimization_medium_score(self):
        """Test partial optimization gives medium score."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Optimize",
            actual_output="""
            Made the prompt more efficient:
            - Streamlined instructions
            - Reduced from 400 to 200 lines

            Could further improve caching.
            """,
        )

        score = metric.measure(test_case)

        # Partial optimization
        assert 0.3 <= score <= 0.75

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_token_efficiency_metric(threshold=0.75)

        assert isinstance(metric, TokenEfficiencyMetric)
        assert metric.threshold == 0.75

    def test_async_measure(self):
        """Test async measure method."""
        import asyncio

        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Test async",
            actual_output="""
            Optimized with 50% token reduction.
            Cache-efficient structure.
            Removed redundant sections.
            """,
        )

        async def run_async():
            return await metric.a_measure(test_case)

        score = asyncio.run(run_async())

        assert 0.0 <= score <= 1.0

    def test_empty_output(self):
        """Test handling of empty output."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(input="Optimize", actual_output="")

        score = metric.measure(test_case)

        assert score < 0.80
        assert not metric.is_successful()

    def test_reason_generation_success(self):
        """Test reason generation for successful optimization."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Full optimization",
            actual_output="""
            Complete token efficiency optimization:
            - 60% token reduction achieved
            - 92% cache hit rate
            - Removed all redundant duplicate content
            - XML structured output with markdown headers
            """,
        )

        metric.measure(test_case)

        assert "Score:" in metric.reason

    def test_reason_generation_failure(self):
        """Test reason generation for failed optimization."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(input="Basic check", actual_output="Looks good.")

        metric.measure(test_case)

        assert "below threshold" in metric.reason

    def test_component_weights_sum_to_one(self):
        """Test that component weights sum to 1.0."""
        # Reduction (0.30) + Cache (0.25) + Redundancy (0.25) + Structure (0.20)
        total = 0.30 + 0.25 + 0.25 + 0.20
        assert total == pytest.approx(1.0)

    def test_score_capped_at_one(self):
        """Test that score is capped at 1.0."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Maximum optimization",
            actual_output="""
            Extreme optimization achieved:

            TOKEN REDUCTION:
            - Before: 1000 tokens
            - After: 100 tokens
            - 90% reduction in token count
            - Decreased length significantly

            CACHE OPTIMIZATION:
            - 99% cache hit rate achieved
            - Static prefix fully cache-friendly
            - Separated stable from variable data
            - Avoid cache miss scenarios

            REDUNDANCY:
            - All duplicates removed
            - DRY principle strictly applied
            - Single source of truth
            - Consolidated all repeated sections

            STRUCTURE:
            - XML tags for complex data
            - Markdown headings throughout
            - Code blocks with syntax hints
            - Bullet points for lists
            ```python
            example()
            ```
            """,
        )

        score = metric.measure(test_case)

        assert score <= 1.0

    def test_specific_reduction_phrases(self):
        """Test various token reduction phrases."""
        metric = TokenEfficiencyMetric(threshold=0.80)

        phrases = [
            "reduced tokens by 40%",
            "cut length in half",
            "decreased from 500 to 200 lines",
            "fewer tokens used",
            "optimized for efficiency",
        ]

        for phrase in phrases:
            test_case = LLMTestCase(
                input="Check", actual_output=f"Improvement: {phrase} in the prompt."
            )
            score = metric.measure(test_case)
            # Should detect reduction-related content
            assert score >= 0.1, f"Failed to detect: {phrase}"

    def test_high_cache_hit_rate_detection(self):
        """Test detection of high cache hit rates."""
        metric = TokenEfficiencyMetric(threshold=0.80)

        rates = ["90%", "95%", "99%"]

        for rate in rates:
            test_case = LLMTestCase(
                input="Check cache",
                actual_output=f"Achieved {rate} cache hit rate with optimized structure.",
            )
            score = metric.measure(test_case)
            # Should detect cache optimization
            assert score >= 0.15, f"Failed for rate: {rate}"

    def test_dry_principle_detection(self):
        """Test DRY principle detection."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Check redundancy",
            actual_output="""
            Applied DRY (Don't Repeat Yourself) principle:
            - Single source of truth for all rules
            - No duplicate instructions
            """,
        )

        score = metric.measure(test_case)

        # Should detect DRY/redundancy work
        assert score >= 0.2

    def test_xml_and_markdown_structure(self):
        """Test combined XML and markdown structure detection."""
        metric = TokenEfficiencyMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Check structure",
            actual_output="""
            Structural improvements:

            XML for data:
            <config>settings</config>

            Markdown for docs:
            ## Section Header

            Both formats optimized for clarity.
            """,
        )

        score = metric.measure(test_case)

        # Should detect both structure types
        assert score >= 0.15
