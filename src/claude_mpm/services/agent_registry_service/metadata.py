"""
Agent Metadata Types and Structures
Provides data structures for agent registry entries

Created: 2025-07-19
Purpose: Agent metadata definitions for registry system
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class AgentMetadata:
    """Enhanced agent metadata structure for registry entries with specialization and model support"""
    name: str
    type: str
    path: str
    tier: str  # 'user', 'system', 'project'
    description: Optional[str] = None
    version: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    last_modified: Optional[float] = None
    file_size: Optional[int] = None
    validated: bool = False
    error_message: Optional[str] = None
    # Enhanced metadata for ISS-0118
    specializations: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    is_hybrid: bool = False
    hybrid_types: List[str] = field(default_factory=list)
    composite_agents: List[str] = field(default_factory=list)
    validation_score: float = 0.0
    complexity_level: str = 'basic'  # 'basic', 'intermediate', 'advanced', 'expert'
    # Model configuration fields
    preferred_model: Optional[str] = None
    model_config: Optional[Dict[str, Any]] = field(default_factory=dict)