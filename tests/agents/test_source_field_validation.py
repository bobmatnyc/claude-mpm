"""Tests for the `source` frontmatter field validation.

Verifies that the FrontmatterValidator in src/claude_mpm/agents/frontmatter_validator.py
correctly handles the `source` enum field (bundled | external).

Coverage:
- `source: bundled` is accepted (no errors)
- `source: external` is accepted (no errors)
- An invalid value (e.g. `source: vendor`) is a hard validation error
- Absent `source` field is valid (the field is optional)
"""

import pytest

from claude_mpm.agents.frontmatter_validator import FrontmatterValidator


@pytest.fixture
def validator() -> FrontmatterValidator:
    """Return a fresh FrontmatterValidator instance."""
    return FrontmatterValidator()


def _minimal_frontmatter(**extras) -> dict:
    """Return a minimal-but-valid frontmatter dict, optionally merged with extras."""
    base = {
        "name": "test-agent",
        "description": "A test agent for validation tests.",
        "version": "1.0.0",
        "model": "sonnet",
    }
    base.update(extras)
    return base


class TestSourceFieldAccepted:
    """Valid `source` values must not produce errors."""

    def test_source_bundled_accepted(self, validator: FrontmatterValidator) -> None:
        """source: bundled is a valid enum value — no errors."""
        fm = _minimal_frontmatter(source="bundled")
        result = validator.validate_and_correct(fm)

        assert not result.errors, f"Unexpected errors: {result.errors}"

    def test_source_external_accepted(self, validator: FrontmatterValidator) -> None:
        """source: external is a valid enum value — no errors."""
        fm = _minimal_frontmatter(source="external")
        result = validator.validate_and_correct(fm)

        assert not result.errors, f"Unexpected errors: {result.errors}"

    def test_source_absent_is_valid(self, validator: FrontmatterValidator) -> None:
        """Omitting `source` entirely must not trigger any errors (optional field)."""
        fm = _minimal_frontmatter()  # no source key
        assert "source" not in fm

        result = validator.validate_and_correct(fm)

        assert not result.errors, f"Unexpected errors: {result.errors}"

    def test_source_absent_preserves_corrected_frontmatter(
        self, validator: FrontmatterValidator
    ) -> None:
        """When `source` is absent, the corrected frontmatter must not inject it."""
        fm = _minimal_frontmatter()
        result = validator.validate_and_correct(fm)

        assert result.corrected_frontmatter is not None
        # source must not be fabricated if the author did not supply it
        assert "source" not in result.corrected_frontmatter


class TestSourceFieldRejected:
    """Invalid `source` values must produce a hard validation error."""

    def test_source_vendor_rejected(self, validator: FrontmatterValidator) -> None:
        """source: vendor is not a recognised enum value — must produce an error."""
        fm = _minimal_frontmatter(source="vendor")
        result = validator.validate_and_correct(fm)

        assert not result.is_valid
        assert any("source" in err.lower() for err in result.errors), (
            f"Expected an error mentioning 'source', got: {result.errors}"
        )

    def test_source_internal_rejected(self, validator: FrontmatterValidator) -> None:
        """source: internal is not a recognised value."""
        fm = _minimal_frontmatter(source="internal")
        result = validator.validate_and_correct(fm)

        assert not result.is_valid
        assert any("source" in err.lower() for err in result.errors)

    def test_source_empty_string_rejected(
        self, validator: FrontmatterValidator
    ) -> None:
        """source: '' (empty string) is not a valid enum value."""
        fm = _minimal_frontmatter(source="")
        result = validator.validate_and_correct(fm)

        assert not result.is_valid
        assert any("source" in err.lower() for err in result.errors)

    def test_source_integer_type_rejected(
        self, validator: FrontmatterValidator
    ) -> None:
        """source: 1 (non-string) must raise a type error, not silently pass."""
        fm = _minimal_frontmatter(source=1)
        result = validator.validate_and_correct(fm)

        assert not result.is_valid
        assert any("source" in err.lower() for err in result.errors)

    def test_source_error_message_mentions_valid_values(
        self, validator: FrontmatterValidator
    ) -> None:
        """Error message for an invalid source must name the allowed values."""
        fm = _minimal_frontmatter(source="vendor")
        result = validator.validate_and_correct(fm)

        error_text = " ".join(result.errors)
        # Both enum values must be named so contributors know what to use
        assert "bundled" in error_text, (
            f"Error should mention 'bundled'. Got: {result.errors}"
        )
        assert "external" in error_text, (
            f"Error should mention 'external'. Got: {result.errors}"
        )


class TestSourceFieldInCorrectedOutput:
    """The corrected frontmatter must preserve valid `source` values unchanged."""

    def test_bundled_preserved_in_corrected(
        self, validator: FrontmatterValidator
    ) -> None:
        """source: bundled must appear unchanged in the corrected frontmatter."""
        fm = _minimal_frontmatter(source="bundled")
        result = validator.validate_and_correct(fm)

        assert result.corrected_frontmatter is not None
        assert result.corrected_frontmatter.get("source") == "bundled"

    def test_external_preserved_in_corrected(
        self, validator: FrontmatterValidator
    ) -> None:
        """source: external must appear unchanged in the corrected frontmatter."""
        fm = _minimal_frontmatter(source="external")
        result = validator.validate_and_correct(fm)

        assert result.corrected_frontmatter is not None
        assert result.corrected_frontmatter.get("source") == "external"
