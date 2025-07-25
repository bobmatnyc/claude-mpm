# Extending Claude MPM

This section provides comprehensive guides for extending Claude MPM with custom functionality.

## Overview

Claude MPM is designed with extensibility in mind. The framework provides multiple extension points that allow you to customize and enhance its behavior without modifying core code.

## Extension Points

### 1. [Custom Orchestrators](custom-orchestrators.md)
Create custom orchestrators to implement new subprocess management strategies or integrate with different execution environments.

### 2. [Custom Hooks](custom-hooks.md)
Implement hooks to intercept and modify behavior at key points in the execution lifecycle.

### 3. [Custom Services](custom-services.md)
Add new services to provide additional functionality or integrate with external systems.

### 4. [Plugins](plugins.md)
Build complete plugins that bundle orchestrators, hooks, and services together.

## Quick Start

### Creating a Simple Hook

```python
from claude_mpm.hooks.base_hook import SubmitHook, HookContext, HookResult

class LoggingHook(SubmitHook):
    """Log all user submissions."""
    
    def __init__(self):
        super().__init__(name="logging-hook", priority=10)
    
    async def execute(self, context: HookContext) -> HookResult:
        print(f"User submitted: {context.data.get('message')}")
        return HookResult(success=True)
```

### Creating a Custom Orchestrator

```python
from claude_mpm.orchestration.orchestrator import MPMOrchestrator

class CustomOrchestrator(MPMOrchestrator):
    """Custom orchestrator with special handling."""
    
    def _process_output_line(self, line: str):
        # Add custom processing
        if "CUSTOM_MARKER" in line:
            self.handle_custom_marker(line)
        
        # Call parent implementation
        super()._process_output_line(line)
    
    def handle_custom_marker(self, line: str):
        # Custom logic here
        pass
```

## Extension Architecture

```
Claude MPM Core
├── Extension Points
│   ├── Hook System
│   │   ├── Pre-hooks
│   │   ├── Post-hooks
│   │   └── Event hooks
│   ├── Orchestrator Interface
│   │   ├── Process Management
│   │   ├── I/O Handling
│   │   └── Session Control
│   └── Service Layer
│       ├── Service Interface
│       ├── Dependency Injection
│       └── Lifecycle Management
└── Plugin System
    ├── Plugin Discovery
    ├── Plugin Loading
    └── Plugin Configuration
```

## Best Practices

### 1. Follow the Interface Contracts
Always implement the required methods and respect the expected behavior of base classes.

### 2. Use Dependency Injection
Don't hardcode dependencies. Accept them as constructor parameters:

```python
class MyService:
    def __init__(self, config_manager, logger):
        self.config = config_manager
        self.logger = logger
```

### 3. Handle Errors Gracefully
Extensions should not crash the main application:

```python
async def execute(self, context: HookContext) -> HookResult:
    try:
        # Your logic here
        return HookResult(success=True)
    except Exception as e:
        self.logger.error(f"Hook failed: {e}")
        return HookResult(success=False, error=str(e))
```

### 4. Provide Configuration Options
Make your extensions configurable:

```python
class ConfigurableHook(BaseHook):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(
            name=config.get("name", "configurable-hook"),
            priority=config.get("priority", 50)
        )
        self.custom_option = config.get("custom_option", "default")
```

### 5. Document Your Extensions
Provide clear documentation including:
- Purpose and functionality
- Configuration options
- Usage examples
- Dependencies
- Performance considerations

## Testing Extensions

### Unit Testing

```python
import pytest
from claude_mpm.hooks.base_hook import HookContext

async def test_custom_hook():
    hook = CustomHook()
    context = HookContext(
        hook_type=HookType.SUBMIT,
        data={"message": "test"}
    )
    
    result = await hook.execute(context)
    assert result.success
    assert result.data.get("processed") == True
```

### Integration Testing

```python
def test_custom_orchestrator():
    orchestrator = CustomOrchestrator()
    
    # Test with mock Claude process
    with mock_claude_process() as process:
        orchestrator.process = process
        orchestrator.send_input("test input")
        
        output = orchestrator.get_output(timeout=1.0)
        assert "expected response" in output
```

## Distribution

### Package Structure

```
my-claude-mpm-extension/
├── setup.py
├── README.md
├── requirements.txt
├── my_extension/
│   ├── __init__.py
│   ├── hooks/
│   │   └── custom_hook.py
│   ├── orchestrators/
│   │   └── custom_orchestrator.py
│   └── services/
│       └── custom_service.py
└── tests/
    └── test_extension.py
```

### Setup.py Example

```python
from setuptools import setup, find_packages

setup(
    name="my-claude-mpm-extension",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "claude-mpm>=1.0.0",
    ],
    entry_points={
        "claude_mpm.hooks": [
            "my_hook = my_extension.hooks:MyHook",
        ],
        "claude_mpm.orchestrators": [
            "my_orchestrator = my_extension.orchestrators:MyOrchestrator",
        ],
    },
)
```

## Next Steps

- Read the detailed guides for each extension type
- Check out example extensions in the `examples/` directory
- Join the community to share your extensions
- Contribute your extensions back to the project