# Project-Level Aliases for claude-mpm

This project includes two convenient aliases/scripts at the project root level for testing the framework before installation:

## claude-mpm

**Location**: `./claude-mpm`

A wrapper script that automatically:
- Activates the virtual environment
- Sets up the Python path
- Delegates to the main claude-mpm script in `scripts/claude-mpm`

**Usage**:
```bash
./claude-mpm --version
./claude-mpm --help
./claude-mpm run -i "Your prompt" --non-interactive
./claude-mpm info
```

## ticket

**Location**: `./ticket`

A wrapper script for ticket management that:
- Activates the virtual environment
- Installs dependencies if needed
- Executes the ticket management script with proper Python environment

**Usage**:
```bash
./ticket help
./ticket create "Fix bug" -t bug -p high
./ticket list
./ticket view TSK-0001
./ticket update TSK-0001 -s in_progress
./ticket close TSK-0001
```

## Benefits

These project-level scripts:
1. Allow testing the framework without global installation
2. Handle virtual environment activation automatically
3. Ensure proper Python path configuration
4. Mirror the behavior of the installed commands

## Testing

Both scripts have been tested and confirmed working:
- `./claude-mpm --version` returns: claude-mpm 1.0.0
- `./ticket help` displays the full help menu
- Virtual environment activation is handled automatically
- No need to manually activate venv before using these commands