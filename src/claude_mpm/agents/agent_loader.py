#!/usr/bin/env python3
"""
Unified Agent Loader System - Main Entry Point
==============================================

This module provides the main entry point for the unified agent loading system.
The system has been refactored into smaller, focused modules for better maintainability:

- agent_registry.py: Core agent discovery and registry management
- agent_cache.py: Caching mechanisms for performance optimization
- agent_validator.py: Schema validation and error handling
- model_selector.py: Dynamic model selection based on task complexity
- legacy_support.py: Backward compatibility functions
- async_loader.py: High-performance async loading operations
- metrics_collector.py: Performance monitoring and telemetry

This main module provides the unified interface while delegating to specialized modules.

Usage Examples:
--------------
    from claude_mpm.agents.agent_loader import get_documentation_agent_prompt

    # Get agent prompt using backward-compatible function
    prompt = get_documentation_agent_prompt()

    # Get agent with model selection info
    prompt, model, config = get_agent_prompt("research_agent",
                                            return_model_info=True,
                                            task_description="Analyze codebase")

    # List all available agents
    agents = list_available_agents()
"""

import logging
import os
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Import modular components
from claude_mpm.core.unified_agent_registry import (
    AgentTier,
    get_agent_registry,
)
from claude_mpm.core.unified_paths import get_path_manager
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache

from ..core.agent_name_normalizer import AgentNameNormalizer
from .base_agent_loader import prepend_base_instructions

# Module-level logger
logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Claude model types for agent configuration."""

    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


class ComplexityLevel(str, Enum):
    """Task complexity levels for model selection."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Re-export key classes and functions
__all__ = [
    "AgentLoader",
    "AgentTier",
    "get_agent_prompt",
    "get_agent_tier",
    "list_agents_by_tier",
    "list_available_agents",
    "reload_agents",
    "validate_agent_files",
]


def _get_agent_templates_dirs() -> Dict[AgentTier, Optional[Path]]:
    """
    Get directories containing agent JSON files across all tiers.

    Returns a dictionary mapping tiers to their agent directories:
    - PROJECT: .claude-mpm/agents in the current working directory
    - USER: ~/.claude-mpm/agents
    - SYSTEM: Built-in agents relative to this module

    WHY: We support multiple tiers to allow project-specific customization
    while maintaining backward compatibility with system agents.

    Returns:
        Dict mapping AgentTier to Path (or None if not available)
    """
    dirs = {}

    # PROJECT tier - ALWAYS check current working directory dynamically
    # This ensures we pick up project agents even if CWD changes
    project_dir = Path.cwd() / get_path_manager().CONFIG_DIR / "agents"
    if project_dir.exists():
        dirs[AgentTier.PROJECT] = project_dir
        logger.debug(f"Found PROJECT agents at: {project_dir}")

    # USER tier - check user home directory
    user_config_dir = get_path_manager().get_user_config_dir()
    if user_config_dir:
        user_agents_dir = user_config_dir / "agents"
        if user_agents_dir.exists():
            dirs[AgentTier.USER] = user_agents_dir
            logger.debug(f"Found USER agents at: {user_agents_dir}")

    # SYSTEM tier - built-in agents
    system_dir = Path(__file__).parent / "templates"
    if system_dir.exists():
        dirs[AgentTier.SYSTEM] = system_dir
        logger.debug(f"Found SYSTEM agents at: {system_dir}")

    return dirs


def _get_agent_templates_dir() -> Path:
    """
    Get the primary directory containing agent JSON files.

    DEPRECATED: Use _get_agent_templates_dirs() for tier-aware loading.
    This function is kept for backward compatibility.

    Returns:
        Path: Absolute path to the system agents directory
    """
    return Path(__file__).parent / "templates"


# Agent directory - where all agent JSON files are stored
AGENT_TEMPLATES_DIR = _get_agent_templates_dir()

AGENT_CACHE_PREFIX = "agent_prompt:v2:"

# Model configuration thresholds for dynamic selection
# WHY: These thresholds define complexity score ranges (0-100) that map to
# appropriate Claude models. The ranges are based on empirical testing of
# task performance across different model tiers.
MODEL_THRESHOLDS = {
    ModelType.HAIKU: {"min_complexity": 0, "max_complexity": 30},
    ModelType.SONNET: {"min_complexity": 31, "max_complexity": 70},
    ModelType.OPUS: {"min_complexity": 71, "max_complexity": 100},
}

MODEL_NAME_MAPPINGS = {
    ModelType.HAIKU: "claude-3-haiku-20240307",  # Fast, cost-effective
    ModelType.SONNET: "claude-sonnet-4-20250514",  # Balanced performance
    ModelType.OPUS: "claude-opus-4-20250514",  # Maximum capability
}


class AgentLoader:
    """
    Simplified Agent Loader - Clean interface to agent registry.

    This class provides a simple, focused interface for agent loading:
    - AgentRegistry: Core agent discovery and registry management
    - Direct file access (no caching complexity)
    - Simple, testable design

    The simplified design provides:
    - Clean separation of concerns
    - Easy testability
    - Minimal complexity
    - Fast, direct file access
    """

    def __init__(self):
        """
        Initialize the agent loader with the registry.

        The initialization process:
        1. Creates the agent registry
        2. Loads agents from all tiers
        """
        start_time = time.time()

        # Initialize the agent registry
        self.registry = get_agent_registry()

        # Load agents through registry
        self.registry.load_agents()

        init_time = (time.time() - start_time) * 1000
        logger.info(
            f"AgentLoader initialized in {init_time:.2f}ms with {len(self.registry._agent_registry)} agents"
        )

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve agent configuration by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent configuration or None if not found
        """
        return self.registry.get_agent(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Get a summary list of all available agents.

        Returns:
            List of agent summaries with key metadata
        """
        return self.registry.list_agents()

    def get_agent_prompt(
        self, agent_id: str, force_reload: bool = False
    ) -> Optional[str]:
        """
        Retrieve agent instructions/prompt by ID.

        Args:
            agent_id: Agent identifier
            force_reload: Ignored (kept for API compatibility)

        Returns:
            Agent prompt string or None if not found
        """
        agent_data = self.registry.get_agent(agent_id)
        if not agent_data:
            return None

        # Extract instructions
        instructions = agent_data.get("instructions", "")
        if not instructions:
            logger.warning(f"Agent '{agent_id}' has no instructions")
            return None

        # Prepend base instructions
        return prepend_base_instructions(instructions)

    def get_agent_metadata(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive agent metadata including capabilities and configuration.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent metadata dictionary or None if not found
        """
        agent_data = self.registry.get_agent(agent_id)
        if not agent_data:
            return None

        metadata = agent_data.get("metadata", {})
        capabilities = agent_data.get("capabilities", {})
        tier = self.registry.get_agent_tier(agent_id)

        # Check for project memory
        has_memory = capabilities.get("has_project_memory", False)

        result = {
            "agent_id": agent_id,
            "name": metadata.get("name", agent_id),
            "description": metadata.get("description", ""),
            "category": metadata.get("category", "general"),
            "version": metadata.get("version", "1.0.0"),
            "model": agent_data.get("model", "claude-sonnet-4-20250514"),
            "resource_tier": agent_data.get("resource_tier", "standard"),
            "tier": tier.value if tier else "unknown",
            "tools": agent_data.get("tools", []),
            "capabilities": capabilities,
            "source_file": agent_data.get("_source_file", "unknown"),
            "has_project_memory": has_memory,
        }

        # Add memory-specific information if present
        if has_memory:
            result["memory_size_kb"] = capabilities.get("memory_size_kb", 0)
            result["memory_file"] = capabilities.get("memory_file", "")
            result["memory_lines"] = capabilities.get("memory_lines", 0)
            result["memory_enhanced"] = True

        return result

    def reload(self) -> None:
        """
        Reload all agents from disk, clearing the registry.
        """
        logger.info("Reloading agent system...")

        # Reload registry
        self.registry.reload()

        logger.info(
            f"Agent system reloaded with {len(self.registry._agent_registry)} agents"
        )


# Global loader instance (singleton pattern)
_loader: Optional[AgentLoader] = None


def _get_loader() -> AgentLoader:
    """
    Get or create the global agent loader instance (singleton pattern).

    Returns:
        AgentLoader: The global agent loader instance
    """
    global _loader
    if _loader is None:
        logger.debug("Initializing global agent loader")
        _loader = AgentLoader()
    return _loader


# Removed duplicate get_agent_prompt function - using the comprehensive version below


def list_available_agents() -> Dict[str, Dict[str, Any]]:
    """
    List all available agents with their key metadata including memory information.

    Returns:
        Dictionary mapping agent IDs to their metadata
    """
    loader = _get_loader()
    agents_list = loader.list_agents()

    # Convert list to dictionary for easier access
    agents_dict = {}
    for agent in agents_list:
        agent_id = agent["id"]
        agent_info = {
            "name": agent["name"],
            "description": agent["description"],
            "category": agent["category"],
            "version": agent.get("version", "1.0.0"),
            "model": agent.get("model", "claude-sonnet-4-20250514"),
            "resource_tier": agent.get("resource_tier", "standard"),
            "tier": agent.get("tier", "system"),
            "has_project_memory": agent.get("has_project_memory", False),
        }

        # Add memory details if present
        if agent.get("has_project_memory", False):
            agent_info["memory_size_kb"] = agent.get("memory_size_kb", 0)
            agent_info["memory_file"] = agent.get("memory_file", "")
            agent_info["memory_lines"] = agent.get("memory_lines", 0)

        agents_dict[agent_id] = agent_info

    return agents_dict


def validate_agent_files() -> Dict[str, Dict[str, Any]]:
    """
    Validate all agent template files against the schema.

    Returns:
        Dictionary mapping agent names to validation results
    """
    loader = _get_loader()
    agents = loader.list_agents()
    results = {}

    for agent in agents:
        agent_id = agent["id"]
        agent_data = loader.get_agent(agent_id)
        if agent_data:
            results[agent_id] = {"valid": True, "errors": [], "warnings": []}
        else:
            results[agent_id] = {
                "valid": False,
                "errors": ["Agent not found"],
                "warnings": [],
            }

    return results


def reload_agents() -> None:
    """
    Force reload all agents from disk, clearing the registry.
    """
    global _loader
    if _loader:
        _loader.reload()
    else:
        # Clear the global instance to force reinitialization
        _loader = None

    logger.info("Agent registry cleared, will reload on next access")


def get_agent_tier(agent_name: str) -> Optional[str]:
    """
    Get the tier from which an agent was loaded.

    Args:
        agent_name: Agent identifier

    Returns:
        Tier name or None if agent not found
    """
    loader = _get_loader()
    tier = loader.registry.get_agent_tier(agent_name)
    return tier.value if tier else None


def list_agents_by_tier() -> Dict[str, List[str]]:
    """
    List available agents organized by their tier.

    Returns:
        Dictionary mapping tier names to lists of agent IDs
    """
    loader = _get_loader()
    agents = loader.list_agents()

    result = {tier.value: [] for tier in AgentTier}

    for agent in agents:
        tier = agent.get("tier", "system")
        if tier in result:
            result[tier].append(agent["id"])

    return result


# Duplicate functions removed - using the ones defined earlier


def get_agent_metadata(agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Get agent metadata without instruction content.

    WHY: This method provides access to agent configuration without
    including the potentially large instruction text. This is useful for:
    - UI displays showing agent capabilities
    - Programmatic agent selection based on features
    - Debugging and introspection

    The returned structure mirrors the JSON schema sections for consistency.
    """
    loader = AgentLoader()
    agent_data = loader.get_agent(agent_id)
    if not agent_data:
        return None

    return {
        "id": agent_id,
        "version": agent_data.get("version", "1.0.0"),
        "metadata": agent_data.get("metadata", {}),  # Name, description, category
        "capabilities": agent_data.get("capabilities", {}),  # Model, tools, features
        "knowledge": agent_data.get("knowledge", {}),  # Domain expertise
        "interactions": agent_data.get("interactions", {}),  # User interaction patterns
    }


# Duplicate _get_loader function removed - using the one defined earlier


def load_agent_prompt_from_md(
    agent_name: str, force_reload: bool = False
) -> Optional[str]:
    """
    Load agent prompt from JSON template (legacy function name).

    Args:
        agent_name: Agent name (matches agent ID in new schema)
        force_reload: Force reload from file, bypassing cache

    Returns:
        str: Agent instructions from JSON template, or None if not found

    NOTE: Despite the "md" in the function name, this loads from JSON files.
    The name is kept for backward compatibility with existing code that
    expects this interface. New code should use get_agent_prompt() directly.

    WHY: This wrapper exists to maintain backward compatibility during the
    migration from markdown-based agents to JSON-based agents.
    """
    loader = _get_loader()
    return loader.get_agent_prompt(agent_name, force_reload)


def _analyze_task_complexity(
    task_description: str, context_size: int = 0, **kwargs: Any
) -> Dict[str, Any]:
    """
    Analyze task complexity to determine optimal model selection.

    Args:
        task_description: Description of the task to analyze
        context_size: Size of context in characters (affects complexity)
        **kwargs: Additional parameters for complexity analysis such as:
            - code_analysis: Whether code analysis is required
            - multi_step: Whether the task involves multiple steps
            - domain_expertise: Required domain knowledge level

    Returns:
        Dictionary containing:
            - complexity_score: Numeric score 0-100
            - complexity_level: LOW, MEDIUM, or HIGH
            - recommended_model: Suggested Claude model tier
            - optimal_prompt_size: Recommended prompt size range
            - error: Error message if analysis fails

    WHY: This is a placeholder implementation that returns sensible defaults.
    The actual TaskComplexityAnalyzer module would use NLP techniques to:
    - Analyze task description for complexity indicators
    - Consider context size and memory requirements
    - Factor in domain-specific requirements
    - Optimize for cost vs capability trade-offs

    Current Implementation: Returns medium complexity as a safe default that
    works well for most tasks while the full analyzer is being developed.
    """
    # Temporary implementation until TaskComplexityAnalyzer is available
    logger.warning("TaskComplexityAnalyzer not available, using default values")
    return {
        "complexity_score": 50,
        "complexity_level": ComplexityLevel.MEDIUM,
        "recommended_model": ModelType.SONNET,
        "optimal_prompt_size": (700, 1000),
        "error": "TaskComplexityAnalyzer module not available",
    }


def _get_model_config(
    agent_name: str, complexity_analysis: Optional[Dict[str, Any]] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Determine optimal model configuration based on agent type and task complexity.

    METRICS TRACKED:
    - Model selection distribution
    - Complexity score distribution
    - Dynamic vs static selection rates

    Args:
        agent_name: Name of the agent requesting model selection (already normalized to agent_id format)
        complexity_analysis: Results from task complexity analysis (if available)

    Returns:
        Tuple of (selected_model, model_config) where:
            - selected_model: Claude API model identifier
            - model_config: Dictionary with selection metadata

    Model Selection Strategy:
    1. Each agent has a default model defined in its capabilities
    2. Dynamic selection can override based on task complexity
    3. Environment variables can control selection behavior

    Environment Variables:
    - ENABLE_DYNAMIC_MODEL_SELECTION: Global toggle (default: true)
    - CLAUDE_PM_{AGENT}_MODEL_SELECTION: Per-agent override

    WHY: This flexible approach allows:
    - Cost optimization by using cheaper models for simple tasks
    - Performance optimization by using powerful models only when needed
    - Easy override for testing or production constraints
    - Gradual rollout of dynamic selection features
    """
    loader = _get_loader()
    agent_data = loader.get_agent(agent_name)

    if not agent_data:
        # Fallback for unknown agents - use Sonnet as safe default
        return "claude-sonnet-4-20250514", {"selection_method": "default"}

    # Get model from agent capabilities (agent's preferred model)
    default_model = agent_data.get("capabilities", {}).get(
        "model", "claude-sonnet-4-20250514"
    )

    # Check if dynamic model selection is enabled globally
    enable_dynamic_selection = (
        os.getenv("ENABLE_DYNAMIC_MODEL_SELECTION", "true").lower() == "true"
    )

    # Check for per-agent override in environment
    # This allows fine-grained control over specific agents
    agent_override_key = f"CLAUDE_PM_{agent_name.upper()}_MODEL_SELECTION"
    agent_override = os.getenv(agent_override_key, "").lower()

    if agent_override == "true":
        enable_dynamic_selection = True
    elif agent_override == "false":
        enable_dynamic_selection = False

    # Apply dynamic model selection based on task complexity
    if enable_dynamic_selection and complexity_analysis:
        recommended_model = complexity_analysis.get(
            "recommended_model", ModelType.SONNET
        )
        selected_model = MODEL_NAME_MAPPINGS.get(recommended_model, default_model)

        # METRICS: Track complexity scores for distribution analysis
        complexity_score = complexity_analysis.get("complexity_score", 50)
        if hasattr(loader, "_metrics"):
            loader._metrics["complexity_scores"].append(complexity_score)
            # Keep only last 1000 scores for memory efficiency
            if len(loader._metrics["complexity_scores"]) > 1000:
                loader._metrics["complexity_scores"] = loader._metrics[
                    "complexity_scores"
                ][-1000:]

        model_config = {
            "selection_method": "dynamic_complexity_based",
            "complexity_score": complexity_score,
            "complexity_level": complexity_analysis.get(
                "complexity_level", ComplexityLevel.MEDIUM
            ),
            "optimal_prompt_size": complexity_analysis.get(
                "optimal_prompt_size", (700, 1000)
            ),
            "default_model": default_model,
        }
    else:
        # Use agent's default model when dynamic selection is disabled
        selected_model = default_model
        model_config = {
            "selection_method": "agent_default",
            "reason": (
                "dynamic_selection_disabled"
                if not enable_dynamic_selection
                else "no_complexity_analysis"
            ),
            "default_model": default_model,
        }

    # METRICS: Track model selection distribution
    # This helps understand model usage patterns and costs
    if hasattr(loader, "_metrics"):
        loader._metrics["model_selections"][selected_model] = (
            loader._metrics["model_selections"].get(selected_model, 0) + 1
        )

    return selected_model, model_config


def get_agent_prompt(
    agent_name: str,
    force_reload: bool = False,
    return_model_info: bool = False,
    **kwargs: Any,
) -> Union[str, Tuple[str, str, Dict[str, Any]]]:
    """
    Get agent prompt with optional dynamic model selection and base instructions.

    This is the primary interface for retrieving agent prompts. It handles:
    1. Loading the agent's instructions from the registry
    2. Optionally analyzing task complexity for model selection
    3. Prepending base instructions for consistency
    4. Adding metadata about model selection decisions

    Args:
        agent_name: Agent name in any format (e.g., "Engineer", "research_agent", "QA")
        force_reload: Force reload from source, bypassing cache
        return_model_info: If True, returns extended info tuple
        **kwargs: Additional arguments:
            - task_description: Description for complexity analysis
            - context_size: Size of context in characters
            - enable_complexity_analysis: Toggle complexity analysis (default: True)
            - Additional task-specific parameters

    Returns:
        If return_model_info=False: Complete agent prompt string
        If return_model_info=True: Tuple of (prompt, selected_model, model_config)

    Raises:
        ValueError: If the requested agent is not found

    Processing Flow:
    1. Normalize agent name to correct agent ID
    2. Load agent instructions (with caching)
    3. Analyze task complexity (if enabled and task_description provided)
    4. Determine optimal model based on complexity
    5. Add model selection metadata to prompt
    6. Prepend base instructions
    7. Return appropriate format based on return_model_info

    WHY: This comprehensive approach ensures:
    - Consistent prompt structure across all agents
    - Optimal model selection for cost/performance
    - Transparency in model selection decisions
    - Flexibility for different use cases
    """
    # Normalize the agent name to handle various formats
    # Convert names like "Engineer", "Research", "QA" to the correct agent IDs
    normalizer = AgentNameNormalizer()
    loader = _get_loader()

    # First check if agent exists with exact name
    if loader.get_agent(agent_name):
        actual_agent_id = agent_name
    # Then check with _agent suffix
    elif loader.get_agent(f"{agent_name}_agent"):
        actual_agent_id = f"{agent_name}_agent"
    # Check if this looks like it might already be an agent ID
    elif agent_name.endswith("_agent"):
        actual_agent_id = agent_name
    else:
        # Get the normalized key (e.g., "engineer", "research", "qa")
        # First check if the agent name is recognized by the normalizer
        cleaned = agent_name.strip().lower().replace("-", "_")

        # Check if this is a known alias or canonical name
        if cleaned in normalizer.ALIASES or cleaned in normalizer.CANONICAL_NAMES:
            agent_key = normalizer.to_key(agent_name)
            # Try both with and without _agent suffix
            if loader.get_agent(agent_key):
                actual_agent_id = agent_key
            elif loader.get_agent(f"{agent_key}_agent"):
                actual_agent_id = f"{agent_key}_agent"
            else:
                actual_agent_id = agent_key  # Use normalized key
        # Unknown agent name - check both variations
        elif loader.get_agent(cleaned):
            actual_agent_id = cleaned
        elif loader.get_agent(f"{cleaned}_agent"):
            actual_agent_id = f"{cleaned}_agent"
        else:
            actual_agent_id = cleaned  # Use cleaned name

    # Log the normalization for debugging
    if agent_name != actual_agent_id:
        logger.debug(f"Normalized agent name '{agent_name}' to '{actual_agent_id}'")

    # Load from JSON template via the loader
    prompt = load_agent_prompt_from_md(actual_agent_id, force_reload)

    if prompt is None:
        raise ValueError(
            f"No agent found with name: {agent_name} (normalized to: {actual_agent_id})"
        )

    # Analyze task complexity if task description is provided
    complexity_analysis = None
    task_description = kwargs.get("task_description", "")
    enable_analysis = kwargs.get("enable_complexity_analysis", True)

    if task_description and enable_analysis:
        # Extract relevant kwargs for complexity analysis
        complexity_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k
            not in ["task_description", "context_size", "enable_complexity_analysis"]
        }
        complexity_analysis = _analyze_task_complexity(
            task_description=task_description,
            context_size=kwargs.get("context_size", 0),
            **complexity_kwargs,
        )

    # Get model configuration based on agent and complexity
    # Pass the normalized agent ID to _get_model_config
    selected_model, model_config = _get_model_config(
        actual_agent_id, complexity_analysis
    )

    # Add model selection metadata to prompt for transparency
    # This helps with debugging and understanding model choices
    if (
        selected_model
        and model_config.get("selection_method") == "dynamic_complexity_based"
    ):
        model_metadata = f"\n<!-- Model Selection: {selected_model} (Complexity: {model_config.get('complexity_level', 'UNKNOWN')}) -->\n"
        prompt = model_metadata + prompt

    # Prepend base instructions with dynamic template based on complexity
    # The base instructions provide common guidelines all agents should follow
    complexity_score = model_config.get("complexity_score", 50) if model_config else 50
    final_prompt = prepend_base_instructions(prompt, complexity_score=complexity_score)

    # Return format based on caller's needs
    if return_model_info:
        return final_prompt, selected_model, model_config
    return final_prompt


# Legacy hardcoded agent functions removed - use get_agent_prompt(agent_id) instead


def get_agent_prompt_with_model_info(
    agent_name: str, force_reload: bool = False, **kwargs: Any
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Convenience wrapper to always get agent prompt with model selection information.

    Args:
        agent_name: Agent ID (e.g., "research_agent")
        force_reload: Force reload from source, bypassing cache
        **kwargs: Additional arguments for prompt generation and model selection
            - task_description: For complexity analysis
            - context_size: For complexity scoring
            - Other task-specific parameters

    Returns:
        Tuple of (prompt, selected_model, model_config) where:
            - prompt: Complete agent prompt with base instructions
            - selected_model: Claude API model identifier
            - model_config: Dictionary with selection metadata

    WHY: This dedicated function ensures type safety for callers that always
    need model information, avoiding the need to handle Union types.

    Example:
        prompt, model, config = get_agent_prompt_with_model_info(
            "research_agent",
            task_description="Analyze Python codebase architecture"
        )
        print(f"Using model: {model} (method: {config['selection_method']})")
    """
    result = get_agent_prompt(
        agent_name, force_reload, return_model_info=True, **kwargs
    )

    # Type narrowing - we know this returns a tuple when return_model_info=True
    if isinstance(result, tuple):
        return result

    # Fallback (shouldn't happen with current implementation)
    # This defensive code ensures we always return the expected tuple format
    loader = _get_loader()
    agent_data = loader.get_agent(agent_name)
    default_model = "claude-sonnet-4-20250514"
    if agent_data:
        default_model = agent_data.get("capabilities", {}).get("model", default_model)

    return result, default_model, {"selection_method": "default"}


# Utility functions for agent management

# Duplicate list_available_agents function removed


def clear_agent_cache(agent_name: Optional[str] = None) -> None:
    """
    Clear cached agent prompts for development or after updates.

    Args:
        agent_name: Specific agent ID to clear, or None to clear all agents

    This function is useful for:
    - Development when modifying agent prompts
    - Forcing reload after agent template updates
    - Troubleshooting caching issues
    - Memory management in long-running processes

    Examples:
        # Clear specific agent cache
        clear_agent_cache("research_agent")

        # Clear all agent caches
        clear_agent_cache()

    WHY: Manual cache management is important because:
    - Agent prompts have a 1-hour TTL but may need immediate refresh
    - Development requires seeing changes without waiting for TTL
    - System administrators need cache control for troubleshooting

    Error Handling: Failures are logged but don't raise exceptions to ensure
    the system remains operational even if cache clearing fails.
    """
    try:
        cache = SharedPromptCache.get_instance()

        if agent_name:
            # Clear specific agent's cache entry
            cache_key = f"{AGENT_CACHE_PREFIX}{agent_name}"
            cache.invalidate(cache_key)
            logger.debug(f"Cache cleared for agent: {agent_name}")
        else:
            # Clear all agent caches by iterating through registry
            loader = _get_loader()
            for agent_id in loader._agent_registry:
                cache_key = f"{AGENT_CACHE_PREFIX}{agent_id}"
                cache.invalidate(cache_key)
            logger.debug("All agent caches cleared")

    except Exception as e:
        # Log but don't raise - cache clearing shouldn't break the system
        logger.error(f"Error clearing agent cache: {e}")


# Duplicate list_agents_by_tier function removed

# Duplicate validate_agent_files function removed

# Duplicate reload_agents function removed

# Duplicate get_agent_tier function removed - using the one defined earlier
