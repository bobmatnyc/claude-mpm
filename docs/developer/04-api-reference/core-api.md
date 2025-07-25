# Core API Reference

This document provides a comprehensive API reference for the core components of Claude MPM.

## Table of Contents

1. [ClaudeLauncher](#claudelauncher)
2. [AgentRegistry](#agentregistry)
3. [FrameworkLoader](#frameworkloader)
4. [LaunchMode](#launchmode)

---

## ClaudeLauncher

The `ClaudeLauncher` class provides a centralized interface for launching Claude CLI with subprocess.Popen.

### Location
`src/claude_mpm/core/claude_launcher.py`

### Class Definition

```python
class ClaudeLauncher:
    """Centralized Claude CLI launcher using subprocess.Popen."""
```

### Constructor

```python
def __init__(
    self,
    model: str = "opus",
    skip_permissions: bool = True,
    log_level: str = "INFO"
)
```

**Parameters:**
- `model` (str): Claude model to use (default: "opus")
- `skip_permissions` (bool): Whether to add --dangerously-skip-permissions flag
- `log_level` (str): Logging level

### Primary Methods

#### launch()

The main entry point for launching Claude processes.

```python
def launch(
    self,
    mode: LaunchMode = LaunchMode.INTERACTIVE,
    input_text: Optional[str] = None,
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    stdin: Optional[Union[int, IO]] = None,
    stdout: Optional[Union[int, IO]] = None,
    stderr: Optional[Union[int, IO]] = None,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    **popen_kwargs
) -> subprocess.Popen
```

**Parameters:**
- `mode` (LaunchMode): Launch mode (INTERACTIVE, PRINT, or SYSTEM_PROMPT)
- `input_text` (Optional[str]): Input text for print mode
- `session_id` (Optional[str]): Optional session ID
- `system_prompt` (Optional[str]): System prompt for system_prompt mode
- `extra_args` (Optional[List[str]]): Additional command line arguments
- `stdin` (Optional[Union[int, IO]]): stdin for Popen (default: PIPE)
- `stdout` (Optional[Union[int, IO]]): stdout for Popen (default: PIPE)
- `stderr` (Optional[Union[int, IO]]): stderr for Popen (default: PIPE)
- `env` (Optional[Dict[str, str]]): Environment variables
- `cwd` (Optional[str]): Working directory
- `**popen_kwargs`: Additional arguments passed to Popen

**Returns:** `subprocess.Popen` - Process object

**Example:**
```python
launcher = ClaudeLauncher(model="opus")
process = launcher.launch(
    mode=LaunchMode.PRINT,
    input_text="Hello, Claude!",
    session_id="my-session"
)
```

#### build_command()

Build command array based on mode and options.

```python
def build_command(
    self,
    mode: LaunchMode = LaunchMode.INTERACTIVE,
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    extra_args: Optional[List[str]] = None
) -> List[str]
```

**Returns:** List[str] - Command array ready for subprocess

### Convenience Methods

#### launch_interactive()

```python
def launch_interactive(
    self,
    session_id: Optional[str] = None,
    **popen_kwargs
) -> subprocess.Popen
```

Launch Claude in interactive mode.

**Example:**
```python
launcher = ClaudeLauncher()
process = launcher.launch_interactive(session_id="interactive-session")
```

#### launch_oneshot()

```python
def launch_oneshot(
    self,
    message: str,
    session_id: Optional[str] = None,
    use_stdin: bool = True,
    timeout: Optional[float] = None
) -> Tuple[str, str, int]
```

Execute a one-shot command and return the response.

**Returns:** Tuple of (stdout, stderr, returncode)

**Example:**
```python
launcher = ClaudeLauncher()
stdout, stderr, code = launcher.launch_oneshot(
    "What is the weather today?",
    timeout=30.0
)
```

#### launch_with_system_prompt()

```python
def launch_with_system_prompt(
    self,
    system_prompt: str,
    session_id: Optional[str] = None,
    **popen_kwargs
) -> subprocess.Popen
```

Launch Claude with a system prompt.

---

## LaunchMode

Enumeration for Claude launch modes.

### Location
`src/claude_mpm/core/claude_launcher.py`

```python
class LaunchMode(Enum):
    """Claude launch modes."""
    INTERACTIVE = "interactive"
    PRINT = "print"
    SYSTEM_PROMPT = "system_prompt"
```

---

## AgentRegistry

The agent registry system provides agent discovery and management capabilities.

### Location
`src/claude_mpm/core/agent_registry.py`

### AgentRegistryAdapter

Main adapter for integrating the agent registry.

```python
class AgentRegistryAdapter:
    """
    Adapter to integrate claude-multiagent-pm's agent registry.
    
    This adapter:
    1. Locates the claude-multiagent-pm installation
    2. Dynamically imports the agent registry
    3. Provides a clean interface for agent operations
    """
```

### Constructor

```python
def __init__(self, framework_path: Optional[Path] = None)
```

**Parameters:**
- `framework_path` (Optional[Path]): Path to claude-multiagent-pm (auto-detected if None)

### Key Methods

#### list_agents()

```python
def list_agents(self, **kwargs) -> Dict[str, Any]
```

List available agents.

**Returns:** Dictionary of agents with metadata

**Example:**
```python
registry = AgentRegistryAdapter()
agents = registry.list_agents()
for agent_id, metadata in agents.items():
    print(f"{agent_id}: {metadata['type']}")
```

#### get_agent_definition()

```python
def get_agent_definition(self, agent_name: str) -> Optional[str]
```

Get agent definition by name.

**Parameters:**
- `agent_name` (str): Name of the agent

**Returns:** Agent definition content or None

#### select_agent_for_task()

```python
def select_agent_for_task(
    self, 
    task_description: str, 
    required_specializations: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]
```

Select optimal agent for a task.

**Parameters:**
- `task_description` (str): Description of the task
- `required_specializations` (Optional[List[str]]): Required agent specializations

**Returns:** Agent metadata or None

**Example:**
```python
registry = AgentRegistryAdapter()
agent = registry.select_agent_for_task(
    "Review the code for security vulnerabilities",
    required_specializations=["security", "code-review"]
)
```

#### get_agent_hierarchy()

```python
def get_agent_hierarchy(self) -> Dict[str, List[str]]
```

Get agent hierarchy (project → user → system).

**Returns:** Dictionary with hierarchy levels and agent names

#### get_core_agents()

```python
def get_core_agents(self) -> List[str]
```

Get list of core system agents.

**Returns:** List of core agent names

#### format_agent_for_task_tool()

```python
def format_agent_for_task_tool(
    self, 
    agent_name: str, 
    task: str, 
    context: str = ""
) -> str
```

Format agent delegation for Task Tool.

**Parameters:**
- `agent_name` (str): Name of the agent
- `task` (str): Task description
- `context` (str): Additional context

**Returns:** Formatted Task Tool prompt

---

## FrameworkLoader

The FrameworkLoader handles loading framework instructions and agent definitions.

### Location
`src/claude_mpm/core/framework_loader.py`

### Key Methods

#### get_framework_instructions()

Load and return the complete framework instructions including agent definitions.

#### get_available_agents()

Return a list of available agent templates.

### Usage Example

```python
from claude_mpm.core.framework_loader import FrameworkLoader

loader = FrameworkLoader()
instructions = loader.get_framework_instructions()
agents = loader.get_available_agents()
```

---

## Error Handling

All core components follow consistent error handling patterns:

1. **Logging**: Errors are logged using the configured logger
2. **Graceful Degradation**: Components attempt to continue operation when possible
3. **Return Values**: Methods return None or empty collections on error
4. **Exceptions**: Only critical errors raise exceptions

### Example Error Handling

```python
try:
    launcher = ClaudeLauncher()
    process = launcher.launch(mode=LaunchMode.INTERACTIVE)
except RuntimeError as e:
    # Claude executable not found
    print(f"Failed to launch Claude: {e}")
```

---

## Best Practices

1. **Resource Management**: Always properly close Popen processes
2. **Timeout Handling**: Use timeouts for one-shot operations
3. **Session IDs**: Use consistent session IDs for related operations
4. **Logging**: Configure appropriate log levels for production vs development

### Example: Complete Lifecycle

```python
from claude_mpm.core.claude_launcher import ClaudeLauncher, LaunchMode
from claude_mpm.core.agent_registry import AgentRegistryAdapter

# Initialize components
launcher = ClaudeLauncher(model="opus", log_level="INFO")
registry = AgentRegistryAdapter()

# Select an agent for a task
agent = registry.select_agent_for_task("Write unit tests")

# Launch Claude with agent context
if agent:
    agent_def = registry.get_agent_definition(agent['id'])
    process = launcher.launch_with_system_prompt(
        system_prompt=agent_def,
        session_id=f"agent-{agent['id']}"
    )
    
    # Handle process lifecycle
    try:
        stdout, stderr = process.communicate(timeout=60)
    finally:
        if process.poll() is None:
            process.terminate()
```