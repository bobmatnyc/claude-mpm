#!/usr/bin/env python3
"""
Unified Agent Loader System
==========================

Provides unified loading of agent prompts from JSON template files using
the new standardized schema format.

Key Features:
- Loads agent prompts from src/claude_mpm/agents/templates/*.json files
- Handles base_agent.md prepending
- Provides backward-compatible get_*_agent_prompt() functions
- Uses SharedPromptCache for performance
- Validates agents against schema before loading

Usage:
    from claude_pm.agents.agent_loader import get_documentation_agent_prompt
    
    # Get agent prompt from JSON template
    prompt = get_documentation_agent_prompt()
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union, List

from ..services.shared_prompt_cache import SharedPromptCache
from .base_agent_loader import prepend_base_instructions
from ..validation.agent_validator import AgentValidator, ValidationResult
from ..utils.paths import PathResolver

# Temporary placeholders for missing module
class ComplexityLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ModelType:
    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"

# Module-level logger
logger = logging.getLogger(__name__)


def _get_agent_templates_dir() -> Path:
    """Get the agent templates directory."""
    return Path(__file__).parent / "templates"


# Agent templates directory
AGENT_TEMPLATES_DIR = _get_agent_templates_dir()

# Cache prefix for agent prompts
AGENT_CACHE_PREFIX = "agent_prompt:v2:"

# Model configuration thresholds
MODEL_THRESHOLDS = {
    ModelType.HAIKU: {"min_complexity": 0, "max_complexity": 30},
    ModelType.SONNET: {"min_complexity": 31, "max_complexity": 70},
    ModelType.OPUS: {"min_complexity": 71, "max_complexity": 100}
}

# Model name mappings for Claude API (updated for new schema)
MODEL_NAME_MAPPINGS = {
    ModelType.HAIKU: "claude-3-haiku-20240307",
    ModelType.SONNET: "claude-sonnet-4-20250514",
    ModelType.OPUS: "claude-opus-4-20250514"
}


class AgentLoader:
    """Loads and manages agent templates with schema validation."""
    
    def __init__(self):
        """Initialize the agent loader."""
        self.validator = AgentValidator()
        self.cache = SharedPromptCache.get_instance()
        self._agent_registry: Dict[str, Dict[str, Any]] = {}
        self._load_agents()
    
    def _load_agents(self) -> None:
        """Load all valid agents from the templates directory."""
        logger.info(f"Loading agents from {AGENT_TEMPLATES_DIR}")
        
        for json_file in AGENT_TEMPLATES_DIR.glob("*.json"):
            if json_file.name == "agent_schema.json":
                continue
            
            try:
                with open(json_file, 'r') as f:
                    agent_data = json.load(f)
                
                # Validate against schema
                validation_result = self.validator.validate_agent(agent_data)
                
                if validation_result.is_valid:
                    agent_id = agent_data.get("id")
                    if agent_id:
                        self._agent_registry[agent_id] = agent_data
                        logger.debug(f"Loaded agent: {agent_id}")
                else:
                    logger.warning(f"Invalid agent in {json_file.name}: {validation_result.errors}")
                    
            except Exception as e:
                logger.error(f"Failed to load {json_file.name}: {e}")
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent data by ID."""
        return self._agent_registry.get(agent_id)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all available agents."""
        agents = []
        for agent_id, agent_data in self._agent_registry.items():
            agents.append({
                "id": agent_id,
                "name": agent_data.get("metadata", {}).get("name", agent_id),
                "description": agent_data.get("metadata", {}).get("description", ""),
                "category": agent_data.get("metadata", {}).get("category", ""),
                "model": agent_data.get("capabilities", {}).get("model", ""),
                "resource_tier": agent_data.get("capabilities", {}).get("resource_tier", "")
            })
        return sorted(agents, key=lambda x: x["id"])
    
    def get_agent_prompt(self, agent_id: str, force_reload: bool = False) -> Optional[str]:
        """Get agent instructions by ID."""
        cache_key = f"{AGENT_CACHE_PREFIX}{agent_id}"
        
        # Check cache first
        if not force_reload:
            cached_content = self.cache.get(cache_key)
            if cached_content is not None:
                logger.debug(f"Agent prompt for '{agent_id}' loaded from cache")
                return str(cached_content)
        
        # Get agent data
        agent_data = self.get_agent(agent_id)
        if not agent_data:
            logger.warning(f"Agent not found: {agent_id}")
            return None
        
        # Extract instructions
        instructions = agent_data.get("instructions", "")
        if not instructions:
            logger.warning(f"No instructions found for agent: {agent_id}")
            return None
        
        # Cache the content with 1 hour TTL
        self.cache.set(cache_key, instructions, ttl=3600)
        logger.debug(f"Agent prompt for '{agent_id}' cached successfully")
        
        return instructions
    
    def get_agent_metadata(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent metadata including capabilities and configuration."""
        agent_data = self.get_agent(agent_id)
        if not agent_data:
            return None
        
        return {
            "id": agent_id,
            "version": agent_data.get("version", "1.0.0"),
            "metadata": agent_data.get("metadata", {}),
            "capabilities": agent_data.get("capabilities", {}),
            "knowledge": agent_data.get("knowledge", {}),
            "interactions": agent_data.get("interactions", {})
        }


# Global loader instance
_loader: Optional[AgentLoader] = None


def _get_loader() -> AgentLoader:
    """Get or create the global agent loader instance."""
    global _loader
    if _loader is None:
        _loader = AgentLoader()
    return _loader


def load_agent_prompt_from_md(agent_name: str, force_reload: bool = False) -> Optional[str]:
    """
    Load agent prompt from new schema JSON template.
    
    Args:
        agent_name: Agent name (matches agent ID in new schema)
        force_reload: Force reload from file, bypassing cache
        
    Returns:
        str: Agent instructions from JSON template, or None if not found
    """
    loader = _get_loader()
    return loader.get_agent_prompt(agent_name, force_reload)


def _analyze_task_complexity(task_description: str, context_size: int = 0, **kwargs: Any) -> Dict[str, Any]:
    """
    Analyze task complexity using TaskComplexityAnalyzer.
    
    Args:
        task_description: Description of the task
        context_size: Size of context in characters
        **kwargs: Additional parameters for complexity analysis
        
    Returns:
        Dictionary containing complexity analysis results
    """
    # Temporary implementation until TaskComplexityAnalyzer is available
    logger.warning("TaskComplexityAnalyzer not available, using default values")
    return {
        "complexity_score": 50,
        "complexity_level": ComplexityLevel.MEDIUM,
        "recommended_model": ModelType.SONNET,
        "optimal_prompt_size": (700, 1000),
        "error": "TaskComplexityAnalyzer module not available"
    }


def _get_model_config(agent_name: str, complexity_analysis: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Get model configuration based on agent type and task complexity.
    
    Args:
        agent_name: Name of the agent
        complexity_analysis: Results from task complexity analysis
        
    Returns:
        Tuple of (selected_model, model_config)
    """
    loader = _get_loader()
    agent_data = loader.get_agent(agent_name)
    
    if not agent_data:
        # Fallback for unknown agents
        return "claude-sonnet-4-20250514", {"selection_method": "default"}
    
    # Get model from agent capabilities
    default_model = agent_data.get("capabilities", {}).get("model", "claude-sonnet-4-20250514")
    
    # Check if dynamic model selection is enabled
    enable_dynamic_selection = os.getenv('ENABLE_DYNAMIC_MODEL_SELECTION', 'true').lower() == 'true'
    
    # Check for per-agent override in environment
    agent_override_key = f"CLAUDE_PM_{agent_name.upper()}_MODEL_SELECTION"
    agent_override = os.getenv(agent_override_key, '').lower()
    
    if agent_override == 'true':
        enable_dynamic_selection = True
    elif agent_override == 'false':
        enable_dynamic_selection = False
    
    # Dynamic model selection based on complexity
    if enable_dynamic_selection and complexity_analysis:
        recommended_model = complexity_analysis.get('recommended_model', ModelType.SONNET)
        selected_model = MODEL_NAME_MAPPINGS.get(recommended_model, default_model)
        
        model_config = {
            "selection_method": "dynamic_complexity_based",
            "complexity_score": complexity_analysis.get('complexity_score', 50),
            "complexity_level": complexity_analysis.get('complexity_level', ComplexityLevel.MEDIUM).value,
            "optimal_prompt_size": complexity_analysis.get('optimal_prompt_size', (700, 1000)),
            "default_model": default_model
        }
    else:
        selected_model = default_model
        model_config = {
            "selection_method": "agent_default",
            "reason": "dynamic_selection_disabled" if not enable_dynamic_selection else "no_complexity_analysis",
            "default_model": default_model
        }
    
    return selected_model, model_config


def get_agent_prompt(agent_name: str, force_reload: bool = False, return_model_info: bool = False, **kwargs: Any) -> Union[str, Tuple[str, str, Dict[str, Any]]]:
    """
    Get agent prompt from JSON template with optional dynamic model selection.
    
    Args:
        agent_name: Agent name (agent ID in new schema)
        force_reload: Force reload from source, bypassing cache
        return_model_info: If True, returns tuple (prompt, model, config)
        **kwargs: Additional arguments including:
            - task_description: Description of the task for complexity analysis
            - context_size: Size of context for complexity analysis
            - enable_complexity_analysis: Override for complexity analysis
        
    Returns:
        str or tuple: Complete agent prompt with base instructions prepended,
                      or tuple of (prompt, selected_model, model_config) if return_model_info=True
    """
    # Load from new schema JSON template
    prompt = load_agent_prompt_from_md(agent_name, force_reload)
    
    if prompt is None:
        raise ValueError(f"No agent found with ID: {agent_name}")
    
    # Analyze task complexity if task description is provided
    complexity_analysis = None
    task_description = kwargs.get('task_description', '')
    enable_analysis = kwargs.get('enable_complexity_analysis', True)
    
    if task_description and enable_analysis:
        complexity_analysis = _analyze_task_complexity(
            task_description=task_description,
            context_size=kwargs.get('context_size', 0),
            **{k: v for k, v in kwargs.items() if k not in ['task_description', 'context_size']}
        )
    
    # Get model configuration
    selected_model, model_config = _get_model_config(agent_name, complexity_analysis)
    
    # Add model selection metadata to prompt if dynamic selection is enabled
    if selected_model and model_config.get('selection_method') == 'dynamic_complexity_based':
        model_metadata = f"\n<!-- Model Selection: {selected_model} (Complexity: {model_config.get('complexity_level', 'UNKNOWN')}) -->\n"
        prompt = model_metadata + prompt
    
    # Prepend base instructions with dynamic template based on complexity
    complexity_score = model_config.get('complexity_score', 50) if model_config else 50
    final_prompt = prepend_base_instructions(prompt, complexity_score=complexity_score)
    
    # Return model info if requested
    if return_model_info:
        return final_prompt, selected_model, model_config
    else:
        return final_prompt


# Backward-compatible functions
def get_documentation_agent_prompt() -> str:
    """Get the complete Documentation Agent prompt with base instructions."""
    prompt = get_agent_prompt("documentation", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_version_control_agent_prompt() -> str:
    """Get the complete Version Control Agent prompt with base instructions."""
    prompt = get_agent_prompt("version_control", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_qa_agent_prompt() -> str:
    """Get the complete QA Agent prompt with base instructions."""
    prompt = get_agent_prompt("qa", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_research_agent_prompt() -> str:
    """Get the complete Research Agent prompt with base instructions."""
    prompt = get_agent_prompt("research", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_ops_agent_prompt() -> str:
    """Get the complete Ops Agent prompt with base instructions."""
    prompt = get_agent_prompt("ops", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_security_agent_prompt() -> str:
    """Get the complete Security Agent prompt with base instructions."""
    prompt = get_agent_prompt("security", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_engineer_agent_prompt() -> str:
    """Get the complete Engineer Agent prompt with base instructions."""
    prompt = get_agent_prompt("engineer", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_data_engineer_agent_prompt() -> str:
    """Get the complete Data Engineer Agent prompt with base instructions."""
    prompt = get_agent_prompt("data_engineer", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_agent_prompt_with_model_info(agent_name: str, force_reload: bool = False, **kwargs: Any) -> Tuple[str, str, Dict[str, Any]]:
    """
    Get agent prompt with model selection information.
    
    Args:
        agent_name: Agent name (agent ID)
        force_reload: Force reload from source, bypassing cache
        **kwargs: Additional arguments for prompt generation and model selection
        
    Returns:
        Tuple of (prompt, selected_model, model_config)
    """
    result = get_agent_prompt(agent_name, force_reload, return_model_info=True, **kwargs)
    
    # Ensure we have a tuple
    if isinstance(result, tuple):
        return result
    
    # Fallback (shouldn't happen)
    loader = _get_loader()
    agent_data = loader.get_agent(agent_name)
    default_model = "claude-sonnet-4-20250514"
    if agent_data:
        default_model = agent_data.get("capabilities", {}).get("model", default_model)
    
    return result, default_model, {"selection_method": "default"}


# Utility functions
def list_available_agents() -> Dict[str, Dict[str, Any]]:
    """
    List all available agents with their metadata.
    
    Returns:
        dict: Agent information including capabilities and metadata
    """
    loader = _get_loader()
    agents = {}
    
    for agent_info in loader.list_agents():
        agent_id = agent_info["id"]
        metadata = loader.get_agent_metadata(agent_id)
        
        if metadata:
            agents[agent_id] = {
                "name": metadata["metadata"].get("name", agent_id),
                "description": metadata["metadata"].get("description", ""),
                "category": metadata["metadata"].get("category", ""),
                "version": metadata["version"],
                "model": metadata["capabilities"].get("model", ""),
                "resource_tier": metadata["capabilities"].get("resource_tier", ""),
                "tools": metadata["capabilities"].get("tools", [])
            }
    
    return agents


def clear_agent_cache(agent_name: Optional[str] = None) -> None:
    """
    Clear cached agent prompts.
    
    Args:
        agent_name: Specific agent to clear, or None to clear all
    """
    try:
        cache = SharedPromptCache.get_instance()
        
        if agent_name:
            cache_key = f"{AGENT_CACHE_PREFIX}{agent_name}"
            cache.invalidate(cache_key)
            logger.debug(f"Cache cleared for agent: {agent_name}")
        else:
            # Clear all agent caches
            loader = _get_loader()
            for agent_id in loader._agent_registry.keys():
                cache_key = f"{AGENT_CACHE_PREFIX}{agent_id}"
                cache.invalidate(cache_key)
            logger.debug("All agent caches cleared")
            
    except Exception as e:
        logger.error(f"Error clearing agent cache: {e}")


def validate_agent_files() -> Dict[str, Dict[str, Any]]:
    """
    Validate all agent files in the templates directory.
    
    Returns:
        dict: Validation results for each agent
    """
    validator = AgentValidator()
    results = {}
    
    for json_file in AGENT_TEMPLATES_DIR.glob("*.json"):
        if json_file.name == "agent_schema.json":
            continue
        
        validation_result = validator.validate_file(json_file)
        results[json_file.stem] = {
            "valid": validation_result.is_valid,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "file_path": str(json_file)
        }
    
    return results


def reload_agents() -> None:
    """Force reload all agents from disk."""
    global _loader
    _loader = None
    logger.info("Agent registry cleared, will reload on next access")