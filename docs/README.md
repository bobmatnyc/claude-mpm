# Claude MPM Documentation

Welcome to Claude MPM (Multi-Agent Project Manager) - a framework that extends Claude Code with multi-agent orchestration capabilities. This documentation hub provides comprehensive guides for all users, from beginners to advanced developers.

## 🚀 Quick Start

**New to Claude MPM?** Start here:
- **[Installation Guide](user/01-getting-started/installation.md)** - Get up and running in minutes
- **[First Run Guide](user/01-getting-started/first-run.md)** - Your first interaction with Claude MPM
- **[Basic Usage](user/02-guides/basic-usage.md)** - Essential commands and workflows

## 📖 Documentation by Audience

### 👤 **For Users** - Using Claude MPM
> **Start here:** [User Documentation Hub](user/README.md)

- **Getting Started**
  - [Installation & Setup](user/01-getting-started/)
  - [Core Concepts](user/01-getting-started/concepts.md)
  - [First Run Experience](user/01-getting-started/first-run.md)

- **Using Claude MPM**
  - [Interactive Mode Guide](user/02-guides/interactive-mode.md)
  - [CLI Commands Reference](user/02-guides/cli-commands-reference.md)
  - [Basic Usage Patterns](user/02-guides/basic-usage.md)

- **Features & Capabilities**
  - [Memory System](user/03-features/memory-system.md)
  - [Agent Delegation](user/03-features/agent-delegation.md)
  - [Code Analysis & Visualization](user/03-features/code-analysis.md)
  - [Mermaid Diagram Generation](user/03-features/mermaid-visualization.md)
  - [Session Logging](user/03-features/session-logging.md)
  - [File Security](user/03-features/file-security.md)

- **Reference & Help**
  - [Configuration Guide](user/04-reference/configuration.md)
  - [Troubleshooting](user/04-reference/troubleshooting.md)
  - [Mermaid Troubleshooting](user/04-reference/troubleshooting-mermaid.md)
  - [Security Settings](user/04-reference/security-configuration.md)

### 👨‍💻 **For Developers** - Building with Claude MPM
> **Start here:** [Developer Documentation Hub](developer/README.md)

- **Architecture & Design**
  - [System Architecture](developer/ARCHITECTURE.md)
  - [Service Layer Guide](developer/SERVICES.md)
  - [Project Structure](developer/STRUCTURE.md)

- **Development**
  - [Testing Strategies](developer/TESTING.md)
  - [Performance Optimization](developer/PERFORMANCE.md)
  - [Code Quality & Linting](developer/LINTING.md)

- **Agent Development**
  - [Agent System Overview](developer/07-agent-system/)
  - [Creating Custom Agents](developer/07-agent-system/creation-guide.md)
  - [Agent Schema Reference](developer/10-schemas/agent_schema_documentation.md)

- **Advanced Topics**
  - [Hook System](developer/02-core-components/hook-system.md)
  - [Code Visualization Guide](developer/02-core-components/code-visualization-guide.md)
  - [Memory System Architecture](developer/08-memory-system/)
  - [Security Framework](developer/09-security/SECURITY.md)
  - [Dashboard Development](developer/11-dashboard/)

### 🛠️ **For Agents** - Agent Development
> **Start here:** [Agent Documentation Hub](agents/README.md)

- **Agent Creation**
  - [Agent Overview](agents/AGENTS.md)
  - [Agent Templates & Examples](agents/)

- **Specialized Agents**
  - [ImageMagick Web Optimization](agents/IMAGEMAGICK_WEB_OPTIMIZATION.md)
  - [Vercel Operations Agent](agents/VERCEL_OPS_AGENT.md)

### 📚 **Reference Documentation** - Technical References
> **Start here:** [Reference Documentation Hub](reference/README.md)

- **Deployment & Operations**
  - [Deployment Guide](reference/DEPLOY.md)
  - [Version Management](reference/VERSIONING.md)
  - [Security Configuration](reference/SECURITY.md)

- **Integration & Setup**
  - [MCP Gateway Setup](reference/MCP_SETUP.md)
  - [MCP Gateway Configuration](reference/MCP_GATEWAY.md)
  - [MCP Usage Guide](reference/MCP_USAGE.md)

## 🗂️ Documentation Organization

The documentation is organized into four main sections:

```
docs/
├── user/           # End-user guides and tutorials
├── developer/      # Development documentation
├── agents/         # Agent-specific documentation  
├── reference/      # Technical references and operations
├── api/           # Auto-generated API documentation
├── _archive/      # Historical documentation (reorganized 2025-08)
└── _internal/     # Internal maintenance docs
```

## 🆘 Getting Help

**Can't find what you're looking for?**

1. **Browse by section above** - Most topics are covered in the organized sections
2. **Check archived content** - Some documentation may be in [`_archive/`](_archive/) following reorganization
3. **Search GitHub Issues** - Known issues and solutions
4. **API Documentation** - Auto-generated docs in [`api/`](api/)

## 📋 Common Tasks

### For New Users
1. **[Install Claude MPM](user/01-getting-started/installation.md)**
2. **[Run your first command](user/01-getting-started/first-run.md)**
3. **[Learn basic usage](user/02-guides/basic-usage.md)**

### For Developers  
1. **[Understand the architecture](developer/ARCHITECTURE.md)**
2. **[Set up development environment](developer/03-development/setup.md)**
3. **[Quality workflow](developer/LINTING.md)** - `make lint-fix` → `make quality` → `make pre-publish`
4. **[Learn testing practices](developer/TESTING.md)**

### For Agent Creation
1. **[Learn agent concepts](agents/AGENTS.md)**
2. **[Follow creation guide](developer/07-agent-system/creation-guide.md)**
3. **[Study agent schema](developer/10-schemas/agent_schema_documentation.md)**

## 🗃️ Archive Notice

**Documentation Reorganized (August 2025)**: Historical documentation has been moved to [`_archive/`](_archive/) to improve navigation. If you're looking for:

- **Old test reports** → [`_archive/test-reports/`](_archive/test-reports/)
- **Legacy features** → [`_archive/temporary/`](_archive/temporary/) 
- **Previous release notes** → [`_archive/old-versions/`](_archive/old-versions/)
- **Implementation summaries** → [`_archive/qa-reports/`](_archive/qa-reports/)

## 🤝 Contributing to Documentation

Documentation improvements are welcome! See:
- [Developer Documentation Standards](developer/README.md#documentation-standards)
- [Project Structure Guide](developer/STRUCTURE.md)
- [Contributing Guidelines](developer/03-development/README.md)

---

**💡 Tip**: This documentation is structured to scale with your expertise. Start with user guides and progress to developer documentation as you become more familiar with Claude MPM.