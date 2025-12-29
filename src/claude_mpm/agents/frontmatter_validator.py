#!/usr/bin/env python3
"""
Frontmatter Validator for Agent Files
=====================================

This module provides validation and automatic correction for agent file frontmatter
in .md, .claude, and .claude-mpm files. It ensures consistency and compatibility
across different agent file formats.

Key Features:
- Validates frontmatter against a defined schema
- Automatically corrects common formatting issues
- Normalizes model names to standard tiers (opus, sonnet, haiku)
- Fixes tools field when provided as string representation
- Provides detailed logging of corrections made
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from claude_mpm.core.enums import ModelTier
from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of frontmatter validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    corrections: List[str]
    corrected_frontmatter: Optional[Dict[str, Any]] = None
    field_corrections: Optional[Dict[str, Any]] = (
        None  # Specific field-level corrections
    )


class FrontmatterValidator:
    """
    Validates and corrects frontmatter in agent files.

    This class handles:
    - Schema validation against frontmatter_schema.json
    - Automatic correction of common issues
    - Model name normalization
    - Tools field parsing and correction
    - Logging of all corrections made
    """

    # NOTE: Model normalization now handled by ModelTier.normalize()
    # This enum-based approach replaced 26 lines of manual mappings

    # Tool name corrections (case normalization)
    TOOL_CORRECTIONS = {
        "read": "Read",
        "write": "Write",
        "edit": "Edit",
        "multiedit": "MultiEdit",
        "grep": "Grep",
        "glob": "Glob",
        "ls": "LS",
        "bash": "Bash",
        "websearch": "WebSearch",
        "webfetch": "WebFetch",
        "notebookread": "NotebookRead",
        "notebookedit": "NotebookEdit",
        "todowrite": "TodoWrite",
        "exitplanmode": "ExitPlanMode",
    }

    # Valid tool names
    VALID_TOOLS = {
        "Read",
        "Write",
        "Edit",
        "MultiEdit",
        "Grep",
        "Glob",
        "LS",
        "Bash",
        "WebSearch",
        "WebFetch",
        "NotebookRead",
        "NotebookEdit",
        "TodoWrite",
        "ExitPlanMode",
        "git",
        "docker",
        "kubectl",
        "terraform",
        "aws",
        "gcloud",
        "azure",
    }

    # Valid model tiers
    VALID_MODELS = {"opus", "sonnet", "haiku"}

    def __init__(self):
        """Initialize the validator with schema if available."""
        self.schema = self._load_schema()
        self.all_valid_fields = self._extract_valid_fields()

    def _load_schema(self) -> Optional[Dict[str, Any]]:
        """Load the frontmatter schema from JSON file."""
        schema_path = (
            Path(__file__).parent.parent / "schemas" / "frontmatter_schema.json"
        )
        if schema_path.exists():
            try:
                with schema_path.open() as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load frontmatter schema: {e}")
        return None

    def _extract_valid_fields(self) -> set:
        """Extract all valid field names from the schema."""
        if self.schema and "properties" in self.schema:
            return set(self.schema["properties"].keys())
        # Fallback to known fields if schema not available
        return {
            "name",
            "description",
            "version",
            "base_version",
            "author",
            "tools",
            "model",
            "tags",
            "category",
            "max_tokens",
            "temperature",
            "resource_tier",
            "dependencies",
            "capabilities",
            "color",
            # NEW: Collection-based identification fields
            "collection_id",
            "source_path",
            "canonical_id",
        }

    def validate_and_correct(self, frontmatter: Dict[str, Any]) -> ValidationResult:
        """
        Validate and automatically correct frontmatter.

        Args:
            frontmatter: Dictionary of frontmatter fields

        Returns:
            ValidationResult with validation status and corrected frontmatter
        """
        errors: List[str] = []
        warnings: List[str] = []
        corrections: List[str] = []
        corrected = frontmatter.copy()
        field_corrections: Dict[str, Any] = {}

        # Check required fields
        self._validate_required_fields(corrected, errors)

        # Validate and correct individual fields
        self._validate_name_field(corrected, field_corrections, errors, corrections)
        self._validate_model_field(corrected, field_corrections, errors, corrections)
        self._validate_tools_field(corrected, field_corrections, warnings, corrections)
        self._validate_version_fields(corrected, field_corrections, errors, corrections)
        self._validate_description_field(corrected, errors, warnings)
        self._validate_category_field(corrected, warnings)
        self._validate_resource_tier_field(corrected, warnings)
        self._validate_color_field(corrected, errors)
        self._validate_author_field(corrected, errors, warnings)
        self._validate_tags_field(corrected, errors, warnings)
        self._validate_numeric_fields(corrected, errors, warnings)
        # NEW: Validate collection-based identification fields
        self._validate_collection_fields(corrected, field_corrections, errors, warnings)

        # Determine if valid
        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            corrections=corrections,
            corrected_frontmatter=corrected if corrections else None,
            field_corrections=field_corrections if field_corrections else None,
        )

    def _validate_required_fields(
        self, corrected: Dict[str, Any], errors: List[str]
    ) -> None:
        """Check that all required fields are present."""
        required_fields = (
            self.schema.get("required", ["name", "description", "version"])
            if self.schema
            else ["name", "description", "version"]
        )
        for field in required_fields:
            if field not in corrected:
                errors.append(f"Missing required field: {field}")

    def _validate_name_field(
        self,
        corrected: Dict[str, Any],
        field_corrections: Dict[str, Any],
        errors: List[str],
        corrections: List[str],
    ) -> None:
        """Validate and correct the name field."""
        if "name" not in corrected:
            return

        name = corrected["name"]
        if not isinstance(name, str):
            errors.append(f"Field 'name' must be a string, got {type(name).__name__}")
            return

        if not re.match(r"^[a-z][a-z0-9_]*$", name):
            # Try to fix the name
            fixed_name = name.lower().replace("-", "_").replace(" ", "_")
            fixed_name = re.sub(r"[^a-z0-9_]", "", fixed_name)
            if fixed_name and fixed_name[0].isalpha():
                corrected["name"] = fixed_name
                field_corrections["name"] = fixed_name
                corrections.append(f"Corrected name from '{name}' to '{fixed_name}'")
            else:
                errors.append(f"Invalid name format: {name}")

    def _validate_model_field(
        self,
        corrected: Dict[str, Any],
        field_corrections: Dict[str, Any],
        errors: List[str],
        corrections: List[str],
    ) -> None:
        """Validate and correct the model field."""
        if "model" not in corrected:
            return

        model = corrected["model"]

        # Convert to string if it's a number (YAML might parse dates as integers)
        if isinstance(model, (int, float)):
            model = str(model)
            corrected["model"] = model
            field_corrections["model"] = model
            corrections.append(f"Converted model from number to string: {model}")

        if not isinstance(model, str):
            errors.append(f"Field 'model' must be a string, got {type(model).__name__}")
            return

        normalized_model = self._normalize_model(model)
        if normalized_model != model:
            corrected["model"] = normalized_model
            field_corrections["model"] = normalized_model
            corrections.append(
                f"Normalized model from '{model}' to '{normalized_model}'"
            )

        if normalized_model not in self.VALID_MODELS:
            errors.append(f"Invalid model: {model} (normalized to {normalized_model})")

    def _validate_tools_field(
        self,
        corrected: Dict[str, Any],
        field_corrections: Dict[str, Any],
        warnings: List[str],
        corrections: List[str],
    ) -> None:
        """Validate and correct the tools field."""
        if "tools" not in corrected:
            return

        tools = corrected["tools"]
        corrected_tools, tool_corrections = self._correct_tools(tools)
        if tool_corrections:
            corrected["tools"] = corrected_tools
            field_corrections["tools"] = corrected_tools
            corrections.extend(tool_corrections)

        # Validate tool names
        invalid_tools = []
        for tool in corrected_tools:
            if tool not in self.VALID_TOOLS:
                # Try to correct the tool name
                corrected_tool = self.TOOL_CORRECTIONS.get(tool.lower())
                if corrected_tool:
                    idx = corrected_tools.index(tool)
                    corrected_tools[idx] = corrected_tool
                    corrected["tools"] = corrected_tools
                    field_corrections["tools"] = corrected_tools
                    corrections.append(f"Corrected tool '{tool}' to '{corrected_tool}'")
                else:
                    invalid_tools.append(tool)

        if invalid_tools:
            warnings.append(f"Unknown tools: {', '.join(invalid_tools)}")

    def _validate_version_fields(
        self,
        corrected: Dict[str, Any],
        field_corrections: Dict[str, Any],
        errors: List[str],
        corrections: List[str],
    ) -> None:
        """Validate and correct version fields."""
        version_fields = ["version", "base_version"]
        for field in version_fields:
            if field not in corrected:
                continue

            version = corrected[field]
            if not isinstance(version, str):
                errors.append(
                    f"Field '{field}' must be a string, got {type(version).__name__}"
                )
                continue

            if re.match(r"^\d+\.\d+\.\d+$", version):
                continue  # Valid format

            # Try to fix common version issues
            if re.match(r"^\d+\.\d+$", version):
                fixed_version = f"{version}.0"
                corrected[field] = fixed_version
                field_corrections[field] = fixed_version
                corrections.append(
                    f"Fixed {field} from '{version}' to '{fixed_version}'"
                )
            elif re.match(r"^v?\d+\.\d+\.\d+$", version):
                fixed_version = version.lstrip("v")
                corrected[field] = fixed_version
                field_corrections[field] = fixed_version
                corrections.append(
                    f"Fixed {field} from '{version}' to '{fixed_version}'"
                )
            else:
                errors.append(f"Invalid {field} format: {version}")

    def _validate_description_field(
        self, corrected: Dict[str, Any], errors: List[str], warnings: List[str]
    ) -> None:
        """Validate the description field."""
        if "description" not in corrected:
            return

        desc = corrected["description"]
        if not isinstance(desc, str):
            errors.append(
                f"Field 'description' must be a string, got {type(desc).__name__}"
            )
        elif len(desc) < 10:
            warnings.append(f"Description too short ({len(desc)} chars, minimum 10)")
        elif len(desc) > 200:
            warnings.append(f"Description too long ({len(desc)} chars, maximum 200)")

    def _validate_category_field(
        self, corrected: Dict[str, Any], warnings: List[str]
    ) -> None:
        """Validate the category field."""
        if "category" not in corrected:
            return

        valid_categories = [
            "engineering",
            "research",
            "quality",
            "operations",
            "specialized",
        ]
        if corrected["category"] not in valid_categories:
            warnings.append(f"Invalid category: {corrected['category']}")

    def _validate_resource_tier_field(
        self, corrected: Dict[str, Any], warnings: List[str]
    ) -> None:
        """Validate the resource_tier field."""
        if "resource_tier" not in corrected:
            return

        valid_tiers = ["basic", "standard", "intensive", "lightweight"]
        if corrected["resource_tier"] not in valid_tiers:
            warnings.append(f"Invalid resource_tier: {corrected['resource_tier']}")

    def _validate_color_field(
        self, corrected: Dict[str, Any], errors: List[str]
    ) -> None:
        """Validate the color field."""
        if "color" not in corrected:
            return

        color = corrected["color"]
        if not isinstance(color, str):
            errors.append(f"Field 'color' must be a string, got {type(color).__name__}")

    def _validate_author_field(
        self, corrected: Dict[str, Any], errors: List[str], warnings: List[str]
    ) -> None:
        """Validate the author field."""
        if "author" not in corrected:
            return

        author = corrected["author"]
        if not isinstance(author, str):
            errors.append(
                f"Field 'author' must be a string, got {type(author).__name__}"
            )
        elif len(author) > 100:
            warnings.append(f"Author field too long ({len(author)} chars, maximum 100)")

    def _validate_tags_field(
        self, corrected: Dict[str, Any], errors: List[str], warnings: List[str]
    ) -> None:
        """Validate the tags field."""
        if "tags" not in corrected:
            return

        tags = corrected["tags"]
        if isinstance(tags, str):
            # Convert comma-separated string to list for validation
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            tag_list = tags
        else:
            errors.append(
                f"Field 'tags' must be a list or comma-separated string, got {type(tags).__name__}"
            )
            return

        for tag in tag_list:
            if not isinstance(tag, str):
                errors.append(f"All tags must be strings, found {type(tag).__name__}")
            elif not re.match(r"^[a-z][a-z0-9-]*$", tag):
                warnings.append(
                    f"Tag '{tag}' doesn't match recommended pattern (lowercase, alphanumeric with hyphens)"
                )

    def _validate_numeric_fields(
        self, corrected: Dict[str, Any], errors: List[str], warnings: List[str]
    ) -> None:
        """Validate numeric fields (max_tokens, temperature)."""
        for field_name, (min_val, max_val) in [
            ("max_tokens", (1000, 200000)),
            ("temperature", (0, 1)),
        ]:
            if field_name not in corrected:
                continue

            value = corrected[field_name]
            if field_name == "temperature" and not isinstance(value, (int, float)):
                errors.append(
                    f"Field '{field_name}' must be a number, got {type(value).__name__}"
                )
            elif field_name == "max_tokens" and not isinstance(value, int):
                errors.append(
                    f"Field '{field_name}' must be an integer, got {type(value).__name__}"
                )
            elif isinstance(value, (int, float)) and not (min_val <= value <= max_val):
                warnings.append(
                    f"Field '{field_name}' value {value} outside recommended range [{min_val}, {max_val}]"
                )

    def _validate_collection_fields(
        self,
        corrected: Dict[str, Any],
        field_corrections: Dict[str, Any],
        errors: List[str],
        warnings: List[str],
    ) -> None:
        """Validate collection-based identification fields.

        NEW: Validates collection_id, source_path, and canonical_id fields.

        These fields are auto-populated by RemoteAgentDiscoveryService for remote agents
        and should follow specific formats:
        - collection_id: "owner/repo-name" (e.g., "bobmatnyc/claude-mpm-agents")
        - source_path: Relative path in repo (e.g., "agents/pm.md")
        - canonical_id: "collection_id:agent_id" or "legacy:filename"
        """
        # Validate collection_id format (optional field)
        if "collection_id" in corrected:
            collection_id = corrected["collection_id"]
            if not isinstance(collection_id, str):
                errors.append(
                    f"Field 'collection_id' must be a string, got {type(collection_id).__name__}"
                )
            elif "/" not in collection_id:
                warnings.append(
                    f"Field 'collection_id' should be in format 'owner/repo-name', got '{collection_id}'"
                )

        # Validate source_path format (optional field)
        if "source_path" in corrected:
            source_path = corrected["source_path"]
            if not isinstance(source_path, str):
                errors.append(
                    f"Field 'source_path' must be a string, got {type(source_path).__name__}"
                )

        # Validate canonical_id format (optional field)
        if "canonical_id" in corrected:
            canonical_id = corrected["canonical_id"]
            if not isinstance(canonical_id, str):
                errors.append(
                    f"Field 'canonical_id' must be a string, got {type(canonical_id).__name__}"
                )
            elif ":" not in canonical_id:
                warnings.append(
                    f"Field 'canonical_id' should be in format 'collection:agent_id' or 'legacy:filename', got '{canonical_id}'"
                )

        # Auto-generate canonical_id if collection_id is present but canonical_id is missing
        if "collection_id" in corrected and "canonical_id" not in corrected:
            collection_id = corrected["collection_id"]
            agent_id = corrected.get("name", "unknown")

            # Generate canonical_id
            canonical_id = f"{collection_id}:{agent_id}"
            corrected["canonical_id"] = canonical_id
            field_corrections["canonical_id"] = canonical_id
            warnings.append(
                f"Auto-generated canonical_id: '{canonical_id}' from collection_id and name"
            )

    def _normalize_model(self, model: str) -> str:
        """
        Normalize model name to standard tier using ModelTier enum.

        Args:
            model: Original model name

        Returns:
            Normalized model tier name
        """
        return ModelTier.normalize(model).value

    def _correct_tools(self, tools: Any) -> Tuple[List[str], List[str]]:
        """
        Correct tools field formatting issues.

        Args:
            tools: Original tools value (could be string, list, etc.)

        Returns:
            Tuple of (corrected_tools_list, list_of_corrections)
        """
        corrections = []

        # If already a proper list, just validate
        if isinstance(tools, list):
            return tools, corrections

        # If it's a string, try to parse it
        if isinstance(tools, str):
            # Remove any surrounding whitespace
            tools_str = tools.strip()

            # Check if it's a string representation of a list
            if tools_str.startswith("[") and tools_str.endswith("]"):
                # Try to parse as JSON array
                try:
                    parsed_tools = json.loads(tools_str)
                    if isinstance(parsed_tools, list):
                        corrections.append(
                            f"Parsed tools from JSON string: {tools_str[:50]}..."
                        )
                        return parsed_tools, corrections
                except json.JSONDecodeError:
                    pass

                # Try to extract comma-separated values
                tools_str = tools_str[1:-1]  # Remove brackets

            # Split by comma and clean up
            if "," in tools_str:
                tool_list = [t.strip().strip("'\"") for t in tools_str.split(",")]
            else:
                # Single tool or space-separated
                tool_list = tools_str.replace(",", " ").split()

            # Clean up tool names
            cleaned_tools = []
            for tool in tool_list:
                tool = tool.strip().strip("'\"")
                if tool:
                    cleaned_tools.append(tool)

            if cleaned_tools:
                corrections.append(
                    f"Converted tools from string to list: {len(cleaned_tools)} tools"
                )
                return cleaned_tools, corrections

        # If we can't parse it, return empty list
        corrections.append(
            f"Could not parse tools field (type: {type(tools).__name__}), using empty list"
        )
        return [], corrections

    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Validate frontmatter in a specific file.

        Args:
            file_path: Path to agent file

        Returns:
            ValidationResult with validation status
        """
        try:
            with file_path.open() as f:
                content = f.read()

            # Extract frontmatter
            frontmatter = self._extract_frontmatter(content)
            if not frontmatter:
                return ValidationResult(
                    is_valid=False,
                    errors=["No frontmatter found in file"],
                    warnings=[],
                    corrections=[],
                )

            # Validate and correct
            return self.validate_and_correct(frontmatter)

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error reading file: {e}"],
                warnings=[],
                corrections=[],
            )

    def _extract_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract frontmatter from file content.

        Args:
            content: File content

        Returns:
            Parsed frontmatter dictionary or None
        """
        # Check for YAML frontmatter (between --- markers)
        if content.startswith("---"):
            try:
                end_marker = content.find("\n---\n", 4)
                if end_marker == -1:
                    end_marker = content.find("\n---\r\n", 4)

                if end_marker != -1:
                    frontmatter_str = content[4:end_marker]
                    return yaml.safe_load(frontmatter_str)
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse YAML frontmatter: {e}")

        return None

    def correct_file(self, file_path: Path, dry_run: bool = False) -> ValidationResult:
        """
        Validate and optionally correct a file's frontmatter.

        Args:
            file_path: Path to agent file
            dry_run: If True, don't write changes to file

        Returns:
            ValidationResult with corrections made
        """
        result = self.validate_file(file_path)

        if result.field_corrections and not dry_run:
            try:
                with file_path.open() as f:
                    content = f.read()

                # Find frontmatter boundaries
                if content.startswith("---"):
                    end_marker = content.find("\n---\n", 4)
                    if end_marker == -1:
                        end_marker = content.find("\n---\r\n", 4)

                    if end_marker != -1:
                        # Apply field-level corrections to preserve structure
                        frontmatter_content = content[4:end_marker]
                        corrected_content = self._apply_field_corrections(
                            frontmatter_content, result.field_corrections
                        )

                        if corrected_content != frontmatter_content:
                            new_content = f"---\n{corrected_content}\n---\n{content[end_marker + 5 :]}"

                            with file_path.open("w") as f:
                                f.write(new_content)

                            logger.info(f"Corrected frontmatter in {file_path}")
                            for correction in result.corrections:
                                logger.info(f"  - {correction}")
            except Exception as e:
                logger.error(f"Failed to write corrections to {file_path}: {e}")

        return result

    def _apply_field_corrections(
        self, frontmatter_content: str, field_corrections: Dict[str, Any]
    ) -> str:
        """
        Apply field-level corrections while preserving structure and other fields.

        Args:
            frontmatter_content: Original YAML frontmatter content
            field_corrections: Dict of field corrections to apply

        Returns:
            Corrected frontmatter content
        """
        lines = frontmatter_content.strip().split("\n")
        corrected_lines = []

        for line in lines:
            # Check if this line contains a field we need to correct
            if ":" in line:
                field_name = line.split(":")[0].strip()
                if field_name in field_corrections:
                    # Replace the field value while preserving structure
                    corrected_value = field_corrections[field_name]
                    if isinstance(corrected_value, list):
                        # Handle list fields like tools
                        if field_name == "tools" and isinstance(corrected_value, list):
                            # Format as comma-separated string to preserve existing format
                            corrected_lines.append(
                                f"{field_name}: {','.join(corrected_value)}"
                            )
                        else:
                            corrected_lines.append(f"{field_name}: {corrected_value}")
                    else:
                        corrected_lines.append(f"{field_name}: {corrected_value}")
                    continue

            # Keep the original line if no correction needed
            corrected_lines.append(line)

        return "\n".join(corrected_lines)
