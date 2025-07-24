"""
External service integrations for agent profile loader.
"""

import logging
from typing import Optional, Dict, Any

from ..shared_prompt_cache import SharedPromptCache
from ..agent_registry import AgentRegistry
from ..agent_training_integration import AgentTrainingIntegration
from ...core.config import Config

# Note: PromptTemplateManager import removed as it doesn't exist in the services directory

logger = logging.getLogger(__name__)


class ServiceIntegrations:
    """Manages integrations with external services."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize service integrations."""
        self.config = config
        self.shared_cache: Optional[SharedPromptCache] = None
        self.agent_registry: Optional[AgentRegistry] = None
        self.training_integration: Optional[AgentTrainingIntegration] = None
    
    async def initialize(self) -> None:
        """Initialize all service integrations."""
        # Initialize SharedPromptCache
        try:
            self.shared_cache = SharedPromptCache.get_instance({
                "max_size": 1000,
                "max_memory_mb": 100,
                "default_ttl": 1800,
                "enable_metrics": True
            })
            logger.info("SharedPromptCache integration enabled")
        except Exception as e:
            logger.warning(f"Failed to initialize SharedPromptCache: {e}")
            self.shared_cache = None
        
        # Initialize AgentRegistry
        try:
            self.agent_registry = AgentRegistry(cache_service=self.shared_cache)
            await self.agent_registry.discover_agents()
            logger.info("AgentRegistry integration enabled")
        except Exception as e:
            logger.warning(f"Failed to initialize AgentRegistry: {e}")
            self.agent_registry = None
        
        
        # Initialize TrainingIntegration
        try:
            self.training_integration = AgentTrainingIntegration(self.config)
            logger.info("Training integration enabled")
        except Exception as e:
            logger.warning(f"Failed to initialize training integration: {e}")
            self.training_integration = None
    
    async def cleanup(self) -> None:
        """Cleanup service integrations."""
        if self.training_integration:
            await self.training_integration.stop()
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache metrics from SharedPromptCache."""
        if self.shared_cache:
            return self.shared_cache.get_metrics()
        return {}
    
    async def deploy_trained_agent(self, agent_type: str, training_session_id: str) -> Dict[str, Any]:
        """Deploy trained agent through training integration."""
        if self.training_integration:
            return await self.training_integration.deploy_trained_agent(
                agent_type=agent_type,
                training_session_id=training_session_id,
                deployment_tier='user'
            )
        return {'success': False, 'error': 'Training integration not available'}
    
    def is_cache_enabled(self) -> bool:
        """Check if cache is enabled."""
        return self.shared_cache is not None
    
    def is_registry_enabled(self) -> bool:
        """Check if agent registry is enabled."""
        return self.agent_registry is not None
    
    def is_training_enabled(self) -> bool:
        """Check if training integration is enabled."""
        return self.training_integration is not None