#!/usr/bin/env python3
"""
Unified Agent Loader System
==========================

Provides unified loading of agent prompts from framework markdown files.
Integrates with SharedPromptCache for performance optimization.

Key Features:
- Loads agent prompts from framework/agent-roles/*.md files
- Handles base_agent.md prepending
- Provides backward-compatible get_*_agent_prompt() functions
- Uses SharedPromptCache for performance
- Special handling for ticketing agent's dynamic CLI help

For advanced agent management features (CRUD, versioning, section updates), use:
    from claude_pm.agents.agent_loader_integration import get_enhanced_loader
    from claude_pm.services.agent_management_service import AgentManager

Usage:
    from claude_pm.agents.agent_loader import get_documentation_agent_prompt
    
    # Get agent prompt from MD file
    prompt = get_documentation_agent_prompt()
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union

from ..services.shared_prompt_cache import SharedPromptCache
from .base_agent_loader import prepend_base_instructions
from ..services.task_complexity_analyzer import TaskComplexityAnalyzer, ComplexityLevel, ModelType
from ..utils.paths import PathResolver

# Module-level logger
logger = logging.getLogger(__name__)


def _get_framework_agent_roles_dir() -> Path:
    """Get the framework agent-roles directory dynamically."""
    # Use PathResolver for consistent path discovery
    try:
        framework_root = PathResolver.get_framework_root()
        
        # Check if we're running from a wheel installation
        try:
            import claude_pm
            package_path = Path(claude_pm.__file__).parent
            path_str = str(package_path.resolve())
            if 'site-packages' in path_str or 'dist-packages' in path_str:
                # For wheel installations, check data directory
                data_agent_roles = package_path / "data" / "framework" / "agent-roles"
                if data_agent_roles.exists():
                    logger.debug(f"Using wheel installation agent-roles: {data_agent_roles}")
                    return data_agent_roles
        except Exception:
            pass
        
        # Check framework structure
        agent_roles_dir = framework_root / "framework" / "agent-roles"
        if agent_roles_dir.exists():
            logger.debug(f"Using framework agent-roles: {agent_roles_dir}")
            return agent_roles_dir
        
        # Try agents directory as fallback
        agents_dir = PathResolver.get_agents_dir()
        logger.debug(f"Using agents directory: {agents_dir}")
        return agents_dir
        
    except FileNotFoundError as e:
        # Ultimate fallback
        logger.warning(f"PathResolver could not find framework root: {e}")
        fallback = Path(__file__).parent.parent.parent / "framework" / "agent-roles"
        logger.warning(f"Using fallback agent-roles path: {fallback}")
        return fallback


# Framework agent-roles directory (dynamically determined)
FRAMEWORK_AGENT_ROLES_DIR = _get_framework_agent_roles_dir()

# Cache prefix for agent prompts
AGENT_CACHE_PREFIX = "agent_prompt:"

# Agent name mappings (agent name -> MD file name)
AGENT_MAPPINGS = {
    "documentation": "documentation-agent.md",
    "version_control": "version-control-agent.md",
    "qa": "qa-agent.md",
    "research": "research-agent.md",
    "ops": "ops-agent.md",
    "security": "security-agent.md",
    "engineer": "engineer-agent.md",
    "data_engineer": "data-agent.md",  # Note: data-agent.md maps to data_engineer
    "pm": "pm-orchestrator-agent.md",
    "orchestrator": "pm-orchestrator-agent.md",
    "pm_orchestrator": "pm-orchestrator-agent.md"
}

# Model configuration thresholds
MODEL_THRESHOLDS = {
    ModelType.HAIKU: {"min_complexity": 0, "max_complexity": 30},
    ModelType.SONNET: {"min_complexity": 31, "max_complexity": 70},
    ModelType.OPUS: {"min_complexity": 71, "max_complexity": 100}
}

# Default model for each agent type (fallback when dynamic selection is disabled)
DEFAULT_AGENT_MODELS = {
    'orchestrator': 'claude-4-opus',
    'pm': 'claude-4-opus',
    'pm_orchestrator': 'claude-4-opus',
    'engineer': 'claude-4-opus',
    'architecture': 'claude-4-opus',
    'documentation': 'claude-sonnet-4-20250514',
    'version_control': 'claude-sonnet-4-20250514',
    'qa': 'claude-sonnet-4-20250514',
    'research': 'claude-sonnet-4-20250514',
    'ops': 'claude-sonnet-4-20250514',
    'security': 'claude-sonnet-4-20250514',
    'data_engineer': 'claude-sonnet-4-20250514'
}

# Model name mappings for Claude API
MODEL_NAME_MAPPINGS = {
    ModelType.HAIKU: "claude-3-haiku-20240307",
    ModelType.SONNET: "claude-sonnet-4-20250514",
    ModelType.OPUS: "claude-4-opus"
}


def load_agent_prompt_from_md(agent_name: str, force_reload: bool = False) -> Optional[str]:
    """
    Load agent prompt from framework markdown file.
    
    Args:
        agent_name: Agent name (e.g., 'documentation', 'ticketing')
        force_reload: Force reload from file, bypassing cache
        
    Returns:
        str: Agent prompt content from MD file, or None if not found
    """
    try:
        # Get cache instance
        cache = SharedPromptCache.get_instance()
        cache_key = f"{AGENT_CACHE_PREFIX}{agent_name}:md"
        
        # Check cache first (unless force reload)
        if not force_reload:
            cached_content = cache.get(cache_key)
            if cached_content is not None:
                logger.debug(f"Agent prompt for '{agent_name}' loaded from cache")
                return str(cached_content)
        
        # Get MD file path
        md_filename = AGENT_MAPPINGS.get(agent_name)
        if not md_filename:
            logger.warning(f"No MD file mapping found for agent: {agent_name}")
            return None
        
        # Always get fresh framework directory path to ensure we're using the right location
        framework_agent_roles_dir = _get_framework_agent_roles_dir()
        md_path = framework_agent_roles_dir / md_filename
        
        # Check if file exists
        if not md_path.exists():
            logger.warning(f"Agent MD file not found: {md_path}")
            return None
            
        logger.debug(f"Loading agent prompt from: {md_path}")
        content = md_path.read_text(encoding='utf-8')
        
        # Cache the content with 1 hour TTL
        cache.set(cache_key, content, ttl=3600)
        logger.debug(f"Agent prompt for '{agent_name}' cached successfully")
        
        return content
        
    except Exception as e:
        logger.error(f"Error loading agent prompt from MD for '{agent_name}': {e}")
        return None




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
    try:
        analyzer = TaskComplexityAnalyzer()
        
        # Extract additional parameters from kwargs
        file_count = kwargs.get('file_count', 0)
        integration_points = kwargs.get('integration_points', 0)
        requires_research = kwargs.get('requires_research', False)
        requires_testing = kwargs.get('requires_testing', False)
        requires_documentation = kwargs.get('requires_documentation', False)
        technical_depth = kwargs.get('technical_depth', None)
        
        # Analyze task complexity
        result = analyzer.analyze_task(
            task_description=task_description,
            context_size=context_size,
            file_count=file_count,
            integration_points=integration_points,
            requires_research=requires_research,
            requires_testing=requires_testing,
            requires_documentation=requires_documentation,
            technical_depth=technical_depth
        )
        
        return {
            "complexity_score": result.complexity_score,
            "complexity_level": result.complexity_level,
            "recommended_model": result.recommended_model,
            "optimal_prompt_size": result.optimal_prompt_size,
            "scoring_breakdown": result.scoring_breakdown,
            "analysis_details": result.analysis_details
        }
        
    except Exception as e:
        logger.warning(f"Failed to analyze task complexity: {e}")
        return {
            "complexity_score": 50,
            "complexity_level": ComplexityLevel.MEDIUM,
            "recommended_model": ModelType.SONNET,
            "optimal_prompt_size": (700, 1000),
            "error": str(e)
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
    # Check if dynamic model selection is enabled
    enable_dynamic_selection = os.getenv('ENABLE_DYNAMIC_MODEL_SELECTION', 'true').lower() == 'true'
    
    # Debug logging
    logger.debug(f"Environment ENABLE_DYNAMIC_MODEL_SELECTION: {os.getenv('ENABLE_DYNAMIC_MODEL_SELECTION')}")
    logger.debug(f"Enable dynamic selection: {enable_dynamic_selection}")
    
    # Check for per-agent override in environment
    agent_override_key = f"CLAUDE_PM_{agent_name.upper()}_MODEL_SELECTION"
    agent_override = os.getenv(agent_override_key, '').lower()
    
    if agent_override == 'true':
        enable_dynamic_selection = True
    elif agent_override == 'false':
        enable_dynamic_selection = False
    
    # Log model selection decision
    logger.info(f"Model selection for {agent_name}: dynamic={enable_dynamic_selection}, "
                f"complexity_available={complexity_analysis is not None}")
    
    # Dynamic model selection based on complexity
    if enable_dynamic_selection and complexity_analysis:
        recommended_model = complexity_analysis.get('recommended_model', ModelType.SONNET)
        selected_model = MODEL_NAME_MAPPINGS.get(recommended_model, DEFAULT_AGENT_MODELS.get(agent_name, 'claude-sonnet-4-20250514'))
        
        model_config = {
            "selection_method": "dynamic_complexity_based",
            "complexity_score": complexity_analysis.get('complexity_score', 50),
            "complexity_level": complexity_analysis.get('complexity_level', ComplexityLevel.MEDIUM).value,
            "optimal_prompt_size": complexity_analysis.get('optimal_prompt_size', (700, 1000)),
            "scoring_breakdown": complexity_analysis.get('scoring_breakdown', {}),
            "analysis_details": complexity_analysis.get('analysis_details', {})
        }
        
        # Log metrics
        logger.info(f"Dynamic model selection for {agent_name}: "
                    f"model={selected_model}, "
                    f"complexity_score={model_config['complexity_score']}, "
                    f"complexity_level={model_config['complexity_level']}")
        
        # Track model selection metrics
        log_model_selection(
            agent_name=agent_name,
            selected_model=selected_model,
            complexity_score=model_config['complexity_score'],
            selection_method=model_config['selection_method']
        )
        
    else:
        # Use default model mapping
        selected_model = DEFAULT_AGENT_MODELS.get(agent_name, 'claude-sonnet-4-20250514')
        model_config = {
            "selection_method": "default_mapping",
            "reason": "dynamic_selection_disabled" if not enable_dynamic_selection else "no_complexity_analysis"
        }
    
    return selected_model, model_config


def get_agent_prompt(agent_name: str, force_reload: bool = False, return_model_info: bool = False, **kwargs: Any) -> Union[str, Tuple[str, str, Dict[str, Any]]]:
    """
    Get agent prompt from MD file with optional dynamic model selection.
    
    Args:
        agent_name: Agent name (e.g., 'documentation', 'ticketing')
        force_reload: Force reload from source, bypassing cache
        return_model_info: If True, returns tuple (prompt, model, config)
        **kwargs: Additional arguments including:
            - task_description: Description of the task for complexity analysis
            - context_size: Size of context for complexity analysis
            - enable_complexity_analysis: Override for complexity analysis
            - Additional complexity factors (file_count, integration_points, etc.)
        
    Returns:
        str or tuple: Complete agent prompt with base instructions prepended,
                      or tuple of (prompt, selected_model, model_config) if return_model_info=True
    """
    # Load from MD file
    prompt = load_agent_prompt_from_md(agent_name, force_reload)
    
    if prompt is None:
        raise ValueError(f"No agent prompt MD file found for: {agent_name}")
    
    # Analyze task complexity if task description is provided
    complexity_analysis = None
    task_description = kwargs.get('task_description', '')
    enable_analysis = kwargs.get('enable_complexity_analysis', True)
    
    if task_description and enable_analysis:
        # Remove already specified parameters from kwargs to avoid duplicates
        analysis_kwargs = {k: v for k, v in kwargs.items() 
                          if k not in ['task_description', 'context_size']}
        complexity_analysis = _analyze_task_complexity(
            task_description=task_description,
            context_size=kwargs.get('context_size', 0),
            **analysis_kwargs
        )
    
    # Get model configuration (always happens, even without complexity analysis)
    selected_model, model_config = _get_model_config(agent_name, complexity_analysis)
    
    # Always store model selection info in kwargs for potential use by callers
    kwargs['_selected_model'] = selected_model
    kwargs['_model_config'] = model_config
    
    # Handle dynamic template formatting if needed
    if "{dynamic_help}" in prompt:
        try:
            # Import CLI helper module to get dynamic help
            from ..orchestration.ai_trackdown_tools import CLIHelpFormatter
            
            # Create a CLI helper instance
            cli_helper = CLIHelpFormatter()
            help_content, _ = cli_helper.get_cli_help()
            dynamic_help = cli_helper.format_help_for_prompt(help_content)
            prompt = prompt.format(dynamic_help=dynamic_help)
        except Exception as e:
            logger.warning(f"Could not format dynamic help for ticketing agent: {e}")
            # Remove the placeholder if we can't fill it
            prompt = prompt.replace("{dynamic_help}", "")
    
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
        agent_name: Agent name (e.g., 'documentation', 'ticketing')
        force_reload: Force reload from source, bypassing cache
        **kwargs: Additional arguments for prompt generation and model selection
        
    Returns:
        Tuple of (prompt, selected_model, model_config)
    """
    # Use get_agent_prompt with return_model_info=True
    result = get_agent_prompt(agent_name, force_reload, return_model_info=True, **kwargs)
    
    # If result is a tuple, return it directly
    if isinstance(result, tuple):
        return result
    
    # Fallback (shouldn't happen)
    return result, DEFAULT_AGENT_MODELS.get(agent_name, 'claude-sonnet-4-20250514'), {"selection_method": "default"}


# Utility functions
def list_available_agents() -> Dict[str, Dict[str, Any]]:
    """
    List all available agents with their sources.
    
    Returns:
        dict: Agent information including MD file path
    """
    agents = {}
    
    # Get fresh framework directory path
    framework_agent_roles_dir = _get_framework_agent_roles_dir()
    
    for agent_name, md_filename in AGENT_MAPPINGS.items():
        md_path = framework_agent_roles_dir / md_filename
        
        agents[agent_name] = {
            "md_file": md_filename if md_path.exists() else None,
            "md_path": str(md_path) if md_path.exists() else None,
            "has_md": md_path.exists(),
            "default_model": DEFAULT_AGENT_MODELS.get(agent_name, 'claude-sonnet-4-20250514')
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
            cache_key = f"{AGENT_CACHE_PREFIX}{agent_name}:md"
            cache.invalidate(cache_key)
            logger.debug(f"Cache cleared for agent: {agent_name}")
        else:
            # Clear all agent caches
            for name in AGENT_MAPPINGS:
                cache_key = f"{AGENT_CACHE_PREFIX}{name}:md"
                cache.invalidate(cache_key)
            logger.debug("All agent caches cleared")
            
    except Exception as e:
        logger.error(f"Error clearing agent cache: {e}")


def validate_agent_files() -> Dict[str, Dict[str, Any]]:
    """
    Validate that all expected agent files exist.
    
    Returns:
        dict: Validation results for each agent
    """
    results = {}
    
    # Get fresh framework directory path
    framework_agent_roles_dir = _get_framework_agent_roles_dir()
    
    for agent_name, md_filename in AGENT_MAPPINGS.items():
        md_path = framework_agent_roles_dir / md_filename
        results[agent_name] = {
            "md_exists": md_path.exists(),
            "md_path": str(md_path)
        }
    
    return results


def get_model_selection_metrics() -> Dict[str, Any]:
    """
    Get metrics about model selection usage.
    
    Returns:
        dict: Metrics including feature flag status and selection counts
    """
    # Check feature flag status
    global_enabled = os.getenv('ENABLE_DYNAMIC_MODEL_SELECTION', 'true').lower() == 'true'
    
    # Check per-agent overrides
    agent_overrides = {}
    for agent_name in AGENT_MAPPINGS.keys():
        override_key = f"CLAUDE_PM_{agent_name.upper()}_MODEL_SELECTION"
        override_value = os.getenv(override_key, '')
        if override_value:
            agent_overrides[agent_name] = override_value.lower() == 'true'
    
    # Get cache instance to check for cached metrics
    try:
        cache = SharedPromptCache.get_instance()
        selection_stats = cache.get("agent_loader:model_selection_stats") or {}
    except Exception:
        selection_stats = {}
    
    return {
        "feature_flag": {
            "global_enabled": global_enabled,
            "agent_overrides": agent_overrides
        },
        "model_thresholds": {
            model_type.value: thresholds 
            for model_type, thresholds in MODEL_THRESHOLDS.items()
        },
        "default_models": DEFAULT_AGENT_MODELS,
        "selection_stats": selection_stats
    }


def log_model_selection(agent_name: str, selected_model: str, complexity_score: int, selection_method: str) -> None:
    """
    Log model selection for metrics tracking.
    
    Args:
        agent_name: Name of the agent
        selected_model: Model that was selected
        complexity_score: Complexity score from analysis
        selection_method: Method used for selection
    """
    try:
        # Get cache instance
        cache = SharedPromptCache.get_instance()
        
        # Get existing stats
        stats_key = "agent_loader:model_selection_stats"
        stats = cache.get(stats_key) or {
            "total_selections": 0,
            "by_model": {},
            "by_agent": {},
            "by_method": {},
            "complexity_distribution": {
                "0-30": 0,
                "31-70": 0,
                "71-100": 0
            }
        }
        
        # Update stats
        stats["total_selections"] += 1
        
        # By model
        if selected_model not in stats["by_model"]:
            stats["by_model"][selected_model] = 0
        stats["by_model"][selected_model] += 1
        
        # By agent
        if agent_name not in stats["by_agent"]:
            stats["by_agent"][agent_name] = {}
        if selected_model not in stats["by_agent"][agent_name]:
            stats["by_agent"][agent_name][selected_model] = 0
        stats["by_agent"][agent_name][selected_model] += 1
        
        # By method
        if selection_method not in stats["by_method"]:
            stats["by_method"][selection_method] = 0
        stats["by_method"][selection_method] += 1
        
        # Complexity distribution
        if complexity_score <= 30:
            stats["complexity_distribution"]["0-30"] += 1
        elif complexity_score <= 70:
            stats["complexity_distribution"]["31-70"] += 1
        else:
            stats["complexity_distribution"]["71-100"] += 1
        
        # Store updated stats with 24 hour TTL
        cache.set(stats_key, stats, ttl=86400)
        
    except Exception as e:
        logger.warning(f"Failed to log model selection metrics: {e}")