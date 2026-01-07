# Agent Presets Guide

**Version**: 5.0.0
**Status**: Current
**Last Updated**: 2025-12-01

Get started instantly with pre-configured agent bundles for common technology stacks.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Available Presets](#available-presets)
- [Choosing a Preset](#choosing-a-preset)
- [Usage Examples](#usage-examples)
- [Customizing Presets](#customizing-presets)
- [Team Workflows](#team-workflows)
- [Troubleshooting](#troubleshooting)
- [Related Documentation](#related-documentation)

---

## Overview

Agent presets provide instant deployment of curated agent bundles for common development scenarios. Instead of manually selecting agents or waiting for auto-detection, deploy a complete agent stack with a single command.

### What Are Agent Presets?

Presets are pre-configured collections of agents optimized for specific technology stacks. Each preset includes:

- **Core agents**: Essential agents for the technology stack
- **Complementary agents**: QA, ops, and security agents
- **Universal agents**: Memory management and research capabilities

### Why Use Presets?

✅ **Instant deployment** - Get started in under 5 seconds
✅ **Best practices** - Curated by Claude MPM experts
✅ **Complete stacks** - All agents you need, nothing you don't
✅ **Team standardization** - Consistent agent configurations across team
✅ **Quick onboarding** - New developers productive immediately

### When to Use Presets

**Use presets when:**
- ✅ You have a standard, well-known technology stack
- ✅ Speed is critical (demos, quick prototypes)
- ✅ Following team conventions
- ✅ You know your stack fits a preset

**Use auto-configure instead when:**
- ⚠️ Mixed or custom technology stacks
- ⚠️ Unique project architecture
- ⚠️ Learning which agents are available
- ⚠️ Project needs differ from standard setups

**See**: [Auto-Configuration Guide](../getting-started/auto-configuration.md) for comparison

---

## Quick Start

### Deploy a Preset

```bash
# Python backend development
claude-mpm agents deploy --preset python-dev

# Next.js full-stack
claude-mpm agents deploy --preset nextjs-fullstack

# React frontend
claude-mpm agents deploy --preset react-dev
```

### List All Presets

```bash
# See all available presets
claude-mpm agents deploy --list-presets
```

### Verify Deployment

```bash
# Check deployed agents
claude-mpm agents list

# Or use status command
claude-mpm status
```

---

## Available Presets

Claude MPM provides 11 curated presets for common development scenarios.

---

### `minimal` - Essential Agents for Any Project

**Description**: 6 core agents providing fundamental capabilities for any project type.

**Agent Count**: 6 agents

**Included Agents**:
- `universal/memory-manager` - Project context and memory management
- `universal/research` - Research and documentation lookup
- `documentation/documentation` - Documentation generation
- `engineer/backend/python-engineer` - Backend development (language-agnostic baseline)
- `qa/qa` - General quality assurance
- `ops/core/ops` - Basic operations support

**Use Cases**:
- Micro projects and quick prototypes
- Learning Claude MPM basics
- Minimal overhead setups
- Quick demos or experiments

**Ideal For**:
- Beginners learning the system
- Small utility projects
- Temporary or experimental work
- Projects where you'll manually add specific agents

**Example:**
```bash
# Minimal setup
claude-mpm agents deploy --preset minimal

# Then add specific agents as needed
claude-mpm agents deploy engineer/frontend/react-engineer
```

---

### `python-dev` - Python Backend Development

**Description**: Fast-track Python backend development with essential agents for API development, testing, and operations.

**Agent Count**: 8 agents

**Included Agents**:
- `universal/memory-manager` - Context management
- `universal/research` - Documentation and research
- `documentation/documentation` - Doc generation
- `engineer/backend/python-engineer` - Python development expertise
- `qa/qa` - General testing
- `qa/api-qa` - API testing specialization
- `ops/core/ops` - Operations and deployment
- `security/security` - Security scanning and best practices

**Use Cases**:
- FastAPI REST APIs
- Django web applications
- Flask microservices
- Python CLI tools
- Data processing pipelines
- Python-based backends

**Ideal For**:
- Python backend teams
- API-first projects
- Microservices architecture
- DevOps automation scripts

**Example Project Types**:
- FastAPI + PostgreSQL + Docker
- Django + Redis + Celery
- Flask + SQLAlchemy
- Python data pipelines

**Command:**
```bash
claude-mpm agents deploy --preset python-dev
```

---

### `python-fullstack` - Python Backend + React Frontend

**Description**: Complete full-stack Python development with React frontend support.

**Agent Count**: 12 agents

**Included Agents**:
- `universal/memory-manager` - Context management
- `universal/research` - Research capabilities
- `universal/code-analyzer` - Code quality analysis
- `documentation/documentation` - Documentation
- `documentation/ticketing` - Ticket management
- `engineer/backend/python-engineer` - Python backend
- `engineer/frontend/react-engineer` - React frontend
- `qa/qa` - General testing
- `qa/api-qa` - API testing
- `qa/web-qa` - Frontend testing
- `ops/core/ops` - Operations
- `security/security` - Security

**Use Cases**:
- FastAPI + React applications
- Django + React applications
- Full-stack Python projects
- Modern Python web apps

**Ideal For**:
- Full-stack Python teams
- Single-page applications with Python backends
- Projects needing both API and UI development
- Integrated front-end and back-end work

**Example Project Types**:
- FastAPI + React + PostgreSQL
- Django Rest Framework + React
- Python API + React admin panel

**Command:**
```bash
claude-mpm agents deploy --preset python-fullstack
```

---

### `javascript-backend` - Node.js Backend Development

**Description**: Node.js backend development with Express, Fastify, or other JavaScript frameworks.

**Agent Count**: 8 agents

**Included Agents**:
- `universal/memory-manager` - Context management
- `universal/research` - Research capabilities
- `documentation/documentation` - Documentation
- `engineer/backend/javascript-engineer` - JavaScript backend expertise
- `qa/qa` - General testing
- `qa/api-qa` - API testing
- `ops/core/ops` - Operations
- `security/security` - Security

**Use Cases**:
- Express.js APIs
- Fastify microservices
- Koa applications
- Node.js REST APIs
- GraphQL servers
- WebSocket servers

**Ideal For**:
- JavaScript backend teams
- Node.js microservices
- Real-time applications
- GraphQL APIs

**Example Project Types**:
- Express + MongoDB + Socket.io
- Fastify + PostgreSQL + Redis
- Koa + REST API
- NestJS backend (use with TypeScript)

**Command:**
```bash
claude-mpm agents deploy --preset javascript-backend
```

---

### `react-dev` - React Frontend Development

**Description**: React frontend development with TypeScript support and web testing.

**Agent Count**: 9 agents

**Included Agents**:
- `universal/memory-manager` - Context management
- `universal/research` - Research capabilities
- `documentation/documentation` - Documentation
- `engineer/frontend/react-engineer` - React expertise
- `engineer/data/typescript-engineer` - TypeScript support
- `qa/qa` - General testing
- `qa/web-qa` - Frontend/UI testing
- `ops/core/ops` - Build and deployment
- `security/security` - Security scanning

**Use Cases**:
- React single-page applications
- Component libraries
- React Native apps (mobile)
- Frontend-only projects
- Design systems

**Ideal For**:
- Frontend teams
- UI/UX-focused projects
- Component library development
- Design system implementation

**Example Project Types**:
- Create React App
- React + TypeScript + Vite
- React component library
- React Native mobile app

**Command:**
```bash
claude-mpm agents deploy --preset react-dev
```

---

### `nextjs-fullstack` - Next.js Full-Stack Development

**Description**: Complete Next.js development stack with React, TypeScript, and Vercel deployment support.

**Agent Count**: 13 agents

**Included Agents**:
- `universal/memory-manager` - Context management
- `universal/research` - Research capabilities
- `universal/code-analyzer` - Code quality analysis
- `documentation/documentation` - Documentation
- `documentation/ticketing` - Ticket management
- `engineer/frontend/nextjs-engineer` - Next.js expertise
- `engineer/frontend/react-engineer` - React components
- `engineer/data/typescript-engineer` - TypeScript support
- `qa/qa` - General testing
- `qa/web-qa` - Frontend testing
- `ops/core/ops` - Operations
- `ops/platform/vercel-ops` - Vercel deployment
- `security/security` - Security

**Use Cases**:
- Next.js applications (Pages Router or App Router)
- Vercel deployments
- Full-stack TypeScript projects
- Server-side rendered React apps
- Static site generation
- Incremental static regeneration

**Ideal For**:
- Modern full-stack teams
- Vercel-hosted projects
- SEO-critical applications
- TypeScript-first development

**Example Project Types**:
- Next.js 14+ with App Router
- Next.js + Prisma + PostgreSQL
- Next.js + tRPC + TypeScript
- E-commerce with Next.js

**Command:**
```bash
claude-mpm agents deploy --preset nextjs-fullstack
```

---

### `rust-dev` - Rust Systems Development

**Description**: Rust systems programming with focus on performance and safety.

**Agent Count**: 7 agents

**Included Agents**:
- `universal/memory-manager` - Context management
- `universal/research` - Research capabilities
- `documentation/documentation` - Documentation
- `engineer/backend/rust-engineer` - Rust expertise
- `qa/qa` - Testing support
- `ops/core/ops` - Build and deployment
- `security/security` - Security scanning

**Use Cases**:
- Rust systems programming
- CLI tools in Rust
- WebAssembly projects
- High-performance backends
- System utilities
- Rust libraries/crates

**Ideal For**:
- Systems programming teams
- Performance-critical applications
- Rust library development
- WebAssembly projects

**Example Project Types**:
- Rust CLI with Clap
- WebAssembly modules
- Rust + Actix-web API
- Performance-critical tools

**Command:**
```bash
claude-mpm agents deploy --preset rust-dev
```

---

### `golang-dev` - Go Backend Development

**Description**: Go backend development for microservices and cloud-native applications.

**Agent Count**: 8 agents

**Included Agents**:
- `universal/memory-manager` - Context management
- `universal/research` - Research capabilities
- `documentation/documentation` - Documentation
- `engineer/backend/golang-engineer` - Go expertise
- `qa/qa` - General testing
- `qa/api-qa` - API testing
- `ops/core/ops` - Operations
- `security/security` - Security

**Use Cases**:
- Go REST APIs
- Microservices in Go
- Cloud-native applications
- gRPC services
- Kubernetes operators
- Go CLI tools

**Ideal For**:
- Go backend teams
- Microservices architectures
- Cloud infrastructure projects
- High-concurrency systems

**Example Project Types**:
- Go + Gin + PostgreSQL
- Go + gRPC + Kubernetes
- Go + Fiber framework
- Cloud-native Go services

**Command:**
```bash
claude-mpm agents deploy --preset golang-dev
```

---

### `java-dev` - Java/Spring Boot Development

**Description**: Java development with Spring Boot framework support for enterprise applications.

**Agent Count**: 9 agents

**Included Agents**:
- `universal/memory-manager` - Context management
- `universal/research` - Research capabilities
- `documentation/documentation` - Documentation
- `documentation/ticketing` - Ticket management
- `engineer/backend/java-engineer` - Java expertise
- `qa/qa` - General testing
- `qa/api-qa` - API testing
- `ops/core/ops` - Operations
- `security/security` - Security

**Use Cases**:
- Spring Boot applications
- Java EE enterprise apps
- Maven/Gradle projects
- Microservices in Java
- Enterprise REST APIs

**Ideal For**:
- Enterprise Java teams
- Spring Boot projects
- Large-scale Java applications
- Microservices architectures

**Example Project Types**:
- Spring Boot + JPA + MySQL
- Java microservices
- Enterprise web applications
- RESTful services with Spring

**Command:**
```bash
claude-mpm agents deploy --preset java-dev
```

---

### `mobile-flutter` - Flutter Mobile Development

**Description**: Cross-platform mobile development with Flutter and Dart.

**Agent Count**: 8 agents

**Included Agents**:
- `universal/memory-manager` - Context management
- `universal/research` - Research capabilities
- `documentation/documentation` - Documentation
- `documentation/ticketing` - Ticket management
- `engineer/mobile/dart-engineer` - Flutter/Dart expertise
- `qa/qa` - Testing support
- `ops/core/ops` - Build and deployment
- `security/security` - Security scanning

**Use Cases**:
- Flutter mobile apps (iOS + Android)
- Cross-platform mobile development
- Dart applications
- Mobile-first projects
- Flutter web apps

**Ideal For**:
- Mobile development teams
- Cross-platform projects
- Flutter specialists
- Dart backend + Flutter frontend

**Example Project Types**:
- Flutter + Firebase
- Flutter + REST API
- Flutter + SQLite
- Cross-platform mobile apps

**Command:**
```bash
claude-mpm agents deploy --preset mobile-flutter
```

---

### `data-eng` - Data Engineering Stack

**Description**: Data engineering with Python, dbt, Airflow, and data pipeline tools.

**Agent Count**: 10 agents

**Included Agents**:
- `universal/memory-manager` - Context management
- `universal/research` - Research capabilities
- `universal/code-analyzer` - Code quality
- `documentation/documentation` - Documentation
- `documentation/ticketing` - Ticket management
- `engineer/backend/python-engineer` - Python expertise
- `engineer/data/data-engineer` - Data engineering specialization
- `qa/qa` - Testing support
- `ops/core/ops` - Operations
- `security/security` - Security

**Use Cases**:
- dbt projects (data transformation)
- Apache Airflow DAGs
- Data pipelines and ETL
- Data warehouse projects
- Analytics engineering
- Data orchestration

**Ideal For**:
- Data engineering teams
- Analytics engineers
- ETL development
- Data platform projects

**Example Project Types**:
- dbt + Snowflake + Airflow
- Python + Pandas + PostgreSQL
- Data pipeline with Dagster
- Analytics engineering stack

**Command:**
```bash
claude-mpm agents deploy --preset data-eng
```

---

## Choosing a Preset

### Decision Matrix

| If Your Stack Is... | Use This Preset | Agent Count |
|---------------------|----------------|-------------|
| Python backend only | `python-dev` | 8 |
| Python + React | `python-fullstack` | 12 |
| Node.js backend | `javascript-backend` | 8 |
| React frontend only | `react-dev` | 9 |
| Next.js full-stack | `nextjs-fullstack` | 13 |
| Go backend | `golang-dev` | 8 |
| Rust systems | `rust-dev` | 7 |
| Java/Spring Boot | `java-dev` | 9 |
| Flutter mobile | `mobile-flutter` | 8 |
| Data pipelines | `data-eng` | 10 |
| Not sure / minimal | `minimal` | 6 |

### By Project Size

| Project Size | Recommended Presets |
|--------------|-------------------|
| **Small** (1-2 developers) | `minimal`, `python-dev`, `react-dev` |
| **Medium** (3-10 developers) | `python-fullstack`, `nextjs-fullstack`, `golang-dev` |
| **Large** (10+ developers) | `java-dev`, `data-eng`, custom combinations |

### By Development Phase

| Phase | Recommended Approach |
|-------|-------------------|
| **Prototype** | `minimal` → add specific agents later |
| **MVP** | Use appropriate preset for your stack |
| **Production** | Preset + manual additions for special needs |
| **Maintenance** | Keep existing preset, add agents as needed |

---

## Usage Examples

### Example 1: Quick Python API Setup

**Scenario**: Building a FastAPI backend with PostgreSQL.

```bash
# Deploy Python development preset
claude-mpm agents deploy --preset python-dev

# Verify deployment
claude-mpm agents list

# Start Claude MPM session
claude-mpm run
```

**Result**: 8 agents deployed in < 5 seconds, ready for Python backend development.

---

### Example 2: Next.js Project for Vercel

**Scenario**: Full-stack Next.js app deploying to Vercel.

```bash
# Deploy Next.js full-stack preset
claude-mpm agents deploy --preset nextjs-fullstack

# Check what was deployed
claude-mpm status
```

**Deployed agents include**:
- Next.js and React engineers
- TypeScript support
- Vercel deployment specialist
- Frontend testing
- All universal agents

---

### Example 3: Team Onboarding

**Scenario**: New developer joining Python backend team.

```bash
# Onboarding script
cat > onboard.sh <<'EOF'
#!/bin/bash
# Team standard: Python + FastAPI + Docker

echo "Setting up Claude MPM agents..."
claude-mpm agents deploy --preset python-dev

echo "Agents deployed! Ready to start developing."
claude-mpm agents list
EOF

chmod +x onboard.sh
./onboard.sh
```

**Result**: Consistent agent setup across entire team in seconds.

---

### Example 4: Multi-Preset for Monorepo

**Scenario**: Monorepo with Python backend + Next.js frontend.

```bash
# Strategy: Deploy multiple presets
# (They share universal agents, no duplication)

# Deploy Python backend agents
claude-mpm agents deploy --preset python-dev

# Deploy Next.js frontend agents (adds only frontend-specific ones)
claude-mpm agents deploy --preset nextjs-fullstack

# Universal agents (memory-manager, research) only deployed once
```

**Result**: Complete agent coverage for both backend and frontend.

---

## Customizing Presets

### Adding Agents to a Preset

Deploy a preset, then add specific agents:

```bash
# Start with Python dev preset
claude-mpm agents deploy --preset python-dev

# Add specialized agent
claude-mpm agents deploy ops/platform/railway-ops

# Add another specialized agent
claude-mpm agents deploy qa/web-qa
```

### Removing Unwanted Agents

Currently not supported via CLI. Manual workaround:

```bash
# Remove specific agent file
rm .claude-mpm/cache/agents/unwanted-agent.md

# Or remove all and redeploy selectively
rm -rf .claude-mpm/cache/agents/
claude-mpm agents deploy engineer/backend/python-engineer
# ... deploy each agent you want
```

### Creating Custom Team Presets

**Future feature**: Custom preset definitions in `.claude-mpm/presets.yaml`.

**Current workaround**: Create a deployment script:

```bash
#!/bin/bash
# team-preset.sh - Our company's standard stack

echo "Deploying company standard agent stack..."

# Core agents
claude-mpm agents deploy universal/memory-manager
claude-mpm agents deploy universal/research
claude-mpm agents deploy documentation/documentation

# Engineering agents (our stack: Python + React)
claude-mpm agents deploy engineer/backend/python-engineer
claude-mpm agents deploy engineer/frontend/react-engineer

# QA agents
claude-mpm agents deploy qa/qa
claude-mpm agents deploy qa/api-qa
claude-mpm agents deploy qa/web-qa

# Ops (we use Railway)
claude-mpm agents deploy ops/core/ops
claude-mpm agents deploy ops/platform/railway-ops

# Security
claude-mpm agents deploy security/security

echo "✅ Team preset deployed!"
```

Make executable and use:
```bash
chmod +x team-preset.sh
./team-preset.sh
```

---

## Team Workflows

### Standardizing Team Environments

**Use Case**: Ensure all developers have identical agent setups.

**Approach**:
1. Team lead selects appropriate preset
2. Document preset choice in README
3. New developers run single command
4. CI/CD uses same preset

**Example README section**:
```markdown
## Development Setup

Install Claude MPM agents:

```bash
# Team standard: Python full-stack preset
claude-mpm agents deploy --preset python-fullstack
```
```

### Onboarding New Developers

**Onboarding checklist** with preset:

```markdown
## New Developer Checklist

- [ ] Install Claude MPM: `pipx install "claude-mpm[monitor]"`
- [ ] Deploy team agents: `claude-mpm agents deploy --preset python-fullstack`
- [ ] Verify setup: `claude-mpm doctor`
- [ ] Start first session: `claude-mpm run --monitor`
```

**Result**: New developers productive in < 5 minutes.

### Multi-Project Setups

**Scenario**: Developer works on multiple projects with different stacks.

**Strategy**: Use presets per project (Claude MPM is project-scoped):

```bash
# Project 1: Python backend
cd ~/projects/api-backend
claude-mpm agents deploy --preset python-dev

# Project 2: Next.js frontend
cd ~/projects/web-frontend
claude-mpm agents deploy --preset nextjs-fullstack

# Project 3: Data pipeline
cd ~/projects/data-pipeline
claude-mpm agents deploy --preset data-eng
```

Each project has its own `.claude-mpm/` directory with appropriate agents.

---

## Troubleshooting

### Preset Not Found

**Symptoms**:
```
Error: Unknown preset: pyton-dev
```

**Solutions**:
1. **Check spelling**: Preset names are exact (e.g., `python-dev`, not `pyton-dev`)
2. **List available presets**: `claude-mpm agents deploy --list-presets`
3. **Check version**: Ensure Claude MPM is v5.0.0+ (`claude-mpm --version`)

**Correct preset names**:
- `minimal`
- `python-dev`
- `python-fullstack`
- `javascript-backend`
- `react-dev`
- `nextjs-fullstack`
- `rust-dev`
- `golang-dev`
- `java-dev`
- `mobile-flutter`
- `data-eng`

---

### Partial Deployment

**Symptoms**:
- Some agents deployed, others missing
- Incomplete agent list

**Solutions**:
1. **Check disk space**: Ensure sufficient storage
2. **Check permissions**: Write access to `.claude-mpm/`
3. **Redeploy with force**: `claude-mpm agents deploy --preset <name> --force`
4. **Check logs**: Look for error messages during deployment

**Verify deployment**:
```bash
# Check deployed agents
claude-mpm agents list

# Expected agent count varies by preset (see preset descriptions above)
```

---

### Wrong Preset Deployed

**Symptoms**:
- Deployed wrong preset by mistake
- Want to switch to different preset

**Solutions**:
1. **Remove and redeploy**:
```bash
# Remove all agents
rm -rf .claude-mpm/cache/agents/

# Deploy correct preset
claude-mpm agents deploy --preset <correct-preset>
```

2. **Add missing agents** (if just need additions):
```bash
# Keep existing, add more
claude-mpm agents deploy --preset <additional-preset>
```

---

### Preset Doesn't Match Project

**Symptoms**:
- Preset includes unnecessary agents
- Missing needed agents

**Solutions**:
1. **Use auto-configure instead**: `claude-mpm agents auto-configure`
2. **Customize after deployment**: Add/remove specific agents
3. **Create custom deployment script**: See [Customizing Presets](#customizing-presets)

---

### Agent Conflicts

**Symptoms**:
- Multiple presets deployed causing confusion
- Duplicate functionality

**Solutions**:
- **Not actually a problem**: Multiple agents can coexist
- Agents with similar capabilities don't conflict
- Universal agents (like `memory-manager`) are shared across presets
- If concerned, remove unwanted agents manually

---

## Preset vs. Auto-Configure

### Quick Comparison

| Aspect | Preset | Auto-Configure |
|--------|--------|---------------|
| **Speed** | Fastest (<5s) | Fast (30-60s) |
| **Accuracy** | Generic (one-size-fits-all) | Project-specific |
| **Customization** | Post-deploy only | Built-in threshold tuning |
| **Learning Curve** | Lowest | Low |
| **Best For** | Known stacks | Custom/mixed stacks |

### When Preset is Better

✅ **Standard technology stacks**: FastAPI, Next.js, Spring Boot, etc.
✅ **Quick onboarding**: Get new developers started immediately
✅ **Team consistency**: Everyone uses same agent set
✅ **Time-critical**: Demos, prototypes, quick experiments

### When Auto-Configure is Better

✅ **Custom stacks**: Unusual combinations or frameworks
✅ **Mixed technologies**: Multiple languages/frameworks
✅ **Precision matters**: Want only agents you'll actually use
✅ **Exploratory**: Learning what agents are available

### Hybrid Approach

Best of both worlds:

```bash
# 1. Start fast with preset
claude-mpm agents deploy --preset python-dev

# 2. Check what auto-configure would add
claude-mpm agents recommend --preview

# 3. Manually add specialized agents if needed
claude-mpm agents deploy ops/platform/railway-ops
```

**See**: [Auto-Configuration Guide](../getting-started/auto-configuration.md) for detailed comparison

---

## Related Documentation

### User Guides
- **[Auto-Configuration Guide](../getting-started/auto-configuration.md)** - Automatic stack detection and agent deployment
- **[Agent Sources Guide](agent-sources.md)** - Managing agent repositories and custom agents
- **[Getting Started](../getting-started/README.md)** - First steps with Claude MPM

### Reference
- **[CLI Agents Reference](../reference/cli-agents.md)** - Complete CLI command documentation
- **[Agent Presets Source Code](../../src/claude_mpm/config/agent_presets.py)** - Preset definitions

### Implementation
- **[Agent Deployment Guide](../guides/single-tier-agent-system.md)** - How agents are deployed
- **[Design Docs](../design/README.md)** - Design decisions

---

**Need Help?**
- List all presets: `claude-mpm agents deploy --list-presets`
- Check deployed agents: `claude-mpm agents list`
- Diagnose issues: `/mpm-doctor`
- See [Troubleshooting Guide](troubleshooting.md)

---

**Last Updated**: 2025-12-01
**Version**: 5.0.0
**Status**: Current
