# Multi-Runtime Adapter Architecture

This package provides a unified interface for working with multiple AI coding assistant runtimes through the Commander framework.

## Architecture Overview

The adapter architecture consists of two layers:

1. **RuntimeAdapter**: Synchronous parsing and state detection
2. **CommunicationAdapter**: Async I/O and state management

## Available Adapters

### Claude Code Adapter
- **Name**: `claude-code`
- **Command**: `claude`
- **Capabilities**:
  - File operations (read/edit/create)
  - Bash execution
  - Git operations
  - Tool use
  - Web search
  - Complex reasoning
- **Instruction File**: `CLAUDE.md`
- **Agent Support**: No

### Auggie Adapter
- **Name**: `auggie`
- **Command**: `auggie`
- **Capabilities**:
  - File operations
  - Bash execution
  - Git operations
  - Tool use
  - MCP server integration
  - Complex reasoning
- **Instruction File**: `.augment/instructions.md`
- **Agent Support**: No

### Codex Adapter
- **Name**: `codex`
- **Command**: `codex`
- **Capabilities**:
  - File operations
  - Bash execution
  - Tool use
  - Complex reasoning
- **Instruction File**: None
- **Agent Support**: No

### MPM Adapter (Full Features)
- **Name**: `mpm`
- **Command**: `claude` (with MPM config)
- **Capabilities**:
  - All Claude Code features
  - **Agent delegation** (sub-agent spawning)
  - **Lifecycle hooks** (pre/post task, commit, etc.)
  - **Loadable skills** (specialized task modules)
  - **Real-time monitoring** (dashboard)
  - **MCP server integration**
- **Instruction File**: `CLAUDE.md`
- **Agent Support**: **Yes**

## Usage

### Basic Usage with Registry

```python
from claude_mpm.commander.adapters import AdapterRegistry

# Get default adapter (best available)
adapter = AdapterRegistry.get_default()
if adapter:
    print(f"Using {adapter.name}")

# Get specific adapter
mpm_adapter = AdapterRegistry.get("mpm")

# Detect available runtimes
available = AdapterRegistry.detect_available()
print(f"Available: {available}")
```

### Build Launch Commands

```python
from claude_mpm.commander.adapters import MPMAdapter

adapter = MPMAdapter()

# Basic launch
cmd = adapter.build_launch_command("/path/to/project")
# Output: cd '/path/to/project' && claude --dangerously-skip-permissions

# With custom prompt
cmd = adapter.build_launch_command(
    "/path/to/project",
    agent_prompt="You are a Python expert"
)
```

### Check Runtime Capabilities

```python
from claude_mpm.commander.adapters import AdapterRegistry, RuntimeCapability

adapter = AdapterRegistry.get("mpm")
info = adapter.runtime_info

# Check for specific capabilities
if RuntimeCapability.AGENT_DELEGATION in info.capabilities:
    print("Supports agent delegation")

if RuntimeCapability.HOOKS in info.capabilities:
    print("Supports lifecycle hooks")

if RuntimeCapability.MCP_TOOLS in info.capabilities:
    print("Supports MCP tools")
```

### Inject Custom Instructions

```python
from claude_mpm.commander.adapters import MPMAdapter

adapter = MPMAdapter()

instructions = """You are a senior Python engineer.
Follow PEP 8 strictly.
Write comprehensive tests for all code."""

# Get command to inject instructions
cmd = adapter.inject_instructions(instructions)
# Output: echo '...' > CLAUDE.md
```

### Inject Agent Context (MPM Only)

```python
from claude_mpm.commander.adapters import MPMAdapter

adapter = MPMAdapter()

agent_id = "eng-001"
context = {
    "role": "Engineer",
    "specialty": "Backend Python",
    "task": "Implement API endpoints"
}

# Get command to inject agent context
cmd = adapter.inject_agent_context(agent_id, context)
# Output: export MPM_AGENT_ID='eng-001' && export MPM_AGENT_CONTEXT='...'
```

### Parse Runtime Output

```python
from claude_mpm.commander.adapters import ClaudeCodeAdapter

adapter = ClaudeCodeAdapter()

# Simulate output from runtime
output = "File created: test.py\n> "

# Parse response
parsed = adapter.parse_response(output)

print(f"Complete: {parsed.is_complete}")  # True
print(f"Error: {parsed.is_error}")        # False
print(f"Content: {parsed.content}")
```

### Select Runtime Based on Requirements

```python
from claude_mpm.commander.adapters import AdapterRegistry, RuntimeCapability

def select_runtime(needs_agents=False, needs_mcp=False):
    """Select appropriate runtime based on requirements."""
    available = AdapterRegistry.detect_available()

    for name in available:
        adapter = AdapterRegistry.get(name)
        if not adapter or not adapter.runtime_info:
            continue

        info = adapter.runtime_info

        # Check agent requirement
        if needs_agents and not info.supports_agents:
            continue

        # Check MCP requirement
        if needs_mcp and RuntimeCapability.MCP_TOOLS not in info.capabilities:
            continue

        # Found suitable runtime
        return adapter

    return None

# Example: Need agent delegation
adapter = select_runtime(needs_agents=True)
if adapter:
    print(f"Selected: {adapter.name}")  # Output: mpm
```

## Runtime Capabilities

| Capability | Claude Code | Auggie | Codex | MPM |
|------------|-------------|--------|-------|-----|
| File Read | ✓ | ✓ | ✓ | ✓ |
| File Edit | ✓ | ✓ | ✓ | ✓ |
| File Create | ✓ | ✓ | ✓ | ✓ |
| Bash Execution | ✓ | ✓ | ✓ | ✓ |
| Git Operations | ✓ | ✓ | ✗ | ✓ |
| Tool Use | ✓ | ✓ | ✓ | ✓ |
| Web Search | ✓ | ✗ | ✗ | ✓ |
| Complex Reasoning | ✓ | ✓ | ✓ | ✓ |
| **Agent Delegation** | ✗ | ✗ | ✗ | **✓** |
| **Lifecycle Hooks** | ✗ | ✗ | ✗ | **✓** |
| **MCP Tools** | ✗ | **✓** | ✗ | **✓** |
| **Skills** | ✗ | ✗ | ✗ | **✓** |
| **Monitoring** | ✗ | ✗ | ✗ | **✓** |

## Adding a New Adapter

To add support for a new runtime:

1. **Create adapter class** in `adapters/<runtime_name>.py`:

```python
from .base import RuntimeAdapter, RuntimeInfo, RuntimeCapability

class MyRuntimeAdapter(RuntimeAdapter):
    @property
    def name(self) -> str:
        return "my-runtime"

    @property
    def runtime_info(self) -> RuntimeInfo:
        return RuntimeInfo(
            name="my-runtime",
            version=None,
            capabilities={
                RuntimeCapability.FILE_EDIT,
                RuntimeCapability.TOOL_USE,
            },
            command="my-cli",
            supports_agents=False,
            instruction_file=None,
        )

    # Implement required methods...
```

2. **Register adapter** in `adapters/__init__.py`:

```python
from .my_runtime import MyRuntimeAdapter

AdapterRegistry.register("my-runtime", MyRuntimeAdapter)
```

3. **Add CLI command mapping** in `registry.py`:

```python
_runtime_commands: Dict[str, str] = {
    "my-runtime": "my-cli",
    # ... other runtimes
}
```

## Files

```
adapters/
├── __init__.py          # Exports and auto-registration
├── base.py              # Base classes and interfaces
├── registry.py          # Adapter registry and auto-detection
├── claude_code.py       # Claude Code adapter
├── auggie.py            # Auggie adapter
├── codex.py             # Codex adapter
├── mpm.py               # MPM adapter (full features)
├── communication.py     # Async communication layer
├── example_usage.py     # Usage examples and tests
└── README.md            # This file
```

## Runtime Selection Priority

The default adapter is selected in this order:

1. **MPM** (most features: agents, hooks, skills, monitoring)
2. **Claude Code** (full-featured, no agents)
3. **Auggie** (MCP support)
4. **Codex** (basic features)

This ensures the most capable runtime is selected by default.

## Testing

Run the example usage script to test the adapter architecture:

```bash
python -m claude_mpm.commander.adapters.example_usage
```

This will demonstrate:
- Adapter registry usage
- Capability checking
- Command building
- Instruction injection
- Agent context injection
- Output parsing
- Runtime selection logic

## Advanced Features

### MPM-Specific Features

#### Agent Delegation
```python
adapter = MPMAdapter()

# Detect agent spawn in output
info = adapter.detect_agent_spawn("[MPM] Agent spawned: eng-001 (Engineer)")
if info:
    print(f"Agent ID: {info['agent_id']}")
    print(f"Role: {info['role']}")
```

#### Lifecycle Hooks
```python
adapter = MPMAdapter()

# Detect hook trigger in output
info = adapter.detect_hook_trigger("[MPM] Hook triggered: pre-commit")
if info:
    print(f"Hook: {info['hook_name']}")
```

## Integration with Commander

The adapters integrate with Commander's `TmuxOrchestrator` through the `CommunicationAdapter` layer:

```python
from claude_mpm.commander.tmux_orchestrator import TmuxOrchestrator
from claude_mpm.commander.adapters import (
    ClaudeCodeCommunicationAdapter,
    MPMAdapter
)

# Create orchestrator
orchestrator = TmuxOrchestrator()

# Create communication adapter
runtime_adapter = MPMAdapter()
comm_adapter = ClaudeCodeCommunicationAdapter(
    orchestrator=orchestrator,
    pane_target="%0",
    runtime_adapter=runtime_adapter,
    poll_interval=0.2
)

# Send message
await comm_adapter.send("Create a Python script")

# Receive response
response = await comm_adapter.receive(timeout=60.0)
print(response.content)
```

## License

Part of the claude-mpm project. See main LICENSE file.
