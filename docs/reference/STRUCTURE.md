# Project Structure

Complete guide to Claude MPM's codebase organization.

## Quick Reference

```
claude-mpm/
├── src/claude_mpm/          # Main package
│   ├── agents/              # Agent system
│   ├── services/            # Service layer
│   ├── hooks/               # Hook system
│   ├── mcp/                 # MCP gateway
│   └── cli/                 # CLI interface
├── docs/                    # Documentation
├── tests/                   # Test suite
├── scripts/                 # Utility scripts
└── skills/                  # Bundled skills
```

## Source Code Structure

### Main Package (`/src/claude_mpm/`)

**Core Modules:**
- `__init__.py` - Package initialization
- `__main__.py` - CLI entry point
- `version.py` - Version information
- `constants.py` - Global constants
- `exceptions.py` - Custom exceptions

### Agent System (`/src/claude_mpm/agents/`)

Agent discovery, loading, and management:

```
agents/
├── __init__.py
├── registry.py          # Agent discovery and loading
├── deployment.py        # Agent lifecycle management
├── management.py        # Agent services
├── capabilities.py      # Capability definitions
└── schema.py            # Agent schema validation
```

**Key Components:**
- **AgentRegistry**: Three-tier agent discovery (PROJECT > USER > SYSTEM)
- **AgentDeployment**: Agent initialization and lifecycle
- **CapabilityManager**: Capability matching and routing

### Service Layer (`/src/claude_mpm/services/`)

Five specialized service domains:

```
services/
├── core/                # Foundation services
│   ├── interfaces.py    # Service contracts
│   ├── base.py          # Base classes
│   └── container.py     # DI container
├── agents/              # Agent services
│   ├── deployment.py    # Agent deployment
│   ├── management.py    # Agent management
│   └── registry.py      # Agent registry
├── communication/       # Real-time communication
│   ├── socketio.py      # SocketIO server
│   └── websocket.py     # WebSocket handling
├── project/             # Project services
│   ├── analyzer.py      # Stack detection
│   └── registry.py      # Project config
└── utility/             # Supporting services
    ├── logging.py       # Logging utilities
    └── filesystem.py    # File operations
```

**Service Interfaces:**
- `IServiceContainer` - Dependency injection
- `IAgentRegistry` - Agent discovery
- `IHealthMonitor` - Service health
- `IConfigurationManager` - Configuration

See [../developer/api-reference.md](../developer/api-reference.md) for API details.

### Hook System (`/src/claude_mpm/hooks/`)

Event-driven extension points:

```
hooks/
├── __init__.py
├── manager.py           # Hook manager
├── handlers.py          # Built-in handlers
└── context.py           # Hook context
```

**Hook Types:**
- `pre_tool_use` - Before tool execution
- `post_tool_use` - After tool execution
- `session_start` - Session initialization
- `session_end` - Session cleanup

See [../developer/pretool-use-hooks.md](../developer/pretool-use-hooks.md) for details.

### MCP Gateway (`/src/claude_mpm/mcp/`)

Model Context Protocol integration:

```
mcp/
├── __init__.py
├── gateway.py           # MCP gateway
├── servers/             # MCP server implementations
│   ├── filesystem.py    # Filesystem server
│   ├── github.py        # GitHub server
│   └── browser.py       # Browser automation
└── tools/               # MCP tool definitions
```

See [../developer/13-mcp-gateway/README.md](../developer/13-mcp-gateway/README.md) for MCP integration.

### CLI Interface (`/src/claude_mpm/cli/`)

Command-line interface:

```
cli/
├── __init__.py
├── main.py              # Main CLI entry
├── commands.py          # Command implementations
└── formatting.py        # Output formatting
```

## Documentation Structure (`/docs/`)

Organized by audience and topic:

```
docs/
├── README.md                    # Documentation hub
├── guides/                      # How-to guides
│   └── FAQ.md                   # Frequently asked questions
├── user/                        # End-user docs
│   ├── getting-started.md       # Quick start guide
│   ├── user-guide.md            # Complete user guide
│   ├── installation.md          # Installation guide
│   ├── troubleshooting.md       # User troubleshooting
│   └── skills-guide.md          # Skills system guide
├── developer/                   # Developer docs
│   ├── ARCHITECTURE.md          # System architecture
│   ├── api-reference.md         # API documentation
│   ├── extending.md             # Extension development
│   └── publishing-guide.md      # Release process
├── agents/                      # Agent docs
│   ├── pm-workflow.md           # PM orchestration
│   ├── creating-agents.md       # Agent development
│   └── agent-patterns.md        # Agent design patterns
├── reference/                   # Reference docs
│   ├── DEPLOY.md                # Deployment guide
│   ├── STRUCTURE.md             # This file
│   ├── SERVICES.md              # Service reference
│   ├── QA.md                    # Testing guide
│   └── MEMORY.md                # Memory system
└── examples/                    # Examples and tutorials
    └── resume-log-examples.md   # Resume log examples
```

See [README.md](README.md) for documentation hub.

## Test Suite (`/tests/`)

Comprehensive test coverage (85%+):

```
tests/
├── unit/                # Unit tests
│   ├── test_agents.py
│   ├── test_services.py
│   └── test_hooks.py
├── integration/         # Integration tests
│   ├── test_workflow.py
│   └── test_mcp.py
├── fixtures/            # Test fixtures
│   ├── agents/          # Test agents
│   └── data/            # Test data
└── conftest.py          # Pytest configuration
```

**Testing Standards:**
- 85%+ code coverage required
- Unit tests for all services
- Integration tests for workflows
- Fixtures for common scenarios

See [QA.md](QA.md) for testing guide.

## Scripts (`/scripts/`)

Utility and automation scripts:

```
scripts/
├── manage_version.py    # Version management
├── setup_dev.sh         # Development setup
├── run_tests.sh         # Test execution
└── deploy.sh            # Deployment automation
```

**Important**: ALL scripts must go in `/scripts/`, NEVER in project root.

## Skills (`/skills/`)

Bundled skills included with Claude MPM:

```
skills/
├── git-workflow.md
├── tdd.md
├── code-review.md
├── systematic-debugging.md
├── api-documentation.md
├── refactoring-patterns.md
└── ... (20 bundled skills)
```

**Skill Tiers:**
1. **Bundled**: `/skills/` - Included with installation
2. **User**: `~/.config/claude-mpm/skills/` - Personal skills
3. **Project**: `.claude-mpm/skills/` - Project-specific skills

See [../user/skills-guide.md](../user/skills-guide.md) for skills documentation.

## Configuration Files

### Package Configuration

```
claude-mpm/
├── pyproject.toml       # Package metadata and dependencies
├── setup.py             # Setup configuration
├── setup.cfg            # Build configuration
├── MANIFEST.in          # Package manifest
└── VERSION              # Version file
```

### Development Configuration

```
claude-mpm/
├── .pre-commit-config.yaml  # Pre-commit hooks
├── .flake8                  # Flake8 linting
├── .mypy.ini                # MyPy type checking
├── pytest.ini               # Pytest configuration
└── .gitignore               # Git ignore rules
```

### Quality Tools

```
claude-mpm/
├── Makefile             # Development tasks
├── .ruff.toml           # Ruff linting
└── .black.toml          # Black formatting
```

## Runtime Directories

### System Configuration

```
/usr/local/share/claude-mpm/
└── configuration.yaml           # System defaults
```

### User Configuration

```
~/.claude-mpm/
├── configuration.yaml           # User configuration
├── agents/                      # Custom agents
├── skills/                      # Custom skills
├── cache/                       # Runtime cache
├── logs/                        # Log files
│   ├── mpm.log                  # Main log
│   ├── agents.log               # Agent logs
│   └── mcp.log                  # MCP logs
└── sessions/                    # Session data
```

### Project Configuration

```
.claude-mpm/
├── configuration.yaml           # Project configuration
├── agents/                      # Project agents
├── skills/                      # Project skills
├── resume-logs/                 # Session resume logs
└── sessions/                    # Project sessions
```

## File Naming Conventions

**Python Modules:**
- Use snake_case: `agent_registry.py`
- Private modules: `_internal.py`
- Test modules: `test_agent_registry.py`

**Documentation:**
- Use UPPERCASE for top-level: `README.md`, `ARCHITECTURE.md`
- Use kebab-case for guides: `getting-started.md`
- Use descriptive names: `resume-log-architecture.md`

**Agents:**
- Use kebab-case: `python-engineer.md`
- Version in frontmatter: `version: 2.3.0`

**Skills:**
- Use kebab-case: `git-workflow.md`
- Version in frontmatter: `version: 0.1.0`

## Development Workflow

### File Placement Rules

1. **Scripts**: ALL scripts go in `/scripts/`, NEVER in project root
2. **Tests**: ALL tests go in `/tests/`, NEVER in project root
3. **Modules**: ALL Python code goes in `/src/claude_mpm/`
4. **Docs**: ALL documentation goes in `/docs/`
5. **Skills**: Bundled skills go in `/skills/`

### Code Organization

**Service-Oriented:**
- Business logic in service layer
- Interface-based contracts
- Dependency injection
- Clear separation of concerns

**Module Structure:**
```python
# Service module template
from claude_mpm.services.core import BaseService
from claude_mpm.services.core.interfaces import IServiceInterface

class MyService(BaseService, IServiceInterface):
    """Service implementation."""

    def __init__(self, container):
        super().__init__(container)

    def my_method(self):
        """Method implementation."""
        pass
```

## Build Artifacts

**Generated Files:**
```
build/               # Build directory
dist/                # Distribution packages
*.egg-info/          # Package metadata
__pycache__/         # Python cache
.pytest_cache/       # Pytest cache
.mypy_cache/         # MyPy cache
```

These are ignored by git (.gitignore).

## See Also

- **[Architecture](../developer/ARCHITECTURE.md)** - System design
- **[Developer Guide](../developer/README.md)** - Development docs
- **[API Reference](../developer/api-reference.md)** - API documentation
- **[Testing Guide](QA.md)** - Testing standards
- **[Services Reference](SERVICES.md)** - Service architecture

---

**For developer guidelines**: See [CONTRIBUTING.md](../../CONTRIBUTING.md)
