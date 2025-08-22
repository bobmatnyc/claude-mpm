# Memory System Services Documentation

> **Navigation**: [Developer Guide](../README.md) → **Memory System**

This directory contains detailed documentation for the memory system services in Claude MPM.

## Overview

The memory system is organized into several key services that work together to provide persistent agent learning capabilities:

- **Response Handling** - Captures and stores agent interactions for memory extraction
- **Memory Builder** - Processes documentation and generates memory content
- **Memory Router** - Routes memory commands to appropriate agents
- **Memory Optimizer** - Optimizes and maintains memory quality
- **Cache Services** - Provides caching for memory operations

## Service Documentation

### Response Handling

- [Response Handling Architecture](response-handling.md) - Dual-logger system for capturing agent interactions
- [Response Logging Implementation](response-logging.md) - Technical implementation details

### Core Services

- [Memory Builder](builder.md) - Documentation processing and memory generation
- [Memory Router](router.md) - Intelligent routing of memory commands
- [Memory Optimizer](optimizer.md) - Memory optimization and maintenance

### Cache Services

- [Shared Prompt Cache](cache-shared.md) - Shared caching for prompt generation
- [Simple Cache](cache-simple.md) - Basic caching implementation

## Architecture

The memory system follows a modular architecture:

```
Memory System
├── Response Handling (Capture agent interactions)
│   ├── ClaudeSessionLogger (Main interface)
│   └── AsyncSessionLogger (High-performance)
├── Builder (Generate memories from docs)
├── Router (Route commands to agents)
├── Optimizer (Maintain memory quality)
└── Cache (Performance optimization)
```

## Integration Points

The memory services integrate with:

- **Agent System**: For agent-specific memory storage
- **Hook System**: For memory update triggers and response capture
- **CLI Commands**: For user-facing memory operations
- **Project Analyzer**: For contextual memory generation
- **Response Tracking**: For capturing agent interactions and extracting learnings

## Development Guidelines

When working with memory services:

1. **Maintain Service Boundaries**: Each service has a specific responsibility
2. **Use Dependency Injection**: Pass configurations and dependencies explicitly
3. **Follow Documentation Standards**: Document WHY decisions were made
4. **Test Coverage**: Ensure comprehensive unit and integration tests
5. **Performance Considerations**: Use caching appropriately

### Agent Response Format for Memory

When developing agents that need to update memories, use these response fields:

#### Incremental Memory Updates
Use the `remember` field to add new memories to existing lists:

```json
{
  "remember": [
    "Project uses FastAPI for web services",
    "All database migrations go in /migrations/ directory"
  ]
}
```

#### Complete Memory Replacement
Use the `MEMORIES` field to replace entire memory contents:

```json
{
  "MEMORIES": [
    "Complete optimized list of all current memories",
    "Including both existing and new knowledge",
    "Properly deduplicated and organized"
  ]
}
```

#### Memory Capture Criteria
Only include memories that are:
- **Project-Specific**: Information unique to this codebase
- **Not Easily Found**: Knowledge not obvious from docs or code
- **User-Directed**: Explicit user instructions with "remember", "memorize", etc.
- **Implementation-Specific**: Project-specific patterns, constraints, or decisions

#### Example Agent Response
```json
{
  "analysis": "I've implemented the authentication system using JWT tokens...",
  "remember": [
    "Authentication tokens expire after 24 hours",
    "User sessions are stored in Redis cache",
    "Password reset tokens are valid for 1 hour only"
  ]
}
```

## Configuration

Memory services are configured through the main configuration:

```yaml
memory:
  enabled: true
  auto_save: true
  optimization:
    max_size_kb: 50
    min_entries: 5
```

For detailed configuration options, see [MEMORY_CONFIG.md](../MEMORY_CONFIG.md).

## Progress Tracking

For the latest updates on memory system improvements, see [progress.md](progress.md).