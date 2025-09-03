# Claude MPM Documentation

**Version**: 4.2.2 | **Updated**: September 2, 2025

Claude MPM (Multi-Agent Project Manager) extends Claude Code with multi-agent orchestration capabilities and service-oriented architecture.

## 🚀 5-Minute Quick Start

```bash
# 1. Install
git clone https://github.com/bobmatnyc/claude-mpm.git && cd claude-mpm
./scripts/claude-mpm --setup

# 2. Run
./scripts/claude-mpm run

# 3. Create custom agent (optional)
mkdir -p .claude-mpm/agents
echo "---
description: My project expert
version: 1.0.0
---
# My Agent
Expert in this project's patterns..." > .claude-mpm/agents/my_agent.md
```

## 📖 Core Documentation (AI-Optimized)

### 🏗️ [Architecture](ARCHITECTURE.md)
**Complete system architecture in one place**
- Service-oriented design with 5 domains
- Three-tier agent system (PROJECT > USER > SYSTEM)  
- Dependency injection and interface contracts
- Performance features (50-80% improvement)
- Security framework and communication layer

### 🔧 [Development](DEVELOPMENT.md) 
**Everything developers need to know**
- Quality workflow: `make lint-fix` → `make quality` → `make test`
- Service development patterns with examples
- CLI command creation
- Testing strategy and performance optimization
- Complete troubleshooting guide

### 🤖 [Agents](AGENTS.md)
**Complete agent development guide**
- Create project agents in 3 steps
- Three-tier precedence system
- Multiple formats (Markdown, JSON, YAML)
- Agent management commands  
- Dependencies and deployment

### 🚀 [Deployment](DEPLOYMENT.md)
**Operations and release management**
- Version management and semantic versioning
- Quality gates and release process
- Environment configuration
- Security protocols

### 📚 [API Reference](API.md)
**Service interfaces and API documentation**
- Core service interfaces
- Agent management APIs
- Communication service APIs
- Usage examples and patterns

### ❓ [Troubleshooting](TROUBLESHOOTING.md)
**Common issues and solutions**
- Setup problems and fixes
- Agent loading issues
- Performance debugging
- Error resolution patterns

## 💡 AI Agent Quick Reference

**For Claude Code/AI agents working with this project:**

| Task | Command | Location |
|------|---------|----------|
| **Run system** | `./scripts/claude-mpm run` | - |
| **Check quality** | `make quality` | - |
| **Fix code style** | `make lint-fix` | - |
| **Run tests** | `make test` | - |
| **List agents** | `./scripts/claude-mpm agents list --by-tier` | - |
| **Create agent** | Create file in `.claude-mpm/agents/` | [Guide](AGENTS.md#quick-start) |
| **Deploy agents** | `./scripts/claude-mpm agents deploy` | - |
| **View architecture** | Read architecture summary | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Service layer** | 5 domains under `src/claude_mpm/services/` | [ARCHITECTURE.md](ARCHITECTURE.md#service-layer) |

## 🎯 Task-Specific Documentation

### New to Claude MPM?
1. **[5-Minute Setup](#-5-minute-quick-start)** ← Start here
2. **[Architecture Overview](ARCHITECTURE.md#overview)** - Understand the system
3. **[Development Workflow](DEVELOPMENT.md#quality-workflow)** - Learn the process

### Developing Code?  
1. **[Development Guide](DEVELOPMENT.md)** ← Essential workflows
2. **[Testing Strategy](DEVELOPMENT.md#testing-strategy)** - Quality practices
3. **[Service Development](DEVELOPMENT.md#service-development)** - Create services

### Creating Agents?
1. **[Agent Quick Start](AGENTS.md#quick-start)** ← 3-step process
2. **[Agent Formats](AGENTS.md#agent-formats)** - Choose format
3. **[Management Commands](AGENTS.md#agent-management)** - CLI tools

### Deploying?
1. **[Deployment Guide](DEPLOYMENT.md)** ← Release process
2. **[Version Management](DEPLOYMENT.md#version-management)** - Versioning
3. **[Quality Gates](DEPLOYMENT.md#quality-gates)** - Pre-release checks

### Having Issues?
1. **[Troubleshooting Guide](TROUBLESHOOTING.md)** ← Common solutions  
2. **[Development Troubleshooting](DEVELOPMENT.md#troubleshooting)** - Dev issues
3. **[Agent Troubleshooting](AGENTS.md#troubleshooting)** - Agent problems

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