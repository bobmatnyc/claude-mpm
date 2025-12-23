# Architecture Overview

> **📖 For detailed architecture documentation, see [developer/ARCHITECTURE.md](developer/ARCHITECTURE.md)**

This is a high-level overview of Claude MPM's architecture. For comprehensive technical details, version history, and implementation specifics, refer to the complete architecture documentation in the developer section.

## Quick Reference

Claude MPM is built on a service-oriented architecture with:

- **Service-Oriented Design**: Five specialized service domains
- **Interface-Based Contracts**: Well-defined component interfaces
- **Dependency Injection**: Loose coupling through DI container
- **Lazy Loading**: Deferred resource initialization for performance
- **Hook System**: Event-driven extensibility
- **MCP Integration**: Model Context Protocol support

## Architecture Benefits

- **50-80% Performance Improvement**: Lazy loading and intelligent caching
- **Enhanced Security**: Defense-in-depth with input validation
- **Better Testability**: Interface-based design enables easy mocking
- **Improved Maintainability**: Clear separation of concerns
- **Scalability**: Supports future growth and extensions

## Five Service Domains

### 1. Core Services (`/src/claude_mpm/services/core/`)
Foundation services and interfaces for the entire system.

### 2. Agent Services (`/src/claude_mpm/services/agents/`)
Agent lifecycle, discovery, and management with three-tier precedence (PROJECT > USER > SYSTEM).

### 3. Communication Services (`/src/claude_mpm/services/communication/`)
Real-time communication and event streaming via WebSocket and Socket.IO.

### 4. Project Services (`/src/claude_mpm/services/project/`)
Project analysis and workspace management with automatic stack detection.

### 5. Infrastructure Services (`/src/claude_mpm/services/infrastructure/`)
Cross-cutting concerns including logging, monitoring, and utilities.

## Three-Tier Agent System

Agents are loaded with precedence (highest to lowest):

1. **PROJECT** (`.claude-mpm/agents/`) - Project-specific agents
2. **USER** (`~/.claude-agents/`) - User customizations
3. **SYSTEM** (bundled) - Default agents

This allows project-specific customization while maintaining defaults.

## Key Systems

### Hook System
Event-driven extension points for pre/post tool execution and session lifecycle.

### Memory System
Persistent, project-specific knowledge using KuzuDB graph storage.

### MCP Gateway
Model Context Protocol integration for external tool development.

### Communication Layer
Real-time monitoring via WebSocket with live agent activity tracking.

## Performance Optimizations

**v5.0+ Architecture Improvements:**
- Consolidated cache architecture (`~/.claude-mpm/cache/agents/`)
- Version-aware agent deployment
- ETag-based sync optimization
- 91% latency reduction in hook system (108ms → 10ms)
- Git branch caching with 5-minute TTL
- Non-blocking HTTP fallback
- 50-80% overall performance improvement

## See Also

- **[Developer Architecture](developer/ARCHITECTURE.md)** ⭐ Complete technical architecture
- **[Agent System](AGENTS.md)** - Multi-agent orchestration
- **[User Guide](user/user-guide.md)** - End-user features
- **[Extending](developer/extending.md)** - Building extensions
- **[Service Reference](developer/api-reference.md)** - API documentation

---

**📖 Complete Technical Documentation**: [developer/ARCHITECTURE.md](developer/ARCHITECTURE.md)
