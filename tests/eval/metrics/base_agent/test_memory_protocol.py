"""
Unit tests for MemoryProtocolMetric.

Tests cover:
- JSON format validation (fenced blocks, raw JSON, invalid JSON)
- Required fields presence and type checking
- Memory capture appropriateness (triggers, user-specific, obvious facts)
- Memory quality (conciseness, project-specificity, duplicates)
- Edge cases and error handling
"""

import pytest
from deepeval.test_case import LLMTestCase

from .memory_protocol_metric import (
    MemoryProtocolMetric,
    create_memory_protocol_metric,
)


class TestMemoryProtocolMetric:
    """Test suite for MemoryProtocolMetric."""

    # ========================================================================
    # PERFECT COMPLIANCE TESTS
    # ========================================================================

    def test_perfect_compliance_with_memory_trigger(self):
        """Test perfect compliance when user explicitly requests memory."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Remember that this project uses pytest for testing",
            actual_output='''I've noted that information.

```json
{
    "task_completed": true,
    "instructions": "Remember testing framework preference",
    "results": "Noted pytest as the testing framework",
    "files_modified": [],
    "tools_used": [],
    "remember": ["Project uses pytest for testing"]
}
```'''
        )

        score = metric.measure(test_case)
        assert abs(score - 1.0) < 0.01, f"Expected perfect score, got {score}"
        assert metric.is_successful()
        assert "Perfect memory protocol compliance" in metric.reason

    def test_perfect_compliance_no_memory_trigger(self):
        """Test perfect compliance when no memory trigger present."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="What is the current configuration?",
            actual_output='''The configuration is set to debug mode.

```json
{
    "task_completed": true,
    "instructions": "Query current configuration",
    "results": "Configuration: debug mode enabled",
    "files_modified": [],
    "tools_used": ["Read"],
    "remember": null
}
```'''
        )

        score = metric.measure(test_case)
        # No trigger, optional memory, should get ~0.925 (0.3 + 0.3 + 0.175 + 0.15)
        # (json=1.0*0.3, fields=1.0*0.3, capture=0.7*0.25, quality=1.0*0.15)
        assert score >= 0.9, f"Expected high score without trigger, got {score}"
        assert metric.is_successful() or score >= 0.9

    # ========================================================================
    # JSON FORMAT TESTS
    # ========================================================================

    def test_json_format_fenced_block(self):
        """Test JSON extraction from fenced code block."""
        metric = MemoryProtocolMetric(threshold=0.3)

        test_case = LLMTestCase(
            input="Test request",
            actual_output='''Response text.

```json
{
    "task_completed": true,
    "instructions": "Test",
    "results": "Done",
    "files_modified": [],
    "tools_used": [],
    "remember": null
}
```'''
        )

        score = metric.measure(test_case)
        # Should score full points for JSON format (30%)
        assert score >= 0.3, f"JSON format should score, got {score}"
        assert metric.is_successful()

    def test_json_format_raw_block(self):
        """Test JSON extraction from raw JSON (no fencing)."""
        metric = MemoryProtocolMetric(threshold=0.3)

        test_case = LLMTestCase(
            input="Test request",
            actual_output='''Response text.

{
    "task_completed": true,
    "instructions": "Test",
    "results": "Done",
    "files_modified": [],
    "tools_used": [],
    "remember": null
}'''
        )

        score = metric.measure(test_case)
        # Should extract raw JSON and score
        assert score >= 0.3, f"Raw JSON should be extracted, got {score}"
        assert metric.is_successful()

    def test_json_format_invalid_json(self):
        """Test handling of invalid JSON."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Test request",
            actual_output='''Response text.

```json
{
    "task_completed": true,
    "instructions": "Test",
    "results": "Done",
    "files_modified": [],
    "tools_used": []
    // Missing remember field and trailing comma
}
```'''
        )

        score = metric.measure(test_case)
        # Invalid JSON should score 0.0
        assert score == 0.0, f"Invalid JSON should score 0.0, got {score}"
        assert not metric.is_successful()
        assert "No valid JSON block" in metric.reason

    def test_json_format_no_json_block(self):
        """Test handling when no JSON block present."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Test request",
            actual_output="Response text without any JSON block."
        )

        score = metric.measure(test_case)
        assert score == 0.0, f"No JSON should score 0.0, got {score}"
        assert not metric.is_successful()
        assert "No valid JSON block" in metric.reason

    # ========================================================================
    # REQUIRED FIELDS TESTS
    # ========================================================================

    def test_required_fields_all_present_correct_types(self):
        """Test all required fields present with correct types."""
        metric = MemoryProtocolMetric(threshold=0.6)

        test_case = LLMTestCase(
            input="Test",
            actual_output='''Done.

```json
{
    "task_completed": true,
    "instructions": "Test instruction",
    "results": "Test results",
    "files_modified": ["file1.py", "file2.py"],
    "tools_used": ["Edit", "Read"],
    "remember": ["Important fact"]
}
```'''
        )

        score = metric.measure(test_case)
        # Should score full points for fields (30%)
        assert score >= 0.6, f"All fields correct should score high, got {score}"
        assert metric.is_successful()

    def test_required_fields_missing_field(self):
        """Test detection of missing required field."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Test",
            actual_output='''Done.

```json
{
    "task_completed": true,
    "instructions": "Test",
    "results": "Done",
    "files_modified": [],
    "tools_used": []
}
```'''
        )

        score = metric.measure(test_case)
        # Missing 'remember' field should reduce score
        assert score < 1.0, f"Missing field should reduce score, got {score}"
        assert not metric.is_successful()
        assert "Missing required fields: remember" in metric.reason

    def test_required_fields_wrong_type(self):
        """Test detection of wrong field type."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Test",
            actual_output='''Done.

```json
{
    "task_completed": "yes",
    "instructions": "Test",
    "results": "Done",
    "files_modified": "none",
    "tools_used": [],
    "remember": null
}
```'''
        )

        score = metric.measure(test_case)
        # Wrong types should reduce score
        assert score < 1.0, f"Wrong types should reduce score, got {score}"
        assert not metric.is_successful()
        assert "Type mismatches" in metric.reason

    def test_required_fields_remember_null_allowed(self):
        """Test that remember field can be null."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="What is X?",
            actual_output='''X is Y.

```json
{
    "task_completed": true,
    "instructions": "Query X",
    "results": "X is Y",
    "files_modified": [],
    "tools_used": [],
    "remember": null
}
```'''
        )

        score = metric.measure(test_case)
        # remember=null is valid (list or None)
        # Should get high score (json=0.3, fields=0.3, capture=0.175, quality=0.15)
        assert score >= 0.9, f"remember=null should be valid, got {score}"

    def test_required_fields_remember_list_allowed(self):
        """Test that remember field can be a list."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Remember this fact",
            actual_output='''Noted.

```json
{
    "task_completed": true,
    "instructions": "Remember fact",
    "results": "Fact noted",
    "files_modified": [],
    "tools_used": [],
    "remember": ["This is the fact"]
}
```'''
        )

        score = metric.measure(test_case)
        # remember=[...] is valid
        assert abs(score - 1.0) < 0.01, f"remember=[...] should be valid, got {score}"
        assert metric.is_successful()

    # ========================================================================
    # MEMORY CAPTURE TESTS
    # ========================================================================

    def test_memory_capture_with_trigger_captured(self):
        """Test memory capture when user explicitly requests."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Don't forget that we use TypeScript for backend",
            actual_output='''I'll remember that.

```json
{
    "task_completed": true,
    "instructions": "Remember tech stack",
    "results": "Noted TypeScript for backend",
    "files_modified": [],
    "tools_used": [],
    "remember": ["Backend uses TypeScript"]
}
```'''
        )

        score = metric.measure(test_case)
        assert abs(score - 1.0) < 0.01, f"Memory trigger should be captured, got {score}"
        assert metric.is_successful()

    def test_memory_capture_with_trigger_not_captured(self):
        """Test failure when memory trigger present but not captured."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Remember that this is important",
            actual_output='''Okay.

```json
{
    "task_completed": true,
    "instructions": "Acknowledge",
    "results": "Acknowledged",
    "files_modified": [],
    "tools_used": [],
    "remember": null
}
```'''
        )

        score = metric.measure(test_case)
        # Should fail memory capture component (0% of 25%)
        assert score < 1.0, f"Missing memory capture should reduce score, got {score}"
        assert not metric.is_successful()
        assert "Memory trigger detected" in metric.reason

    def test_memory_capture_user_specific_should_not_capture(self):
        """Test that user-specific preferences should not be captured."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="I prefer using tabs instead of spaces",
            actual_output='''Noted your preference.

```json
{
    "task_completed": true,
    "instructions": "Acknowledge user preference",
    "results": "Preference noted",
    "files_modified": [],
    "tools_used": [],
    "remember": null
}
```'''
        )

        score = metric.measure(test_case)
        # Should NOT capture user preference
        assert abs(score - 1.0) < 0.01, f"User preference should not be captured, got {score}"
        assert metric.is_successful()

    def test_memory_capture_user_specific_incorrectly_captured(self):
        """Test failure when user-specific preference is captured."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="I like using single quotes for strings",
            actual_output='''Noted.

```json
{
    "task_completed": true,
    "instructions": "Remember preference",
    "results": "Preference stored",
    "files_modified": [],
    "tools_used": [],
    "remember": ["User prefers single quotes"]
}
```'''
        )

        score = metric.measure(test_case)
        # Should fail for capturing user-specific preference
        assert score < 1.0, f"User preference capture should reduce score, got {score}"
        assert not metric.is_successful()

    def test_memory_capture_obvious_fact_should_not_capture(self):
        """Test that obvious facts should not be captured."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="The code is in the src directory",
            actual_output='''Understood.

```json
{
    "task_completed": true,
    "instructions": "Acknowledge directory location",
    "results": "Code location noted",
    "files_modified": [],
    "tools_used": [],
    "remember": null
}
```'''
        )

        score = metric.measure(test_case)
        # Should NOT capture obvious fact
        assert abs(score - 1.0) < 0.01, f"Obvious fact should not be captured, got {score}"
        assert metric.is_successful()

    # ========================================================================
    # MEMORY QUALITY TESTS
    # ========================================================================

    def test_memory_quality_concise_entries(self):
        """Test memory quality with concise entries (<100 chars)."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Remember X and Y",
            actual_output='''Noted.

```json
{
    "task_completed": true,
    "instructions": "Remember facts",
    "results": "Facts stored",
    "files_modified": [],
    "tools_used": [],
    "remember": ["Fact X", "Fact Y"]
}
```'''
        )

        score = metric.measure(test_case)
        assert abs(score - 1.0) < 0.01, f"Concise entries should score perfectly, got {score}"
        assert metric.is_successful()

    def test_memory_quality_verbose_entries(self):
        """Test memory quality with verbose entries (>=100 chars)."""
        metric = MemoryProtocolMetric(threshold=1.0)

        verbose_entry = "A" * 150  # 150 chars

        test_case = LLMTestCase(
            input="Remember this",
            actual_output=f'''Noted.

```json
{{
    "task_completed": true,
    "instructions": "Remember",
    "results": "Stored",
    "files_modified": [],
    "tools_used": [],
    "remember": ["{verbose_entry}"]
}}
```'''
        )

        score = metric.measure(test_case)
        # Should reduce quality score due to verbosity
        assert score < 1.0, f"Verbose entries should reduce score, got {score}"
        assert "verbose entries" in metric.reason.lower()

    def test_memory_quality_generic_entries(self):
        """Test memory quality with generic (non-project-specific) entries."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Note that",
            actual_output='''Noted.

```json
{
    "task_completed": true,
    "instructions": "Remember",
    "results": "Stored",
    "files_modified": [],
    "tools_used": [],
    "remember": ["Always use best practices", "Never use global variables"]
}
```'''
        )

        score = metric.measure(test_case)
        # Should reduce quality score due to generic entries
        assert score < 1.0, f"Generic entries should reduce score, got {score}"
        assert "generic entries" in metric.reason.lower()

    def test_memory_quality_duplicate_entries(self):
        """Test memory quality with duplicate entries."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Remember this",
            actual_output='''Noted.

```json
{
    "task_completed": true,
    "instructions": "Remember",
    "results": "Stored",
    "files_modified": [],
    "tools_used": [],
    "remember": ["Project uses pytest", "Project uses pytest"]
}
```'''
        )

        score = metric.measure(test_case)
        # Should reduce quality score due to duplicates
        assert score < 1.0, f"Duplicate entries should reduce score, got {score}"
        assert "duplicate entries" in metric.reason.lower()

    def test_memory_quality_empty_remember_field(self):
        """Test memory quality when remember field is empty list."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="What is X?",
            actual_output='''X is Y.

```json
{
    "task_completed": true,
    "instructions": "Query",
    "results": "Answer",
    "files_modified": [],
    "tools_used": [],
    "remember": []
}
```'''
        )

        score = metric.measure(test_case)
        # Empty remember list should get full quality score (N/A)
        assert score >= 0.9, f"Empty remember should not reduce quality, got {score}"

    # ========================================================================
    # FACTORY FUNCTION TEST
    # ========================================================================

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_memory_protocol_metric(threshold=0.95)

        assert isinstance(metric, MemoryProtocolMetric)
        assert metric.threshold == 0.95

    # ========================================================================
    # EDGE CASES
    # ========================================================================

    def test_edge_case_multiple_json_blocks(self):
        """Test that only the last JSON block is used."""
        metric = MemoryProtocolMetric(threshold=1.0)

        test_case = LLMTestCase(
            input="Test",
            actual_output='''First response.

```json
{
    "task_completed": false,
    "instructions": "Wrong",
    "results": "Wrong",
    "files_modified": [],
    "tools_used": [],
    "remember": null
}
```

Second response.

```json
{
    "task_completed": true,
    "instructions": "Correct",
    "results": "Correct",
    "files_modified": [],
    "tools_used": [],
    "remember": null
}
```'''
        )

        score = metric.measure(test_case)
        # Should extract the last JSON block (within 2000 chars)
        assert score >= 0.9, f"Should use last JSON block, got {score}"

    def test_edge_case_json_in_middle_of_response(self):
        """Test JSON block not at the end of response."""
        metric = MemoryProtocolMetric(threshold=0.5)

        # Create response with JSON not in last 2000 chars
        filler_text = "A" * 2500

        test_case = LLMTestCase(
            input="Test",
            actual_output=f'''```json
{{
    "task_completed": true,
    "instructions": "Test",
    "results": "Done",
    "files_modified": [],
    "tools_used": [],
    "remember": null
}}
```

{filler_text}'''
        )

        score = metric.measure(test_case)
        # JSON too far from end, should not be found
        assert score == 0.0, f"JSON not at end should fail, got {score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
