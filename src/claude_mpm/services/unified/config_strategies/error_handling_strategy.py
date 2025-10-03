"""
Error Handling Strategy - Unifies 99 error handling patterns into composable handlers
Part of Phase 3 Configuration Consolidation
"""

import json
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, Union

from claude_mpm.core.logging_utils import get_logger

from .unified_config_service import IConfigStrategy


class ErrorSeverity(Enum):
    """Error severity levels"""

    CRITICAL = "critical"  # System failure
    ERROR = "error"  # Operation failure
    WARNING = "warning"  # Recoverable issue
    INFO = "info"  # Informational
    DEBUG = "debug"  # Debug information


class ErrorCategory(Enum):
    """Categories of errors for handling strategy"""

    FILE_IO = "file_io"
    PARSING = "parsing"
    VALIDATION = "validation"
    NETWORK = "network"
    PERMISSION = "permission"
    TYPE_CONVERSION = "type_conversion"
    MISSING_DEPENDENCY = "missing_dependency"
    CONFIGURATION = "configuration"
    RUNTIME = "runtime"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for error handling"""

    error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    source: Optional[str] = None
    operation: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    traceback: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False


@dataclass
class ErrorHandlingResult:
    """Result of error handling operation"""

    handled: bool
    recovered: bool = False
    fallback_value: Any = None
    should_retry: bool = False
    retry_after: Optional[int] = None  # seconds
    should_escalate: bool = False
    message: Optional[str] = None
    actions_taken: List[str] = field(default_factory=list)


class BaseErrorHandler(ABC):
    """Base class for all error handlers"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def can_handle(self, context: ErrorContext) -> bool:
        """Check if this handler can handle the error"""

    @abstractmethod
    def handle(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle the error"""

    def log_error(self, context: ErrorContext, message: Optional[str] = None):
        """Log error with appropriate level"""
        log_message = message or str(context.error)

        if context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif context.severity == ErrorSeverity.ERROR:
            self.logger.error(log_message)
        elif context.severity == ErrorSeverity.WARNING:
            self.logger.warning(log_message)
        elif context.severity == ErrorSeverity.INFO:
            self.logger.info(log_message)
        else:
            self.logger.debug(log_message)


class FileIOErrorHandler(BaseErrorHandler):
    """Handles file I/O errors - consolidates 18 file error patterns"""

    ERROR_MAPPING: ClassVar[dict] = {
        FileNotFoundError: "File not found",
        PermissionError: "Permission denied",
        IsADirectoryError: "Path is a directory",
        NotADirectoryError: "Path is not a directory",
        IOError: "I/O operation failed",
        OSError: "Operating system error",
    }

    def can_handle(self, context: ErrorContext) -> bool:
        """Check if error is file I/O related"""
        return context.category == ErrorCategory.FILE_IO or isinstance(
            context.error, (FileNotFoundError, PermissionError, IOError, OSError)
        )

    def handle(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle file I/O errors with recovery strategies"""
        result = ErrorHandlingResult(handled=True)

        error_type = type(context.error)
        error_message = self.ERROR_MAPPING.get(error_type, "Unknown file error")

        # Log the error
        self.log_error(context, f"{error_message}: {context.source}")

        # Try recovery strategies
        if isinstance(context.error, FileNotFoundError):
            result = self._handle_file_not_found(context)
        elif isinstance(context.error, PermissionError):
            result = self._handle_permission_error(context)
        else:
            result = self._handle_generic_io_error(context)

        result.actions_taken.append(f"Handled {error_type.__name__}")
        return result

    def _handle_file_not_found(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle file not found errors"""
        result = ErrorHandlingResult(handled=True)

        # Check for fallback locations
        if context.metadata.get("fallback_paths"):
            for fallback in context.metadata["fallback_paths"]:
                fallback_path = Path(fallback)
                if fallback_path.exists():
                    result.recovered = True
                    result.fallback_value = str(fallback_path)
                    result.actions_taken.append(f"Used fallback path: {fallback_path}")
                    self.logger.info(f"Using fallback configuration: {fallback_path}")
                    return result

        # Check for default values
        if context.metadata.get("default_config"):
            result.recovered = True
            result.fallback_value = context.metadata["default_config"]
            result.actions_taken.append("Used default configuration")
            return result

        # Create file if requested
        if context.metadata.get("create_if_missing"):
            path = Path(context.source)
            try:
                path.parent.mkdir(parents=True, exist_ok=True)

                # Create with default content
                default_content = context.metadata.get("default_content", {})

                if path.suffix == ".json":
                    path.write_text(json.dumps(default_content, indent=2))
                else:
                    path.write_text(str(default_content))

                result.recovered = True
                result.should_retry = True
                result.actions_taken.append(f"Created missing file: {path}")
                self.logger.info(f"Created missing configuration file: {path}")

            except Exception as e:
                self.logger.error(f"Failed to create file: {e}")
                result.should_escalate = True

        return result

    def _handle_permission_error(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle permission errors"""
        result = ErrorHandlingResult(handled=True)

        # Try alternative location
        if context.metadata.get("alt_location"):
            alt_path = Path(context.metadata["alt_location"])
            try:
                # Test write permission
                alt_path.parent.mkdir(parents=True, exist_ok=True)
                test_file = alt_path.parent / ".test_write"
                test_file.touch()
                test_file.unlink()

                result.recovered = True
                result.fallback_value = str(alt_path)
                result.actions_taken.append(f"Using alternative location: {alt_path}")

            except (OSError, PermissionError):
                result.should_escalate = True

        # Use read-only mode if applicable
        elif context.metadata.get("allow_readonly"):
            result.recovered = True
            result.fallback_value = {"readonly": True}
            result.actions_taken.append("Switched to read-only mode")

        return result

    def _handle_generic_io_error(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle generic I/O errors"""
        result = ErrorHandlingResult(handled=True)

        # Retry with exponential backoff
        retry_count = context.metadata.get("retry_count", 0)
        max_retries = context.metadata.get("max_retries", 3)

        if retry_count < max_retries:
            result.should_retry = True
            result.retry_after = 2**retry_count  # Exponential backoff
            result.actions_taken.append(
                f"Retry {retry_count + 1}/{max_retries} after {result.retry_after}s"
            )
        else:
            result.should_escalate = True
            result.message = f"Failed after {max_retries} retries"

        return result


class ParsingErrorHandler(BaseErrorHandler):
    """Handles parsing errors - consolidates 22 parsing error patterns"""

    PARSER_ERRORS: ClassVar[dict] = {
        json.JSONDecodeError: ErrorCategory.PARSING,
        ValueError: ErrorCategory.PARSING,  # Common for parsing
        SyntaxError: ErrorCategory.PARSING,
    }

    def can_handle(self, context: ErrorContext) -> bool:
        """Check if error is parsing related"""
        return (
            context.category == ErrorCategory.PARSING
            or type(context.error) in self.PARSER_ERRORS
            or "parse" in str(context.error).lower()
            or "decode" in str(context.error).lower()
        )

    def handle(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle parsing errors with recovery strategies"""
        result = ErrorHandlingResult(handled=True)

        # Try recovery strategies based on error type
        if isinstance(context.error, json.JSONDecodeError):
            result = self._handle_json_error(context)
        elif "yaml" in str(context.error).lower():
            result = self._handle_yaml_error(context)
        else:
            result = self._handle_generic_parse_error(context)

        return result

    def _handle_json_error(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle JSON parsing errors"""
        result = ErrorHandlingResult(handled=True)

        content = context.metadata.get("content", "")

        # Try to fix common JSON issues
        fixes = [
            self._fix_json_comments,
            self._fix_json_quotes,
            self._fix_json_trailing_commas,
            self._fix_json_unquoted_keys,
        ]

        for fix_func in fixes:
            try:
                fixed_content = fix_func(content)
                parsed = json.loads(fixed_content)
                result.recovered = True
                result.fallback_value = parsed
                result.actions_taken.append(f"Fixed JSON with {fix_func.__name__}")
                self.logger.info(f"Recovered from JSON error using {fix_func.__name__}")
                return result
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

        # Use lenient parser if available
        if context.metadata.get("allow_lenient"):
            result = self._parse_lenient_json(content, result)

        return result

    def _fix_json_comments(self, content: str) -> str:
        """Remove comments from JSON"""
        import re

        # Remove single-line comments
        content = re.sub(r"//.*?$", "", content, flags=re.MULTILINE)
        # Remove multi-line comments
        return re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    def _fix_json_quotes(self, content: str) -> str:
        """Fix quote issues in JSON"""
        import re

        # Replace single quotes with double quotes (careful with values)
        # This is a simple approach - more sophisticated parsing might be needed
        content = re.sub(r"'([^']*)':", r'"\1":', content)  # Keys
        return re.sub(r":\s*'([^']*)'", r': "\1"', content)  # Values

    def _fix_json_trailing_commas(self, content: str) -> str:
        """Remove trailing commas"""
        import re

        content = re.sub(r",\s*}", "}", content)
        return re.sub(r",\s*]", "]", content)

    def _fix_json_unquoted_keys(self, content: str) -> str:
        """Add quotes to unquoted keys"""
        import re

        # Match unquoted keys (word characters followed by colon)
        return re.sub(r"(\w+):", r'"\1":', content)

    def _parse_lenient_json(
        self, content: str, result: ErrorHandlingResult
    ) -> ErrorHandlingResult:
        """Parse JSON leniently"""
        try:
            # Try using ast.literal_eval for Python literals
            import ast

            parsed = ast.literal_eval(content)
            result.recovered = True
            result.fallback_value = parsed
            result.actions_taken.append("Parsed as Python literal")
        except (ValueError, SyntaxError, TypeError):
            # Return empty dict as last resort
            result.recovered = True
            result.fallback_value = {}
            result.actions_taken.append("Used empty configuration as fallback")

        return result

    def _handle_yaml_error(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle YAML parsing errors"""
        result = ErrorHandlingResult(handled=True)

        content = context.metadata.get("content", "")

        # Try to fix common YAML issues
        try:
            import yaml

            # Try with safe loader
            parsed = yaml.safe_load(content)
            result.recovered = True
            result.fallback_value = parsed
            result.actions_taken.append("Parsed with safe YAML loader")

        except (yaml.YAMLError, ValueError, AttributeError):
            # Try to fix tabs
            content = content.replace("\t", "    ")
            try:
                parsed = yaml.safe_load(content)
                result.recovered = True
                result.fallback_value = parsed
                result.actions_taken.append("Fixed YAML tabs")
            except (yaml.YAMLError, ValueError, AttributeError):
                result.fallback_value = {}
                result.actions_taken.append("Used empty configuration as fallback")

        return result

    def _handle_generic_parse_error(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle generic parsing errors"""
        result = ErrorHandlingResult(handled=True)

        # Try alternative formats
        content = context.metadata.get("content", "")

        formats = [
            ("json", json.loads),
            ("yaml", self._try_yaml),
            ("ini", self._try_ini),
            ("properties", self._try_properties),
        ]

        for format_name, parser in formats:
            try:
                parsed = parser(content)
                if parsed:
                    result.recovered = True
                    result.fallback_value = parsed
                    result.actions_taken.append(f"Parsed as {format_name}")
                    return result
            except (ValueError, TypeError, AttributeError, ImportError):
                continue

        # Use default/empty config
        result.recovered = True
        result.fallback_value = context.metadata.get("default_config", {})
        result.actions_taken.append("Used default configuration")

        return result

    def _try_yaml(self, content: str) -> Dict:
        """Try parsing as YAML"""
        import yaml

        return yaml.safe_load(content)

    def _try_ini(self, content: str) -> Dict:
        """Try parsing as INI"""
        import configparser

        parser = configparser.ConfigParser()
        parser.read_string(content)
        return {s: dict(parser.items(s)) for s in parser.sections()}

    def _try_properties(self, content: str) -> Dict:
        """Try parsing as properties file"""
        result = {}
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
        return result


class ValidationErrorHandler(BaseErrorHandler):
    """Handles validation errors - consolidates 15 validation error patterns"""

    def can_handle(self, context: ErrorContext) -> bool:
        """Check if error is validation related"""
        return (
            context.category == ErrorCategory.VALIDATION
            or "validation" in str(context.error).lower()
            or "invalid" in str(context.error).lower()
            or "constraint" in str(context.error).lower()
        )

    def handle(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle validation errors"""
        result = ErrorHandlingResult(handled=True)

        # Get validation details
        field = context.metadata.get("field")
        value = context.metadata.get("value")
        schema = context.metadata.get("schema")

        # Try to fix or provide default
        if field and schema:
            result = self._fix_validation_error(field, value, schema, result)
        else:
            result = self._handle_generic_validation(context, result)

        return result

    def _fix_validation_error(
        self, field: str, value: Any, schema: Dict, result: ErrorHandlingResult
    ) -> ErrorHandlingResult:
        """Try to fix validation error"""
        field_schema = schema.get("properties", {}).get(field, {})

        # Try type coercion
        if "type" in field_schema:
            expected_type = field_schema["type"]
            coerced = self._coerce_type(value, expected_type)

            if coerced is not None:
                result.recovered = True
                result.fallback_value = {field: coerced}
                result.actions_taken.append(f"Coerced {field} to {expected_type}")
                return result

        # Use default value if available
        if "default" in field_schema:
            result.recovered = True
            result.fallback_value = {field: field_schema["default"]}
            result.actions_taken.append(f"Used default value for {field}")
            return result

        # Use minimum/maximum for range errors
        if "minimum" in field_schema and isinstance(value, (int, float)):
            if value < field_schema["minimum"]:
                result.recovered = True
                result.fallback_value = {field: field_schema["minimum"]}
                result.actions_taken.append(f"Clamped {field} to minimum")
                return result

        if "maximum" in field_schema and isinstance(value, (int, float)):
            if value > field_schema["maximum"]:
                result.recovered = True
                result.fallback_value = {field: field_schema["maximum"]}
                result.actions_taken.append(f"Clamped {field} to maximum")
                return result

        return result

    def _coerce_type(self, value: Any, expected_type: str) -> Any:
        """Attempt to coerce value to expected type"""
        try:
            if expected_type == "string":
                return str(value)
            if expected_type == "integer":
                return int(value)
            if expected_type == "number":
                return float(value)
            if expected_type == "boolean":
                if isinstance(value, str):
                    return value.lower() in ["true", "yes", "1", "on"]
                return bool(value)
            if expected_type == "array":
                if isinstance(value, str):
                    # Try comma-separated
                    return [v.strip() for v in value.split(",")]
                return list(value)
            if expected_type == "object":
                if isinstance(value, str):
                    return json.loads(value)
                return dict(value)
        except (ValueError, TypeError, json.JSONDecodeError):
            return None

    def _handle_generic_validation(
        self, context: ErrorContext, result: ErrorHandlingResult
    ) -> ErrorHandlingResult:
        """Handle generic validation errors"""
        # Use strict vs lenient mode
        if context.metadata.get("strict", True):
            result.should_escalate = True
            result.message = "Validation failed in strict mode"
        else:
            # In lenient mode, use config as-is with warnings
            result.recovered = True
            result.fallback_value = context.metadata.get("config", {})
            result.actions_taken.append("Accepted configuration in lenient mode")
            self.logger.warning(
                f"Validation error ignored in lenient mode: {context.error}"
            )

        return result


class NetworkErrorHandler(BaseErrorHandler):
    """Handles network-related errors - consolidates 12 network error patterns"""

    NETWORK_ERRORS: ClassVar[list] = [
        ConnectionError,
        TimeoutError,
        ConnectionRefusedError,
        ConnectionResetError,
        BrokenPipeError,
    ]

    def can_handle(self, context: ErrorContext) -> bool:
        """Check if error is network related"""
        return (
            context.category == ErrorCategory.NETWORK
            or any(isinstance(context.error, err) for err in self.NETWORK_ERRORS)
            or "connection" in str(context.error).lower()
            or "timeout" in str(context.error).lower()
        )

    def handle(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle network errors with retry logic"""
        result = ErrorHandlingResult(handled=True)

        # Implement exponential backoff retry
        retry_count = context.metadata.get("retry_count", 0)
        max_retries = context.metadata.get("max_retries", 5)

        if retry_count < max_retries:
            # Calculate backoff time
            backoff = min(300, 2**retry_count)  # Max 5 minutes
            result.should_retry = True
            result.retry_after = backoff
            result.actions_taken.append(
                f"Retry {retry_count + 1}/{max_retries} after {backoff}s"
            )

            # Add jitter to prevent thundering herd
            import random

            result.retry_after += random.uniform(0, backoff * 0.1)

        # Try offline/cached mode
        elif context.metadata.get("cache_available"):
            result.recovered = True
            result.fallback_value = context.metadata.get("cached_config")
            result.actions_taken.append("Using cached configuration")
        else:
            result.should_escalate = True
            result.message = f"Network error after {max_retries} retries"

        return result


class TypeConversionErrorHandler(BaseErrorHandler):
    """Handles type conversion errors - consolidates 10 type conversion patterns"""

    def can_handle(self, context: ErrorContext) -> bool:
        """Check if error is type conversion related"""
        return (
            context.category == ErrorCategory.TYPE_CONVERSION
            or isinstance(context.error, (TypeError, ValueError))
            or "type" in str(context.error).lower()
            or "convert" in str(context.error).lower()
        )

    def handle(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle type conversion errors"""
        result = ErrorHandlingResult(handled=True)

        source_value = context.metadata.get("value")
        target_type = context.metadata.get("target_type")

        if source_value is not None and target_type:
            # Try intelligent conversion
            converted = self._smart_convert(source_value, target_type)

            if converted is not None:
                result.recovered = True
                result.fallback_value = converted
                result.actions_taken.append(f"Converted to {target_type}")
            else:
                # Use default for type
                default = self._get_type_default(target_type)
                result.recovered = True
                result.fallback_value = default
                result.actions_taken.append(f"Used default for {target_type}")

        return result

    def _smart_convert(self, value: Any, target_type: Type) -> Any:
        """Smart type conversion with fallbacks"""
        converters = {
            str: self._to_string,
            int: self._to_int,
            float: self._to_float,
            bool: self._to_bool,
            list: self._to_list,
            dict: self._to_dict,
        }

        converter = converters.get(target_type)
        if converter:
            try:
                return converter(value)
            except (ValueError, TypeError, AttributeError):
                pass

        return None

    def _to_string(self, value: Any) -> str:
        """Convert to string"""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)

    def _to_int(self, value: Any) -> int:
        """Convert to integer"""
        if isinstance(value, str):
            # Try to extract number from string
            import re

            match = re.search(r"-?\d+", value)
            if match:
                return int(match.group())
        return int(float(value))

    def _to_float(self, value: Any) -> float:
        """Convert to float"""
        if isinstance(value, str):
            # Handle percentage
            if "%" in value:
                return float(value.replace("%", "")) / 100
            # Handle comma as decimal separator
            value = value.replace(",", ".")
        return float(value)

    def _to_bool(self, value: Any) -> bool:
        """Convert to boolean"""
        if isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "on", "enabled"]
        return bool(value)

    def _to_list(self, value: Any) -> list:
        """Convert to list"""
        if isinstance(value, str):
            # Try JSON array
            if value.startswith("["):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    pass
            # Try comma-separated
            return [v.strip() for v in value.split(",")]
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes, dict)):
            return list(value)
        return [value]

    def _to_dict(self, value: Any) -> dict:
        """Convert to dictionary"""
        if isinstance(value, str):
            # Try JSON object
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                pass
            # Try key=value pairs
            result = {}
            for pair in value.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    result[k.strip()] = v.strip()
            return result
        if hasattr(value, "__dict__"):
            return vars(value)
        return {}

    def _get_type_default(self, target_type: Type) -> Any:
        """Get default value for type"""
        defaults = {
            str: "",
            int: 0,
            float: 0.0,
            bool: False,
            list: [],
            dict: {},
            type(None): None,
        }
        return defaults.get(target_type)


class CompositeErrorHandler(BaseErrorHandler):
    """Orchestrates multiple error handlers - consolidates 22 composite patterns"""

    def __init__(self):
        super().__init__()
        self.handlers = [
            FileIOErrorHandler(),
            ParsingErrorHandler(),
            ValidationErrorHandler(),
            NetworkErrorHandler(),
            TypeConversionErrorHandler(),
        ]

    def can_handle(self, context: ErrorContext) -> bool:
        """Composite handler can handle any error"""
        return True

    def handle(self, context: ErrorContext) -> ErrorHandlingResult:
        """Try multiple handlers in sequence"""
        # First, try specific handlers
        for handler in self.handlers:
            if handler.can_handle(context):
                result = handler.handle(context)

                if result.recovered or not result.should_escalate:
                    return result

        # If no specific handler worked, use fallback strategies
        return self._handle_unknown_error(context)

    def _handle_unknown_error(self, context: ErrorContext) -> ErrorHandlingResult:
        """Handle unknown errors with generic strategies"""
        result = ErrorHandlingResult(handled=True)

        # Log the full error
        self.logger.error(
            f"Unknown error in {context.operation}: {context.error}", exc_info=True
        )

        # Try generic recovery strategies
        if context.metadata.get("default_config"):
            result.recovered = True
            result.fallback_value = context.metadata["default_config"]
            result.actions_taken.append("Used default configuration for unknown error")
        elif context.metadata.get("skip_on_error"):
            result.recovered = True
            result.fallback_value = {}
            result.actions_taken.append("Skipped configuration due to error")
        else:
            result.should_escalate = True
            result.message = f"Unhandled error: {context.error}"

        return result


class ErrorHandlingStrategy(IConfigStrategy):
    """
    Main error handling strategy
    Unifies 99 error handling patterns into composable handlers
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.composite_handler = CompositeErrorHandler()
        self.error_history: List[ErrorContext] = []
        self.recovery_strategies: Dict[str, Callable] = {}

    def can_handle(self, source: Union[str, Path, Dict]) -> bool:
        """Error handler can handle any source"""
        return True

    def load(self, source: Any, **kwargs) -> Dict[str, Any]:
        """Not used for error handling"""
        return {}

    def validate(self, config: Dict[str, Any], schema: Optional[Dict] = None) -> bool:
        """Validate with error handling"""
        return True

    def transform(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform config with error handling"""
        return config

    def handle_error(
        self,
        error: Exception,
        source: Optional[str] = None,
        operation: Optional[str] = None,
        **metadata,
    ) -> ErrorHandlingResult:
        """Main error handling entry point"""
        # Categorize error
        category = self._categorize_error(error)
        severity = self._determine_severity(error, category)

        # Create error context
        context = ErrorContext(
            error=error,
            category=category,
            severity=severity,
            source=source,
            operation=operation,
            traceback=traceback.format_exc(),
            metadata=metadata,
        )

        # Record in history
        self.error_history.append(context)

        # Handle the error
        result = self.composite_handler.handle(context)

        # Apply recovery strategies if needed
        if not result.recovered and self.recovery_strategies:
            result = self._apply_recovery_strategies(context, result)

        # Update context
        context.recovery_attempted = result.recovered or result.should_retry
        context.recovery_successful = result.recovered

        return result

    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize the error type"""
        type(error)

        # File I/O errors
        if isinstance(error, (FileNotFoundError, PermissionError, IOError, OSError)):
            return ErrorCategory.FILE_IO

        # Parsing errors
        if isinstance(error, (json.JSONDecodeError, ValueError, SyntaxError)):
            if "parse" in str(error).lower() or "decode" in str(error).lower():
                return ErrorCategory.PARSING

        # Network errors
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK

        # Type conversion errors
        if isinstance(error, TypeError):
            return ErrorCategory.TYPE_CONVERSION

        # Check error message for hints
        error_msg = str(error).lower()

        if "validation" in error_msg or "invalid" in error_msg:
            return ErrorCategory.VALIDATION
        if "permission" in error_msg or "access" in error_msg:
            return ErrorCategory.PERMISSION
        if "not found" in error_msg or "missing" in error_msg:
            return ErrorCategory.MISSING_DEPENDENCY
        if "config" in error_msg or "setting" in error_msg:
            return ErrorCategory.CONFIGURATION

        return ErrorCategory.UNKNOWN

    def _determine_severity(
        self, error: Exception, category: ErrorCategory
    ) -> ErrorSeverity:
        """Determine error severity"""
        # Critical errors
        critical_types = [MemoryError, SystemError, KeyboardInterrupt]
        if type(error) in critical_types:
            return ErrorSeverity.CRITICAL

        # Category-based severity
        severity_map = {
            ErrorCategory.FILE_IO: ErrorSeverity.ERROR,
            ErrorCategory.PARSING: ErrorSeverity.WARNING,
            ErrorCategory.VALIDATION: ErrorSeverity.WARNING,
            ErrorCategory.NETWORK: ErrorSeverity.ERROR,
            ErrorCategory.PERMISSION: ErrorSeverity.ERROR,
            ErrorCategory.TYPE_CONVERSION: ErrorSeverity.WARNING,
            ErrorCategory.MISSING_DEPENDENCY: ErrorSeverity.ERROR,
            ErrorCategory.CONFIGURATION: ErrorSeverity.ERROR,
            ErrorCategory.RUNTIME: ErrorSeverity.ERROR,
            ErrorCategory.UNKNOWN: ErrorSeverity.ERROR,
        }

        return severity_map.get(category, ErrorSeverity.ERROR)

    def _apply_recovery_strategies(
        self, context: ErrorContext, result: ErrorHandlingResult
    ) -> ErrorHandlingResult:
        """Apply custom recovery strategies"""
        for name, strategy in self.recovery_strategies.items():
            try:
                recovery_result = strategy(context)
                if recovery_result:
                    result.recovered = True
                    result.fallback_value = recovery_result
                    result.actions_taken.append(f"Applied recovery strategy: {name}")
                    return result
            except Exception as e:
                self.logger.debug(f"Recovery strategy {name} failed: {e}")

        return result

    def register_recovery_strategy(self, name: str, strategy: Callable):
        """Register a custom recovery strategy"""
        self.recovery_strategies[name] = strategy
        self.logger.debug(f"Registered recovery strategy: {name}")

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics"""
        if not self.error_history:
            return {
                "total_errors": 0,
                "categories": {},
                "severities": {},
                "recovery_rate": 0.0,
            }

        total = len(self.error_history)
        recovered = sum(1 for e in self.error_history if e.recovery_successful)

        categories = {}
        severities = {}

        for error in self.error_history:
            # Count by category
            cat_name = error.category.value
            categories[cat_name] = categories.get(cat_name, 0) + 1

            # Count by severity
            sev_name = error.severity.value
            severities[sev_name] = severities.get(sev_name, 0) + 1

        return {
            "total_errors": total,
            "recovered": recovered,
            "recovery_rate": (recovered / total) * 100 if total > 0 else 0,
            "categories": categories,
            "severities": severities,
            "recent_errors": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "category": e.category.value,
                    "severity": e.severity.value,
                    "operation": e.operation,
                    "recovered": e.recovery_successful,
                }
                for e in self.error_history[-10:]  # Last 10 errors
            ],
        }


# Export main components
__all__ = [
    "ErrorCategory",
    "ErrorContext",
    "ErrorHandlingResult",
    "ErrorHandlingStrategy",
    "ErrorSeverity",
]
