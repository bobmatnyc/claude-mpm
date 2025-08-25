# Claude MPM User Documentation

Welcome to the Claude MPM user documentation. This guide will help you understand and use Claude MPM effectively.

## What is Claude MPM?

Claude MPM (Multi-Agent Project Manager) is a framework for Claude that enhances your AI assistant with:

- **Multi-agent workflows** - Delegates tasks to specialized agents
- **Hook system** - Extensible architecture for customization
- **Session management** - Comprehensive logging and history
- **Service architecture** - Clean separation of business logic

## Documentation Structure

### [01. Getting Started](01-getting-started/README.md)
New to Claude MPM? Start here to get up and running quickly.
- Installation guide
- First run tutorial
- Core concepts

### [02. Guides](02-guides/README.md)
Step-by-step guides for common tasks and workflows.
- Basic usage patterns
- Interactive mode usage
- Agent system usage

### [03. Features](03-features/README.md)
Deep dives into Claude MPM's features.
- Agent delegation system
- Hook system
- Session logging
- Service architecture

### [04. Reference](04-reference/README.md)
Technical reference and troubleshooting.
- CLI command reference
- Configuration options
- Troubleshooting guide

### [05. Migration](05-migration/README.md)
Migrating from other tools or versions.
- From claude-multiagent-pm
- Version migration guides

## Quick Start

```bash
# Install Claude MPM
git clone https://github.com/yourusername/claude-mpm.git
cd claude-mpm
./install_dev.sh

# Activate virtual environment
source venv/bin/activate

# Run your first command
claude-mpm run -i "Hello, Claude!" --non-interactive
```

## Key Differences from claude-multiagent-pm

Claude MPM is a fork that uses **subprocess orchestration** instead of CLAUDE.md files:

- No CLAUDE.md files needed in your projects
- Framework instructions are injected dynamically
- Full process control and monitoring
- Automatic ticket extraction
- Comprehensive session logging

## Getting Help

- Check the [Troubleshooting Guide](04-reference/troubleshooting.md)
- Review [Common Issues](04-reference/troubleshooting.md#common-issues)
- See the [FAQ](04-reference/troubleshooting.md#faq)

## Contributing

Claude MPM is open source. To contribute:
1. Read the [Developer Documentation](../developer/README.md)
2. Check the [Project Structure](../developer/STRUCTURE.md)
3. Follow the [QA Guidelines](../developer/QA.md)

## Related Documentation

- **[Developer Documentation](../developer/README.md)** - Architecture, APIs, development guides
- **[Agent Documentation](../agents/README.md)** - Creating and managing agents
- **[Reference Documentation](../reference/README.md)** - Technical references and deployment
- **[Main Documentation Hub](../README.md)** - Complete navigation guide