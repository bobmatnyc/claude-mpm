"""Agent services module - hierarchical organization of agent-related services."""

# Registry exports
from .registry.agent_registry import (
    AgentRegistry,
    AgentMetadata,
    AgentTier,
    AgentType,
)
from .registry.deployed_agent_discovery import DeployedAgentDiscovery
from .registry.modification_tracker import (
    AgentModificationTracker,
    ModificationType,
    ModificationTier,
    AgentModification,
    ModificationHistory,
)

# Loading exports
from .loading.framework_agent_loader import FrameworkAgentLoader
from .loading.agent_profile_loader import AgentProfileLoader
from .loading.base_agent_manager import BaseAgentManager

# Deployment exports
from .deployment.agent_deployment import AgentDeploymentService
from .deployment.agent_lifecycle_manager import (
    AgentLifecycleManager,
    LifecycleState,
    LifecycleOperation,
    AgentLifecycleRecord,
    LifecycleOperationResult,
)
from .deployment.agent_versioning import AgentVersionManager

# Memory exports
from .memory.agent_memory_manager import (
    AgentMemoryManager,
    get_memory_manager,
)
from .memory.agent_persistence_service import (
    AgentPersistenceService,
    PersistenceStrategy,
    PersistenceOperation,
    PersistenceRecord,
)

# Management exports
from .management.agent_management_service import AgentManager
from .management.agent_capabilities_generator import AgentCapabilitiesGenerator

__all__ = [
    # Registry
    "AgentRegistry",
    "AgentMetadata",
    "AgentTier",
    "AgentType",
    "DeployedAgentDiscovery",
    "AgentModificationTracker",
    "ModificationType",
    "ModificationTier",
    "AgentModification",
    "ModificationHistory",
    # Loading
    "FrameworkAgentLoader",
    "AgentProfileLoader",
    "BaseAgentManager",
    # Deployment
    "AgentDeploymentService",
    "AgentLifecycleManager",
    "LifecycleState",
    "LifecycleOperation",
    "AgentLifecycleRecord",
    "LifecycleOperationResult",
    "AgentVersionManager",
    # Memory
    "AgentMemoryManager",
    "get_memory_manager",
    "AgentPersistenceService",
    "PersistenceStrategy",
    "PersistenceOperation",
    "PersistenceRecord",
    # Management
    "AgentManager",
    "AgentCapabilitiesGenerator",
]