# Claude MPM CLI Architecture

This document describes the refactored CLI architecture for claude-mpm.

## Overview

The CLI has been refactored from a single monolithic `cli.py` file into a modular structure that improves maintainability and code organization.

## Directory Structure

```
cli/
├── __init__.py       # Main entry point - orchestrates the CLI flow
├── parser.py         # Argument parsing logic - single source of truth for CLI arguments
├── utils.py          # Shared utility functions
├── commands/         # Individual command implementations
│   ├── __init__.py
│   ├── run.py        # Default command - runs Claude sessions
│   ├── tickets.py    # Comprehensive ticket management commands
│   ├── info.py       # Shows system information
│   ├── agents.py     # Manages agent deployments
│   ├── memory.py     # Agent memory management
│   ├── monitor.py    # System monitoring
│   ├── config.py     # Configuration management
│   └── aggregate.py  # Event aggregation
└── README.md         # This file
```

## Key Design Decisions

### 1. Modular Command Structure
Each command is implemented in its own module under `commands/`. This makes it easy to:
- Add new commands without touching existing code
- Test commands in isolation
- Understand what each command does

### 2. Centralized Argument Parsing
All argument definitions are in `parser.py`. This provides:
- Single source of truth for CLI arguments
- Reusable argument groups (common arguments, run arguments)
- Clear separation of parsing from execution

### 3. Shared Utilities
Common functions are in `utils.py`:
- `get_user_input()` - Handles input from files, stdin, or command line
- `get_agent_versions_display()` - Formats agent version information
- `setup_logging()` - Configures logging based on arguments
- `ensure_directories()` - Creates required directories on first run

### 4. Backward Compatibility
The refactoring maintains full backward compatibility:
- `__main__.py` still imports from `claude_mpm.cli`
- The main `cli/__init__.py` exports the same `main()` function
- All existing commands and arguments work exactly as before

## Entry Points

1. **Package execution**: `python -m claude_mpm`
   - Uses `__main__.py` which imports from `cli/__init__.py`

2. **Direct import**: `from claude_mpm.cli import main`
   - Imports the main function from `cli/__init__.py`

3. **Shell script**: `claude-mpm` command
   - Calls `python -m claude_mpm` with proper environment setup

## Adding New Commands

To add a new command:

1. Create a new module in `commands/`:
```python
# commands/mycommand.py
def my_command(args):
    """Execute my command."""
    # Implementation here
```

2. Add the command to `commands/__init__.py`:
```python
from .mycommand import my_command
```

3. Add parser configuration in `parser.py`:
```python
# In create_parser()
mycommand_parser = subparsers.add_parser(
    "mycommand",
    help="Description of my command"
)
# Add command-specific arguments
```

4. Add the command mapping in `cli/__init__.py`:
```python
# In _execute_command()
command_map = {
    # ... existing commands ...
    "mycommand": my_command,
}
```

## Command Reference

### Core Commands

**`run`** - Execute Claude sessions (default command)
- Interactive and non-interactive modes
- Hook service integration
- Agent selection and deployment
- Custom input processing

**`tickets`** - Comprehensive ticket management system
- Full CRUD operations for tickets
- Hierarchical ticket organization (Epics → Issues → Tasks)
- Search and filtering capabilities
- Workflow state management
- Integration with ai-trackdown-pytools

**`agents`** - Manage agent deployments
- List available agents by tier (PROJECT > USER > SYSTEM)
- Deploy agents to Claude Desktop compatibility format
- Validate agent configurations
- Clean up deployment artifacts

**`info`** - Display system information
- Version details and environment status
- Configuration validation
- Agent availability and status
- System health checks

### Ticket Management Commands

The `tickets` command provides a complete ticketing solution with the following subcommands:

#### Core Ticket Operations
- **`create`** - Create new tickets with proper classification
  - Support for epics, issues, tasks, bugs, and features
  - Priority assignment and hierarchical linking
  - Tag management and assignee support
  - Automatic ID generation and metadata

- **`list`** - Display recent tickets with filtering
  - Type and status filtering
  - Configurable result limits
  - Verbose mode for detailed information
  - Visual status indicators with emoji

- **`view`** - Show detailed ticket information
  - Complete ticket metadata and description
  - Parent/child relationship display
  - Assignment and tag information
  - Creation and update timestamps

- **`update`** - Modify ticket properties
  - Status and priority changes
  - Description and tag updates
  - Assignment management
  - Fallback to aitrackdown CLI for complex operations

#### Advanced Ticket Operations
- **`search`** - Find tickets by content
  - Full-text search in titles, descriptions, and tags
  - Type and status filtering
  - Context snippets for relevant matches
  - Configurable result limits

- **`close`** - Mark tickets as completed
  - Resolution reason capture
  - Automatic status transition
  - Comment integration for closure notes

- **`delete`** - Remove tickets permanently
  - Confirmation prompts for safety
  - Force option for batch operations
  - Integration with aitrackdown cleanup

- **`comment`** - Add discussion to tickets
  - Progress updates and technical notes
  - Team communication and coordination
  - Rich text support through aitrackdown

- **`workflow`** - Manage workflow states
  - State transition validation
  - Comment integration for change reasons
  - Status mapping to aitrackdown workflow

#### Ticket System Features

**Hierarchical Organization:**
```
Epic (Strategic Level)      - EP-XXXX
├── Issue (Feature Level)   - ISS-XXXX
│   ├── Task (Implementation) - TSK-XXXX
│   └── Task (Implementation) - TSK-XXXX
└── Issue (Feature Level)   - ISS-XXXX
    └── Task (Implementation) - TSK-XXXX
```

**Status Management:**
- `open` - Ready to start work
- `in_progress` - Currently being developed
- `blocked` - Cannot proceed due to dependencies
- `ready` - Awaiting review or testing
- `tested` - QA approved
- `done` - Completed successfully
- `closed` - Finalized (completed or cancelled)

**Priority Levels:**
- `critical` (P0) - System down, data loss, security breach
- `high` (P1) - Major feature broken, significant user impact
- `medium` (P2) - Minor issues, workarounds available
- `low` (P3) - Cosmetic issues, convenience features

**Integration Points:**
- **ai-trackdown-pytools**: Backend storage and advanced operations
- **TicketManager**: Primary interface for ticket operations
- **Claude Sessions**: Automatic ticket creation from patterns
- **Hook System**: Event-driven ticket updates and notifications

### Additional Management Commands

**`memory`** - Agent memory system management
- Initialize and configure agent memory
- View and optimize memory stores
- Cross-reference management
- Memory routing and building

**`monitor`** - System monitoring and health
- Start/stop/restart monitoring services
- Port management and status checks
- Performance metrics and alerts

**`config`** - Configuration management
- Validate system configuration
- View current settings
- Status reporting and diagnostics

**`aggregate`** - Event aggregation system
- Session management and tracking
- Event export and analysis
- Historical data management

## Removed Files

- `cli_main.py` - Redundant entry point, functionality moved to `__main__.py`
- Original `cli.py` - Split into the modular structure described above

## Preserved Files

- `cli_enhancements.py` - Experimental Click-based CLI with enhanced features
  - Kept for reference and future enhancement ideas
  - Not currently used in production