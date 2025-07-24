"""
Core Agent Registry Module - Core framework exposure of agent registry functionality

This module exposes the AgentRegistry from services to the core framework layer,
providing the expected interface for core framework operations.

Created: 2025-07-16 (Emergency restoration)
Updated: 2025-07-18 (Switch to synchronous implementation)
Purpose: Restore missing claude_pm.core.agent_registry import with synchronous operations
"""

# Import AgentRegistry from synchronous services and expose it at core level
from claude_pm.services.agent_registry_sync import AgentRegistry, AgentMetadata
from typing import Dict, Set, List, Any, Optional

# Expose key classes and functions for core framework access
__all__ = [
    'AgentRegistry', 
    'AgentMetadata',
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

# Create convenience aliases for common operations
def create_agent_registry(cache_service: Any = None) -> AgentRegistry:
    """
    Create a new AgentRegistry instance
    
    Args:
        cache_service: Optional cache service for performance optimization
        
    Returns:
        AgentRegistry instance
    """
    return AgentRegistry(cache_service=cache_service)

def discover_agents(force_refresh: bool = False) -> Dict[str, AgentMetadata]:
    """
    Convenience function for synchronous agent discovery
    
    Args:
        force_refresh: Force cache refresh
        
    Returns:
        Dictionary of discovered agents
    """
    registry = AgentRegistry()
    return registry.discover_agents(force_refresh=force_refresh)

def get_core_agent_types() -> Set[str]:
    """
    Get the set of core agent types
    
    Returns:
        Set of core agent type names
    """
    registry = AgentRegistry()
    return registry.core_agent_types

def get_specialized_agent_types() -> Set[str]:
    """
    Get the set of specialized agent types beyond core 9
    
    Returns:
        Set of specialized agent type names
    """
    registry = AgentRegistry()
    return registry.specialized_agent_types

# Add convenience method for synchronous access with camelCase naming
def listAgents() -> Dict[str, Dict[str, Any]]:
    """
    Synchronous function for listing all agents (camelCase compatibility)
    
    This provides a synchronous interface for simple agent listing operations
    that matches the camelCase naming convention in CLAUDE.md documentation.
    
    Returns:
        Dictionary of agent name -> agent metadata
    """
    registry = AgentRegistry()
    # The sync version already has a listAgents method that returns a dict
    return registry.listAgents()

# Add synchronous convenience functions
def list_agents(agent_type: Optional[str] = None, tier: Optional[str] = None) -> List[AgentMetadata]:
    """
    Synchronous function to list agents with optional filtering
    
    Args:
        agent_type: Filter by agent type
        tier: Filter by hierarchy tier
        
    Returns:
        List of agent metadata dictionaries
    """
    registry = AgentRegistry()
    return registry.list_agents(agent_type=agent_type, tier=tier)

def discover_agents_sync(force_refresh: bool = False) -> Dict[str, AgentMetadata]:
    """
    Synchronous function for agent discovery
    
    Args:
        force_refresh: Force cache refresh
        
    Returns:
        Dictionary of discovered agents
    """
    registry = AgentRegistry()
    return registry.discover_agents(force_refresh=force_refresh)

def get_agent(agent_name: str) -> Optional[Dict[str, Any]]:
    """
    Synchronous function to get a specific agent
    
    Args:
        agent_name: Name of agent to retrieve
        
    Returns:
        Agent metadata or None
    """
    registry = AgentRegistry()
    agent = registry.get_agent(agent_name)
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
    registry = AgentRegistry()
    # This method doesn't exist in sync version, return basic stats
    agents = registry.list_agents()
    return {
        'total_agents': len(agents),
        'agent_types': len(set(a.type for a in agents)),
        'tiers': list(set(a.tier for a in agents))
    }