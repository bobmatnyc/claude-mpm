# Agent Lifecycle Manager API Reference

Comprehensive API documentation for the AgentLifecycleManager, the unified interface for agent management in Claude MPM.

## Table of Contents

1. [Overview](#overview)
2. [Class Definition](#class-definition)
3. [Initialization](#initialization)
4. [Core Methods](#core-methods)
5. [Query Methods](#query-methods)
6. [Data Models](#data-models)
7. [Error Handling](#error-handling)
8. [Examples](#examples)

## Overview

The `AgentLifecycleManager` provides a unified async interface for complete agent lifecycle management, integrating content operations, modification tracking, persistence, and registry synchronization.

**Location**: `src/claude_mpm/services/agent_lifecycle_manager.py`

## Class Definition

```python
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
```

## Initialization

### Constructor

```python
def __init__(self, config: Optional[Dict[str, Any]] = None)
```

**Parameters:**
- `config` (Optional[Dict[str, Any]]): Configuration dictionary with the following options:
  - `enable_auto_backup` (bool): Enable automatic backups on deletion (default: True)
  - `enable_auto_validation` (bool): Enable automatic validation (default: True)
  - `enable_cache_invalidation` (bool): Enable cache invalidation (default: True)
  - `enable_registry_sync` (bool): Enable registry synchronization (default: True)
  - `default_persistence_strategy` (str): Default persistence strategy (default: "user_override")

### Starting the Service

```python
async def start() -> None
```

Initializes the lifecycle manager and all dependent services.

**Example:**
```python
lifecycle_manager = AgentLifecycleManager({
    "enable_auto_backup": True,
    "enable_cache_invalidation": True
})
await lifecycle_manager.start()
```

### Stopping the Service

```python
async def stop() -> None
```

Cleanly shuts down the lifecycle manager and dependent services.

## Core Methods

### create_agent

```python
async def create_agent(
    agent_name: str,
    agent_content: str,
    tier: ModificationTier = ModificationTier.USER,
    agent_type: str = "custom",
    **kwargs
) -> LifecycleOperationResult
```

Creates a new agent with complete lifecycle tracking.

**Parameters:**
- `agent_name` (str): Name of the agent to create (e.g., "security-agent")
- `agent_content` (str): Markdown content of the agent file
- `tier` (ModificationTier): Target tier (PROJECT, USER, or SYSTEM)
- `agent_type` (str): Type classification for the agent
- `**kwargs`: Additional metadata (author, tags, specializations, etc.)

**Returns:** `LifecycleOperationResult` with operation details

**Example:**
```python
result = await lifecycle_manager.create_agent(
    agent_name="security-audit-agent",
    agent_content="""# Security Audit Agent

## Primary Role
Perform security audits and compliance checks...
""",
    tier=ModificationTier.PROJECT,
    agent_type="security",
    author="security-team",
    tags=["security", "audit", "compliance"],
    specializations=["penetration-testing", "vulnerability-assessment"]
)

if result.success:
    print(f"Agent created: {result.metadata['file_path']}")
else:
    print(f"Creation failed: {result.error_message}")
```

### update_agent

```python
async def update_agent(
    agent_name: str,
    agent_content: str,
    **kwargs
) -> LifecycleOperationResult
```

Updates an existing agent with lifecycle tracking and versioning.

**Parameters:**
- `agent_name` (str): Name of the agent to update
- `agent_content` (str): New markdown content for the agent
- `**kwargs`: Metadata updates (model_preference, tags, specializations, etc.)

**Returns:** `LifecycleOperationResult` with operation details

**Example:**
```python
result = await lifecycle_manager.update_agent(
    agent_name="security-audit-agent",
    agent_content=updated_content,
    model_preference="claude-3-opus",
    tags=["security", "audit", "compliance", "updated"]
)

if result.success:
    print(f"Updated to version: {result.metadata['new_version']}")
    print(f"Modification ID: {result.modification_id}")
```

### delete_agent

```python
async def delete_agent(
    agent_name: str,
    **kwargs
) -> LifecycleOperationResult
```

Deletes an agent with automatic backup creation.

**Parameters:**
- `agent_name` (str): Name of the agent to delete
- `**kwargs`: Additional metadata (reason, deleted_by, etc.)

**Returns:** `LifecycleOperationResult` with operation details

**Example:**
```python
result = await lifecycle_manager.delete_agent(
    agent_name="deprecated-agent",
    reason="Replaced by new security-agent",
    deleted_by="admin"
)

if result.success:
    print(f"Agent deleted, backup at: {result.metadata['backup_path']}")
```

### restore_agent

```python
async def restore_agent(
    agent_name: str,
    backup_path: Optional[str] = None
) -> LifecycleOperationResult
```

Restores an agent from backup.

**Parameters:**
- `agent_name` (str): Name of the agent to restore
- `backup_path` (Optional[str]): Specific backup to restore (uses latest if not specified)

**Returns:** `LifecycleOperationResult` with operation details

**Example:**
```python
# Restore from latest backup
result = await lifecycle_manager.restore_agent("security-agent")

# Restore from specific backup
result = await lifecycle_manager.restore_agent(
    "security-agent",
    backup_path="/path/to/backup/security-agent_20240115_120000.md"
)
```

## Query Methods

### get_agent_status

```python
async def get_agent_status(
    agent_name: str
) -> Optional[AgentLifecycleRecord]
```

Gets the current lifecycle status of an agent.

**Parameters:**
- `agent_name` (str): Name of the agent

**Returns:** `AgentLifecycleRecord` or None if not found

**Example:**
```python
status = await lifecycle_manager.get_agent_status("security-agent")
if status:
    print(f"State: {status.current_state.value}")
    print(f"Version: {status.version}")
    print(f"Last modified: {status.last_modified_datetime}")
    print(f"Modifications: {len(status.modifications)}")
```

### list_agents

```python
async def list_agents(
    state_filter: Optional[LifecycleState] = None
) -> List[AgentLifecycleRecord]
```

Lists agents with optional state filtering.

**Parameters:**
- `state_filter` (Optional[LifecycleState]): Filter by lifecycle state

**Returns:** List of `AgentLifecycleRecord` objects sorted by last modified time

**Example:**
```python
# List all active agents
active_agents = await lifecycle_manager.list_agents(
    state_filter=LifecycleState.ACTIVE
)

for agent in active_agents:
    print(f"{agent.agent_name}: v{agent.version} ({agent.tier.value})")

# List all agents
all_agents = await lifecycle_manager.list_agents()
```

### get_operation_history

```python
async def get_operation_history(
    agent_name: Optional[str] = None,
    limit: int = 100
) -> List[LifecycleOperationResult]
```

Gets operation history with optional filtering.

**Parameters:**
- `agent_name` (Optional[str]): Filter by agent name
- `limit` (int): Maximum number of results (default: 100)

**Returns:** List of `LifecycleOperationResult` objects

**Example:**
```python
# Get all recent operations
history = await lifecycle_manager.get_operation_history(limit=50)

# Get operations for specific agent
agent_history = await lifecycle_manager.get_operation_history(
    agent_name="security-agent",
    limit=20
)

for op in agent_history:
    print(f"{op.operation.value}: {op.success} ({op.duration_ms}ms)")
```

### get_lifecycle_stats

```python
async def get_lifecycle_stats() -> Dict[str, Any]
```

Gets comprehensive lifecycle statistics.

**Returns:** Dictionary containing:
- `total_agents`: Total number of tracked agents
- `active_operations`: Number of currently active operations
- `agents_by_state`: Distribution of agents by lifecycle state
- `agents_by_tier`: Distribution of agents by tier
- `performance_metrics`: Performance statistics
- `recent_operations`: Count of operations in the last hour

**Example:**
```python
stats = await lifecycle_manager.get_lifecycle_stats()

print(f"Total agents: {stats['total_agents']}")
print(f"Active operations: {stats['active_operations']}")
print(f"\nAgents by state:")
for state, count in stats['agents_by_state'].items():
    print(f"  {state}: {count}")

metrics = stats['performance_metrics']
print(f"\nPerformance:")
print(f"  Total operations: {metrics['total_operations']}")
print(f"  Success rate: {metrics['successful_operations'] / metrics['total_operations'] * 100:.1f}%")
print(f"  Average duration: {metrics['average_duration_ms']:.1f}ms")
```

## Data Models

### LifecycleOperationResult

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

### AgentLifecycleRecord

```python
@dataclass
class AgentLifecycleRecord:
    agent_name: str
    current_state: LifecycleState
    tier: ModificationTier
    file_path: str
    created_at: float
    last_modified: float
    version: str
    modifications: List[str] = field(default_factory=list)
    persistence_operations: List[str] = field(default_factory=list)
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
```

### Enumerations

```python
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

class ModificationTier(Enum):
    """Agent hierarchy tiers."""
    SYSTEM = "system"
    USER = "user"
    PROJECT = "project"
```

## Error Handling

All methods return `LifecycleOperationResult` objects that encapsulate success/failure:

```python
result = await lifecycle_manager.create_agent(...)

if result.success:
    # Operation succeeded
    print(f"Success in {result.duration_ms}ms")
else:
    # Operation failed
    print(f"Failed: {result.error_message}")
    
    # Check for specific errors
    if "already exists" in result.error_message:
        # Handle duplicate agent
        pass
    elif "permission" in result.error_message.lower():
        # Handle permission error
        pass
```

### Common Error Scenarios

1. **Agent Already Exists**
   ```python
   result.error_message = "Agent already exists"
   ```

2. **Agent Not Found**
   ```python
   result.error_message = "Agent not found"
   ```

3. **Permission Denied**
   ```python
   result.error_message = "Permission denied for tier: PROJECT"
   ```

4. **Invalid Content**
   ```python
   result.error_message = "Invalid agent content: missing required sections"
   ```

## Examples

### Complete Agent Lifecycle

```python
import asyncio
from claude_mpm.services.agents.deployment import (
    AgentLifecycleManager,
    ModificationTier,
    LifecycleState
)

async def manage_agent_lifecycle():
    # Initialize manager
    manager = AgentLifecycleManager({
        "enable_auto_backup": True,
        "enable_cache_invalidation": True
    })
    await manager.start()
    
    try:
        # 1. Create agent
        create_result = await manager.create_agent(
            agent_name="data-processor",
            agent_content="""# Data Processing Agent
            
## Primary Role
Process and transform data according to business rules.

## Capabilities
- Data validation
- Format conversion
- Batch processing
""",
            tier=ModificationTier.PROJECT,
            agent_type="data",
            author="data-team"
        )
        
        if not create_result.success:
            print(f"Creation failed: {create_result.error_message}")
            return
            
        print(f"Agent created successfully")
        
        # 2. Check status
        status = await manager.get_agent_status("data-processor")
        print(f"Initial state: {status.current_state.value}")
        print(f"Version: {status.version}")
        
        # 3. Update agent
        update_result = await manager.update_agent(
            agent_name="data-processor",
            agent_content="""# Data Processing Agent v2
            
## Primary Role
Process, validate, and transform data with enhanced error handling.

## Capabilities
- Data validation with schema support
- Multiple format conversion
- Parallel batch processing
- Error recovery
""",
            tags=["data", "processing", "v2"]
        )
        
        if update_result.success:
            print(f"Updated to version: {update_result.metadata['new_version']}")
        
        # 4. Get operation history
        history = await manager.get_operation_history(
            agent_name="data-processor"
        )
        
        print(f"\nOperation history:")
        for op in history:
            print(f"  {op.operation.value}: {op.duration_ms:.1f}ms")
        
        # 5. Delete with backup
        delete_result = await manager.delete_agent(
            agent_name="data-processor",
            reason="Testing deletion and restore"
        )
        
        backup_path = delete_result.metadata.get('backup_path')
        print(f"\nDeleted, backup at: {backup_path}")
        
        # 6. Restore from backup
        restore_result = await manager.restore_agent(
            agent_name="data-processor",
            backup_path=backup_path
        )
        
        if restore_result.success:
            print("Agent restored successfully")
        
        # 7. Get final statistics
        stats = await manager.get_lifecycle_stats()
        print(f"\nFinal statistics:")
        print(f"  Total agents: {stats['total_agents']}")
        print(f"  Total operations: {stats['performance_metrics']['total_operations']}")
        
    finally:
        await manager.stop()

# Run the example
asyncio.run(manage_agent_lifecycle())
```

### Batch Operations with Error Handling

```python
async def batch_agent_operations():
    manager = AgentLifecycleManager()
    await manager.start()
    
    agents_to_create = [
        ("agent1", "content1", ModificationTier.USER),
        ("agent2", "content2", ModificationTier.PROJECT),
        ("agent3", "content3", ModificationTier.USER)
    ]
    
    results = []
    for name, content, tier in agents_to_create:
        result = await manager.create_agent(
            agent_name=name,
            agent_content=content,
            tier=tier
        )
        results.append((name, result))
    
    # Summary
    successful = sum(1 for _, r in results if r.success)
    print(f"Created {successful}/{len(results)} agents successfully")
    
    # Handle failures
    for name, result in results:
        if not result.success:
            print(f"Failed to create {name}: {result.error_message}")
            # Implement retry logic or alternative handling
    
    await manager.stop()
```

### Monitoring and Alerting

```python
async def monitor_agent_health():
    manager = AgentLifecycleManager()
    await manager.start()
    
    # Check for conflicted agents
    all_agents = await manager.list_agents()
    conflicted = [
        agent for agent in all_agents 
        if agent.current_state == LifecycleState.CONFLICTED
    ]
    
    if conflicted:
        print(f"Alert: {len(conflicted)} agents in conflicted state:")
        for agent in conflicted:
            print(f"  - {agent.agent_name}: {agent.validation_errors}")
    
    # Check performance
    stats = await manager.get_lifecycle_stats()
    metrics = stats['performance_metrics']
    
    if metrics['average_duration_ms'] > 1000:
        print(f"Alert: Slow operations detected")
        print(f"  Average duration: {metrics['average_duration_ms']:.1f}ms")
    
    success_rate = metrics['successful_operations'] / metrics['total_operations']
    if success_rate < 0.95:
        print(f"Alert: Low success rate: {success_rate*100:.1f}%")
    
    await manager.stop()
```

## Best Practices

1. **Always check operation results**
   ```python
   result = await manager.create_agent(...)
   if not result.success:
       logger.error(f"Operation failed: {result.error_message}")
   ```

2. **Use appropriate tiers**
   - SYSTEM: Core framework agents
   - USER: User-specific customizations
   - PROJECT: Project-specific agents

3. **Include metadata for tracking**
   ```python
   await manager.create_agent(
       agent_name="my-agent",
       agent_content=content,
       author="team-name",
       tags=["category", "version"],
       jira_ticket="PROJ-123"
   )
   ```

4. **Monitor performance metrics**
   ```python
   stats = await manager.get_lifecycle_stats()
   # Set up alerts based on metrics
   ```

5. **Handle service lifecycle properly**
   ```python
   manager = AgentLifecycleManager()
   try:
       await manager.start()
       # Operations...
   finally:
       await manager.stop()
   ```