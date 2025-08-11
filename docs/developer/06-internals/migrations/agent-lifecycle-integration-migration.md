# Agent Lifecycle Integration Migration Guide

This guide helps developers migrate from direct agent management to the integrated AgentLifecycleManager approach.

## Overview

The new architecture introduces AgentLifecycleManager as the primary interface for all agent operations, with AgentManager injected as a dependency for content management.

## Migration Checklist

- [ ] Replace direct AgentManager usage with AgentLifecycleManager
- [ ] Update synchronous calls to use async/await patterns  
- [ ] Handle LifecycleOperationResult instead of raw returns
- [ ] Update error handling to check result.success
- [ ] Remove manual cache invalidation (now automatic)
- [ ] Remove manual registry updates (now automatic)

## Code Migration Examples

### 1. Creating Agents

#### Before (Direct AgentManager)

```python
from claude_mpm.services.agents.management import AgentManager
from claude_mpm.models.agent_definition import AgentDefinition, AgentMetadata

# Synchronous creation
agent_manager = AgentManager()

# Build definition manually
metadata = AgentMetadata(
    type="custom",
    version="1.0.0",
    specializations=["testing"]
)

definition = AgentDefinition(
    name="test-agent",
    title="Test Agent",
    metadata=metadata,
    primary_role="Testing agent",
    # ... other fields
)

# Create agent
file_path = agent_manager.create_agent(
    "test-agent",
    definition,
    "project"
)

# Manual cache invalidation needed
cache.invalidate(f"agent_profile:test-agent:*")

# Manual registry update needed  
registry.discover_agents()
```

#### After (AgentLifecycleManager)

```python
from claude_mpm.services.agents.deployment import (
    AgentLifecycleManager,
    ModificationTier
)

# Async creation with lifecycle management
lifecycle_manager = AgentLifecycleManager()
await lifecycle_manager.start()

# Simple creation - definition built internally
result = await lifecycle_manager.create_agent(
    agent_name="test-agent",
    agent_content=agent_markdown_content,
    tier=ModificationTier.PROJECT,
    agent_type="testing",
    specializations=["testing"],
    author="dev-team"
)

# Check result
if result.success:
    print(f"Agent created at: {result.metadata['file_path']}")
    print(f"Cache invalidated: {result.cache_invalidated}")
    print(f"Registry updated: {result.registry_updated}")
else:
    print(f"Creation failed: {result.error_message}")
```

### 2. Reading Agents

#### Before

```python
# Direct read
agent_def = agent_manager.read_agent("test-agent")
if agent_def:
    print(f"Version: {agent_def.metadata.version}")
    print(f"Capabilities: {agent_def.capabilities}")
else:
    print("Agent not found")
```

#### After

```python
# Get lifecycle status
status = await lifecycle_manager.get_agent_status("test-agent")
if status:
    print(f"State: {status.current_state.value}")
    print(f"Version: {status.version}")
    print(f"Last modified: {status.last_modified_datetime}")
    
    # For content, still use AgentManager via lifecycle manager
    if lifecycle_manager.agent_manager:
        agent_def = await lifecycle_manager._run_sync_in_executor(
            lifecycle_manager.agent_manager.read_agent,
            "test-agent"
        )
```

### 3. Updating Agents

#### Before

```python
# Manual update process
agent_def = agent_manager.read_agent("test-agent")
if agent_def:
    # Update fields
    agent_def.metadata.version = "2.0.0"
    agent_def.capabilities.append("new-capability")
    
    # Save changes
    updated = agent_manager.update_agent(
        "test-agent",
        {"metadata": agent_def.metadata},
        increment_version=True
    )
    
    # Manual cleanup
    cache.invalidate(f"agent_profile:test-agent:*")
    registry.refresh()
```

#### After

```python
# Streamlined update with tracking
result = await lifecycle_manager.update_agent(
    agent_name="test-agent",
    agent_content=updated_content,
    model_preference="claude-3-opus",
    tags=["updated", "v2"]
)

if result.success:
    print(f"Updated to version: {result.metadata['new_version']}")
    print(f"Modification tracked: {result.modification_id}")
    print(f"Duration: {result.duration_ms}ms")
else:
    print(f"Update failed: {result.error_message}")
```

### 4. Deleting Agents

#### Before

```python
# Direct deletion without backup
success = agent_manager.delete_agent("test-agent")
if success:
    print("Agent deleted")
    # Manual cleanup
    cache.clear_agent("test-agent")
    registry.remove_agent("test-agent")
```

#### After

```python
# Deletion with automatic backup and tracking
result = await lifecycle_manager.delete_agent(
    agent_name="test-agent",
    reason="Deprecated agent"
)

if result.success:
    print(f"Agent deleted with backup: {result.metadata['backup_path']}")
    print(f"All caches cleared: {result.cache_invalidated}")
    print(f"Registry updated: {result.registry_updated}")
    
    # Can restore later if needed
    restore_result = await lifecycle_manager.restore_agent(
        "test-agent",
        backup_path=result.metadata['backup_path']
    )
```

### 5. Listing and Querying Agents

#### Before

```python
# Manual aggregation
all_agents = agent_manager.list_agents()
for name, info in all_agents.items():
    print(f"{name}: {info['version']} ({info['location']})")
```

#### After

```python
# Rich lifecycle information
from claude_mpm.services.agents.deployment import LifecycleState

# List with state filtering
active_agents = await lifecycle_manager.list_agents(
    state_filter=LifecycleState.ACTIVE
)

for agent in active_agents:
    print(f"{agent.agent_name}:")
    print(f"  State: {agent.current_state.value}")
    print(f"  Tier: {agent.tier.value}")
    print(f"  Version: {agent.version}")
    print(f"  Age: {agent.age_days:.1f} days")
    print(f"  Modifications: {len(agent.modifications)}")

# Get comprehensive statistics
stats = await lifecycle_manager.get_lifecycle_stats()
print(f"\nTotal agents: {stats['total_agents']}")
print(f"By state: {stats['agents_by_state']}")
print(f"By tier: {stats['agents_by_tier']}")
print(f"Recent operations: {stats['recent_operations']}")
```

## Error Handling Updates

### Before

```python
try:
    agent_manager.create_agent(name, definition, location)
except FileExistsError:
    print("Agent already exists")
except PermissionError:
    print("No permission to create agent")
except Exception as e:
    print(f"Unknown error: {e}")
```

### After

```python
result = await lifecycle_manager.create_agent(
    agent_name=name,
    agent_content=content,
    tier=tier
)

# All errors captured in result
if not result.success:
    if "already exists" in result.error_message:
        print("Agent already exists")
    elif "permission" in result.error_message.lower():
        print("Permission denied")
    else:
        print(f"Operation failed: {result.error_message}")
        
    # Check operation history for patterns
    history = await lifecycle_manager.get_operation_history(
        agent_name=name,
        limit=10
    )
    failed_ops = [op for op in history if not op.success]
    if len(failed_ops) > 3:
        print("Multiple failures detected, escalating...")
```

## Performance Monitoring

### Before

```python
# Manual timing
import time

start = time.time()
agent_manager.update_agent("test-agent", updates)
duration = time.time() - start
print(f"Update took {duration:.2f} seconds")
```

### After

```python
# Automatic performance tracking
result = await lifecycle_manager.update_agent(
    "test-agent",
    new_content
)

print(f"Operation completed in {result.duration_ms}ms")

# Get aggregated metrics
stats = await lifecycle_manager.get_lifecycle_stats()
metrics = stats['performance_metrics']

print(f"\nPerformance Summary:")
print(f"Total operations: {metrics['total_operations']}")
print(f"Success rate: {metrics['successful_operations'] / metrics['total_operations'] * 100:.1f}%")
print(f"Average duration: {metrics['average_duration_ms']:.1f}ms")

# Operation distribution
if 'operation_distribution' in metrics:
    print(f"\nOperations by type:")
    for op_type, count in metrics['operation_distribution'].items():
        print(f"  {op_type}: {count}")
```

## Testing Updates

### Before

```python
def test_agent_creation():
    manager = AgentManager()
    
    # Create test agent
    definition = create_test_definition()
    path = manager.create_agent("test", definition, "project")
    
    # Verify
    assert path.exists()
    assert manager.read_agent("test") is not None
    
    # Cleanup
    manager.delete_agent("test")
```

### After

```python
import pytest

@pytest.mark.asyncio
async def test_agent_lifecycle():
    manager = AgentLifecycleManager()
    await manager.start()
    
    try:
        # Create with lifecycle tracking
        create_result = await manager.create_agent(
            agent_name="test",
            agent_content="# Test Agent\n\nTest content",
            tier=ModificationTier.PROJECT
        )
        
        assert create_result.success
        assert create_result.cache_invalidated
        assert create_result.registry_updated
        assert create_result.modification_id is not None
        
        # Verify lifecycle state
        status = await manager.get_agent_status("test")
        assert status is not None
        assert status.current_state == LifecycleState.ACTIVE
        assert len(status.modifications) == 1
        
        # Test update
        update_result = await manager.update_agent(
            "test",
            "# Test Agent\n\nUpdated content"
        )
        
        assert update_result.success
        status = await manager.get_agent_status("test")
        assert status.current_state == LifecycleState.MODIFIED
        assert len(status.modifications) == 2
        
        # Test deletion with restore
        delete_result = await manager.delete_agent("test")
        assert delete_result.success
        assert delete_result.metadata.get('backup_path') is not None
        
        # Verify state
        status = await manager.get_agent_status("test")
        assert status.current_state == LifecycleState.DELETED
        
    finally:
        await manager.stop()
```

## Integration with Other Services

### Hook Integration

```python
# Register lifecycle hooks
from claude_mpm.hooks.base_hook import BaseHook, HookContext, HookResult

class AgentCreationHook(BaseHook):
    async def execute(self, context: HookContext) -> HookResult:
        if context.data.get('operation') == 'create_agent':
            agent_name = context.data.get('agent_name')
            # Custom logic for agent creation
            await notify_team(f"New agent created: {agent_name}")
        
        return HookResult(success=True)

# Register with lifecycle manager
lifecycle_manager.register_hook(AgentCreationHook())
```

### Registry Synchronization

```python
# Automatic registry updates
result = await lifecycle_manager.create_agent(...)

# Registry is automatically updated, but you can verify
if lifecycle_manager.agent_registry:
    all_agents = lifecycle_manager.agent_registry.list_agents()
    new_agent = next(
        (a for a in all_agents if a.name == "test-agent"),
        None
    )
    assert new_agent is not None
```

## Common Pitfalls to Avoid

### 1. Mixing Sync and Async

```python
# Wrong: Calling sync method directly
agent_def = lifecycle_manager.agent_manager.read_agent("test")  # Blocks!

# Correct: Use executor wrapper
agent_def = await lifecycle_manager._run_sync_in_executor(
    lifecycle_manager.agent_manager.read_agent,
    "test"
)
```

### 2. Ignoring Operation Results

```python
# Wrong: Not checking result
await lifecycle_manager.create_agent(name, content, tier)
# Assumes success!

# Correct: Always check results
result = await lifecycle_manager.create_agent(name, content, tier)
if not result.success:
    logger.error(f"Failed to create agent: {result.error_message}")
    # Handle error appropriately
```

### 3. Manual Cache/Registry Management

```python
# Wrong: Manual invalidation
await lifecycle_manager.update_agent(name, content)
cache.invalidate(f"agent_profile:{name}:*")  # Redundant!
registry.refresh()  # Redundant!

# Correct: Trust the lifecycle manager
result = await lifecycle_manager.update_agent(name, content)
# Cache and registry automatically updated
```

## Summary

The migration to AgentLifecycleManager provides:

1. **Unified Interface**: Single async API for all agent operations
2. **Automatic Management**: Cache, registry, and tracking handled automatically
3. **Better Error Handling**: Comprehensive result objects with error details
4. **Performance Tracking**: Built-in metrics and operation history
5. **Lifecycle Awareness**: Full visibility into agent states and modifications

By following this guide, you can smoothly transition to the new integrated architecture while gaining additional capabilities for agent lifecycle management.