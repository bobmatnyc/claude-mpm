# Project Organization Standard

**Version**: 1.0.0
**Last Updated**: 2025-10-08
**Applies To**: Claude MPM v4.4.2+

This document defines the official organization standards used by Claude MPM's `/mpm-organize` command and should be followed by all contributors and AI agents working on this project.

---

## Table of Contents

1. [Overview](#overview)
2. [Core Principles](#core-principles)
3. [Directory Structure](#directory-structure)
4. [File Placement Rules](#file-placement-rules)
5. [Naming Conventions](#naming-conventions)
6. [Module Organization](#module-organization)
7. [Testing Organization](#testing-organization)
8. [Documentation Structure](#documentation-structure)
9. [Script Organization](#script-organization)
10. [Agent Organization](#agent-organization)
11. [Framework-Specific Rules](#framework-specific-rules)
12. [Validation and Enforcement](#validation-and-enforcement)
13. [Migration Procedures](#migration-procedures)

---

## Overview

Claude MPM follows a **service-oriented architecture** with clear separation of concerns. The organization system enforces consistent structure through:

- **Automated structure linting**: Validates file placement during builds
- **Pattern detection**: Learns and enforces project-specific conventions
- **Framework awareness**: Respects framework-specific requirements
- **Git integration**: Uses `git mv` to preserve file history

## Core Principles

### 1. Separation of Concerns
- **Source code** (`/src/claude_mpm/`): Production Python package code only
- **Tests** (`/tests/`): All test files, fixtures, and test utilities
- **Scripts** (`/scripts/`): Executable utilities organized by purpose
- **Documentation** (`/docs/`): All project documentation
- **Temporary files** (`/tmp/`): Ephemeral files, never committed

### 2. Discoverability
- Files should be in predictable locations based on their purpose
- Follow established patterns consistently
- Use descriptive names that indicate file purpose
- Group related files together

### 3. Maintainability
- Keep files focused on single responsibilities
- Split files exceeding 800 lines (refactor at 600+ lines)
- Avoid deep nesting (max 4-5 levels)
- Use clear, hierarchical organization

### 4. Framework Compatibility
- Respect framework-specific conventions (Next.js, Django, Rails, etc.)
- Don't fight the framework's preferred structure
- Document any deviations from framework standards

---

## Directory Structure

### Top-Level Organization

```
claude-mpm/
├── .claude/                    # Claude Code settings (IDE-specific)
├── .claude-mpm/                # Project-level Claude MPM config
├── docs/                       # ALL documentation
├── scripts/                    # ALL executable scripts
├── src/claude_mpm/             # Source code (Python package)
├── tests/                      # ALL tests
├── tmp/                        # Temporary files (gitignored)
├── examples/                   # Example implementations
├── CLAUDE.md                   # Development guidelines (this project)
├── README.md                   # User-facing documentation
└── pyproject.toml              # Python project configuration
```

### Source Code Structure (`/src/claude_mpm/`)

```
src/claude_mpm/
├── __init__.py                 # Package initialization
├── __main__.py                 # Entry point for `python -m claude_mpm`
├── _version.py                 # Version management
│
├── agents/                     # Agent system
│   ├── INSTRUCTIONS.md         # PM instructions (loaded by framework)
│   ├── BASE_PM.md              # Base PM agent definition
│   ├── BASE_*.md               # Base agent definitions
│   └── templates/              # SYSTEM-tier agent templates
│       ├── engineer.json
│       ├── project_organizer.json
│       └── *.json              # Agent definitions
│
├── cli/                        # CLI implementation
│   ├── __init__.py             # Main CLI orchestration
│   ├── parser.py               # Argument parsing
│   ├── utils.py                # Shared CLI utilities
│   └── commands/               # Individual command implementations
│       ├── run.py              # Default command
│       ├── agents.py           # Agent management
│       └── *.py                # Other commands
│
├── commands/                   # Slash command definitions
│   ├── mpm-organize.md         # /mpm-organize documentation
│   ├── mpm-init.md             # /mpm-init documentation
│   └── *.md                    # Other slash commands
│
├── core/                       # Core framework components
│   ├── agent_registry.py       # Agent discovery and management
│   ├── simple_runner.py        # Main runner implementation
│   └── framework_loader.py     # Framework instruction loading
│
├── schemas/                    # JSON schemas for validation
│   └── agent_schema.json       # Agent definition schema
│
├── validation/                 # Validation framework
│   ├── agent_validator.py      # Agent schema validation
│   └── migration.py            # Agent migration utilities
│
├── services/                   # Service layer (see Service Organization)
│   ├── core/                   # Core service interfaces and base classes
│   ├── agents/                 # Agent lifecycle and management
│   ├── communication/          # WebSocket and SocketIO
│   ├── project/                # Project analysis and registry
│   └── infrastructure/         # Logging, monitoring, metrics
│
├── hooks/                      # Hook system for extensibility
│   ├── base_hook.py            # Base hook classes
│   ├── hook_client.py          # Hook client implementation
│   └── builtin/                # Built-in hook implementations
│
├── dashboard/                  # Dashboard application
│   ├── app.py                  # Dashboard server
│   ├── static/                 # Static assets
│   └── templates/              # HTML templates
│
└── utils/                      # Shared utilities
    └── logger.py               # Logging utilities
```

### Service Organization (`/src/claude_mpm/services/`)

```
services/
├── core/                       # Core service framework
│   ├── interfaces.py           # Service interface definitions
│   ├── base.py                 # Base service classes
│   └── container.py            # Dependency injection container
│
├── agents/                     # Agent services
│   ├── deployment/             # Agent deployment
│   │   ├── agent_deployment.py
│   │   ├── agent_lifecycle_manager.py
│   │   ├── pipeline/           # Deployment pipeline
│   │   └── strategies/         # Deployment strategies
│   ├── memory/                 # Agent memory management
│   ├── registry/               # Agent discovery and tracking
│   ├── loading/                # Agent profile loading
│   └── management/             # Agent capabilities and management
│
├── communication/              # Communication services
│   ├── socketio.py             # SocketIO server
│   └── websocket.py            # WebSocket client
│
├── project/                    # Project services
│   ├── analyzer.py             # Project structure analysis
│   └── registry.py             # Project metadata management
│
└── infrastructure/             # Infrastructure services
    ├── logging.py              # Structured logging
    └── monitoring.py           # Health monitoring
```

### Documentation Structure (`/docs/`)

```
docs/
├── README.md                   # Documentation index (START HERE)
│
├── developer/                  # Developer documentation
│   ├── ARCHITECTURE.md         # Service-oriented architecture
│   ├── STRUCTURE.md            # Project structure (authoritative)
│   ├── SERVICES.md             # Service development guide
│   ├── TESTING.md              # Testing strategies
│   ├── QA.md                   # Quality assurance procedures
│   ├── LINTING.md              # Linting and code quality
│   └── OUTPUT_STYLE.md         # Agent response formatting
│
├── reference/                  # Reference documentation
│   ├── PROJECT_ORGANIZATION.md # This file
│   ├── DEPLOY.md               # Deployment procedures
│   ├── VERSIONING.md           # Version management
│   └── SECURITY.md             # Security framework
│
├── user/                       # User documentation
│   ├── getting-started/        # Getting started guides
│   ├── 03-features/            # Feature documentation
│   └── MIGRATION.md            # Migration guides
│
├── design/                     # Design documents
│   └── *.md                    # Technical specifications
│
├── examples/                   # Usage examples
│   └── *.md                    # Configuration examples
│
├── assets/                     # Documentation assets
│   └── *.png                   # Images and diagrams
│
├── dashboard/                  # Dashboard documentation
│   └── *.md                    # Dashboard guides
│
└── _archive/                   # Archived documentation
    ├── changelogs/             # Historical changelogs
    ├── qa-reports/             # QA reports
    └── test-results/           # Test results
```

### Script Organization (`/scripts/`)

```
scripts/
├── claude-mpm                  # Main executable (bash)
├── run_mpm.py                  # Python runner
├── install.sh                  # Installation script
├── uninstall.sh                # Uninstallation script
├── build-*.sh                  # Build scripts
│
├── development/                # Development tools
│   ├── debug_*.py              # Debugging scripts
│   ├── run_all_tests.sh        # Test runner
│   ├── run_lint.sh             # Linting runner
│   └── diagnose_*.py           # Diagnostic tools
│
├── monitoring/                 # Monitoring tools
│   ├── monitor_*.py            # Monitoring scripts
│   └── socketio_server.py      # Server monitoring
│
├── utilities/                  # Configuration and utilities
│   ├── configure_mcp_*.py      # MCP configuration
│   ├── mcp_*.py                # MCP utilities
│   ├── eventbus_*.py           # Event bus tools
│   └── generate_*.py           # Code generation
│
└── verification/               # Verification tools
    ├── verify_*.py             # Verification scripts
    └── test_*.py               # Integration tests
```

### Test Organization (`/tests/`)

```
tests/
├── conftest.py                 # Pytest configuration
├── test_*.py                   # Unit tests
│
├── agents/                     # Agent-specific tests
│   └── test_*.py
│
├── cli/                        # CLI tests
│   └── commands/               # Command tests
│       └── test_*.py
│
├── e2e/                        # End-to-end tests
│   └── test_*.py
│
├── integration/                # Integration tests
│   └── test_*.py
│
├── services/                   # Service layer tests
│   ├── agents/                 # Agent service tests
│   ├── communication/          # Communication tests
│   └── *.py                    # Other service tests
│
├── fixtures/                   # Test fixtures and data
│   ├── agents/                 # Agent test fixtures
│   └── *.json                  # Test data files
│
└── test-reports/               # Test execution reports
    └── *.xml                   # JUnit XML reports
```

---

## File Placement Rules

### By File Type

| File Type | Location | Examples |
|-----------|----------|----------|
| Python modules | `/src/claude_mpm/[module]/` | `agent_registry.py` |
| Agent definitions | `.claude-mpm/agents/` (project)<br>`~/.claude-mpm/agents/` (user)<br>`/src/claude_mpm/agents/templates/` (system) | `engineer.json`, `custom_agent.md` |
| Service classes | `/src/claude_mpm/services/[domain]/` | `agent_deployment.py` |
| Tests | `/tests/[category]/` | `test_agent_registry.py` |
| Documentation | `/docs/[category]/` | `ARCHITECTURE.md` |
| Scripts | `/scripts/[purpose]/` | `debug_agents.py` |
| Temporary files | `/tmp/` | `test_output.log` |
| JSON schemas | `/src/claude_mpm/schemas/` | `agent_schema.json` |
| Hooks | `/src/claude_mpm/hooks/builtin/` | `response_logger.py` |
| CLI commands | `/src/claude_mpm/cli/commands/` | `run.py` |
| Slash commands | `/src/claude_mpm/commands/` | `mpm-organize.md` |

### By Purpose

| Purpose | Primary Location | Secondary Location |
|---------|------------------|-------------------|
| Production code | `/src/claude_mpm/` | N/A |
| Unit tests | `/tests/test_*.py` | `/tests/[module]/` |
| Integration tests | `/tests/integration/` | `/tests/test_*_integration.py` |
| E2E tests | `/tests/e2e/` | N/A |
| Test data | `/tests/fixtures/` | N/A |
| Development scripts | `/scripts/development/` | N/A |
| Monitoring tools | `/scripts/monitoring/` | N/A |
| Configuration scripts | `/scripts/utilities/` | N/A |
| User documentation | `/docs/user/` | N/A |
| Developer docs | `/docs/developer/` | N/A |
| API reference | `/docs/reference/` | N/A |
| Design docs | `/docs/design/` | N/A |
| Archived docs | `/docs/_archive/` | N/A |

### Prohibited Locations

**NEVER place files in these locations:**

| File Type | ❌ NEVER Here | ✅ Place Here Instead |
|-----------|---------------|---------------------|
| Scripts | Project root | `/scripts/[purpose]/` |
| Tests | Project root | `/tests/` |
| Tests | `/src/` | `/tests/` |
| Temporary files | Project root | `/tmp/` |
| Temporary files | `/docs/` | `/tmp/` |
| Documentation drafts | Project root | `/tmp/docs/` then move to `/docs/` |
| Test outputs | Project root | `/tmp/test_results/` |
| Debug files | Anywhere | `/tmp/debug/` |

---

## Naming Conventions

### File Naming

| Type | Convention | Examples |
|------|-----------|----------|
| Python modules | `snake_case.py` | `agent_registry.py`, `hook_service.py` |
| Test files | `test_*.py` | `test_agent_registry.py`, `test_services.py` |
| Agent definitions | `[agent-id].json` | `engineer.json`, `project-organizer.json` |
| Markdown docs | `UPPERCASE.md` or `lowercase.md` | `ARCHITECTURE.md`, `getting-started.md` |
| Scripts | `snake_case.py` or `kebab-case.sh` | `debug_agents.py`, `run-tests.sh` |
| Configuration | `snake_case.yaml/json` | `agent_schema.json`, `config.yaml` |

### Directory Naming

| Type | Convention | Examples |
|------|-----------|----------|
| Python packages | `lowercase` or `snake_case` | `services`, `agent_deployment` |
| Documentation | `lowercase` or `kebab-case` | `developer`, `getting-started` |
| Scripts | `lowercase` | `development`, `monitoring` |
| Tests | `lowercase` | `integration`, `e2e` |

### Variable and Function Naming

| Language | Convention | Examples |
|----------|-----------|----------|
| Python | `snake_case` | `agent_registry`, `load_framework` |
| Python classes | `PascalCase` | `AgentRegistry`, `BaseService` |
| Python constants | `UPPER_SNAKE_CASE` | `MAX_FILE_SIZE`, `DEFAULT_PORT` |
| JavaScript/TypeScript | `camelCase` | `agentRegistry`, `loadFramework` |
| JavaScript classes | `PascalCase` | `AgentRegistry`, `BaseService` |
| JavaScript constants | `UPPER_SNAKE_CASE` | `MAX_FILE_SIZE`, `DEFAULT_PORT` |

### Agent Naming

- **Agent IDs**: Use lowercase with hyphens: `project-organizer`, `engineer`
- **Agent files**: Match agent ID: `project-organizer.json`
- **Agent classes**: Use PascalCase if implementing: `ProjectOrganizerAgent`
- **No suffixes**: Avoid `_agent` suffix in IDs (e.g., `engineer` not `engineer_agent`)

---

## Module Organization

### Python Package Structure

Follow the **src layout** pattern:

```
src/claude_mpm/
├── __init__.py                 # Package initialization
├── module/                     # Feature module
│   ├── __init__.py             # Module initialization
│   ├── submodule.py            # Submodule
│   └── utils.py                # Module utilities
```

### Import Patterns

**Always use absolute imports:**

```python
# ✅ Correct
from claude_mpm.core.agent_registry import AgentRegistry
from claude_mpm.services.agents.deployment import AgentDeploymentService

# ❌ Incorrect (relative imports in main code)
from ..core.agent_registry import AgentRegistry
from .deployment import AgentDeploymentService
```

**Package initialization (`__init__.py`):**

```python
# Export primary interfaces
from .agent_registry import AgentRegistry
from .framework_loader import FrameworkLoader

__all__ = ['AgentRegistry', 'FrameworkLoader']
```

### Service Organization

Services follow a **domain-driven design** with clear interfaces:

```
services/
├── [domain]/                   # Service domain (agents, communication, etc.)
│   ├── __init__.py             # Domain exports
│   ├── [service_name].py       # Service implementation
│   └── [feature]/              # Sub-domain if needed
│       ├── __init__.py
│       └── *.py
```

Example:
```
services/
├── agents/
│   ├── __init__.py
│   ├── deployment/
│   │   ├── __init__.py
│   │   ├── agent_deployment.py
│   │   └── agent_lifecycle_manager.py
│   └── memory/
│       ├── __init__.py
│       └── agent_memory_manager.py
```

---

## Testing Organization

### Test File Structure

Match source structure in `/tests/`:

```
Source:  src/claude_mpm/core/agent_registry.py
Test:    tests/test_agent_registry.py
or       tests/core/test_agent_registry.py

Source:  src/claude_mpm/services/agents/deployment/agent_deployment.py
Test:    tests/services/agents/test_agent_deployment.py
```

### Test Categories

| Category | Location | Purpose |
|----------|----------|---------|
| Unit tests | `/tests/test_*.py` | Test individual functions/classes |
| Integration tests | `/tests/integration/` | Test component interactions |
| E2E tests | `/tests/e2e/` | Test complete workflows |
| Service tests | `/tests/services/` | Test service layer |
| CLI tests | `/tests/cli/` | Test CLI commands |
| Agent tests | `/tests/agents/` | Test agent behavior |

### Test Naming

```python
# File: tests/test_agent_registry.py

class TestAgentRegistry:
    """Test suite for AgentRegistry class."""

    def test_discover_agents(self):
        """Test agent discovery across all tiers."""
        pass

    def test_get_agent_not_found(self):
        """Test error handling when agent not found."""
        pass
```

### Test Fixtures

Place shared fixtures in `/tests/fixtures/`:

```
tests/fixtures/
├── agents/                     # Agent test fixtures
│   ├── test_engineer.json
│   └── test_organizer.json
├── projects/                   # Project test data
│   └── sample_project/
└── data/                       # General test data
    └── sample_data.json
```

---

## Documentation Structure

### Documentation Categories

| Category | Location | Purpose |
|----------|----------|---------|
| Entry point | `/docs/README.md` | Documentation navigation |
| Architecture | `/docs/developer/ARCHITECTURE.md` | System design |
| Structure | `/docs/developer/STRUCTURE.md` | File organization (authoritative) |
| Organization | `/docs/reference/PROJECT_ORGANIZATION.md` | This file |
| User guides | `/docs/user/` | End-user documentation |
| Developer guides | `/docs/developer/` | Developer documentation |
| Reference | `/docs/reference/` | API and technical reference |
| Examples | `/docs/examples/` | Usage examples |
| Design | `/docs/design/` | Design documents |
| Archive | `/docs/_archive/` | Historical documentation |

### Documentation Hierarchy

```
docs/
├── README.md                   # START HERE - Navigation to all docs
├── developer/                  # For developers working on Claude MPM
│   ├── ARCHITECTURE.md         # System architecture
│   ├── STRUCTURE.md            # File organization (authoritative)
│   ├── SERVICES.md             # Service development
│   └── ...
├── reference/                  # Technical reference
│   ├── PROJECT_ORGANIZATION.md # This file
│   ├── API.md                  # API reference
│   └── ...
├── user/                       # For users of Claude MPM
│   ├── getting-started/        # Getting started guides
│   └── 03-features/            # Feature documentation
└── _archive/                   # Historical documentation
```

### Cross-Referencing

Use relative links from `/docs/` root:

```markdown
See [Architecture Overview](developer/ARCHITECTURE.md) for details.
See [Project Organization](reference/PROJECT_ORGANIZATION.md) for file placement rules.
```

From CLAUDE.md (project root), use `docs/` prefix:

```markdown
See [docs/developer/STRUCTURE.md](docs/developer/STRUCTURE.md) for file organization.
```

---

## Script Organization

### Script Categories

Scripts in `/scripts/` are organized by purpose:

| Category | Location | Purpose |
|----------|----------|---------|
| Main executables | `/scripts/` (root) | `claude-mpm`, `run_mpm.py` |
| Development | `/scripts/development/` | Testing, debugging, linting |
| Monitoring | `/scripts/monitoring/` | Runtime monitoring tools |
| Utilities | `/scripts/utilities/` | Configuration, MCP, code generation |
| Verification | `/scripts/verification/` | System verification, integration tests |

### Script Naming

- **Bash scripts**: `kebab-case.sh` or no extension
- **Python scripts**: `snake_case.py`
- **Prefix by purpose**: `debug_`, `monitor_`, `verify_`, `configure_`

Examples:
```
scripts/
├── claude-mpm                  # Main executable
├── development/
│   ├── debug_agents.py         # Prefix: debug_
│   ├── run_all_tests.sh        # Prefix: run_
│   └── diagnose_structure.py   # Prefix: diagnose_
├── monitoring/
│   ├── monitor_dashboard.py    # Prefix: monitor_
│   └── socketio_server.py      # Descriptive name
└── utilities/
    ├── configure_mcp_server.py # Prefix: configure_
    └── generate_agent.py       # Prefix: generate_
```

### Making Scripts Executable

```bash
# Add shebang
#!/usr/bin/env python3

# Make executable
chmod +x scripts/development/debug_agents.py
```

---

## Agent Organization

### Agent Tier System

Claude MPM uses a **three-tier agent system** with clear precedence:

1. **PROJECT Tier** (`.claude-mpm/agents/`)
   - Highest precedence
   - Project-specific customizations and domain agents
   - Overrides USER and SYSTEM agents
   - Flat directory structure (no subdirectories)

2. **USER Tier** (`~/.claude-mpm/agents/`)
   - User-level customizations across projects
   - Overrides SYSTEM agents
   - Personal preferences and workflows

3. **SYSTEM Tier** (`/src/claude_mpm/agents/templates/`)
   - Framework built-in agents (lowest precedence)
   - Maintained by Claude MPM developers
   - Fallback when no higher-tier agent exists

### Agent File Formats

Agents support multiple formats:

- **JSON**: `.json` (preferred for structured data)
- **Markdown**: `.md` (preferred for instruction-heavy agents)
- **YAML**: `.yaml` or `.yml` (alternative structured format)

### Agent File Naming

Match agent ID exactly:

```
Agent ID: engineer
File: engineer.json (or engineer.md, engineer.yaml)

Agent ID: project-organizer
File: project-organizer.json

❌ NEVER: engineer_agent.json
❌ NEVER: Engineer.json
❌ NEVER: engineer-v1.json
```

### Agent Directory Structure

```
.claude-mpm/agents/              # PROJECT tier (flat structure)
├── engineer.md                  # Override system engineer
├── custom-domain-expert.json    # Project-specific agent
└── data-analyst.yaml            # Project-specific agent

~/.claude-mpm/agents/            # USER tier (flat structure)
├── engineer.json                # User's engineer override
└── personal-assistant.md        # User's personal agent

src/claude_mpm/agents/templates/ # SYSTEM tier (flat structure)
├── engineer.json                # Built-in engineer
├── project-organizer.json       # Built-in organizer
└── *.json                       # Other built-in agents
```

---

## Framework-Specific Rules

### Next.js Projects

Respect Next.js conventions:

```
[project]/
├── pages/                      # Pages router (Next.js 12)
├── app/                        # App router (Next.js 13+)
├── public/                     # Static assets
├── components/                 # React components
├── lib/                        # Utility functions
├── styles/                     # Stylesheets
└── api/                        # API routes
```

**Do NOT reorganize** Next.js framework directories.

### Django Projects

Respect Django conventions:

```
[project]/
├── [app_name]/                 # Django app
│   ├── migrations/             # Database migrations
│   ├── templates/              # HTML templates
│   ├── static/                 # Static files
│   ├── models.py               # Data models
│   ├── views.py                # View functions
│   └── urls.py                 # URL routing
└── manage.py                   # Django management
```

**Do NOT reorganize** Django app structure.

### React Projects

Common React organization:

```
src/
├── components/                 # React components
│   ├── common/                 # Shared components
│   └── [feature]/              # Feature-specific components
├── hooks/                      # Custom hooks
├── utils/                      # Utility functions
├── services/                   # API services
└── App.jsx                     # Root component
```

### Python Projects (Claude MPM Pattern)

```
src/[package_name]/
├── __init__.py                 # Package initialization
├── cli/                        # CLI commands
├── core/                       # Core functionality
├── services/                   # Service layer
├── agents/                     # Agent system
└── utils/                      # Utilities
```

---

## Validation and Enforcement

### Automated Structure Linting

Claude MPM includes automated structure validation:

```bash
# Validate project structure with linting
make lint

# Auto-fix structure issues (dry-run)
/mpm-organize --dry-run

# Apply structure fixes
/mpm-organize
```

### Structure Linting Rules

See [docs/developer/LINTING.md](../developer/LINTING.md) for:
- File placement validation
- Code quality and formatting
- Import organization
- Type checking with mypy

### Pre-commit Hooks

Structure validation runs automatically:

```bash
# Install pre-commit hooks
pre-commit install

# Runs on every commit:
# - Structure linting
# - Code formatting
# - Import organization
# - Type checking
```

### Quality Gates

Before release, comprehensive validation:

```bash
# Run all quality checks
make quality

# Run pre-publish checks
make pre-publish

# Safe release build with validation
make safe-release-build
```

---

## Migration Procedures

### Reorganizing Existing Projects

#### Step 1: Backup

```bash
# Create backup before reorganization
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz .
```

#### Step 2: Preview Changes

```bash
# Dry-run to see what would change
/mpm-organize --dry-run
```

#### Step 3: Execute Reorganization

```bash
# Full reorganization with backup
/mpm-organize

# Or force even with uncommitted changes
/mpm-organize --force --verbose
```

#### Step 4: Verify and Test

```bash
# Check git status
git status

# Run tests
make test

# Run quality checks
make quality

# Verify build
make build
```

#### Step 5: Commit Changes

```bash
# Stage all changes
git add .

# Commit with descriptive message
git commit -m "refactor: reorganize project structure per PROJECT_ORGANIZATION.md"
```

### Moving Individual Files

#### For Tracked Files (use git mv)

```bash
# Move file preserving git history
git mv old/path/file.py new/path/file.py

# Update import statements
# (search and replace in affected files)

# Run tests
pytest tests/
```

#### For New/Untracked Files

```bash
# Simply move to correct location
mv file.py correct/location/file.py

# Add to git
git add correct/location/file.py
```

### Import Path Updates

After moving files, update import statements:

```python
# Before (old location)
from old.module.path import SomeClass

# After (new location)
from new.module.path import SomeClass
```

Use search and replace or `sed`:

```bash
# Find all files with old import
grep -r "from old.module.path import" .

# Replace (example with sed)
find . -type f -name "*.py" -exec sed -i '' \
  's/from old\.module\.path import/from new.module.path import/g' {} +
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial comprehensive organization standard |

---

## References

- **[STRUCTURE.md](../developer/STRUCTURE.md)**: Authoritative file organization reference
- **[ARCHITECTURE.md](../developer/ARCHITECTURE.md)**: System architecture overview
- **[SERVICES.md](../developer/SERVICES.md)**: Service development guidelines
- **[/mpm-organize command](../../src/claude_mpm/commands/mpm-organize.md)**: Organization command documentation
- **[LINTING.md](../developer/LINTING.md)**: Code quality and structure validation

---

**Maintained by**: Claude MPM Team
**Questions or Updates**: See [Contributing Guidelines](../../CLAUDE.md#contributing)
