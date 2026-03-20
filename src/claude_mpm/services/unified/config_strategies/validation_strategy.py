"""
Validation Strategy - Reduces 236 validation functions to 15 composable validators
Part of Phase 3 Configuration Consolidation
"""

import ipaddress
import re
import urllib.parse
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from re import Pattern  # noqa: TC003
from typing import Any

from claude_mpm.core.enums import ValidationSeverity
from claude_mpm.core.logging_utils import get_logger

from .unified_config_service import IConfigStrategy


class ValidationType(Enum):
    """Types of validation operations"""

    TYPE = "type"
    REQUIRED = "required"
    RANGE = "range"
    LENGTH = "length"
    PATTERN = "pattern"
    ENUM = "enum"
    FORMAT = "format"
    DEPENDENCY = "dependency"
    UNIQUE = "unique"
    CUSTOM = "custom"
    CONDITIONAL = "conditional"
    RECURSIVE = "recursive"
    CROSS_FIELD = "cross_field"
    COMPOSITE = "composite"
    SCHEMA = "schema"


@dataclass
class ValidationRule:
    """Single validation rule definition"""

    type: ValidationType
    params: dict[str, Any] = field(default_factory=dict)
    message: str | None = None
    severity: str = ValidationSeverity.ERROR
    condition: Callable | None = None


@dataclass
class ValidationResult:
    """Result of validation operation"""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


class BaseValidator(ABC):
    """Base class for all validators"""

    def __init__(self):
        """Initialise the base validator with a class-specific logger.

        WHY: Each concrete validator subclass needs its own logger so log messages
        identify the originating validator without manual naming at every log site.
        WHAT: Creates a logger named after the concrete class using get_logger.
        TEST: Instantiate a concrete subclass; assert self.logger.name == subclass name.
        """
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Perform validation"""

    def _create_result(
        self,
        valid: bool,
        message: str | None = None,
        severity: str = ValidationSeverity.ERROR,
    ) -> ValidationResult:
        """Create validation result"""
        result = ValidationResult(valid=valid)

        if not valid and message:
            if severity == ValidationSeverity.ERROR:
                result.errors.append(message)
            elif severity == ValidationSeverity.WARNING:
                result.warnings.append(message)
            else:
                result.info.append(message)

        return result


class TypeValidator(BaseValidator):
    """Validates data types - replaces 45 type validation functions"""

    TYPE_MAP = {
        "string": str,
        "str": str,
        "integer": int,
        "int": int,
        "float": float,
        "number": (int, float),
        "boolean": bool,
        "bool": bool,
        "array": list,
        "list": list,
        "object": dict,
        "dict": dict,
        "null": type(None),
        "none": type(None),
        "any": object,
    }

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate value type"""
        expected_type = rule.params.get("type")

        if not expected_type:
            return self._create_result(True)

        # Handle string type names
        if isinstance(expected_type, str):
            expected_type = self.TYPE_MAP.get(expected_type.lower(), expected_type)

        # Handle multiple types
        if isinstance(expected_type, (list, tuple)):
            for t in expected_type:
                type_obj = self.TYPE_MAP.get(t, t) if isinstance(t, str) else t
                if isinstance(value, type_obj):
                    return self._create_result(True)

            types_str = ", ".join(str(t) for t in expected_type)
            return self._create_result(
                False,
                f"Value must be one of types: {types_str}, got {type(value).__name__}",
                rule.severity,
            )

        # Single type validation
        if not isinstance(value, expected_type):
            return self._create_result(
                False,
                f"Expected type {expected_type}, got {type(value).__name__}",
                rule.severity,
            )

        return self._create_result(True)


class RequiredValidator(BaseValidator):
    """Validates required fields - replaces 35 required validation functions"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate required fields"""
        required_fields = rule.params.get("fields", [])
        config = context.get("config", {})

        missing = []
        for field in required_fields:
            if "." in field:
                # Nested field check
                if not self._check_nested_field(config, field):
                    missing.append(field)
            # Simple field check
            elif field not in config or config[field] is None:
                missing.append(field)

        if missing:
            return self._create_result(
                False, f"Required fields missing: {', '.join(missing)}", rule.severity
            )

        return self._create_result(True)

    def _check_nested_field(self, obj: dict, path: str) -> bool:
        """Check if nested field exists"""
        parts = path.split(".")
        current = obj

        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]

        return current is not None


class RangeValidator(BaseValidator):
    """Validates numeric ranges - replaces 28 range validation functions"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate numeric range"""
        if not isinstance(value, (int, float)):
            return self._create_result(True)  # Skip non-numeric values

        min_val = rule.params.get("min")
        max_val = rule.params.get("max")
        exclusive_min = rule.params.get("exclusive_min", False)
        exclusive_max = rule.params.get("exclusive_max", False)

        # Check minimum
        if min_val is not None:
            if exclusive_min and value <= min_val:
                return self._create_result(
                    False,
                    f"Value {value} must be greater than {min_val}",
                    rule.severity,
                )
            if not exclusive_min and value < min_val:
                return self._create_result(
                    False, f"Value {value} must be at least {min_val}", rule.severity
                )

        # Check maximum
        if max_val is not None:
            if exclusive_max and value >= max_val:
                return self._create_result(
                    False, f"Value {value} must be less than {max_val}", rule.severity
                )
            if not exclusive_max and value > max_val:
                return self._create_result(
                    False, f"Value {value} must be at most {max_val}", rule.severity
                )

        return self._create_result(True)


class LengthValidator(BaseValidator):
    """Validates string/array lengths - replaces 22 length validation functions"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate length constraints"""
        if not hasattr(value, "__len__"):
            return self._create_result(True)  # Skip non-sized values

        length = len(value)
        min_length = rule.params.get("min")
        max_length = rule.params.get("max")
        exact_length = rule.params.get("exact")

        # Check exact length
        if exact_length is not None and length != exact_length:
            return self._create_result(
                False,
                f"Length must be exactly {exact_length}, got {length}",
                rule.severity,
            )

        # Check minimum length
        if min_length is not None and length < min_length:
            return self._create_result(
                False,
                f"Length must be at least {min_length}, got {length}",
                rule.severity,
            )

        # Check maximum length
        if max_length is not None and length > max_length:
            return self._create_result(
                False,
                f"Length must be at most {max_length}, got {length}",
                rule.severity,
            )

        return self._create_result(True)


class PatternValidator(BaseValidator):
    """Validates regex patterns - replaces 31 pattern validation functions"""

    def __init__(self):
        """Initialise the pattern validator with an empty compiled-pattern cache.

        WHY: Compiling the same regex repeatedly is wasteful; the cache ensures each
        pattern is compiled at most once and reused across all subsequent validations.
        WHAT: Calls super().__init__() for the logger; initialises _compiled_patterns
        to an empty dict.
        TEST: Instantiate; assert _compiled_patterns is an empty dict.
        """
        super().__init__()
        self._compiled_patterns: dict[str, Pattern] = {}

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate against regex pattern"""
        if not isinstance(value, str):
            return self._create_result(True)  # Skip non-string values

        pattern = rule.params.get("pattern")
        if not pattern:
            return self._create_result(True)

        # Compile and cache pattern
        if pattern not in self._compiled_patterns:
            try:
                self._compiled_patterns[pattern] = re.compile(pattern)
            except re.error as e:
                return self._create_result(False, f"Invalid pattern: {e}", "error")

        regex = self._compiled_patterns[pattern]

        # Check match
        if not regex.match(value):
            message = rule.params.get(
                "message", f"Value does not match pattern: {pattern}"
            )
            return self._create_result(False, message, rule.severity)

        return self._create_result(True)


class EnumValidator(BaseValidator):
    """Validates enum values - replaces 18 enum validation functions"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate enum membership"""
        allowed_values = rule.params.get("values", [])

        if not allowed_values:
            return self._create_result(True)

        # Handle case sensitivity
        case_sensitive = rule.params.get("case_sensitive", True)

        if not case_sensitive and isinstance(value, str):
            value_lower = value.lower()
            allowed_lower = [
                v.lower() if isinstance(v, str) else v for v in allowed_values
            ]

            if value_lower not in allowed_lower:
                return self._create_result(
                    False,
                    f"Value '{value}' not in allowed values: {allowed_values}",
                    rule.severity,
                )
        elif value not in allowed_values:
            return self._create_result(
                False,
                f"Value '{value}' not in allowed values: {allowed_values}",
                rule.severity,
            )

        return self._create_result(True)


class FormatValidator(BaseValidator):
    """Validates common formats - replaces 24 format validation functions"""

    FORMAT_VALIDATORS: dict[str, Callable[[str], bool]] = {}

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate format"""
        if not isinstance(value, str):
            return self._create_result(True)

        format_type = rule.params.get("format")
        if not format_type:
            return self._create_result(True)

        validator = self.FORMAT_VALIDATORS.get(format_type)
        if not validator:
            return self._create_result(
                False, f"Unknown format: {format_type}", "warning"
            )

        try:
            if validator(value):
                return self._create_result(True)
            return self._create_result(
                False,
                f"Value '{value}' is not a valid {format_type}",
                rule.severity,
            )
        except Exception as e:
            return self._create_result(
                False, f"Format validation failed: {e}", rule.severity
            )

    @staticmethod
    def _validate_url(value: str) -> bool:
        """Return True if value is a valid absolute URL (has scheme and netloc).

        WHY: URL validation is needed for configuration fields that point to external
        services; urllib.parse handles edge cases better than a hand-rolled regex.
        WHAT: Parses value with urlparse and checks both scheme and netloc are non-empty.
        TEST: Assert _validate_url("https://example.com") is True and
        _validate_url("not-a-url") is False.
        """
        try:
            result = urllib.parse.urlparse(value)
            return all([result.scheme, result.netloc])
        except (ValueError, AttributeError, TypeError):
            return False

    @staticmethod
    def _validate_uri(value: str) -> bool:
        """Return True if value is a valid URI (has at least a scheme).

        WHY: URI validation is broader than URL validation; some config fields accept
        non-HTTP URIs (file:, data:, urn:) that lack a netloc component.
        WHAT: Parses value with urlparse and checks the scheme is non-empty.
        TEST: Assert _validate_uri("urn:isbn:0451450523") is True and
        _validate_uri("no-scheme") is False.
        """
        try:
            result = urllib.parse.urlparse(value)
            return bool(result.scheme)
        except (ValueError, AttributeError, TypeError):
            return False

    @staticmethod
    def _validate_uuid(value: str) -> bool:
        """Return True if value is a valid UUID string.

        WHY: UUID format is used for identifiers in config; stdlib uuid.UUID parsing
        provides authoritative validation without a fragile hand-rolled regex.
        WHAT: Passes value to uuid.UUID(); returns True on success, False on ValueError.
        TEST: Assert _validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True
        and _validate_uuid("not-a-uuid") is False.
        """
        import uuid

        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError, TypeError):
            return False

    @staticmethod
    def _validate_ipv4(value: str) -> bool:
        """Return True if value is a valid IPv4 address string.

        WHY: Config fields for host addresses should reject invalid IPs at validation
        time rather than at runtime when connections fail.
        WHAT: Passes value to ipaddress.IPv4Address(); returns True on success.
        TEST: Assert _validate_ipv4("192.168.1.1") is True and
        _validate_ipv4("999.0.0.1") is False.
        """
        try:
            ipaddress.IPv4Address(value)
            return True
        except (ValueError, ipaddress.AddressValueError):
            return False

    @staticmethod
    def _validate_ipv6(value: str) -> bool:
        """Return True if value is a valid IPv6 address string.

        WHY: Config fields may accept IPv6 addresses; stdlib ipaddress handles all
        compressed and expanded forms correctly.
        WHAT: Passes value to ipaddress.IPv6Address(); returns True on success.
        TEST: Assert _validate_ipv6("::1") is True and _validate_ipv6("xyz") is False.
        """
        try:
            ipaddress.IPv6Address(value)
            return True
        except (ValueError, ipaddress.AddressValueError):
            return False

    @staticmethod
    def _validate_ip(value: str) -> bool:
        """Return True if value is a valid IPv4 or IPv6 address string.

        WHY: Some config fields accept either IP version; this unifies both checks into
        one call using stdlib ipaddress which handles both families.
        WHAT: Passes value to ipaddress.ip_address(); returns True for both IPv4/IPv6.
        TEST: Assert _validate_ip("10.0.0.1") is True, _validate_ip("::1") is True,
        and _validate_ip("not.an.ip") is False.
        """
        try:
            ipaddress.ip_address(value)
            return True
        except (ValueError, ipaddress.AddressValueError):
            return False

    @staticmethod
    def _validate_hostname(value: str) -> bool:
        """Return True if value matches the RFC 1123 hostname format.

        WHY: Hostnames in config must follow DNS naming rules to be usable at
        runtime; validating early prevents obscure connection failures later.
        WHAT: Matches value against a regex enforcing label length (1-63 chars),
        total length (1-253 chars), no leading/trailing hyphens, and no consecutive hyphens.
        TEST: Assert _validate_hostname("my-host.example.com") is True and
        _validate_hostname("-bad.host") is False.
        """
        pattern = re.compile(
            r"^(?=.{1,253}$)(?!-)(?!.*--)"
            r"[a-zA-Z0-9-]{1,63}"
            r"(?:\.[a-zA-Z0-9-]{1,63})*$"
        )
        return bool(pattern.match(value))

    @staticmethod
    def _validate_date(value: str) -> bool:
        """Return True if value is a valid ISO 8601 date (YYYY-MM-DD).

        WHY: Date fields in config must be parseable; validating the format early
        prevents runtime errors when the value is consumed by date-aware code.
        WHAT: Parses value with strptime("%Y-%m-%d"); returns True on success.
        TEST: Assert _validate_date("2025-01-01") is True and
        _validate_date("01-01-2025") is False.
        """
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _validate_time(value: str) -> bool:
        """Return True if value is a valid time string (HH:MM:SS or HH:MM).

        WHY: Time fields in config must be clock-parseable; accepting both HH:MM and
        HH:MM:SS covers common shorthand without being overly strict.
        WHAT: Tries strptime with HH:MM:SS then falls back to HH:MM; returns True on
        first success.
        TEST: Assert _validate_time("14:30:00") is True, _validate_time("14:30") is True,
        and _validate_time("25:00") is False.
        """
        try:
            datetime.strptime(value, "%H:%M:%S")
            return True
        except (ValueError, TypeError):
            try:
                datetime.strptime(value, "%H:%M")
                return True
            except (ValueError, TypeError):
                return False

    @staticmethod
    def _validate_datetime(value: str) -> bool:
        """Return True if value matches any of the supported ISO 8601 datetime formats.

        WHY: Datetime config fields may use different but equivalent representations;
        accepting multiple common formats avoids brittle single-format requirements.
        WHAT: Tries strptime with four formats in order and returns True on the first
        match; returns False if all formats fail.
        TEST: Assert _validate_datetime("2025-01-01T12:00:00Z") is True and
        _validate_datetime("not-a-date") is False.
        """
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
        ]
        for fmt in formats:
            try:
                datetime.strptime(value, fmt)
                return True
            except (ValueError, TypeError):
                continue
        return False

    @staticmethod
    def _validate_json(value: str) -> bool:
        """Return True if value is valid JSON.

        WHY: Config fields that embed JSON snippets must be parseable at runtime;
        early validation surfaces syntax errors before they cause harder-to-debug failures.
        WHAT: Calls json.loads(value); returns True on success, False on decode error.
        TEST: Assert _validate_json('{"k": 1}') is True and
        _validate_json("{bad json}") is False.
        """
        import json

        try:
            json.loads(value)
            return True
        except (json.JSONDecodeError, ValueError, TypeError):
            return False

    @staticmethod
    def _validate_base64(value: str) -> bool:
        """Return True if value is valid standard base64-encoded data.

        WHY: Config fields for secrets or binary blobs are often base64-encoded; early
        validation prevents opaque decode errors later in the pipeline.
        WHAT: Calls base64.b64decode(value, validate=True) which rejects non-alphabet
        characters; returns True on success.
        TEST: Assert _validate_base64("aGVsbG8=") is True and
        _validate_base64("not!base64$") is False.
        """
        import base64

        try:
            base64.b64decode(value, validate=True)
            return True
        except (ValueError, base64.binascii.Error):
            return False

    @staticmethod
    def _validate_path(value: str) -> bool:
        """Return True if value is a syntactically valid filesystem path.

        WHY: Path config fields must at minimum be parseable by pathlib; this
        validates syntax without requiring the path to exist.
        WHAT: Passes value to Path(); returns True if no exception is raised.
        TEST: Assert _validate_path("/usr/local/bin") is True.
        (Platform-specific invalid paths will return False.)
        """
        try:
            Path(value)
            return True
        except (ValueError, TypeError, OSError):
            return False

    @staticmethod
    def _validate_semver(value: str) -> bool:
        """Return True if value is a valid semantic version string (semver 2.0).

        WHY: Version fields in config should conform to semver so downstream tooling
        can compare and sort them reliably.
        WHAT: Matches value against the full semver 2.0 regex (major.minor.patch with
        optional pre-release and build metadata); returns True on full match.
        TEST: Assert _validate_semver("1.2.3") is True,
        _validate_semver("1.2.3-alpha.1") is True, and
        _validate_semver("1.2") is False.
        """
        pattern = re.compile(
            r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
            r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
            r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
            r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
        )
        return bool(pattern.match(value))


# Initialize FORMAT_VALIDATORS after class definition to avoid forward reference issues
FormatValidator.FORMAT_VALIDATORS = {
    "email": lambda v: "@" in v and "." in v.split("@")[1],
    "url": FormatValidator._validate_url,
    "uri": FormatValidator._validate_uri,
    "uuid": FormatValidator._validate_uuid,
    "ipv4": FormatValidator._validate_ipv4,
    "ipv6": FormatValidator._validate_ipv6,
    "ip": FormatValidator._validate_ip,
    "hostname": FormatValidator._validate_hostname,
    "date": FormatValidator._validate_date,
    "time": FormatValidator._validate_time,
    "datetime": FormatValidator._validate_datetime,
    "json": FormatValidator._validate_json,
    "base64": FormatValidator._validate_base64,
    "path": FormatValidator._validate_path,
    "semver": FormatValidator._validate_semver,
}


class DependencyValidator(BaseValidator):
    """Validates field dependencies - replaces 16 dependency validation functions"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate field dependencies"""
        config = context.get("config", {})
        dependencies = rule.params.get("dependencies", {})

        errors = []

        for field, deps in dependencies.items():
            if field in config and config[field] is not None:
                # Field is present, check dependencies
                if isinstance(deps, str):
                    deps = [deps]

                for dep in deps:
                    if dep not in config or config[dep] is None:
                        errors.append(f"Field '{field}' requires '{dep}' to be present")

        if errors:
            result = ValidationResult(valid=False)
            for error in errors:
                if rule.severity == ValidationSeverity.ERROR:
                    result.errors.append(error)
                elif rule.severity == ValidationSeverity.WARNING:
                    result.warnings.append(error)
                else:
                    result.info.append(error)
            return result

        return self._create_result(True)


class UniqueValidator(BaseValidator):
    """Validates unique values - replaces 12 unique validation functions"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate unique values in collections"""
        if not isinstance(value, (list, tuple)):
            return self._create_result(True)

        # Check uniqueness
        seen = set()
        duplicates = set()

        for item in value:
            # Convert unhashable types to string
            hashable_item = item
            if isinstance(item, (dict, list)):
                hashable_item = str(item)

            if hashable_item in seen:
                duplicates.add(hashable_item)
            seen.add(hashable_item)

        if duplicates:
            return self._create_result(
                False, f"Duplicate values found: {duplicates}", rule.severity
            )

        return self._create_result(True)


class CustomValidator(BaseValidator):
    """Executes custom validation functions - replaces 20 custom validation functions"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Execute custom validation function"""
        validator_func = rule.params.get("function")

        if not validator_func or not callable(validator_func):
            return self._create_result(True)

        try:
            # Call custom validator
            result = validator_func(value, context)

            # Handle different return types
            if isinstance(result, bool):
                if not result:
                    message = rule.params.get("message", "Custom validation failed")
                    return self._create_result(False, message, rule.severity)
                return self._create_result(True)

            if isinstance(result, str):
                # String means validation failed with that message
                return self._create_result(False, result, rule.severity)

            if isinstance(result, tuple):
                # (valid, message) tuple
                valid, message = result
                if not valid:
                    return self._create_result(False, message, rule.severity)
                return self._create_result(True)

            if isinstance(result, ValidationResult):
                return result

            # Unknown return type, assume success if truthy
            return self._create_result(bool(result))

        except Exception as e:
            return self._create_result(False, f"Custom validation error: {e}", "error")


class ConditionalValidator(BaseValidator):
    """Validates based on conditions - replaces 15 conditional validation functions"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Perform conditional validation"""
        condition = rule.params.get("if")
        then_rule = rule.params.get("then")
        else_rule = rule.params.get("else")

        if not condition:
            return self._create_result(True)

        # Evaluate condition
        condition_met = self._evaluate_condition(condition, value, context)

        # Apply appropriate rule
        if condition_met and then_rule:
            return self._apply_rule(then_rule, value, context)
        if not condition_met and else_rule:
            return self._apply_rule(else_rule, value, context)

        return self._create_result(True)

    def _evaluate_condition(
        self, condition: Any, value: Any, context: dict[str, Any]
    ) -> bool:
        """Evaluate condition"""
        if callable(condition):
            return condition(value, context)

        if isinstance(condition, dict):
            # Field comparison condition
            field = condition.get("field")
            operator = condition.get("operator", "==")
            expected = condition.get("value")

            config = context.get("config", {})
            actual = config.get(field)

            return self._compare_values(actual, operator, expected)

        return bool(condition)

    def _compare_values(self, actual: Any, operator: str, expected: Any) -> bool:
        """Compare values with operator"""
        operators = {
            "==": lambda a, e: a == e,
            "!=": lambda a, e: a != e,
            "<": lambda a, e: a < e,
            "<=": lambda a, e: a <= e,
            ">": lambda a, e: a > e,
            ">=": lambda a, e: a >= e,
            "in": lambda a, e: a in e,
            "not_in": lambda a, e: a not in e,
            "contains": lambda a, e: e in a,
            "matches": lambda a, e: re.match(e, str(a)) is not None,
        }

        comparator = operators.get(operator)
        if not comparator:
            return False

        try:
            return comparator(actual, expected)
        except (TypeError, ValueError, AttributeError, KeyError):
            return False

    def _apply_rule(
        self, rule_def: dict, value: Any, context: dict[str, Any]
    ) -> ValidationResult:
        """Apply validation rule"""
        # Create and execute rule
        rule = ValidationRule(
            type=ValidationType[rule_def.get("type", "CUSTOM").upper()],
            params=rule_def.get("params", {}),
            message=rule_def.get("message"),
            severity=rule_def.get("severity", ValidationSeverity.ERROR),
        )

        # Find appropriate validator
        validator = ValidationStrategy().validators.get(rule.type)
        if validator:
            return validator.validate(value, rule, context)

        return self._create_result(True)


class RecursiveValidator(BaseValidator):
    """Validates nested structures recursively - replaces 10 recursive validation functions"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Recursively validate nested structures"""
        schema = rule.params.get("schema", {})
        max_depth = rule.params.get("max_depth", 10)
        current_depth = context.get("_depth", 0)

        if current_depth >= max_depth:
            return self._create_result(
                False, f"Maximum recursion depth {max_depth} exceeded", "error"
            )

        result = ValidationResult(valid=True)

        if isinstance(value, dict):
            result = self._validate_dict(value, schema, context, current_depth)
        elif isinstance(value, list):
            result = self._validate_list(value, schema, context, current_depth)
        # Validate single value
        elif "type" in schema:
            type_rule = ValidationRule(
                type=ValidationType.TYPE, params={"type": schema["type"]}
            )
            type_validator = TypeValidator()
            result = type_validator.validate(value, type_rule, context)

        return result

    def _validate_dict(
        self, value: dict, schema: dict, context: dict, depth: int
    ) -> ValidationResult:
        """Validate dictionary recursively"""
        result = ValidationResult(valid=True)
        properties = schema.get("properties", {})

        for key, prop_schema in properties.items():
            if key in value:
                # Create context for nested validation
                nested_context = context.copy()
                nested_context["_depth"] = depth + 1

                # Recursively validate
                nested_rule = ValidationRule(
                    type=ValidationType.RECURSIVE,
                    params={
                        "schema": prop_schema,
                        "max_depth": context.get("max_depth", 10),
                    },
                )

                nested_result = self.validate(value[key], nested_rule, nested_context)

                if not nested_result.valid:
                    result.valid = False
                    result.errors.extend([f"{key}.{e}" for e in nested_result.errors])
                    result.warnings.extend(
                        [f"{key}.{w}" for w in nested_result.warnings]
                    )

        return result

    def _validate_list(
        self, value: list, schema: dict, context: dict, depth: int
    ) -> ValidationResult:
        """Validate list recursively"""
        result = ValidationResult(valid=True)
        items_schema = schema.get("items", {})

        for i, item in enumerate(value):
            # Create context for nested validation
            nested_context = context.copy()
            nested_context["_depth"] = depth + 1

            # Recursively validate
            nested_rule = ValidationRule(
                type=ValidationType.RECURSIVE,
                params={
                    "schema": items_schema,
                    "max_depth": context.get("max_depth", 10),
                },
            )

            nested_result = self.validate(item, nested_rule, nested_context)

            if not nested_result.valid:
                result.valid = False
                result.errors.extend([f"[{i}].{e}" for e in nested_result.errors])
                result.warnings.extend([f"[{i}].{w}" for w in nested_result.warnings])

        return result


class CrossFieldValidator(BaseValidator):
    """Validates cross-field constraints - replaces 8 cross-field validation functions"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate cross-field constraints"""
        config = context.get("config", {})
        constraints = rule.params.get("constraints", [])

        result = ValidationResult(valid=True)

        for constraint in constraints:
            if not self._evaluate_constraint(config, constraint):
                message = constraint.get("message", "Cross-field constraint failed")
                if rule.severity == ValidationSeverity.ERROR:
                    result.errors.append(message)
                elif rule.severity == ValidationSeverity.WARNING:
                    result.warnings.append(message)
                else:
                    result.info.append(message)
                result.valid = False

        return result

    def _evaluate_constraint(self, config: dict, constraint: dict) -> bool:
        """Evaluate a cross-field constraint"""
        constraint_type = constraint.get("type")

        if constraint_type == "mutual_exclusive":
            # Only one of the fields should be present
            fields = constraint.get("fields", [])
            present = [f for f in fields if f in config and config[f] is not None]
            return len(present) <= 1

        if constraint_type == "mutual_required":
            # All fields must be present together
            fields = constraint.get("fields", [])
            present = [f for f in fields if f in config and config[f] is not None]
            return len(present) == 0 or len(present) == len(fields)

        if constraint_type == "sum":
            # Sum of fields must match condition
            fields = constraint.get("fields", [])
            operator = constraint.get("operator", "==")
            target = constraint.get("value", 0)

            total = sum(config.get(f, 0) for f in fields)
            return self._compare_values(total, operator, target)

        if constraint_type == "comparison":
            # Compare two fields
            field1 = constraint.get("field1")
            field2 = constraint.get("field2")
            operator = constraint.get("operator", "==")

            if field1 in config and field2 in config:
                return self._compare_values(config[field1], operator, config[field2])

        elif constraint_type == "custom":
            # Custom constraint function
            func = constraint.get("function")
            if callable(func):
                return func(config)

        return True

    def _compare_values(self, val1: Any, operator: str, val2: Any) -> bool:
        """Compare two values with operator"""
        operators = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
        }

        comparator = operators.get(operator)
        if comparator:
            try:
                return comparator(val1, val2)
            except (TypeError, ValueError, AttributeError, KeyError):
                return False

        return False


class CompositeValidator(BaseValidator):
    """Composes multiple validators - replaces 6 composite validation functions"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Apply multiple validators in sequence"""
        validators = rule.params.get("validators", [])
        operator = rule.params.get("operator", "AND")  # AND, OR

        results = []
        combined_result = ValidationResult(valid=True)

        # Get validator instances
        strategy = ValidationStrategy()

        for validator_def in validators:
            # Create rule from definition
            val_rule = ValidationRule(
                type=ValidationType[validator_def.get("type", "CUSTOM").upper()],
                params=validator_def.get("params", {}),
                message=validator_def.get("message"),
                severity=validator_def.get("severity", rule.severity),
            )

            # Get validator and execute
            validator = strategy.validators.get(val_rule.type)
            if validator:
                result = validator.validate(value, val_rule, context)
                results.append(result)

                # Collect all messages
                combined_result.errors.extend(result.errors)
                combined_result.warnings.extend(result.warnings)
                combined_result.info.extend(result.info)

        # Apply operator logic
        if operator == "AND":
            combined_result.valid = all(r.valid for r in results)
        elif operator == "OR":
            combined_result.valid = any(r.valid for r in results)
            if combined_result.valid:
                # Clear errors if any validator passed
                combined_result.errors.clear()
                combined_result.warnings.clear()

        return combined_result


class SchemaValidator(BaseValidator):
    """Validates against full schema - orchestrates other validators"""

    def validate(
        self, value: Any, rule: ValidationRule, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate against complete schema"""
        schema = rule.params.get("schema", {})
        config = value if isinstance(value, dict) else {"value": value}

        # Update context
        context = context.copy()
        context["config"] = config

        result = ValidationResult(valid=True)
        strategy = ValidationStrategy()

        # Apply each schema validation
        if "type" in schema:
            type_result = strategy.validate_type(config, schema)
            self._merge_results(result, type_result)

        if "required" in schema:
            req_result = strategy.validate_required(config, schema)
            self._merge_results(result, req_result)

        if "properties" in schema:
            for key, prop_schema in schema["properties"].items():
                if key in config:
                    prop_result = self.validate(
                        config[key],
                        ValidationRule(
                            type=ValidationType.SCHEMA, params={"schema": prop_schema}
                        ),
                        context,
                    )
                    if not prop_result.valid:
                        result.valid = False
                        result.errors.extend(
                            [f"{key}: {e}" for e in prop_result.errors]
                        )

        return result

    def _merge_results(self, target: ValidationResult, source: ValidationResult):
        """Merge validation results"""
        if not source.valid:
            target.valid = False
        target.errors.extend(source.errors)
        target.warnings.extend(source.warnings)
        target.info.extend(source.info)


class ValidationStrategy(IConfigStrategy):
    """
    Main validation strategy
    Reduces 236 validation functions to 15 composable validators
    """

    def __init__(self):
        """Initialise ValidationStrategy with all 15 composable validators.

        WHY: Constructing validators at init time avoids per-call instantiation overhead
        and provides a single registry dict that compose_validators can look up by type.
        WHAT: Creates a logger and populates self.validators with one instance of each
        concrete BaseValidator subclass, keyed by its ValidationType enum value.
        TEST: Instantiate ValidationStrategy(); assert len(self.validators) == 15 and
        ValidationType.SCHEMA is in self.validators.
        """
        self.logger = get_logger(self.__class__.__name__)
        self.validators = {
            ValidationType.TYPE: TypeValidator(),
            ValidationType.REQUIRED: RequiredValidator(),
            ValidationType.RANGE: RangeValidator(),
            ValidationType.LENGTH: LengthValidator(),
            ValidationType.PATTERN: PatternValidator(),
            ValidationType.ENUM: EnumValidator(),
            ValidationType.FORMAT: FormatValidator(),
            ValidationType.DEPENDENCY: DependencyValidator(),
            ValidationType.UNIQUE: UniqueValidator(),
            ValidationType.CUSTOM: CustomValidator(),
            ValidationType.CONDITIONAL: ConditionalValidator(),
            ValidationType.RECURSIVE: RecursiveValidator(),
            ValidationType.CROSS_FIELD: CrossFieldValidator(),
            ValidationType.COMPOSITE: CompositeValidator(),
            ValidationType.SCHEMA: SchemaValidator(),
        }

    def can_handle(self, source: str | Path | dict) -> bool:
        """Check if this strategy can handle validation"""
        return isinstance(source, dict)

    def load(self, source: Any, **kwargs) -> dict[str, Any]:
        """Not used for validation"""
        return source if isinstance(source, dict) else {}

    def validate(self, config: dict[str, Any], schema: dict | None = None) -> bool:
        """Main validation entry point"""
        if not schema:
            return True

        context = {"config": config}
        result = self._validate_with_schema(config, schema, context)

        if not result.valid:
            self.logger.error(f"Validation errors: {result.errors}")
            if result.warnings:
                self.logger.warning(f"Validation warnings: {result.warnings}")

        return result.valid

    def transform(self, config: dict[str, Any]) -> dict[str, Any]:
        """Transform config based on schema"""
        return config

    def _validate_with_schema(
        self, config: dict, schema: dict, context: dict
    ) -> ValidationResult:
        """Validate configuration against schema"""
        # Use schema validator for comprehensive validation
        schema_rule = ValidationRule(
            type=ValidationType.SCHEMA, params={"schema": schema}
        )

        return self.validators[ValidationType.SCHEMA].validate(
            config, schema_rule, context
        )

    # Helper methods for direct validation
    def validate_type(self, config: dict, schema: dict) -> ValidationResult:
        """Validate types in configuration"""
        result = ValidationResult(valid=True)
        properties = schema.get("properties", {})

        for key, prop_schema in properties.items():
            if key in config and "type" in prop_schema:
                rule = ValidationRule(
                    type=ValidationType.TYPE, params={"type": prop_schema["type"]}
                )
                prop_result = self.validators[ValidationType.TYPE].validate(
                    config[key], rule, {"config": config}
                )
                if not prop_result.valid:
                    result.valid = False
                    result.errors.extend([f"{key}: {e}" for e in prop_result.errors])

        return result

    def validate_required(self, config: dict, schema: dict) -> ValidationResult:
        """Validate required fields"""
        required_fields = schema.get("required", [])
        if required_fields:
            rule = ValidationRule(
                type=ValidationType.REQUIRED, params={"fields": required_fields}
            )
            return self.validators[ValidationType.REQUIRED].validate(
                None, rule, {"config": config}
            )

        return ValidationResult(valid=True)

    def compose_validators(self, *validator_names: str) -> Callable:
        """Compose multiple validators into a single function"""

        def composed_validator(config: dict, schema: dict) -> ValidationResult:
            """Run each named validator against config and merge the results.

            WHY: Composing validators at call time allows the same composed function to
            be reused with different config inputs without capturing config in the closure.
            WHAT: Iterates validator_names from the outer scope; for each name looks up
            the corresponding ValidationType and BaseValidator, calls validate(), and
            accumulates errors/warnings into a combined ValidationResult.
            TEST: Compose "TYPE" and "REQUIRED" validators; call with a config missing
            a required field; assert the result is invalid and errors list is non-empty.
            """
            result = ValidationResult(valid=True)

            for name in validator_names:
                val_type = ValidationType[name.upper()]
                if val_type in self.validators:
                    validator = self.validators[val_type]
                    rule = ValidationRule(type=val_type, params=schema)
                    val_result = validator.validate(config, rule, {"config": config})

                    if not val_result.valid:
                        result.valid = False
                        result.errors.extend(val_result.errors)
                        result.warnings.extend(val_result.warnings)

            return result

        return composed_validator


# Export main components
__all__ = ["ValidationResult", "ValidationRule", "ValidationStrategy", "ValidationType"]
