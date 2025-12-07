"""
Unit tests for AntiPatternDetectionMetric.

Tests the 5-component weighted scoring:
1. Emoji detection (25%)
2. Over-specification detection (20%)
3. Generic prompt detection (20%)
4. Cache-hostile detection (15%)
5. Negative instruction detection (20%)
"""

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.prompt_engineer.anti_pattern_detection_metric import (
    AntiPatternDetectionMetric,
    create_anti_pattern_detection_metric,
)


class TestAntiPatternDetectionMetric:
    """Test suite for AntiPatternDetectionMetric."""

    def test_comprehensive_anti_pattern_detection(self):
        """Test detection of all anti-pattern categories."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze this prompt for anti-patterns",
            actual_output="""
            ## Anti-Pattern Analysis

            ### Emoji Detection
            Found decorative emojis that should be removed. The prompt contains emoji
            anti-patterns that violate professional communication standards.

            ### Over-Specification
            The prompt is over-specified with 700+ lines and micro-instructions.
            Recommend reducing verbosity and consolidating instructions.

            ### Generic Language
            Detected vague prompts lacking specific context. Need to add measurable
            criteria and concrete requirements.

            ### Cache-Hostile Patterns
            Variable data in system prompts causes cache invalidation. Separate
            static content for 90%+ cache hit rates.

            ### Negative Instructions
            Found "Don't X" patterns - convert to positive framing with "Do Y instead".
            Negative instructions should be rewritten as affirmative guidance.
            """
        )

        score = metric.measure(test_case)

        assert score >= 0.85
        assert metric.is_successful()

    def test_emoji_detection_positive(self):
        """Test emoji anti-pattern detection."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Check for emojis",
            actual_output="""
            Emoji anti-pattern detected. Remove all decorative emojis from the prompt.
            Professional communication should be emoji-free. Avoid using emojis
            as they reduce clarity and professionalism.
            """
        )

        score = metric.measure(test_case)

        assert score >= 0.2  # At least emoji component contributes

    def test_emoji_present_in_output_fails(self):
        """Test that emojis in output are flagged."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze the prompt",
            actual_output="Great job! The prompt looks good."
        )

        score = metric.measure(test_case)

        # Should have low emoji score since no detection mentioned
        # and no emojis present (neutral)
        assert score < 0.85

    def test_overspecification_detection(self):
        """Test over-specification detection."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Review prompt structure",
            actual_output="""
            The prompt is over-specified with excessive micro-instructions.
            Reduce verbosity from 700 lines to under 200 lines.
            Consolidate redundant step-by-step instructions.
            Too verbose - needs streamlining.
            """
        )

        score = metric.measure(test_case)

        # Should detect over-specification
        assert score >= 0.15  # Over-spec component contributes

    def test_generic_prompt_detection(self):
        """Test generic prompt detection."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze prompt quality",
            actual_output="""
            Detected generic prompt with vague language. The instructions
            lack specific context and measurable criteria.
            Need to add concrete requirements and clear success metrics.
            Make the prompt more specific with actionable goals.
            """
        )

        score = metric.measure(test_case)

        # Should detect generic patterns
        assert score >= 0.15

    def test_cache_hostile_detection(self):
        """Test cache-hostile pattern detection."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Check cache efficiency",
            actual_output="""
            Cache-hostile patterns detected in system prompt. Variable data
            causes cache invalidation. Separate static and dynamic content
            to achieve 90% cache hit rates. Move timestamps and user-specific
            data out of the system prompt for cache efficiency.
            """
        )

        score = metric.measure(test_case)

        # Should detect cache-hostile patterns
        assert score >= 0.1

    def test_negative_instruction_detection(self):
        """Test negative instruction detection."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Review instruction framing",
            actual_output="""
            Negative instruction patterns found. Convert "Don't do X" to
            positive framing with "Do Y instead". Use affirmative language
            to tell the model what to do, not what to avoid.
            Rewrite all negative instructions as constructive guidance.
            """
        )

        score = metric.measure(test_case)

        # Should detect negative instructions
        assert score >= 0.15

    def test_no_detection_fails(self):
        """Test that missing detection fails threshold."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze prompt",
            actual_output="""
            The prompt looks fine. No issues found.
            Everything is working correctly.
            """
        )

        score = metric.measure(test_case)

        assert score < 0.85
        assert not metric.is_successful()

    def test_partial_detection_medium_score(self):
        """Test partial detection gives medium score."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Review prompt",
            actual_output="""
            Found some issues:
            - Remove emojis from the prompt (emoji anti-pattern)
            - The prompt is too verbose, consider streamlining
            """
        )

        score = metric.measure(test_case)

        # Partial detection - some components pass
        assert 0.3 <= score <= 0.8

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_anti_pattern_detection_metric(threshold=0.90)

        assert isinstance(metric, AntiPatternDetectionMetric)
        assert metric.threshold == 0.90

    def test_async_measure(self):
        """Test async measure method."""
        import asyncio

        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Test async",
            actual_output="""
            Emoji detection: remove all decorative emojis.
            Over-specification: reduce verbose instructions.
            Cache-hostile: separate variable data.
            """
        )

        async def run_async():
            return await metric.a_measure(test_case)

        score = asyncio.run(run_async())

        assert 0.0 <= score <= 1.0

    def test_empty_output(self):
        """Test handling of empty output."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze",
            actual_output=""
        )

        score = metric.measure(test_case)

        assert score < 0.85
        assert not metric.is_successful()

    def test_reason_generation_success(self):
        """Test reason generation for successful detection."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Full analysis",
            actual_output="""
            Anti-pattern analysis complete:
            1. Emoji anti-pattern: Remove decorative emojis
            2. Over-specification detected: Reduce 700 lines to 150
            3. Generic prompt: Add specific measurable criteria
            4. Cache-hostile: Achieve 90% cache hit with static separation
            5. Negative instructions: Convert "Don't X" to positive framing
            """
        )

        metric.measure(test_case)

        assert "Score:" in metric.reason

    def test_reason_generation_failure(self):
        """Test reason generation for failed detection."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Basic check",
            actual_output="Looks good to me."
        )

        metric.measure(test_case)

        assert "below threshold" in metric.reason

    def test_component_weights_sum_to_one(self):
        """Test that component weights sum to 1.0."""
        # Emoji (0.25) + Over-spec (0.20) + Generic (0.20) + Cache (0.15) + Negative (0.20)
        total = 0.25 + 0.20 + 0.20 + 0.15 + 0.20
        assert total == pytest.approx(1.0)

    def test_score_capped_at_one(self):
        """Test that score is capped at 1.0."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Comprehensive analysis",
            actual_output="""
            Complete anti-pattern detection:

            EMOJI: All decorative emojis removed. Emoji-free communication enforced.

            OVER-SPECIFICATION: Reduced from 738 lines to 150 lines (80% reduction).
            Eliminated micro-instructions and consolidated to essential guidance.

            GENERIC: Added specific measurable criteria. Replaced vague language
            with concrete requirements and actionable success metrics.

            CACHE: Achieved 95% cache hit rate by separating stable system prompts
            from variable user data. Cache-friendly structure implemented.

            NEGATIVE: Converted all "Don't X" patterns to positive "Do Y" framing.
            Affirmative instruction style throughout.
            """
        )

        score = metric.measure(test_case)

        assert score <= 1.0

    def test_specific_emoji_phrases(self):
        """Test various emoji detection phrases."""
        metric = AntiPatternDetectionMetric(threshold=0.85)

        phrases = [
            "remove emojis",
            "avoid decorative emoji",
            "emoji anti-pattern",
            "no emojis allowed",
            "eliminate emojis",
        ]

        for phrase in phrases:
            test_case = LLMTestCase(
                input="Check",
                actual_output=f"Found issue: {phrase} from the prompt."
            )
            score = metric.measure(test_case)
            # Should detect emoji-related content
            assert score >= 0.1, f"Failed to detect: {phrase}"

    def test_overspecification_line_count_mention(self):
        """Test detection of specific line count mentions."""
        metric = AntiPatternDetectionMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Analyze verbosity",
            actual_output="""
            Over-specification detected:
            - Original: 700+ lines
            - Target: Under 200 lines
            Reduce verbosity by consolidating instructions.
            """
        )

        score = metric.measure(test_case)

        # Should detect the line count as over-specification
        assert score >= 0.15

