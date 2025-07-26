# Orchestration API Reference

This document provides a comprehensive API reference for the orchestration components of Claude MPM.

## Table of Contents

1. [Overview](#overview)
2. [Base Orchestrator](#base-orchestrator)
3. [Orchestrator Implementations](#orchestrator-implementations)
4. [Ticket Extractor](#ticket-extractor)
5. [Agent Delegator](#agent-delegator)
6. [Orchestrator Factory](#orchestrator-factory)

---

## Overview

The orchestration layer manages Claude subprocess lifecycle, I/O handling, and session management. All orchestrators inherit from a common base and implement specific launch strategies.

### Architecture

```
MPMOrchestrator (Base)
├── SubprocessOrchestrator
├── InteractiveSubprocessOrchestrator
├── SystemPromptOrchestrator
├── DirectOrchestrator
├── PtyOrchestrator
├── PexpectOrchestrator
└── WrapperOrchestrator
```

---

## Base Orchestrator

### MPMOrchestrator

Base orchestrator class that provides core functionality for all implementations.

### Location
`src/claude_mpm/orchestration/orchestrator.py`

### Constructor

```python
def __init__(
    self,
    framework_path: Optional[Path] = None,
    agents_dir: Optional[Path] = None,
    log_level: str = "OFF",
    log_dir: Optional[Path] = None,
)
```

**Parameters:**
- `framework_path` (Optional[Path]): Path to framework directory
- `agents_dir` (Optional[Path]): Custom agents directory
- `log_level` (str): Logging level (OFF, INFO, DEBUG)
- `log_dir` (Optional[Path]): Custom log directory

### Core Methods

#### start()

```python
def start(self) -> bool
```

Start the orchestrated Claude session.

**Returns:** True if successfully started, False otherwise

#### stop()

```python
def stop(self)
```

Stop the orchestrated session and perform cleanup.

#### send_input()

```python
def send_input(self, text: str)
```

Send input to Claude subprocess.

**Parameters:**
- `text` (str): Input text to send

#### get_output()

```python
def get_output(self, timeout: float = 0.1) -> Optional[str]
```

Get output from Claude (non-blocking).

**Parameters:**
- `timeout` (float): Timeout for waiting (default: 0.1 seconds)

**Returns:** Output string or None if no output available

### Session Management Methods

#### run_interactive()

```python
def run_interactive(self)
```

Run an interactive session with user input loop.

#### run_non_interactive()

```python
def run_non_interactive(self, user_input: str)
```

Run a non-interactive session with given input.

**Parameters:**
- `user_input` (str): The input to send to Claude

### Example Usage

```python
from claude_mpm.orchestration.orchestrator import MPMOrchestrator

orchestrator = MPMOrchestrator(log_level="INFO")
if orchestrator.start():
    orchestrator.send_input("Hello, Claude!")
    output = orchestrator.get_output(timeout=1.0)
    if output:
        print(output)
    orchestrator.stop()
```

---

## Orchestrator Implementations

### SubprocessOrchestrator

Standard subprocess-based orchestrator using pipes for I/O.

### Location
`src/claude_mpm/orchestration/subprocess_orchestrator.py`

```python
class SubprocessOrchestrator(MPMOrchestrator):
    """Orchestrator using subprocess.Popen with pipes."""
```

### Key Features
- Uses subprocess.PIPE for I/O
- Thread-based output handling
- Session logging and management

---

### InteractiveSubprocessOrchestrator

Enhanced subprocess orchestrator with interactive features.

### Location
`src/claude_mpm/orchestration/interactive_subprocess_orchestrator.py`

```python
class InteractiveSubprocessOrchestrator(MPMOrchestrator):
    """Enhanced orchestrator for interactive sessions."""
```

### Additional Methods

```python
def enable_raw_mode(self)
def disable_raw_mode(self)
def handle_special_keys(self, key: str) -> bool
```

---

### SystemPromptOrchestrator

Orchestrator that uses --append-system-prompt for framework injection.

### Location
`src/claude_mpm/orchestration/system_prompt_orchestrator.py`

```python
class SystemPromptOrchestrator:
    """Orchestrator using system prompt injection."""
    
    def __init__(
        self,
        model: str = "opus",
        framework_path: Optional[Path] = None,
        use_stdin: bool = False
    )
```

### Key Methods

```python
def prepare_system_prompt(self) -> str
def run(self, user_message: str, timeout: int = 300) -> Tuple[str, str, int]
```

---

### PtyOrchestrator

Orchestrator using pseudo-terminal for better interactive support.

### Location
`src/claude_mpm/orchestration/pty_orchestrator.py`

```python
class PtyOrchestrator(MPMOrchestrator):
    """Orchestrator using PTY for terminal emulation."""
```

### PTY-Specific Features
- Full terminal emulation
- Better handling of interactive prompts
- Support for terminal control sequences

---

### PexpectOrchestrator

Orchestrator using pexpect library for expect-style interaction.

### Location
`src/claude_mpm/orchestration/pexpect_orchestrator.py`

```python
class PexpectOrchestrator:
    """Orchestrator using pexpect for pattern-based interaction."""
    
    def __init__(
        self,
        model: str = "opus",
        timeout: int = 30,
        log_file: Optional[str] = None
    )
```

### Key Methods

```python
def expect_patterns(self, patterns: List[str]) -> int
def send_line(self, text: str)
def interact(self)
```

---

## Agent Delegator

Component for detecting and handling agent delegations.

### Location
`src/claude_mpm/orchestration/agent_delegator.py`

### AgentDelegator Class

```python
class AgentDelegator:
    """Handle agent delegation detection and routing."""
    
    def __init__(self, agent_registry: AgentRegistryAdapter)
```

### Key Methods

#### extract_delegations()

```python
def extract_delegations(self, text: str) -> List[Dict[str, Any]]
```

Extract agent delegations from text.

**Returns:** List of delegation dictionaries:
```python
{
    'agent': 'engineer',
    'task': 'Implement the new feature',
    'context': 'Additional context'
}
```

#### should_delegate()

```python
def should_delegate(self, text: str) -> bool
```

Check if text contains delegation markers.

### Delegation Patterns

Recognizes patterns like:
- `@engineer: Please implement...`
- `**Engineer**: Review the code...`
- `Delegate to QA: Test the feature...`

---

## Orchestrator Factory

Factory for creating orchestrator instances.

### Location
`src/claude_mpm/orchestration/factory.py`

### create_orchestrator()

```python
def create_orchestrator(
    orchestrator_type: str,
    **kwargs
) -> Union[MPMOrchestrator, Any]
```

Create an orchestrator instance by type.

**Parameters:**
- `orchestrator_type` (str): Type of orchestrator to create
- `**kwargs`: Arguments passed to orchestrator constructor

**Supported Types:**
- `"subprocess"` - SubprocessOrchestrator
- `"interactive"` - InteractiveSubprocessOrchestrator
- `"system_prompt"` - SystemPromptOrchestrator
- `"pty"` - PtyOrchestrator
- `"pexpect"` - PexpectOrchestrator
- `"direct"` - DirectOrchestrator

### Example

```python
from claude_mpm.orchestration.factory import create_orchestrator

# Create interactive orchestrator
orchestrator = create_orchestrator(
    "interactive",
    log_level="INFO",
    framework_path=Path("./framework")
)

# Create system prompt orchestrator
sp_orchestrator = create_orchestrator(
    "system_prompt",
    model="opus",
    use_stdin=True
)
```

---

## Advanced Usage

### Custom Output Processing

```python
class CustomOrchestrator(MPMOrchestrator):
    def _process_output_line(self, line: str):
        # Custom processing
        if "ERROR" in line:
            self.logger.error(f"Claude error: {line}")
        
        # Call parent implementation
        super()._process_output_line(line)
```

### Session Hooks

```python
orchestrator = MPMOrchestrator()

# Add pre-start hook
def on_start():
    print("Starting Claude session...")

orchestrator.on_start = on_start

# Add post-stop hook
def on_stop():
    print("Session ended")
    
orchestrator.on_stop = on_stop
```

### Timeout Handling

```python
from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator

orchestrator = SubprocessOrchestrator()
orchestrator.start()

# Set response timeout
import time
start_time = time.time()
timeout = 30.0

while time.time() - start_time < timeout:
    output = orchestrator.get_output(timeout=0.5)
    if output and "DONE" in output:
        break
        
orchestrator.stop()
```

---

## Error Handling

All orchestrators implement consistent error handling:

1. **Start Failures**: Return False from start() method
2. **I/O Errors**: Logged and handled gracefully
3. **Process Errors**: Captured in stderr and logged
4. **Cleanup**: Always performed in stop() method

### Example Error Handling

```python
orchestrator = create_orchestrator("subprocess", log_level="DEBUG")

if not orchestrator.start():
    print("Failed to start Claude")
    # Check logs for details
else:
    try:
        orchestrator.run_interactive()
    except KeyboardInterrupt:
        print("Session interrupted")
    finally:
        orchestrator.stop()
```

---

## Best Practices

1. **Choose the Right Orchestrator**:
   - Use `subprocess` for basic automation
   - Use `interactive` for user-facing CLI
   - Use `system_prompt` for one-shot operations
   - Use `pty` for full terminal emulation needs

2. **Resource Management**:
   - Always call stop() to clean up resources
   - Use context managers when available
   - Handle KeyboardInterrupt gracefully

3. **Logging**:
   - Use appropriate log levels
   - Enable DEBUG logging for troubleshooting
   - Review session logs for debugging

4. **Performance**:
   - Use non-blocking get_output() calls
   - Implement timeouts for long operations
   - Consider using thread pools for multiple sessions