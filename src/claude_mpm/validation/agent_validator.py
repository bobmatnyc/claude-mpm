"""
Agent validation framework using JSON Schema validation.

This module provides comprehensive validation for agent configurations
using the standardized JSON schema with direct validation approach.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import jsonschema
from jsonschema import validate, ValidationError, Draft7Validator

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of agent validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentValidator:
    """Validates agent configurations against JSON schema."""
    
    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize the validator with the agent schema."""
        if schema_path is None:
            schema_path = Path(__file__).parent.parent / "schemas" / "agent_schema.json"
        
        self.schema_path = schema_path
        self.schema = self._load_schema()
        self.validator = Draft7Validator(self.schema)
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load the JSON schema from file."""
        try:
            with open(self.schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema from {self.schema_path}: {e}")
            raise
    
    def validate_agent(self, agent_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a single agent configuration against the schema.
        
        Args:
            agent_data: Agent configuration dictionary
            
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        result = ValidationResult(is_valid=True)
        
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
        
        # Additional business rule validations
        if result.is_valid:
            self._validate_business_rules(agent_data, result)
        
        # Add metadata
        result.metadata = {
            "validated_at": datetime.utcnow().isoformat(),
            "schema_version": self.schema.get("version", "1.0.0"),
            "agent_id": agent_data.get("id", "unknown")
        }
        
        return result
    
    def _validate_business_rules(self, agent_data: Dict[str, Any], result: ValidationResult) -> None:
        """Apply additional business rule validations beyond schema."""
        
        # Validate resource tier consistency
        resource_tier = agent_data.get("capabilities", {}).get("resource_tier")
        if resource_tier:
            self._validate_resource_tier_limits(agent_data, resource_tier, result)
        
        # Validate instruction length (double-check)
        instructions = agent_data.get("instructions", "")
        if len(instructions) > 8000:
            result.errors.append(f"Instructions exceed 8000 character limit: {len(instructions)} characters")
            result.is_valid = False
        
        # Validate model compatibility with tools
        self._validate_model_tool_compatibility(agent_data, result)
        
        # Validate agent ID format (clean IDs without _agent suffix)
        agent_id = agent_data.get("id", "")
        if agent_id.endswith("_agent"):
            result.warnings.append(f"Agent ID '{agent_id}' contains deprecated '_agent' suffix")
        
        # Validate handoff agents exist
        handoff_agents = agent_data.get("interactions", {}).get("handoff_agents", [])
        for handoff_id in handoff_agents:
            if handoff_id == agent_id:
                result.warnings.append(f"Agent '{agent_id}' references itself in handoff_agents")
    
    def _validate_resource_tier_limits(self, agent_data: Dict[str, Any], tier: str, result: ValidationResult) -> None:
        """Validate resource limits match the tier constraints."""
        tier_limits = {
            "intensive": {
                "memory_limit": (4096, 8192),
                "cpu_limit": (60, 100),
                "timeout": (600, 3600)
            },
            "standard": {
                "memory_limit": (2048, 4096),
                "cpu_limit": (30, 60),
                "timeout": (300, 1200)
            },
            "lightweight": {
                "memory_limit": (512, 2048),
                "cpu_limit": (10, 30),
                "timeout": (30, 600)
            }
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
    
    def _validate_model_tool_compatibility(self, agent_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate that model and tools are compatible."""
        model = agent_data.get("capabilities", {}).get("model", "")
        tools = agent_data.get("capabilities", {}).get("tools", [])
        
        # Haiku models shouldn't use resource-intensive tools
        if "haiku" in model.lower():
            intensive_tools = {"docker", "kubectl", "terraform", "aws", "gcloud", "azure"}
            used_intensive = set(tools) & intensive_tools
            if used_intensive:
                result.warnings.append(
                    f"Haiku model '{model}' using resource-intensive tools: {used_intensive}"
                )
        
        # Network access requirement
        network_tools = {"WebSearch", "WebFetch", "aws", "gcloud", "azure"}
        needs_network = bool(set(tools) & network_tools)
        has_network = agent_data.get("capabilities", {}).get("network_access", False)
        
        if needs_network and not has_network:
            result.warnings.append(
                f"Agent uses network tools {set(tools) & network_tools} but network_access is False"
            )
    
    def validate_file(self, file_path: Path) -> ValidationResult:
        """Validate an agent configuration file."""
        try:
            with open(file_path, 'r') as f:
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
        """Validate all agent files in a directory."""
        results = {}
        
        for json_file in directory.glob("*.json"):
            if json_file.name == "agent_schema.json":
                continue
            
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
            "properties": list(self.schema.get("properties", {}).keys())
        }


def validate_agent_migration(old_agent: Dict[str, Any], new_agent: Dict[str, Any]) -> ValidationResult:
    """
    Validate that a migrated agent maintains compatibility.
    
    Args:
        old_agent: Original agent configuration
        new_agent: Migrated agent configuration
        
    Returns:
        ValidationResult with migration validation results
    """
    result = ValidationResult(is_valid=True)
    
    # Check that core functionality is preserved
    old_tools = set(old_agent.get("configuration_fields", {}).get("tools", []))
    new_tools = set(new_agent.get("capabilities", {}).get("tools", []))
    
    if old_tools != new_tools:
        missing = old_tools - new_tools
        added = new_tools - old_tools
        if missing:
            result.warnings.append(f"Tools removed in migration: {missing}")
        if added:
            result.warnings.append(f"Tools added in migration: {added}")
    
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