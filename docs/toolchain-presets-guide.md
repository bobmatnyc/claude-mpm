# Toolchain Presets Guide

**Quick deployment of agent and skill bundles for your development stack**

---

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [MIN vs MAX Decision Guide](#min-vs-max-decision-guide)
- [Available Toolchains](#available-toolchains)
- [Interactive Mode](#interactive-mode)
- [Core Components](#core-components)
- [Usage Examples](#usage-examples)
- [Migration from Legacy Presets](#migration-from-legacy-presets)

---

## Overview

Toolchain presets provide **instant deployment** of agent and skill bundles tailored to your development stack. Instead of manually selecting dozens of components, deploy everything you need with a single command.

### What Are Presets?

**Presets** are curated bundles of agents and skills designed for specific toolchains:
- **Agent Presets**: Collections of specialized agents (engineers, QA, ops, etc.)
- **Skill Presets**: Collections of knowledge modules for specific technologies

### MIN vs MAX Variants

Each toolchain has **two preset variants**:

| Variant | Purpose | Agent Count | Skill Count | Startup Time | Resource Usage |
|---------|---------|-------------|-------------|--------------|----------------|
| **MIN** | Essentials only | 8-10 | 2-4 | ⚡ Fast | 💾 Low |
| **MAX** | Full capabilities | 12-17 | 6-10 | 🐢 Slower | 💾 High |

**Rule of Thumb**:
- **MIN**: Quick start, learning, small projects, microservices
- **MAX**: Production apps, enterprise scale, comprehensive coverage

---

## Quick Start

### Deploy Agent Preset (Interactive)
```bash
# Interactive checkbox selection - recommended for beginners
claude-mpm configure

# Select your toolchain preset from the list (e.g., python-min, nextjs-max)
```

### Deploy Skill Preset (Interactive)
```bash
# Interactive checkbox selection - NEW in v5.0!
claude-mpm skills configure

# Select your toolchain preset from the list (e.g., python-min, react-max)
```

### Deploy from Command Line (Automation)
```bash
# Deploy specific agent preset
claude-mpm configure --preset python-min

# Deploy specific skill preset
claude-mpm skills deploy-github --preset python-min

# Deploy both agents and skills for a toolchain
claude-mpm configure --preset python-min
claude-mpm skills deploy-github --preset python-min
```

---

## MIN vs MAX Decision Guide

### Use MIN Presets When:
- ✅ Starting a new project
- ✅ Learning a new toolchain
- ✅ Building microservices or small apps
- ✅ Want fast Claude Code startup
- ✅ Limited system resources
- ✅ Need only core functionality

### Use MAX Presets When:
- ✅ Production applications
- ✅ Enterprise-scale projects
- ✅ Need comprehensive test coverage
- ✅ Require security scanning
- ✅ Want full refactoring capabilities
- ✅ Building complex architectures

### Example: Python Toolchain

#### python-min (8 agents, 4 skills)
**Best for**: Quick scripts, small FastAPI microservices, prototypes

**Includes**:
- CORE agents (mpm, research, documentation, engineer)
- python-engineer, qa, ops
- pytest, asyncio, mypy skills

**Use cases**:
```bash
# FastAPI microservice
claude-mpm configure --preset python-min

# Quick data processing script
claude-mpm configure --preset python-min
```

#### python-max (14 agents, 8 skills)
**Best for**: Django production apps, complex APIs, enterprise Python

**Includes**:
- Everything in MIN
- PLUS: code-analyzer, memory-manager, api-qa, security, ticketing, refactoring
- PLUS: flask, testing-anti-patterns, verification-before-completion skills

**Use cases**:
```bash
# Django production application
claude-mpm configure --preset python-max
claude-mpm skills deploy-github --preset python-max

# Enterprise Python API with full testing
claude-mpm configure --preset python-max
```

---

## Available Toolchains

### Python Development
```bash
# Quick start for Python projects
claude-mpm configure --preset python-min
claude-mpm skills deploy-github --preset python-min

# Full Python stack for production
claude-mpm configure --preset python-max
claude-mpm skills deploy-github --preset python-max
```

**python-min**: 8 agents, 4 skills - Python scripts, small projects, FastAPI microservices
**python-max**: 14 agents, 8 skills - FastAPI production, Django, Python APIs at scale

---

### JavaScript/Node.js Development
```bash
# Essentials for Node.js backend
claude-mpm configure --preset javascript-min
claude-mpm skills deploy-github --preset javascript-min

# Full Node.js stack with testing
claude-mpm configure --preset javascript-max
claude-mpm skills deploy-github --preset javascript-max
```

**javascript-min**: 8 agents, 3 skills - Express.js, Node.js scripts, backend microservices
**javascript-max**: 13 agents, 7 skills - Express.js production, Fastify, enterprise Node.js

---

### React Development
```bash
# React essentials for SPAs
claude-mpm configure --preset react-min
claude-mpm skills deploy-github --preset react-min

# Full React stack for production
claude-mpm configure --preset react-max
claude-mpm skills deploy-github --preset react-max
```

**react-min**: 8 agents, 3 skills - React SPAs, component libraries, quick prototypes
**react-max**: 12 agents, 8 skills - React production apps, component systems, frontend at scale

---

### Next.js Full-Stack
```bash
# Next.js essentials
claude-mpm configure --preset nextjs-min
claude-mpm skills deploy-github --preset nextjs-min

# Full Next.js stack with database
claude-mpm configure --preset nextjs-max
claude-mpm skills deploy-github --preset nextjs-max
```

**nextjs-min**: 9 agents, 4 skills - Next.js apps, Vercel deployment, full-stack TypeScript
**nextjs-max**: 17 agents, 10 skills - Next.js production, enterprise apps, full-stack at scale

---

### TypeScript Development
```bash
# TypeScript essentials
claude-mpm configure --preset typescript-min
claude-mpm skills deploy-github --preset typescript-min

# Full TypeScript stack with ORMs
claude-mpm configure --preset typescript-max
claude-mpm skills deploy-github --preset typescript-max
```

**typescript-min**: 8 agents, 3 skills - Type-safe apps, TypeScript projects, Node.js with types
**typescript-max**: 14 agents, 8 skills - Enterprise TypeScript, full-stack apps, type-safe APIs

---

### Rust Systems Programming
```bash
# Rust essentials for CLI tools
claude-mpm configure --preset rust-min
claude-mpm skills deploy-github --preset rust-min

# Full Rust stack for production
claude-mpm configure --preset rust-max
claude-mpm skills deploy-github --preset rust-max
```

**rust-min**: 8 agents, 2 skills - Rust CLI tools, systems programming, WebAssembly
**rust-max**: 11 agents, 4 skills - Rust production systems, performance-critical apps

---

### Go Development
```bash
# Go essentials
claude-mpm configure --preset golang-min

# Full Go stack
claude-mpm configure --preset golang-max
```

**golang-min**: 8 agents - Go services, microservices, CLI tools
**golang-max**: 12 agents - Go production, distributed systems, enterprise Go

---

### WordPress Development
```bash
# WordPress plugin basics
claude-mpm skills deploy-github --preset wordpress-min

# Full WordPress stack with block editor
claude-mpm skills deploy-github --preset wordpress-max
```

**wordpress-min**: 2 skills - WordPress plugins, theme customization
**wordpress-max**: 4 skills - WordPress production, block themes, custom blocks, FSE

---

### AI/MCP Development
```bash
# MCP server essentials
claude-mpm skills deploy-github --preset ai-min

# Full AI toolkit
claude-mpm skills deploy-github --preset ai-max
```

**ai-min**: 2 skills - MCP servers, Claude integrations, AI tools
**ai-max**: 4 skills - Multi-model AI apps, Claude Desktop extensions, AI tooling

---

### Svelte Development
```bash
# Svelte essentials
claude-mpm skills deploy-github --preset svelte-min

# Full Svelte stack with SvelteKit
claude-mpm skills deploy-github --preset svelte-max
```

**svelte-min**: 2 skills - Svelte apps, reactive UIs, minimal JavaScript
**svelte-max**: 4 skills - SvelteKit production, full-stack Svelte, SSR/SSG apps

---

### Testing & Quality
```bash
# Testing essentials
claude-mpm skills deploy-github --preset testing-min

# Comprehensive testing stack
claude-mpm skills deploy-github --preset testing-max
```

**testing-min**: 3 skills - Test quality, async testing, test improvement
**testing-max**: 7 skills - Comprehensive testing, test automation, quality assurance

---

### Collaboration & Planning
```bash
# Collaboration essentials
claude-mpm skills deploy-github --preset collaboration-min

# Full collaboration stack
claude-mpm skills deploy-github --preset collaboration-max
```

**collaboration-min**: 2 skills - Idea refinement, design thinking, feature planning
**collaboration-max**: 5 skills - Team coordination, code reviews, planning, parallel work

---

## Interactive Mode

**NEW in v5.0**: Interactive checkbox selection for agents and skills!

### Interactive Agent Configuration
```bash
claude-mpm configure
```

**Features**:
- ✅ Checkbox selection with arrow keys
- ✅ Status column showing Installed/Available
- ✅ Pre-selection for already installed agents
- ✅ Apply/Adjust/Cancel menu
- ✅ Ability to adjust selections before applying
- ✅ Visual feedback with green checkboxes

**Workflow**:
1. Run `claude-mpm configure`
2. Use arrow keys to navigate, spacebar to select/deselect
3. Press Enter when done
4. Review selections in summary table
5. Choose: Apply, Adjust (go back), or Cancel

### Interactive Skill Configuration
```bash
claude-mpm skills configure
```

**Features**:
- ✅ Same UX as agents configure
- ✅ Checkbox selection interface
- ✅ Status detection (Installed/Available)
- ✅ Pre-selection for deployed skills
- ✅ Apply/Adjust/Cancel workflow

**Workflow**: Same as agents (see above)

### CLI Mode (Automation)

For scripts and automation, use command-line arguments:

```bash
# Deploy specific preset without interaction
claude-mpm configure --preset python-max

# Deploy skills from GitHub
claude-mpm skills deploy-github --preset python-max

# Force redeployment
claude-mpm configure --preset python-max --force
claude-mpm skills deploy-github --preset python-max --force
```

---

## Core Components

Every preset includes **CORE components** that provide essential functionality:

### CORE Agents (5 agents in every preset)

| Agent | Purpose | Why Essential |
|-------|---------|---------------|
| **mpm-agent-manager** | Agent lifecycle management | Deploy, update, and manage agents |
| **mpm-skills-manager** | Skills management | Deploy, update, and manage skills |
| **research** | Codebase investigation | Analyze code, understand architecture |
| **documentation** | Documentation generation | Create and maintain docs |
| **engineer** | General-purpose engineering | Handle diverse coding tasks |

### CORE Skills (1 skill in every preset)

| Skill | Purpose | Why Essential |
|-------|---------|---------------|
| **skill-creator** | Skill creation and management | Extend Claude's capabilities dynamically |

**Why Core Components?**
- **Self-sufficiency**: Can bootstrap additional components as needed
- **Universal utility**: Useful for ANY project type
- **Foundation**: Other specialized components build on these

---

## Usage Examples

### Example 1: Starting a New Next.js Project
```bash
# Start with MIN for quick setup
claude-mpm configure --preset nextjs-min
claude-mpm skills deploy-github --preset nextjs-min

# Later, upgrade to MAX for production
claude-mpm configure --preset nextjs-max
claude-mpm skills deploy-github --preset nextjs-max
```

### Example 2: Python API Development

**Phase 1: Prototype (MIN)**
```bash
claude-mpm configure --preset python-min
claude-mpm skills deploy-github --preset python-min

# Now you have: python-engineer, qa, ops, pytest, asyncio, mypy
```

**Phase 2: Production (MAX)**
```bash
claude-mpm configure --preset python-max
claude-mpm skills deploy-github --preset python-max

# Added: security, api-qa, refactoring, code-analyzer, testing-anti-patterns
```

### Example 3: React Component Library

**MIN for Initial Development**:
```bash
claude-mpm configure --preset react-min
claude-mpm skills deploy-github --preset react-min

# Focus: Core React development (8 agents, 3 skills)
```

**MAX for Production Library**:
```bash
claude-mpm configure --preset react-max
claude-mpm skills deploy-github --preset react-max

# Added: State machines, Headless UI, testing patterns, architecture skills
```

### Example 4: WordPress Plugin Development
```bash
# Start with fundamentals
claude-mpm skills deploy-github --preset wordpress-min

# Expand for block editor development
claude-mpm skills deploy-github --preset wordpress-max
```

### Example 5: Testing-Focused Project
```bash
# Deploy comprehensive testing stack
claude-mpm skills deploy-github --preset testing-max

# Includes: pytest, vitest, jest, testing-anti-patterns, condition-based-waiting
```

---

## Migration from Legacy Presets

### Legacy Preset Mapping

| Legacy Preset | New Equivalent | Recommendation |
|--------------|----------------|----------------|
| `python-dev` | `python-min` or `python-max` | Use MIN for simple projects, MAX for production |
| `javascript-backend` | `javascript-min` or `javascript-max` | Same as above |
| `react-dev` | `react-min` or `react-max` | Same as above |
| `nextjs-fullstack` | `nextjs-max` | Full-stack projects need MAX |
| `rust-dev` | `rust-min` or `rust-max` | Use MIN unless building complex systems |
| `golang-dev` | `golang-min` or `golang-max` | Same as Rust |
| `java-dev` | `java-min` or `java-max` | Same as above |
| `mobile-flutter` | `flutter-min` or `flutter-max` | Same as above |
| `data-eng` | `python-max` + custom | Data engineering benefits from MAX |

### Migration Steps

1. **Check current agents/skills**:
   ```bash
   claude-mpm agents list
   claude-mpm skills check-deployed
   ```

2. **Choose MIN or MAX**:
   - Review [MIN vs MAX Decision Guide](#min-vs-max-decision-guide)
   - Consider project complexity and requirements

3. **Deploy new preset**:
   ```bash
   claude-mpm configure --preset <toolchain>-min
   # OR
   claude-mpm configure --preset <toolchain>-max
   ```

4. **Deploy matching skills**:
   ```bash
   claude-mpm skills deploy-github --preset <toolchain>-min
   # OR
   claude-mpm skills deploy-github --preset <toolchain>-max
   ```

5. **Verify deployment**:
   ```bash
   claude-mpm agents list
   claude-mpm skills check-deployed
   ```

---

## Best Practices

### 1. Start with MIN, Upgrade to MAX
```bash
# Begin with essentials
claude-mpm configure --preset python-min

# Upgrade when needed
claude-mpm configure --preset python-max
```

**Why**: Faster startup, simpler mental model, upgrade as complexity grows

### 2. Match Agents and Skills
```bash
# Deploy matching presets
claude-mpm configure --preset nextjs-min
claude-mpm skills deploy-github --preset nextjs-min
```

**Why**: Agents and skills work together (e.g., react-engineer + react skills)

### 3. Use Interactive Mode for Exploration
```bash
# Explore available components
claude-mpm configure           # See all agents
claude-mpm skills configure     # See all skills
```

**Why**: Visual selection, see what's available, adjust before applying

### 4. Use CLI Mode for Automation
```bash
# In CI/CD or setup scripts
claude-mpm configure --preset python-max --force
claude-mpm skills deploy-github --preset python-max --force
```

**Why**: Reproducible, scriptable, no user interaction required

### 5. Check Deployed Status
```bash
# Before deploying
claude-mpm agents list
claude-mpm skills check-deployed

# After deploying
claude-mpm agents list
claude-mpm skills check-deployed
```

**Why**: Verify what's installed, avoid duplicates, understand current state

---

## Troubleshooting

### Preset Not Found
```bash
# Error: "Unknown preset: pytohn-min"
# Solution: Check spelling and available presets
claude-mpm configure --help
# Lists all available agent presets
```

### Agents Not Deploying
```bash
# Check for deployment errors
claude-mpm configure --preset python-min

# Force redeployment if needed
claude-mpm configure --preset python-min --force
```

### Skills Not Installing
```bash
# Check deployed skills
claude-mpm skills check-deployed

# Force reinstall
claude-mpm skills deploy-github --preset python-min --force

# Check collection configuration
claude-mpm skills collection-list
```

### Interactive Mode Not Working
```bash
# Ensure questionary is installed
pip install questionary>=5.0.2

# Or reinstall claude-mpm
pip install --upgrade claude-mpm
```

---

## Advanced Usage

### Combining Presets (NOT RECOMMENDED)
```bash
# Deploy multiple toolchain presets (use with caution)
claude-mpm configure --preset python-max
claude-mpm configure --preset javascript-max

# Warning: May result in many agents (resource intensive)
```

### Custom Preset Creation (Future)
```bash
# NOT YET IMPLEMENTED
# Future: Create custom presets
claude-mpm configure --create-preset my-stack \
  --agents python-engineer,react-engineer,qa \
  --description "My custom stack"
```

### Preset Validation (Future)
```bash
# NOT YET IMPLEMENTED
# Future: Validate preset configuration
claude-mpm configure --validate-preset python-max
```

---

## FAQ

**Q: Can I use multiple presets simultaneously?**
A: Yes, but it's not recommended. Deploy one preset and add individual components as needed.

**Q: What happens if I deploy MIN then MAX?**
A: MAX will add additional agents/skills. No duplicates are created.

**Q: Can I remove a preset?**
A: Remove individual agents/skills. Use `claude-mpm agents clean` or `claude-mpm skills remove --all`.

**Q: Do presets work with custom collections?**
A: Agent presets always work. Skill presets depend on collection availability.

**Q: How often are presets updated?**
A: Presets are updated with each Claude MPM release. Check release notes.

**Q: Can I suggest new presets?**
A: Yes! Open an issue on GitHub with your toolchain and use case.

---

## Related Documentation

- [Agent Configuration Guide](agents-configure-guide.md)
- [Skills Management Guide](skills-management-guide.md)
- [MIN/MAX Preset Reference](preset-reference.md)
- [Interactive Configure Mode](interactive-configure-mode.md)

---

**Version**: 5.0
**Last Updated**: 2025-12-02
**Related Ticket**: 1M-502 Phase 2 - UX Improvements
