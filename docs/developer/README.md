# Claude MPM Developer Documentation

Welcome to the Claude MPM developer documentation. This comprehensive guide covers everything you need to know about developing, extending, and maintaining Claude MPM.

## What is Claude MPM?

Claude MPM (Multi-Agent Project Manager) is a subprocess orchestration layer for Claude that enables:

- **Subprocess Control**: Launch and control Claude as a managed subprocess
- **Multi-Agent Workflows**: Coordinate specialized agents for complex tasks
- **Pattern Detection**: Automatically extract tickets, TODOs, and action items
- **Session Management**: Comprehensive logging and state management
- **Dynamic Framework Injection**: Inject instructions at runtime without static files

## Documentation Structure

### 📐 [01-architecture/](01-architecture/)
Understanding the system design and architecture
- [Architecture Overview](01-architecture/README.md)
- [Subprocess Design](01-architecture/subprocess-design.md)
- [Component Diagram](01-architecture/component-diagram.md)
- [Data Flow](01-architecture/data-flow.md)
- [Design Patterns](01-architecture/patterns.md)

### 🔧 [02-core-components/](02-core-components/)
Deep dive into the main components
- [Component Index](02-core-components/README.md)
- [Orchestrators](02-core-components/orchestrators.md)
- [Agent System](02-core-components/agent-system.md)
- [Ticket Extractor](02-core-components/ticket-extractor.md)
- [Hook Service](02-core-components/hook-service.md)

### 💻 [03-development/](03-development/)
Setting up and developing Claude MPM
- [Development Guide](03-development/README.md)
- [Setup Instructions](03-development/setup.md)
- [Coding Standards](03-development/coding-standards.md)
- [Testing Guide](03-development/testing.md)
- [Debugging Tips](03-development/debugging.md)

### 📚 [04-api-reference/](04-api-reference/)
Complete API documentation
- [API Index](04-api-reference/README.md)
- [Core API](04-api-reference/core-api.md)
- [Orchestration API](04-api-reference/orchestration-api.md)
- [Services API](04-api-reference/services-api.md)
- [Utils API](04-api-reference/utils-api.md)

### 🔌 [05-extending/](05-extending/)
Extending Claude MPM with custom components
- [Extension Guide](05-extending/README.md)
- [Custom Orchestrators](05-extending/custom-orchestrators.md)
- [Custom Hooks](05-extending/custom-hooks.md)
- [Custom Services](05-extending/custom-services.md)
- [Plugin Development](05-extending/plugins.md)

### 🔍 [06-internals/](06-internals/)
Internal implementation details
- [Internal Documentation](06-internals/README.md)
- [Subprocess Logging](06-internals/subprocess-logging.md)
- [Migration Guides](06-internals/migrations/)
- [Codebase Analysis](06-internals/analysis/)

## Quick Start for Developers

### 1. Clone and Setup
```bash
git clone https://github.com/your-repo/claude-mpm.git
cd claude-mpm
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### 2. Run Tests
```bash
# Quick E2E tests
./scripts/run_e2e_tests.sh

# Full test suite
./scripts/run_all_tests.sh
```

### 3. Understand the Architecture
Start with the [Architecture Overview](01-architecture/README.md) to understand how Claude MPM works internally.

### 4. Explore Components
Review the [Core Components](02-core-components/README.md) to understand the building blocks.

### 5. Set Up Development
Follow the [Development Setup](03-development/setup.md) guide for a complete development environment.

## Key Concepts

### Subprocess Orchestration
Claude MPM runs Claude as a subprocess using `subprocess.Popen`, providing full control over:
- Input/output streams
- Process lifecycle
- Resource monitoring
- Pattern detection

### Agent System
Multiple specialized agents handle different aspects:
- **Engineer Agent**: Code implementation
- **QA Agent**: Testing and quality assurance
- **Documentation Agent**: Documentation creation
- **Research Agent**: Code analysis and exploration
- **Security Agent**: Security reviews
- And more...

### Hook System
Extensible architecture through pre/post hooks:
- Message interception
- Response transformation
- Custom automation
- Third-party integrations

## Contributing

Before contributing, please:
1. Read the [Coding Standards](03-development/coding-standards.md)
2. Set up your [Development Environment](03-development/setup.md)
3. Run the [Test Suite](03-development/testing.md)
4. Review the [API Documentation](04-api-reference/)

## Getting Help

- 📖 Start with this documentation
- 🐛 Report issues on GitHub
- 💬 Join discussions in the community
- 📧 Contact maintainers for urgent issues

## Version Information

This documentation is for Claude MPM version 1.0+. For migration from claude-multiagent-pm, see the [migration guide](../user/differences-from-claude-multiagent-pm.md).