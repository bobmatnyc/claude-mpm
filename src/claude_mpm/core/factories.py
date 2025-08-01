"""
Factory classes for creating complex dependencies in Claude MPM.

Provides factory patterns for services that require complex initialization
or have multiple configuration options.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar

from .container import DIContainer
from .logger import get_logger
from .config import Config
from ..services.agent_deployment import AgentDeploymentService
from ..orchestration.factory import OrchestratorFactory
from ..orchestration.base import BaseOrchestrator

logger = get_logger(__name__)

T = TypeVar('T')


class ServiceFactory(ABC):
    """Base factory for creating services."""
    
    @abstractmethod
    def create(self, container: DIContainer, **kwargs) -> Any:
        """Create a service instance."""
        pass




class OrchestratorFactoryWrapper(ServiceFactory):
    """Factory wrapper for creating orchestrator instances."""
    
    def __init__(self):
        """Initialize the factory wrapper."""
        self._factory = OrchestratorFactory()
        
    def create(
        self,
        container: DIContainer,
        orchestrator_type: Optional[str] = None,
        **kwargs
    ) -> BaseOrchestrator:
        """
        Create an orchestrator instance.
        
        Args:
            container: DI container
            orchestrator_type: Type of orchestrator to create
            **kwargs: Additional arguments for orchestrator
            
        Returns:
            Orchestrator instance
        """
        config = container.resolve(Config)
        
        # Get orchestrator type from config if not provided
        if orchestrator_type is None:
            orchestrator_type = config.get('orchestrator.type', 'subprocess')
            
        # Get orchestrator config
        orch_config = config.get(f'orchestrator.{orchestrator_type}', {})
        
        # Merge with provided kwargs
        orch_config.update(kwargs)
        
        # No hook manager injection needed - Claude Code hooks are external
            
        # Create orchestrator
        orchestrator = self._factory.create_orchestrator(
            orchestrator_type,
            **orch_config
        )
        
        logger.info(f"Created {orchestrator_type} orchestrator")
        return orchestrator


class AgentServiceFactory(ServiceFactory):
    """Factory for creating agent-related services."""
    
    def create(
        self,
        container: DIContainer,
        framework_dir: Optional[Path] = None,
        project_dir: Optional[Path] = None
    ) -> AgentDeploymentService:
        """
        Create an agent deployment service.
        
        Args:
            container: DI container
            framework_dir: Framework directory path
            project_dir: Project directory path
            
        Returns:
            Agent deployment service instance
        """
        config = container.resolve(Config)
        
        # Get directories from config if not provided
        if framework_dir is None:
            framework_dir = Path(config.get('framework.dir', 'framework'))
            
        if project_dir is None:
            project_dir = Path(config.get('project.dir', '.'))
            
        # Create service with dependencies
        service = AgentDeploymentService()
        
        # Inject any required dependencies
        if hasattr(service, 'set_directories'):
            service.set_directories(framework_dir, project_dir)
            
        logger.info("Created agent deployment service")
        return service


class SessionManagerFactory(ServiceFactory):
    """Factory for creating session managers."""
    
    def create(
        self,
        container: DIContainer,
        session_type: str = "standard",
        **kwargs
    ) -> Any:
        """
        Create a session manager instance.
        
        Args:
            container: DI container
            session_type: Type of session manager
            **kwargs: Additional configuration
            
        Returns:
            Session manager instance
        """
        config = container.resolve(Config)
        
        if session_type == "agent":
            from ..core.agent_session_manager import AgentSessionManager
            
            session_dir = kwargs.get('session_dir') or Path(config.get('session.dir', '.claude-mpm/sessions'))
            max_sessions = kwargs.get('max_sessions_per_agent', config.get('session.max_per_agent', 3))
            
            return AgentSessionManager(
                session_dir=session_dir,
                max_sessions_per_agent=max_sessions
            )
        else:
            from ..core.session_manager import SessionManager
            
            session_dir = kwargs.get('session_dir') or Path(config.get('session.dir', '.claude-mpm/sessions'))
            
            return SessionManager(session_dir=session_dir)


class ConfigurationFactory(ServiceFactory):
    """Factory for creating configuration instances."""
    
    def create(
        self,
        container: DIContainer,
        config_data: Optional[Dict[str, Any]] = None,
        config_path: Optional[Path] = None,
        env_prefix: str = "CLAUDE_MPM"
    ) -> Config:
        """
        Create a configuration instance.
        
        Args:
            container: DI container
            config_data: Initial configuration data
            config_path: Path to configuration file
            env_prefix: Environment variable prefix
            
        Returns:
            Configuration instance
        """
        # Load from multiple sources
        config = Config(config_data or {}, config_path)
        
        # Load environment variables
        import os
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                # Convert CLAUDE_MPM_FOO_BAR to foo.bar
                config_key = key[len(env_prefix)+1:].lower().replace('_', '.')
                config.set(config_key, value)
                
        logger.info("Created configuration instance")
        return config


# Factory registry for easy access
class FactoryRegistry:
    """Registry for all service factories."""
    
    def __init__(self):
        """Initialize factory registry."""
        self._factories: Dict[str, ServiceFactory] = {
            'orchestrator': OrchestratorFactoryWrapper(),
            'agent_service': AgentServiceFactory(),
            'session_manager': SessionManagerFactory(),
            'configuration': ConfigurationFactory(),
        }
        
    def get_factory(self, name: str) -> ServiceFactory:
        """Get a factory by name."""
        if name not in self._factories:
            raise KeyError(f"Factory '{name}' not registered")
        return self._factories[name]
        
    def register_factory(self, name: str, factory: ServiceFactory) -> None:
        """Register a new factory."""
        self._factories[name] = factory
        logger.debug(f"Registered factory: {name}")
        
    def create(self, factory_name: str, container: DIContainer, **kwargs) -> Any:
        """Create a service using a named factory."""
        factory = self.get_factory(factory_name)
        return factory.create(container, **kwargs)


# Global factory registry
_factory_registry = FactoryRegistry()


def get_factory_registry() -> FactoryRegistry:
    """Get the global factory registry."""
    return _factory_registry