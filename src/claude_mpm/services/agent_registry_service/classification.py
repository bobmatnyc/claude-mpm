"""
Agent Classification Module
Handles agent type classification and categorization

Created: 2025-07-19
Purpose: Agent type classification functionality
"""

import logging
from pathlib import Path
from typing import Dict, List

from .utils import (
    CORE_AGENT_TYPES, SPECIALIZED_AGENT_TYPES, CLASSIFICATION_PATTERNS
)

logger = logging.getLogger(__name__)


def classify_agent_type(agent_name: str, agent_file: Path) -> str:
    """
    Enhanced agent type classification supporting specialized agents beyond core 9 types.
    Implements comprehensive pattern-based detection for ISS-0118.
    
    Args:
        agent_name: Agent name
        agent_file: Agent file path
        
    Returns:
        Agent type classification
    """
    name_lower = agent_name.lower()
    
    # First check for core agent types (highest priority)
    # Special handling for data-agent -> data_engineer mapping
    if 'data-agent' in name_lower or 'data_agent' in name_lower:
        return 'data_engineer'
    
    for core_type in CORE_AGENT_TYPES:
        if core_type in name_lower or name_lower in core_type:
            return core_type
    
    # Check specialized agent patterns
    for agent_type, patterns in CLASSIFICATION_PATTERNS.items():
        if any(pattern in name_lower for pattern in patterns):
            return agent_type
    
    # Enhanced core agent type pattern matching (fallback)
    core_patterns = {
        'documentation': ['doc', 'docs', 'manual', 'guide', 'readme'],
        'ticketing': ['ticket', 'issue', 'bug', 'task', 'jira'],
        'version_control': ['version', 'git', 'vcs', 'commit', 'branch', 'merge'],
        'qa': ['qa', 'quality', 'assurance', 'validation', 'verification'],
        'research': ['research', 'analyze', 'investigate', 'study', 'explore'],
        'ops': ['ops', 'operations', 'maintenance', 'administration'],
        'security': ['security', 'auth', 'permission', 'vulnerability', 'encryption'],
        'engineer': ['engineer', 'code', 'develop', 'programming', 'implementation'],
        'data_engineer': ['data_engineer', 'etl', 'pipeline', 'warehouse']
    }
    
    for core_type, patterns in core_patterns.items():
        if any(pattern in name_lower for pattern in patterns):
            return core_type
    
    # Path-based classification hints
    path_str = str(agent_file).lower()
    if 'frontend' in path_str or 'ui' in path_str:
        return 'frontend'
    elif 'backend' in path_str or 'api' in path_str:
        return 'backend'
    elif 'database' in path_str or 'db' in path_str:
        return 'database'
    elif 'test' in path_str:
        return 'testing'
    elif 'deploy' in path_str:
        return 'deployment'
    
    return 'custom'