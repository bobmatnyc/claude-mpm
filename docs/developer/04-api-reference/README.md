# API Reference

This section provides comprehensive API documentation for all public interfaces in Claude MPM. The API is organized by module and includes detailed parameter descriptions, return types, and usage examples.

## API Organization

The Claude MPM API is organized into four main categories:

### [Core API](core-api.md)
Fundamental classes and functions that form the foundation of Claude MPM:
- `ClaudeLauncher` - Unified subprocess launcher
- `AgentRegistry` - Agent discovery and management
- `FrameworkLoader` - Framework instruction loading
- Base classes and interfaces

### [Orchestration API](orchestration-api.md)
Classes for managing Claude subprocess orchestration:
- `BaseOrchestrator` - Abstract orchestrator interface
- `SubprocessOrchestrator` - Direct subprocess control
- `SystemPromptOrchestrator` - System prompt injection
- `InteractiveSubprocessOrchestrator` - Enhanced interactive mode

### [Services API](services-api.md)
Service layer components:
- `HookService` - Hook system management
- `SessionLogger` - Session logging and history
- `AgentService` - Agent lifecycle management

### [Utils API](utils-api.md)
Utility functions and helpers:
- `subprocess_utils` - Safe subprocess execution
- `file_utils` - File operations
- `logger` - Logging utilities
- `validators` - Input validation

## API Conventions

### Naming Conventions

```python
# Classes use PascalCase
class SubprocessOrchestrator:
    pass

# Functions and methods use snake_case
def execute_agent(agent_name: str) -> Result:
    pass

# Constants use UPPER_SNAKE_CASE
DEFAULT_TIMEOUT = 300
MAX_AGENTS = 10

# Private members use leading underscore
def _internal_method(self):
    pass
```

### Type Hints

All public APIs use type hints:

```python
from typing import Optional, List, Dict, Union, Any

def process_message(
    message: str,
    timeout: float = 30.0,
    context: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """Process a message with optional context."""
    pass
```

### Return Values

APIs follow consistent return patterns:

```python
# Success/failure with result
@dataclass
class Result:
    success: bool
    data: Optional[Any]
    error: Optional[str]

# Optional returns for queries
def find_agent(name: str) -> Optional[Agent]:
    """Returns Agent if found, None otherwise."""
    pass

# Exceptions for errors
def validate_input(data: str) -> str:
    """Validates input, raises ValueError if invalid."""
    if not data:
        raise ValueError("Input cannot be empty")
    return data
```

### Error Handling

All APIs use consistent error handling:

```python
# Base exception
class ClaudeMPMError(Exception):
    """Base exception for all Claude MPM errors."""
    pass

# Specific exceptions
class OrchestratorError(ClaudeMPMError):
    """Orchestrator-related errors."""
    pass

class AgentNotFoundError(ClaudeMPMError):
    """Raised when requested agent doesn't exist."""
    pass

# Usage
try:
    agent = registry.get_agent("engineer")
except AgentNotFoundError as e:
    logger.error(f"Agent not found: {e}")
    # Handle error
```

## API Stability

### Versioning

Claude MPM follows [Semantic Versioning](https://semver.org/):
- **Major version**: Breaking API changes
- **Minor version**: New features, backward compatible
- **Patch version**: Bug fixes, backward compatible

### Deprecation Policy

APIs are deprecated with warnings before removal:

```python
import warnings

def old_function():
    """Deprecated function.
    
    .. deprecated:: 1.2.0
       Use :func:`new_function` instead.
    """
    warnings.warn(
        "old_function is deprecated, use new_function instead",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function()
```

### Experimental APIs

Experimental APIs are marked clearly:

```python
from claude_mpm.experimental import NewFeature

# Experimental APIs may change without notice
# Use at your own risk
```

## Quick Reference

### Creating an Orchestrator

```python
from claude_mpm.core import ClaudeLauncher
from claude_mpm.orchestration import SubprocessOrchestrator

# Create launcher
launcher = ClaudeLauncher()

# Create orchestrator
orchestrator = SubprocessOrchestrator(
    launcher=launcher,
    config={'timeout': 300}
)

# Start subprocess
orchestrator.start()

# Send message
orchestrator.send_message("Hello Claude")

# Receive response
response = orchestrator.receive_output()

# Clean up
orchestrator.stop()
```

### Using the Agent System

```python
from claude_mpm.core import AgentRegistry
from claude_mpm.agents import AgentExecutor

# Get registry
registry = AgentRegistry()

# List available agents
agents = registry.list_agents()

# Execute agent
executor = AgentExecutor()
result = executor.execute_agent(
    agent_name="engineer",
    task="Create a function",
    context={"language": "python"}
)
```

### Hook System

```python
from claude_mpm.hooks import HookService, PreMessageHook

# Create hook
class MyHook(PreMessageHook):
    def execute(self, message: str) -> str:
        return f"[Modified] {message}"

# Register hook
hook_service = HookService()
hook_service.register_hook('pre_message', MyHook())

# Hooks execute automatically
```


## API Documentation Format

Each API entry includes:

### Function/Method Documentation

```python
def function_name(
    param1: Type,
    param2: Optional[Type] = None
) -> ReturnType:
    """Brief description of function.
    
    Longer description explaining the function's purpose,
    behavior, and any important details.
    
    Args:
        param1: Description of first parameter.
        param2: Description of optional parameter.
            Defaults to None.
    
    Returns:
        Description of return value.
    
    Raises:
        ExceptionType: When this exception is raised.
    
    Example:
        >>> result = function_name("value", param2=42)
        >>> print(result)
        Expected output
    
    Note:
        Any additional notes or warnings.
    
    Since: 1.0.0
    """
```

### Class Documentation

```python
class ClassName:
    """Brief description of class.
    
    Longer description explaining the class's purpose,
    usage, and important details.
    
    Attributes:
        attr1 (Type): Description of attribute.
        attr2 (Type): Description of attribute.
    
    Example:
        >>> obj = ClassName()
        >>> obj.method()
        Expected output
    
    Since: 1.0.0
    """
```

## API Sections

- **[Core API](core-api.md)**: Foundation classes and interfaces
- **[Orchestration API](orchestration-api.md)**: Subprocess orchestration
- **[Services API](services-api.md)**: Business logic services  
- **[Utils API](utils-api.md)**: Utility functions and helpers

## Getting Help

- Use Python's built-in help: `help(function_name)`
- Check docstrings: `function_name.__doc__`
- View source code: `inspect.getsource(function_name)`
- File issues for unclear documentation

## Next Steps

1. Explore the [Core API](core-api.md) for fundamental classes
2. Learn about [Orchestration](orchestration-api.md) for subprocess control
3. Review [Services](services-api.md) for business logic
4. Check [Utils](utils-api.md) for helpful utilities