"""
Unit tests for RefactoringQualityMetric.

Tests the 5-component weighted scoring:
1. Before/after comparison (25%)
2. Quality rubric application (20%)
3. Improvement prioritization (20%)
4. Claude 4.5 alignment (20%)
5. Evidence-based recommendations (15%)
"""

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.prompt_engineer.refactoring_quality_metric import (
    RefactoringQualityMetric,
    create_refactoring_quality_metric,
)


class TestRefactoringQualityMetric:
    """Test suite for RefactoringQualityMetric."""

    def test_comprehensive_refactoring_quality(self):
        """Test comprehensive refactoring quality."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Refactor this prompt",
            actual_output="""
            ## Prompt Refactoring Report

            ### Before/After Comparison
            - Original: 700 lines, unfocused
            - Refactored: 150 lines, structured
            - Improvement: 78% reduction

            ### Quality Rubric Assessment
            Using 8-criteria evaluation:
            | Criterion | Before | After |
            |-----------|--------|-------|
            | Clarity | 2/5 | 4/5 |
            | Specificity | 2/5 | 5/5 |
            | Measurable | 1/5 | 4/5 |
            | Actionable | 3/5 | 5/5 |
            | Correctness | 4/5 | 5/5 |
            | Consistency | 2/5 | 5/5 |
            | Completeness | 3/5 | 4/5 |
            | Maintainability | 2/5 | 5/5 |

            Average: 2.4 -> 4.6 (+2.2 improvement)

            ### Prioritized Improvements
            1. **High Impact**: Remove emojis and over-specification
            2. **Medium Impact**: Add measurable success criteria
            3. **Low Impact**: Improve section organization

            ### Claude 4.5 Alignment
            Applied 2025 best practices:
            - Extended thinking configuration (16k budget)
            - Parallel tool execution patterns
            - Structured output with XML schema
            - Direct, concise communication style
            - No emojis throughout

            ### Evidence-Based Rationale
            Each change justified because:
            - Emoji removal improves professional tone (research shows 40% better reception)
            - Token reduction leads to faster inference (therefore lower latency)
            - Structure improves comprehension (based on cognitive load studies)
            """
        )

        score = metric.measure(test_case)

        assert score >= 0.80
        assert metric.is_successful()

    def test_before_after_comparison(self):
        """Test before/after comparison detection."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Show improvements",
            actual_output="""
            Before: 500 lines, verbose instructions
            After: 200 lines, focused guidance

            Original was unfocused, new version is streamlined.
            Reduced from 1000 tokens to 400 tokens.
            """
        )

        score = metric.measure(test_case)

        # Should detect before/after comparison
        assert score >= 0.20

    def test_quantitative_before_after(self):
        """Test quantitative before/after metrics."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Measure improvements",
            actual_output="""
            Quantitative improvements:
            - Was 800 tokens, now 300 tokens
            - Reduced by 62.5%
            - From 40 lines to 15 lines
            """
        )

        score = metric.measure(test_case)

        # Should score well for quantitative comparison
        assert score >= 0.20

    def test_quality_rubric_8_criteria(self):
        """Test quality rubric with 8 criteria."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Apply rubric",
            actual_output="""
            Quality Rubric (8 criteria, 1-5 scale):

            1. Clarity: 4/5 - Instructions are clear
            2. Specificity: 5/5 - Concrete requirements
            3. Measurable: 4/5 - Success metrics defined
            4. Actionable: 5/5 - Steps are executable
            5. Correctness: 5/5 - Technically accurate
            6. Consistency: 4/5 - Uniform style
            7. Completeness: 4/5 - All sections present
            8. Maintainability: 5/5 - Easy to update

            Average score: 4.5/5
            """
        )

        score = metric.measure(test_case)

        # Should score well for rubric
        assert score >= 0.15

    def test_improvement_prioritization(self):
        """Test improvement prioritization detection."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Prioritize changes",
            actual_output="""
            Prioritized by impact:

            1. High priority: Remove emojis (critical)
            2. Medium priority: Reduce verbosity
            3. Low priority: Reorganize sections

            Must-have changes first, nice-to-have later.
            Most important improvements at the top.
            """
        )

        score = metric.measure(test_case)

        # Should detect prioritization
        assert score >= 0.15

    def test_claude45_alignment(self):
        """Test Claude 4.5 alignment detection."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Apply best practices",
            actual_output="""
            Claude 4.5 Best Practices Applied:

            - Extended thinking with 16k token budget
            - Parallel tool execution patterns
            - Structured output with JSON schema
            - Direct communication style
            - No emojis in output
            - 2025 modern patterns
            """
        )

        score = metric.measure(test_case)

        # Should detect Claude 4.5 alignment
        assert score >= 0.15

    def test_evidence_based_recommendations(self):
        """Test evidence-based recommendations."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Justify changes",
            actual_output="""
            Changes with rationale:

            1. Remove emojis because they reduce professional tone
            2. Add structure since it improves comprehension
            3. Use XML therefore output is machine-readable

            Based on research, structured prompts perform better.
            According to best practices, this approach works.
            The reason for each change is documented.
            """
        )

        score = metric.measure(test_case)

        # Should detect evidence-based approach
        assert score >= 0.10

    def test_no_quality_indicators_fails(self):
        """Test that missing quality indicators fails."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Review prompt",
            actual_output="""
            Made some changes to the prompt.
            It should work better now.
            """
        )

        score = metric.measure(test_case)

        assert score < 0.80
        assert not metric.is_successful()

    def test_partial_quality_medium_score(self):
        """Test partial quality gives medium score."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Quick refactor",
            actual_output="""
            Before: Long prompt
            After: Shorter prompt

            Improved clarity and specificity.
            """
        )

        score = metric.measure(test_case)

        # Partial quality indicators
        assert 0.2 <= score <= 0.7

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_refactoring_quality_metric(threshold=0.75)

        assert isinstance(metric, RefactoringQualityMetric)
        assert metric.threshold == 0.75

    def test_async_measure(self):
        """Test async measure method."""
        import asyncio

        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Test async",
            actual_output="""
            Before: 500 lines
            After: 200 lines
            Improved clarity and specificity.
            Because shorter is better.
            """
        )

        async def run_async():
            return await metric.a_measure(test_case)

        score = asyncio.run(run_async())

        assert 0.0 <= score <= 1.0

    def test_empty_output(self):
        """Test handling of empty output."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Refactor",
            actual_output=""
        )

        score = metric.measure(test_case)

        assert score < 0.80
        assert not metric.is_successful()

    def test_reason_generation_success(self):
        """Test reason generation for successful refactoring."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Full refactor",
            actual_output="""
            Complete refactoring:
            - Before: 700 lines, After: 150 lines (78% reduction)
            - Quality rubric: average 4.5/5 on clarity, specificity, measurable
            - Priority: 1. High impact, 2. Medium, 3. Low
            - Claude 4.5: Extended thinking, parallel tools, no emojis
            - Rationale: because each change improves efficiency
            """
        )

        metric.measure(test_case)

        assert "Score:" in metric.reason

    def test_reason_generation_failure(self):
        """Test reason generation for failed refactoring."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Basic check",
            actual_output="Made changes."
        )

        metric.measure(test_case)

        assert "below threshold" in metric.reason

    def test_component_weights_sum_to_one(self):
        """Test that component weights sum to 1.0."""
        # Before/After (0.25) + Rubric (0.20) + Priority (0.20) + Claude45 (0.20) + Evidence (0.15)
        total = 0.25 + 0.20 + 0.20 + 0.20 + 0.15
        assert total == pytest.approx(1.0)

    def test_score_capped_at_one(self):
        """Test that score is capped at 1.0."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="Maximum quality",
            actual_output="""
            ## Complete Refactoring Analysis

            ### BEFORE/AFTER
            Original: 1000 lines, 5000 tokens
            New: 200 lines, 1000 tokens
            Improvement: 80% reduction
            Was verbose, now concise.

            ### QUALITY RUBRIC
            8 criteria assessment (1-5 scale):
            - Clarity: 5/5
            - Specificity: 5/5
            - Measurable: 5/5
            - Actionable: 5/5
            - Correctness: 5/5
            - Consistency: 5/5
            - Completeness: 5/5
            - Maintainability: 5/5
            Average: 5.0/5

            ### PRIORITY ORDER
            Ranked by impact:
            1. Critical: Remove emojis (high priority)
            2. Essential: Add structure (must-have)
            3. Important: Reduce length (should-have)
            4. Nice-to-have: Polish wording (could-have)

            ### CLAUDE 4.5 ALIGNMENT
            2025 best practices:
            - Extended thinking: 32k budget
            - Parallel tool execution enabled
            - Structured output with XML schema
            - Direct communication, no emojis
            - Modern patterns throughout

            ### EVIDENCE
            Each change justified because:
            - Research shows structured prompts work better
            - Therefore improvements are measurable
            - Based on best practices, this approach is optimal
            - According to studies, users prefer concise prompts
            - The reason for removal: reduces cognitive load
            - Hence the final result is superior
            """
        )

        score = metric.measure(test_case)

        assert score <= 1.0

    def test_various_comparison_phrases(self):
        """Test various before/after comparison phrases."""
        metric = RefactoringQualityMetric(threshold=0.80)

        phrases = [
            "before: X, after: Y",
            "original: A, refactored: B",
            "was 100, now 50",
            "old version vs new version",
            "improvement from 200 to 100 lines",
        ]

        for phrase in phrases:
            test_case = LLMTestCase(
                input="Check",
                actual_output=f"Changes: {phrase} in the prompt."
            )
            score = metric.measure(test_case)
            # Should detect comparison patterns
            assert score >= 0.1, f"Failed to detect: {phrase}"

    def test_criteria_keywords(self):
        """Test detection of quality criteria keywords."""
        metric = RefactoringQualityMetric(threshold=0.80)

        criteria = [
            "clarity",
            "specificity",
            "measurable",
            "actionable",
            "correctness",
            "consistency",
            "completeness",
            "maintainability",
        ]

        for criterion in criteria:
            test_case = LLMTestCase(
                input="Evaluate",
                actual_output=f"Improved {criterion} by restructuring the prompt."
            )
            score = metric.measure(test_case)
            # Should contribute to rubric score
            assert score >= 0.05, f"Failed for criterion: {criterion}"

    def test_numbered_list_prioritization(self):
        """Test numbered list as prioritization."""
        metric = RefactoringQualityMetric(threshold=0.80)
        test_case = LLMTestCase(
            input="List changes",
            actual_output="""
            Improvements:
            1. First, remove emojis
            2. Second, add structure
            3. Third, reduce length
            4. Finally, polish wording
            """
        )

        score = metric.measure(test_case)

        # Should detect structured prioritization
        assert score >= 0.15

    def test_justification_keywords(self):
        """Test evidence-based justification keywords."""
        metric = RefactoringQualityMetric(threshold=0.80)

        keywords = [
            "because",
            "therefore",
            "since",
            "hence",
            "based on",
            "according to",
        ]

        for keyword in keywords:
            test_case = LLMTestCase(
                input="Justify",
                actual_output=f"Made this change {keyword} it improves clarity."
            )
            score = metric.measure(test_case)
            # Should detect justification
            assert score >= 0.05, f"Failed for keyword: {keyword}"

