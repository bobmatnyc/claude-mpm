# Claude MPM Project Structure

This document provides a comprehensive overview of the claude-mpm project structure. **Always refer to this document when creating new files to ensure they are placed in the correct location.**

**🔧 Structure Enforcement**: This project includes an automated structure linting system that validates file placement and prevents violations. See [STRUCTURE_LINTING.md](STRUCTURE_LINTING.md) for details.

Last Updated: 2025-08-17

## Project Overview

Claude MPM uses a standard Python project layout with the main package located in `src/claude_mpm/`. The project follows a service-oriented architecture with clear separation of concerns.

## Directory Structure

```
claude-mpm/
├── .claude/                          # Claude-specific settings
│   ├── settings.json                 # Claude settings
│   └── hooks/                        # Claude hooks directory
│
├── .claude-mpm/                      # Project-specific Claude MPM directory
│   ├── agents/                       # PROJECT tier agent definitions (highest precedence)
│   │   ├── engineer.md               # Override system engineer with project customizations
│   │   ├── custom_domain.json        # Project-specific domain agent
│   │   # Agents support .md, .json, and .yaml formats in flat directory structure
│   ├── config/                       # Project configuration
│   ├── hooks/                        # Project-specific hooks
│   └── logs/                         # Project log files
│
├── docs/                             # Documentation
│   ├── archive/                      # Archived documentation and QA reports
│   │   ├── changelogs/              # Historical changelog files
│   │   ├── implementation-status/   # Implementation status reports
│   │   ├── qa-reports/              # Quality assurance reports
│   │   ├── test-results/            # Test execution results
│   │   └── user/                    # Archived user documentation
│   ├── assets/                       # Documentation assets (images, diagrams)
│   │   └── claude-mpm.png           # Project logo
│   ├── dashboard/                    # Dashboard documentation
│   ├── design/                       # Design documents and technical specifications
│   ├── developer/                    # Developer documentation (API, internals, guides)
│   ├── examples/                     # Usage examples and configurations
│   ├── qa/                           # QA reports and test documentation
│   ├── user/                         # User-facing documentation
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
│   ├── agents/                       # Agent-specific tests
│   ├── e2e/                          # End-to-end tests
│   ├── fixtures/                     # Test fixtures and data
│   ├── integration/                  # Integration tests
│   ├── services/                     # Service layer tests
│   ├── test-reports/                 # Test execution reports
│   └── test_*.py                     # Unit and integration tests
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

### Agent Tier System
The system supports three tiers of agents with clear precedence:

1. **PROJECT Tier** (`.claude-mpm/agents/` in current project)
   - Highest precedence
   - Project-specific customizations and domain agents
   - Can override USER and SYSTEM agents
   - Supports `.md`, `.json`, and `.yaml` formats
   - Automatically discovered and cached

2. **USER Tier** (`~/.claude-mpm/agents/` in user home)
   - User-level customizations across projects
   - Can override SYSTEM agents
   - Useful for personal preferences and workflows

3. **SYSTEM Tier** (`/src/claude_mpm/agents/templates/`) - Framework built-in agents
   - Framework built-in agents (lowest precedence)
   - Maintained by Claude MPM developers
   - Fallback when no higher-tier agent exists

### `/src/claude_mpm/schemas/` - Validation Schemas
- **agent_schema.json**: JSON Schema for agent validation (v2.0.0)
  - Enforces required fields: id, version, metadata, capabilities, instructions
  - Validates resource tiers and tool assignments
  - Ensures consistent agent behavior

### `/src/claude_mpm/validation/` - Validation Framework
- **agent_validator.py**: Validates agents against schema
- **migration.py**: Utilities for migrating old agent formats


### `/src/claude_mpm/services/` - Service Layer
Modern service-oriented architecture with clear separation of concerns:

#### Core Services (`/src/claude_mpm/services/core/`)
- **interfaces.py**: Comprehensive interface definitions for all service contracts
- **base.py**: Base service classes (`BaseService`, `SyncBaseService`, `SingletonService`)

#### Agent Services (`/src/claude_mpm/services/agents/`)
- **deployment/**: Agent deployment and lifecycle management
  - **agent_deployment.py**: Core deployment service (`AgentDeploymentService`)
  - **agent_lifecycle_manager.py**: Lifecycle management (`AgentLifecycleManager`)
  - **agent_versioning.py**: Version management (`AgentVersionManager`)
  - **pipeline/**: Deployment pipeline components
  - **strategies/**: Deployment strategy implementations
- **memory/**: Agent memory and persistence services
  - **agent_memory_manager.py**: Memory management (`AgentMemoryManager`)
  - **agent_persistence_service.py**: Persistence operations (`AgentPersistenceService`)
- **registry/**: Agent discovery and modification tracking
  - **agent_registry.py**: Central registry (`AgentRegistry`)
  - **deployed_agent_discovery.py**: Discovery service (`DeployedAgentDiscovery`)
  - **modification_tracker.py**: Change tracking (`AgentModificationTracker`)
- **loading/**: Agent profile loading services
  - **agent_profile_loader.py**: Profile loading (`AgentProfileLoader`)
  - **framework_agent_loader.py**: Framework loader (`FrameworkAgentLoader`)
  - **base_agent_manager.py**: Base management (`BaseAgentManager`)
- **management/**: Agent capabilities and management
  - **agent_management_service.py**: Management service (`AgentManager`)
  - **agent_capabilities_generator.py**: Capabilities generation (`AgentCapabilitiesGenerator`)

#### Communication Services (`/src/claude_mpm/services/communication/`)
- **socketio.py**: SocketIO server implementation for real-time communication
- **websocket.py**: WebSocket client management

#### Project Services (`/src/claude_mpm/services/project/`)
- **analyzer.py**: Project structure and technology detection
- **registry.py**: Project registration and metadata management

#### Infrastructure Services (`/src/claude_mpm/services/infrastructure/`)
- **logging.py**: Structured logging service
- **monitoring.py**: Health monitoring and metrics collection

#### Framework Services
- **framework_claude_md_generator/**: INSTRUCTIONS.md/CLAUDE.md generation and management
  - **content_assembler.py**: Assembles content with dynamic agent capabilities
  - **deployment_manager.py**: Manages deployment with fresh capability generation
- **memory/**: Agent memory system
  - **builder.py**: Memory construction and optimization
  - **router.py**: Memory routing and management
  - **optimizer.py**: Memory optimization and cleanup
  - **cache/**: Caching services for performance

#### Other Services
- **hook_service.py**: Hook service for extensibility
- **ticket_manager.py**: Ticket management and tracking
- **version_control/**: Git integration and version management

### `/src/claude_mpm/hooks/` - Hook System
Extensibility through pre/post hooks:
- **base_hook.py**: Base classes for hooks
- **builtin/**: Example hook implementations

### `/docs/` - Documentation
Project documentation including this structure guide:
- **archive/**: Historical documentation, QA reports, and archived materials
- **assets/**: Images, diagrams, and other documentation assets
- **dashboard/**: Dashboard-specific documentation
- **design/**: Technical design documents and specifications
- **developer/**: API reference, internals, and developer guides
- **examples/**: Usage examples and configuration templates
- **user/**: End-user documentation and guides

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
2. **Agent definitions**: 
   - **Project agents**: Place in `.claude-mpm/agents/` (highest precedence)
   - **User agents**: Place in `~/.claude-mpm/agents/` 
   - **System agents**: Built-in framework agents in `/src/claude_mpm/agents/templates/` (framework development only)
3. **Service classes**: Place in `/src/claude_mpm/services/`
4. **Validation schemas**: Place in `/src/claude_mpm/schemas/`
5. **Hook implementations**: Place in `/src/claude_mpm/hooks/builtin/`
6. **Tests**: Place in `/tests/` with `test_` prefix
   - Unit tests: `/tests/test_*.py`
   - Integration tests: `/tests/integration/` or `/tests/test_*.py` (with clear naming)
   - E2E tests: `/tests/e2e/`
   - Agent tests: `/tests/agents/`
   - Service tests: `/tests/services/`
   - Test data: `/tests/fixtures/`
   - Test reports: `/tests/test-reports/`
7. **Documentation**: Place in `/docs/`
   - User guides: `/docs/user/`
   - Developer docs: `/docs/developer/`
   - Design docs: `/docs/design/`
   - Dashboard docs: `/docs/dashboard/`
   - Examples: `/docs/examples/`
   - Assets: `/docs/assets/`
   - Archives: `/docs/archive/`
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
5. Agent files support multiple formats: JSON, Markdown (.md), and YAML

## Recent Additions

- **Hook System**: Complete extensibility framework
- **Tree-sitter Integration**: AST-level code analysis for 41+ programming languages
  - Enables advanced code understanding in Research Agent operations
  - Powers real-time agent modification tracking with syntax awareness
  - Provides fast, incremental parsing for performance-critical operations
- **Project Reorganization** (v3.4.5): Major cleanup and reorganization
- **Service Layer Refactoring** (v3.8.2): Service-oriented architecture with 50-80% performance improvements
  - Moved 458+ test files from `/scripts/` to `/tests/` directory
  - Created `/docs/archive/` for historical documentation and QA reports
  - Added `/docs/assets/` for documentation resources
  - Enhanced `/tests/fixtures/` for test data management
  - Added backward compatibility wrapper (`ticket_wrapper.py`) for moved functionality

## Design Patterns

1. **Service-Oriented Architecture**: Business logic organized into specialized service domains
2. **Interface-Based Contracts**: All major services implement well-defined interfaces
3. **Dependency Injection**: Services use dependency injection container for loose coupling
4. **Lazy Loading**: Performance optimization through deferred resource initialization
5. **Plugin Architecture**: Hook system for extensibility
6. **Registry Pattern**: Dynamic agent discovery and management
7. **Factory Pattern**: Service factories for creating configured instances
8. **Singleton Pattern**: Shared resources and configuration management
9. **Adapter Pattern**: Integration with external systems
10. **Observer Pattern**: Event-driven communication between services