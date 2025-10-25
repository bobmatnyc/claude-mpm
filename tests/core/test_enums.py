"""
Comprehensive unit tests for claude-mpm enum system.

Tests all 6 core enums with focus on:
- Value integrity and uniqueness
- String conversion and comparison
- Backward compatibility with magic strings
- Special methods (normalize, etc.)
- Edge cases and error handling
"""

import pytest

from src.claude_mpm.core.enums import (
    AgentCategory,
    ModelTier,
    OperationResult,
    OutputFormat,
    ServiceState,
    ValidationSeverity,
)


class TestOperationResult:
    """Tests for OperationResult enum."""

    def test_all_values_exist(self):
        """Verify all expected operation result values are defined."""
        expected_values = [
            "success",
            "error",
            "failed",
            "pending",
            "completed",
            "timeout",
            "cancelled",
            "context_ready",
            "skipped",
            "retry",
            "partial",
            "unknown",
        ]
        for value in expected_values:
            assert any(v.value == value for v in OperationResult)

    def test_string_conversion(self):
        """Test that enum values convert to expected strings."""
        assert str(OperationResult.SUCCESS) == "success"
        assert str(OperationResult.ERROR) == "error"
        assert str(OperationResult.FAILED) == "failed"
        assert str(OperationResult.PENDING) == "pending"

    def test_equality_with_strings(self):
        """Test that enums compare equal to their string values."""
        assert OperationResult.SUCCESS == "success"
        assert OperationResult.ERROR == "error"
        assert OperationResult.COMPLETED == "completed"

    def test_value_uniqueness(self):
        """Ensure all OperationResult values are unique."""
        values = [v.value for v in OperationResult]
        assert len(values) == len(set(values))

    def test_lowercase_values(self):
        """Verify all values are lowercase for consistency."""
        for result in OperationResult:
            assert result.value == result.value.lower()

    def test_membership(self):
        """Test enum membership checks."""
        assert OperationResult.SUCCESS in OperationResult
        assert OperationResult.SUCCESS.value == "success"

    def test_iteration(self):
        """Verify enum can be iterated."""
        results = list(OperationResult)
        assert len(results) == 13  # Updated in Phase 3C (added ROLLBACK)
        assert OperationResult.SUCCESS in results
        assert OperationResult.ROLLBACK in results


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_all_formats_exist(self):
        """Verify all expected output formats are defined."""
        expected_formats = [
            "json",
            "yaml",
            "text",
            "markdown",
            "raw",
            "table",
            "csv",
            "html",
            "xml",
        ]
        for format_type in expected_formats:
            assert any(f.value == format_type for f in OutputFormat)

    def test_string_conversion(self):
        """Test format enum string conversion."""
        assert str(OutputFormat.JSON) == "json"
        assert str(OutputFormat.YAML) == "yaml"
        assert str(OutputFormat.TEXT) == "text"
        assert str(OutputFormat.TABLE) == "table"

    def test_equality_with_strings(self):
        """Test format enum equality with string literals."""
        assert OutputFormat.JSON == "json"
        assert OutputFormat.YAML == "yaml"
        assert OutputFormat.MARKDOWN == "markdown"

    def test_case_insensitive_comparison(self):
        """Test that format comparison handles case variations."""
        # Using .lower() for comparison (pattern from migrations)
        assert str(OutputFormat.JSON).lower() == "json"
        assert str(OutputFormat.YAML).lower() == "yaml"

    def test_common_formats_present(self):
        """Verify most commonly used formats exist."""
        assert OutputFormat.JSON
        assert OutputFormat.YAML
        assert OutputFormat.TEXT
        assert OutputFormat.TABLE

    def test_structured_formats(self):
        """Test identification of structured formats (JSON/YAML)."""
        structured = [OutputFormat.JSON, OutputFormat.YAML]
        for fmt in structured:
            assert fmt in [OutputFormat.JSON, OutputFormat.YAML]

    def test_value_uniqueness(self):
        """Ensure all OutputFormat values are unique."""
        values = [f.value for f in OutputFormat]
        assert len(values) == len(set(values))

    def test_iteration(self):
        """Verify enum can be iterated."""
        formats = list(OutputFormat)
        assert len(formats) == 9


class TestServiceState:
    """Tests for ServiceState enum."""

    def test_all_states_exist(self):
        """Verify all expected service states are defined."""
        expected_states = [
            "stopped",
            "starting",
            "running",
            "stopping",
            "restarting",
            "error",
            "unknown",
            "degraded",
            "idle",
        ]
        for state in expected_states:
            assert any(s.value == state for s in ServiceState)

    def test_lifecycle_states(self):
        """Test primary lifecycle states."""
        assert ServiceState.STOPPED
        assert ServiceState.STARTING
        assert ServiceState.RUNNING
        assert ServiceState.STOPPING

    def test_error_states(self):
        """Test error and unknown states."""
        assert ServiceState.ERROR
        assert ServiceState.UNKNOWN
        assert ServiceState.DEGRADED

    def test_string_conversion(self):
        """Test state enum string conversion."""
        assert str(ServiceState.RUNNING) == "running"
        assert str(ServiceState.STOPPED) == "stopped"
        assert str(ServiceState.ERROR) == "error"

    def test_equality_with_strings(self):
        """Test state enum equality with string literals."""
        assert ServiceState.RUNNING == "running"
        assert ServiceState.STOPPED == "stopped"
        assert ServiceState.STARTING == "starting"

    def test_value_uniqueness(self):
        """Ensure all ServiceState values are unique."""
        values = [s.value for s in ServiceState]
        assert len(values) == len(set(values))

    def test_iteration(self):
        """Verify enum can be iterated."""
        states = list(ServiceState)
        assert len(states) == 9


class TestValidationSeverity:
    """Tests for ValidationSeverity enum."""

    def test_all_severities_exist(self):
        """Verify all expected severity levels are defined."""
        expected_severities = ["info", "warning", "error", "critical", "debug"]
        for severity in expected_severities:
            assert any(s.value == severity for s in ValidationSeverity)

    def test_severity_hierarchy(self):
        """Test that all severity levels exist in logical order."""
        severities = [
            ValidationSeverity.DEBUG,
            ValidationSeverity.INFO,
            ValidationSeverity.WARNING,
            ValidationSeverity.ERROR,
            ValidationSeverity.CRITICAL,
        ]
        assert len(severities) == 5

    def test_string_conversion(self):
        """Test severity enum string conversion."""
        assert str(ValidationSeverity.INFO) == "info"
        assert str(ValidationSeverity.ERROR) == "error"
        assert str(ValidationSeverity.CRITICAL) == "critical"

    def test_equality_with_strings(self):
        """Test severity enum equality with string literals."""
        assert ValidationSeverity.INFO == "info"
        assert ValidationSeverity.WARNING == "warning"
        assert ValidationSeverity.ERROR == "error"

    def test_value_uniqueness(self):
        """Ensure all ValidationSeverity values are unique."""
        values = [s.value for s in ValidationSeverity]
        assert len(values) == len(set(values))

    def test_iteration(self):
        """Verify enum can be iterated."""
        severities = list(ValidationSeverity)
        assert len(severities) == 5


class TestModelTier:
    """Tests for ModelTier enum."""

    def test_tier_names_exist(self):
        """Verify simplified tier names exist."""
        assert ModelTier.OPUS
        assert ModelTier.SONNET
        assert ModelTier.HAIKU

    def test_full_identifiers_exist(self):
        """Verify full model identifiers exist."""
        # Claude 4.x
        assert ModelTier.OPUS_4
        assert ModelTier.SONNET_4
        assert ModelTier.SONNET_4_5

        # Claude 3.x
        assert ModelTier.OPUS_3
        assert ModelTier.SONNET_3_5
        assert ModelTier.HAIKU_3

    def test_tier_name_values(self):
        """Test that tier names have correct values."""
        assert ModelTier.OPUS.value == "opus"
        assert ModelTier.SONNET.value == "sonnet"
        assert ModelTier.HAIKU.value == "haiku"

    def test_full_identifier_values(self):
        """Test that full identifiers have correct values."""
        assert ModelTier.OPUS_4.value == "claude-opus-4-20250514"
        assert ModelTier.SONNET_4.value == "claude-sonnet-4-20250514"
        assert ModelTier.HAIKU_3.value == "claude-3-haiku-20240307"

    def test_normalize_tier_names(self):
        """Test normalize method with tier names."""
        assert ModelTier.normalize("opus") == ModelTier.OPUS
        assert ModelTier.normalize("sonnet") == ModelTier.SONNET
        assert ModelTier.normalize("haiku") == ModelTier.HAIKU

    def test_normalize_uppercase(self):
        """Test normalize handles uppercase input."""
        assert ModelTier.normalize("OPUS") == ModelTier.OPUS
        assert ModelTier.normalize("SONNET") == ModelTier.SONNET
        assert ModelTier.normalize("Haiku") == ModelTier.HAIKU

    def test_normalize_full_identifiers(self):
        """Test normalize with full model identifiers."""
        assert ModelTier.normalize("claude-opus-4-20250514") == ModelTier.OPUS_4
        assert ModelTier.normalize("claude-sonnet-4-20250514") == ModelTier.SONNET_4
        assert ModelTier.normalize("claude-3-haiku-20240307") == ModelTier.HAIKU_3

    def test_normalize_partial_matches(self):
        """Test normalize extracts tier from partial strings."""
        assert ModelTier.normalize("claude-opus") == ModelTier.OPUS
        assert ModelTier.normalize("sonnet-latest") == ModelTier.SONNET
        assert ModelTier.normalize("some-haiku-version") == ModelTier.HAIKU

    def test_normalize_whitespace(self):
        """Test normalize handles whitespace."""
        assert ModelTier.normalize("  opus  ") == ModelTier.OPUS
        assert ModelTier.normalize("\nsonnet\t") == ModelTier.SONNET

    def test_normalize_unknown_defaults_to_sonnet(self):
        """Test normalize returns SONNET for unknown models."""
        assert ModelTier.normalize("unknown-model") == ModelTier.SONNET
        assert ModelTier.normalize("random-text") == ModelTier.SONNET
        assert ModelTier.normalize("") == ModelTier.SONNET

    def test_value_uniqueness(self):
        """Ensure all ModelTier values are unique."""
        values = [t.value for t in ModelTier]
        assert len(values) == len(set(values))

    def test_iteration(self):
        """Verify enum can be iterated."""
        tiers = list(ModelTier)
        assert len(tiers) == 9


class TestAgentCategory:
    """Tests for AgentCategory enum."""

    def test_all_categories_exist(self):
        """Verify all expected agent categories are defined."""
        expected_categories = [
            # Core categories
            "engineering",
            "research",
            "analysis",
            # Quality and Testing
            "quality",
            "qa",
            "security",
            # Operations
            "operations",
            "infrastructure",
            # Documentation and Content
            "documentation",
            "content",
            # Data
            "data",
            # Specialized
            "optimization",
            "specialized",
            "system",
            # Management
            "project-management",
            "product",
            # Legacy and General
            "version_control",
            "design",
            "general",
            "custom",
        ]
        for category in expected_categories:
            assert any(c.value == category for c in AgentCategory), f"Category '{category}' not found in AgentCategory enum"

    def test_core_categories(self):
        """Test core agent categories exist."""
        assert AgentCategory.RESEARCH
        assert AgentCategory.ENGINEERING
        assert AgentCategory.QA
        assert AgentCategory.SECURITY

    def test_support_categories(self):
        """Test support categories exist."""
        assert AgentCategory.DOCUMENTATION
        assert AgentCategory.OPERATIONS
        assert AgentCategory.VERSION_CONTROL

    def test_specialized_categories(self):
        """Test specialized categories exist."""
        assert AgentCategory.DATA
        assert AgentCategory.PROJECT_MANAGEMENT
        assert AgentCategory.DESIGN

    def test_fallback_categories(self):
        """Test fallback categories exist."""
        assert AgentCategory.GENERAL
        assert AgentCategory.CUSTOM

    def test_string_conversion(self):
        """Test category enum string conversion."""
        assert str(AgentCategory.RESEARCH) == "research"
        assert str(AgentCategory.ENGINEERING) == "engineering"
        assert str(AgentCategory.QA) == "qa"

    def test_equality_with_strings(self):
        """Test category enum equality with string literals."""
        assert AgentCategory.RESEARCH == "research"
        assert AgentCategory.ENGINEERING == "engineering"
        assert AgentCategory.VERSION_CONTROL == "version_control"

    def test_value_uniqueness(self):
        """Ensure all AgentCategory values are unique."""
        values = [c.value for c in AgentCategory]
        assert len(values) == len(set(values))

    def test_iteration(self):
        """Verify enum can be iterated."""
        categories = list(AgentCategory)
        assert len(categories) == 20  # Updated in Phase 3C (expanded from 12 to 20 categories)


class TestEnumInteroperability:
    """Tests for cross-enum functionality and backward compatibility."""

    def test_all_enums_are_str_enum(self):
        """Verify all enums inherit from StrEnum."""
        # StrEnum automatically makes values strings
        assert isinstance(OperationResult.SUCCESS, str)
        assert isinstance(OutputFormat.JSON, str)
        assert isinstance(ServiceState.RUNNING, str)
        assert isinstance(ValidationSeverity.ERROR, str)
        assert isinstance(ModelTier.OPUS, str)
        assert isinstance(AgentCategory.ENGINEERING, str)

    def test_backward_compatibility_with_magic_strings(self):
        """Test that enums work in place of old magic strings."""
        # Old code: if status == "success"
        # New code: if status == OperationResult.SUCCESS
        status = OperationResult.SUCCESS
        assert status == "success"

        # Old code: format_type in ["json", "yaml"]
        # New code: format_type in [OutputFormat.JSON, OutputFormat.YAML]
        format_type = OutputFormat.JSON
        assert format_type in ["json", "yaml"]

    def test_enum_in_dict_keys(self):
        """Test that enums can be used as dict keys."""
        result_map = {
            OperationResult.SUCCESS: "✓",
            OperationResult.ERROR: "✗",
        }
        assert result_map[OperationResult.SUCCESS] == "✓"
        assert result_map[OperationResult.ERROR] == "✗"

    def test_enum_in_dict_values(self):
        """Test that enums work as dict values."""
        config = {
            "format": OutputFormat.JSON,
            "state": ServiceState.RUNNING,
            "severity": ValidationSeverity.WARNING,
        }
        assert config["format"] == "json"
        assert config["state"] == "running"
        assert config["severity"] == "warning"

    def test_enum_in_sets(self):
        """Test that enums work in sets."""
        structured_formats = {OutputFormat.JSON, OutputFormat.YAML}
        assert OutputFormat.JSON in structured_formats
        assert OutputFormat.TEXT not in structured_formats

    def test_enum_string_concatenation(self):
        """Test that enums concatenate with strings."""
        result = OperationResult.SUCCESS
        message = f"Operation {result}"
        assert message == "Operation success"

    def test_enum_case_handling(self):
        """Test case sensitivity and normalization."""
        # Enums are case-sensitive by value
        assert OperationResult.SUCCESS.value == "success"
        assert str(OutputFormat.JSON).lower() == "json"

        # But ModelTier.normalize handles case
        assert ModelTier.normalize("OPUS") == ModelTier.OPUS


class TestEnumDocstrings:
    """Tests to verify enum documentation is present."""

    def test_operation_result_has_docstring(self):
        """Verify OperationResult has class docstring."""
        assert OperationResult.__doc__ is not None
        assert len(OperationResult.__doc__) > 0

    def test_output_format_has_docstring(self):
        """Verify OutputFormat has class docstring."""
        assert OutputFormat.__doc__ is not None
        assert len(OutputFormat.__doc__) > 0

    def test_service_state_has_docstring(self):
        """Verify ServiceState has class docstring."""
        assert ServiceState.__doc__ is not None
        assert len(ServiceState.__doc__) > 0

    def test_model_tier_has_docstring(self):
        """Verify ModelTier has class docstring."""
        assert ModelTier.__doc__ is not None
        assert len(ModelTier.__doc__) > 0

    def test_model_tier_normalize_has_docstring(self):
        """Verify ModelTier.normalize method has docstring."""
        assert ModelTier.normalize.__doc__ is not None
        assert "normalize" in ModelTier.normalize.__doc__.lower()


class TestEnumEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_string_comparisons(self):
        """Test enum behavior with empty strings."""
        assert OperationResult.SUCCESS != ""
        assert OutputFormat.TEXT != ""

    def test_none_comparisons(self):
        """Test enum behavior with None."""
        assert OperationResult.SUCCESS is not None
        assert OperationResult.SUCCESS != None  # noqa: E711

    def test_model_tier_normalize_with_empty_string(self):
        """Test ModelTier.normalize with empty string."""
        result = ModelTier.normalize("")
        assert result == ModelTier.SONNET  # Default fallback

    def test_model_tier_normalize_with_spaces(self):
        """Test ModelTier.normalize with only spaces."""
        result = ModelTier.normalize("   ")
        assert result == ModelTier.SONNET  # Default fallback

    def test_enum_boolean_context(self):
        """Test that enums are truthy."""
        assert OperationResult.SUCCESS
        assert bool(OutputFormat.JSON)
        assert bool(ServiceState.RUNNING)

    def test_enum_length(self):
        """Test that enum values have expected lengths."""
        assert len(OperationResult.SUCCESS) == len("success")
        assert len(OutputFormat.JSON) == len("json")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
