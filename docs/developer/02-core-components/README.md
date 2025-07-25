# Core Components

This section provides detailed documentation on the core components that make up Claude MPM. Each component is designed with specific responsibilities and clear interfaces to ensure modularity and maintainability.

## Component Overview

Claude MPM's core components work together to provide subprocess orchestration, multi-agent coordination, and extensible automation capabilities.

### Component Categories

1. **Orchestrators** - Manage Claude subprocess lifecycle and I/O
2. **Agent System** - Coordinate specialized AI agents
3. **Ticket Extractor** - Detect and create actionable items
4. **Hook Service** - Provide extensibility points
5. **Core Services** - Supporting infrastructure

## Component Architecture

```
┌──────────────────────────────────────────────────┐
│                  User Interface                   │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────┐
│                 Orchestrators                     │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │ Subprocess  │ │System Prompt│ │Interactive │ │
│  └─────────────┘ └─────────────┘ └────────────┘ │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────┐
│                Core Services                      │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │Claude       │ │Agent        │ │Framework   │ │
│  │Launcher     │ │Registry     │ │Loader      │ │
│  └─────────────┘ └─────────────┘ └────────────┘ │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────┐
│              Feature Services                     │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │Ticket       │ │Hook         │ │Session     │ │
│  │Extractor    │ │Service      │ │Logger      │ │
│  └─────────────┘ └─────────────┘ └────────────┘ │
└──────────────────────────────────────────────────┘
```

## Component Documentation

### [Orchestrators](orchestrators.md)
The heart of Claude MPM - managing subprocess creation, I/O streams, and process lifecycle.

**Key Classes**:
- `BaseOrchestrator` - Abstract base for all orchestrators
- `SubprocessOrchestrator` - Direct subprocess control
- `SystemPromptOrchestrator` - Uses --system-prompt flag
- `InteractiveSubprocessOrchestrator` - Enhanced interactive mode

### [Agent System](agent-system.md)
Multi-agent coordination for specialized task execution.

**Key Components**:
- `AgentRegistry` - Dynamic agent discovery
- `Agent Templates` - Specialized agent definitions
- `AgentExecutor` - Parallel agent execution
- `ResultAggregator` - Combine agent outputs

### [Ticket Extractor](ticket-extractor.md)
Pattern detection and automatic ticket creation.

**Key Features**:
- Pattern matching for TODO, BUG, FEATURE
- AI-Trackdown integration
- Duplicate detection
- Session-based tracking

### [Hook Service](hook-service.md)
Extensibility through event-driven hooks.

**Hook Types**:
- Pre-message hooks
- Post-message hooks
- Error hooks
- Session lifecycle hooks

## Component Interactions

### Initialization Flow

```python
# 1. Create core services
launcher = ClaudeLauncher(config)
registry = AgentRegistry()
loader = FrameworkLoader()

# 2. Create orchestrator with dependencies
orchestrator = SubprocessOrchestrator(
    launcher=launcher,
    registry=registry,
    loader=loader
)

# 3. Initialize feature services
hook_service = HookService()
ticket_extractor = TicketExtractor()
session_logger = SessionLogger()

# 4. Wire everything together
orchestrator.add_service(hook_service)
orchestrator.add_service(ticket_extractor)
orchestrator.add_service(session_logger)

# 5. Start the system
orchestrator.start()
```

### Message Processing Pipeline

```python
def process_message(message: str) -> str:
    # 1. Pre-processing hooks
    message = hook_service.execute_pre_hooks(message)
    
    # 2. Framework injection
    message = loader.inject_framework(message)
    
    # 3. Send to Claude
    orchestrator.send_message(message)
    
    # 4. Receive response
    response = orchestrator.receive_output()
    
    # 5. Pattern detection
    patterns = ticket_extractor.extract_patterns(response)
    
    # 6. Execute actions
    for pattern in patterns:
        if pattern.type == 'delegation':
            agent_executor.execute(pattern)
        elif pattern.type == 'ticket':
            ticket_extractor.create_ticket(pattern)
    
    # 7. Post-processing hooks
    response = hook_service.execute_post_hooks(response)
    
    return response
```

## Component Lifecycle

### Component States

```
┌─────────┐     ┌──────────────┐     ┌─────────┐
│ Created │────▶│ Initialized  │────▶│ Active  │
└─────────┘     └──────────────┘     └────┬────┘
                                          │
                                          ▼
┌─────────┐     ┌──────────────┐     ┌─────────┐
│Destroyed│◀────│   Stopping   │◀────│ Paused  │
└─────────┘     └──────────────┘     └─────────┘
```

### Lifecycle Management

```python
class Component:
    def __init__(self):
        self.state = 'created'
    
    def initialize(self):
        """Initialize component resources"""
        self.validate_configuration()
        self.setup_resources()
        self.state = 'initialized'
    
    def start(self):
        """Start component operation"""
        if self.state != 'initialized':
            raise InvalidStateError()
        self.state = 'active'
    
    def pause(self):
        """Pause component operation"""
        if self.state == 'active':
            self.state = 'paused'
    
    def stop(self):
        """Stop component and cleanup"""
        self.state = 'stopping'
        self.cleanup_resources()
        self.state = 'destroyed'
```

## Component Configuration

### Configuration Sources

1. **Environment Variables**
   ```bash
   CLAUDE_MPM_ORCHESTRATOR=subprocess
   CLAUDE_MPM_MAX_AGENTS=4
   CLAUDE_MPM_HOOK_PORT=8080
   ```

2. **Configuration Files**
   ```yaml
   # config.yaml
   orchestrator:
     type: subprocess
     timeout: 300
   agents:
     max_parallel: 4
     timeout: 300
   hooks:
     enabled: true
     port: 8080
   ```

3. **Command Line Arguments**
   ```bash
   claude-mpm --orchestrator subprocess --max-agents 4
   ```

### Configuration Priority

```
Command Line > Environment Variables > Config Files > Defaults
```

## Component Testing

### Unit Testing Components

```python
# Test individual component
def test_orchestrator():
    orchestrator = MockOrchestrator()
    orchestrator.start()
    
    orchestrator.send_message("test")
    response = orchestrator.receive_output()
    
    assert response == "mock response"
    orchestrator.stop()
```

### Integration Testing

```python
# Test component interactions
def test_component_integration():
    # Create components
    launcher = ClaudeLauncher(test_config)
    orchestrator = SubprocessOrchestrator(launcher)
    extractor = TicketExtractor()
    
    # Wire together
    orchestrator.add_pattern_handler(extractor)
    
    # Test flow
    orchestrator.start()
    orchestrator.send_message("TODO: Test integration")
    
    # Verify ticket created
    tickets = extractor.get_tickets()
    assert len(tickets) == 1
    assert tickets[0].type == "TODO"
```

## Component Monitoring

### Health Checks

```python
class ComponentHealth:
    def check_orchestrator(self) -> HealthStatus:
        return HealthStatus(
            healthy=orchestrator.is_running(),
            details={
                'process_alive': orchestrator.process.poll() is None,
                'responsive': orchestrator.ping(),
                'memory_usage': orchestrator.get_memory_usage()
            }
        )
    
    def check_all_components(self) -> Dict[str, HealthStatus]:
        return {
            'orchestrator': self.check_orchestrator(),
            'agent_registry': self.check_agent_registry(),
            'hook_service': self.check_hook_service(),
            'ticket_extractor': self.check_ticket_extractor()
        }
```

### Performance Metrics

```python
class ComponentMetrics:
    def __init__(self):
        self.metrics = {
            'orchestrator': {
                'messages_sent': 0,
                'messages_received': 0,
                'average_response_time': 0
            },
            'agents': {
                'total_executed': 0,
                'average_execution_time': 0,
                'failure_rate': 0
            },
            'tickets': {
                'total_created': 0,
                'by_type': {'TODO': 0, 'BUG': 0, 'FEATURE': 0}
            }
        }
```

## Best Practices

### 1. Component Independence
- Components should not directly depend on each other
- Use dependency injection for required services
- Communicate through well-defined interfaces

### 2. Error Handling
- Each component handles its own errors
- Propagate critical errors up the chain
- Log all errors with context

### 3. Resource Management
- Components manage their own resources
- Clean up in stop() method
- Use context managers where appropriate

### 4. Testing
- Unit test each component in isolation
- Integration test component interactions
- Mock external dependencies

### 5. Documentation
- Document component interfaces
- Provide usage examples
- Keep documentation up to date

## Next Steps

- Review individual component documentation:
  - [Orchestrators](orchestrators.md) - Subprocess management
  - [Agent System](agent-system.md) - Multi-agent coordination
  - [Ticket Extractor](ticket-extractor.md) - Pattern detection
  - [Hook Service](hook-service.md) - Extensibility
  
- See [API Reference](../04-api-reference/) for detailed API documentation
- Check [Extending Claude MPM](../05-extending/) for customization options