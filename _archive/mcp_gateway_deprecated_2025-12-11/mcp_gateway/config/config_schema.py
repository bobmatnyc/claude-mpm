"""
MCP Gateway Configuration Schema
================================

Defines and validates the configuration schema for MCP Gateway.

Part of ISS-0034: Infrastructure Setup - MCP Gateway Project Foundation
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MCPConfigSchema:
    """
    Configuration schema definition for MCP Gateway.

    This class defines the structure and validation rules for
    MCP Gateway configuration.
    """

    # Schema version for migration support
    SCHEMA_VERSION = "1.0.0"

    # Configuration schema definition
    SCHEMA = {
        "mcp": {
            "type": "object",
            "required": True,
            "properties": {
                "server": {
                    "type": "object",
                    "required": True,
                    "properties": {
                        "name": {"type": "string", "required": True},
                        "version": {"type": "string", "required": True},
                        "description": {"type": "string", "required": False},
                        "communication": {
                            "type": "object",
                            "required": True,
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "required": True,
                                    "enum": ["stdio", "websocket", "http"],
                                },
                                "timeout": {
                                    "type": "number",
                                    "required": False,
                                    "min": 1,
                                    "max": 3600,
                                },
                                "buffer_size": {
                                    "type": "integer",
                                    "required": False,
                                    "min": 1024,
                                    "max": 1048576,
                                },
                            },
                        },
                        "capabilities": {
                            "type": "object",
                            "required": False,
                            "properties": {
                                "tools": {"type": "boolean", "required": False},
                                "resources": {"type": "boolean", "required": False},
                                "prompts": {"type": "boolean", "required": False},
                            },
                        },
                    },
                },
                "tools": {
                    "type": "object",
                    "required": False,
                    "properties": {
                        "enabled": {"type": "boolean", "required": False},
                        "auto_discover": {"type": "boolean", "required": False},
                        "discovery_paths": {
                            "type": "array",
                            "required": False,
                            "items": {"type": "string"},
                        },
                        "timeout_default": {
                            "type": "number",
                            "required": False,
                            "min": 1,
                            "max": 300,
                        },
                        "max_concurrent": {
                            "type": "integer",
                            "required": False,
                            "min": 1,
                            "max": 100,
                        },
                    },
                },
                "logging": {
                    "type": "object",
                    "required": False,
                    "properties": {
                        "level": {
                            "type": "string",
                            "required": False,
                            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        },
                        "file": {"type": "string", "required": False},
                        "max_size": {"type": "string", "required": False},
                        "max_files": {
                            "type": "integer",
                            "required": False,
                            "min": 1,
                            "max": 100,
                        },
                        "format": {
                            "type": "string",
                            "required": False,
                            "enum": ["json", "text"],
                        },
                    },
                },
                "security": {
                    "type": "object",
                    "required": False,
                    "properties": {
                        "validate_schemas": {"type": "boolean", "required": False},
                        "sanitize_inputs": {"type": "boolean", "required": False},
                        "max_request_size": {
                            "type": "integer",
                            "required": False,
                            "min": 1024,
                            "max": 104857600,  # 100MB max
                        },
                        "allowed_tools": {
                            "type": "array",
                            "required": False,
                            "items": {"type": "string"},
                        },
                        "blocked_tools": {
                            "type": "array",
                            "required": False,
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        }
    }


def validate_config(
    config: Dict[str, Any], schema: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Validate configuration against schema.

    Args:
        config: Configuration dictionary to validate
        schema: Schema to validate against (uses default if not provided)

    Returns:
        List of validation errors (empty if valid)
    """
    if schema is None:
        schema = MCPConfigSchema.SCHEMA

    errors = []

    def validate_value(value: Any, spec: Dict[str, Any], path: str) -> None:
        """Recursively validate a value against its specification."""

        # Check type
        expected_type = spec.get("type")
        if expected_type:
            if expected_type == "object" and not isinstance(value, dict):
                errors.append(f"{path}: Expected object, got {type(value).__name__}")
                return
            if expected_type == "array" and not isinstance(value, list):
                errors.append(f"{path}: Expected array, got {type(value).__name__}")
                return
            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"{path}: Expected string, got {type(value).__name__}")
                return
            if expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"{path}: Expected number, got {type(value).__name__}")
                return
            if expected_type == "integer" and not isinstance(value, int):
                errors.append(f"{path}: Expected integer, got {type(value).__name__}")
                return
            if expected_type == "boolean" and not isinstance(value, bool):
                errors.append(f"{path}: Expected boolean, got {type(value).__name__}")
                return

        # Check enum values
        if "enum" in spec and value not in spec["enum"]:
            errors.append(
                f"{path}: Value '{value}' not in allowed values: {spec['enum']}"
            )

        # Check numeric constraints
        if isinstance(value, (int, float)):
            if "min" in spec and value < spec["min"]:
                errors.append(
                    f"{path}: Value {value} is less than minimum {spec['min']}"
                )
            if "max" in spec and value > spec["max"]:
                errors.append(
                    f"{path}: Value {value} is greater than maximum {spec['max']}"
                )

        # Validate object properties
        if expected_type == "object" and isinstance(value, dict):
            properties = spec.get("properties", {})
            for prop_name, prop_spec in properties.items():
                prop_path = f"{path}.{prop_name}"

                if prop_name in value:
                    validate_value(value[prop_name], prop_spec, prop_path)
                elif prop_spec.get("required", False):
                    errors.append(f"{prop_path}: Required field missing")

        # Validate array items
        if expected_type == "array" and isinstance(value, list):
            item_spec = spec.get("items", {})
            for i, item in enumerate(value):
                validate_value(item, item_spec, f"{path}[{i}]")

    # Start validation from root
    validate_value(config, {"type": "object", "properties": schema}, "config")

    return errors


def generate_config_template() -> Dict[str, Any]:
    """
    Generate a configuration template with all possible options.

    Returns:
        Configuration template dictionary
    """
    from ..config.configuration import MCPConfiguration

    return MCPConfiguration.DEFAULT_CONFIG
