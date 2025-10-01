"""
Configuration Schema - Declarative configuration with automatic validation
Part of Phase 3 Configuration Consolidation
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from claude_mpm.core.logging_utils import get_logger

T = TypeVar("T")


class SchemaType(Enum):
    """Supported schema types"""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"
    ANY = "any"


class SchemaFormat(Enum):
    """Supported format constraints"""

    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    EMAIL = "email"
    URI = "uri"
    UUID = "uuid"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    HOSTNAME = "hostname"
    PATH = "path"
    REGEX = "regex"
    JSON = "json"
    BASE64 = "base64"
    SEMVER = "semver"


@dataclass
class SchemaProperty:
    """Schema property definition"""

    type: Union[SchemaType, List[SchemaType]]
    description: Optional[str] = None
    default: Any = None
    required: bool = False
    nullable: bool = False

    # Constraints
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    exclusive_minimum: Optional[Union[int, float]] = None
    exclusive_maximum: Optional[Union[int, float]] = None

    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    format: Optional[SchemaFormat] = None

    enum: Optional[List[Any]] = None
    const: Optional[Any] = None

    # Array constraints
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    unique_items: bool = False
    items: Optional["SchemaProperty"] = None

    # Object constraints
    properties: Optional[Dict[str, "SchemaProperty"]] = None
    additional_properties: Union[bool, "SchemaProperty"] = True
    required_properties: Optional[List[str]] = None

    # Advanced
    dependencies: Optional[Dict[str, Union[List[str], "SchemaProperty"]]] = None
    one_of: Optional[List["SchemaProperty"]] = None
    any_of: Optional[List["SchemaProperty"]] = None
    all_of: Optional[List["SchemaProperty"]] = None
    not_schema: Optional["SchemaProperty"] = None

    # Custom validation
    validator: Optional[Callable[[Any], bool]] = None
    transformer: Optional[Callable[[Any], Any]] = None

    # Metadata
    deprecated: bool = False
    examples: Optional[List[Any]] = None
    read_only: bool = False
    write_only: bool = False


@dataclass
class ConfigSchema:
    """Complete configuration schema"""

    title: str
    description: Optional[str] = None
    version: str = "1.0.0"
    properties: Dict[str, SchemaProperty] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    additional_properties: Union[bool, SchemaProperty] = True

    # Schema metadata
    schema_id: Optional[str] = None
    schema_uri: Optional[str] = None

    # Defaults
    defaults: Dict[str, Any] = field(default_factory=dict)

    # Validation rules
    dependencies: Optional[Dict[str, Union[List[str], SchemaProperty]]] = None
    pattern_properties: Optional[Dict[str, SchemaProperty]] = None

    # Conditional schemas
    if_schema: Optional["ConfigSchema"] = None
    then_schema: Optional["ConfigSchema"] = None
    else_schema: Optional["ConfigSchema"] = None

    # Composition
    all_of: Optional[List["ConfigSchema"]] = None
    any_of: Optional[List["ConfigSchema"]] = None
    one_of: Optional[List["ConfigSchema"]] = None
    not_schema: Optional["ConfigSchema"] = None

    # Custom handlers
    pre_validators: List[Callable] = field(default_factory=list)
    post_validators: List[Callable] = field(default_factory=list)
    transformers: List[Callable] = field(default_factory=list)


class SchemaBuilder:
    """Builder for creating configuration schemas fluently"""

    def __init__(self, title: str):
        self.schema = ConfigSchema(title=title)
        self.logger = get_logger(self.__class__.__name__)

    def description(self, desc: str) -> "SchemaBuilder":
        """Set schema description"""
        self.schema.description = desc
        return self

    def version(self, ver: str) -> "SchemaBuilder":
        """Set schema version"""
        self.schema.version = ver
        return self

    def property(
        self, name: str, type: Union[SchemaType, str], **kwargs
    ) -> "SchemaBuilder":
        """Add a property to the schema"""
        if isinstance(type, str):
            type = SchemaType(type)

        prop = SchemaProperty(type=type, **kwargs)
        self.schema.properties[name] = prop

        if kwargs.get("required", False) and name not in self.schema.required:
            self.schema.required.append(name)

        return self

    def string(self, name: str, **kwargs) -> "SchemaBuilder":
        """Add string property"""
        return self.property(name, SchemaType.STRING, **kwargs)

    def integer(self, name: str, **kwargs) -> "SchemaBuilder":
        """Add integer property"""
        return self.property(name, SchemaType.INTEGER, **kwargs)

    def number(self, name: str, **kwargs) -> "SchemaBuilder":
        """Add number property"""
        return self.property(name, SchemaType.NUMBER, **kwargs)

    def boolean(self, name: str, **kwargs) -> "SchemaBuilder":
        """Add boolean property"""
        return self.property(name, SchemaType.BOOLEAN, **kwargs)

    def array(
        self, name: str, items: Optional[SchemaProperty] = None, **kwargs
    ) -> "SchemaBuilder":
        """Add array property"""
        return self.property(name, SchemaType.ARRAY, items=items, **kwargs)

    def object(
        self,
        name: str,
        properties: Optional[Dict[str, SchemaProperty]] = None,
        **kwargs,
    ) -> "SchemaBuilder":
        """Add object property"""
        return self.property(name, SchemaType.OBJECT, properties=properties, **kwargs)

    def enum(self, name: str, values: List[Any], **kwargs) -> "SchemaBuilder":
        """Add enum property"""
        return self.property(name, SchemaType.STRING, enum=values, **kwargs)

    def required_fields(self, *fields: str) -> "SchemaBuilder":
        """Mark fields as required"""
        for field in fields:
            if field not in self.schema.required:
                self.schema.required.append(field)
        return self

    def default(self, name: str, value: Any) -> "SchemaBuilder":
        """Set default value for property"""
        if name in self.schema.properties:
            self.schema.properties[name].default = value
        self.schema.defaults[name] = value
        return self

    def dependency(
        self, field: str, depends_on: Union[str, List[str]]
    ) -> "SchemaBuilder":
        """Add field dependency"""
        if self.schema.dependencies is None:
            self.schema.dependencies = {}

        if isinstance(depends_on, str):
            depends_on = [depends_on]

        self.schema.dependencies[field] = depends_on
        return self

    def validator(self, func: Callable) -> "SchemaBuilder":
        """Add custom validator"""
        self.schema.post_validators.append(func)
        return self

    def transformer(self, func: Callable) -> "SchemaBuilder":
        """Add transformer function"""
        self.schema.transformers.append(func)
        return self

    def build(self) -> ConfigSchema:
        """Build and return the schema"""
        return self.schema


class SchemaValidator:
    """Validates configurations against schemas"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self, config: Dict[str, Any], schema: ConfigSchema) -> bool:
        """Validate configuration against schema"""
        self.errors = []
        self.warnings = []

        # Run pre-validators
        for validator in schema.pre_validators:
            if not validator(config):
                self.errors.append(f"Pre-validation failed: {validator.__name__}")
                return False

        # Validate required fields
        for field in schema.required:
            if field not in config:
                self.errors.append(f"Required field missing: {field}")

        # Validate properties
        for name, prop in schema.properties.items():
            if name in config:
                self._validate_property(config[name], prop, name)

        # Check additional properties
        if not schema.additional_properties:
            extra = set(config.keys()) - set(schema.properties.keys())
            if extra:
                self.errors.append(f"Additional properties not allowed: {extra}")

        # Validate dependencies
        if schema.dependencies:
            self._validate_dependencies(config, schema.dependencies)

        # Run post-validators
        for validator in schema.post_validators:
            if not validator(config):
                self.errors.append(f"Post-validation failed: {validator.__name__}")

        return len(self.errors) == 0

    def _validate_property(self, value: Any, prop: SchemaProperty, path: str):
        """Validate a single property"""
        # Check nullable
        if value is None:
            if not prop.nullable:
                self.errors.append(f"{path}: null value not allowed")
            return

        # Check type
        if not self._check_type(value, prop.type):
            self.errors.append(f"{path}: type mismatch, expected {prop.type}")

        # Check constraints based on type
        if isinstance(value, (int, float)):
            self._validate_numeric(value, prop, path)
        elif isinstance(value, str):
            self._validate_string(value, prop, path)
        elif isinstance(value, list):
            self._validate_array(value, prop, path)
        elif isinstance(value, dict):
            self._validate_object(value, prop, path)

        # Check enum
        if prop.enum and value not in prop.enum:
            self.errors.append(f"{path}: value must be one of {prop.enum}")

        # Check const
        if prop.const is not None and value != prop.const:
            self.errors.append(f"{path}: value must be {prop.const}")

        # Run custom validator
        if prop.validator and not prop.validator(value):
            self.errors.append(f"{path}: custom validation failed")

    def _check_type(
        self, value: Any, expected: Union[SchemaType, List[SchemaType]]
    ) -> bool:
        """Check if value matches expected type"""
        if isinstance(expected, list):
            return any(self._check_type(value, t) for t in expected)

        type_map = {
            SchemaType.STRING: str,
            SchemaType.INTEGER: int,
            SchemaType.NUMBER: (int, float),
            SchemaType.BOOLEAN: bool,
            SchemaType.ARRAY: list,
            SchemaType.OBJECT: dict,
            SchemaType.NULL: type(None),
            SchemaType.ANY: object,
        }

        expected_type = type_map.get(expected, object)
        return isinstance(value, expected_type)

    def _validate_numeric(
        self, value: Union[int, float], prop: SchemaProperty, path: str
    ):
        """Validate numeric constraints"""
        if prop.minimum is not None and value < prop.minimum:
            self.errors.append(f"{path}: value {value} is below minimum {prop.minimum}")

        if prop.maximum is not None and value > prop.maximum:
            self.errors.append(f"{path}: value {value} exceeds maximum {prop.maximum}")

        if prop.exclusive_minimum is not None and value <= prop.exclusive_minimum:
            self.errors.append(
                f"{path}: value {value} must be greater than {prop.exclusive_minimum}"
            )

        if prop.exclusive_maximum is not None and value >= prop.exclusive_maximum:
            self.errors.append(
                f"{path}: value {value} must be less than {prop.exclusive_maximum}"
            )

    def _validate_string(self, value: str, prop: SchemaProperty, path: str):
        """Validate string constraints"""
        if prop.min_length is not None and len(value) < prop.min_length:
            self.errors.append(
                f"{path}: length {len(value)} is below minimum {prop.min_length}"
            )

        if prop.max_length is not None and len(value) > prop.max_length:
            self.errors.append(
                f"{path}: length {len(value)} exceeds maximum {prop.max_length}"
            )

        if prop.pattern:
            import re

            if not re.match(prop.pattern, value):
                self.errors.append(f"{path}: does not match pattern {prop.pattern}")

        if prop.format and not self._validate_format(value, prop.format):
            self.errors.append(f"{path}: invalid format {prop.format.value}")

    def _validate_array(self, value: List, prop: SchemaProperty, path: str):
        """Validate array constraints"""
        if prop.min_items is not None and len(value) < prop.min_items:
            self.errors.append(
                f"{path}: array length {len(value)} is below minimum {prop.min_items}"
            )

        if prop.max_items is not None and len(value) > prop.max_items:
            self.errors.append(
                f"{path}: array length {len(value)} exceeds maximum {prop.max_items}"
            )

        if prop.unique_items:
            seen = set()
            for item in value:
                item_key = (
                    str(item)
                    if not isinstance(item, (dict, list))
                    else json.dumps(item, sort_keys=True)
                )
                if item_key in seen:
                    self.errors.append(f"{path}: duplicate items not allowed")
                    break
                seen.add(item_key)

        if prop.items:
            for i, item in enumerate(value):
                self._validate_property(item, prop.items, f"{path}[{i}]")

    def _validate_object(self, value: Dict, prop: SchemaProperty, path: str):
        """Validate object constraints"""
        if prop.properties:
            for name, sub_prop in prop.properties.items():
                if name in value:
                    self._validate_property(value[name], sub_prop, f"{path}.{name}")

        if prop.required_properties:
            for req in prop.required_properties:
                if req not in value:
                    self.errors.append(f"{path}: required property '{req}' missing")

        if not prop.additional_properties and prop.properties:
            extra = set(value.keys()) - set(prop.properties.keys())
            if extra:
                self.errors.append(
                    f"{path}: additional properties not allowed: {extra}"
                )

    def _validate_dependencies(self, config: Dict, dependencies: Dict):
        """Validate field dependencies"""
        for field, deps in dependencies.items():
            if field in config and isinstance(deps, list):
                for dep in deps:
                    if dep not in config:
                        self.errors.append(
                            f"Field '{field}' requires '{dep}' to be present"
                        )

    def _validate_format(self, value: str, format: SchemaFormat) -> bool:
        """Validate string format"""
        validators = {
            SchemaFormat.EMAIL: lambda v: "@" in v and "." in v.split("@")[1],
            SchemaFormat.DATE: lambda v: self._try_parse_date(v, "%Y-%m-%d"),
            SchemaFormat.DATETIME: lambda v: self._try_parse_date(
                v, "%Y-%m-%dT%H:%M:%S"
            ),
            SchemaFormat.UUID: lambda v: self._validate_uuid(v),
            SchemaFormat.IPV4: lambda v: self._validate_ipv4(v),
            SchemaFormat.IPV6: lambda v: self._validate_ipv6(v),
            SchemaFormat.URI: lambda v: "://" in v,
            SchemaFormat.PATH: lambda v: True,  # Any string is valid path
            SchemaFormat.SEMVER: lambda v: self._validate_semver(v),
        }

        validator = validators.get(format)
        return validator(value) if validator else True

    def _try_parse_date(self, value: str, format: str) -> bool:
        """Try to parse date string"""
        try:
            datetime.strptime(value, format)
            return True
        except (ValueError, TypeError):
            return False

    def _validate_uuid(self, value: str) -> bool:
        """Validate UUID format"""
        import uuid

        try:
            uuid.UUID(value)
            return True
        except (ValueError, TypeError, AttributeError):
            return False

    def _validate_ipv4(self, value: str) -> bool:
        """Validate IPv4 address"""
        import ipaddress

        try:
            ipaddress.IPv4Address(value)
            return True
        except (ValueError, TypeError, ipaddress.AddressValueError):
            return False

    def _validate_ipv6(self, value: str) -> bool:
        """Validate IPv6 address"""
        import ipaddress

        try:
            ipaddress.IPv6Address(value)
            return True
        except (ValueError, TypeError, ipaddress.AddressValueError):
            return False

    def _validate_semver(self, value: str) -> bool:
        """Validate semantic version"""
        import re

        pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
        return bool(re.match(pattern, value))


class SchemaRegistry:
    """Registry for managing configuration schemas"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.schemas: Dict[str, ConfigSchema] = {}
        self.versions: Dict[str, Dict[str, ConfigSchema]] = {}

    def register(self, schema: ConfigSchema, name: Optional[str] = None):
        """Register a schema"""
        name = name or schema.title

        # Store by name
        self.schemas[name] = schema

        # Store by version
        if name not in self.versions:
            self.versions[name] = {}
        self.versions[name][schema.version] = schema

        self.logger.info(f"Registered schema: {name} v{schema.version}")

    def get(self, name: str, version: Optional[str] = None) -> Optional[ConfigSchema]:
        """Get schema by name and optionally version"""
        if version:
            return self.versions.get(name, {}).get(version)
        return self.schemas.get(name)

    def list_schemas(self) -> List[str]:
        """List all registered schemas"""
        return list(self.schemas.keys())

    def list_versions(self, name: str) -> List[str]:
        """List all versions of a schema"""
        return list(self.versions.get(name, {}).keys())


class ConfigMigration:
    """Handles configuration migration between schema versions"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.migrations: Dict[tuple, Callable] = {}

    def register_migration(
        self, from_version: str, to_version: str, migration_func: Callable[[Dict], Dict]
    ):
        """Register a migration function"""
        key = (from_version, to_version)
        self.migrations[key] = migration_func
        self.logger.info(f"Registered migration: {from_version} -> {to_version}")

    def migrate(
        self, config: Dict[str, Any], from_version: str, to_version: str
    ) -> Dict[str, Any]:
        """Migrate configuration between versions"""
        key = (from_version, to_version)

        if key in self.migrations:
            # Direct migration available
            return self.migrations[key](config)

        # Try to find migration path
        path = self._find_migration_path(from_version, to_version)

        if not path:
            raise ValueError(f"No migration path from {from_version} to {to_version}")

        # Apply migrations in sequence
        current = config
        for i in range(len(path) - 1):
            key = (path[i], path[i + 1])
            if key in self.migrations:
                current = self.migrations[key](current)
                self.logger.info(f"Applied migration: {path[i]} -> {path[i + 1]}")

        return current

    def _find_migration_path(
        self, from_version: str, to_version: str
    ) -> Optional[List[str]]:
        """Find migration path between versions using BFS"""
        from collections import deque

        # Build graph of migrations
        graph = {}
        for from_v, to_v in self.migrations:
            if from_v not in graph:
                graph[from_v] = []
            graph[from_v].append(to_v)

        # BFS to find path
        queue = deque([(from_version, [from_version])])
        visited = {from_version}

        while queue:
            current, path = queue.popleft()

            if current == to_version:
                return path

            for next_v in graph.get(current, []):
                if next_v not in visited:
                    visited.add(next_v)
                    queue.append((next_v, [*path, next_v]))

        return None


class TypedConfig(Generic[T]):
    """Type-safe configuration wrapper"""

    def __init__(self, schema: ConfigSchema, data: Dict[str, Any]):
        self.schema = schema
        self._data = data
        self._validator = SchemaValidator()

        # Validate on initialization
        if not self._validator.validate(data, schema):
            raise ValueError(f"Invalid configuration: {self._validator.errors}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value with validation"""
        # Create temporary config with new value
        temp = self._data.copy()
        temp[key] = value

        # Validate
        if not self._validator.validate(temp, self.schema):
            raise ValueError(f"Invalid value for {key}: {self._validator.errors}")

        self._data[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self._data.copy()

    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access"""
        return self._data[key]

    def __setitem__(self, key: str, value: Any):
        """Dictionary-style setting with validation"""
        self.set(key, value)


# Predefined common schemas
def create_database_schema() -> ConfigSchema:
    """Create common database configuration schema"""
    return (
        SchemaBuilder("Database Configuration")
        .string("host", required=True, default="localhost")
        .integer("port", required=True, minimum=1, maximum=65535, default=5432)
        .string("database", required=True)
        .string("username", required=True)
        .string("password", write_only=True)
        .integer("pool_size", minimum=1, maximum=100, default=10)
        .integer("timeout", minimum=1, default=30)
        .boolean("ssl", default=False)
        .build()
    )


def create_api_schema() -> ConfigSchema:
    """Create common API configuration schema"""
    return (
        SchemaBuilder("API Configuration")
        .string("base_url", required=True, format=SchemaFormat.URI)
        .string("api_key", required=True, write_only=True)
        .integer("timeout", minimum=1, default=30)
        .integer("retry_count", minimum=0, maximum=10, default=3)
        .number("retry_delay", minimum=0, default=1.0)
        .array("allowed_methods", default=["GET", "POST", "PUT", "DELETE"])
        .object("headers", default={})
        .boolean("verify_ssl", default=True)
        .build()
    )


def create_logging_schema() -> ConfigSchema:
    """Create common logging configuration schema"""
    return (
        SchemaBuilder("Logging Configuration")
        .enum(
            "level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO"
        )
        .string(
            "format", default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        .string("file", format=SchemaFormat.PATH)
        .integer("max_size", minimum=1, default=10485760)  # 10MB
        .integer("backup_count", minimum=0, default=5)
        .boolean("console", default=True)
        .boolean("file_enabled", default=False)
        .build()
    )


# Export main components
__all__ = [
    "ConfigMigration",
    "ConfigSchema",
    "SchemaBuilder",
    "SchemaFormat",
    "SchemaProperty",
    "SchemaRegistry",
    "SchemaType",
    "SchemaValidator",
    "TypedConfig",
    "create_api_schema",
    "create_database_schema",
    "create_logging_schema",
]
