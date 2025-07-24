#!/usr/bin/env python3
"""
Cache integration for agent modification tracking.

This module handles cache invalidation when agents are modified to ensure
the system always uses up-to-date agent information.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from claude_mpm.services.shared_prompt_cache import SharedPromptCache


class CacheIntegration:
    """Integration with SharedPromptCache for invalidation on modifications."""
    
    def __init__(self, shared_cache: Optional[SharedPromptCache] = None):
        self.logger = logging.getLogger(__name__)
        self.shared_cache = shared_cache or SharedPromptCache.get_instance()
    
    async def invalidate_agent_cache(self, agent_name: str) -> None:
        """Invalidate cache entries for modified agent."""
        if not self.shared_cache:
            return
        
        try:
            # Standard cache invalidation patterns
            patterns = [
                f"agent_profile:{agent_name}:*",
                f"task_prompt:{agent_name}:*",
                f"agent_registry_discovery",
                f"agent_profile_enhanced:{agent_name}:*"
            ]
            
            for pattern in patterns:
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda p=pattern: self.shared_cache.invalidate(p)
                )
            
            self.logger.debug(f"Invalidated cache entries for agent '{agent_name}'")
            
        except Exception as e:
            self.logger.warning(f"Failed to invalidate cache for agent '{agent_name}': {e}")
    
    async def invalidate_specialized_cache(self, agent_name: str, metadata: Dict[str, Any]) -> None:
        """Invalidate specialized agent cache entries."""
        if not self.shared_cache:
            return
        
        try:
            # Standard cache invalidation patterns
            patterns = [
                f"agent_profile:{agent_name}:*",
                f"task_prompt:{agent_name}:*",
                f"agent_registry_discovery",
                f"agent_profile_enhanced:{agent_name}:*"
            ]
            
            # Add specialized cache patterns
            specialized_type = metadata.get('specialized_type')
            if specialized_type:
                patterns.extend([
                    f"specialized_agents:{specialized_type}:*",
                    f"agent_type_discovery:{specialized_type}:*"
                ])
            
            # Framework-specific cache patterns
            frameworks = metadata.get('frameworks', [])
            for framework in frameworks:
                patterns.append(f"framework_agents:{framework}:*")
            
            # Domain-specific cache patterns
            domains = metadata.get('domains', [])
            for domain in domains:
                patterns.append(f"domain_agents:{domain}:*")
            
            # Hybrid agent cache patterns
            if metadata.get('is_hybrid'):
                patterns.append(f"hybrid_agents:*")
                hybrid_types = metadata.get('hybrid_types', [])
                for hybrid_type in hybrid_types:
                    patterns.append(f"hybrid_type:{hybrid_type}:*")
            
            # Invalidate all patterns
            for pattern in patterns:
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda p=pattern: self.shared_cache.invalidate(p)
                )
            
            self.logger.debug(f"Invalidated {len(patterns)} specialized cache patterns for agent '{agent_name}'")
            
        except Exception as e:
            self.logger.warning(f"Failed to invalidate specialized cache for agent '{agent_name}': {e}")
    
    async def invalidate_hierarchy_cache(self, tier: str) -> None:
        """Invalidate cache for an entire tier in the hierarchy."""
        if not self.shared_cache:
            return
        
        try:
            patterns = [
                f"agent_hierarchy:{tier}:*",
                f"tier_agents:{tier}:*",
                "agent_registry_discovery"
            ]
            
            for pattern in patterns:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda p=pattern: self.shared_cache.invalidate(p)
                )
            
            self.logger.debug(f"Invalidated hierarchy cache for tier '{tier}'")
            
        except Exception as e:
            self.logger.warning(f"Failed to invalidate hierarchy cache for tier '{tier}': {e}")
    
    async def batch_invalidate(self, agent_names: List[str]) -> None:
        """Invalidate cache for multiple agents in batch."""
        if not self.shared_cache:
            return
        
        try:
            patterns = []
            
            for agent_name in agent_names:
                patterns.extend([
                    f"agent_profile:{agent_name}:*",
                    f"task_prompt:{agent_name}:*",
                    f"agent_profile_enhanced:{agent_name}:*"
                ])
            
            # Add common patterns once
            patterns.append("agent_registry_discovery")
            
            # Execute batch invalidation
            for pattern in patterns:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda p=pattern: self.shared_cache.invalidate(p)
                )
            
            self.logger.debug(f"Batch invalidated cache for {len(agent_names)} agents")
            
        except Exception as e:
            self.logger.warning(f"Failed to batch invalidate cache: {e}")