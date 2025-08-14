# Claude MPM Exception Hierarchy

## Overview

Claude MPM uses a centralized exception hierarchy to standardize error handling across the codebase. All custom exceptions inherit from `MPMError` and provide contextual information for better debugging.

## Exception Classes

### Base Exception

**`MPMError`** - Base class for all MPM exceptions
- Stores message and optional context dictionary
- Generates error codes automatically from class names
- Provides `to_dict()` for structured logging

### Specific Exception Classes

| Exception | Purpose | Common Context Fields |
|-----------|---------|----------------------|
| **`AgentDeploymentError`** | Agent deployment failures | `agent_id`, `template_path`, `deployment_path` |
| **`ConfigurationError`** | Configuration validation errors | `config_file`, `field`, `expected_type`, `actual_value` |
| **`ConnectionError`** | Network/SocketIO connection issues | `host`, `port`, `timeout`, `retry_count` |
| **`ValidationError`** | Input validation failures | `field`, `value`, `constraint`, `schema_path` |
| **`ServiceNotFoundError`** | DI container service lookup failures | `service_name`, `service_type`, `available_services` |
| **`MemoryError`** | Memory service operation failures | `agent_id`, `memory_type`, `operation`, `storage_path` |
| **`HookError`** | Hook execution failures | `hook_name`, `hook_type`, `event`, `error_details` |
| **`SessionError`** | Session management failures | `session_id`, `session_type`, `state`, `operation` |

## Usage Examples

### Basic Usage

```python
from claude_mpm.core.exceptions import AgentDeploymentError

# Simple error
raise AgentDeploymentError("Deployment failed")

# Error with context
raise AgentDeploymentError(
    "Template not found",
    context={
        "agent_id": "engineer",
        "template_path": "/agents/engineer.json"
    }
)
```

### Catching Specific Errors

```python
from claude_mpm.core.exceptions import ConnectionError

try:
    # Network operation
    connect_to_server()
except ConnectionError as e:
    print(f"Connection failed: {e}")
    print(f"Context: {e.context}")
    # Retry logic here
```

### Using Error Groups

```python
from claude_mpm.core.exceptions import CONFIGURATION_ERRORS, ALL_MPM_ERRORS

# Catch configuration-related errors
try:
    validate_config()
except CONFIGURATION_ERRORS as e:
    # Catches ConfigurationError and ValidationError
    handle_config_error(e)

# Catch all MPM errors
try:
    complex_operation()
except ALL_MPM_ERRORS as e:
    # Catches any MPM-specific exception
    log_error(e.to_dict())
```

### Structured Logging

```python
from claude_mpm.core.exceptions import HookError
import json

try:
    execute_hook()
except HookError as e:
    # Get structured error data
    error_data = e.to_dict()
    # Log as JSON for monitoring systems
    logger.error(json.dumps(error_data))
```

## Migration Guide

### Updating Existing Code

Replace generic exceptions with specific MPM exceptions:

**Before:**
```python
raise ValueError(f"Invalid config: {field}")
```

**After:**
```python
from claude_mpm.core.exceptions import ConfigurationError

raise ConfigurationError(
    "Invalid configuration",
    context={"field": field, "value": value}
)
```

### Backward Compatibility

The exception hierarchy maintains backward compatibility:
- Existing `except Exception` clauses still work
- All MPM exceptions inherit from Python's `Exception`
- Context is optional - simple string messages work

### Factory Functions

For convenience, factory functions are available:

```python
from claude_mpm.core.exceptions import create_configuration_error

error = create_configuration_error(
    "Invalid timeout value",
    config_file="config.yaml",
    field="timeout",
    expected_type="int"
)
```

## Error Groups

Pre-defined error groups for catch-all handling:

- **`DEPLOYMENT_ERRORS`** - Agent deployment errors
- **`CONFIGURATION_ERRORS`** - Configuration and validation errors
- **`NETWORK_ERRORS`** - Connection and network errors
- **`SERVICE_ERRORS`** - Service, memory, hook, and session errors
- **`ALL_MPM_ERRORS`** - All MPM-specific exceptions

## Best Practices

1. **Always provide context** when raising exceptions:
   ```python
   raise ValidationError(
       "Invalid agent version",
       context={"version": version, "expected_format": "x.y.z"}
   )
   ```

2. **Use specific exceptions** rather than generic ones:
   ```python
   # Good
   raise AgentDeploymentError("Deployment failed")
   
   # Avoid
   raise Exception("Deployment failed")
   ```

3. **Include actionable information** in error messages:
   ```python
   raise ConfigurationError(
       "Port must be between 1024-65535",
       context={"port": port, "config_file": "server.yaml"}
   )
   ```

4. **Use error groups** for broad exception handling:
   ```python
   try:
       deploy_agent()
   except DEPLOYMENT_ERRORS as e:
       rollback_deployment()
       raise
   ```

5. **Log structured errors** for monitoring:
   ```python
   except MPMError as e:
       metrics.record_error(
           error_type=e.__class__.__name__,
           error_code=e.error_code,
           context=e.context
       )
   ```

## Implementation Details

The exception hierarchy is implemented in:
- **Source**: `/src/claude_mpm/core/exceptions.py`
- **Tests**: `/tests/test_exceptions.py`
- **Examples**: `/examples/exception_usage.py`

### Files Updated to Use New Exceptions

- `/src/claude_mpm/services/agents/deployment/agent_deployment.py` - Uses `AgentDeploymentError`
- `/src/claude_mpm/services/socketio_server.py` - Uses `ConnectionError`
- `/src/claude_mpm/core/config.py` - Uses `ConfigurationError`

Additional files can be updated incrementally as needed while maintaining backward compatibility.