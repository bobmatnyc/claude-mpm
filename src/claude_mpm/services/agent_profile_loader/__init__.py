"""
Agent Profile Loader Service
===========================

Comprehensive agent profile loading service with enhanced prompt integration.
Implements three-tier hierarchy precedence and improved prompt system integration.

Key Features:
- Three-tier hierarchy precedence (Project → User → System)
- Improved prompt integration with training system
- SharedPromptCache integration for performance optimization
- AgentRegistry integration for enhanced discovery
- Training system integration for prompt improvement
- Task Tool subprocess creation enhancement
- Profile validation and error handling

Framework Version: 014
Implementation: 2025-07-15
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

from ...core.base_service import BaseService
from ...core.config import Config
from .models import ProfileTier, ProfileStatus, AgentProfile, ImprovedPrompt
from .profile_manager import ProfileManager
from .improved_prompts import ImprovedPromptManager
from .task_integration import TaskIntegration
from .service_integrations import ServiceIntegrations
from .profile_discovery import ProfileDiscovery
from .metrics_validator import MetricsValidator

logger = logging.getLogger(__name__)


class AgentProfileLoader(BaseService):
    """
    Comprehensive agent profile loading service with enhanced prompt integration.
    
    Features:
    - Three-tier hierarchy precedence (Project → User → System)
    - Improved prompt integration with training system
    - SharedPromptCache integration for performance optimization
    - AgentRegistry integration for enhanced discovery
    - Profile validation and error handling
    - Task Tool subprocess creation enhancement
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the agent profile loader."""
        super().__init__(name="agent_profile_loader", config=config)
        
        # Core configuration
        self.working_directory = Path(os.getcwd())
        self.framework_path = self._detect_framework_path()
        self.user_home = Path.home()
        
        # Components
        self.profile_manager = ProfileManager(
            self.working_directory,
            self.framework_path,
            self.user_home
        )
        self.task_integration = TaskIntegration()
        self.service_integrations = ServiceIntegrations(config)
        self.profile_discovery = ProfileDiscovery(
            self.profile_manager.tier_paths,
            None  # Will be set after service initialization
        )
        self.metrics_validator = MetricsValidator(self.profile_manager.tier_paths)
        
        logger.info(f"AgentProfileLoader initialized successfully")
        logger.info(f"  Working directory: {self.working_directory}")
        logger.info(f"  Framework path: {self.framework_path}")
    
    async def _initialize(self) -> None:
        """Initialize the service and its integrations."""
        logger.info("Initializing AgentProfileLoader service...")
        
        # Initialize service integrations
        await self.service_integrations.initialize()
        
        # Update profile discovery with agent registry
        self.profile_discovery.agent_registry = self.service_integrations.agent_registry
        
        logger.info("AgentProfileLoader service initialized successfully")
    
    async def _cleanup(self) -> None:
        """Cleanup service resources."""
        logger.info("Cleaning up AgentProfileLoader service...")
        
        # Clear caches
        self.profile_manager.invalidate_cache()
        
        # Cleanup service integrations
        await self.service_integrations.cleanup()
        
        logger.info("AgentProfileLoader service cleaned up")
    
    def _detect_framework_path(self) -> Path:
        """Detect framework path from environment or deployment structure."""
        # Try environment variable first
        if framework_path := os.getenv('CLAUDE_PM_FRAMEWORK_PATH'):
            return Path(framework_path)
            
        # Try deployment directory
        if deployment_dir := os.getenv('CLAUDE_PM_DEPLOYMENT_DIR'):
            return Path(deployment_dir)
            
        # Try to find framework directory with agent-roles
        current_dir = Path(__file__).parent.parent.parent.parent  # Go up to project root
        framework_dir = current_dir / 'framework'
        if framework_dir.exists() and (framework_dir / 'agent-roles').exists():
            return framework_dir
            
        # Try relative to current module
        current_dir = Path(__file__).parent.parent.parent
        if (current_dir / 'agent-roles').exists():
            return current_dir
        elif (current_dir / 'agents').exists():
            return current_dir
            
        # Fallback to working directory
        return self.working_directory
    
    async def load_agent_profile(self, agent_name: str, force_refresh: bool = False) -> Optional[AgentProfile]:
        """
        Load agent profile following three-tier hierarchy with improved prompt integration.
        
        Args:
            agent_name: Name of agent profile to load
            force_refresh: Force cache refresh
            
        Returns:
            AgentProfile if found, None otherwise
        """
        return await self.profile_manager.load_agent_profile(agent_name=agent_name, force_refresh=force_refresh)
    
    async def save_improved_prompt(self, improved_prompt: ImprovedPrompt) -> bool:
        """Save improved prompt to training system."""
        return await self.profile_manager.improved_prompt_manager.save_improved_prompt(improved_prompt)
    
    async def deploy_improved_prompt(self, agent_name: str, training_session_id: str) -> Dict[str, Any]:
        """Deploy improved prompt to agent profile."""
        try:
            # Get improved prompt
            improved_prompt_manager = self.profile_manager.improved_prompt_manager
            improved_prompt = improved_prompt_manager.improved_prompts_cache.get(agent_name)
            
            if not improved_prompt or improved_prompt.training_session_id != training_session_id:
                return {
                    'success': False,
                    'error': 'Improved prompt not found or session mismatch'
                }
            
            # Mark as deployment ready
            improved_prompt_manager.mark_deployment_ready(agent_name, training_session_id)
            
            # Save updated prompt
            await improved_prompt_manager.save_improved_prompt(improved_prompt)
            
            # Clear profile cache to force reload
            self.profile_manager.invalidate_cache(agent_name)
            
            # Integration with training system
            deployment_result = await self.service_integrations.deploy_trained_agent(
                agent_name, training_session_id
            )
            
            return {
                'success': True,
                'agent_name': agent_name,
                'training_session_id': training_session_id,
                'improvement_score': improved_prompt.improvement_score,
                'deployment_ready': True,
                'training_deployment': deployment_result.get('success', False)
            }
            
        except Exception as e:
            logger.error(f"Error deploying improved prompt for {agent_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def build_enhanced_task_prompt(self, agent_name: str, task_context: Dict[str, Any]) -> str:
        """Build enhanced Task Tool prompt with improved prompt integration."""
        # Load agent profile
        profile = await self.load_agent_profile(agent_name)
        if not profile:
            raise ValueError(f"No profile found for agent: {agent_name}")
        
        # Build enhanced prompt using task integration
        return await self.task_integration.build_enhanced_task_prompt(profile, task_context)
    
    async def get_profile_hierarchy(self, agent_name: str) -> List[AgentProfile]:
        """Get all available profiles for an agent across all tiers."""
        return await self.profile_manager.get_profile_hierarchy(agent_name)
    
    async def list_available_agents(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all available agents with enhanced metadata."""
        agents = await self.profile_discovery.list_available_agents()
        
        # Enhance with profile information if registry was used
        if self.service_integrations.agent_registry:
            for tier_agents in agents.values():
                for agent_info in tier_agents:
                    try:
                        profile = await self.load_agent_profile(agent_info['name'])
                        if profile:
                            agent_info['has_improved_prompt'] = profile.has_improved_prompt
                            agent_info['status'] = profile.status.value
                            agent_info['capabilities'] = profile.capabilities
                    except Exception:
                        pass  # Keep default values
        
        return agents
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the profile loader."""
        return self.metrics_validator.collect_performance_metrics(
            self.profile_manager,
            self.service_integrations
        )
    
    async def validate_profile_integration(self) -> Dict[str, Any]:
        """Validate profile integration with framework systems."""
        return await self.metrics_validator.validate_profile_integration(
            self.service_integrations
        )
    
    def invalidate_cache(self, agent_name: Optional[str] = None) -> None:
        """Invalidate profile cache."""
        self.profile_manager.invalidate_cache(agent_name)
        if self.service_integrations.shared_cache and agent_name:
            self.service_integrations.shared_cache.invalidate(f"agent_profile:{agent_name}:*")
        elif self.service_integrations.shared_cache:
            self.service_integrations.shared_cache.invalidate("agent_profile:*")


# Factory function
def create_agent_profile_loader(config: Optional[Config] = None) -> AgentProfileLoader:
    """Create an AgentProfileLoader instance."""
    return AgentProfileLoader(config)


# Integration with existing systems
async def integrate_with_task_tool(agent_name: str, task_context: Dict[str, Any]) -> str:
    """Integration function for Task Tool subprocess creation."""
    loader = create_agent_profile_loader()
    await loader.start()
    
    try:
        enhanced_prompt = await loader.build_enhanced_task_prompt(agent_name, task_context)
        return enhanced_prompt
    finally:
        await loader.stop()


# Export main classes and functions
__all__ = [
    'AgentProfileLoader',
    'AgentProfile',
    'ProfileTier',
    'ProfileStatus',
    'ImprovedPrompt',
    'create_agent_profile_loader',
    'integrate_with_task_tool'
]


if __name__ == "__main__":
    # Demo and testing
    async def demo():
        """Demonstrate AgentProfileLoader usage."""
        print("🚀 AgentProfileLoader Demo")
        print("=" * 50)
        
        # Initialize loader
        loader = create_agent_profile_loader()
        await loader.start()
        
        try:
            # Load a profile
            profile = await loader.load_agent_profile("engineer")
            if profile:
                print(f"\n📋 Loaded Profile: {profile.name}")
                print(f"  Role: {profile.role}")
                print(f"  Tier: {profile.tier.value}")
                print(f"  Has Improved Prompt: {profile.has_improved_prompt}")
                print(f"  Status: {profile.status.value}")
                print(f"  Capabilities: {len(profile.capabilities)}")
            
            # List available agents
            agents = await loader.list_available_agents()
            print(f"\n🤖 Available Agents:")
            for tier, tier_agents in agents.items():
                print(f"  {tier.upper()}: {len(tier_agents)} agents")
            
            # Get performance metrics
            metrics = await loader.get_performance_metrics()
            print(f"\n📊 Performance Metrics:")
            for key, value in metrics.items():
                print(f"  {key}: {value}")
            
            # Validate integration
            validation = await loader.validate_profile_integration()
            print(f"\n✅ Integration Validation: {'Valid' if validation['valid'] else 'Invalid'}")
            print(f"  Issues: {len(validation['issues'])}")
            print(f"  Warnings: {len(validation['warnings'])}")
            
        finally:
            await loader.stop()
            print("\n✅ Demo completed")
    
    # Run demo
    asyncio.run(demo())