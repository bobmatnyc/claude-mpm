# Claude MPM Architecture Overview

Claude MPM implements a sophisticated subprocess orchestration architecture that fundamentally differs from traditional file-based Claude configuration approaches. This document provides a comprehensive overview of the system architecture.

## Core Architecture Principles

### 1. Subprocess Control, Not File Configuration

Unlike traditional CLAUDE.md approaches, Claude MPM launches Claude as a **managed subprocess**:

```
┌─────────────┐       ┌─────────────────┐       ┌──────────────┐
│   Terminal  │──────▶│   Claude MPM    │──────▶│    Claude    │
│   (User)    │       │  (Orchestrator) │       │ (Subprocess) │
└─────────────┘       └─────────────────┘       └──────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
              ┌─────▼─────┐    ┌─────▼─────┐
              │  Pattern   │    │   Agent   │
              │ Detection  │    │ Delegator │
              └───────────┘    └───────────┘
```

### 2. Real-time I/O Interception

All input and output streams are intercepted in real-time:
- User input is processed before reaching Claude
- Claude's output is analyzed for patterns
- Actions are triggered based on detected patterns

### 3. Dynamic Framework Injection

Framework instructions are injected at runtime:
- No static CLAUDE.md files required
- Instructions can be modified dynamically
- Context-aware prompt engineering

### 4. Multi-Agent Orchestration

The system orchestrates multiple specialized agents:
- Agents run as separate subprocesses
- Parallel execution for efficiency
- Results aggregation and synthesis

## System Layers

### 1. CLI Layer
**Location**: `src/claude_mpm/cli/` (modular structure with commands)

The entry point that:
- Parses command-line arguments
- Initializes the orchestrator
- Manages the main event loop

### 2. Orchestration Layer
**Location**: `src/claude_mpm/orchestration/`

Multiple orchestrator implementations:
- **SubprocessOrchestrator**: Direct subprocess control
- **SystemPromptOrchestrator**: Uses --system-prompt flag
- **AgentDelegatorOrchestrator**: Handles multi-agent delegation
- **InteractiveSubprocessOrchestrator**: Interactive mode with resource monitoring

### 3. Core Services Layer
**Location**: `src/claude_mpm/services/`

Business logic services:
- **HookService**: Manages extensibility hooks
- **AgentService**: Agent lifecycle management
- **SessionLogger**: Comprehensive logging

### 4. Agent System
**Location**: `src/claude_mpm/agents/`

Specialized agents for different tasks:
- Engineer, QA, Documentation agents
- Research, Security, Operations agents
- Custom agent support via templates

### 5. Utility Layer
**Location**: `src/claude_mpm/utils/`

Shared utilities:
- **SubprocessUtils**: Safe subprocess execution
- **FileUtils**: Atomic file operations
- **LoggerMixin**: Consistent logging
- **PathResolver**: Path resolution

## Key Components Interaction

### Startup Sequence

```python
1. CLI parses arguments
2. ClaudeLauncher initialized
3. Framework instructions loaded
4. Orchestrator selected based on mode
5. Hook service started (if enabled)
6. Claude subprocess launched
7. I/O streams connected
8. Main event loop begins
```

### Message Flow

```python
1. User types message
2. Pre-message hooks execute
3. Framework instructions injected
4. Message sent to Claude subprocess
5. Claude processes and responds
6. Response intercepted
7. Pattern detection runs
8. Post-message hooks execute
9. Actions triggered (tickets, delegations)
10. Response shown to user
```

### Agent Delegation Flow

```python
1. PM (orchestrator) detects delegation pattern
2. Agent type identified from pattern
3. Agent subprocess created
4. Context and task provided to agent
5. Agent executes task
6. Results captured and formatted
7. Results integrated into main session
8. User sees consolidated response
```

## Design Patterns Used

### 1. Strategy Pattern
Different orchestrator implementations for various use cases

### 2. Observer Pattern
Hook system for extensibility

### 3. Factory Pattern
Agent creation and orchestrator selection

### 4. Decorator Pattern
LoggerMixin for consistent logging

### 5. Adapter Pattern
Integration with external systems (AI-Trackdown)

## Memory and Resource Management

### Process Isolation
- Each agent runs in separate process
- Memory limits enforced per process
- Automatic cleanup on completion

### Parallel Execution
- ThreadPoolExecutor for concurrent agents
- Configurable parallelism limits
- Resource monitoring and throttling

### State Management
- Session state maintained in orchestrator
- Agent results cached
- Cleanup on session end

## Security Considerations

### Process Isolation
- Agents cannot access parent process memory
- Limited environment variable exposure
- Controlled file system access

### Input Validation
- Command injection prevention
- Path traversal protection
- Safe subprocess argument handling

### Output Sanitization
- Escape sequences handled
- Binary data filtered
- Size limits enforced

## Performance Optimizations

### Lazy Loading
- Agents loaded on demand
- Framework instructions cached
- Minimal startup overhead

### Stream Processing
- Non-blocking I/O operations
- Efficient pattern matching
- Batched ticket creation

### Resource Pooling
- Reusable subprocess components
- Connection pooling for services
- Cached agent templates

## Extension Points

### 1. Custom Orchestrators
Implement `BaseOrchestrator` for new strategies

### 2. Hook System
Pre/post message hooks for custom behavior

### 3. Agent Templates
Add new agent types via markdown templates

### 4. Pattern Detectors
Custom pattern detection for new ticket types

### 5. Service Plugins
Additional services for new functionality

## Next Steps

- Review [Subprocess Design](subprocess-design.md) for implementation details
- See [Component Diagram](component-diagram.md) for visual architecture
- Explore [Data Flow](data-flow.md) for detailed message routing
- Study [Design Patterns](patterns.md) for pattern implementations
- Read [Agent Management Integration](agent-management-integration.md) for the unified agent lifecycle architecture