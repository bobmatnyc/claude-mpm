"""
Agent Registry Cache Management
Handles caching functionality for agent registry

Created: 2025-07-19
Purpose: Cache management for agent discovery and metadata
"""

import time
import logging
from typing import Dict, Any, Optional

from ..shared_prompt_cache import SharedPromptCache
from .metadata import AgentMetadata

logger = logging.getLogger(__name__)


class AgentRegistryCache:
    """Manages caching for agent registry operations"""
    
    def __init__(self, cache_service: Optional[SharedPromptCache] = None):
        self.cache_service = cache_service or SharedPromptCache()
        self.last_discovery_time: Optional[float] = None
        self.discovery_cache_ttl = 300  # 5 minutes
    
    def is_discovery_cache_valid(self) -> bool:
        """Check if discovery cache is still valid"""
        if self.last_discovery_time is None:
            return False
        return (time.time() - self.last_discovery_time) < self.discovery_cache_ttl
    
    def get_cached_discovery(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get cached discovery results if valid"""
        if not self.is_discovery_cache_valid():
            return None
        
        cache_hit = self.cache_service.get("agent_registry_discovery")
        if cache_hit:
            logger.debug("Using cached agent discovery results")
            return cache_hit
        return None
    
    def cache_discovery_results(self, agents: Dict[str, AgentMetadata]) -> None:
        """Cache discovery results"""
        # Convert to dictionary format for caching
        from dataclasses import asdict
        cache_data = {name: asdict(metadata) for name, metadata in agents.items()}
        self.cache_service.set("agent_registry_discovery", cache_data, ttl=self.discovery_cache_ttl)
        self.last_discovery_time = time.time()
    
    def clear_cache(self) -> None:
        """Clear discovery cache and force refresh on next access"""
        self.last_discovery_time = None
        self.cache_service.invalidate("agent_registry_discovery")
    
    def test_cache_health(self) -> Dict[str, Any]:
        """Test cache service health"""
        try:
            cache_test_key = 'agent_registry_health_check_test'
            self.cache_service.set(cache_test_key, {'test': True}, ttl=1)
            cache_result = self.cache_service.get(cache_test_key)
            cache_healthy = cache_result is not None and cache_result.get('test') == True
            
            return {
                'available': True,
                'functional': cache_healthy,
                'type': type(self.cache_service).__name__
            }
        except Exception as e:
            return {
                'available': False,
                'error': str(e)
            }