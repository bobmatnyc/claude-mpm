# Orchestrator Factory Pattern

## Overview

The `OrchestratorFactory` class provides a centralized way to create orchestrator instances based on mode and configuration. This pattern simplifies the complex orchestrator selection logic previously found in the `run_session` function, reducing its cyclomatic complexity from 19 to under 10.

## Benefits

1. **Reduced Complexity**: Eliminates complex if/elif chains for orchestrator selection
2. **Centralized Logic**: All orchestrator creation logic in one place
3. **Extensibility**: Easy to add new orchestrator types via registration
4. **Auto-discovery**: Automatically discovers available orchestrators
5. **Type Safety**: Uses enums for orchestrator modes
6. **Better Testing**: Factory pattern enables easier unit testing

## Usage

### Basic Usage

```python
from claude_mpm.orchestration.factory import OrchestratorFactory

# Create factory
factory = OrchestratorFactory()

# Create default orchestrator (SystemPromptOrchestrator)
orchestrator = factory.create_orchestrator()

# Create specific orchestrator type
orchestrator = factory.create_orchestrator(mode="subprocess")
```

### Configuration-based Creation

```python
# Build configuration from CLI args or other sources
config = {
    "framework_path": args.framework_path,
    "agents_dir": args.agents_dir,
    "log_level": args.logging,
    "log_dir": args.log_dir,
    "hook_manager": hook_manager,
    "subprocess": args.subprocess,
    "interactive_subprocess": args.interactive_subprocess,
    "enable_todo_hijacking": args.todo_hijack,
    "no_tickets": args.no_tickets,
}

# Factory determines mode from config flags
orchestrator = factory.create_orchestrator(config=config)
```

### Mode Precedence

The factory uses the following precedence for determining orchestrator mode:

1. **Explicit mode parameter**: If `mode` is provided, it takes precedence
2. **Config flags** (in order):
   - `interactive_subprocess=True` → InteractiveSubprocessOrchestrator
   - `subprocess=True` → SubprocessOrchestrator
   - Default → SystemPromptOrchestrator

## Available Orchestrator Modes

```python
from claude_mpm.orchestration.factory import OrchestratorMode

# Core modes always available
OrchestratorMode.SYSTEM_PROMPT      # SystemPromptOrchestrator
OrchestratorMode.SUBPROCESS         # SubprocessOrchestrator
OrchestratorMode.INTERACTIVE_SUBPROCESS  # InteractiveSubprocessOrchestrator

# Optional modes (auto-discovered if available)
OrchestratorMode.DIRECT            # DirectOrchestrator
OrchestratorMode.PTY               # PTYOrchestrator
OrchestratorMode.WRAPPER           # WrapperOrchestrator
OrchestratorMode.SIMPLE            # SimpleOrchestrator
```

## Listing Available Modes

```python
factory = OrchestratorFactory()
modes = factory.list_available_modes()

for mode_name, info in modes.items():
    print(f"{mode_name}:")
    print(f"  Class: {info['class']}")
    print(f"  Module: {info['module']}")
    print(f"  Description: {info['description']}")
```

## Registering Custom Orchestrators

```python
from claude_mpm.orchestration.orchestrator import MPMOrchestrator
from claude_mpm.orchestration.factory import OrchestratorFactory, OrchestratorMode

class CustomOrchestrator(MPMOrchestrator):
    """My custom orchestrator implementation."""
    pass

# Register with factory
factory = OrchestratorFactory()
factory.register_orchestrator(OrchestratorMode.CUSTOM, CustomOrchestrator)

# Now it can be created
orchestrator = factory.create_orchestrator(mode="custom")
```

## Refactoring run_session

### Before (Complex)

```python
def run_session(args, hook_manager=None):
    # ... setup code ...
    
    # Complex if/elif chain (cyclomatic complexity: 19)
    if getattr(args, 'interactive_subprocess', False):
        try:
            from .orchestration.interactive_subprocess_orchestrator import InteractiveSubprocessOrchestrator
        except ImportError:
            from orchestration.interactive_subprocess_orchestrator import InteractiveSubprocessOrchestrator
        orchestrator = InteractiveSubprocessOrchestrator(
            framework_path=framework_path,
            agents_dir=agents_dir,
            log_level=args.logging,
            log_dir=log_dir,
            hook_manager=hook_manager
        )
    elif getattr(args, 'subprocess', False):
        try:
            from .orchestration.subprocess_orchestrator import SubprocessOrchestrator
        except ImportError:
            from orchestration.subprocess_orchestrator import SubprocessOrchestrator
        orchestrator = SubprocessOrchestrator(
            framework_path=framework_path,
            agents_dir=agents_dir,
            log_level=args.logging,
            log_dir=log_dir,
            hook_manager=hook_manager,
            enable_todo_hijacking=getattr(args, 'todo_hijack', False)
        )
    else:
        # Default to system prompt orchestrator
        try:
            from .orchestration.system_prompt_orchestrator import SystemPromptOrchestrator
        except ImportError:
            from orchestration.system_prompt_orchestrator import SystemPromptOrchestrator
        orchestrator = SystemPromptOrchestrator(
            framework_path=framework_path,
            agents_dir=agents_dir,
            log_level=args.logging,
            log_dir=log_dir,
            hook_manager=hook_manager
        )
    
    # ... rest of function ...
```

### After (Simple)

```python
def run_session(args, hook_manager=None):
    # ... setup code ...
    
    # Simple factory-based creation (cyclomatic complexity: <10)
    factory = OrchestratorFactory()
    
    config = {
        "framework_path": args.framework_path,
        "agents_dir": getattr(args, 'agents_dir', None),
        "log_level": args.logging,
        "log_dir": args.log_dir,
        "hook_manager": hook_manager,
        "subprocess": getattr(args, 'subprocess', False),
        "interactive_subprocess": getattr(args, 'interactive_subprocess', False),
        "enable_todo_hijacking": getattr(args, 'todo_hijack', False),
        "no_tickets": args.no_tickets,
    }
    
    orchestrator = factory.create_orchestrator(config=config)
    
    # ... rest of function ...
```

## Error Handling

The factory provides clear error messages for common issues:

```python
try:
    orchestrator = factory.create_orchestrator(mode="invalid")
except ValueError as e:
    print(f"Error: {e}")
    # Output: "Invalid orchestrator mode: invalid. Available modes: system_prompt, subprocess, ..."

try:
    factory.register_orchestrator(mode, NonOrchestratorClass)
except ValueError as e:
    print(f"Error: {e}")
    # Output: "NonOrchestratorClass must inherit from MPMOrchestrator"
```

## Integration with CLI

The factory integrates seamlessly with the existing CLI structure:

1. Parse command-line arguments
2. Build configuration dictionary from args
3. Pass config to factory
4. Factory handles all orchestrator selection logic
5. Return configured orchestrator ready to use

This pattern maintains backward compatibility while significantly reducing code complexity.