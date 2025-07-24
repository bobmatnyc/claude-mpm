"""
Core profile loading and caching functionality.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import ProfileTier, ProfileStatus, AgentProfile
from .profile_parser import ProfileParser
from .improved_prompts import ImprovedPromptManager
from ..shared_prompt_cache import cache_result

logger = logging.getLogger(__name__)


class ProfileManager:
    """Manages agent profile loading and caching."""
    
    def __init__(self, working_directory: Path, framework_path: Path, user_home: Path):
        """Initialize the profile manager."""
        self.working_directory = working_directory
        self.framework_path = framework_path
        self.user_home = user_home
        
        # Profile storage
        self.profile_cache: Dict[str, AgentProfile] = {}
        self.tier_paths: Dict[ProfileTier, Path] = {}
        
        # Components
        self.parser = ProfileParser()
        self.improved_prompt_manager = ImprovedPromptManager(user_home)
        
        # Performance metrics
        self.performance_metrics = {
            'profiles_loaded': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'improved_prompts_loaded': 0
        }
        
        # Initialize paths
        self._initialize_tier_paths()
    
    def _initialize_tier_paths(self) -> None:
        """Initialize paths for each tier with proper precedence."""
        # Project tier - current directory (highest precedence)
        project_path = self.working_directory / '.claude-pm' / 'agents' / 'project-specific'
        self.tier_paths[ProfileTier.PROJECT] = project_path
        
        # User tier - user home directory (for trained/customized agents)
        user_path = self.user_home / '.claude-pm' / 'agents' / 'user-defined'
        self.tier_paths[ProfileTier.USER] = user_path
        
        # System tier - framework agent-roles directory (core system agents)
        system_path = self.framework_path / 'agent-roles'
        if not system_path.exists():
            raise FileNotFoundError(
                f"System agents directory not found at {system_path}. "
                f"Framework path: {self.framework_path}"
            )
        self.tier_paths[ProfileTier.SYSTEM] = system_path
        
        # Create project and user directories if they don't exist
        project_path.mkdir(parents=True, exist_ok=True)
        user_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized tier paths: {len(self.tier_paths)} tiers")
        for tier, path in self.tier_paths.items():
            exists = "✓" if path.exists() else "✗"
            logger.info(f"  {tier.value}: {path} {exists}")
    
    async def load_agent_profile(self, agent_name: str, force_refresh: bool = False) -> Optional[AgentProfile]:
        """
        Load agent profile following three-tier hierarchy with improved prompt integration.
        
        Args:
            agent_name: Name of agent profile to load
            force_refresh: Force cache refresh
            
        Returns:
            AgentProfile if found, None otherwise
        """
        try:
            # Check local cache first (if not forcing refresh)
            if not force_refresh and agent_name in self.profile_cache:
                self.performance_metrics['cache_hits'] += 1
                return self.profile_cache[agent_name]
            
            self.performance_metrics['cache_misses'] += 1
            
            # Search through hierarchy (Project → User → System)
            for tier in [ProfileTier.PROJECT, ProfileTier.USER, ProfileTier.SYSTEM]:
                profile = await self._load_profile_from_tier(agent_name, tier)
                if profile:
                    # Check for improved prompt
                    await self._apply_improved_prompt(profile)
                    
                    # Cache the profile
                    self.profile_cache[agent_name] = profile
                    
                    # Update performance metrics
                    self.performance_metrics['profiles_loaded'] += 1
                    
                    logger.debug(f"Loaded {agent_name} profile from {tier.value} tier")
                    return profile
            
            # No profile found - return None as per the Optional[AgentProfile] type hint
            checked_paths = []
            for tier in [ProfileTier.PROJECT, ProfileTier.USER, ProfileTier.SYSTEM]:
                tier_path = self.tier_paths[tier]
                checked_paths.append(f"{tier.value}: {tier_path}")
            
            logger.warning(
                f"Agent profile '{agent_name}' not found in any tier. "
                f"Searched paths: {', '.join(checked_paths)}"
            )
            return None
            
        except Exception as e:
            logger.error(f"Error loading profile for {agent_name}: {e}")
            raise RuntimeError(f"Failed to load agent profile '{agent_name}': {e}")
    
    async def _load_profile_from_tier(self, agent_name: str, tier: ProfileTier) -> Optional[AgentProfile]:
        """Load profile from specific tier."""
        tier_path = self.tier_paths[tier]
        if not tier_path.exists():
            return None
        
        # Try different file naming conventions
        profile_files = [
            f"{agent_name}.md",
            f"{agent_name}-agent.md",
            f"{agent_name}_agent.md", 
            f"{agent_name}-profile.md",
            f"{agent_name.title()}.md",
            f"{agent_name}.py",
            f"{agent_name}_agent.py"
        ]
        
        for filename in profile_files:
            profile_path = tier_path / filename
            if profile_path.exists():
                return await self.parser.parse_profile_file(profile_path, tier)
        
        return None
    
    async def _apply_improved_prompt(self, profile: AgentProfile) -> None:
        """Apply improved prompt from training system if available."""
        improved_prompt = await self.improved_prompt_manager.get_improved_prompt(profile.name)
        
        if improved_prompt and improved_prompt.deployment_ready:
            profile.improved_prompt = improved_prompt
            profile.status = ProfileStatus.IMPROVED
            profile.prompt_version = f"{profile.prompt_version}-improved"
            
            logger.debug(f"Applied improved prompt for {profile.name} "
                       f"(improvement score: {improved_prompt.improvement_score})")
            
            self.performance_metrics['improved_prompts_loaded'] += 1
    
    async def get_profile_hierarchy(self, agent_name: str) -> List[AgentProfile]:
        """Get all available profiles for an agent across all tiers."""
        profiles = []
        
        for tier in [ProfileTier.PROJECT, ProfileTier.USER, ProfileTier.SYSTEM]:
            profile = await self._load_profile_from_tier(agent_name, tier)
            if profile:
                profiles.append(profile)
        
        return profiles
    
    def invalidate_cache(self, agent_name: Optional[str] = None) -> None:
        """Invalidate profile cache."""
        if agent_name:
            self.profile_cache.pop(agent_name, None)
        else:
            self.profile_cache.clear()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        metrics = self.performance_metrics.copy()
        metrics.update({
            'cached_profiles': len(self.profile_cache),
            'tiers_configured': len(self.tier_paths)
        })
        return metrics