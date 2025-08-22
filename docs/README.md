# Documentation

Welcome to the Claude MPM documentation. This directory contains comprehensive guides for users, developers, and administrators.

## Quick Navigation

### For Users
- **[User Guide](./user/)** - Complete user documentation
- **[Quick Start](../QUICKSTART.md)** - Get started in 5 minutes
- **[Memory System](./MEMORY.md)** - Agent memory and learning
- **[Project Agents](./PROJECT_AGENTS.md)** - Local agent deployment
- **[MCP Setup](./MCP_SETUP.md)** - Complete MCP Gateway configuration guide

### For Developers
- **[Developer Guide](./developer/)** - Architecture, APIs, and development
- **[Agent Development](./developer/agents/AGENT_DEVELOPMENT.md)** - Creating custom agents
- **[Memory System](./developer/memory/MEMORY_SYSTEM.md)** - Technical memory documentation
- **[Security Guide](./developer/security/SECURITY.md)** - Security architecture
- **[Schema Reference](./developer/schemas/SCHEMA_REFERENCE.md)** - JSON schemas

### For Contributors
- **[Project Structure](./STRUCTURE.md)** - Codebase organization
- **[Quality Assurance](./QA.md)** - Testing and validation
- **[Deployment Guide](./DEPLOY.md)** - Release and publishing
- **[Versioning](./VERSIONING.md)** - Version management

## Documentation Structure

```
docs/
├── README.md                    # This file
├── user/                        # User-facing documentation
│   ├── 01-getting-started/     # Installation and setup
│   ├── 02-usage/               # Using Claude MPM
│   ├── 03-features/            # Feature guides
│   └── 04-reference/           # Command reference
├── developer/                   # Developer documentation
│   ├── agents/                 # Agent system
│   ├── memory/                 # Memory system
│   ├── security/               # Security system
│   ├── schemas/                # JSON schemas
│   ├── dashboard/              # Monitoring dashboard
│   ├── responses/              # Response system
│   └── 01-architecture/        # System architecture
└── archive/                     # Archived documentation
```

## Critical Pathways

### Agent Development Workflow
1. [Developer Guide](./developer/) → [Agent System](./developer/agents/) → [Agent Development Guide](./developer/agents/AGENT_DEVELOPMENT.md)
2. [Schema Reference](./developer/schemas/SCHEMA_REFERENCE.md) → [Agent Schema Documentation](./developer/schemas/agent_schema_documentation.md)
3. [Security Guide](./developer/security/SECURITY.md) → [Agent Security](./developer/security/agent_schema_security_notes.md)

### Memory System Workflow
1. [Memory Guide](./MEMORY.md) → [Memory System Technical](./developer/memory/MEMORY_SYSTEM.md)
2. [Response System](./developer/responses/README.md) → [Response Logging](./developer/memory/response-logging.md)
3. [Memory Builder](./developer/memory/builder.md) → [Memory Optimizer](./developer/memory/optimizer.md)

### Dashboard & Monitoring
1. [User Dashboard Guide](./user/03-features/dashboard-enhancements.md) → [Developer Dashboard](./developer/dashboard/README.md)
2. [Config Window](./developer/dashboard/CONFIG_WINDOW_V2.md)

### Security Workflow
1. [User Security](./user/03-features/file-security.md) → [Developer Security](./developer/security/SECURITY.md)
2. [Security Extensions](./developer/05-extending/file-security-hook.md)

## Getting Help

- Check relevant user or developer guides above
- Search existing documentation with your browser
- Review [archived documentation](./archive/) for historical context
- Check [GitHub Issues](https://github.com/your-org/claude-mpm/issues) for known issues

## Contributing to Documentation

See [Developer Guide](./developer/README.md) for guidelines on:
- Documentation standards
- File organization
- Cross-referencing
- Review process