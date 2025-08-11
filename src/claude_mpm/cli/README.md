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
│   ├── tickets.py    # Lists tickets
│   ├── info.py       # Shows system information
│   └── agents.py     # Manages agent deployments
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

## Removed Files

- `cli_main.py` - Redundant entry point, functionality moved to `__main__.py`
- Original `cli.py` - Split into the modular structure described above

## Preserved Files

- `cli_enhancements.py` - Experimental Click-based CLI with enhanced features
  - Kept for reference and future enhancement ideas
  - Not currently used in production