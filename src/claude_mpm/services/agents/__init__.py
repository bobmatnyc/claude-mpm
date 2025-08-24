"""Agent services module - hierarchical organization of agent-related services."""

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
    # Deployment
    "AgentDeploymentService",
    "AgentLifecycleManager",
    "AgentLifecycleRecord",
    # Management
    "AgentManager",
    # Memory
    "AgentMemoryManager",
    "AgentMetadata",
    "AgentModification",
    "AgentModificationTracker",
    "AgentPersistenceService",
    "AgentProfileLoader",
    # Registry
    "AgentRegistry",
    "AgentTier",
    "AgentType",
    "AgentVersionManager",
    "BaseAgentManager",
    "DeployedAgentDiscovery",
    # Loading
    "FrameworkAgentLoader",
    "LifecycleOperation",
    "LifecycleOperationResult",
    "LifecycleState",
    "ModificationHistory",
    "ModificationTier",
    "ModificationType",
    "PersistenceOperation",
    "PersistenceRecord",
    "PersistenceStrategy",
    "get_memory_manager",
]
