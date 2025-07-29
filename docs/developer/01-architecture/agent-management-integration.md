# Agent Management Integration Architecture

This document describes the integrated agent management architecture in Claude MPM, where AgentManager is injected as a dependency into AgentLifecycleManager for comprehensive agent lifecycle management.

## Overview

The agent management system follows a clear separation of concerns:
- **AgentManager**: Handles agent content operations (CRUD, parsing, versioning)
- **AgentLifecycleManager**: Orchestrates the complete agent lifecycle with tracking, persistence, and registry synchronization

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                    AgentLifecycleManager                           │
│  (Orchestration Layer - Async)                                     │
├────────────────────────────────────────────────────────────────────┤
│  - Lifecycle State Management (Active, Modified, Deleted)          │
│  - Operation Coordination (Create, Update, Delete, Restore)        │
│  - Performance Metrics & Monitoring                                │
│  - Cache Invalidation & Registry Synchronization                   │
└────────────────────────┬───────────────────────────────────────────┘
                         │ Dependency Injection
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                        AgentManager                                │
│  (Content Management Layer - Sync)                                 │
├────────────────────────────────────────────────────────────────────┤
│  - Agent CRUD Operations                                           │
│  - Markdown Parsing & Generation                                   │
│  - Section Management                                              │
│  - Version Control                                                 │
└────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                    Supporting Services                             │
├────────────────────────────────────────────────────────────────────┤
│  AgentRegistry │ ModificationTracker │ PersistenceService │ Cache  │
└────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### AgentLifecycleManager (Orchestration)

**Purpose**: Provides a unified async interface for complete agent lifecycle management.

**Key Responsibilities**:
1. **Lifecycle State Management**
   - Tracks agent states: Active, Modified, Deleted, Conflicted
   - Maintains operation history and performance metrics
   - Coordinates multi-service operations

2. **Service Integration**
   - Injects AgentManager for content operations
   - Coordinates with ModificationTracker for change tracking
   - Manages cache invalidation through SharedPromptCache
   - Synchronizes with AgentRegistry for discovery

3. **Async/Sync Bridge**
   - Wraps sync AgentManager calls in executor
   - Provides fully async API to consumers
   - Ensures non-blocking operations

### AgentManager (Content Management)

**Purpose**: Handles all agent content operations with markdown parsing and generation.

**Key Responsibilities**:
1. **Content Operations**
   - Create, Read, Update, Delete agent definitions
   - Parse markdown with frontmatter and sections
   - Generate properly formatted agent files

2. **Version Management**
   - Increment serial versions on updates
   - Track version history in metadata
   - Maintain backward compatibility

3. **Section Management**
   - Extract and update individual sections
   - Parse complex structures (workflows, permissions)
   - Maintain section integrity

## Integration Pattern

### Dependency Injection

```python
class AgentLifecycleManager(BaseService):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("agent_lifecycle_manager", config)
        
        # Core services injected as dependencies
        self.agent_manager: Optional[AgentManager] = None
        self.modification_tracker: Optional[AgentModificationTracker] = None
        self.persistence_service: Optional[AgentPersistenceService] = None
        self.shared_cache: Optional[SharedPromptCache] = None
        self.agent_registry: Optional[AgentRegistry] = None
    
    async def _initialize_core_services(self) -> None:
        """Initialize injected services."""
        # AgentManager handles content operations
        self.agent_manager = AgentManager()
        
        # Other services for complete lifecycle management
        self.shared_cache = SharedPromptCache.get_instance()
        self.agent_registry = AgentRegistry(cache_service=self.shared_cache)
        self.modification_tracker = AgentModificationTracker()
        self.persistence_service = AgentPersistenceService()
```

### Async/Sync Execution Pattern

```python
async def _run_sync_in_executor(self, func, *args, **kwargs):
    """
    Run synchronous AgentManager methods in executor.
    
    This pattern allows the async AgentLifecycleManager to call
    sync AgentManager methods without blocking the event loop.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)

# Usage example
async def create_agent(self, agent_name: str, agent_content: str, ...):
    # Create agent definition model
    agent_def = await self._create_agent_definition(...)
    
    # Call sync AgentManager method in executor
    file_path = await self._run_sync_in_executor(
        self.agent_manager.create_agent,
        agent_name, agent_def, location
    )
```

## Data Flow

### Agent Creation Flow

```
1. Client calls AgentLifecycleManager.create_agent()
   ↓
2. AgentLifecycleManager creates AgentDefinition model
   ↓
3. AgentManager.create_agent() called via executor
   ↓
4. AgentManager parses and writes agent file
   ↓
5. ModificationTracker records the change
   ↓
6. Cache invalidated, Registry updated
   ↓
7. LifecycleOperationResult returned to client
```

### Model Mapping

The integration involves mapping between different data models:

```python
# AgentLifecycleManager works with lifecycle data
@dataclass
class AgentLifecycleRecord:
    agent_name: str
    current_state: LifecycleState
    tier: ModificationTier
    file_path: str
    version: str
    modifications: List[str]
    # ... lifecycle tracking fields

# AgentManager works with content model
@dataclass 
class AgentDefinition:
    name: str
    title: str
    metadata: AgentMetadata
    primary_role: str
    capabilities: List[str]
    # ... content fields
```

## API Design

### Unified Public Interface

The AgentLifecycleManager provides the single entry point for all agent operations:

```python
# Create a new agent
result = await lifecycle_manager.create_agent(
    agent_name="security-agent",
    agent_content=content,
    tier=ModificationTier.PROJECT,
    agent_type="security",
    specializations=["audit", "compliance"]
)

# Update existing agent
result = await lifecycle_manager.update_agent(
    agent_name="security-agent",
    agent_content=new_content,
    increment_version=True
)

# Delete agent with backup
result = await lifecycle_manager.delete_agent(
    agent_name="security-agent",
    create_backup=True
)

# Restore from backup
result = await lifecycle_manager.restore_agent(
    agent_name="security-agent",
    backup_path="/path/to/backup"
)
```

### Operation Results

All operations return a comprehensive result object:

```python
@dataclass
class LifecycleOperationResult:
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
```

## Error Handling

### Graceful Fallbacks

The integration includes fallback mechanisms when AgentManager is unavailable:

```python
try:
    if self.agent_manager:
        file_path = await self._run_sync_in_executor(
            self.agent_manager.create_agent,
            agent_name, agent_def, location
        )
    else:
        # Fallback to direct file creation
        file_path = await self._determine_agent_file_path(agent_name, tier)
        path_ops.ensure_dir(file_path.parent)
        path_ops.safe_write(file_path, agent_content)
except Exception as e:
    self.logger.error(f"AgentManager failed: {e}")
    # Fallback logic...
```

### Comprehensive Error Tracking

```python
# Errors are tracked in operation results
if not result.success:
    logger.error(f"Operation failed: {result.error_message}")
    
    # Update lifecycle state to reflect error
    record.current_state = LifecycleState.CONFLICTED
    
    # Metrics track failure rates
    self.performance_metrics['failed_operations'] += 1
```

## Performance Considerations

### Executor Usage

- Sync AgentManager methods run in thread pool executor
- Prevents blocking the async event loop
- Allows parallel agent operations

### Caching Strategy

```python
# Cache invalidation patterns
async def _invalidate_agent_cache(self, agent_name: str) -> bool:
    patterns = [
        f"agent_profile:{agent_name}:*",
        f"task_prompt:{agent_name}:*",
        f"agent_registry_discovery",
        f"agent_profile_enhanced:{agent_name}:*"
    ]
    
    for pattern in patterns:
        await self._invalidate_pattern(pattern)
```

### Metrics Collection

```python
# Comprehensive metrics tracking
self.performance_metrics = {
    'total_operations': 0,
    'successful_operations': 0,
    'failed_operations': 0,
    'average_duration_ms': 0.0,
    'operation_distribution': {},  # By operation type
    'tier_performance': {},        # By agent tier
    'cache_invalidations': 0
}
```

## Best Practices

### 1. Always Use AgentLifecycleManager

```python
# Good: Use the lifecycle manager
lifecycle_manager = AgentLifecycleManager()
await lifecycle_manager.start()
result = await lifecycle_manager.create_agent(...)

# Avoid: Direct AgentManager usage
agent_manager = AgentManager()
agent_manager.create_agent(...)  # No lifecycle tracking!
```

### 2. Handle Operation Results

```python
result = await lifecycle_manager.update_agent(...)

if result.success:
    logger.info(f"Agent updated in {result.duration_ms}ms")
    logger.info(f"New version: {result.metadata['new_version']}")
else:
    logger.error(f"Update failed: {result.error_message}")
    # Implement retry or escalation logic
```

### 3. Monitor Performance

```python
# Get lifecycle statistics
stats = await lifecycle_manager.get_lifecycle_stats()

logger.info(f"Total agents: {stats['total_agents']}")
logger.info(f"Active operations: {stats['active_operations']}")
logger.info(f"Average operation time: {stats['performance_metrics']['average_duration_ms']}ms")
```

## Migration Guide

### From Direct AgentManager Usage

```python
# Old approach
agent_manager = AgentManager()
agent_def = agent_manager.read_agent("my-agent")
agent_def.metadata.version = "2.0.0"
agent_manager.update_agent("my-agent", {"metadata": agent_def.metadata})

# New approach with lifecycle management
lifecycle_manager = AgentLifecycleManager()
await lifecycle_manager.start()

result = await lifecycle_manager.update_agent(
    agent_name="my-agent",
    agent_content=new_content,
    metadata={"version": "2.0.0"}
)

if result.success:
    logger.info(f"Agent updated with tracking: {result.modification_id}")
```

### From Custom Agent Operations

```python
# Old: Manual file operations
agent_file = Path(".claude-pm/agents/my-agent.md")
agent_file.write_text(content)
# No tracking, no cache invalidation, no registry update!

# New: Managed operations
result = await lifecycle_manager.create_agent(
    agent_name="my-agent",
    agent_content=content,
    tier=ModificationTier.PROJECT
)
# Automatic tracking, caching, registry sync
```

## Future Enhancements

### 1. Batch Operations

```python
# Future: Batch agent updates
results = await lifecycle_manager.batch_update_agents([
    {"name": "agent1", "content": content1},
    {"name": "agent2", "content": content2}
])
```

### 2. Agent Dependencies

```python
# Future: Dependency management
deps = await lifecycle_manager.get_agent_dependencies("my-agent")
await lifecycle_manager.update_agent_graph(agent_name, dependencies)
```

### 3. Advanced Querying

```python
# Future: Query agents by capability
agents = await lifecycle_manager.query_agents(
    capabilities=["security", "audit"],
    tier=ModificationTier.PROJECT,
    state=LifecycleState.ACTIVE
)
```

## Summary

The integrated agent management architecture provides:

1. **Clear Separation**: AgentManager handles content, AgentLifecycleManager handles orchestration
2. **Single Entry Point**: All operations go through AgentLifecycleManager
3. **Comprehensive Tracking**: Every operation is tracked with metrics and history
4. **Robust Error Handling**: Fallbacks ensure operations complete even if services fail
5. **Performance Optimized**: Async operations with efficient executor usage
6. **Future-Proof**: Extensible design supports new features without breaking changes

This architecture ensures reliable, traceable, and performant agent management across the Claude MPM system.