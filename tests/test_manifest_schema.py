"""
tests/test_manifest_schema.py — Unit tests for the manifest JSON schema module.

WHAT: Exercises ``validate_manifest`` against the canonical schema, confirming
that valid minimal and full manifests pass validation and that invalid manifests
raise ``ManifestValidationError`` with informative messages.

WHY: The schema is the contract boundary.  These tests pin the exact validation
behaviour so changes to the schema produce explicit test failures, not silent
regressions.

References
----------
SPEC-MANIFEST-03~1 : docs/specs/manifest.md#SPEC-MANIFEST-03~1
"""

from __future__ import annotations

import pytest

from claude_mpm.manifest.schema import (
    MANIFEST_SCHEMA,
    ManifestValidationError,
    validate_manifest,
)

# ===========================================================================
# Valid manifests
# ===========================================================================


class TestValidManifests:
    """Manifests that must pass validation without raising."""

    def test_minimal_manifest_passes(self) -> None:
        validate_manifest({"version": "1.0"})

    def test_full_manifest_passes(self) -> None:
        validate_manifest(
            {
                "version": "1.0",
                "extends": "default",
                "agents": {
                    "engineer": {"model": "sonnet", "color": "blue"},
                },
                "hooks": {
                    "PreToolUse": ["./hooks/pre.sh"],
                    "Stop": ["./hooks/stop.sh"],
                },
                "settings": {
                    "permissions": {"additionalDirectories": ["~/shared"]},
                },
                "setup": {
                    "services": ["kuzu-memory", "mcp-ticketer"],
                },
            }
        )

    def test_manifest_with_only_extends(self) -> None:
        validate_manifest({"version": "1.0", "extends": "enterprise"})

    def test_manifest_with_only_agents(self) -> None:
        validate_manifest({"version": "1.0", "agents": {}})

    def test_manifest_with_empty_setup(self) -> None:
        validate_manifest({"version": "1.0", "setup": {}})

    def test_manifest_with_empty_services_array(self) -> None:
        validate_manifest({"version": "1.0", "setup": {"services": []}})

    def test_unknown_top_level_key_is_allowed(self) -> None:
        """additionalProperties is True — unknown keys must not fail validation."""
        validate_manifest({"version": "1.0", "future_key": "some-value"})

    def test_agent_with_arbitrary_fields(self) -> None:
        """Agent objects accept arbitrary fields (MPM-proprietary + native)."""
        validate_manifest(
            {
                "version": "1.0",
                "agents": {
                    "eng": {
                        "model": "sonnet",
                        "resource_tier": "tier2",
                        "max_tokens": 8192,
                        "custom_field": True,
                    }
                },
            }
        )


# ===========================================================================
# Invalid manifests — required fields
# ===========================================================================


class TestMissingRequiredFields:
    """Manifests missing required fields must raise ManifestValidationError."""

    def test_missing_version_fails(self) -> None:
        with pytest.raises(ManifestValidationError) as exc_info:
            validate_manifest({})
        err = exc_info.value
        assert "version" in err.message or "version" in err.path

    def test_empty_dict_fails(self) -> None:
        with pytest.raises(ManifestValidationError):
            validate_manifest({})


# ===========================================================================
# Invalid manifests — wrong version
# ===========================================================================


class TestWrongVersion:
    """Only version '1.0' is valid."""

    def test_wrong_version_string_fails(self) -> None:
        with pytest.raises(ManifestValidationError) as exc_info:
            validate_manifest({"version": "2.0"})
        err = exc_info.value
        assert "version" in err.path or "2.0" in err.message

    def test_integer_version_fails(self) -> None:
        with pytest.raises(ManifestValidationError):
            validate_manifest({"version": 1})

    def test_null_version_fails(self) -> None:
        with pytest.raises(ManifestValidationError):
            validate_manifest({"version": None})

    def test_empty_version_string_fails(self) -> None:
        with pytest.raises(ManifestValidationError):
            validate_manifest({"version": ""})


# ===========================================================================
# Invalid manifests — malformed sub-structures
# ===========================================================================


class TestMalformedSubStructures:
    """Schema violations in nested keys must raise ManifestValidationError."""

    def test_setup_services_not_array_fails(self) -> None:
        with pytest.raises(ManifestValidationError):
            validate_manifest({"version": "1.0", "setup": {"services": "not-an-array"}})

    def test_setup_services_array_of_non_strings_fails(self) -> None:
        with pytest.raises(ManifestValidationError):
            validate_manifest({"version": "1.0", "setup": {"services": [1, 2, 3]}})

    def test_agents_value_not_object_fails(self) -> None:
        with pytest.raises(ManifestValidationError):
            validate_manifest({"version": "1.0", "agents": {"eng": "not-an-object"}})

    def test_hooks_value_not_array_fails(self) -> None:
        with pytest.raises(ManifestValidationError):
            validate_manifest(
                {"version": "1.0", "hooks": {"PreToolUse": "not-an-array"}}
            )

    def test_hooks_array_of_non_strings_fails(self) -> None:
        with pytest.raises(ManifestValidationError):
            validate_manifest({"version": "1.0", "hooks": {"PreToolUse": [42]}})

    def test_extends_empty_string_fails(self) -> None:
        with pytest.raises(ManifestValidationError):
            validate_manifest({"version": "1.0", "extends": ""})

    def test_extends_not_string_fails(self) -> None:
        with pytest.raises(ManifestValidationError):
            validate_manifest({"version": "1.0", "extends": 123})


# ===========================================================================
# ManifestValidationError attributes
# ===========================================================================


class TestManifestValidationErrorAttributes:
    """The exception must carry path and message attributes."""

    def test_error_has_path_attribute(self) -> None:
        with pytest.raises(ManifestValidationError) as exc_info:
            validate_manifest({})
        err = exc_info.value
        assert hasattr(err, "path")
        assert isinstance(err.path, str)

    def test_error_has_message_attribute(self) -> None:
        with pytest.raises(ManifestValidationError) as exc_info:
            validate_manifest({})
        err = exc_info.value
        assert hasattr(err, "message")
        assert isinstance(err.message, str)
        assert len(err.message) > 0

    def test_error_str_contains_path_and_message(self) -> None:
        with pytest.raises(ManifestValidationError) as exc_info:
            validate_manifest({"version": "2.0"})
        err = exc_info.value
        assert err.path in str(err)


# ===========================================================================
# Schema dict structure
# ===========================================================================


class TestSchemaDict:
    """MANIFEST_SCHEMA itself must be well-formed."""

    def test_schema_is_dict(self) -> None:
        assert isinstance(MANIFEST_SCHEMA, dict)

    def test_schema_has_required_key(self) -> None:
        assert "required" in MANIFEST_SCHEMA
        assert "version" in MANIFEST_SCHEMA["required"]

    def test_schema_allows_additional_properties(self) -> None:
        assert MANIFEST_SCHEMA.get("additionalProperties") is True

    def test_schema_has_version_enum(self) -> None:
        version_schema = MANIFEST_SCHEMA["properties"]["version"]
        assert "1.0" in version_schema["enum"]
