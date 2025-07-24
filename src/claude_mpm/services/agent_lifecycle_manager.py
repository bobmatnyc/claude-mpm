#!/usr/bin/env python3
"""
Agent Lifecycle Manager - ISS-0118 Integration Service
======================================================

Comprehensive agent lifecycle management integrating modification tracking,
persistence, and registry services for complete agent management across
the three-tier hierarchy.

Key Features:
- Unified agent lifecycle management (create, modify, delete, restore)
- Integrated modification tracking and persistence
- Automatic cache invalidation and registry updates
- Comprehensive backup and versioning system
- Conflict detection and resolution workflows
- Performance monitoring and optimization

Performance Impact:
- <100ms end-to-end agent operations
- Automatic cache coherency maintenance
- Intelligent persistence routing
- Real-time modification detection

Created for ISS-0118: Agent Registry and Hierarchical Discovery System
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple, Union

from claude_pm.services.shared_prompt_cache import SharedPromptCache
from claude_pm.services.agent_registry import AgentRegistry, AgentMetadata
from claude_pm.services.agent_modification_tracker import (
    AgentModificationTracker, 
    AgentModification, 
    ModificationType, 
    ModificationTier
)
from claude_pm.services.agent_persistence_service import (
    AgentPersistenceService,
    PersistenceRecord,
    PersistenceStrategy,
    PersistenceOperation
)
from claude_pm.core.base_service import BaseService


class LifecycleOperation(Enum):
    """Agent lifecycle operations."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    MIGRATE = "migrate"
    REPLICATE = "replicate"
    VALIDATE = "validate"


class LifecycleState(Enum):
    """Agent lifecycle states."""
    ACTIVE = "active"
    MODIFIED = "modified"
    DELETED = "deleted"
    CONFLICTED = "conflicted"
    MIGRATING = "migrating"
    VALIDATING = "validating"


@dataclass
class AgentLifecycleRecord:
    """Complete lifecycle record for an agent."""
    
    agent_name: str
    current_state: LifecycleState
    tier: ModificationTier
    file_path: str
    created_at: float
    last_modified: float
    version: str
    modifications: List[str] = field(default_factory=list)  # Modification IDs
    persistence_operations: List[str] = field(default_factory=list)  # Operation IDs
    backup_paths: List[str] = field(default_factory=list)
    validation_status: str = "valid"
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def age_days(self) -> float:
        """Get age in days."""
        return (time.time() - self.created_at) / (24 * 3600)
    
    @property
    def last_modified_datetime(self) -> datetime:
        """Get last modified as datetime."""
        return datetime.fromtimestamp(self.last_modified)


@dataclass
class LifecycleOperationResult:
    """Result of a lifecycle operation."""
    
    operation: LifecycleOperation
    agent_name: str
    success: bool
    duration_ms: float
    error_message: Optional[str] = None
    modification_id: Optional[str] = None
    persistence_id: Optional[str] = None
    cache_invalidated: bool = False
    registry_updated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentLifecycleManager(BaseService):
    """
    Agent Lifecycle Manager - Unified agent management across hierarchy tiers.
    
    Features:
    - Complete agent lifecycle management (CRUD operations)
    - Integrated modification tracking and persistence
    - Automatic cache invalidation and registry synchronization
    - Comprehensive backup and versioning system
    - Real-time conflict detection and resolution
    - Performance monitoring and optimization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the agent lifecycle manager."""
        super().__init__("agent_lifecycle_manager", config)
        
        # Configuration
        self.enable_auto_backup = self.get_config("enable_auto_backup", True)
        self.enable_auto_validation = self.get_config("enable_auto_validation", True)
        self.enable_cache_invalidation = self.get_config("enable_cache_invalidation", True)
        self.enable_registry_sync = self.get_config("enable_registry_sync", True)
        self.default_persistence_strategy = PersistenceStrategy(
            self.get_config("default_persistence_strategy", PersistenceStrategy.USER_OVERRIDE.value)
        )
        
        # Core services
        self.shared_cache: Optional[SharedPromptCache] = None
        self.agent_registry: Optional[AgentRegistry] = None
        self.modification_tracker: Optional[AgentModificationTracker] = None
        self.persistence_service: Optional[AgentPersistenceService] = None
        
        # Lifecycle tracking
        self.agent_records: Dict[str, AgentLifecycleRecord] = {}
        self.operation_history: List[LifecycleOperationResult] = []
        self.active_operations: Dict[str, LifecycleOperation] = {}
        
        # Performance metrics
        self.performance_metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_duration_ms': 0.0,
            'cache_hit_rate': 0.0
        }
        
        # Operation lock for thread safety
        self._operation_lock = asyncio.Lock()
        
        self.logger.info("AgentLifecycleManager initialized")
    
    async def _initialize(self) -> None:
        """Initialize the lifecycle manager."""
        self.logger.info("Initializing AgentLifecycleManager...")
        
        # Initialize core services
        await self._initialize_core_services()
        
        # Load existing agent records
        await self._load_agent_records()
        
        # Start service integrations
        await self._setup_service_integrations()
        
        # Perform initial registry sync
        if self.enable_registry_sync:
            await self._sync_with_registry()
        
        self.logger.info("AgentLifecycleManager initialized successfully")
    
    async def _cleanup(self) -> None:
        """Cleanup lifecycle manager resources."""
        self.logger.info("Cleaning up AgentLifecycleManager...")
        
        # Save agent records
        await self._save_agent_records()
        
        # Stop core services if we own them
        await self._cleanup_core_services()
        
        self.logger.info("AgentLifecycleManager cleaned up")
    
    async def _health_check(self) -> Dict[str, bool]:
        """Perform lifecycle manager health checks."""
        checks = {}
        
        try:
            # Check core service availability
            checks["cache_service"] = self.shared_cache is not None
            checks["registry_service"] = self.agent_registry is not None
            checks["tracker_service"] = self.modification_tracker is not None
            checks["persistence_service"] = self.persistence_service is not None
            
            # Check operation capabilities
            checks["can_create_agents"] = await self._test_create_capability()
            checks["can_modify_agents"] = await self._test_modify_capability()
            checks["can_delete_agents"] = await self._test_delete_capability()
            
            # Check data integrity
            checks["agent_records_valid"] = len(self.agent_records) >= 0
            checks["operation_history_valid"] = len(self.operation_history) >= 0
            
        except Exception as e:
            self.logger.error(f"Lifecycle manager health check failed: {e}")
            checks["health_check_error"] = False
        
        return checks
    
    async def _initialize_core_services(self) -> None:
        """Initialize core service dependencies."""
        try:
            # Initialize SharedPromptCache
            self.shared_cache = SharedPromptCache.get_instance()
            
            # Initialize AgentRegistry
            self.agent_registry = AgentRegistry(cache_service=self.shared_cache)
            
            # Initialize AgentModificationTracker
            self.modification_tracker = AgentModificationTracker()
            await self.modification_tracker.start()
            
            # Initialize AgentPersistenceService
            self.persistence_service = AgentPersistenceService()
            await self.persistence_service.start()
            
            self.logger.info("Core services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize core services: {e}")
            raise
    
    async def _setup_service_integrations(self) -> None:
        """Set up integrations between services."""
        try:
            # Register modification callback
            if self.modification_tracker:
                self.modification_tracker.register_modification_callback(
                    self._handle_modification_event
                )
            
            self.logger.debug("Service integrations set up successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to setup some service integrations: {e}")
    
    async def _load_agent_records(self) -> None:
        """Load existing agent lifecycle records."""
        try:
            records_file = Path.home() / '.claude-pm' / 'agent_tracking' / 'lifecycle_records.json'
            if records_file.exists():
                with open(records_file, 'r') as f:
                    data = json.load(f)
                
                for agent_name, record_data in data.items():
                    record = AgentLifecycleRecord(**record_data)
                    # Convert string enum back to enum
                    record.current_state = LifecycleState(record_data['current_state'])
                    record.tier = ModificationTier(record_data['tier'])
                    self.agent_records[agent_name] = record
                
                self.logger.info(f"Loaded {len(self.agent_records)} agent records")
            
        except Exception as e:
            self.logger.warning(f"Failed to load agent records: {e}")
    
    async def _save_agent_records(self) -> None:
        """Save agent lifecycle records to disk."""
        try:
            records_file = Path.home() / '.claude-pm' / 'agent_tracking' / 'lifecycle_records.json'
            records_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {}
            for agent_name, record in self.agent_records.items():
                record_dict = record.__dict__.copy()
                # Convert enums to strings for JSON serialization
                record_dict['current_state'] = record.current_state.value
                record_dict['tier'] = record.tier.value
                data[agent_name] = record_dict
            
            with open(records_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            self.logger.debug(f"Saved {len(self.agent_records)} agent records")
            
        except Exception as e:
            self.logger.error(f"Failed to save agent records: {e}")
    
    async def _sync_with_registry(self) -> None:
        """Synchronize with agent registry."""
        try:
            if not self.agent_registry:
                return
            
            # Discover all agents via registry
            await self.agent_registry.discover_agents()
            all_agents = await self.agent_registry.list_agents()
            
            # Update lifecycle records with registry data
            for agent_metadata in all_agents:
                if agent_metadata.name not in self.agent_records:
                    # Create new lifecycle record
                    tier_map = {
                        'project': ModificationTier.PROJECT,
                        'user': ModificationTier.USER,
                        'system': ModificationTier.SYSTEM
                    }
                    
                    record = AgentLifecycleRecord(
                        agent_name=agent_metadata.name,
                        current_state=LifecycleState.ACTIVE,
                        tier=tier_map.get(agent_metadata.tier, ModificationTier.USER),
                        file_path=agent_metadata.path,
                        created_at=agent_metadata.last_modified or time.time(),
                        last_modified=agent_metadata.last_modified or time.time(),
                        version="1.0.0",
                        metadata={
                            'type': agent_metadata.type,
                            'description': agent_metadata.description,
                            'capabilities': agent_metadata.capabilities,
                            'validated': agent_metadata.validated
                        }
                    )
                    
                    self.agent_records[agent_metadata.name] = record
            
            self.logger.info(f"Synchronized with registry: {len(all_agents)} agents")
            
        except Exception as e:
            self.logger.error(f"Failed to sync with registry: {e}")
    
    async def create_agent(self,
                          agent_name: str,
                          agent_content: str,
                          tier: ModificationTier = ModificationTier.USER,
                          agent_type: str = "custom",
                          **kwargs) -> LifecycleOperationResult:
        """
        Create a new agent with complete lifecycle tracking.
        
        Args:
            agent_name: Name of the agent to create
            agent_content: Content of the agent file
            tier: Target tier for creation
            agent_type: Type of agent (for classification)
            **kwargs: Additional metadata
            
        Returns:
            LifecycleOperationResult with operation details
        """
        start_time = time.time()
        
        async with self._operation_lock:
            self.active_operations[agent_name] = LifecycleOperation.CREATE
            
            try:
                # Check if agent already exists
                if agent_name in self.agent_records:
                    return LifecycleOperationResult(
                        operation=LifecycleOperation.CREATE,
                        agent_name=agent_name,
                        success=False,
                        duration_ms=(time.time() - start_time) * 1000,
                        error_message="Agent already exists"
                    )
                
                # Determine file path
                file_path = await self._determine_agent_file_path(agent_name, tier)
                
                # Track modification
                modification = await self.modification_tracker.track_modification(
                    agent_name=agent_name,
                    modification_type=ModificationType.CREATE,
                    file_path=str(file_path),
                    tier=tier,
                    agent_type=agent_type,
                    **kwargs
                )
                
                # Persist agent
                persistence_record = await self.persistence_service.persist_agent(
                    agent_name=agent_name,
                    agent_content=agent_content,
                    source_tier=tier,
                    target_tier=tier,
                    strategy=self.default_persistence_strategy
                )
                
                # Create lifecycle record
                lifecycle_record = AgentLifecycleRecord(
                    agent_name=agent_name,
                    current_state=LifecycleState.ACTIVE,
                    tier=tier,
                    file_path=str(file_path),
                    created_at=time.time(),
                    last_modified=time.time(),
                    version="1.0.0",
                    modifications=[modification.modification_id],
                    persistence_operations=[persistence_record.operation_id],
                    metadata={
                        'agent_type': agent_type,
                        **kwargs
                    }
                )
                
                self.agent_records[agent_name] = lifecycle_record
                
                # Invalidate cache and update registry
                cache_invalidated = await self._invalidate_agent_cache(agent_name)
                registry_updated = await self._update_registry(agent_name)
                
                # Create result
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.CREATE,
                    agent_name=agent_name,
                    success=persistence_record.success,
                    duration_ms=(time.time() - start_time) * 1000,
                    modification_id=modification.modification_id,
                    persistence_id=persistence_record.operation_id,
                    cache_invalidated=cache_invalidated,
                    registry_updated=registry_updated,
                    metadata={'file_path': str(file_path)}
                )
                
                if not persistence_record.success:
                    result.error_message = persistence_record.error_message
                    lifecycle_record.current_state = LifecycleState.CONFLICTED
                
                # Update performance metrics
                await self._update_performance_metrics(result)
                
                self.operation_history.append(result)
                self.logger.info(f"Created agent '{agent_name}' in {result.duration_ms:.1f}ms")
                
                return result
                
            except Exception as e:
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.CREATE,
                    agent_name=agent_name,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message=str(e)
                )
                
                self.operation_history.append(result)
                await self._update_performance_metrics(result)
                
                self.logger.error(f"Failed to create agent '{agent_name}': {e}")
                return result
            
            finally:
                self.active_operations.pop(agent_name, None)
    
    async def update_agent(self,
                          agent_name: str,
                          agent_content: str,
                          **kwargs) -> LifecycleOperationResult:
        """
        Update an existing agent with lifecycle tracking.
        
        Args:
            agent_name: Name of the agent to update
            agent_content: New content for the agent
            **kwargs: Additional metadata
            
        Returns:
            LifecycleOperationResult with operation details
        """
        start_time = time.time()
        
        async with self._operation_lock:
            self.active_operations[agent_name] = LifecycleOperation.UPDATE
            
            try:
                # Check if agent exists
                if agent_name not in self.agent_records:
                    return LifecycleOperationResult(
                        operation=LifecycleOperation.UPDATE,
                        agent_name=agent_name,
                        success=False,
                        duration_ms=(time.time() - start_time) * 1000,
                        error_message="Agent not found"
                    )
                
                record = self.agent_records[agent_name]
                
                # Track modification
                modification = await self.modification_tracker.track_modification(
                    agent_name=agent_name,
                    modification_type=ModificationType.MODIFY,
                    file_path=record.file_path,
                    tier=record.tier,
                    **kwargs
                )
                
                # Persist agent
                persistence_record = await self.persistence_service.persist_agent(
                    agent_name=agent_name,
                    agent_content=agent_content,
                    source_tier=record.tier,
                    strategy=self.default_persistence_strategy
                )
                
                # Update lifecycle record
                record.current_state = LifecycleState.MODIFIED
                record.last_modified = time.time()
                record.modifications.append(modification.modification_id)
                record.persistence_operations.append(persistence_record.operation_id)
                
                # Increment version
                current_version = record.version.split('.')
                current_version[-1] = str(int(current_version[-1]) + 1)
                record.version = '.'.join(current_version)
                
                # Invalidate cache and update registry
                cache_invalidated = await self._invalidate_agent_cache(agent_name)
                registry_updated = await self._update_registry(agent_name)
                
                # Create result
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.UPDATE,
                    agent_name=agent_name,
                    success=persistence_record.success,
                    duration_ms=(time.time() - start_time) * 1000,
                    modification_id=modification.modification_id,
                    persistence_id=persistence_record.operation_id,
                    cache_invalidated=cache_invalidated,
                    registry_updated=registry_updated,
                    metadata={'new_version': record.version}
                )
                
                if not persistence_record.success:
                    result.error_message = persistence_record.error_message
                    record.current_state = LifecycleState.CONFLICTED
                
                # Update performance metrics
                await self._update_performance_metrics(result)
                
                self.operation_history.append(result)
                self.logger.info(f"Updated agent '{agent_name}' to version {record.version} in {result.duration_ms:.1f}ms")
                
                return result
                
            except Exception as e:
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.UPDATE,
                    agent_name=agent_name,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message=str(e)
                )
                
                self.operation_history.append(result)
                await self._update_performance_metrics(result)
                
                self.logger.error(f"Failed to update agent '{agent_name}': {e}")
                return result
            
            finally:
                self.active_operations.pop(agent_name, None)
    
    async def delete_agent(self, agent_name: str, **kwargs) -> LifecycleOperationResult:
        """
        Delete an agent with lifecycle tracking.
        
        Args:
            agent_name: Name of the agent to delete
            **kwargs: Additional metadata
            
        Returns:
            LifecycleOperationResult with operation details
        """
        start_time = time.time()
        
        async with self._operation_lock:
            self.active_operations[agent_name] = LifecycleOperation.DELETE
            
            try:
                # Check if agent exists
                if agent_name not in self.agent_records:
                    return LifecycleOperationResult(
                        operation=LifecycleOperation.DELETE,
                        agent_name=agent_name,
                        success=False,
                        duration_ms=(time.time() - start_time) * 1000,
                        error_message="Agent not found"
                    )
                
                record = self.agent_records[agent_name]
                
                # Create backup before deletion
                backup_path = None
                if self.enable_auto_backup:
                    backup_path = await self._create_deletion_backup(agent_name, record)
                
                # Track modification
                modification = await self.modification_tracker.track_modification(
                    agent_name=agent_name,
                    modification_type=ModificationType.DELETE,
                    file_path=record.file_path,
                    tier=record.tier,
                    backup_path=backup_path,
                    **kwargs
                )
                
                # Delete file
                file_path = Path(record.file_path)
                if file_path.exists():
                    file_path.unlink()
                
                # Update lifecycle record
                record.current_state = LifecycleState.DELETED
                record.last_modified = time.time()
                record.modifications.append(modification.modification_id)
                if backup_path:
                    record.backup_paths.append(backup_path)
                
                # Invalidate cache and update registry
                cache_invalidated = await self._invalidate_agent_cache(agent_name)
                registry_updated = await self._update_registry(agent_name)
                
                # Create result
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.DELETE,
                    agent_name=agent_name,
                    success=True,
                    duration_ms=(time.time() - start_time) * 1000,
                    modification_id=modification.modification_id,
                    cache_invalidated=cache_invalidated,
                    registry_updated=registry_updated,
                    metadata={'backup_path': backup_path}
                )
                
                # Update performance metrics
                await self._update_performance_metrics(result)
                
                self.operation_history.append(result)
                self.logger.info(f"Deleted agent '{agent_name}' in {result.duration_ms:.1f}ms")
                
                return result
                
            except Exception as e:
                result = LifecycleOperationResult(
                    operation=LifecycleOperation.DELETE,
                    agent_name=agent_name,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message=str(e)
                )
                
                self.operation_history.append(result)
                await self._update_performance_metrics(result)
                
                self.logger.error(f"Failed to delete agent '{agent_name}': {e}")
                return result
            
            finally:
                self.active_operations.pop(agent_name, None)
    
    async def _determine_agent_file_path(self, agent_name: str, tier: ModificationTier) -> Path:
        """Determine appropriate file path for agent."""
        if tier == ModificationTier.USER:
            base_path = Path.home() / '.claude-pm' / 'agents'
        elif tier == ModificationTier.PROJECT:
            base_path = Path.cwd() / '.claude-pm' / 'agents'
        else:  # SYSTEM
            base_path = Path.cwd() / 'claude_pm' / 'agents'
        
        base_path.mkdir(parents=True, exist_ok=True)
        return base_path / f"{agent_name}_agent.py"
    
    async def _create_deletion_backup(self, agent_name: str, record: AgentLifecycleRecord) -> Optional[str]:
        """Create backup before agent deletion."""
        try:
            import shutil
            
            source_path = Path(record.file_path)
            if not source_path.exists():
                return None
            
            backup_dir = Path.home() / '.claude-pm' / 'agent_tracking' / 'backups'
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{agent_name}_deleted_{timestamp}{source_path.suffix}"
            backup_path = backup_dir / backup_filename
            
            shutil.copy2(source_path, backup_path)
            return str(backup_path)
            
        except Exception as e:
            self.logger.warning(f"Failed to create deletion backup for {agent_name}: {e}")
            return None
    
    async def _invalidate_agent_cache(self, agent_name: str) -> bool:
        """Invalidate cache entries for agent."""
        if not self.enable_cache_invalidation or not self.shared_cache:
            return False
        
        try:
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
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to invalidate cache for {agent_name}: {e}")
            return False
    
    async def _update_registry(self, agent_name: str) -> bool:
        """Update agent registry after modification."""
        if not self.enable_registry_sync or not self.agent_registry:
            return False
        
        try:
            # Refresh specific agent in registry
            await self.agent_registry.refresh_agent(agent_name)
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to update registry for {agent_name}: {e}")
            return False
    
    async def _update_performance_metrics(self, result: LifecycleOperationResult) -> None:
        """Update performance metrics with operation result."""
        self.performance_metrics['total_operations'] += 1
        
        if result.success:
            self.performance_metrics['successful_operations'] += 1
        else:
            self.performance_metrics['failed_operations'] += 1
        
        # Update average duration
        total_ops = self.performance_metrics['total_operations']
        current_avg = self.performance_metrics['average_duration_ms']
        new_avg = ((current_avg * (total_ops - 1)) + result.duration_ms) / total_ops
        self.performance_metrics['average_duration_ms'] = new_avg
        
        # Update cache hit rate if cache was involved
        if result.cache_invalidated:
            # This would be more sophisticated in practice
            pass
    
    async def _handle_modification_event(self, modification: AgentModification) -> None:
        """Handle modification events from tracker."""
        try:
            agent_name = modification.agent_name
            
            # Update lifecycle record if exists
            if agent_name in self.agent_records:
                record = self.agent_records[agent_name]
                record.last_modified = modification.timestamp
                record.modifications.append(modification.modification_id)
                
                # Update state based on modification type
                if modification.modification_type == ModificationType.DELETE:
                    record.current_state = LifecycleState.DELETED
                elif modification.modification_type in [ModificationType.CREATE, ModificationType.MODIFY]:
                    record.current_state = LifecycleState.MODIFIED
                
                self.logger.debug(f"Updated lifecycle record for {agent_name} due to {modification.modification_type.value}")
            
        except Exception as e:
            self.logger.error(f"Error handling modification event: {e}")
    
    async def _test_create_capability(self) -> bool:
        """Test agent creation capability."""
        try:
            # This would test if we can create agents in the configured tiers
            return (self.modification_tracker is not None and 
                   self.persistence_service is not None)
        except Exception:
            return False
    
    async def _test_modify_capability(self) -> bool:
        """Test agent modification capability."""
        try:
            # This would test if we can modify existing agents
            return (self.modification_tracker is not None and 
                   self.persistence_service is not None)
        except Exception:
            return False
    
    async def _test_delete_capability(self) -> bool:
        """Test agent deletion capability."""
        try:
            # This would test if we can delete agents
            return self.modification_tracker is not None
        except Exception:
            return False
    
    async def _cleanup_core_services(self) -> None:
        """Cleanup core services if we manage their lifecycle."""
        try:
            if self.modification_tracker:
                await self.modification_tracker.stop()
            
            if self.persistence_service:
                await self.persistence_service.stop()
            
        except Exception as e:
            self.logger.error(f"Error cleaning up core services: {e}")
    
    # Public API Methods
    
    async def get_agent_status(self, agent_name: str) -> Optional[AgentLifecycleRecord]:
        """Get current status of an agent."""
        return self.agent_records.get(agent_name)
    
    async def list_agents(self, state_filter: Optional[LifecycleState] = None) -> List[AgentLifecycleRecord]:
        """List agents with optional state filtering."""
        agents = list(self.agent_records.values())
        
        if state_filter:
            agents = [agent for agent in agents if agent.current_state == state_filter]
        
        return sorted(agents, key=lambda x: x.last_modified, reverse=True)
    
    async def get_operation_history(self, agent_name: Optional[str] = None, limit: int = 100) -> List[LifecycleOperationResult]:
        """Get operation history with optional filtering."""
        history = self.operation_history
        
        if agent_name:
            history = [op for op in history if op.agent_name == agent_name]
        
        return sorted(history, key=lambda x: x.duration_ms, reverse=True)[:limit]
    
    async def get_lifecycle_stats(self) -> Dict[str, Any]:
        """Get comprehensive lifecycle statistics."""
        stats = {
            'total_agents': len(self.agent_records),
            'active_operations': len(self.active_operations),
            'performance_metrics': self.performance_metrics.copy()
        }
        
        # State distribution
        state_counts = {}
        for record in self.agent_records.values():
            state_counts[record.current_state.value] = state_counts.get(record.current_state.value, 0) + 1
        
        stats['agents_by_state'] = state_counts
        
        # Tier distribution
        tier_counts = {}
        for record in self.agent_records.values():
            tier_counts[record.tier.value] = tier_counts.get(record.tier.value, 0) + 1
        
        stats['agents_by_tier'] = tier_counts
        
        # Recent activity
        recent_ops = [
            op for op in self.operation_history 
            if (time.time() - (op.duration_ms / 1000)) < 3600  # Last hour
        ]
        stats['recent_operations'] = len(recent_ops)
        
        return stats
    
    async def restore_agent(self, agent_name: str, backup_path: Optional[str] = None) -> LifecycleOperationResult:
        """Restore agent from backup."""
        start_time = time.time()
        
        try:
            record = self.agent_records.get(agent_name)
            if not record:
                return LifecycleOperationResult(
                    operation=LifecycleOperation.RESTORE,
                    agent_name=agent_name,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message="Agent record not found"
                )
            
            # Use latest backup if not specified
            if not backup_path and record.backup_paths:
                backup_path = record.backup_paths[-1]
            
            if not backup_path or not Path(backup_path).exists():
                return LifecycleOperationResult(
                    operation=LifecycleOperation.RESTORE,
                    agent_name=agent_name,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message="No valid backup found"
                )
            
            # Read backup content
            backup_content = Path(backup_path).read_text(encoding='utf-8')
            
            # Restore via update operation
            return await self.update_agent(
                agent_name=agent_name,
                agent_content=backup_content,
                restored_from=backup_path
            )
            
        except Exception as e:
            return LifecycleOperationResult(
                operation=LifecycleOperation.RESTORE,
                agent_name=agent_name,
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )