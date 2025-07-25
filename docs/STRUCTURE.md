# Claude MPM Project Structure

This document provides a comprehensive overview of the claude-mpm project structure. **Always refer to this document when creating new files to ensure they are placed in the correct location.**

Last Updated: 2025-01-24

## Project Overview

Claude MPM uses a standard Python project layout with the main package located in `src/claude_mpm/`. The project follows a service-oriented architecture with clear separation of concerns.

## Directory Structure

```
claude-mpm/
├── .ai-trackdown/                    # AI Trackdown integration
│   ├── cache/                        # Cache directory
│   ├── config.yaml                   # AI Trackdown configuration
│   ├── project.yaml                  # Project-specific config
│   ├── schemas/                      # Schema definitions
│   └── templates/                    # Template files
│
├── .claude/                          # Claude-specific settings
│   ├── settings.json                 # Claude settings
│   └── hooks/                        # Claude hooks directory
│
├── .claude-pm/                       # Claude PM framework directory
│   ├── agents/                       # Agent definitions
│   │   └── project-specific/         # Project-specific agents
│   ├── config/                       # Framework configuration
│   └── logs/                         # Log files
│
├── docs/                             # Documentation
│   ├── design/                       # Design documents
│   ├── claude_launcher_migration.md  # Migration guide for ClaudeLauncher
│   └── STRUCTURE.md                  # This file
│
├── examples/                         # Example implementations
│   └── todo_hijacker_demo.py         # Todo hijacking demonstration
│
├── scripts/                          # ALL executable scripts and utilities
│   ├── claude-mpm                    # Main executable script
│   ├── run_mpm.py                    # Python runner for MPM
│   ├── demo/                         # Demo scripts
│   └── test_*.py                     # Test scripts (temporary/debugging)
│
├── src/claude_mpm/                   # Main source code (Python package)
│   ├── __init__.py                   # Package initialization
│   ├── __main__.py                   # Entry point for python -m
│   ├── _version.py                   # Version management
│   ├── cli.py                        # CLI implementation
│   ├── cli_main.py                   # CLI main entry point
│   │
│   ├── agents/                       # Agent system
│   │   ├── templates/                # Agent templates
│   │   │   ├── documentation_agent.md
│   │   │   ├── engineer_agent.md
│   │   │   ├── qa_agent.md
│   │   │   └── ...
│   │   └── base_agent.md             # Base agent template
│   │
│   ├── config/                       # Configuration module
│   │   └── hook_config.py            # Hook configuration
│   │
│   ├── core/                         # Core components
│   │   ├── __init__.py
│   │   ├── agent_registry.py         # Agent registry implementation
│   │   ├── claude_launcher.py        # Unified Claude CLI launcher (NEW)
│   │   ├── framework_loader.py       # Framework loading
│   │   └── ...
│   │
│   ├── framework/                    # Framework files
│   │   ├── INSTRUCTIONS.md           # Main framework instructions (legacy: CLAUDE.md)
│   │   ├── agent-roles/              # Agent role definitions
│   │   └── ...
│   │
│   ├── hooks/                        # Hook system
│   │   ├── base_hook.py              # Base hook class
│   │   ├── hook_client.py            # Hook client implementation
│   │   └── builtin/                  # Built-in hooks
│   │
│   ├── orchestration/                # Orchestration layer
│   │   ├── orchestrator.py           # Base orchestrator
│   │   ├── subprocess_orchestrator.py # Subprocess orchestrator
│   │   ├── todo_hijacker.py          # Todo hijacking system
│   │   └── ...
│   │
│   ├── services/                     # Service layer
│   │   ├── hook_service.py           # Hook service
│   │   ├── hook_service_manager.py   # Hook service manager
│   │   └── ...
│   │
│   └── utils/                        # Utilities
│       └── logger.py                 # Logging utilities
│
├── tests/                            # ALL test files (pytest/unittest)
│   ├── test_*.py                     # Unit and integration tests
│   ├── e2e/                          # End-to-end tests
│   └── fixtures/                     # Test fixtures and data
│
├── setup.py                          # Setup script
├── pyproject.toml                    # Python project configuration
└── README.md                         # Project documentation
```

## Key Directories and Their Purpose

### `/src/claude_mpm/` - Main Package
The main Python package following the src layout pattern. All source code lives here.

### `/src/claude_mpm/core/` - Core Components
- **agent_registry.py**: Dynamic agent discovery and management
- **claude_launcher.py**: Unified launcher for Claude CLI (consolidates all subprocess calls)
- **framework_loader.py**: Loads INSTRUCTIONS.md (or legacy CLAUDE.md) and framework instructions

### `/src/claude_mpm/agents/` - Agent System
- **templates/**: Pre-defined agent templates (documentation, engineer, QA, etc.)
- **base_agent.md**: Base template for all agents

### `/src/claude_mpm/orchestration/` - Orchestration Layer
Different orchestration strategies for running Claude:
- **orchestrator.py**: Base orchestrator class
- **subprocess_orchestrator.py**: Uses subprocess for delegations
- **interactive_subprocess_orchestrator.py**: Interactive subprocess mode
- **todo_hijacker.py**: Intercepts and transforms TODOs into agent delegations

### `/src/claude_mpm/services/` - Service Layer
Business logic and service implementations:
- **hook_service.py**: Hook service for extensibility
- **Agent services**: Lifecycle, management, and profile loading
- **Framework services**: INSTRUCTIONS.md/CLAUDE.md generation and management
- **agent_modification_tracker/**: Real-time agent modification tracking
  - Uses **tree-sitter** for AST-level code analysis
  - **TreeSitterAnalyzer** provides syntax-aware parsing for 41+ languages
  - Supports real-time monitoring, backups, and cache invalidation
  - Enables Research Agent's advanced code analysis capabilities

### `/src/claude_mpm/hooks/` - Hook System
Extensibility through pre/post hooks:
- **base_hook.py**: Base classes for hooks
- **builtin/**: Example hook implementations

### `/docs/` - Documentation
Project documentation including this structure guide.

### `/scripts/` - Executable Scripts and Utilities
All executable scripts and command-line utilities should be placed here:
- **claude-mpm**: Main executable bash script
- **run_mpm.py**: Python runner for MPM
- **demo/**: Demo and example scripts
- **Debugging scripts**: Temporary test scripts for debugging (prefix with `test_`)
- **Migration scripts**: Database or data migration scripts
- **Build scripts**: Build and deployment automation

## File Placement Guidelines

When creating new files, follow these guidelines:

1. **Python modules**: Place in appropriate subdirectory under `/src/claude_mpm/`
2. **Agent templates**: Place in `/src/claude_mpm/agents/templates/`
3. **New orchestrators**: Place in `/src/claude_mpm/orchestration/`
4. **Service classes**: Place in `/src/claude_mpm/services/`
5. **Hook implementations**: Place in `/src/claude_mpm/hooks/builtin/`
6. **Tests**: Place in `/tests/` with `test_` prefix
   - Unit tests: `/tests/test_*.py`
   - Integration tests: `/tests/test_*.py` (with clear naming)
   - E2E tests: `/tests/e2e/`
   - Test data: `/tests/fixtures/`
7. **Documentation**: Place in `/docs/`
   - Design docs: `/docs/design/`
   - User guides: `/docs/`
8. **Scripts**: Place in `/scripts/`
   - Executable scripts: `/scripts/*.py` or `/scripts/*.sh`
   - Demo scripts: `/scripts/demo/`
   - **NEVER place scripts in the project root directory**
   - **NEVER place test files outside of `/tests/`**

## Important Notes

1. The project uses the standard Python "src layout" where the package lives in `src/`
2. All imports should use the full package name: `from claude_mpm.core import ...`
3. The main entry points are:
   - `/scripts/claude-mpm` (bash script)
   - `/src/claude_mpm/cli_main.py` (Python entry point)
4. Configuration files use YAML format
5. Agent templates use Markdown format

## Recent Additions

- **ClaudeLauncher** (`/src/claude_mpm/core/claude_launcher.py`): Unified subprocess launcher for all Claude CLI calls
- **Todo Hijacking System**: Advanced TODO interception and transformation
- **Hook System**: Complete extensibility framework
- **Interactive Subprocess Orchestrator**: Enhanced interactive mode support
- **Tree-sitter Integration**: AST-level code analysis for 41+ programming languages
  - Enables advanced code understanding in Research Agent operations
  - Powers real-time agent modification tracking with syntax awareness
  - Provides fast, incremental parsing for performance-critical operations

## Design Patterns

1. **Service-Oriented Architecture**: Business logic in service layer
2. **Plugin Architecture**: Hook system for extensibility
3. **Strategy Pattern**: Multiple orchestrator implementations
4. **Registry Pattern**: Dynamic agent discovery
5. **Adapter Pattern**: Integration with external systems