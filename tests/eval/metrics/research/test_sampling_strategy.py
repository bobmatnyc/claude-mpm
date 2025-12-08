"""
Unit tests for SamplingStrategyMetric.

Tests cover:
- Discovery tools detection (grep, glob, search, find)
- Pattern extraction validation (structure, architecture, patterns)
- Strategic sampling detection (representative samples, focused approach)
- Executive summary presence
- Anti-pattern detection (brute force indicators)
- Edge cases and scoring thresholds
"""

import pytest
from deepeval.test_case import LLMTestCase

from .sampling_strategy_metric import (
    SamplingStrategyMetric,
    create_sampling_strategy_metric,
)


class TestSamplingStrategyMetric:
    """Test suite for SamplingStrategyMetric."""

    # ========================================================================
    # PERFECT COMPLIANCE TESTS
    # ========================================================================

    def test_perfect_strategic_research(self):
        """Test perfect compliance with all strategic components."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Analyze the architecture of this codebase",
            actual_output="""I'll analyze the codebase architecture strategically.

First, I'll use Glob to discover Python files:
Found 45 files across src/, tests/, and scripts/ directories.

Using Grep to search for patterns:
- Service classes: 12 files
- Repository classes: 8 files
- Controllers: 15 files

Key patterns identified:
1. Service-oriented architecture with dependency injection
2. Repository pattern for data access layer
3. MVC structure with clear separation of concerns

Representative samples:
- src/services/user_service.py (service layer example)
- src/repositories/base_repository.py (repository pattern)
- src/controllers/api_controller.py (controller pattern)

Executive Summary:
The codebase follows a clean architecture with three main layers:
controllers (presentation), services (business logic), and repositories
(data access). Dependency injection is used throughout for testability.
""",
        )

        score = metric.measure(test_case)
        assert score >= 0.85, (
            f"Perfect strategic research should score >= 0.85, got {score}"
        )
        assert metric.is_successful()
        assert "Excellent strategic research" in metric.reason

    # ========================================================================
    # DISCOVERY TOOLS TESTS (30% weight)
    # ========================================================================

    def test_discovery_tools_multiple_tools(self):
        """Test discovery with multiple tools (grep + glob)."""
        metric = SamplingStrategyMetric(threshold=0.3)

        test_case = LLMTestCase(
            input="Find all test files",
            actual_output="""Using Glob to find test files: **/*test*.py
Found 50 test files.

Using Grep to search for test patterns: "def test_"
Identified 250 test functions.
""",
        )

        score = metric.measure(test_case)
        # Should score full points for discovery (30%)
        assert score >= 0.3, f"Multiple discovery tools should score, got {score}"
        assert metric.is_successful()

    def test_discovery_tools_single_tool(self):
        """Test discovery with single tool (partial score)."""
        metric = SamplingStrategyMetric(threshold=0.15)

        test_case = LLMTestCase(
            input="Search for configuration files",
            actual_output="""Searching for config files in the repository.
Found config.yaml and settings.json in the config/ directory.
""",
        )

        score = metric.measure(test_case)
        # Should get partial discovery score (0.5 * 0.30 = 0.15)
        assert score >= 0.15, (
            f"Single discovery tool should get partial score, got {score}"
        )

    def test_discovery_tools_none(self):
        """Test no discovery tools used."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Analyze codebase",
            actual_output="""I read the files and found some code.
There are classes and functions.
""",
        )

        score = metric.measure(test_case)
        # Should lose discovery component (0% of 30%)
        assert score < 0.85, f"No discovery should fail threshold, got {score}"
        assert not metric.is_successful()
        assert "No discovery tools detected" in metric.reason

    def test_discovery_tools_case_insensitive(self):
        """Test discovery tool detection is case-insensitive."""
        metric = SamplingStrategyMetric(threshold=0.3)

        test_case = LLMTestCase(
            input="Find files",
            actual_output="""Using GLOB to discover files.
Using grep to SEARCH for patterns.
""",
        )

        score = metric.measure(test_case)
        # Should detect both tools despite case differences
        assert score >= 0.3, f"Case-insensitive discovery should work, got {score}"

    # ========================================================================
    # PATTERN EXTRACTION TESTS (25% weight)
    # ========================================================================

    def test_pattern_extraction_multiple_indicators(self):
        """Test pattern extraction with multiple indicators."""
        metric = SamplingStrategyMetric(threshold=0.25)

        test_case = LLMTestCase(
            input="What patterns are used?",
            actual_output="""Analyzing the codebase structure and architecture.

Key patterns identified:
1. Factory pattern for object creation
2. Observer pattern for event handling
3. Strategy pattern for algorithm selection

The architecture follows a layered design with clear separation.
""",
        )

        score = metric.measure(test_case)
        # Should score full points for pattern extraction (25%)
        assert score >= 0.25, f"Multiple pattern indicators should score, got {score}"
        assert metric.is_successful()

    def test_pattern_extraction_single_indicator(self):
        """Test pattern extraction with single indicator (partial score)."""
        metric = SamplingStrategyMetric(threshold=0.15)

        test_case = LLMTestCase(
            input="Describe structure",
            actual_output="""The codebase has a clear structure with modules organized by feature.
Files are grouped logically.
""",
        )

        score = metric.measure(test_case)
        # Should get partial pattern score (0.6 * 0.25 = 0.15)
        assert score >= 0.10, (
            f"Single pattern indicator should get partial score, got {score}"
        )

    def test_pattern_extraction_none(self):
        """Test no pattern extraction."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Analyze code",
            actual_output="""I found some files with code in them.
The code does various things.
""",
        )

        score = metric.measure(test_case)
        # Should lose pattern component (0% of 25%)
        assert score < 0.85, f"No pattern extraction should fail, got {score}"
        assert "No pattern extraction detected" in metric.reason

    def test_pattern_extraction_architecture_keywords(self):
        """Test pattern extraction with architecture keywords."""
        metric = SamplingStrategyMetric(threshold=0.25)

        test_case = LLMTestCase(
            input="Describe architecture",
            actual_output="""The architecture is based on microservices design pattern.
Each service follows a clean architecture approach.
""",
        )

        score = metric.measure(test_case)
        assert score >= 0.25, f"Architecture keywords should score, got {score}"

    # ========================================================================
    # STRATEGIC SAMPLING TESTS (25% weight)
    # ========================================================================

    def test_strategic_sampling_multiple_indicators(self):
        """Test strategic sampling with multiple indicators."""
        metric = SamplingStrategyMetric(threshold=0.25)

        test_case = LLMTestCase(
            input="Give examples",
            actual_output="""I focused on key files that represent the architecture.

Representative sample files:
- user_service.py (service layer)
- auth_middleware.py (middleware pattern)

Selected strategically to demonstrate core patterns.
""",
        )

        score = metric.measure(test_case)
        # Should score full points for sampling (25%)
        assert score >= 0.25, f"Multiple sampling indicators should score, got {score}"
        assert metric.is_successful()

    def test_strategic_sampling_single_indicator(self):
        """Test strategic sampling with single indicator (partial score)."""
        metric = SamplingStrategyMetric(threshold=0.15)

        test_case = LLMTestCase(
            input="Show examples",
            actual_output="""Here are some representative samples from the codebase:
- example1.py
- example2.py
""",
        )

        score = metric.measure(test_case)
        # Should get partial sampling score (0.6 * 0.25 = 0.15)
        assert score >= 0.10, f"Single sampling indicator should score, got {score}"

    def test_strategic_sampling_none(self):
        """Test no strategic sampling."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Analyze files",
            actual_output="""I looked at the files and they contain code.
The code has functions and classes.
""",
        )

        score = metric.measure(test_case)
        # Should lose sampling component (0% of 25%)
        assert score < 0.85, f"No strategic sampling should fail, got {score}"
        assert "No strategic sampling detected" in metric.reason

    def test_strategic_sampling_key_examples(self):
        """Test strategic sampling with key examples language."""
        metric = SamplingStrategyMetric(threshold=0.25)

        test_case = LLMTestCase(
            input="Show key files",
            actual_output="""Key examples that illustrate the pattern:
- main.py (entry point)
- config.py (configuration)
""",
        )

        score = metric.measure(test_case)
        assert score >= 0.20, f"Key examples should score, got {score}"

    # ========================================================================
    # EXECUTIVE SUMMARY TESTS (20% weight)
    # ========================================================================

    def test_executive_summary_present(self):
        """Test executive summary is present."""
        metric = SamplingStrategyMetric(threshold=0.20)

        test_case = LLMTestCase(
            input="Summarize findings",
            actual_output="""Analysis of codebase...

Executive Summary:
The codebase is well-structured with clear separation of concerns.
Main components include services, repositories, and controllers.
""",
        )

        score = metric.measure(test_case)
        # Should score full points for summary (20%)
        assert score >= 0.20, f"Executive summary should score, got {score}"
        assert metric.is_successful()

    def test_executive_summary_overview(self):
        """Test summary with overview keyword."""
        metric = SamplingStrategyMetric(threshold=0.20)

        test_case = LLMTestCase(
            input="Give overview",
            actual_output="""Overview:
The project follows standard Python conventions with pytest for testing.
""",
        )

        score = metric.measure(test_case)
        assert score >= 0.20, f"Overview should count as summary, got {score}"

    def test_executive_summary_conclusion(self):
        """Test summary with conclusion keyword."""
        metric = SamplingStrategyMetric(threshold=0.20)

        test_case = LLMTestCase(
            input="Analyze",
            actual_output="""Detailed analysis...

Conclusion:
The architecture is solid with room for improvement in testing coverage.
""",
        )

        score = metric.measure(test_case)
        assert score >= 0.20, f"Conclusion should count as summary, got {score}"

    def test_executive_summary_none(self):
        """Test no executive summary."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Analyze",
            actual_output="""I found files. The files have code.
""",
        )

        score = metric.measure(test_case)
        # Should lose summary component (0% of 20%)
        assert score < 0.85, f"No summary should fail, got {score}"
        assert "No executive summary" in metric.reason

    # ========================================================================
    # ANTI-PATTERN TESTS
    # ========================================================================

    def test_anti_pattern_reading_all(self):
        """Test anti-pattern: reading all files."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Analyze codebase",
            actual_output="""I'm reading all the files in the repository.
Processing every single file to get complete coverage.

Using Glob and Grep for discovery.
Identified patterns in the code.
Focused on representative samples.

Summary: Architecture is good.
""",
        )

        score = metric.measure(test_case)
        # Base score would be high, but penalty should reduce it
        # Anti-patterns: "reading all" + "every single" = 2 * 0.2 = 0.4 penalty
        # Penalty reduces score by up to 50%
        assert score < 0.85, (
            f"Anti-patterns should reduce score below threshold, got {score}"
        )
        assert not metric.is_successful()
        assert "Anti-patterns detected" in metric.reason

    def test_anti_pattern_exhaustive(self):
        """Test anti-pattern: exhaustive analysis."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Analyze",
            actual_output="""Performing exhaustive analysis of all files.

Using Glob to find files.
Identified patterns.
Sample files shown.

Summary: Complete analysis done.
""",
        )

        score = metric.measure(test_case)
        # "exhaustive" anti-pattern should trigger penalty
        assert score < 0.90, f"Exhaustive anti-pattern should reduce score, got {score}"
        assert "Anti-patterns detected" in metric.reason

    def test_anti_pattern_none(self):
        """Test no anti-patterns present."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Analyze",
            actual_output="""Strategic analysis using discovery tools.

Using Glob and Grep for targeted discovery.
Identified key patterns.
Focused on representative samples.

Summary: Clean architecture with good practices.
""",
        )

        score = metric.measure(test_case)
        # No anti-patterns, should score well
        assert score >= 0.85, f"No anti-patterns should allow high score, got {score}"
        assert metric.is_successful()

    # ========================================================================
    # COMBINED COMPONENT TESTS
    # ========================================================================

    def test_threshold_85_percent_requires_most_components(self):
        """Test that 0.85 threshold requires most components."""
        metric = SamplingStrategyMetric(threshold=0.85)

        # Missing strategic sampling (25%)
        test_case = LLMTestCase(
            input="Analyze",
            actual_output="""Using Glob and Grep for discovery.
Identified architecture patterns and structure.

Summary: Good architecture overall.
""",
        )

        score = metric.measure(test_case)
        # Discovery (30%) + Pattern (25%) + Summary (20%) = 75%
        # Missing sampling (25%), should fail threshold
        assert score < 0.85, (
            f"Missing component should fail 0.85 threshold, got {score}"
        )
        assert not metric.is_successful()

    def test_all_components_partial_scores(self):
        """Test partial scores in all components."""
        metric = SamplingStrategyMetric(threshold=0.50)

        test_case = LLMTestCase(
            input="Analyze",
            actual_output="""Searching for files in the repository.
Found some structure in the code.
Here's a sample file: main.py
Overview: Code is organized.
""",
        )

        score = metric.measure(test_case)
        # Each component has partial score:
        # Discovery: 0.5 * 0.30 = 0.15 (1 tool: "searching")
        # Pattern: 0.0 * 0.25 = 0.00 (only "structure" mentioned, needs 2+)
        # Sampling: 0.6 * 0.25 = 0.15 (1 indicator: "sample")
        # Summary: 1.0 * 0.20 = 0.20 (has "overview")
        # Total: 0.15 + 0.00 + 0.15 + 0.20 = 0.50
        assert 0.45 <= score <= 0.55, f"Partial scores should total ~0.50, got {score}"
        assert metric.is_successful()

    # ========================================================================
    # FACTORY FUNCTION TEST
    # ========================================================================

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_sampling_strategy_metric(threshold=0.90)

        assert isinstance(metric, SamplingStrategyMetric)
        assert metric.threshold == 0.90

    # ========================================================================
    # EDGE CASES
    # ========================================================================

    def test_edge_case_empty_output(self):
        """Test handling of empty output."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(input="Analyze", actual_output="")

        score = metric.measure(test_case)
        assert score == 0.0, f"Empty output should score 0.0, got {score}"
        assert not metric.is_successful()

    def test_edge_case_minimal_output(self):
        """Test handling of minimal output."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(input="Analyze", actual_output="Done.")

        score = metric.measure(test_case)
        assert score == 0.0, f"Minimal output should score 0.0, got {score}"
        assert not metric.is_successful()

    def test_edge_case_very_high_threshold(self):
        """Test with very high threshold (requires perfection)."""
        metric = SamplingStrategyMetric(threshold=0.99)

        test_case = LLMTestCase(
            input="Analyze",
            actual_output="""Using Glob and Grep to discover files.
Identified patterns and architecture.
Focused on representative samples.
Summary: Clean architecture.
""",
        )

        score = metric.measure(test_case)
        # Should score well but might not hit 0.99
        assert score >= 0.85, f"Good output should score high, got {score}"
        # May or may not pass 0.99 threshold
        if score >= 0.99:
            assert metric.is_successful()

    def test_reason_generation_all_components_missing(self):
        """Test reason generation when all components missing."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(input="Analyze", actual_output="I looked at files.")

        score = metric.measure(test_case)
        assert score == 0.0, f"No components should score 0.0, got {score}"

        # Check all components mentioned in reason
        assert "No discovery tools" in metric.reason
        assert "No pattern extraction" in metric.reason
        assert "No strategic sampling" in metric.reason
        assert "No executive summary" in metric.reason

    def test_reason_generation_success(self):
        """Test reason generation for successful case."""
        metric = SamplingStrategyMetric(threshold=0.85)

        test_case = LLMTestCase(
            input="Analyze",
            actual_output="""Using Glob and Grep for discovery.
Identified patterns and architecture.
Focused on representative sample files.
Summary: Clean architecture with good separation of concerns.
""",
        )

        score = metric.measure(test_case)
        assert score >= 0.85, f"All components should score >= 0.85, got {score}"
        assert "Excellent strategic research" in metric.reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
