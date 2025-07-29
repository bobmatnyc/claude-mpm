# Agent Management Developer Guide

This guide explains the agent management architecture and how to work with agents in Claude MPM.

## Architecture Overview

The agent management system follows a clear separation of concerns with two main components:

### 1. AgentManager (Content Layer)

**Purpose**: Handles all agent content operations

**Responsibilities**:
- **CRUD Operations**: Create, Read, Update, Delete agent files
- **Markdown Processing**: Parse and generate agent markdown with frontmatter
- **Section Management**: Extract and update individual agent sections
- **Version Control**: Manage agent versions and metadata

**Key Characteristics**:
- Synchronous API
- File-system focused
- Content-aware parsing
- No external service dependencies

### 2. AgentLifecycleManager (Orchestration Layer)

**Purpose**: Orchestrates complete agent lifecycle with tracking and integration

**Responsibilities**:
- **Lifecycle Management**: Track agent states (Active, Modified, Deleted)
- **Service Coordination**: Integrate multiple services for complete operations
- **Performance Tracking**: Monitor operation metrics and history
- **Async Operations**: Provide non-blocking API for all operations

**Key Characteristics**:
- Asynchronous API
- Service orchestration
- Comprehensive tracking
- Automatic cache/registry management

## When to Use Each Component

### Use AgentLifecycleManager (Recommended)

The AgentLifecycleManager should be your primary interface for agent operations:

```python
# Recommended approach
lifecycle_manager = AgentLifecycleManager()
await lifecycle_manager.start()

# All operations through lifecycle manager
result = await lifecycle_manager.create_agent(
    agent_name="my-agent",
    agent_content=content,
    tier=ModificationTier.PROJECT
)
```

**Use cases**:
- Creating new agents with full tracking
- Updating agents with version management
- Deleting agents with automatic backups
- Querying agent status and history
- Monitoring agent operations

### Use AgentManager Directly (Special Cases)

Direct AgentManager usage should be limited to specific scenarios:

```python
# Special case: Bulk content analysis
agent_manager = AgentManager()

# Read multiple agents for analysis
for agent_name in agent_list:
    agent_def = agent_manager.read_agent(agent_name)
    if agent_def:
        analyze_capabilities(agent_def.capabilities)
```

**Valid use cases**:
- Bulk read operations for analysis
- Content migration scripts
- Testing agent parsing logic
- Tools that only need content access

## Code Examples

### Basic Agent Operations

```python
import asyncio
from claude_mpm.services.agent_lifecycle_manager import (
    AgentLifecycleManager,
    ModificationTier,
    LifecycleState
)

async def manage_agents():
    # Initialize lifecycle manager
    manager = AgentLifecycleManager()
    await manager.start()
    
    try:
        # Create an agent
        result = await manager.create_agent(
            agent_name="data-validator",
            agent_content="""# Data Validator Agent

## Primary Role
Validate data integrity and format compliance.

## Capabilities
- Schema validation
- Format checking
- Data cleansing
""",
            tier=ModificationTier.PROJECT,
            agent_type="validation",
            author="data-team"
        )
        
        if result.success:
            print(f"Agent created: {result.agent_name}")
            print(f"Location: {result.metadata['file_path']}")
        else:
            print(f"Failed: {result.error_message}")
            return
        
        # Update the agent
        result = await manager.update_agent(
            agent_name="data-validator",
            agent_content="""# Data Validator Agent v2

## Primary Role
Validate data integrity with enhanced error reporting.

## Capabilities
- Schema validation with detailed errors
- Multiple format support
- Data cleansing and transformation
- Validation report generation
"""
        )
        
        # Check agent status
        status = await manager.get_agent_status("data-validator")
        print(f"\nAgent Status:")
        print(f"  State: {status.current_state.value}")
        print(f"  Version: {status.version}")
        print(f"  Modifications: {len(status.modifications)}")
        
    finally:
        await manager.stop()

# Run the example
asyncio.run(manage_agents())
```

### Advanced Lifecycle Management

```python
async def advanced_lifecycle_example():
    manager = AgentLifecycleManager({
        "enable_auto_backup": True,
        "enable_cache_invalidation": True
    })
    await manager.start()
    
    try:
        # List all agents by state
        active_agents = await manager.list_agents(
            state_filter=LifecycleState.ACTIVE
        )
        print(f"Active agents: {len(active_agents)}")
        
        # Get operation history
        history = await manager.get_operation_history(limit=10)
        for op in history:
            print(f"{op.operation.value} on {op.agent_name}: "
                  f"{op.duration_ms:.1f}ms")
        
        # Get comprehensive statistics
        stats = await manager.get_lifecycle_stats()
        print(f"\nSystem Statistics:")
        print(f"  Total agents: {stats['total_agents']}")
        print(f"  By state: {stats['agents_by_state']}")
        print(f"  By tier: {stats['agents_by_tier']}")
        
        metrics = stats['performance_metrics']
        print(f"\nPerformance Metrics:")
        print(f"  Operations: {metrics['total_operations']}")
        print(f"  Success rate: "
              f"{metrics['successful_operations']/metrics['total_operations']*100:.1f}%")
        print(f"  Avg duration: {metrics['average_duration_ms']:.1f}ms")
        
    finally:
        await manager.stop()
```

### Integration with Other Services

```python
async def integrated_agent_workflow():
    # Services work together automatically
    manager = AgentLifecycleManager()
    await manager.start()
    
    # Create agent - automatically:
    # - Tracks in modification tracker
    # - Invalidates cache entries
    # - Updates agent registry
    # - Creates lifecycle record
    result = await manager.create_agent(
        agent_name="integrated-agent",
        agent_content=content,
        tier=ModificationTier.USER
    )
    
    # The lifecycle manager handles all integrations
    print(f"Cache invalidated: {result.cache_invalidated}")
    print(f"Registry updated: {result.registry_updated}")
    print(f"Modification tracked: {result.modification_id}")
    
    await manager.stop()
```

## Best Practices

### 1. Service Lifecycle Management

```python
# Always use proper lifecycle management
manager = AgentLifecycleManager()
try:
    await manager.start()
    # Your operations here
finally:
    await manager.stop()

# Or use context manager (if implemented)
async with AgentLifecycleManager() as manager:
    # Your operations here
    pass
```

### 2. Error Handling

```python
# Always check operation results
result = await manager.create_agent(...)

if not result.success:
    # Log the error
    logger.error(f"Failed to create agent: {result.error_message}")
    
    # Check for specific errors
    if "already exists" in result.error_message:
        # Handle duplicate
        pass
    elif "permission" in result.error_message.lower():
        # Handle permission issue
        pass
    else:
        # Generic error handling
        raise Exception(f"Agent operation failed: {result.error_message}")
```

### 3. Metadata Management

```python
# Include rich metadata for tracking
result = await manager.create_agent(
    agent_name="tracked-agent",
    agent_content=content,
    tier=ModificationTier.PROJECT,
    # Metadata for tracking
    author="team-name",
    jira_ticket="PROJ-123",
    tags=["feature-x", "experimental"],
    specializations=["data-processing", "validation"],
    # Custom metadata
    reviewed_by="senior-dev",
    deployment_target="production"
)
```

### 4. Performance Monitoring

```python
# Monitor performance regularly
async def monitor_performance():
    stats = await manager.get_lifecycle_stats()
    metrics = stats['performance_metrics']
    
    # Set up alerts
    if metrics['average_duration_ms'] > 1000:
        alert("Slow agent operations detected")
    
    if metrics['failed_operations'] > metrics['successful_operations'] * 0.1:
        alert("High failure rate detected")
    
    # Track trends
    if 'operation_distribution' in metrics:
        most_common = max(
            metrics['operation_distribution'].items(),
            key=lambda x: x[1]
        )
        print(f"Most common operation: {most_common[0]}")
```

## Common Patterns

### Agent Migration

```python
async def migrate_agent_tier(agent_name: str, from_tier: ModificationTier, to_tier: ModificationTier):
    manager = AgentLifecycleManager()
    await manager.start()
    
    try:
        # Read current content
        if manager.agent_manager:
            agent_def = await manager._run_sync_in_executor(
                manager.agent_manager.read_agent,
                agent_name
            )
            
            if not agent_def:
                print(f"Agent {agent_name} not found")
                return
            
            # Delete from old location
            delete_result = await manager.delete_agent(agent_name)
            if not delete_result.success:
                print(f"Failed to delete: {delete_result.error_message}")
                return
            
            # Create in new location
            create_result = await manager.create_agent(
                agent_name=agent_name,
                agent_content=agent_def.raw_content,
                tier=to_tier,
                migrated_from=from_tier.value
            )
            
            if create_result.success:
                print(f"Agent migrated from {from_tier.value} to {to_tier.value}")
            else:
                # Restore from backup if migration failed
                await manager.restore_agent(agent_name)
                
    finally:
        await manager.stop()
```

### Batch Validation

```python
async def validate_all_agents():
    manager = AgentLifecycleManager()
    await manager.start()
    
    validation_results = []
    
    try:
        all_agents = await manager.list_agents()
        
        for agent_record in all_agents:
            # Validate each agent
            if manager.agent_manager:
                agent_def = await manager._run_sync_in_executor(
                    manager.agent_manager.read_agent,
                    agent_record.agent_name
                )
                
                if agent_def:
                    # Perform validation
                    errors = validate_agent_definition(agent_def)
                    if errors:
                        validation_results.append({
                            "agent": agent_record.agent_name,
                            "errors": errors
                        })
        
        # Report results
        if validation_results:
            print(f"Validation errors found in {len(validation_results)} agents")
            for result in validation_results:
                print(f"  {result['agent']}: {result['errors']}")
        else:
            print("All agents validated successfully")
            
    finally:
        await manager.stop()
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```python
   # Wrong
   from claude_mpm.services import AgentLifecycleManager  # Won't work
   
   # Correct
   from claude_mpm.services.agent_lifecycle_manager import AgentLifecycleManager
   ```

2. **Sync/Async Mismatch**
   ```python
   # Wrong - blocks event loop
   manager.agent_manager.read_agent("test")  
   
   # Correct - use executor
   await manager._run_sync_in_executor(
       manager.agent_manager.read_agent,
       "test"
   )
   ```

3. **Missing Service Start**
   ```python
   # Wrong - services not initialized
   manager = AgentLifecycleManager()
   result = await manager.create_agent(...)  # Will fail
   
   # Correct - start services first
   manager = AgentLifecycleManager()
   await manager.start()
   result = await manager.create_agent(...)
   ```

## Summary

The agent management system provides:

1. **Clear Architecture**: Separation between content (AgentManager) and lifecycle (AgentLifecycleManager)
2. **Unified Interface**: AgentLifecycleManager as the primary API for all operations
3. **Comprehensive Tracking**: Every operation is tracked with full history
4. **Automatic Integration**: Cache, registry, and tracking handled automatically
5. **Robust Error Handling**: All operations return detailed result objects
6. **Performance Monitoring**: Built-in metrics and statistics

For most use cases, use the AgentLifecycleManager for all agent operations to ensure proper tracking, caching, and integration with the Claude MPM ecosystem.