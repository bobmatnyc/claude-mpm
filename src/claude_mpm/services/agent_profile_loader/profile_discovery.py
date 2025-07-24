"""
Agent discovery and listing functionality.
"""

import logging
from typing import Dict, List, Any

from .models import ProfileTier, AgentProfile
from .profile_parser import ProfileParser

logger = logging.getLogger(__name__)


class ProfileDiscovery:
    """Handles agent profile discovery and listing."""
    
    def __init__(self, tier_paths: Dict[ProfileTier, dict], agent_registry=None):
        """Initialize profile discovery."""
        self.tier_paths = tier_paths
        self.agent_registry = agent_registry
        self.parser = ProfileParser()
    
    async def list_available_agents(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all available agents with enhanced metadata."""
        agents = {}
        
        # Use AgentRegistry if available
        if self.agent_registry:
            try:
                registry_agents = await self.agent_registry.list_agents()
                
                for agent_metadata in registry_agents:
                    tier = agent_metadata.tier
                    if tier not in agents:
                        agents[tier] = []
                    
                    agent_info = {
                        'name': agent_metadata.name,
                        'type': agent_metadata.type,
                        'tier': tier,
                        'path': agent_metadata.path,
                        'validated': agent_metadata.validated,
                        'has_improved_prompt': False,  # Will be populated by loader
                        'status': 'unknown',
                        'capabilities': []
                    }
                    
                    agents[tier].append(agent_info)
                
            except Exception as e:
                logger.error(f"Error using AgentRegistry: {e}")
        
        # Fallback to direct file scanning
        if not agents:
            for tier, tier_path in self.tier_paths.items():
                if not tier_path.exists():
                    continue
                
                tier_agents = []
                for agent_file in tier_path.glob('*.md'):
                    try:
                        profile = await self.parser.parse_profile_file(agent_file, tier)
                        if profile:
                            tier_agents.append({
                                'name': profile.name,
                                'type': 'unknown',
                                'tier': tier.value,
                                'path': str(profile.path),
                                'validated': True,
                                'has_improved_prompt': profile.has_improved_prompt,
                                'status': profile.status.value,
                                'capabilities': profile.capabilities
                            })
                    except Exception as e:
                        logger.error(f"Error parsing {agent_file}: {e}")
                        continue
                
                agents[tier.value] = tier_agents
        
        return agents
    
    async def discover_agents_by_capability(self, capability: str) -> List[AgentProfile]:
        """Discover agents that have a specific capability."""
        matching_agents = []
        
        for tier, tier_path in self.tier_paths.items():
            if not tier_path.exists():
                continue
                
            for agent_file in tier_path.glob('*.md'):
                try:
                    profile = await self.parser.parse_profile_file(agent_file, tier)
                    if profile and any(capability.lower() in cap.lower() for cap in profile.capabilities):
                        matching_agents.append(profile)
                except Exception as e:
                    logger.error(f"Error parsing {agent_file}: {e}")
                    continue
        
        return matching_agents
    
    async def get_agent_count_by_tier(self) -> Dict[str, int]:
        """Get count of agents in each tier."""
        counts = {}
        
        for tier, tier_path in self.tier_paths.items():
            if tier_path.exists():
                agent_files = list(tier_path.glob('*.md'))
                counts[tier.value] = len(agent_files)
            else:
                counts[tier.value] = 0
        
        return counts