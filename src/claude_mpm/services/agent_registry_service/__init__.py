"""
Agent Registry Service - Synchronous Implementation
Provides fully synchronous agent discovery without async complexity

Created: 2025-07-19
Purpose: Modularized synchronous agent registry for CLI/script usage
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import asdict
import logging

from .metadata import AgentMetadata
from .cache import AgentRegistryCache
from .discovery import AgentDiscovery
from .validation import AgentValidator
from .utils import (
    CORE_AGENT_TYPES, SPECIALIZED_AGENT_TYPES,
    determine_tier, has_tier_precedence
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Core Agent Registry - Fully synchronous agent discovery and management system
    
    Features:
    - Two-tier hierarchy discovery (user → system)
    - Synchronous directory scanning
    - Agent metadata collection and caching
    - Agent type detection and classification
    - SharedPromptCache integration
    - Agent validation and error handling
    """
    
    def __init__(self, cache_service=None, model_selector=None):
        """Initialize AgentRegistry with optional cache service and model selector"""
        self.cache_manager = AgentRegistryCache(cache_service)
        self.discovery = AgentDiscovery(model_selector)
        self.validator = AgentValidator()
        self.model_selector = model_selector
        
        self.registry: Dict[str, AgentMetadata] = {}
        self.discovery_paths: List[Path] = []
        self.core_agent_types = CORE_AGENT_TYPES
        self.specialized_agent_types = SPECIALIZED_AGENT_TYPES
        
        # Initialize discovery paths
        self.discovery_paths = self.discovery.initialize_discovery_paths()
        
        # Expose cache_service and last_discovery_time for backward compatibility
        self.cache_service = self.cache_manager.cache_service
        
    @property
    def last_discovery_time(self):
        """Expose last_discovery_time from cache manager"""
        return self.cache_manager.last_discovery_time
    
    @last_discovery_time.setter
    def last_discovery_time(self, value):
        """Set last_discovery_time on cache manager"""
        self.cache_manager.last_discovery_time = value
    
    def discover_agents(self, force_refresh: bool = False) -> Dict[str, AgentMetadata]:
        """
        Discover all available agents across two-tier hierarchy
        
        Args:
            force_refresh: Force cache refresh even if within TTL
            
        Returns:
            Dictionary of agent name -> AgentMetadata
        """
        discovery_start = time.time()
        
        # Check if we need to refresh discovery
        if not force_refresh and self.cache_manager.is_discovery_cache_valid():
            cache_hit = self.cache_manager.get_cached_discovery()
            if cache_hit:
                self.registry = {name: AgentMetadata(**data) for name, data in cache_hit.items()}
                return self.registry
        
        logger.info("Starting agent discovery across hierarchy")
        discovered_agents = {}
        
        # Discover agents from each path with hierarchy precedence
        for path in self.discovery_paths:
            tier = determine_tier(path)
            path_agents = self.discovery.scan_directory(path, tier)
            
            # Apply hierarchy precedence (user overrides system)
            for agent_name, agent_metadata in path_agents.items():
                if agent_name not in discovered_agents:
                    discovered_agents[agent_name] = agent_metadata
                    logger.debug(f"Discovered agent '{agent_name}' from {tier} tier")
                else:
                    # Check tier precedence
                    existing_tier = discovered_agents[agent_name].tier
                    if has_tier_precedence(tier, existing_tier):
                        discovered_agents[agent_name] = agent_metadata
                        logger.debug(f"Agent '{agent_name}' overridden by {tier} tier")
        
        # Validate discovered agents
        validated_agents = self.validator.validate_agents(discovered_agents)
        
        # Update registry and cache
        self.registry = validated_agents
        self.cache_manager.cache_discovery_results(validated_agents)
        
        discovery_time = time.time() - discovery_start
        logger.info(f"Agent discovery completed in {discovery_time:.3f}s, found {len(validated_agents)} agents")
        
        return self.registry
    
    def get_agent(self, agent_name: str) -> Optional[AgentMetadata]:
        """
        Get specific agent metadata
        
        Args:
            agent_name: Name of agent to retrieve
            
        Returns:
            AgentMetadata or None if not found
        """
        if not self.registry:
            self.discover_agents()
        
        return self.registry.get(agent_name)
    
    def list_agents(self, agent_type: Optional[str] = None, tier: Optional[str] = None) -> List[AgentMetadata]:
        """
        List agents with optional filtering
        
        Args:
            agent_type: Filter by agent type
            tier: Filter by hierarchy tier
            
        Returns:
            List of matching AgentMetadata
        """
        if not self.registry:
            self.discover_agents()
        
        agents = list(self.registry.values())
        
        if agent_type:
            agents = [a for a in agents if a.type == agent_type]
        
        if tier:
            agents = [a for a in agents if a.tier == tier]
        
        return agents
    
    def listAgents(self, agent_type: Optional[str] = None, tier: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        List agents with optional filtering (camelCase wrapper for compatibility)
        
        This method provides a camelCase interface to maintain compatibility with
        the CLAUDE.md documentation while preserving the snake_case Python convention.
        
        Args:
            agent_type: Filter by agent type
            tier: Filter by hierarchy tier
            
        Returns:
            Dictionary of agent name -> agent metadata
        """
        agents = self.list_agents(agent_type=agent_type, tier=tier)
        
        # Convert to expected dictionary format
        return {
            agent.name: {
                'type': agent.type,
                'path': agent.path,
                'tier': agent.tier,
                'last_modified': agent.last_modified,
                'specializations': agent.specializations,
                'description': agent.description,
                'validated': agent.validated,
                'complexity_level': agent.complexity_level,
                'preferred_model': agent.preferred_model
            } for agent in agents
        }
    
    def get_agent_types(self) -> Set[str]:
        """
        Get all discovered agent types
        
        Returns:
            Set of agent types
        """
        if not self.registry:
            self.discover_agents()
        
        return {metadata.type for metadata in self.registry.values()}
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics and metrics
        
        Returns:
            Dictionary of registry statistics
        """
        if not self.registry:
            self.discover_agents()
        
        stats = {
            'total_agents': len(self.registry),
            'validated_agents': len([a for a in self.registry.values() if a.validated]),
            'failed_agents': len([a for a in self.registry.values() if not a.validated]),
            'agent_types': len(self.get_agent_types()),
            'agents_by_tier': {},
            'agents_by_type': {},
            'last_discovery': self.cache_manager.last_discovery_time,
            'discovery_paths': [str(p) for p in self.discovery_paths]
        }
        
        # Count by tier
        for metadata in self.registry.values():
            tier = metadata.tier
            stats['agents_by_tier'][tier] = stats['agents_by_tier'].get(tier, 0) + 1
        
        # Count by type
        for metadata in self.registry.values():
            agent_type = metadata.type
            stats['agents_by_type'][agent_type] = stats['agents_by_type'].get(agent_type, 0) + 1
        
        return stats
    
    def refresh_agent(self, agent_name: str) -> Optional[AgentMetadata]:
        """
        Refresh specific agent metadata
        
        Args:
            agent_name: Name of agent to refresh
            
        Returns:
            Updated AgentMetadata or None if not found
        """
        if agent_name not in self.registry:
            return None
        
        current_metadata = self.registry[agent_name]
        agent_file = Path(current_metadata.path)
        
        if not agent_file.exists():
            # Agent file removed
            del self.registry[agent_name]
            return None
        
        # Re-extract metadata
        updated_metadata = self.discovery.extract_agent_metadata(agent_file, current_metadata.tier)
        if updated_metadata:
            # Validate updated agent
            validated = self.validator.validate_agents({agent_name: updated_metadata})
            if agent_name in validated:
                self.registry[agent_name] = validated[agent_name]
                return validated[agent_name]
        
        return None
    
    def clear_cache(self) -> None:
        """Clear discovery cache and force refresh on next access"""
        self.registry.clear()
        self.cache_manager.clear_cache()
    
    # Internal method proxies for backward compatibility with tests
    def _determine_tier(self, path: Path) -> str:
        """Proxy to utils.determine_tier for backward compatibility"""
        return determine_tier(path)
    
    def _classify_agent_type(self, agent_name: str, agent_file: Path) -> str:
        """Proxy to classification.classify_agent_type for backward compatibility"""
        from .classification import classify_agent_type
        return classify_agent_type(agent_name, agent_file)
    
    def discover_agents_sync(self, force_refresh: bool = False) -> Dict[str, AgentMetadata]:
        """Alias for discover_agents for backward compatibility"""
        return self.discover_agents(force_refresh=force_refresh)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check on the AgentRegistry.
        
        Returns:
            Dictionary with health status information
        """
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            # Check 1: Discovery paths accessibility
            discovery_paths_status = []
            accessible_paths = 0
            for path in self.discovery_paths:
                path_status = {
                    'path': str(path),
                    'exists': path.exists(),
                    'readable': path.exists() and os.access(path, os.R_OK)
                }
                discovery_paths_status.append(path_status)
                if path_status['readable']:
                    accessible_paths += 1
            
            health_status['checks']['discovery_paths'] = {
                'total': len(self.discovery_paths),
                'accessible': accessible_paths,
                'details': discovery_paths_status
            }
            
            if accessible_paths == 0:
                health_status['errors'].append('No accessible discovery paths found')
                health_status['status'] = 'critical'
            elif accessible_paths < len(self.discovery_paths):
                health_status['warnings'].append(f'Only {accessible_paths}/{len(self.discovery_paths)} discovery paths are accessible')
                if health_status['status'] == 'healthy':
                    health_status['status'] = 'degraded'
            
            # Check 2: Cache service availability
            cache_health = self.cache_manager.test_cache_health()
            health_status['checks']['cache_service'] = cache_health
            
            if not cache_health.get('functional', False):
                health_status['warnings'].append('Cache service is not functioning properly')
                if health_status['status'] == 'healthy':
                    health_status['status'] = 'degraded'
            
            # Check 3: Model selector availability
            try:
                model_selector_status = self.model_selector is not None
                health_status['checks']['model_selector'] = {
                    'available': model_selector_status,
                    'type': type(self.model_selector).__name__ if model_selector_status else None
                }
                
                if not model_selector_status:
                    health_status['warnings'].append('Model selector not available')
                    
            except Exception as e:
                health_status['checks']['model_selector'] = {
                    'available': False,
                    'error': str(e)
                }
                health_status['warnings'].append(f'Model selector error: {e}')
            
            # Check 4: Registry state
            health_status['checks']['registry'] = {
                'loaded': bool(self.registry),
                'agent_count': len(self.registry),
                'last_discovery': self.cache_manager.last_discovery_time,
                'cache_valid': self.cache_manager.is_discovery_cache_valid()
            }
            
            # Check 5: Agent type coverage
            if self.registry:
                discovered_types = set(metadata.type for metadata in self.registry.values())
                core_coverage = len(self.core_agent_types.intersection(discovered_types))
                
                health_status['checks']['agent_coverage'] = {
                    'core_types_discovered': core_coverage,
                    'core_types_total': len(self.core_agent_types),
                    'specialized_types_discovered': len(discovered_types.intersection(self.specialized_agent_types)),
                    'total_types_discovered': len(discovered_types)
                }
                
                if core_coverage < len(self.core_agent_types):
                    missing_core = self.core_agent_types - discovered_types
                    health_status['warnings'].append(f'Missing core agent types: {", ".join(sorted(missing_core))}')
            else:
                health_status['checks']['agent_coverage'] = {
                    'message': 'No agents discovered yet'
                }
            
            # Check 6: System resources
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                
                health_status['checks']['system_resources'] = {
                    'memory_usage_mb': memory_info.rss / 1024 / 1024,
                    'available': True
                }
            except ImportError:
                health_status['checks']['system_resources'] = {
                    'available': False,
                    'note': 'psutil not installed'
                }
            except Exception as e:
                health_status['checks']['system_resources'] = {
                    'available': False,
                    'error': str(e)
                }
            
            # Overall health assessment
            if health_status['errors']:
                health_status['status'] = 'critical'
            elif len(health_status['warnings']) > 3:
                health_status['status'] = 'degraded'
            
            health_status['summary'] = {
                'status': health_status['status'],
                'error_count': len(health_status['errors']),
                'warning_count': len(health_status['warnings']),
                'checks_passed': sum(1 for check in health_status['checks'].values() 
                                   if isinstance(check, dict) and check.get('available', True))
            }
            
        except Exception as e:
            health_status['status'] = 'error'
            health_status['errors'].append(f'Health check failed: {str(e)}')
            health_status['exception'] = str(e)
        
        return health_status
    
    def get_agent_model_configuration(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """
        Get model configuration for a specific agent type.
        
        Args:
            agent_type: Type of the agent
            
        Returns:
            Model configuration dictionary or None if agent type not found
        """
        if not self.registry:
            self.discover_agents()
        
        # Find agent by type
        agent_metadata = None
        for metadata in self.registry.values():
            if metadata.type == agent_type:
                agent_metadata = metadata
                break
        
        if not agent_metadata:
            return None
        
        return {
            "agent_name": agent_metadata.name,
            "agent_type": agent_metadata.type,
            "preferred_model": agent_metadata.preferred_model,
            "model_config": agent_metadata.model_config,
            "complexity_level": agent_metadata.complexity_level,
            "capabilities": agent_metadata.capabilities,
            "specializations": agent_metadata.specializations
        }
    
    def get_model_usage_statistics(self) -> Dict[str, Any]:
        """
        Get statistics on model usage across all agents.
        
        Returns:
            Dictionary with model usage statistics
        """
        if not self.registry:
            self.discover_agents()
        
        stats = {
            "model_distribution": {},
            "agent_type_model_mapping": {},
            "complexity_level_distribution": {},
            "auto_selected_count": 0,
            "manually_configured_count": 0,
            "total_agents": len(self.registry)
        }
        
        for metadata in self.registry.values():
            # Count model distribution
            if metadata.preferred_model:
                stats["model_distribution"][metadata.preferred_model] = \
                    stats["model_distribution"].get(metadata.preferred_model, 0) + 1
            
            # Agent type to model mapping
            agent_type = metadata.type
            if agent_type not in stats["agent_type_model_mapping"]:
                stats["agent_type_model_mapping"][agent_type] = {}
            
            model = metadata.preferred_model or "none"
            stats["agent_type_model_mapping"][agent_type][model] = \
                stats["agent_type_model_mapping"][agent_type].get(model, 0) + 1
            
            # Complexity level distribution
            complexity = metadata.complexity_level
            if complexity not in stats["complexity_level_distribution"]:
                stats["complexity_level_distribution"][complexity] = {}
            
            stats["complexity_level_distribution"][complexity][model] = \
                stats["complexity_level_distribution"][complexity].get(model, 0) + 1
            
            # Auto vs manual selection
            if metadata.model_config.get("auto_selected"):
                stats["auto_selected_count"] += 1
            elif metadata.model_config.get("explicit") or metadata.model_config.get("manually_updated"):
                stats["manually_configured_count"] += 1
        
        return stats


# Re-export key components for backward compatibility
__all__ = ['AgentRegistry', 'AgentMetadata']