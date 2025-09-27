# 💻 Claude MPM Developer Guide

**Complete developer documentation for contributing to and extending Claude MPM**
**Version 4.3.3** | Last Updated: September 19, 2025

Welcome to the Claude MPM developer documentation! This comprehensive guide covers everything you need to know for developing, contributing to, and extending Claude MPM.

## 🚀 Quick Development Setup

### Prerequisites
- **Python 3.8+** (3.11+ recommended)
- **Git** for version control
- **Node.js 16+** (for dashboard development)
- **Claude Code** for testing integration

### 1-Minute Setup
```bash
# Clone and setup
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Complete development setup (recommended)
make dev-complete

# Or step-by-step:
make setup-dev          # Install in development mode
make setup-pre-commit   # Set up automated code formatting
```

### Quality-First Workflow
```bash
# Daily development commands (use these frequently!)
make lint-fix           # Auto-fix formatting, imports, and simple issues
make quality            # Run all quality checks before commits
make safe-release-build # Complete quality gate + build process
```

**💡 Pro Tip**: Run `make lint-fix` frequently during development - it's safe and keeps code clean!

## 📖 Developer Documentation Structure

### 🎯 By Development Focus

| Focus Area | Start Here | Key Resources |
|------------|------------|---------------|
| **New Contributors** | [Contributing Guide](03-development/README.md) | [Architecture](ARCHITECTURE.md), [Testing](TESTING.md) |
| **Service Development** | [Service Guide](SERVICES.md) | [API Reference](../API.md), [Performance](PERFORMANCE.md) |
| **Agent Creation** | [Agent System](07-agent-system/README.md) | [Creation Guide](07-agent-system/creation-guide.md), [Schema](10-schemas/SCHEMA_REFERENCE.md) |
| **Dashboard/UI** | [Dashboard Guide](11-dashboard/README.md) | [Frontend](03-development/frontend.md), [Config](11-dashboard/CONFIG_WINDOW_V2.md) |
| **MCP Integration** | [MCP Gateway](13-mcp-gateway/README.md) | [Tool Development](13-mcp-gateway/tool-development.md), [API](04-api-reference/mcp-gateway-api.md) |

### 🔧 System Architecture & Core Concepts

#### 🏗️ System Design
- **[Architecture Overview](ARCHITECTURE.md)** - Service-oriented design with 5 domains
- **[Service Layer Guide](SERVICES.md)** - Service development patterns and interfaces
- **[Unified Configuration](02-core-components/UNIFIED_CONFIGURATION.md)** - Consolidated config system with 99.9% performance improvement
- **[Performance Guide](PERFORMANCE.md)** - Caching, optimization, and 50-80% improvements
- **[Security Framework](../reference/SECURITY.md)** - Multi-layered security and validation

#### 📊 Agent & Memory Systems
- **[Agent Development](07-agent-system/AGENT_DEVELOPMENT.md)** - Complete agent creation guide
- **[Memory System](08-memory-system/MEMORY_SYSTEM.md)** - Agent learning and persistence
- **[Response System](12-responses/README.md)** - Response handling and processing
- **[Schema Reference](10-schemas/SCHEMA_REFERENCE.md)** - Agent and memory schemas

### 🛠️ Development Workflow

#### 🚀 Getting Started
- **[Development Setup](03-development/setup.md)** - Environment configuration
- **[Contributing Guide](03-development/README.md)** - How to contribute effectively
- **[Testing Strategy](TESTING.md)** - Unit, integration, and E2E testing
- **[Code Quality](LINTING.md)** - Automated formatting and quality checks

#### 🔌 Extending Claude MPM
- **[MCP Gateway](13-mcp-gateway/README.md)** - Model Context Protocol integration
- **[Custom Hooks](05-extending/hooks.md)** - Extensibility through hooks
- **[Plugin Architecture](05-extending/plugins.md)** - Plugin development patterns
- **[Agent Extensions](05-extending/agents.md)** - Extending agent capabilities

### 📱 User Interface & Monitoring

#### 📊 Dashboard Development
- **[Dashboard Overview](11-dashboard/README.md)** - Real-time monitoring interface
- **[Frontend Development](03-development/frontend.md)** - React/Next.js development
- **[Config Interface](11-dashboard/CONFIG_WINDOW_V2.md)** - Configuration management UI
- **[WebSocket API](../user/websocket-api.md)** - Real-time communication protocol

#### 🔍 Monitoring & Observability
- **[Logging System](02-core-components/logging.md)** - Structured logging and tracing
- **[Metrics Collection](02-core-components/metrics.md)** - Performance and usage metrics
- **[Error Handling](02-core-components/error-handling.md)** - Error management patterns
- **[Debugging Tools](03-development/debugging.md)** - Development and production debugging

### 🔐 Security & Operations

#### 🛡️ Security Framework
- **[Security Guide](09-security/SECURITY.md)** - Multi-layered security architecture
- **[Agent Security](09-security/agent_schema_security_notes.md)** - Agent-specific security measures
- **[Input Validation](09-security/validation.md)** - Comprehensive input sanitization
- **[Path Security](09-security/path-security.md)** - Filesystem protection patterns

#### 🚀 Operations & Deployment
- **[Deployment Guide](../DEPLOYMENT.md)** - Release and deployment procedures
- **[Version Management](../reference/VERSIONING.md)** - Semantic versioning strategy
- **[CI/CD Pipeline](03-development/cicd.md)** - Automated quality and deployment
- **[Performance Monitoring](02-core-components/performance.md)** - Production monitoring

## 🏗️ Architecture Highlights (v4.3.3)

### Service-Oriented Design
- **5 Specialized Domains**: Agent, Communication, Core, Infrastructure, Project services
- **Interface-Based Contracts**: All services implement explicit interfaces
- **Dependency Injection**: Service container with automatic resolution
- **Performance Optimized**: 50-80% improvement through caching and lazy loading

### Agent System Features
- **Three-Tier Hierarchy**: PROJECT > USER > SYSTEM precedence
- **15+ Specialized Agents**: Engineer, QA, Documentation, Security, Research, etc.
- **Dynamic Discovery**: Real-time capability detection and routing
- **Memory Integration**: Persistent learning across sessions
- **Multiple Formats**: Markdown, JSON, YAML support

### Security Framework
- **Multi-Layered Protection**: Input validation, path restrictions, RBAC
- **Agent Security**: Role-based access control and capability limits
- **Audit Trails**: Complete activity logging and monitoring
- **Secure Operations**: Filesystem protection and PID validation

## 🛠️ Common Development Tasks

### 🤖 Creating a Custom Agent

```bash
# 1. Create project agent directory
mkdir -p .claude-mpm/agents

# 2. Create agent with frontmatter
cat > .claude-mpm/agents/custom_qa.md << 'EOF'
---
description: Custom QA agent for this project
version: 2.0.0
tools: ["Read", "Grep", "Bash", "Edit"]
model: claude-sonnet-4-20250514
priority: high
---

# Custom QA Agent

Specialized testing and quality assurance for this project.

## Expertise
- Project-specific test patterns
- Custom assertion libraries
- Performance testing workflows

## Testing Strategy
...
EOF

# 3. Verify deployment
claude-mpm agents list --by-tier
```

### 🧠 Setting Up Memory System

```bash
# Initialize agent memory
claude-mpm memory init

# Build from project documentation
claude-mpm memory build --docs ./docs

# Check memory status
claude-mpm memory status

# Optimize memories (remove duplicates)
claude-mpm memory optimize --all
```

### 🔧 Service Development Pattern

```python
# 1. Define interface
from abc import ABC, abstractmethod

class IMyService(ABC):
    @abstractmethod
    async def process_data(self, data: dict) -> dict:
        pass

# 2. Implement service
from claude_mpm.services.core.base import BaseService

class MyService(BaseService, IMyService):
    def __init__(self, dependency: IDependency):
        super().__init__("MyService")
        self.dependency = dependency

    async def initialize(self) -> bool:
        # Service initialization
        return True

    async def process_data(self, data: dict) -> dict:
        # Implementation
        return {"processed": True}

# 3. Register in container
from claude_mpm.services.core.container import ServiceContainer
container = ServiceContainer()
container.register(IMyService, MyService, singleton=True)
```

### 🧪 Testing Best Practices

```bash
# Run quality checks before commits
make quality

# Auto-fix formatting issues
make lint-fix

# Run comprehensive test suite
make test

# Performance and integration tests
make test-integration

# Check test coverage
make coverage
```

### 📊 Dashboard Development

```bash
# Start development dashboard
cd src/claude_mpm/dashboard
npm install
npm run dev

# Test with monitoring
claude-mpm run --monitor --port 8766

# Build for production
npm run build
```

## 🎯 Development Workflows

### 📝 Feature Development Workflow

1. **Setup**: `make dev-complete` for complete development environment
2. **Code**: Implement feature following service-oriented patterns
3. **Quality**: `make lint-fix` → `make quality` to maintain standards
4. **Test**: Write comprehensive tests (unit, integration, E2E)
5. **Document**: Update relevant documentation
6. **Review**: Submit PR following [Contributing Guidelines](03-development/README.md)

### 🔍 Debugging Workflow

1. **Enable Verbose Logging**:
   ```bash
   claude-mpm run --verbose --monitor
   ```
2. **Check Service Health**:
   ```bash
   claude-mpm doctor --verbose
   ```
3. **Monitor Real-Time**: Use dashboard at http://localhost:8765
4. **Review Logs**: Check `~/.claude-mpm/logs/` for detailed traces
5. **Test Isolation**: Use `--non-interactive` for focused testing

### 🚀 Release Workflow

1. **Quality Gate**: `make quality` must pass
2. **Version Management**: Use [semantic versioning](../reference/VERSIONING.md)
3. **Build & Test**: `make safe-release-build`
4. **Documentation**: Update version references to current
5. **Deploy**: Follow [Deployment Guide](../DEPLOYMENT.md)

## 🧑‍💻 Contributing Guidelines

### Code Quality Standards

| Aspect | Requirement | Tool/Command |
|--------|-------------|--------------|
| **Formatting** | Black + isort | `make lint-fix` |
| **Linting** | Ruff + Flake8 | `make quality` |
| **Type Checking** | mypy compliance | `make quality` |
| **Testing** | 85%+ coverage | `make test` |
| **Documentation** | Comprehensive docstrings | Manual review |

### Development Principles

1. **Service-Oriented**: Use interface-based design patterns
2. **Performance-First**: Implement caching and lazy loading
3. **Security-Aware**: Follow security framework guidelines
4. **Test-Driven**: Write tests before implementation
5. **Documentation-Complete**: Document all public APIs

### Pull Request Process

1. **Follow Quality Workflow**: `make lint-fix` → `make quality` → `make test`
2. **Update Documentation**: Keep docs current with changes
3. **Add Tests**: Ensure comprehensive test coverage
4. **Version Compatibility**: Check for breaking changes
5. **Review Security**: Follow security guidelines

## 📚 Learning Path for New Contributors

### Week 1: Foundation
- [ ] Read [Architecture Overview](ARCHITECTURE.md)
- [ ] Complete [Development Setup](03-development/setup.md)
- [ ] Run through [Contributing Guide](03-development/README.md)
- [ ] Create first agent following [Agent Development](07-agent-system/AGENT_DEVELOPMENT.md)

### Week 2: Development
- [ ] Study [Service Development](SERVICES.md) patterns
- [ ] Understand [Testing Strategy](TESTING.md)
- [ ] Explore [Memory System](08-memory-system/MEMORY_SYSTEM.md)
- [ ] Practice with [Quality Workflow](#quality-first-workflow)

### Week 3: Advanced Topics
- [ ] Learn [Security Framework](09-security/SECURITY.md)
- [ ] Study [Performance Optimization](PERFORMANCE.md)
- [ ] Explore [MCP Gateway](13-mcp-gateway/README.md)
- [ ] Contribute first feature or bug fix

## 🆘 Developer Support

### Quick Troubleshooting

| Issue | Solution | Documentation |
|-------|----------|---------------|
| **Import errors** | Check PYTHONPATH and venv | [Setup Guide](03-development/setup.md) |
| **Quality checks fail** | Run `make lint-fix` first | [Code Quality](LINTING.md) |
| **Tests not passing** | Check test environment setup | [Testing Guide](TESTING.md) |
| **Service resolution errors** | Verify container registration | [Service Guide](SERVICES.md) |

### Getting Help

1. **📖 [Troubleshooting](../TROUBLESHOOTING.md)** - Comprehensive problem-solving
2. **🤝 [Contributing Guide](03-development/README.md)** - How to contribute effectively
3. **🐛 [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)** - Technical support
4. **📚 [Documentation Hub](../README.md)** - Complete documentation navigation

## 🔗 Related Documentation

- **📚 [Documentation Hub](../README.md)** - Master navigation center
- **👥 [User Guide](../user/README.md)** - User-facing documentation
- **🤖 [Agent System](../AGENTS.md)** - Agent development guide
- **🚀 [Deployment](../DEPLOYMENT.md)** - Operations and deployment
- **📊 [API Reference](../API.md)** - Complete API documentation

---

**💡 Developer Tip**: Start with the [Contributing Guide](03-development/README.md) and [Architecture Overview](ARCHITECTURE.md) to understand the system design, then dive into specific areas based on your interests and contributions!