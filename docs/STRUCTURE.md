# Claude MPM Project Structure

This document provides a comprehensive overview of the claude-mpm project structure. **Always refer to this document when creating new files to ensure they are placed in the correct location.**

Last Updated: 2025-01-24

## Project Overview

Claude MPM uses a standard Python project layout with the main package located in `src/claude_mpm/`. The project follows a service-oriented architecture with clear separation of concerns.

## Directory Structure

```
claude-mpm/
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
│   │   ├── agent-template.yaml       # Meta-template for generating agents
│   │   └── templates/                # Agent templates (JSON format)
│   │       ├── documentation_agent.json
│   │       ├── engineer_agent.json
│   │       ├── qa_agent.json
│   │       ├── research_agent.json
│   │       ├── security_agent.json
│   │       └── ...                  # Other agent templates
│   │
│   ├── config/                       # Configuration module
│   │   └── hook_config.py            # Hook configuration
│   │
│   ├── core/                         # Core components
│   │   ├── __init__.py
│   │   ├── agent_registry.py         # Agent registry implementation
│   │   ├── simple_runner.py          # Main runner implementation
│   │   ├── framework_loader.py       # Framework loading
│   │   └── ...
│   │
│
│   ├── hooks/                        # Hook system
│   │   ├── base_hook.py              # Base hook class
│   │   ├── hook_client.py            # Hook client implementation
│   │   └── builtin/                  # Built-in hooks
│   │
│   ├── services/                     # Service layer
│   │   ├── ticket_manager.py         # Ticket management service
│   │   ├── agent_deployment.py       # Agent deployment service
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
- **simple_runner.py**: Main runner implementation
- **framework_loader.py**: Loads INSTRUCTIONS.md (or legacy CLAUDE.md) and framework instructions

### `/src/claude_mpm/agents/` - Agent System
- **agent-template.yaml**: Meta-template for generating new agent profiles
- **templates/**: Pre-defined agent templates in JSON format (documentation, engineer, QA, research, security, etc.)
- Agent templates are dynamically discovered and loaded by the agent registry


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
2. **Agent templates**: Place in `/src/claude_mpm/agents/templates/` (as JSON files)
3. **Service classes**: Place in `/src/claude_mpm/services/`
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
5. Agent templates use JSON format

## Recent Additions

- **Hook System**: Complete extensibility framework
- **Tree-sitter Integration**: AST-level code analysis for 41+ programming languages
  - Enables advanced code understanding in Research Agent operations
  - Powers real-time agent modification tracking with syntax awareness
  - Provides fast, incremental parsing for performance-critical operations

## Design Patterns

1. **Service-Oriented Architecture**: Business logic in service layer
2. **Plugin Architecture**: Hook system for extensibility
3. **Registry Pattern**: Dynamic agent discovery
5. **Adapter Pattern**: Integration with external systems