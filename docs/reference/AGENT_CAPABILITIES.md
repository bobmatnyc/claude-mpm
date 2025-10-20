# Agent Capabilities Reference

**Version**: 4.10.0
**Last Updated**: 2025-10-20

Complete reference documentation for all Claude MPM agent capabilities, routing configurations, and integration details.

---

## Table of Contents

- [Coding Agents](#coding-agents)
- [Routing Configuration](#routing-configuration)
- [Memory Integration](#memory-integration)
- [Quality Standards](#quality-standards)
- [Integration Patterns](#integration-patterns)

---

## Coding Agents

Comprehensive capabilities for all 8 coding agents.

### Python Engineer v2.0.0

**Agent ID**: `python-engineer`
**Version**: v2.0.0
**Model**: Sonnet
**Category**: Engineering
**Status**: ✅ Production

#### Core Capabilities

| Capability | Details |
|------------|---------|
| **Python Version** | 3.13+ with JIT compiler |
| **Architecture** | ABC interfaces, DI containers, SOLID principles |
| **Async Support** | AsyncIO, async/await patterns |
| **Type Safety** | mypy, type hints, Pydantic validation |
| **Testing** | pytest, unittest, 85%+ coverage |
| **Performance** | Profiling, caching, optimization |
| **Frameworks** | FastAPI, Django, Flask |

#### Routing Configuration

```yaml
keywords:
  - python
  - fastapi
  - django
  - async
  - asyncio
  - service-oriented
  - dependency-injection

file_patterns:
  - "*.py"
  - "**/*.py"
  - "pyproject.toml"
  - "requirements.txt"
  - "setup.py"

path_patterns:
  - "/api/"
  - "/services/"
  - "/models/"

priority: 100
```

#### Memory Routing Rules

Stores:
- Implementation patterns (e.g., DI containers, service patterns)
- Architecture decisions (e.g., SOA vs monolith)
- Performance optimizations (e.g., caching strategies)
- Testing strategies (e.g., pytest patterns)
- Python-specific best practices

#### Example Delegation

```
User: "I need a service-oriented Python application with FastAPI"
PM: Task(agent="python-engineer",
         task="Implement service-oriented Python application with:
               - ABC interfaces for services
               - DI container for dependencies
               - Async patterns for I/O
               - Type hints throughout
               - Comprehensive pytest tests")
```

#### Quality Checklist

- [ ] Python 3.13+ features used
- [ ] Type hints on all public interfaces
- [ ] Black formatting applied
- [ ] PEP 8 compliance
- [ ] Async/await for I/O operations
- [ ] 85%+ test coverage
- [ ] Error handling comprehensive

---

### TypeScript Engineer v2.0.0

**Agent ID**: `typescript-engineer`
**Version**: v2.0.0
**Model**: Sonnet
**Category**: Engineering
**Status**: ✅ Production

#### Core Capabilities

| Capability | Details |
|------------|---------|
| **TypeScript Version** | 5.6+ with strict mode |
| **Type System** | Branded types, discriminated unions, conditional types |
| **Build Tools** | Vite, Bun, esbuild, SWC |
| **Testing** | Vitest, Playwright |
| **Frameworks** | React, Vue, Next.js integration |
| **Performance** | Web Workers, optimization |
| **Functional** | FP patterns with TS |

#### Routing Configuration

```yaml
keywords:
  - typescript
  - type-safe
  - branded-types
  - discriminated-unions
  - strict-mode

file_patterns:
  - "*.ts"
  - "*.tsx"
  - "**/*.ts"
  - "**/*.tsx"
  - "tsconfig.json"

path_patterns:
  - "/src/"
  - "/lib/"
  - "/types/"

priority: 100
```

#### Memory Routing Rules

Stores:
- TypeScript patterns (branded types, discriminated unions)
- Build tool configurations (Vite, Bun settings)
- Performance optimizations (Web Workers, lazy loading)
- Modern development strategies

#### Example Delegation

```
User: "Build a type-safe API client with branded types"
PM: Task(agent="typescript-engineer",
         task="Implement type-safe API client with:
               - Branded types for IDs
               - Discriminated unions for responses
               - Result types for error handling
               - Type-safe fetch wrapper")
```

---

### Next.js Engineer v2.0.0

**Agent ID**: `nextjs-engineer`
**Version**: v2.0.0
**Model**: Sonnet
**Category**: Engineering
**Status**: ✅ Production

#### Core Capabilities

| Capability | Details |
|------------|---------|
| **Next.js Version** | 15 with App Router |
| **Architecture** | Server/Client Components |
| **Data Fetching** | SSR, SSG, ISR |
| **Mutations** | Server Actions |
| **Performance** | Image/font optimization |
| **TypeScript** | Full TS integration |
| **Deployment** | Vercel, self-hosted, Docker |

#### Routing Configuration

```yaml
keywords:
  - nextjs
  - next.js
  - app-router
  - server-components
  - server-actions

file_patterns:
  - "next.config.*"
  - "app/**/*.tsx"
  - "app/**/*.ts"

path_patterns:
  - "/app/"
  - "/components/"
  - "/lib/"

priority: 100
```

#### Memory Routing Rules

Stores:
- Next.js 15 patterns (App Router, Server Components)
- TypeScript implementations
- Performance optimizations
- Modern web development strategies

---

### Go Engineer v1.0.0 🆕

**Agent ID**: `go-engineer`
**Version**: v1.0.0
**Model**: Sonnet
**Category**: Engineering
**Status**: ✅ Production

#### Core Capabilities

| Capability | Details |
|------------|---------|
| **Go Version** | 1.24+ |
| **Concurrency** | Goroutines, channels, context |
| **Architecture** | Clean architecture, hexagonal |
| **Testing** | Table-driven, race detection |
| **APIs** | HTTP servers, gRPC, WebSocket |
| **Performance** | Profiling, benchmarking |
| **Deployment** | Docker, Kubernetes |

#### Routing Configuration

```yaml
keywords:
  - go
  - golang
  - goroutines
  - channels
  - concurrency
  - microservices

file_patterns:
  - "*.go"
  - "go.mod"
  - "go.sum"

path_patterns:
  - "/cmd/"
  - "/internal/"
  - "/pkg/"

priority: 100
```

#### Memory Routing Rules

Stores:
- Concurrency patterns (goroutines, channels)
- Context management strategies
- Microservices architectures
- Performance optimizations

---

### Java Engineer v1.0.0 🆕

**Agent ID**: `java-engineer`
**Version**: v1.0.0
**Model**: Sonnet
**Category**: Engineering
**Status**: ✅ Production

#### Core Capabilities

| Capability | Details |
|------------|---------|
| **Java Version** | 21 LTS |
| **Spring Boot** | 3.x with auto-configuration |
| **Architecture** | Hexagonal, clean architecture, DDD, CQRS |
| **Concurrency** | Virtual threads, CompletableFuture, reactive |
| **Testing** | JUnit 5, Mockito, AssertJ, TestContainers |
| **Build Tools** | Maven 4.x, Gradle 8.x |
| **Performance** | G1GC, ZGC, JFR, JMH benchmarking |

#### Routing Configuration

```yaml
keywords:
  - java
  - java-21
  - spring
  - spring-boot
  - maven
  - gradle
  - junit
  - junit5
  - virtual-threads
  - enterprise
  - microservices
  - jvm

file_patterns:
  - "*.java"
  - "pom.xml"
  - "build.gradle"
  - "build.gradle.kts"

path_patterns:
  - "/src/main/java/"
  - "/src/test/java/"
  - "/src/"

priority: 100
```

#### Memory Routing Rules

Stores:
- Java 21 LTS features (virtual threads, pattern matching, sealed classes)
- Spring Boot 3.x patterns and configurations
- Hexagonal and clean architecture implementations
- Concurrency patterns (virtual threads, CompletableFuture, reactive streams)
- Performance optimization techniques (JVM tuning, profiling)
- Testing strategies (JUnit 5, Mockito, TestContainers)

#### Example Delegation

```
User: "I need a Spring Boot REST API with virtual threads"
PM: Task(agent="java-engineer",
         task="Implement Spring Boot REST API with:
               - Java 21 virtual threads for concurrency
               - Constructor injection
               - Hexagonal architecture (domain, application, infrastructure)
               - JUnit 5 and Mockito tests
               - TestContainers for integration tests")
```

#### Quality Checklist

- [ ] Java 21 LTS features used (virtual threads, pattern matching)
- [ ] Constructor injection in Spring components
- [ ] Try-with-resources for AutoCloseable
- [ ] Explicit @Transactional boundaries
- [ ] 90%+ test coverage with JUnit 5
- [ ] Static analysis passed (SonarQube, SpotBugs)
- [ ] Performance profiled (JFR/JMC)

---

### Rust Engineer v1.0.0 🆕

**Agent ID**: `rust-engineer`
**Version**: v1.0.0
**Model**: Sonnet
**Category**: Engineering
**Status**: ✅ Production

#### Core Capabilities

| Capability | Details |
|------------|---------|
| **Rust Edition** | 2024 |
| **Memory Safety** | Ownership, borrowing, lifetimes |
| **Performance** | Zero-cost abstractions |
| **Concurrency** | Fearless concurrency |
| **WebAssembly** | WASM compilation |
| **Testing** | Cargo test, property-based |
| **Ecosystem** | Tokio, Actix, Rocket |

#### Routing Configuration

```yaml
keywords:
  - rust
  - wasm
  - webassembly
  - systems-programming
  - memory-safety

file_patterns:
  - "*.rs"
  - "Cargo.toml"
  - "Cargo.lock"

path_patterns:
  - "/src/"
  - "/tests/"

priority: 100
```

#### Memory Routing Rules

Stores:
- Ownership patterns
- Lifetime management strategies
- WebAssembly optimizations
- Zero-cost abstraction patterns

---

### PHP Engineer v2.0.0

**Agent ID**: `php-engineer`
**Version**: v2.0.0
**Model**: Sonnet
**Category**: Engineering
**Status**: ✅ Production

#### Core Capabilities

| Capability | Details |
|------------|---------|
| **PHP Version** | 8.4-8.5 |
| **Frameworks** | Laravel 12+, Symfony 7+ |
| **Architecture** | DDD, CQRS, hexagonal |
| **Type Safety** | Strict types, PHPStan/Psalm |
| **Testing** | PHPUnit, Pest |
| **Deployment** | DigitalOcean, Docker, K8s |
| **Performance** | OPcache optimization |

#### Routing Configuration

```yaml
keywords:
  - php
  - laravel
  - symfony
  - ddd
  - cqrs

file_patterns:
  - "*.php"
  - "composer.json"
  - "composer.lock"

path_patterns:
  - "/app/"
  - "/src/"

priority: 100
```

#### Memory Routing Rules

Stores:
- Modern PHP patterns (8.4+ features)
- Laravel/Symfony best practices
- DDD/CQRS architectures
- Performance optimizations

---

### Ruby Engineer v2.0.0

**Agent ID**: `ruby-engineer`
**Version**: v2.0.0
**Model**: Sonnet
**Category**: Engineering
**Status**: ✅ Production

#### Core Capabilities

| Capability | Details |
|------------|---------|
| **Ruby Version** | 3.4 with YJIT |
| **Rails Version** | 8 |
| **Architecture** | Service objects, PORO |
| **Testing** | RSpec with coverage |
| **Performance** | YJIT optimization |
| **Background** | Sidekiq, Good Job |
| **Deployment** | Heroku, Fly.io, Docker |

#### Routing Configuration

```yaml
keywords:
  - ruby
  - rails
  - rspec
  - service-objects
  - yjit

file_patterns:
  - "*.rb"
  - "Gemfile"
  - "Gemfile.lock"

path_patterns:
  - "/app/"
  - "/spec/"
  - "/lib/"

priority: 100
```

#### Memory Routing Rules

Stores:
- Ruby patterns (service objects, PORO)
- Rails 8 architectures
- RSpec testing strategies
- YJIT performance optimizations

---

## Routing Configuration

### Priority System

Agents are selected based on priority scores:

| Priority | Meaning | Use Cases |
|----------|---------|-----------|
| 100 | High priority | Language-specific agents |
| 75 | Medium-high | Specialized sub-domains |
| 50 | Medium | General-purpose agents |
| 25 | Low | Fallback agents |

### Routing Algorithm

```python
def select_agent(context):
    """Select best agent based on context"""
    scores = {}

    for agent in agents:
        score = 0

        # Keyword matching
        for keyword in agent.keywords:
            if keyword in context.lower():
                score += 10

        # File pattern matching
        for pattern in agent.file_patterns:
            if matches_pattern(context.files, pattern):
                score += 20

        # Path pattern matching
        for pattern in agent.path_patterns:
            if matches_path(context.working_dir, pattern):
                score += 15

        # Apply priority multiplier
        scores[agent.id] = score * agent.priority

    return max(scores, key=scores.get)
```

### Multi-Agent Scenarios

When multiple agents could handle a task:

1. **Python + TypeScript**: Use both for full-stack
2. **Next.js + TypeScript**: Next.js for framework, TypeScript for utilities
3. **Go + Rust**: Go for services, Rust for performance-critical
4. **Ruby + TypeScript**: Rails backend, TS frontend

---

## Memory Integration

### Memory Storage Structure

```
.claude-mpm/memories/
├── python_engineer.md
├── typescript_engineer.md
├── nextjs_engineer.md
├── go_engineer.md
├── rust_engineer.md
├── php_engineer.md
└── ruby_engineer.md
```

### Memory Update Triggers

Memory updates occur when:

- User says "remember", "don't forget"
- Agent discovers important pattern
- Architectural decision is made
- Performance optimization is found
- Bug pattern is identified

### Memory Categories

Each agent stores memories in categories:

1. **Implementation Patterns**: Code patterns and structures
2. **Architecture Decisions**: High-level design choices
3. **Performance Optimizations**: Speed/efficiency improvements
4. **Testing Strategies**: Test approaches and patterns
5. **Common Mistakes**: Anti-patterns to avoid

---

## Quality Standards

### Universal Standards (All Agents)

- Search-first methodology
- Code conciseness (minimize LOC)
- 85%+ test coverage
- Comprehensive documentation
- Error handling patterns
- Performance considerations

### Language-Specific Standards

#### Python
- PEP 8 + Black formatting
- Type hints on public APIs
- Async for I/O operations

#### TypeScript
- Strict mode enabled
- No implicit any
- Branded types for domains

#### Next.js
- App Router architecture
- Server Components default
- TypeScript throughout

#### Go
- gofmt formatting
- Explicit error handling
- Context management

#### Rust
- Clippy-clean code
- Comprehensive error handling
- Property-based tests

#### PHP
- PSR-12 standard
- Strict types enabled
- PHPStan level 8+

#### Ruby
- RuboCop compliance
- Service object patterns
- Comprehensive RSpec

---

## Integration Patterns

### Agent Handoffs

Agents collaborate through handoffs:

```
Research → Code Analyzer → [Coding Agent] → QA → Documentation
```

### Example Full Workflow

```
1. Research Agent: Analyzes requirements
2. Code Analyzer: Reviews proposed solution
3. Python Engineer: Implements FastAPI service
4. QA Agent: Tests implementation
5. Documentation Agent: Updates API docs
```

### Cross-Agent Communication

Agents share context through:

- Structured task descriptions
- Memory system
- File artifacts
- Test results
- Documentation

---

## Further Reading

- [Coding Agents Catalog](CODING_AGENTS.md)
- [Agent Deployment Log](AGENT_DEPLOYMENT_LOG.md)
- [Agent Testing Guide](../developer/AGENT_TESTING.md)
- [Agent Development](../developer/07-agent-system/creation-guide.md)

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-17
**Maintained By**: Claude MPM Team
