# Developer Documentation

Technical documentation for Claude MPM contributors and extenders.

## Documentation Structure

### Core Documentation

- **[Architecture](ARCHITECTURE.md)** - System design, core concepts, and service architecture
- **[Extending](extending.md)** - Build custom agents, hooks, services, and MCP tools
- **[Skills Versioning System](skills-versioning.md)** - Technical implementation details
- **[API Reference](api-reference.md)** - Complete API documentation for all services
- **[Integrating Structured Questions](integrating-structured-questions.md)** - Add structured questions to custom agents

### Development Guides

- **[Agent Modification Workflow](agent-modification-workflow.md)** - How to modify and contribute agents
- **[Code Formatting](CODE_FORMATTING.md)** - Code style and formatting standards
- **[Publishing Guide](publishing-guide.md)** - Release and publishing procedures
- **[Pre-publish Checklist](pre-publish-checklist.md)** - Pre-release verification checklist

### Technical Deep Dives

- **[Code Navigation](code-navigation/)** - Detailed codebase navigation guides
- **[Internals](internals/)** - Internal implementation details and mechanisms
- **[Troubleshooting](troubleshooting/)** - Development troubleshooting guides
- **[Testing](testing/)** - Testing framework, evaluation system, and QA processes

## Quick Links

**New to the codebase?**
1. Read [Architecture](architecture.md) → Understand system design
2. Browse [API Reference](api-reference.md) → Learn service interfaces
3. Explore [Extending](extending.md) → Build extensions

**Common Tasks:**
- Understand architecture: [Architecture - System Design](architecture.md#system-design)
- Create custom agent: [Extending - Custom Agents](extending.md#custom-agents)
- Add service: [Extending - Custom Services](extending.md#custom-services)
- Create hook: [Extending - Custom Hooks](extending.md#custom-hooks)
- Build MCP tool: [Extending - MCP Tools](extending.md#mcp-tools)

**Development Setup:**

```bash
# Clone and install
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm
pip install -e ".[dev,monitor]"

# Run tests
make test

# Run quality checks
make quality

# Fix linting issues
make lint-fix
```

## Architecture Overview

**Service-Oriented Design**: Five specialized domains

1. **Core Services**: Fundamental system operations
2. **Agent Services**: Agent lifecycle and management
3. **Orchestration Services**: Multi-agent coordination
4. **MCP Services**: External tool integration
5. **Utility Services**: Supporting functionality

**Key Concepts:**

- **Three-Tier Agent System**: PROJECT > USER > SYSTEM hierarchy
- **Hook System**: Event-driven pre/post execution hooks
- **Memory System**: Persistent project-specific knowledge
- **Service Contracts**: Clear interfaces between components

## Contributing

**Development Workflow:**

1. Fork and clone repository
2. Create feature branch
3. Make changes with tests
4. Run quality checks: `make quality`
5. Submit pull request

**Code Standards:**

- Python 3.11+ compatibility
- Type hints required
- Docstrings for public APIs
- Tests for new features
- Linting with ruff
- Formatting with black

**Testing:**

```bash
# Run all tests
make test

# Run specific test
pytest tests/test_specific.py

# Run with coverage
make test-coverage
```

## Resources

- **Source Code**: https://github.com/bobmatnyc/claude-mpm
- **Issue Tracker**: https://github.com/bobmatnyc/claude-mpm/issues
- **User Documentation**: [../user/README.md](../user/README.md)
- **Agent Documentation**: [../agents/README.md](../agents/README.md)
