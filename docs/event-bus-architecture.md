# Event Bus Architecture Design

## Current Architecture Problems

### 1. Tight Coupling
- **Hook Handler → Socket.IO**: Direct dependency on Socket.IO client
- **Multiple Emitters**: Various components trying to emit events independently
- **Hard Dependencies**: Components fail if Socket.IO is unavailable
- **Testing Difficulty**: Can't test event producers without Socket.IO server

### 2. Connection Management Issues
- **Multiple Connections**: Each component manages its own Socket.IO connection
- **Connection Pooling Complexity**: Complex pooling logic in hook_handler.py
- **Circuit Breaker Pattern**: Implemented at individual component level
- **Resource Waste**: Multiple connections to same Socket.IO server

### 3. Event Flow Problems
- **No Central Event Stream**: Events scattered across multiple components
- **Inconsistent Event Format**: Different components format events differently
- **Lost Events**: Events lost when Socket.IO is down
- **No Event History**: Can't replay or inspect past events

### 4. Maintainability Issues
- **Scattered Logic**: Event emission logic across multiple files
- **Difficult Debugging**: Hard to trace event flow
- **No Metrics**: Can't monitor event throughput or failures
- **Complex Error Handling**: Each component handles errors differently

## Proposed Event Bus Architecture

### Core Design Principles

1. **Decoupling**: Producers don't know about consumers
2. **Reliability**: In-memory queue with optional persistence
3. **Performance**: Minimal overhead, async processing
4. **Flexibility**: Easy to add/remove producers and consumers
5. **Observability**: Built-in metrics and debugging

### Architecture Overview

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Event Producers │     │    Event Bus     │     │  Event Consumers │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ • Hook Handler   │────▶│ • In-Memory Queue│────▶│ • Socket.IO      │
│ • CLI Commands   │     │ • Topic Routing  │     │ • Logger         │
│ • System Events  │     │ • Filtering      │     │ • Metrics        │
│ • Agent Events   │     │ • Transformation │     │ • File Writer    │
│ • Build Monitor  │     │ • Error Handling │     │ • Debugger       │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

### Component Responsibilities

#### Event Bus (Core)
- Manages event subscriptions
- Routes events to consumers
- Handles backpressure
- Provides metrics
- Optional persistence

#### Event Producers
- Publish events without knowing consumers
- Fire-and-forget pattern
- No error handling required

#### Event Consumers
- Subscribe to event topics/patterns
- Process events asynchronously
- Handle their own errors
- Can filter/transform events

### Event Format

```python
@dataclass
class Event:
    id: str                    # Unique event ID
    topic: str                 # Event topic (e.g., "hook.response")
    type: str                  # Event type (e.g., "AssistantResponse")
    timestamp: datetime        # When event was created
    source: str               # Who created the event
    data: Dict[str, Any]      # Event payload
    metadata: Dict[str, Any]  # Additional metadata
    correlation_id: Optional[str]  # For tracking related events
```

### Topic Hierarchy

Events organized in hierarchical topics:
- `hook.*` - Hook system events
- `hook.response` - Assistant responses
- `hook.tool` - Tool usage events
- `cli.*` - CLI command events
- `system.*` - System events
- `agent.*` - Agent events
- `build.*` - Build monitoring events

### Consumer Types

1. **Synchronous Consumers**: Process events immediately
2. **Asynchronous Consumers**: Process events in background
3. **Batch Consumers**: Process events in batches
4. **Filtered Consumers**: Only receive matching events

### Error Handling

- Consumers handle their own errors
- Failed consumers don't affect others
- Optional dead letter queue
- Configurable retry policies

### Benefits

1. **Decoupling**: Components independent
2. **Reliability**: Events queued when consumers down
3. **Testability**: Easy to test with mock bus
4. **Extensibility**: Easy to add new producers/consumers
5. **Debugging**: Central place to monitor events
6. **Performance**: Async processing, batching
7. **Flexibility**: Multiple consumer patterns

## Implementation Plan

### Phase 1: Core Event Bus
- Create EventBus class with basic pub/sub
- Implement topic-based routing
- Add async event processing
- Create Event dataclass

### Phase 2: Socket.IO Consumer
- Create SocketIOConsumer class
- Subscribe to all events
- Maintain single Socket.IO connection
- Handle connection failures gracefully

### Phase 3: Hook Integration
- Update hook_handler to use EventBus
- Remove direct Socket.IO dependency
- Simplify connection management

### Phase 4: Additional Consumers
- Add LoggingConsumer for debugging
- Add MetricsConsumer for monitoring
- Add FileConsumer for persistence

### Phase 5: Advanced Features
- Add event filtering
- Add event transformation
- Add dead letter queue
- Add event replay capability

## Migration Strategy

1. **Parallel Operation**: Run EventBus alongside existing system
2. **Gradual Migration**: Move components one by one
3. **Backward Compatibility**: Keep existing interfaces working
4. **Testing**: Comprehensive tests at each stage
5. **Monitoring**: Track metrics during migration

## Success Metrics

- **Decoupling**: Zero direct Socket.IO dependencies in producers
- **Reliability**: <0.01% event loss rate
- **Performance**: <1ms publish latency
- **Testability**: 100% unit test coverage
- **Maintainability**: Single place for event logic