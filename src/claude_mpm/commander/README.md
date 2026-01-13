# MPM Commander Module

The Commander module provides tmux-based orchestration for managing multiple MPM project sessions from a single user-level daemon.

## Architecture

```
Commander (user-level, daemon) → manages multiple projects
    ↓
MPM (project-level) → current behavior, unchanged
    ↓
Claude Code (session-level) → actual coding
```

## Components

### TmuxOrchestrator

Core class that wraps tmux commands to manage sessions, panes, and I/O.

**Key Features:**
- Session management (create, check, kill)
- Pane management (create, list, kill)
- I/O operations (send keys, capture output)
- Error handling (tmux not found, invalid targets)
- Logging support for debugging

## Installation

The commander module is part of claude-mpm. Install with:

```bash
pip install claude-mpm
```

**Requirements:**
- Python 3.8+
- tmux installed and in PATH

## Usage

### Basic Example

```python
from claude_mpm.commander import TmuxOrchestrator

# Create orchestrator
orchestrator = TmuxOrchestrator(session_name="mpm-commander")

# Create session
orchestrator.create_session()

# Create pane for a project
target = orchestrator.create_pane("my-project", "/path/to/project")

# Send commands
orchestrator.send_keys(target, "echo 'Hello'")
orchestrator.send_keys(target, "ls -la")

# Capture output
output = orchestrator.capture_output(target, lines=50)
print(output)

# List all panes
panes = orchestrator.list_panes()
for pane in panes:
    print(f"{pane['id']}: {pane['path']}")

# Cleanup
orchestrator.kill_pane(target)
orchestrator.kill_session()
```

### Error Handling

```python
from claude_mpm.commander import TmuxOrchestrator, TmuxNotFoundError

try:
    orchestrator = TmuxOrchestrator()
except TmuxNotFoundError as e:
    print(f"Error: {e.message}")
    print("Please install tmux:")
    print("  macOS: brew install tmux")
    print("  Ubuntu/Debian: sudo apt-get install tmux")
```

### Advanced Usage

```python
# Custom session name
orchestrator = TmuxOrchestrator(session_name="custom-session")

# Send keys without Enter
orchestrator.send_keys(target, "ls -la", enter=False)

# Capture more history
output = orchestrator.capture_output(target, lines=500)

# Check if session exists
if orchestrator.session_exists():
    print("Session is running")
else:
    orchestrator.create_session()
```

## API Reference

### TmuxOrchestrator

#### Constructor

```python
TmuxOrchestrator(session_name: str = "mpm-commander")
```

**Parameters:**
- `session_name`: Name of the tmux session (default: "mpm-commander")

**Raises:**
- `TmuxNotFoundError`: If tmux is not installed or not in PATH

#### Methods

##### `session_exists() -> bool`

Check if commander session exists.

**Returns:** True if session exists, False otherwise

##### `create_session() -> bool`

Create main commander tmux session if not exists.

**Returns:** True if session was created, False if already existed

##### `create_pane(pane_id: str, working_dir: str) -> str`

Create new pane for a project.

**Parameters:**
- `pane_id`: Identifier for this pane (used in logging)
- `working_dir`: Working directory for the pane

**Returns:** Tmux target string (pane ID like "%0", "%1")

**Raises:** `subprocess.CalledProcessError` if pane creation fails

##### `send_keys(target: str, keys: str, enter: bool = True) -> bool`

Send keystrokes to a pane.

**Parameters:**
- `target`: Tmux target (from create_pane)
- `keys`: Keys to send to the pane
- `enter`: Whether to send Enter key after keys (default: True)

**Returns:** True if successful

**Raises:** `subprocess.CalledProcessError` if target pane doesn't exist

##### `capture_output(target: str, lines: int = 100) -> str`

Capture recent output from pane.

**Parameters:**
- `target`: Tmux target (from create_pane)
- `lines`: Number of lines to capture from history (default: 100)

**Returns:** Captured output as string

**Raises:** `subprocess.CalledProcessError` if target pane doesn't exist

##### `list_panes() -> List[Dict[str, str]]`

List all panes with their status.

**Returns:** List of dicts with keys:
- `id`: Pane ID (e.g., "%0")
- `path`: Current working directory
- `pid`: Process ID
- `active`: Boolean indicating if pane is active

##### `kill_pane(target: str) -> bool`

Kill a specific pane.

**Parameters:**
- `target`: Tmux target (from create_pane or list_panes)

**Returns:** True if successful

**Raises:** `subprocess.CalledProcessError` if target pane doesn't exist

##### `kill_session() -> bool`

Kill the entire commander session.

**Returns:** True if session was killed, False if it didn't exist

## Examples

See `examples/commander_demo.py` for a complete working example.

Run the demo:

```bash
python examples/commander_demo.py
```

## Testing

Run the test suite:

```bash
pytest tests/commander/ -v
```

Run with coverage:

```bash
pytest tests/commander/ --cov=claude_mpm.commander --cov-report=html
```

## Implementation Notes

### Tmux Target Format

Pane IDs (like `%0`, `%1`) can be used directly as tmux targets. The orchestrator returns these IDs from `create_pane()` and uses them for all pane operations.

### Error Handling

The orchestrator uses subprocess error handling:
- `TmuxNotFoundError`: Raised when tmux binary not found
- `subprocess.CalledProcessError`: Raised when tmux commands fail

All errors include context for debugging.

### Logging

Enable debug logging to see tmux commands:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Backwards Compatibility

This module is **opt-in** via the `--commander` flag. Without the flag, claude-mpm works as it does today. The commander mode is a new feature for Phase 1 of Issue #168.

## Future Enhancements (Planned)

- Phase 2: ProjectManager class for managing project states
- Phase 3: Commander daemon with API
- Phase 4: Multi-project coordination and resource allocation

## Contributing

When contributing to the commander module:

1. Add unit tests for all new functionality
2. Use mocks for subprocess calls in tests
3. Update this README with new features
4. Follow the existing code style and patterns

## License

Same as claude-mpm main project.
