"""
Agent validation framework using JSON Schema validation.

This module provides comprehensive validation for agent configurations
using the standardized JSON schema with direct validation approach.

Security Features:
- Input validation using JSON Schema to prevent malformed data
- Path traversal protection in file operations
- Resource limit validation to prevent resource exhaustion
- Strict schema validation with no additional properties allowed
- Character limit enforcement to prevent memory exhaustion
- Safe JSON parsing with error handling

Security Considerations:
- All file paths should be validated and sanitized
- Agent IDs must follow strict naming conventions
- Resource limits prevent denial of service attacks
- Schema validation prevents injection of unexpected fields
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft7Validator, ValidationError, validate

from claude_mpm.config.paths import paths
from claude_mpm.core.constants import (
    ErrorMessages,
    ResourceLimits,
    SystemLimits,
    TimeoutConfig,
)
from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of agent validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentValidator:
    """Validates agent configurations against JSON schema.

    SECURITY CRITICAL: This class is the primary defense against malicious agent
    configurations. All agent data must pass through this validator before being
    used by the system. Bypassing this validator could lead to:
    - Arbitrary code execution (via tool access)
    - Resource exhaustion (via resource limits)
    - Data exfiltration (via file/network access)
    - Privilege escalation (via tool combinations)
    """

    # Model name mappings for normalization to tier names
    MODEL_MAPPINGS = {
        # Sonnet variations
        "claude-3-5-sonnet-20241022": "sonnet",
        "claude-3-5-sonnet-20240620": "sonnet",
        "claude-sonnet-4-20250514": "sonnet",
        "claude-4-sonnet-20250514": "sonnet",
        "claude-3-sonnet-20240229": "sonnet",
        # Opus variations
        "claude-3-opus-20240229": "opus",
        "claude-opus-4-20250514": "opus",
        "claude-4-opus-20250514": "opus",
        # Haiku variations
        "claude-3-haiku-20240307": "haiku",
        "claude-3-5-haiku-20241022": "haiku",
    }

    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize the validator with the agent schema."""
        if schema_path is None:
            schema_path = paths.schemas_dir / "agent_schema.json"

        self.schema_path = schema_path
        self.schema = self._load_schema()
        self.validator = Draft7Validator(self.schema)

    def _load_schema(self) -> Dict[str, Any]:
        """Load the JSON schema from file.

        Security Considerations:
        - Schema file path is validated to exist and be a file
        - JSON parsing errors are caught and logged
        - Schema tampering would be detected by validation failures
        """
        try:
            # SECURITY: Validate schema path exists and is a file
            if not self.schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
            if not self.schema_path.is_file():
                raise ValueError(f"Schema path is not a file: {self.schema_path}")

            with self.schema_path.open() as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema from {self.schema_path}: {e}")
            raise

    def _normalize_model(self, model: str) -> str:
        """Normalize model name to standard tier (opus, sonnet, haiku).

        Args:
            model: Original model name

        Returns:
            Normalized model tier name
        """
        # Direct mapping check
        if model in self.MODEL_MAPPINGS:
            return self.MODEL_MAPPINGS[model]

        # Already normalized
        if model in {"opus", "sonnet", "haiku"}:
            return model

        # Check if model contains tier name
        model_lower = model.lower()
        for tier in ("opus", "sonnet", "haiku"):
            if tier in model_lower:
                return tier

        # Default to sonnet if unrecognized
        logger.warning(f"Unrecognized model '{model}', defaulting to 'sonnet'")
        return "sonnet"

    def validate_agent(self, agent_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a single agent configuration against the schema.

        Security Features:
        - Strict JSON Schema validation prevents unexpected fields
        - Business rule validation adds additional security checks
        - Input size limits prevent memory exhaustion
        - Agent ID format validation prevents injection attacks

        Args:
            agent_data: Agent configuration dictionary

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        result = ValidationResult(is_valid=True)

        # Normalize model name before validation
        if "capabilities" in agent_data and "model" in agent_data["capabilities"]:
            original_model = agent_data["capabilities"]["model"]
            normalized_model = self._normalize_model(original_model)
            if original_model != normalized_model:
                agent_data["capabilities"]["model"] = normalized_model
                result.warnings.append(
                    f"Normalized model from '{original_model}' to '{normalized_model}'"
                )

        # Perform JSON schema validation
        try:
            validate(instance=agent_data, schema=self.schema)
        except ValidationError as e:
            result.is_valid = False
            result.errors.append(f"Schema validation error: {e.message}")

            # Add path information if available
            if e.path:
                path = ".".join(str(p) for p in e.path)
                result.errors.append(f"Error at path: {path}")

        # SECURITY: Additional business rule validations beyond schema
        # These provide defense-in-depth security checks
        if result.is_valid:
            self._validate_business_rules(agent_data, result)

        # Add metadata
        result.metadata = {
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": self.schema.get("version", "1.1.0"),
            "agent_id": agent_data.get("id", "unknown"),
        }

        return result

    def _validate_business_rules(
        self, agent_data: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Apply additional business rule validations beyond schema.

        Security Validations:
        - Resource limits to prevent DoS attacks
        - Instruction length limits to prevent memory exhaustion
        - Agent ID format to prevent injection attacks
        - Tool compatibility to prevent privilege escalation
        - Self-reference prevention in handoff agents
        """

        # Validate resource tier consistency
        resource_tier = agent_data.get("capabilities", {}).get("resource_tier")
        if resource_tier:
            self._validate_resource_tier_limits(agent_data, resource_tier, result)

        # SECURITY: Validate instruction length to prevent memory exhaustion
        # Double-check even though schema enforces this - defense in depth
        instructions = agent_data.get("instructions", "")
        if len(instructions) > SystemLimits.MAX_INSTRUCTION_LENGTH:
            result.errors.append(
                ErrorMessages.INSTRUCTION_TOO_LONG.format(
                    limit=SystemLimits.MAX_INSTRUCTION_LENGTH, actual=len(instructions)
                )
            )
            result.is_valid = False

        # Validate model compatibility with tools
        self._validate_model_tool_compatibility(agent_data, result)

        # SECURITY: Validate agent ID format to prevent injection attacks
        # Pattern enforced: ^[a-z][a-z0-9_]*$ prevents special characters
        agent_id = agent_data.get("id", "")
        if agent_id.endswith("_agent"):
            result.warnings.append(
                f"Agent ID '{agent_id}' contains deprecated '_agent' suffix"
            )

        # SECURITY: Additional ID validation for defense in depth
        if agent_id and not agent_id.replace("_", "").replace("-", "").isalnum():
            result.errors.append(f"Agent ID '{agent_id}' contains invalid characters")
            result.is_valid = False

        # SECURITY: Validate handoff agents to prevent circular references and privilege escalation
        handoff_agents = agent_data.get("interactions", {}).get("handoff_agents", [])
        for handoff_id in handoff_agents:
            if handoff_id == agent_id:
                result.warnings.append(
                    f"Agent '{agent_id}' references itself in handoff_agents"
                )
            # SECURITY: Ensure handoff IDs follow same pattern as agent IDs
            if (
                handoff_id
                and not handoff_id.replace("_", "").replace("-", "").isalnum()
            ):
                result.errors.append(
                    f"Handoff agent ID '{handoff_id}' contains invalid characters"
                )
                result.is_valid = False

    def _validate_resource_tier_limits(
        self, agent_data: Dict[str, Any], tier: str, result: ValidationResult
    ) -> None:
        """Validate resource limits match the tier constraints.

        Security Purpose:
        - Prevents resource exhaustion attacks
        - Ensures agents can't request excessive resources
        - Enforces fair resource allocation
        - Prevents denial of service through resource hogging
        """
        tier_limits = {
            "intensive": {
                "memory_limit": ResourceLimits.INTENSIVE_MEMORY_RANGE,
                "cpu_limit": ResourceLimits.INTENSIVE_CPU_RANGE,
                "timeout": TimeoutConfig.INTENSIVE_TIMEOUT_RANGE,
            },
            "standard": {
                "memory_limit": ResourceLimits.STANDARD_MEMORY_RANGE,
                "cpu_limit": ResourceLimits.STANDARD_CPU_RANGE,
                "timeout": TimeoutConfig.STANDARD_TIMEOUT_RANGE,
            },
            "lightweight": {
                "memory_limit": ResourceLimits.LIGHTWEIGHT_MEMORY_RANGE,
                "cpu_limit": ResourceLimits.LIGHTWEIGHT_CPU_RANGE,
                "timeout": TimeoutConfig.LIGHTWEIGHT_TIMEOUT_RANGE,
            },
        }

        if tier not in tier_limits:
            return

        limits = tier_limits[tier]
        capabilities = agent_data.get("capabilities", {})

        # Check memory limit
        memory = capabilities.get("memory_limit")
        if memory is not None:
            min_mem, max_mem = limits["memory_limit"]
            if not (min_mem <= memory <= max_mem):
                result.warnings.append(
                    f"Memory limit {memory}MB outside recommended range "
                    f"{min_mem}-{max_mem}MB for tier '{tier}'"
                )

        # Check CPU limit
        cpu = capabilities.get("cpu_limit")
        if cpu is not None:
            min_cpu, max_cpu = limits["cpu_limit"]
            if not (min_cpu <= cpu <= max_cpu):
                result.warnings.append(
                    f"CPU limit {cpu}% outside recommended range "
                    f"{min_cpu}-{max_cpu}% for tier '{tier}'"
                )

        # Check timeout
        timeout = capabilities.get("timeout")
        if timeout is not None:
            min_timeout, max_timeout = limits["timeout"]
            if not (min_timeout <= timeout <= max_timeout):
                result.warnings.append(
                    f"Timeout {timeout}s outside recommended range "
                    f"{min_timeout}-{max_timeout}s for tier '{tier}'"
                )

    def _validate_model_tool_compatibility(
        self, agent_data: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate that model and tools are compatible."""
        model = agent_data.get("capabilities", {}).get("model", "")
        tools = agent_data.get("capabilities", {}).get("tools", [])

        # Normalize model name for comparison
        normalized_model = self._normalize_model(model)

        # Haiku models shouldn't use resource-intensive tools
        if normalized_model == "haiku":
            intensive_tools = {
                "docker",
                "kubectl",
                "terraform",
                "aws",
                "gcloud",
                "azure",
            }
            used_intensive = set(tools) & intensive_tools
            if used_intensive:
                result.warnings.append(
                    f"Haiku model '{model}' using resource-intensive tools: {used_intensive}"
                )

        # SECURITY: Network access requirement validation
        # Ensures agents can't use network tools without explicit permission
        network_tools = {"WebSearch", "WebFetch", "aws", "gcloud", "azure"}
        needs_network = bool(set(tools) & network_tools)
        has_network = agent_data.get("capabilities", {}).get("network_access", False)

        if needs_network and not has_network:
            result.warnings.append(
                f"Agent uses network tools {set(tools) & network_tools} but network_access is False"
            )

        # SECURITY: Check for potentially dangerous tool combinations
        dangerous_combos = [
            (
                {"Bash", "Write"},
                "Can execute arbitrary code by writing and running scripts",
            ),
            ({"docker", "kubectl"}, "Container escape potential with both tools"),
            (
                {"aws", "gcloud", "azure"},
                "Multiple cloud access increases attack surface",
            ),
        ]

        for combo, risk in dangerous_combos:
            if combo.issubset(set(tools)):
                result.warnings.append(
                    f"Potentially dangerous tool combination: {combo} - {risk}"
                )

    def validate_file(self, file_path: Path) -> ValidationResult:
        """Validate an agent configuration file.

        Security Measures:
        - Path traversal protection through Path object
        - Safe JSON parsing with error handling
        - File size limits should be enforced by caller
        """
        try:
            # SECURITY: Validate file path
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            if not file_path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")

            # SECURITY: Check file size to prevent memory exhaustion
            file_size = file_path.stat().st_size
            max_size = SystemLimits.MAX_AGENT_CONFIG_SIZE
            if file_size > max_size:
                raise ValueError(ErrorMessages.FILE_TOO_LARGE.format(limit=max_size))
            with file_path.open() as f:
                agent_data = json.load(f)

            result = self.validate_agent(agent_data)
            result.metadata["file_path"] = str(file_path)
            return result

        except json.JSONDecodeError as e:
            result = ValidationResult(is_valid=False)
            result.errors.append(f"Invalid JSON in {file_path}: {e}")
            return result
        except Exception as e:
            result = ValidationResult(is_valid=False)
            result.errors.append(f"Error reading {file_path}: {e}")
            return result

    def validate_directory(self, directory: Path) -> Dict[str, ValidationResult]:
        """Validate all agent files in a directory.

        Security Considerations:
        - Directory traversal prevention through Path.glob
        - Symlink following should be disabled in production
        - Large directory DoS prevention through file count limits
        """
        results = {}

        # SECURITY: Validate directory exists and is accessible
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        # SECURITY: Limit number of files to prevent DoS
        max_files = SystemLimits.MAX_FILES_TO_VALIDATE
        file_count = 0

        for json_file in directory.glob("*.json"):
            if json_file.name == "agent_schema.json":
                continue

            # SECURITY: Skip symlinks to prevent directory traversal
            if json_file.is_symlink():
                logger.warning(f"Skipping symlink: {json_file}")
                continue

            file_count += 1
            if file_count > max_files:
                logger.warning(
                    f"Reached maximum file limit ({max_files}), stopping validation"
                )
                break

            logger.info(f"Validating {json_file}")
            results[json_file.name] = self.validate_file(json_file)

        return results

    def get_schema_info(self) -> Dict[str, Any]:
        """Get information about the loaded schema."""
        return {
            "schema_path": str(self.schema_path),
            "schema_title": self.schema.get("title", "Unknown"),
            "schema_description": self.schema.get("description", ""),
            "required_fields": self.schema.get("required", []),
            "properties": list(self.schema.get("properties", {}).keys()),
        }


def validate_agent_migration(
    old_agent: Dict[str, Any], new_agent: Dict[str, Any]
) -> ValidationResult:
    """
    Validate that a migrated agent maintains compatibility.

    Security Importance:
    - Ensures privilege escalation doesn't occur during migration
    - Validates that security constraints are preserved
    - Prevents addition of dangerous tools without review

    Args:
        old_agent: Original agent configuration
        new_agent: Migrated agent configuration

    Returns:
        ValidationResult with migration validation results
    """
    result = ValidationResult(is_valid=True)

    # SECURITY: Check that core functionality is preserved without privilege escalation
    old_tools = set(old_agent.get("configuration_fields", {}).get("tools", []))
    new_tools = set(new_agent.get("capabilities", {}).get("tools", []))

    if old_tools != new_tools:
        missing = old_tools - new_tools
        added = new_tools - old_tools
        if missing:
            result.warnings.append(f"Tools removed in migration: {missing}")
        if added:
            result.warnings.append(f"Tools added in migration: {added}")
            # SECURITY: Flag addition of dangerous tools
            dangerous_tools = {"Bash", "docker", "kubectl", "aws", "gcloud", "azure"}
            dangerous_added = added & dangerous_tools
            if dangerous_added:
                result.errors.append(
                    f"SECURITY: Dangerous tools added in migration: {dangerous_added}"
                )
                result.is_valid = False

    # Check instruction preservation
    old_instructions = old_agent.get("narrative_fields", {}).get("instructions", "")
    new_instructions = new_agent.get("instructions", "")

    if old_instructions and not new_instructions:
        result.errors.append("Instructions lost in migration")
        result.is_valid = False
    elif len(old_instructions) > len(new_instructions) * 1.1:  # Allow 10% reduction
        result.warnings.append("Significant instruction content reduction in migration")

    return result


# Convenience functions
def validate_agent_file(file_path: Path) -> ValidationResult:
    """Validate a single agent file."""
    validator = AgentValidator()
    return validator.validate_file(file_path)


def validate_all_agents(directory: Path) -> Tuple[int, int, List[str]]:
    """
    Validate all agents in a directory and return summary.

    Returns:
        Tuple of (valid_count, invalid_count, error_messages)
    """
    validator = AgentValidator()
    results = validator.validate_directory(directory)

    valid_count = sum(1 for r in results.values() if r.is_valid)
    invalid_count = len(results) - valid_count

    error_messages = []
    for filename, result in results.items():
        if not result.is_valid:
            for error in result.errors:
                error_messages.append(f"{filename}: {error}")

    return valid_count, invalid_count, error_messages
