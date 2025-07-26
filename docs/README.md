# Claude MPM Documentation

Welcome to the Claude MPM documentation. This comprehensive guide helps users and developers understand, use, and extend Claude MPM effectively.

## Core Documentation

Essential documentation for all users:

- 📋 **[STRUCTURE.md](STRUCTURE.md)** - Project file organization and structure
- 🧪 **[QA.md](QA.md)** - Testing procedures and quality assurance
- 🚀 **[DEPLOY.md](DEPLOY.md)** - Deployment and release process
- 📊 **[LOGGING.md](LOGGING.md)** - Comprehensive logging guide
- 🔢 **[VERSIONING.md](VERSIONING.md)** - Version management and conventions

## Documentation by Role

### 📚 [User Documentation](user/)
Everything you need to use Claude MPM effectively:
- **[01. Getting Started](user/01-getting-started/)** - Installation, first run, core concepts
- **[02. Guides](user/02-guides/)** - Step-by-step guides for common workflows
- **[03. Features](user/03-features/)** - Deep dives into Claude MPM features
- **[04. Reference](user/04-reference/)** - CLI commands, configuration, troubleshooting
- **[05. Migration](user/05-migration/)** - Migration from claude-multiagent-pm

### 🔧 [Developer Documentation](developer/)
Technical documentation for contributors and developers:
- **[01. Architecture](developer/01-architecture/)** - System design and patterns
- **[02. Core Components](developer/02-core-components/)** - Component deep dives
- **[03. Development](developer/03-development/)** - Setup, coding standards, testing
- **[04. API Reference](developer/04-api-reference/)** - Complete API documentation
- **[05. Extending](developer/05-extending/)** - Custom components and plugins
- **[06. Internals](developer/06-internals/)** - Implementation details

### 🎨 [Design Documentation](design/)
Architecture decisions and technical designs:
- [Hook System Design](design/comprehensive-hooks-guide.md)
- [Claude Code Integration](design/claude-code-hooks-technical-impelmentatin-guide.md)
- [MPM Command Interception](design/MPM_COMMAND_INTERCEPTION.md)
- [Slash Commands Design](design/slash_command_python_design.md)

### 📋 [Miscellaneous](misc/)
Additional project information:
- [Project Summary](misc/SUMMARY.md)
- [Hook Integration Summary](misc/HOOK_INTEGRATION_SUMMARY.md)
- [Agent Roles Summary](misc/agent_roles_summary.md)

### 📦 [Archive](archive/)
Historical and deprecated documentation:
- [Archive Index](archive/README.md)
- [Test Results](archive/test-results/)

## Quick Start Guide

### 🚀 New Users
1. **Install Claude MPM**: Follow the [Installation Guide](user/01-getting-started/installation.md)
2. **First Run**: Learn the basics with [First Run Guide](user/01-getting-started/first-run.md)
3. **Core Concepts**: Understand [Key Concepts](user/01-getting-started/concepts.md)
4. **Basic Usage**: Try [Basic Commands](user/02-guides/basic-usage.md)

### 💻 Developers
1. **Setup**: Start with [Development Setup](developer/03-development/setup.md)
2. **Architecture**: Review [Architecture Overview](developer/01-architecture/README.md)
3. **Testing**: Follow [Testing Guidelines](QA.md)
4. **Contributing**: Check [Coding Standards](developer/03-development/coding-standards.md)

### 🔍 Finding What You Need

**By Task:**
- **Installing**: [User Installation](user/01-getting-started/installation.md) | [Dev Setup](developer/03-development/setup.md)
- **Using Claude MPM**: [Basic Usage](user/02-guides/basic-usage.md) | [Interactive Mode](user/02-guides/interactive-mode.md)
- **Troubleshooting**: [Troubleshooting Guide](user/04-reference/troubleshooting.md) | [Debugging](developer/03-development/debugging.md)
- **Extending**: [Custom Hooks](developer/05-extending/custom-hooks.md) | [Plugins](developer/05-extending/plugins.md)

**By Topic:**
- **Commands**: [CLI Reference](user/04-reference/cli-commands.md)
- **Configuration**: [Configuration Guide](user/04-reference/configuration.md)
- **APIs**: [API Reference](developer/04-api-reference/README.md)
- **Testing**: [QA Guide](QA.md) | [Testing Guide](developer/03-development/testing.md)
- **Deployment**: [Deployment Process](DEPLOY.md)
- **Logging**: [Logging System](LOGGING.md)

## Documentation Standards

When contributing to documentation:
- Keep documentation synchronized with code changes
- Use clear, concise language appropriate for the target audience
- Include practical examples and code snippets
- Cross-reference related documents
- Move outdated content to the [archive](archive/) directory

## Additional Resources

- **Project Repository**: [GitHub](https://github.com/yourusername/claude-mpm)
- **Issue Tracker**: [GitHub Issues](https://github.com/yourusername/claude-mpm/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/claude-mpm/discussions)

---

*Documentation for Claude MPM v1.0.1*