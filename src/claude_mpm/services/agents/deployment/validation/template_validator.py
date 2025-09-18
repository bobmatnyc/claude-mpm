"""Template validator for agent templates."""

import json
from pathlib import Path
from typing import Any, Dict

from claude_mpm.core.logger import get_logger

from .validation_result import ValidationResult


class TemplateValidator:
    """Validator for agent template files.

    This validator checks agent template JSON files for:
    - Valid JSON syntax
    - Required fields according to agent schema
    - Field value validation
    - Schema compliance
    """

    def __init__(self):
        """Initialize the template validator."""
        self.logger = get_logger(__name__)

        # Required fields according to agent schema
        self.required_fields = {
            "schema_version": str,
            "agent_id": str,
            "agent_version": str,
            "agent_type": str,
            "metadata": dict,
            "capabilities": dict,
            "instructions": str,
        }

        # Required metadata fields
        self.required_metadata_fields = {
            "name": str,
            "description": str,
            "category": str,
            "tags": list,
        }

        # Required capabilities fields
        self.required_capabilities_fields = {
            "model": str,
            "resource_tier": str,
        }

        # Instructions is now a string field, not a dictionary

    def validate_template_file(self, template_file: Path) -> ValidationResult:
        """Validate a template file.

        Args:
            template_file: Path to template file

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult(is_valid=True)

        # Check if file exists
        if not template_file.exists():
            result.add_error(f"Template file does not exist: {template_file}")
            return result

        # Check if it's a file
        if not template_file.is_file():
            result.add_error(f"Template path is not a file: {template_file}")
            return result

        try:
            # Read and parse JSON
            content = template_file.read_text(encoding="utf-8")
            template_data = json.loads(content)

            # Validate structure
            self._validate_template_structure(template_data, result)

            # Validate metadata
            if "metadata" in template_data:
                self._validate_metadata(template_data["metadata"], result)

            # Validate capabilities
            if "capabilities" in template_data:
                self._validate_capabilities(template_data["capabilities"], result)

            # Validate instructions (now a string field)
            if "instructions" in template_data:
                self._validate_instructions_string(
                    template_data["instructions"], result
                )

            # Validate agent ID format
            if "agent_id" in template_data:
                self._validate_agent_id(template_data["agent_id"], result)

            # Add metadata
            result.metadata["template_file"] = str(template_file)
            result.metadata["agent_id"] = template_data.get("agent_id", "unknown")

        except json.JSONDecodeError as e:
            result.add_error(
                f"Invalid JSON syntax: {e}", line_number=getattr(e, "lineno", None)
            )
        except UnicodeDecodeError as e:
            result.add_error(f"File encoding error: {e}")
        except Exception as e:
            result.add_error(f"Unexpected error reading template: {e}")

        return result

    def _validate_template_structure(
        self, template_data: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate the basic template structure.

        Args:
            template_data: Template data dictionary
            result: ValidationResult to update
        """
        # Check required fields
        for field, expected_type in self.required_fields.items():
            if field not in template_data:
                result.add_error(f"Missing required field: {field}")
            else:
                value = template_data[field]
                if not isinstance(value, expected_type):
                    result.add_error(
                        f"Field '{field}' should be {expected_type.__name__}, got {type(value).__name__}",
                        field_name=field,
                    )

        # Check schema version
        if "schema_version" in template_data:
            schema_version = template_data["schema_version"]
            if not schema_version.startswith("1."):
                result.add_warning(
                    f"Schema version '{schema_version}' may not be supported",
                    field_name="schema_version",
                    suggestion="Use schema version 1.x.x",
                )

    def _validate_metadata(
        self, metadata: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate metadata section.

        Args:
            metadata: Metadata dictionary
            result: ValidationResult to update
        """
        for field, expected_type in self.required_metadata_fields.items():
            if field not in metadata:
                result.add_error(
                    f"Missing required metadata field: {field}",
                    field_name=f"metadata.{field}",
                )
            else:
                value = metadata[field]
                if not isinstance(value, expected_type):
                    result.add_error(
                        f"Metadata field '{field}' should be {expected_type.__name__}, got {type(value).__name__}",
                        field_name=f"metadata.{field}",
                    )

        # Validate specific fields
        if "name" in metadata:
            name = metadata["name"]
            if not name or not name.strip():
                result.add_error(
                    "Agent name cannot be empty", field_name="metadata.name"
                )

        if "description" in metadata:
            description = metadata["description"]
            if not description or not description.strip():
                result.add_error(
                    "Agent description cannot be empty",
                    field_name="metadata.description",
                )
            elif len(description) < 10:
                result.add_warning(
                    "Agent description is very short",
                    field_name="metadata.description",
                    suggestion="Provide a more detailed description",
                )

        if "tags" in metadata:
            tags = metadata["tags"]
            if isinstance(tags, str):
                # Convert comma-separated string to list for validation
                tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
                if len(tag_list) == 0:
                    result.add_warning("No tags specified", field_name="metadata.tags")
            elif isinstance(tags, list):
                if len(tags) == 0:
                    result.add_warning("No tags specified", field_name="metadata.tags")
            else:
                result.add_error(
                    "Tags should be a list or comma-separated string",
                    field_name="metadata.tags",
                )

    def _validate_capabilities(
        self, capabilities: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate capabilities section.

        Args:
            capabilities: Capabilities dictionary
            result: ValidationResult to update
        """
        for field, expected_type in self.required_capabilities_fields.items():
            if field not in capabilities:
                result.add_error(
                    f"Missing required capabilities field: {field}",
                    field_name=f"capabilities.{field}",
                )
            else:
                value = capabilities[field]
                if not isinstance(value, expected_type):
                    result.add_error(
                        f"Capabilities field '{field}' should be {expected_type.__name__}, got {type(value).__name__}",
                        field_name=f"capabilities.{field}",
                    )

        # Validate model
        if "model" in capabilities:
            model = capabilities["model"]
            valid_models = ["sonnet", "haiku", "opus"]
            if model not in valid_models:
                result.add_warning(
                    f"Unknown model '{model}'",
                    field_name="capabilities.model",
                    suggestion=f"Use one of: {', '.join(valid_models)}",
                )

        # Validate tools (optional field but validate if present)
        if "tools" in capabilities:
            tools = capabilities["tools"]
            if not isinstance(tools, list):
                result.add_error(
                    "Tools should be a list", field_name="capabilities.tools"
                )
            elif len(tools) == 0:
                result.add_warning(
                    "No tools specified", field_name="capabilities.tools"
                )

        # Validate resource_tier
        if "resource_tier" in capabilities:
            resource_tier = capabilities["resource_tier"]
            valid_tiers = ["basic", "standard", "intensive", "lightweight", "high"]
            if resource_tier not in valid_tiers:
                result.add_warning(
                    f"Unknown resource tier '{resource_tier}'",
                    field_name="capabilities.resource_tier",
                    suggestion=f"Use one of: {', '.join(valid_tiers)}",
                )

    def _validate_instructions_string(
        self, instructions: str, result: ValidationResult
    ) -> None:
        """Validate instructions string.

        Args:
            instructions: Instructions string
            result: ValidationResult to update
        """
        # Check if instructions is actually a string
        if not isinstance(instructions, str):
            result.add_error(
                f"Instructions should be a string, got {type(instructions).__name__}",
                field_name="instructions",
            )
            return

        # Check if instructions is not empty
        if not instructions or not instructions.strip():
            result.add_error(
                "Instructions cannot be empty",
                field_name="instructions",
            )
        elif len(instructions) < 20:
            result.add_warning(
                "Instructions are very short",
                field_name="instructions",
                suggestion="Provide more detailed instructions",
            )

        # Check for file references that might be invalid
        if instructions.startswith("file:"):
            file_ref = instructions[5:]  # Remove "file:" prefix
            result.add_warning(
                f"Instructions reference external file: {file_ref}",
                field_name="instructions",
                suggestion="Consider embedding instructions directly or ensure the referenced file exists",
            )

    def _validate_agent_id(self, agent_id: str, result: ValidationResult) -> None:
        """Validate agent ID format.

        Args:
            agent_id: Agent ID to validate
            result: ValidationResult to update
        """
        import re

        # Agent ID should be lowercase with hyphens
        pattern = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
        if not re.match(pattern, agent_id):
            result.add_error(
                f"Invalid agent ID format: '{agent_id}'",
                field_name="agent_id",
                suggestion="Use lowercase letters, numbers, and hyphens only (e.g., 'my-agent')",
            )
