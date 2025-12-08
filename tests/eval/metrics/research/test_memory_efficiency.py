"""
Unit tests for MemoryEfficiencyMetric.

Tests all scoring components:
1. File size check detection
2. Summarizer usage validation
3. File limit compliance
4. Strategic sampling detection
5. Brute force pattern avoidance

Covers both compliant and non-compliant Research Agent responses.
"""

import pytest
from deepeval.test_case import LLMTestCase

from .memory_efficiency_metric import (
    MemoryEfficiencyMetric,
    create_memory_efficiency_metric,
)


class TestMemoryEfficiencyMetric:
    """Test suite for MemoryEfficiencyMetric."""

    def test_perfect_compliance(self):
        """Test response with perfect memory efficiency compliance."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
First, I'll use grep to locate authentication-related files.

Checking file size... auth.py is 45KB (large file).

Since this is a large file (>20KB), I'll use the document_summarizer tool
to get an overview rather than reading the entire file.

Using document_summarizer for auth.py...

After analyzing the summary, I'll strategically sample key sections:
- Reading auth.py lines 100-250 (authentication core logic)
- Reading config.py lines 500-650 (token validation)
- Reading validators.py lines 1-150 (input validation)

This targeted approach avoids reading the entire codebase and focuses
on the most relevant authentication implementation details.
"""

        test_case = LLMTestCase(
            input="Research the authentication implementation", actual_output=output
        )

        score = metric.measure(test_case)

        # Should score very high (all components satisfied)
        # Use epsilon for floating point comparison
        epsilon = 1e-9
        assert score >= (0.9 - epsilon), f"Expected score >= 0.9, got {score}"
        assert metric.is_successful()
        assert (
            "perfect" in metric.reason.lower()
            or "all protocols followed" in metric.reason.lower()
        )

    def test_file_size_check_present(self):
        """Test detection of file size checking patterns."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
Checking file size before reading...
- auth.py: 45KB
- config.py: 12KB
- validators.py: 8KB
"""

        test_case = LLMTestCase(input="Research files", actual_output=output)

        score = metric.measure(test_case)

        # File size check component should score 1.0
        size_check_score = metric._score_file_size_check(output)
        assert size_check_score == 1.0, f"Expected 1.0, got {size_check_score}"

    def test_file_size_check_missing(self):
        """Test penalty when file size check is missing."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
Reading auth.py...
Reading config.py...
Reading validators.py...
"""

        test_case = LLMTestCase(input="Research files", actual_output=output)

        score = metric.measure(test_case)

        # File size check component should score low
        size_check_score = metric._score_file_size_check(output)
        assert size_check_score < 0.5, f"Expected <0.5, got {size_check_score}"

    def test_summarizer_usage_for_large_files(self):
        """Test detection of summarizer usage for large files."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
File size: 45KB - this is a large file.
Using document_summarizer to analyze the file efficiently...
"""

        test_case = LLMTestCase(input="Analyze large file", actual_output=output)

        score = metric.measure(test_case)

        # Summarizer component should score 1.0
        summarizer_score = metric._score_summarizer_usage(output)
        assert summarizer_score == 1.0, f"Expected 1.0, got {summarizer_score}"

    def test_summarizer_missing_for_large_files(self):
        """Test penalty when summarizer not used for large files."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
Reading large file (55KB)... analyzing entire contents.
"""

        test_case = LLMTestCase(input="Analyze file", actual_output=output)

        score = metric.measure(test_case)

        # Summarizer component should score low
        summarizer_score = metric._score_summarizer_usage(output)
        assert summarizer_score < 0.5, f"Expected <0.5, got {summarizer_score}"

    def test_file_limit_compliance_within_range(self):
        """Test file limit compliance when within recommended range (3-5 files)."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
Reading auth.py...
Reading config.py...
Reading validators.py...
Reading middleware.py...
Reading tokens.py...
"""

        test_case = LLMTestCase(input="Research authentication", actual_output=output)

        score = metric.measure(test_case)

        # File limit component should score 1.0 (5 files is at upper range)
        file_limit_score = metric._score_file_limit_compliance(output)
        assert file_limit_score == 1.0, f"Expected 1.0, got {file_limit_score}"

    def test_file_limit_violation_excessive_files(self):
        """Test penalty when too many files are read."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
Reading file1.py...
Reading file2.py...
Reading file3.py...
Reading file4.py...
Reading file5.py...
Reading file6.py...
Reading file7.py...
Reading file8.py...
Reading file9.py...
Reading file10.py...
Reading file11.py...
"""

        test_case = LLMTestCase(input="Research codebase", actual_output=output)

        score = metric.measure(test_case)

        # File limit component should score very low (11 files is excessive)
        file_limit_score = metric._score_file_limit_compliance(output)
        assert file_limit_score < 0.5, f"Expected <0.5, got {file_limit_score}"

    def test_strategic_sampling_detected(self):
        """Test detection of strategic sampling patterns."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
Sampling auth.py:
- Lines 100-250 (core authentication logic)
- Lines 500-650 (token validation)

Reading first 150 lines of config.py for configuration analysis.
"""

        test_case = LLMTestCase(input="Sample files", actual_output=output)

        score = metric.measure(test_case)

        # Sampling component should score 1.0
        sampling_score = metric._score_strategic_sampling(output)
        assert sampling_score == 1.0, f"Expected 1.0, got {sampling_score}"

    def test_strategic_sampling_missing(self):
        """Test penalty when no strategic sampling is detected."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
Reading entire file contents...
Analyzing all lines...
"""

        test_case = LLMTestCase(input="Analyze file", actual_output=output)

        score = metric.measure(test_case)

        # Sampling component should score low
        sampling_score = metric._score_strategic_sampling(output)
        assert sampling_score < 0.5, f"Expected <0.5, got {sampling_score}"

    def test_no_brute_force_targeted_discovery(self):
        """Test reward for targeted discovery (grep/glob)."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
Using grep to find authentication-related files...
Filtering results with glob pattern '**/*auth*.py'...
Located 3 relevant files for analysis.
"""

        test_case = LLMTestCase(input="Find auth files", actual_output=output)

        score = metric.measure(test_case)

        # Brute force component should score 1.0 (targeted discovery)
        brute_force_score = metric._score_no_brute_force(output)
        assert brute_force_score == 1.0, f"Expected 1.0, got {brute_force_score}"

    def test_brute_force_pattern_detected(self):
        """Test penalty when brute force patterns are detected."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
Reading all files in the codebase...
Scanning entire repository for authentication patterns...
Checking every file to ensure completeness...
"""

        test_case = LLMTestCase(input="Research codebase", actual_output=output)

        score = metric.measure(test_case)

        # Brute force component should score 0.0
        brute_force_score = metric._score_no_brute_force(output)
        assert brute_force_score == 0.0, f"Expected 0.0, got {brute_force_score}"

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_memory_efficiency_metric(threshold=0.95)

        assert isinstance(metric, MemoryEfficiencyMetric)
        assert metric.threshold == 0.95

    def test_async_measure(self):
        """Test async measurement delegates to sync."""
        import asyncio

        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
Checking file size... auth.py is 45KB.
Using document_summarizer for large file analysis...
Sampling lines 100-200...
"""

        test_case = LLMTestCase(input="Research auth", actual_output=output)

        # Run async measure
        async def run_async():
            return await metric.a_measure(test_case)

        score = asyncio.run(run_async())

        assert score >= 0.9
        assert metric.is_successful()

    def test_threshold_enforcement(self):
        """Test threshold enforcement with epsilon handling."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        # Non-compliant output (should fail)
        output = """
Reading all files in the codebase without checking sizes...
No summarization used...
"""

        test_case = LLMTestCase(input="Research", actual_output=output)

        score = metric.measure(test_case)

        assert score < 0.9, f"Expected score <0.9, got {score}"
        assert not metric.is_successful()

    def test_metric_name_property(self):
        """Test metric name property."""
        metric = MemoryEfficiencyMetric()
        assert metric.__name__ == "Memory Efficiency"

    def test_reason_generation_comprehensive(self):
        """Test comprehensive reason generation with multiple violations."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        output = """
Reading file1.py...
Reading file2.py...
Reading file3.py...
Reading file4.py...
Reading file5.py...
Reading file6.py...
Reading file7.py...

File sizes: 45KB, 55KB, 30KB

Analyzing entire codebase to ensure completeness...
Reading all files without sampling...
"""

        test_case = LLMTestCase(input="Research", actual_output=output)

        score = metric.measure(test_case)

        # Reason should mention multiple issues
        reason = metric.reason
        assert (
            "file" in reason.lower()
            or "limit" in reason.lower()
            or "sampling" in reason.lower()
        )
        assert len(reason) > 20, "Reason should be descriptive"

    def test_score_properties_initialized(self):
        """Test score properties are None before measurement."""
        metric = MemoryEfficiencyMetric()

        assert metric.score is None
        assert metric.reason is None
        assert not metric.is_successful()

    def test_multiple_measurements_update_state(self):
        """Test that multiple measurements update metric state correctly."""
        metric = MemoryEfficiencyMetric(threshold=0.9)

        # First measurement (compliant)
        compliant_output = """
Checking file size... auth.py is 45KB.
Using document_summarizer...
Sampling lines 100-200...
"""

        test_case1 = LLMTestCase(input="Research", actual_output=compliant_output)

        score1 = metric.measure(test_case1)
        assert score1 >= 0.9
        assert metric.is_successful()

        # Second measurement (non-compliant)
        non_compliant_output = """
Reading all files without size checks...
"""

        test_case2 = LLMTestCase(input="Research", actual_output=non_compliant_output)

        score2 = metric.measure(test_case2)
        assert score2 < 0.9
        assert not metric.is_successful()

        # Verify state was updated
        assert metric.score == score2
        assert metric.score != score1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
