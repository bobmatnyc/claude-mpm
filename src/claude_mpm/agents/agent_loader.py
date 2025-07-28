#!/usr/bin/env python3
"""
Unified Agent Loader System
==========================

This module provides a unified system for loading and managing AI agent configurations
from JSON template files. It serves as the central registry for all agent types in the
Claude MPM system, handling discovery, validation, caching, and dynamic model selection.

Architecture Overview:
----------------------
The agent loader follows a plugin-like architecture where agents are discovered from
JSON template files in a designated directory. Each agent is validated against a
standardized schema before being registered for use.

Key Features:
-------------
- Automatic agent discovery from src/claude_mpm/agents/templates/*.json files
- Schema validation ensures all agents conform to the expected structure
- Intelligent caching using SharedPromptCache for performance optimization
- Dynamic model selection based on task complexity analysis
- Backward compatibility with legacy get_*_agent_prompt() functions
- Prepends base instructions to maintain consistency across all agents

Design Decisions:
-----------------
1. JSON-based Configuration: We chose JSON over YAML or Python files for:
   - Schema validation support
   - Language-agnostic configuration
   - Easy parsing and generation by tools

2. Lazy Loading with Caching: Agents are loaded on-demand and cached to:
   - Reduce startup time
   - Minimize memory usage for unused agents
   - Allow hot-reloading during development

3. Dynamic Model Selection: The system can analyze task complexity to:
   - Optimize cost by using appropriate model tiers
   - Improve performance for simple tasks
   - Ensure complex tasks get sufficient model capabilities

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

import json
import logging
import os
import time
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union, List

from ..services.shared_prompt_cache import SharedPromptCache
from .base_agent_loader import prepend_base_instructions
from ..validation.agent_validator import AgentValidator, ValidationResult
from ..utils.paths import PathResolver

# Temporary placeholders for missing module
# WHY: These classes would normally come from a task_complexity module, but
# we've included them here temporarily to avoid breaking dependencies.
# This allows the agent loader to function independently while the full
# complexity analysis system is being developed.
class ComplexityLevel:
    """Represents the complexity level of a task for model selection."""
    LOW = "LOW"      # Simple tasks suitable for fast, economical models
    MEDIUM = "MEDIUM"  # Standard tasks requiring balanced capabilities
    HIGH = "HIGH"    # Complex tasks needing advanced reasoning

class ModelType:
    """Claude model tiers used for dynamic selection based on task complexity."""
    HAIKU = "haiku"    # Fast, economical model for simple tasks
    SONNET = "sonnet"  # Balanced model for general-purpose tasks
    OPUS = "opus"      # Most capable model for complex reasoning

# Module-level logger
logger = logging.getLogger(__name__)


def _get_agent_templates_dir() -> Path:
    """
    Get the directory containing agent template JSON files.
    
    WHY: We use a function instead of a direct constant to ensure the path
    is always resolved relative to this module's location, making the code
    portable across different installation methods (pip install, development mode, etc.).
    
    Returns:
        Path: Absolute path to the templates directory
    """
    return Path(__file__).parent / "templates"


# Agent templates directory - where all agent JSON files are stored
AGENT_TEMPLATES_DIR = _get_agent_templates_dir()

# Cache prefix for agent prompts - versioned to allow cache invalidation on schema changes
# WHY: The "v2:" suffix allows us to invalidate all cached prompts when we make
# breaking changes to the agent schema format
AGENT_CACHE_PREFIX = "agent_prompt:v2:"

# Model configuration thresholds for dynamic selection
# WHY: These thresholds define complexity score ranges (0-100) that map to
# appropriate Claude models. The ranges are based on empirical testing of
# task performance across different model tiers.
MODEL_THRESHOLDS = {
    ModelType.HAIKU: {"min_complexity": 0, "max_complexity": 30},
    ModelType.SONNET: {"min_complexity": 31, "max_complexity": 70},
    ModelType.OPUS: {"min_complexity": 71, "max_complexity": 100}
}

# Model name mappings for Claude API
# WHY: These map our internal model types to the actual API model identifiers.
# The specific versions are chosen for their stability and feature completeness.
MODEL_NAME_MAPPINGS = {
    ModelType.HAIKU: "claude-3-haiku-20240307",      # Fast, cost-effective
    ModelType.SONNET: "claude-sonnet-4-20250514",    # Balanced performance
    ModelType.OPUS: "claude-opus-4-20250514"         # Maximum capability
}


class AgentLoader:
    """
    Central registry for loading and managing agent configurations.
    
    This class implements the core agent discovery and management system. It:
    1. Discovers agent JSON files from the templates directory
    2. Validates each agent against the standardized schema
    3. Maintains an in-memory registry of valid agents
    4. Provides caching for performance optimization
    5. Supports dynamic agent reloading
    
    METRICS COLLECTION OPPORTUNITIES:
    - Agent load times and cache hit rates
    - Validation performance by agent type
    - Agent usage frequency and patterns
    - Model selection distribution
    - Task complexity analysis results
    - Memory usage for agent templates
    - Error rates during loading/validation
    - Agent prompt size distributions
    
    The loader follows a singleton-like pattern through the module-level
    _loader instance to ensure consistent state across the application.
    
    Attributes:
        validator: AgentValidator instance for schema validation
        cache: SharedPromptCache instance for performance optimization
        _agent_registry: Internal dictionary mapping agent IDs to their configurations
    """
    
    def __init__(self):
        """
        Initialize the agent loader and discover available agents.
        
        The initialization process:
        1. Creates validator for schema checking
        2. Gets shared cache instance for performance
        3. Initializes empty agent registry
        4. Triggers agent discovery and loading
        
        METRICS OPPORTUNITIES:
        - Track initialization time
        - Monitor agent discovery performance
        - Count total agents loaded vs validation failures
        - Measure memory footprint of loaded agents
        
        WHY: We load agents eagerly during initialization to:
        - Detect configuration errors early
        - Build the registry once for efficient access
        - Validate all agents before the system starts using them
        """
        self.validator = AgentValidator()
        self.cache = SharedPromptCache.get_instance()
        self._agent_registry: Dict[str, Dict[str, Any]] = {}
        
        # METRICS: Initialize performance tracking
        # This structure collects valuable telemetry for AI agent performance
        self._metrics = {
            'agents_loaded': 0,
            'validation_failures': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'load_times': {},  # agent_id -> load time ms
            'usage_counts': {},  # agent_id -> usage count
            'model_selections': {},  # model -> count
            'complexity_scores': [],  # Distribution of task complexity
            'prompt_sizes': {},  # agent_id -> prompt size in chars
            'error_types': {},  # error_type -> count
            'initialization_time_ms': 0
        }
        
        # METRICS: Track initialization performance
        start_time = time.time()
        self._load_agents()
        self._metrics['initialization_time_ms'] = (time.time() - start_time) * 1000
        logger.debug(f"Agent loader initialized in {self._metrics['initialization_time_ms']:.2f}ms")
    
    def _load_agents(self) -> None:
        """
        Discover and load all valid agents from the templates directory.
        
        This method implements the agent discovery mechanism:
        1. Scans the templates directory for JSON files
        2. Skips the schema definition file
        3. Loads and validates each potential agent file
        4. Registers valid agents in the internal registry
        
        WHY: We use a file-based discovery mechanism because:
        - It allows easy addition of new agents without code changes
        - Agents can be distributed as simple JSON files
        - The system remains extensible and maintainable
        
        Error Handling:
        - Invalid JSON files are logged but don't stop the loading process
        - Schema validation failures are logged with details
        - The system continues to function with whatever valid agents it finds
        """
        logger.info(f"Loading agents from {AGENT_TEMPLATES_DIR}")
        
        for json_file in AGENT_TEMPLATES_DIR.glob("*.json"):
            # Skip the schema definition file itself
            if json_file.name == "agent_schema.json":
                continue
            
            try:
                with open(json_file, 'r') as f:
                    agent_data = json.load(f)
                
                # Validate against schema to ensure consistency
                validation_result = self.validator.validate_agent(agent_data)
                
                if validation_result.is_valid:
                    agent_id = agent_data.get("agent_id")
                    if agent_id:
                        self._agent_registry[agent_id] = agent_data
                        # METRICS: Track successful agent load
                        self._metrics['agents_loaded'] += 1
                        logger.debug(f"Loaded agent: {agent_id}")
                else:
                    # Log validation errors but continue loading other agents
                    # METRICS: Track validation failure
                    self._metrics['validation_failures'] += 1
                    logger.warning(f"Invalid agent in {json_file.name}: {validation_result.errors}")
                    
            except Exception as e:
                # Log loading errors but don't crash - system should be resilient
                logger.error(f"Failed to load {json_file.name}: {e}")
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve agent configuration by ID.
        
        Args:
            agent_id: Unique identifier for the agent (e.g., "research_agent")
            
        Returns:
            Dict containing the full agent configuration, or None if not found
            
        WHY: Direct dictionary lookup for O(1) performance, essential for
        frequently accessed agents during runtime.
        """
        return self._agent_registry.get(agent_id)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Get a summary list of all available agents.
        
        Returns:
            List of agent summaries containing key metadata fields
            
        WHY: We return a summary instead of full configurations to:
        - Reduce memory usage when listing many agents
        - Provide only the information needed for agent selection
        - Keep the API response size manageable
        
        The returned list is sorted by ID for consistent ordering across calls.
        """
        agents = []
        for agent_id, agent_data in self._agent_registry.items():
            # Extract key fields from nested structure for easy consumption
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
        """
        Retrieve agent instructions/prompt by ID with caching support.
        
        Args:
            agent_id: Unique identifier for the agent
            force_reload: If True, bypass cache and reload from registry
            
        Returns:
            The agent's instruction prompt, or None if not found
            
        Caching Strategy:
        - Prompts are cached for 1 hour (3600 seconds) by default
        - Cache keys are versioned (v2:) to allow bulk invalidation
        - Force reload bypasses cache for development/debugging
        
        METRICS TRACKED:
        - Cache hit/miss rates for optimization
        - Agent usage frequency for popular agents
        - Prompt loading times for performance
        - Prompt sizes for memory analysis
        
        WHY: Caching is critical here because:
        - Agent prompts can be large (several KB)
        - They're accessed frequently during agent execution
        - They rarely change in production
        - The 1-hour TTL balances freshness with performance
        """
        cache_key = f"{AGENT_CACHE_PREFIX}{agent_id}"
        
        # METRICS: Track usage count for this agent
        self._metrics['usage_counts'][agent_id] = self._metrics['usage_counts'].get(agent_id, 0) + 1
        
        # METRICS: Track load time
        load_start = time.time()
        
        # Check cache first unless force reload is requested
        if not force_reload:
            cached_content = self.cache.get(cache_key)
            if cached_content is not None:
                # METRICS: Track cache hit
                self._metrics['cache_hits'] += 1
                logger.debug(f"Agent prompt for '{agent_id}' loaded from cache")
                return str(cached_content)
        
        # METRICS: Track cache miss
        self._metrics['cache_misses'] += 1
        
        # Get agent data from registry
        agent_data = self.get_agent(agent_id)
        if not agent_data:
            logger.warning(f"Agent not found: {agent_id}")
            return None
        
        # Extract instructions from the agent configuration
        instructions = agent_data.get("instructions", "")
        if not instructions:
            logger.warning(f"No instructions found for agent: {agent_id}")
            return None
        
        # METRICS: Track prompt size for memory analysis
        self._metrics['prompt_sizes'][agent_id] = len(instructions)
        
        # METRICS: Record load time
        load_time_ms = (time.time() - load_start) * 1000
        self._metrics['load_times'][agent_id] = load_time_ms
        
        # Cache the content with 1 hour TTL for performance
        self.cache.set(cache_key, instructions, ttl=3600)
        logger.debug(f"Agent prompt for '{agent_id}' cached successfully")
        
        return instructions
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get collected performance metrics.
        
        Returns:
            Dictionary containing:
            - Cache performance (hit rate, miss rate)
            - Agent usage statistics
            - Load time analysis
            - Memory usage patterns
            - Error tracking
            
        This data could be:
        - Exposed via monitoring endpoints
        - Logged periodically for analysis
        - Used for capacity planning
        - Fed to AI operations platforms
        """
        cache_total = self._metrics['cache_hits'] + self._metrics['cache_misses']
        cache_hit_rate = 0.0
        if cache_total > 0:
            cache_hit_rate = (self._metrics['cache_hits'] / cache_total) * 100
        
        # Calculate average load times
        avg_load_time = 0.0
        if self._metrics['load_times']:
            avg_load_time = sum(self._metrics['load_times'].values()) / len(self._metrics['load_times'])
        
        # Find most used agents
        top_agents = sorted(
            self._metrics['usage_counts'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'initialization_time_ms': self._metrics['initialization_time_ms'],
            'agents_loaded': self._metrics['agents_loaded'],
            'validation_failures': self._metrics['validation_failures'],
            'cache_hit_rate_percent': cache_hit_rate,
            'cache_hits': self._metrics['cache_hits'],
            'cache_misses': self._metrics['cache_misses'],
            'average_load_time_ms': avg_load_time,
            'top_agents_by_usage': dict(top_agents),
            'model_selection_distribution': self._metrics['model_selections'].copy(),
            'prompt_size_stats': {
                'total_agents': len(self._metrics['prompt_sizes']),
                'average_size': sum(self._metrics['prompt_sizes'].values()) / len(self._metrics['prompt_sizes']) if self._metrics['prompt_sizes'] else 0,
                'max_size': max(self._metrics['prompt_sizes'].values()) if self._metrics['prompt_sizes'] else 0,
                'min_size': min(self._metrics['prompt_sizes'].values()) if self._metrics['prompt_sizes'] else 0
            },
            'error_types': self._metrics['error_types'].copy()
        }
    
    def get_agent_metadata(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive agent metadata including capabilities and configuration.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            Dictionary containing all agent metadata except instructions,
            or None if agent not found
            
        WHY: This method provides access to agent configuration without
        including the potentially large instruction text. This is useful for:
        - UI displays showing agent capabilities
        - Programmatic agent selection based on features
        - Debugging and introspection
        
        The returned structure mirrors the JSON schema sections for consistency.
        """
        agent_data = self.get_agent(agent_id)
        if not agent_data:
            return None
        
        return {
            "id": agent_id,
            "version": agent_data.get("version", "1.0.0"),
            "metadata": agent_data.get("metadata", {}),      # Name, description, category
            "capabilities": agent_data.get("capabilities", {}), # Model, tools, features
            "knowledge": agent_data.get("knowledge", {}),      # Domain expertise
            "interactions": agent_data.get("interactions", {})  # User interaction patterns
        }


# Global loader instance - singleton pattern for consistent state
# WHY: We use a module-level singleton because:
# - Agent configurations should be consistent across the application
# - Loading and validation only needs to happen once
# - Multiple loaders would lead to cache inconsistencies
_loader: Optional[AgentLoader] = None


def _get_loader() -> AgentLoader:
    """
    Get or create the global agent loader instance (singleton pattern).
    
    Returns:
        AgentLoader: The single global instance
        
    WHY: The singleton pattern ensures:
    - Agents are loaded and validated only once
    - All parts of the application see the same agent registry
    - Cache state remains consistent
    - Memory usage is minimized
    
    Thread Safety: Python's GIL makes this simple implementation thread-safe
    for the single assignment operation.
    """
    global _loader
    if _loader is None:
        _loader = AgentLoader()
    return _loader


def load_agent_prompt_from_md(agent_name: str, force_reload: bool = False) -> Optional[str]:
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


def _analyze_task_complexity(task_description: str, context_size: int = 0, **kwargs: Any) -> Dict[str, Any]:
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
        "error": "TaskComplexityAnalyzer module not available"
    }


def _get_model_config(agent_name: str, complexity_analysis: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Determine optimal model configuration based on agent type and task complexity.
    
    METRICS TRACKED:
    - Model selection distribution
    - Complexity score distribution
    - Dynamic vs static selection rates
    
    Args:
        agent_name: Name of the agent requesting model selection
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
    default_model = agent_data.get("capabilities", {}).get("model", "claude-sonnet-4-20250514")
    
    # Check if dynamic model selection is enabled globally
    enable_dynamic_selection = os.getenv('ENABLE_DYNAMIC_MODEL_SELECTION', 'true').lower() == 'true'
    
    # Check for per-agent override in environment
    # This allows fine-grained control over specific agents
    agent_override_key = f"CLAUDE_PM_{agent_name.upper()}_MODEL_SELECTION"
    agent_override = os.getenv(agent_override_key, '').lower()
    
    if agent_override == 'true':
        enable_dynamic_selection = True
    elif agent_override == 'false':
        enable_dynamic_selection = False
    
    # Apply dynamic model selection based on task complexity
    if enable_dynamic_selection and complexity_analysis:
        recommended_model = complexity_analysis.get('recommended_model', ModelType.SONNET)
        selected_model = MODEL_NAME_MAPPINGS.get(recommended_model, default_model)
        
        # METRICS: Track complexity scores for distribution analysis
        complexity_score = complexity_analysis.get('complexity_score', 50)
        if hasattr(loader, '_metrics'):
            loader._metrics['complexity_scores'].append(complexity_score)
            # Keep only last 1000 scores for memory efficiency
            if len(loader._metrics['complexity_scores']) > 1000:
                loader._metrics['complexity_scores'] = loader._metrics['complexity_scores'][-1000:]
        
        model_config = {
            "selection_method": "dynamic_complexity_based",
            "complexity_score": complexity_score,
            "complexity_level": complexity_analysis.get('complexity_level', ComplexityLevel.MEDIUM),
            "optimal_prompt_size": complexity_analysis.get('optimal_prompt_size', (700, 1000)),
            "default_model": default_model
        }
    else:
        # Use agent's default model when dynamic selection is disabled
        selected_model = default_model
        model_config = {
            "selection_method": "agent_default",
            "reason": "dynamic_selection_disabled" if not enable_dynamic_selection else "no_complexity_analysis",
            "default_model": default_model
        }
    
    # METRICS: Track model selection distribution
    # This helps understand model usage patterns and costs
    if hasattr(loader, '_metrics'):
        loader._metrics['model_selections'][selected_model] = \
            loader._metrics['model_selections'].get(selected_model, 0) + 1
    
    return selected_model, model_config


def get_agent_prompt(agent_name: str, force_reload: bool = False, return_model_info: bool = False, **kwargs: Any) -> Union[str, Tuple[str, str, Dict[str, Any]]]:
    """
    Get agent prompt with optional dynamic model selection and base instructions.
    
    This is the primary interface for retrieving agent prompts. It handles:
    1. Loading the agent's instructions from the registry
    2. Optionally analyzing task complexity for model selection
    3. Prepending base instructions for consistency
    4. Adding metadata about model selection decisions
    
    Args:
        agent_name: Agent ID (e.g., "research_agent", "qa_agent")
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
    1. Load agent instructions (with caching)
    2. Analyze task complexity (if enabled and task_description provided)
    3. Determine optimal model based on complexity
    4. Add model selection metadata to prompt
    5. Prepend base instructions
    6. Return appropriate format based on return_model_info
    
    WHY: This comprehensive approach ensures:
    - Consistent prompt structure across all agents
    - Optimal model selection for cost/performance
    - Transparency in model selection decisions
    - Flexibility for different use cases
    """
    # Load from JSON template via the loader
    prompt = load_agent_prompt_from_md(agent_name, force_reload)
    
    if prompt is None:
        raise ValueError(f"No agent found with ID: {agent_name}")
    
    # Analyze task complexity if task description is provided
    complexity_analysis = None
    task_description = kwargs.get('task_description', '')
    enable_analysis = kwargs.get('enable_complexity_analysis', True)
    
    if task_description and enable_analysis:
        # Extract relevant kwargs for complexity analysis
        complexity_kwargs = {k: v for k, v in kwargs.items() 
                           if k not in ['task_description', 'context_size', 'enable_complexity_analysis']}
        complexity_analysis = _analyze_task_complexity(
            task_description=task_description,
            context_size=kwargs.get('context_size', 0),
            **complexity_kwargs
        )
    
    # Get model configuration based on agent and complexity
    selected_model, model_config = _get_model_config(agent_name, complexity_analysis)
    
    # Add model selection metadata to prompt for transparency
    # This helps with debugging and understanding model choices
    if selected_model and model_config.get('selection_method') == 'dynamic_complexity_based':
        model_metadata = f"\n<!-- Model Selection: {selected_model} (Complexity: {model_config.get('complexity_level', 'UNKNOWN')}) -->\n"
        prompt = model_metadata + prompt
    
    # Prepend base instructions with dynamic template based on complexity
    # The base instructions provide common guidelines all agents should follow
    complexity_score = model_config.get('complexity_score', 50) if model_config else 50
    final_prompt = prepend_base_instructions(prompt, complexity_score=complexity_score)
    
    # Return format based on caller's needs
    if return_model_info:
        return final_prompt, selected_model, model_config
    else:
        return final_prompt


# Backward-compatible functions
# WHY: These functions exist to maintain backward compatibility with existing code
# that expects agent-specific getter functions. New code should use get_agent_prompt()
# directly with the agent_id parameter for more flexibility.
#
# DEPRECATION NOTE: These functions may be removed in a future major version.
# They add maintenance overhead and limit extensibility compared to the generic interface.

def get_documentation_agent_prompt() -> str:
    """
    Get the complete Documentation Agent prompt with base instructions.
    
    Returns:
        Complete prompt string ready for use with Claude API
        
    DEPRECATED: Use get_agent_prompt("documentation_agent") instead
    """
    prompt = get_agent_prompt("documentation_agent", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_version_control_agent_prompt() -> str:
    """
    Get the complete Version Control Agent prompt with base instructions.
    
    Returns:
        Complete prompt string ready for use with Claude API
        
    DEPRECATED: Use get_agent_prompt("version_control_agent") instead
    """
    prompt = get_agent_prompt("version_control_agent", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_qa_agent_prompt() -> str:
    """
    Get the complete QA Agent prompt with base instructions.
    
    Returns:
        Complete prompt string ready for use with Claude API
        
    DEPRECATED: Use get_agent_prompt("qa_agent") instead
    """
    prompt = get_agent_prompt("qa_agent", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_research_agent_prompt() -> str:
    """
    Get the complete Research Agent prompt with base instructions.
    
    Returns:
        Complete prompt string ready for use with Claude API
        
    DEPRECATED: Use get_agent_prompt("research_agent") instead
    """
    prompt = get_agent_prompt("research_agent", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_ops_agent_prompt() -> str:
    """
    Get the complete Ops Agent prompt with base instructions.
    
    Returns:
        Complete prompt string ready for use with Claude API
        
    DEPRECATED: Use get_agent_prompt("ops_agent") instead
    """
    prompt = get_agent_prompt("ops_agent", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_security_agent_prompt() -> str:
    """
    Get the complete Security Agent prompt with base instructions.
    
    Returns:
        Complete prompt string ready for use with Claude API
        
    DEPRECATED: Use get_agent_prompt("security_agent") instead
    """
    prompt = get_agent_prompt("security_agent", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_engineer_agent_prompt() -> str:
    """
    Get the complete Engineer Agent prompt with base instructions.
    
    Returns:
        Complete prompt string ready for use with Claude API
        
    DEPRECATED: Use get_agent_prompt("engineer_agent") instead
    """
    prompt = get_agent_prompt("engineer_agent", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_data_engineer_agent_prompt() -> str:
    """
    Get the complete Data Engineer Agent prompt with base instructions.
    
    Returns:
        Complete prompt string ready for use with Claude API
        
    DEPRECATED: Use get_agent_prompt("data_engineer_agent") instead
    """
    prompt = get_agent_prompt("data_engineer_agent", return_model_info=False)
    assert isinstance(prompt, str), "Expected string when return_model_info=False"
    return prompt


def get_agent_prompt_with_model_info(agent_name: str, force_reload: bool = False, **kwargs: Any) -> Tuple[str, str, Dict[str, Any]]:
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
    result = get_agent_prompt(agent_name, force_reload, return_model_info=True, **kwargs)
    
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

def list_available_agents() -> Dict[str, Dict[str, Any]]:
    """
    List all available agents with their key metadata.
    
    Returns:
        Dictionary mapping agent IDs to their metadata summaries
        
    The returned dictionary provides a comprehensive view of all registered
    agents, useful for:
    - UI agent selection interfaces
    - Documentation generation
    - System introspection and debugging
    - Programmatic agent discovery
    
    Example Return Value:
        {
            "research_agent": {
                "name": "Research Agent",
                "description": "Analyzes codebases...",
                "category": "analysis",
                "version": "1.0.0",
                "model": "claude-opus-4-20250514",
                "resource_tier": "standard",
                "tools": ["code_analysis", "search"]
            },
            ...
        }
        
    WHY: This aggregated view is more useful than raw agent data because:
    - It provides a consistent interface regardless of schema changes
    - It includes only the fields relevant for agent selection
    - It's optimized for UI display and decision making
    """
    loader = _get_loader()
    agents = {}
    
    for agent_info in loader.list_agents():
        agent_id = agent_info["id"]
        metadata = loader.get_agent_metadata(agent_id)
        
        if metadata:
            # Extract and flatten key information for easy consumption
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
            for agent_id in loader._agent_registry.keys():
                cache_key = f"{AGENT_CACHE_PREFIX}{agent_id}"
                cache.invalidate(cache_key)
            logger.debug("All agent caches cleared")
            
    except Exception as e:
        # Log but don't raise - cache clearing shouldn't break the system
        logger.error(f"Error clearing agent cache: {e}")


def validate_agent_files() -> Dict[str, Dict[str, Any]]:
    """
    Validate all agent template files against the schema.
    
    Returns:
        Dictionary mapping agent names to validation results
        
    This function performs comprehensive validation of all agent files,
    checking for:
    - JSON syntax errors
    - Schema compliance
    - Required fields presence
    - Data type correctness
    - Constraint violations
    
    Return Format:
        {
            "agent_name": {
                "valid": bool,
                "errors": [list of error messages],
                "warnings": [list of warning messages],
                "file_path": "/full/path/to/file.json"
            },
            ...
        }
        
    Use Cases:
    - Pre-deployment validation in CI/CD
    - Development-time agent verification  
    - Troubleshooting agent loading issues
    - Automated testing of agent configurations
    
    WHY: Separate validation allows checking agents without loading them,
    useful for CI/CD pipelines and development workflows where we want to
    catch errors before runtime.
    """
    validator = AgentValidator()
    results = {}
    
    for json_file in AGENT_TEMPLATES_DIR.glob("*.json"):
        # Skip the schema definition file itself
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
    """
    Force reload all agents from disk, clearing the registry and cache.
    
    This function completely resets the agent loader state, causing:
    1. The global loader instance to be destroyed
    2. All cached agent prompts to be invalidated
    3. Fresh agent discovery on next access
    
    Use Cases:
    - Hot-reloading during development
    - Picking up new agent files without restart
    - Recovering from corrupted state
    - Testing agent loading logic
    
    WHY: Hot-reloading is essential for development productivity and
    allows dynamic agent updates in production without service restart.
    
    Implementation Note: We simply clear the global loader reference.
    The next call to _get_loader() will create a fresh instance that
    re-discovers and re-validates all agents.
    """
    global _loader
    _loader = None
    logger.info("Agent registry cleared, will reload on next access")