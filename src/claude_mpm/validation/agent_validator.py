"""
Agent validation framework inspired by awesome-claude-code validation patterns.

This module provides comprehensive validation for agent configurations with
override support, field locking, and detailed error reporting.
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set, Any
import yaml
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of agent validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    locked_fields: Set[str] = field(default_factory=set)
    applied_overrides: Dict[str, Any] = field(default_factory=dict)


class AgentValidator:
    """Validates agent configurations with override support."""
    
    REQUIRED_FIELDS = ['name', 'version', 'description', 'agents']
    AGENT_REQUIRED_FIELDS = ['name', 'role', 'prompt_template']
    
    def __init__(self, override_file: Optional[Path] = None):
        """Initialize the validator with optional override configuration."""
        self.overrides = {}
        if override_file and override_file.exists():
            self.overrides = self._load_overrides(override_file)
    
    def _load_overrides(self, override_file: Path) -> Dict[str, Any]:
        """Load override configuration from YAML file."""
        try:
            with open(override_file, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('overrides', {})
        except Exception as e:
            logger.warning(f"Failed to load overrides from {override_file}: {e}")
            return {}
    
    def validate_agent_config(self, config: Dict[str, Any], agent_id: str) -> ValidationResult:
        """Validate a single agent configuration."""
        result = ValidationResult(is_valid=True)
        
        # Apply overrides
        config, locked_fields, skip_validation = self._apply_overrides(config, agent_id)
        result.locked_fields = locked_fields
        
        if skip_validation:
            logger.info(f"Skipping validation for agent {agent_id} - marked as skip_validation")
            return result
        
        # Validate required fields
        for field in self.AGENT_REQUIRED_FIELDS:
            if field not in locked_fields and field not in config:
                result.errors.append(f"Missing required field: {field}")
                result.is_valid = False
        
        # Validate prompt template
        if 'prompt_template' in config and 'prompt_template' not in locked_fields:
            template_result = self._validate_prompt_template(config['prompt_template'])
            if not template_result[0]:
                result.errors.extend(template_result[1])
                result.is_valid = False
        
        # Validate tools if present
        if 'tools' in config:
            tools_result = self._validate_tools(config['tools'])
            if not tools_result[0]:
                result.errors.extend(tools_result[1])
                result.is_valid = False
        
        return result
    
    def _apply_overrides(self, config: Dict[str, Any], agent_id: str) -> Tuple[Dict[str, Any], Set[str], bool]:
        """Apply overrides to an agent configuration."""
        if agent_id not in self.overrides:
            return config, set(), False
        
        override_config = self.overrides[agent_id]
        locked_fields = set()
        skip_validation = override_config.get('skip_validation', False)
        
        # Apply each override
        for field, value in override_config.items():
            if field.endswith('_locked'):
                base_field = field.replace('_locked', '')
                if override_config.get(field, False):
                    locked_fields.add(base_field)
            elif field not in ['notes', 'skip_validation']:
                config[field] = value
        
        return config, locked_fields, skip_validation
    
    def _validate_prompt_template(self, template: str) -> Tuple[bool, List[str]]:
        """Validate prompt template format and placeholders."""
        errors = []
        
        if not template or not isinstance(template, str):
            errors.append("Prompt template must be a non-empty string")
            return False, errors
        
        # Check for common placeholders
        expected_placeholders = ['{context}', '{task}', '{constraints}']
        missing_placeholders = []
        
        for placeholder in expected_placeholders:
            if placeholder not in template:
                missing_placeholders.append(placeholder)
        
        if missing_placeholders:
            errors.append(f"Prompt template missing placeholders: {', '.join(missing_placeholders)}")
        
        return len(errors) == 0, errors
    
    def _validate_tools(self, tools: List[str]) -> Tuple[bool, List[str]]:
        """Validate agent tools configuration."""
        errors = []
        
        if not isinstance(tools, list):
            errors.append("Tools must be a list")
            return False, errors
        
        # Known valid tools
        valid_tools = {
            'file_operations', 'code_analysis', 'git_operations',
            'testing', 'documentation', 'security_scan'
        }
        
        for tool in tools:
            if tool not in valid_tools:
                errors.append(f"Unknown tool: {tool}")
        
        return len(errors) == 0, errors
    
    def validate_profile(self, profile_path: Path) -> ValidationResult:
        """Validate an entire agent profile."""
        result = ValidationResult(is_valid=True)
        
        try:
            with open(profile_path, 'r') as f:
                profile_data = yaml.safe_load(f)
        except Exception as e:
            result.errors.append(f"Failed to load profile: {e}")
            result.is_valid = False
            return result
        
        # Validate top-level fields
        for field in self.REQUIRED_FIELDS:
            if field not in profile_data:
                result.errors.append(f"Missing required top-level field: {field}")
                result.is_valid = False
        
        # Validate each agent
        if 'agents' in profile_data:
            for agent_config in profile_data['agents']:
                agent_id = agent_config.get('name', 'unknown')
                agent_result = self.validate_agent_config(agent_config, agent_id)
                
                if not agent_result.is_valid:
                    result.is_valid = False
                    result.errors.extend([f"Agent '{agent_id}': {e}" for e in agent_result.errors])
                
                result.warnings.extend([f"Agent '{agent_id}': {w}" for w in agent_result.warnings])
                result.locked_fields.update(agent_result.locked_fields)
        
        return result