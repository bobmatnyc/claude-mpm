# Developer Documentation

## Overview

Comprehensive developer documentation for Claude MPM, organized for easy navigation and reference.

## Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/claude-mpm.git
cd claude-mpm

# Setup development environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"

# Run tests
pytest tests/
```

## Documentation Structure

### Core Systems

#### 🤖 [Agent System](./07-agent-system/)
- **[Agent Development Guide](./07-agent-system/AGENT_DEVELOPMENT.md)** - Complete guide for creating and deploying agents
  - Agent architecture and types
  - Creating agents in multiple formats
  - Frontmatter configuration
  - Three-tier deployment system
  - Testing and validation
- **[Agent Formats](./07-agent-system/formats.md)** - Supported file formats and conversion
- **[Frontmatter Guide](./07-agent-system/frontmatter.md)** - YAML frontmatter configuration
- **[Compatibility](./07-agent-system/compatibility.md)** - Version compatibility and migration
- **[Schema Documentation](./07-agent-system/schema.md)** - Agent schema reference

#### 🧠 [Memory System](./08-memory-system/)
- **[Memory System Guide](./08-memory-system/MEMORY_SYSTEM.md)** - Comprehensive memory system documentation
  - 10 specialized agent types with dedicated memory
  - Memory routing and building
  - Optimization and management
  - CLI operations and configuration
- **[Response Handling](./08-memory-system/response-handling.md)** - Processing agent responses for memory
- **[Response Logging](./08-memory-system/response-logging.md)** - Logging system for responses
- **[Memory Router](./08-memory-system/router.md)** - Content routing to appropriate agents
- **[Memory Builder](./08-memory-system/builder.md)** - Building memories from documentation
- **[Memory Optimizer](./08-memory-system/optimizer.md)** - Optimization and deduplication

#### 🔒 [Security](./09-security/)
- **[Security Guide](./09-security/SECURITY.md)** - Complete security documentation
  - Multi-layered filesystem security
  - Agent security and RBAC
  - PID validation
  - Path restrictions
  - Security best practices
- **[Schema Security](./09-security/agent_schema_security_notes.md)** - Schema validation security

#### 📋 [Schemas](./10-schemas/)
- **[Schema Reference](./10-schemas/SCHEMA_REFERENCE.md)** - JSON schema documentation
  - Agent schema v1.2.0
  - Frontmatter schema
  - Validation rules and tools
  - Schema evolution and migration
- **[Agent Schema Documentation](./10-schemas/agent_schema_documentation.md)** - Detailed schema docs

#### 📊 [Dashboard](./11-dashboard/)
- **[Dashboard Overview](./11-dashboard/README.md)** - Real-time monitoring dashboard
- **[Config Window V2](./11-dashboard/CONFIG_WINDOW_V2.md)** - Configuration interface

#### 📝 [Response System](./12-responses/)
- **[Response System Overview](./12-responses/README.md)** - Response handling architecture
- **[Development Guide](./12-responses/DEVELOPMENT.md)** - Developing with responses
- **[Technical Reference](./12-responses/TECHNICAL_REFERENCE.md)** - API and internals
- **[User Guide](./12-responses/USER_GUIDE.md)** - Using the response system

#### 🔌 [MCP Gateway](./13-mcp-gateway/)
- **[MCP Gateway Overview](./13-mcp-gateway/README.md)** - Model Context Protocol gateway implementation
  - Production-ready MCP protocol handler
  - Claude Code integration
  - Extensible tool framework
  - Singleton coordination
  - Comprehensive testing and documentation
- **[Tool Development Guide](./13-mcp-gateway/tool-development.md)** - Creating custom MCP tools
- **[Configuration Reference](./13-mcp-gateway/configuration.md)** - Gateway configuration options
- **[MCP Gateway API](./04-api-reference/mcp-gateway-api.md)** - Complete API reference

### Development Guides

#### 📚 [Architecture](./01-architecture/)
- System design patterns
- Component diagrams
- Data flow architecture
- Integration patterns

#### 🔧 [Core Components](./02-core-components/)
- Agent system internals
- Hook system architecture
- Memory system components
- Schema architecture

#### 💻 [Development](./03-development/)
- Setup and configuration
- Coding standards
- Testing strategies
- Debugging techniques

#### 📖 [API Reference](./04-api-reference/)
- Core API documentation
- Service APIs
- Agent lifecycle API
- Orchestration API

#### 🔌 [Extending](./05-extending/)
- Custom hooks development
- Agent extension points
- Plugin architecture
- Security extensions

#### ⚙️ [Internals](./06-internals/)
- Analysis reports
- Migration guides
- Performance optimization
- Advanced topics

## Key Features

### Agent Management
- **Three-tier precedence system**: PROJECT > USER > SYSTEM
- **Multiple format support**: Markdown, JSON, YAML
- **Dynamic capability discovery**: Real-time agent capability detection
- **Version management**: Semantic versioning for agents and schemas

📖 **See**: [Agent Development Guide](./07-agent-system/AGENT_DEVELOPMENT.md) | [Schema Reference](./10-schemas/SCHEMA_REFERENCE.md)

### Memory System
- **10 specialized agents**: Each with dedicated memory sections
- **Intelligent routing**: Content automatically routed to appropriate agents
- **Project-specific learning**: Memories tailored to your codebase
- **Optimization tools**: Deduplication and consolidation

📖 **See**: [Memory System Guide](./08-memory-system/MEMORY_SYSTEM.md) | [Response System](./12-responses/README.md)

### Security
- **Multi-layered protection**: Working directory, agent-level, and PM coordination
- **Path restrictions**: Comprehensive path validation and traversal prevention
- **Role-based access**: Fine-grained permissions per agent type
- **Audit logging**: Complete activity tracking

📖 **See**: [Security Guide](./09-security/SECURITY.md) | [Schema Security](./09-security/agent_schema_security_notes.md)

## Common Tasks

### Creating a Custom Agent

```bash
# Create project agent directory
mkdir -p .claude-mpm/agents

# Create agent with frontmatter
cat > .claude-mpm/agents/custom_qa.md << 'EOF'
---
description: Custom QA agent for project
version: 2.0.0
tools: ["Read", "Grep", "Bash"]
model: claude-sonnet-4-20250514
---

# Custom QA Agent

Project-specific testing instructions...
EOF

# Verify deployment
./claude-mpm agents list --by-tier
```

### Building Memory from Documentation

```bash
# Initialize memory system
./claude-mpm memory init

# Build from docs
./claude-mpm memory build --docs ./docs

# Check status
./claude-mpm memory status

# Optimize if needed
./claude-mpm memory optimize --all
```

### Validating Agent Configuration

```bash
# Validate single agent
python scripts/validate_agent_frontmatter.py .claude-mpm/agents/my_agent.md

# Validate all agents
python scripts/validate_agent_frontmatter.py .claude-mpm/agents/*.md

# Check schema compliance
python scripts/validate_agent_configuration.py --all
```

## Best Practices

### Agent Development
1. Use semantic versioning for agents
2. Include comprehensive instructions
3. Follow the principle of least privilege for tools
4. Test agents thoroughly before deployment
5. Document project-specific knowledge

### Memory Management
1. Regular optimization to prevent bloat
2. Review memories before committing
3. Use memory directives in agent responses
4. Share memories with team via version control

### Security
1. Always validate paths before file operations
2. Use agent-specific file access restrictions
3. Enable audit logging in production
4. Regular security audits of agent permissions

## Complete Development Workflows

### 🤖 Agent Development Workflow
1. **Plan**: [Agent Development Guide](./07-agent-system/AGENT_DEVELOPMENT.md) → [Schema Reference](./10-schemas/SCHEMA_REFERENCE.md)
2. **Implement**: [Agent Formats](./07-agent-system/formats.md) → [Frontmatter Guide](./07-agent-system/frontmatter.md)
3. **Secure**: [Security Guide](./09-security/SECURITY.md) → [Schema Security](./09-security/agent_schema_security_notes.md)
4. **Test**: [Development Testing](./03-development/testing.md) → [Agent Validation](./02-core-components/agent-system.md)

### 🧠 Memory Integration Workflow
1. **Understanding**: [Memory System Guide](./08-memory-system/MEMORY_SYSTEM.md) → [Response System](./12-responses/README.md)
2. **Implementation**: [Response Handling](./08-memory-system/response-handling.md) → [Memory Builder](./08-memory-system/builder.md)
3. **Optimization**: [Memory Optimizer](./08-memory-system/optimizer.md) → [Memory Router](./08-memory-system/router.md)

### 🔒 Security Implementation Workflow
1. **Architecture**: [Security Guide](./09-security/SECURITY.md) → [Core Components](./02-core-components/README.md)
2. **Extensions**: [Custom Security](./05-extending/file-security-hook.md) → [Security API](./04-api-reference/README.md)
3. **User Features**: [User Security Guide](../user/03-features/file-security.md)

### 📊 Dashboard Development Workflow
1. **Setup**: [Dashboard Overview](./11-dashboard/README.md) → [Config Window](./11-dashboard/CONFIG_WINDOW_V2.md)
2. **Integration**: [User Dashboard](../user/03-features/dashboard-enhancements.md)

## Troubleshooting

### Common Issues

**Agent not found**
```bash
./claude-mpm agents list --by-tier | grep agent_name
```

**Memory not loading**
```bash
./claude-mpm memory status
./claude-mpm memory validate --agent engineer
```

**Validation errors**
```bash
python scripts/validate_agent_frontmatter.py agent.md --verbose
```

## Archive

Older and deprecated documentation has been moved to [./archive/](./archive/) for reference.

## Contributing

1. Follow [coding standards](./03-development/coding-standards.md)
2. Add tests for new features
3. Update documentation
4. Submit PR with clear description

## Support

- Check [User Documentation](../user/)
- Search [GitHub Issues](https://github.com/your-org/claude-mpm/issues)
- Create detailed issue reports

## License

MIT License - See [LICENSE](../../LICENSE)