"""Agent services module - hierarchical organization of agent-related services."""

# Auto-configuration exports
from .auto_config_manager import AutoConfigManagerService

# Registry exports
# Deployment exports
from .deployment.agent_deployment import AgentDeploymentService
from .deployment.agent_lifecycle_manager import (
    AgentLifecycleManager,
    AgentLifecycleRecord,
    LifecycleOperation,
    LifecycleOperationResult,
    LifecycleState,
)
from .deployment.agent_versioning import AgentVersionManager
from .loading.agent_profile_loader import AgentProfileLoader
from .loading.base_agent_manager import BaseAgentManager

# Loading exports
from .loading.framework_agent_loader import FrameworkAgentLoader
from .management.agent_capabilities_generator import AgentCapabilitiesGenerator

# Management exports
from .management.agent_management_service import AgentManager

# Memory exports
from .memory.agent_memory_manager import AgentMemoryManager, get_memory_manager
from .memory.agent_persistence_service import (
    AgentPersistenceService,
    PersistenceOperation,
    PersistenceRecord,
    PersistenceStrategy,
)
from .observers import (
    CompositeObserver,
    ConsoleProgressObserver,
    IDeploymentObserver,
    NullObserver,
)

# Recommender exports
from .recommender import AgentRecommenderService
from .registry import AgentMetadata, AgentRegistry, AgentTier, AgentType
from .registry.deployed_agent_discovery import DeployedAgentDiscovery
from .registry.modification_tracker import (
    AgentModification,
    AgentModificationTracker,
    ModificationHistory,
    ModificationTier,
    ModificationType,
)

__all__ = [
    "AgentCapabilitiesGenerator",
    "AgentDeploymentService",
    "AgentLifecycleManager",
    "AgentLifecycleRecord",
    "AgentManager",
    "AgentMemoryManager",
    "AgentMetadata",
    "AgentModification",
    "AgentModificationTracker",
    "AgentPersistenceService",
    "AgentProfileLoader",
    "AgentRecommenderService",
    "AgentRegistry",
    "AgentTier",
    "AgentType",
    "AgentVersionManager",
    "AutoConfigManagerService",
    "BaseAgentManager",
    "CompositeObserver",
    "ConsoleProgressObserver",
    "DeployedAgentDiscovery",
    "FrameworkAgentLoader",
    "IDeploymentObserver",
    "LifecycleOperation",
    "LifecycleOperationResult",
    "LifecycleState",
    "ModificationHistory",
    "ModificationTier",
    "ModificationType",
    "NullObserver",
    "PersistenceOperation",
    "PersistenceRecord",
    "PersistenceStrategy",
    "get_memory_manager",
]
