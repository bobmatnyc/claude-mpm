# Claude MPM Code Navigation Guide

This directory contains comprehensive documentation for navigating and understanding the Claude MPM codebase. These documents serve as quick-reference guides for future development work.

## Contents

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE-OVERVIEW.md](ARCHITECTURE-OVERVIEW.md) | High-level architecture and design patterns |
| [CODE-PATHS.md](CODE-PATHS.md) | Key code paths and entry points |
| [SERVICE-LAYER.md](SERVICE-LAYER.md) | Detailed service architecture and dependencies |
| [AGENT-SYSTEM.md](AGENT-SYSTEM.md) | Agent templates, loading, and deployment |
| [HOOKS-AND-EXTENSIONS.md](HOOKS-AND-EXTENSIONS.md) | Hook system and extensibility points |
| [CLI-STRUCTURE.md](CLI-STRUCTURE.md) | CLI commands and parsers |
| [SKILLS-SYSTEM.md](SKILLS-SYSTEM.md) | Skills management and integration |
| [TECHNICAL-DEBT.md](TECHNICAL-DEBT.md) | Known issues and improvement areas |

## Quick Links

### Core Entry Points
- **Main CLI**: `src/claude_mpm/cli/__main__.py`
- **Package Init**: `src/claude_mpm/__init__.py`
- **Service Container**: `src/claude_mpm/core/container.py`

### Key Services
- **Agent Services**: `src/claude_mpm/services/agents/`
- **Hook System**: `src/claude_mpm/hooks/`
- **Skills System**: `src/claude_mpm/skills/`
- **MCP Gateway**: `src/claude_mpm/services/mcp_gateway/`

### Configuration
- **Project Config**: `.claude-mpm/configuration.yaml`
- **User Config**: `~/.claude-mpm/configuration.yaml`
- **Agent Templates**: `src/claude_mpm/agents/templates/`

## How to Use These Guides

1. **New Feature Development**: Start with ARCHITECTURE-OVERVIEW.md to understand where your feature fits
2. **Bug Fixes**: Use CODE-PATHS.md to trace execution flow
3. **Service Changes**: Consult SERVICE-LAYER.md for dependency information
4. **Agent Work**: Reference AGENT-SYSTEM.md for template and deployment patterns
5. **Extension Development**: See HOOKS-AND-EXTENSIONS.md for hook points

## Keeping Documents Updated

These documents should be updated when:
- New services or modules are added
- Architecture patterns change
- Major refactoring occurs
- New entry points or code paths are created

---
Last Updated: 2025-11-29
