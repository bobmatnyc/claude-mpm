"""Agent registry integration for Claude MPM."""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import importlib.util

try:
    from ..utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger


class SimpleAgentRegistry:
    """Simple agent registry implementation."""
    
    def __init__(self, framework_path: Path):
        self.framework_path = framework_path
        self.agents = {}
        self._discover_agents()
    
    def _discover_agents(self):
        """Discover agents from the framework."""
        agents_dir = self.framework_path / "src" / "claude_mpm" / "agents"
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                agent_id = agent_file.stem
                self.agents[agent_id] = {
                    'type': agent_id,
                    'path': str(agent_file),
                    'last_modified': agent_file.stat().st_mtime
                }
    
    def listAgents(self, **kwargs):
        """List all agents."""
        return self.agents


class AgentRegistryAdapter:
    """
    Adapter to integrate claude-multiagent-pm's agent registry.
    
    This adapter:
    1. Locates the claude-multiagent-pm installation
    2. Dynamically imports the agent registry
    3. Provides a clean interface for agent operations
    """
    
    def __init__(self, framework_path: Optional[Path] = None):
        """
        Initialize the agent registry adapter.
        
        Args:
            framework_path: Path to claude-multiagent-pm (auto-detected if None)
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
            (path / "src" / "claude_mpm").exists() and 
            (path / "src" / "claude_mpm" / "agents").exists()
        )
    
    def _initialize_registry(self):
        """Initialize the agent registry."""
        if not self.framework_path:
            self.logger.warning("No framework path, registry unavailable")
            return
        
        try:
            # For now, create a simple registry implementation
            # This will be replaced with proper agent discovery later
            self.registry = SimpleAgentRegistry(self.framework_path)
            self.logger.info("Agent registry initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize registry: {e}")
    
    def list_agents(self, **kwargs) -> Dict[str, Any]:
        """
        List available agents.
        
        Args:
            **kwargs: Arguments to pass to AgentRegistry.listAgents()
            
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
            if required_specializations:
                agents = self.registry.listAgents(specializations=required_specializations)
            else:
                agents = self.registry.listAgents()
            
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
            
            # Categorize by path
            for agent_id, metadata in all_agents.items():
                agent_path = metadata.get('path', '')
                
                if 'project-specific' in agent_path:
                    hierarchy['project'].append(agent_id)
                elif 'user-agents' in agent_path or 'user-defined' in agent_path:
                    hierarchy['user'].append(agent_id)
                else:
                    hierarchy['system'].append(agent_id)
            
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
            'version-control',
            'data-engineer'
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
            'version-control': 'Versioner',
            'data-engineer': 'Data Engineer'
        }
        
        nickname = nicknames.get(agent_name, agent_name.title())
        
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        return f"""**{nickname}**: {task}

TEMPORAL CONTEXT: Today is {today}. Apply date awareness to task execution.

**Task**: {task}

**Context**: {context}

**Authority**: Agent has full authority for {agent_name} operations
**Expected Results**: Completed task with operational insights"""