"""
Data models and enums for agent profile loader.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any


class ProfileTier(Enum):
    """Profile hierarchy tiers with precedence order."""
    PROJECT = "project"      # Highest precedence
    USER = "user"           # Medium precedence  
    SYSTEM = "system"       # Lowest precedence (fallback)


class ProfileStatus(Enum):
    """Profile status options."""
    ACTIVE = "active"
    IMPROVED = "improved"
    TRAINING = "training"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class ImprovedPrompt:
    """Enhanced prompt from training system."""
    agent_type: str
    original_prompt: str
    improved_prompt: str
    improvement_score: float
    training_session_id: str
    timestamp: datetime
    validation_metrics: Dict[str, Any] = field(default_factory=dict)
    deployment_ready: bool = False
    
    @property
    def prompt_id(self) -> str:
        """Unique prompt identifier."""
        return f"{self.agent_type}_{self.training_session_id}"


@dataclass
class AgentProfile:
    """Comprehensive agent profile with enhanced capabilities."""
    name: str
    tier: ProfileTier
    path: Path
    role: str
    capabilities: List[str] = field(default_factory=list)
    authority_scope: List[str] = field(default_factory=list)
    context_preferences: Dict[str, Any] = field(default_factory=dict)
    escalation_criteria: List[str] = field(default_factory=list)
    integration_patterns: Dict[str, str] = field(default_factory=dict)
    quality_standards: List[str] = field(default_factory=list)
    communication_style: Dict[str, str] = field(default_factory=dict)
    content: str = ""
    
    # Enhanced attributes for improved prompt integration
    prompt_template_id: Optional[str] = None
    improved_prompt: Optional[ImprovedPrompt] = None
    prompt_version: str = "1.0.0"
    training_enabled: bool = True
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    status: ProfileStatus = ProfileStatus.ACTIVE
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def profile_id(self) -> str:
        """Unique profile identifier."""
        return f"{self.tier.value}:{self.name}"
    
    @property
    def nickname(self) -> str:
        """Agent nickname for Task Tool integration."""
        nickname_map = {
            'engineer': 'Engineer',
            'documentation': 'Documenter',
            'qa': 'QA',
            'ops': 'Ops',
            'security': 'Security',
            'research': 'Researcher',
            'version_control': 'Versioner',
            'ticketing': 'Ticketer',
            'data_engineer': 'Data Engineer',
            'architect': 'Architect',
            'pm': 'PM',
            'orchestrator': 'Orchestrator'
        }
        return nickname_map.get(self.name, self.name.title())
    
    @property
    def has_improved_prompt(self) -> bool:
        """Check if profile has improved prompt."""
        return self.improved_prompt is not None and self.improved_prompt.deployment_ready
    
    def get_effective_prompt(self) -> str:
        """Get the most effective prompt (improved or original)."""
        if self.has_improved_prompt:
            return self.improved_prompt.improved_prompt
        return self.content