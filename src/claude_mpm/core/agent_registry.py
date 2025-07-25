"""
Consolidated Agent Registry for Claude MPM.

This module combines functionality from:
- agent_registry.py (current working implementation)
- agent_registry_original.py (legacy convenience functions)

Provides:
- Agent discovery from the framework
- Agent listing and selection
- Compatibility with both sync and async interfaces
- Legacy function names for backwards compatibility
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
import importlib.util
from datetime import datetime
from dataclasses import dataclass

try:
    from ..core.logger import get_logger
except ImportError:
    from core.logger import get_logger


@dataclass
class AgentMetadata:
    """Metadata for an agent."""
    name: str
    type: str
    path: str
    tier: str = "system"
    last_modified: float = 0.0
    specializations: List[str] = None
    description: str = ""
    
    def __post_init__(self):
        if self.specializations is None:
            self.specializations = []


class SimpleAgentRegistry:
    """Simple agent registry implementation."""
    
    def __init__(self, framework_path: Path):
        self.framework_path = framework_path
        self.agents = {}
        self._discover_agents()
    
    def _discover_agents(self):
        """Discover agents from the framework."""
        # Check multiple possible locations
        agent_locations = [
            self.framework_path / "src" / "claude_mpm" / "agents" / "templates",
            self.framework_path / "src" / "claude_mpm" / "agents",
            self.framework_path / "agents",
        ]
        
        for agents_dir in agent_locations:
            if agents_dir.exists():
                # Look for both .md and .json files
                for pattern in ["*.md", "*.json"]:
                    for agent_file in agents_dir.glob(pattern):
                        agent_id = agent_file.stem
                        self.agents[agent_id] = {
                            'name': agent_id,
                            'type': agent_id,
                            'path': str(agent_file),
                            'last_modified': agent_file.stat().st_mtime,
                            'tier': self._determine_tier(agent_file),
                            'specializations': self._extract_specializations(agent_id),
                            'description': self._extract_description(agent_id)
                        }
    
    def _determine_tier(self, agent_path: Path) -> str:
        """Determine agent tier based on path."""
        path_str = str(agent_path)
        if 'project' in path_str or '.claude-mpm' in path_str:
            return 'project'
        elif 'user' in path_str or str(Path.home()) in path_str:
            return 'user'
        else:
            return 'system'
    
    def _extract_specializations(self, agent_id: str) -> List[str]:
        """Extract specializations based on agent type."""
        specialization_map = {
            'engineer': ['coding', 'architecture', 'implementation'],
            'documentation': ['docs', 'api', 'guides'],
            'qa': ['testing', 'quality', 'validation'],
            'research': ['analysis', 'investigation', 'exploration'],
            'ops': ['deployment', 'monitoring', 'infrastructure'],
            'security': ['security', 'audit', 'compliance'],
            'version_control': ['git', 'versioning', 'releases'],
            'data_engineer': ['data', 'etl', 'analytics']
        }
        return specialization_map.get(agent_id, [])
    
    def _extract_description(self, agent_id: str) -> str:
        """Extract description for agent."""
        descriptions = {
            'engineer': 'Software engineering and implementation',
            'documentation': 'Documentation creation and maintenance',
            'qa': 'Quality assurance and testing',
            'research': 'Research and investigation',
            'ops': 'Operations and deployment',
            'security': 'Security analysis and compliance',
            'version_control': 'Version control and release management',
            'data_engineer': 'Data engineering and analytics'
        }
        return descriptions.get(agent_id, f'{agent_id.title()} agent')
    
    def listAgents(self, **kwargs) -> Dict[str, Any]:
        """List all agents (camelCase for compatibility)."""
        return self.agents
    
    def list_agents(self, agent_type: Optional[str] = None, tier: Optional[str] = None) -> List[AgentMetadata]:
        """List agents with optional filtering."""
        results = []
        for agent_id, metadata in self.agents.items():
            if agent_type and metadata.get('type') != agent_type:
                continue
            if tier and metadata.get('tier') != tier:
                continue
            
            results.append(AgentMetadata(
                name=metadata['name'],
                type=metadata['type'],
                path=metadata['path'],
                tier=metadata.get('tier', 'system'),
                last_modified=metadata.get('last_modified', 0),
                specializations=metadata.get('specializations', []),
                description=metadata.get('description', '')
            ))
        return results
    
    def get_agent(self, agent_name: str) -> Optional[AgentMetadata]:
        """Get a specific agent."""
        metadata = self.agents.get(agent_name)
        if metadata:
            return AgentMetadata(
                name=metadata['name'],
                type=metadata['type'],
                path=metadata['path'],
                tier=metadata.get('tier', 'system'),
                last_modified=metadata.get('last_modified', 0),
                specializations=metadata.get('specializations', []),
                description=metadata.get('description', '')
            )
        return None
    
    def discover_agents(self, force_refresh: bool = False) -> Dict[str, AgentMetadata]:
        """Discover agents (optionally refresh)."""
        if force_refresh:
            self.agents.clear()
            self._discover_agents()
        
        return {
            agent_id: AgentMetadata(
                name=metadata['name'],
                type=metadata['type'],
                path=metadata['path'],
                tier=metadata.get('tier', 'system'),
                last_modified=metadata.get('last_modified', 0),
                specializations=metadata.get('specializations', []),
                description=metadata.get('description', '')
            )
            for agent_id, metadata in self.agents.items()
        }
    
    @property
    def core_agent_types(self) -> Set[str]:
        """Get core agent types."""
        return {
            'documentation',
            'engineer', 
            'qa',
            'research',
            'ops',
            'security',
            'version_control',
            'data_engineer'
        }
    
    @property
    def specialized_agent_types(self) -> Set[str]:
        """Get specialized agent types beyond core."""
        all_types = set(metadata['type'] for metadata in self.agents.values())
        return all_types - self.core_agent_types


class AgentRegistryAdapter:
    """
    Adapter to integrate agent registry functionality.
    
    This adapter:
    1. Locates the claude-mpm installation
    2. Provides a clean interface for agent operations
    3. Maintains backwards compatibility
    """
    
    def __init__(self, framework_path: Optional[Path] = None):
        """
        Initialize the agent registry adapter.
        
        Args:
            framework_path: Path to claude-mpm (auto-detected if None)
        """
        self.logger = get_logger("agent_registry")
        self.framework_path = framework_path or self._find_framework()
        self.registry = None
        self._initialize_registry()
    
    def _find_framework(self) -> Optional[Path]:
        """Find claude-mpm installation.
        
        Search order:
        1. CLAUDE_MPM_PATH environment variable
        2. Current working directory (if it's claude-mpm)
        3. Walk up from current file location
        4. Common development locations
        """
        # Check environment variable first
        env_path = os.environ.get("CLAUDE_MPM_PATH")
        if env_path:
            candidate = Path(env_path)
            if self._is_valid_framework_path(candidate):
                self.logger.info(f"Using claude-mpm from CLAUDE_MPM_PATH: {candidate}")
                return candidate
            else:
                self.logger.warning(f"CLAUDE_MPM_PATH is set but invalid: {env_path}")
        
        # Check current working directory
        cwd = Path.cwd()
        if self._is_valid_framework_path(cwd):
            return cwd
            
        # Check if we're running from within the installed package
        current_file = Path(__file__).resolve()
        for parent in current_file.parents:
            if self._is_valid_framework_path(parent):
                return parent
            # Stop at site-packages or similar
            if parent.name in ("site-packages", "dist-packages", "lib"):
                break
        
        # Check common development locations
        candidates = [
            Path.home() / "Projects" / "claude-mpm",
            Path.home() / "claude-mpm",
        ]
        
        for candidate in candidates:
            if self._is_valid_framework_path(candidate):
                self.logger.info(f"Found claude-mpm at: {candidate}")
                return candidate
        
        return None
    
    def _is_valid_framework_path(self, path: Path) -> bool:
        """Check if a path is a valid claude-mpm installation."""
        return (
            path.exists() and 
            (path / "src" / "claude_mpm").exists()
        )
    
    def _initialize_registry(self):
        """Initialize the agent registry."""
        if not self.framework_path:
            self.logger.warning("No framework path, registry unavailable")
            return
        
        try:
            self.registry = SimpleAgentRegistry(self.framework_path)
            self.logger.info("Agent registry initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize registry: {e}")
    
    def list_agents(self, **kwargs) -> Dict[str, Any]:
        """
        List available agents.
        
        Args:
            **kwargs: Arguments to pass to registry
            
        Returns:
            Dictionary of agents with metadata
        """
        if not self.registry:
            return {}
        
        try:
            return self.registry.listAgents(**kwargs)
        except Exception as e:
            self.logger.error(f"Error listing agents: {e}")
            return {}
    
    def get_agent_definition(self, agent_name: str) -> Optional[str]:
        """
        Get agent definition by name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent definition content or None
        """
        if not self.registry:
            return None
        
        try:
            # Try to load agent definition
            agents = self.registry.listAgents()
            for agent_id, metadata in agents.items():
                if agent_name in agent_id or agent_name == metadata.get('type'):
                    # Load the agent file
                    agent_path = Path(metadata['path'])
                    if agent_path.exists():
                        return agent_path.read_text()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting agent definition: {e}")
            return None
    
    def select_agent_for_task(self, task_description: str, required_specializations: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Select optimal agent for a task.
        
        Args:
            task_description: Description of the task
            required_specializations: Required agent specializations
            
        Returns:
            Agent metadata or None
        """
        if not self.registry:
            return None
        
        try:
            # Get agents with required specializations
            agents = self.registry.listAgents()
            
            if required_specializations:
                # Filter by specializations
                filtered = {}
                for agent_id, metadata in agents.items():
                    agent_specs = set(metadata.get('specializations', []))
                    if any(spec in agent_specs for spec in required_specializations):
                        filtered[agent_id] = metadata
                agents = filtered
            
            if not agents:
                return None
            
            # For now, return the first matching agent
            # In future, could implement more sophisticated selection
            agent_id = next(iter(agents))
            return {
                'id': agent_id,
                'metadata': agents[agent_id]
            }
            
        except Exception as e:
            self.logger.error(f"Error selecting agent: {e}")
            return None
    
    def get_agent_hierarchy(self) -> Dict[str, List[str]]:
        """
        Get agent hierarchy (project → user → system).
        
        Returns:
            Dictionary with hierarchy levels and agent names
        """
        if not self.registry:
            return {
                'project': [],
                'user': [],
                'system': []
            }
        
        try:
            # Get all agents
            all_agents = self.registry.listAgents()
            
            hierarchy = {
                'project': [],
                'user': [],
                'system': []
            }
            
            # Categorize by tier
            for agent_id, metadata in all_agents.items():
                tier = metadata.get('tier', 'system')
                hierarchy[tier].append(agent_id)
            
            return hierarchy
            
        except Exception as e:
            self.logger.error(f"Error getting hierarchy: {e}")
            return {'project': [], 'user': [], 'system': []}
    
    def get_core_agents(self) -> List[str]:
        """
        Get list of core system agents.
        
        Returns:
            List of core agent names
        """
        return [
            'documentation',
            'engineer', 
            'qa',
            'research',
            'ops',
            'security',
            'version_control',
            'data_engineer'
        ]
    
    def format_agent_for_task_tool(self, agent_name: str, task: str, context: str = "") -> str:
        """
        Format agent delegation for Task Tool.
        
        Args:
            agent_name: Name of the agent
            task: Task description
            context: Additional context
            
        Returns:
            Formatted Task Tool prompt
        """
        # Map agent names to nicknames
        nicknames = {
            'documentation': 'Documenter',
            'engineer': 'Engineer',
            'qa': 'QA',
            'research': 'Researcher',
            'ops': 'Ops',
            'security': 'Security',
            'version_control': 'Versioner',
            'data_engineer': 'Data Engineer'
        }
        
        nickname = nicknames.get(agent_name, agent_name.title())
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        return f"""**{nickname}**: {task}

TEMPORAL CONTEXT: Today is {today}. Apply date awareness to task execution.

**Task**: {task}

**Context**: {context}

**Authority**: Agent has full authority for {agent_name} operations
**Expected Results**: Completed task with operational insights"""


# Export main class as AgentRegistry for compatibility
AgentRegistry = SimpleAgentRegistry

# Convenience functions for backwards compatibility
def create_agent_registry(cache_service: Any = None, framework_path: Optional[Path] = None) -> AgentRegistry:
    """
    Create a new AgentRegistry instance
    
    Args:
        cache_service: Ignored for compatibility
        framework_path: Path to framework (auto-detected if None)
        
    Returns:
        AgentRegistry instance
    """
    if not framework_path:
        adapter = AgentRegistryAdapter()
        framework_path = adapter.framework_path
    
    if framework_path:
        return AgentRegistry(framework_path)
    else:
        raise ValueError("Could not find claude-mpm framework path")

def discover_agents(force_refresh: bool = False) -> Dict[str, AgentMetadata]:
    """
    Convenience function for synchronous agent discovery
    
    Args:
        force_refresh: Force cache refresh
        
    Returns:
        Dictionary of discovered agents
    """
    adapter = AgentRegistryAdapter()
    if adapter.registry:
        return adapter.registry.discover_agents(force_refresh=force_refresh)
    return {}

def get_core_agent_types() -> Set[str]:
    """
    Get the set of core agent types
    
    Returns:
        Set of core agent type names
    """
    adapter = AgentRegistryAdapter()
    if adapter.registry:
        return adapter.registry.core_agent_types
    return set()

def get_specialized_agent_types() -> Set[str]:
    """
    Get the set of specialized agent types beyond core 9
    
    Returns:
        Set of specialized agent type names
    """
    adapter = AgentRegistryAdapter()
    if adapter.registry:
        return adapter.registry.specialized_agent_types
    return set()

def listAgents() -> Dict[str, Dict[str, Any]]:
    """
    Synchronous function for listing all agents (camelCase compatibility)
    
    Returns:
        Dictionary of agent name -> agent metadata
    """
    adapter = AgentRegistryAdapter()
    if adapter.registry:
        return adapter.registry.listAgents()
    return {}

def list_agents(agent_type: Optional[str] = None, tier: Optional[str] = None) -> List[AgentMetadata]:
    """
    Synchronous function to list agents with optional filtering
    
    Args:
        agent_type: Filter by agent type
        tier: Filter by hierarchy tier
        
    Returns:
        List of agent metadata dictionaries
    """
    adapter = AgentRegistryAdapter()
    if adapter.registry:
        return adapter.registry.list_agents(agent_type=agent_type, tier=tier)
    return []

def discover_agents_sync(force_refresh: bool = False) -> Dict[str, AgentMetadata]:
    """
    Synchronous function for agent discovery
    
    Args:
        force_refresh: Force cache refresh
        
    Returns:
        Dictionary of discovered agents
    """
    return discover_agents(force_refresh)

def get_agent(agent_name: str) -> Optional[Dict[str, Any]]:
    """
    Synchronous function to get a specific agent
    
    Args:
        agent_name: Name of agent to retrieve
        
    Returns:
        Agent metadata or None
    """
    adapter = AgentRegistryAdapter()
    if adapter.registry:
        agent = adapter.registry.get_agent(agent_name)
        if agent:
            return {
                'name': agent.name,
                'type': agent.type,
                'path': agent.path,
                'tier': agent.tier,
                'last_modified': agent.last_modified,
                'specializations': agent.specializations,
                'description': agent.description
            }
    return None

def get_registry_stats() -> Dict[str, Any]:
    """
    Synchronous function to get registry statistics
    
    Returns:
        Dictionary of registry statistics
    """
    adapter = AgentRegistryAdapter()
    if adapter.registry:
        agents = adapter.registry.list_agents()
        return {
            'total_agents': len(agents),
            'agent_types': len(set(a.type for a in agents)),
            'tiers': list(set(a.tier for a in agents))
        }
    return {'total_agents': 0, 'agent_types': 0, 'tiers': []}


# Export all public symbols
__all__ = [
    'AgentRegistry',
    'AgentRegistryAdapter', 
    'AgentMetadata',
    'SimpleAgentRegistry',
    'create_agent_registry',
    'discover_agents',
    'get_core_agent_types',
    'get_specialized_agent_types',
    'listAgents',
    'list_agents',
    'discover_agents_sync',
    'get_agent',
    'get_registry_stats'
]