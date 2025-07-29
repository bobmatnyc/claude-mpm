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
│   ├── cli/                          # CLI implementation (modular structure)
│   │   ├── __init__.py               # Main entry point - orchestrates CLI flow
│   │   ├── parser.py                 # Argument parsing logic
│   │   ├── utils.py                  # Shared utility functions
│   │   ├── commands/                 # Individual command implementations
│   │   │   ├── __init__.py
│   │   │   ├── run.py                # Default command - runs Claude sessions
│   │   │   ├── tickets.py            # Lists tickets
│   │   │   ├── info.py               # Shows system information
│   │   │   ├── agents.py             # Manages agent deployments
│   │   │   └── ui.py                 # Terminal UI launcher
│   │   └── README.md                 # CLI architecture documentation
│   │
│   ├── cli_old.py                    # Legacy CLI (preserved for reference)
│   ├── cli_enhancements.py           # Experimental Click-based CLI
│   │
│   ├── agents/                       # Agent system
│   │   ├── agent-template.yaml       # Meta-template for generating agents
│   │   ├── documentation.json        # Documentation agent (v2.0.0 format)
│   │   ├── engineer.json             # Engineer agent (v2.0.0 format)
│   │   ├── qa.json                   # QA agent (v2.0.0 format)
│   │   ├── research.json             # Research agent (v2.0.0 format)
│   │   ├── security.json             # Security agent (v2.0.0 format)
│   │   └── ...                      # Other agent definitions
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
│   ├── schemas/                      # JSON schemas for validation
│   │   └── agent_schema.json         # Agent definition schema (v2.0.0)
│   │
│   ├── validation/                   # Validation framework
│   │   ├── __init__.py
│   │   ├── agent_validator.py        # Agent schema validator
│   │   └── migration.py              # Migration utilities
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
- **Agent JSON files**: Standardized agent definitions (v2.0.0 format)
  - Uses clean IDs without `_agent` suffix (e.g., `research.json` not `research_agent.json`)
  - All agents validated against `/src/claude_mpm/schemas/agent_schema.json`
  - Includes resource tier assignments (intensive, standard, lightweight)
- Agent templates are dynamically discovered and loaded by the agent registry

### `/src/claude_mpm/schemas/` - Validation Schemas
- **agent_schema.json**: JSON Schema for agent validation (v2.0.0)
  - Enforces required fields: id, version, metadata, capabilities, instructions
  - Validates resource tiers and tool assignments
  - Ensures consistent agent behavior

### `/src/claude_mpm/validation/` - Validation Framework
- **agent_validator.py**: Validates agents against schema
- **migration.py**: Utilities for migrating old agent formats


### `/src/claude_mpm/services/` - Service Layer
Business logic and service implementations:
- **hook_service.py**: Hook service for extensibility
- **Agent services**: Lifecycle, management, and profile loading
  - **deployed_agent_discovery.py**: Discovers and analyzes deployed agents
  - **agent_capabilities_generator.py**: Generates dynamic agent documentation
- **Framework services**: INSTRUCTIONS.md/CLAUDE.md generation and management
  - **content_assembler.py**: Assembles content with dynamic agent capabilities
  - **deployment_manager.py**: Manages deployment with fresh capability generation
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
2. **Agent definitions**: Place in `/src/claude_mpm/agents/` (as JSON files with clean IDs)
3. **Service classes**: Place in `/src/claude_mpm/services/`
4. **Validation schemas**: Place in `/src/claude_mpm/schemas/`
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
   - `/src/claude_mpm/__main__.py` (Python module entry point)
   - `/src/claude_mpm/cli/__init__.py` (CLI implementation)
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