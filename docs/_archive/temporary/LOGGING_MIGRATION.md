# Logging Migration Guide

This guide helps developers migrate existing code to use the standardized logging infrastructure introduced in TSK-0045.

## Overview

The new centralized logging system provides:
- Consistent logger factory method (`get_logger`)
- Structured logging with context
- Performance logging decorators
- Context managers for operation tracking
- Standardized log levels and formatting

## Quick Migration Steps

### 1. Update Import Statements

**Old:**
```python
from claude_mpm.core.logger import get_logger
# or
import logging
logger = logging.getLogger(__name__)
```

**New:**
```python
from claude_mpm.core.logging_config import get_logger, log_operation, log_performance_context
```

### 2. Update Logger Initialization

**Old:**
```python
self.logger = get_logger("my_service")
# or
self.logger = logging.getLogger("my_service")
```

**New:**
```python
self.logger = get_logger(__name__)  # Uses module name for consistency
```

### 3. Replace Print Statements

**Old:**
```python
print(f"Processing {count} items")
print(f"Error: {error_msg}")
```

**New:**
```python
self.logger.info(f"Processing items", extra={"count": count})
self.logger.error(f"Processing failed", extra={"error": error_msg})
```

### 4. Add Structured Context

**Old:**
```python
self.logger.info(f"User {user_id} performed action {action}")
```

**New:**
```python
self.logger.info("User performed action", extra={
    "user_id": user_id,
    "action": action
})
```

## Advanced Features

### Operation Tracking

Track operations with automatic timing:

```python
with log_operation(self.logger, "database_query", query_type="select"):
    # Perform database operation
    result = db.query(sql)
    # Automatically logs start, end, and timing
```

### Performance Monitoring

Monitor performance with thresholds:

```python
with log_performance_context(
    self.logger,
    "api_call",
    warn_threshold=1.0,  # Warn if takes > 1 second
    error_threshold=5.0   # Error if takes > 5 seconds
):
    response = make_api_call()
```

### Function Call Logging

Automatically log function entry/exit:

```python
@log_function_call
def process_data(self, data: dict) -> dict:
    # Function entry/exit automatically logged
    return {"processed": True}
```

### Contextual Logging

Add context that applies to all logs in a scope:

```python
with LogContext.context(request_id="req_123", user="alice"):
    # All logs in this block will include request_id and user
    self.logger.info("Processing request")
    self.logger.info("Request completed")
```

## Log Level Guidelines

Use appropriate log levels based on the standardized definitions:

| Level | Usage | Example |
|-------|-------|---------|
| **DEBUG** | Detailed diagnostic information | Variable values, execution flow |
| **INFO** | Normal operations, significant events | Service started, request completed |
| **WARNING** | Potentially harmful situations | Deprecated API usage, retry attempts |
| **ERROR** | Error events allowing continued operation | Single request failure |
| **CRITICAL** | Events that may cause abort | Database connection lost |

## Migration Checklist

- [ ] Update all import statements to use `logging_config`
- [ ] Replace `get_logger("name")` with `get_logger(__name__)`
- [ ] Convert print statements to appropriate log levels
- [ ] Add structured context using `extra` parameter
- [ ] Replace error prints with `logger.error()` or `logger.exception()`
- [ ] Add operation tracking for long-running operations
- [ ] Add performance monitoring for critical paths
- [ ] Review and apply appropriate log levels

## Common Patterns

### Error Handling

```python
try:
    # Operation that might fail
    result = risky_operation()
except SpecificError as e:
    self.logger.error("Operation failed", exc_info=True, extra={
        "error_type": type(e).__name__,
        "recovery_action": "retry"
    })
    # Handle error...
```

### Service Initialization

```python
class MyService:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("Service initialized", extra={
            "version": self.version,
            "config": self.config_summary
        })
```

### API Request Logging

```python
with log_operation(self.logger, "api_request", endpoint=endpoint, method=method):
    response = make_request(endpoint, method, data)
    self.logger.info("Request completed", extra={
        "status_code": response.status_code,
        "response_time": response.elapsed
    })
```

## Backward Compatibility

The new logging system maintains backward compatibility:
- Existing `get_logger()` calls still work
- The underlying `logger.py` module is still available
- Gradual migration is supported

## Benefits After Migration

- **Consistency**: All components use the same logging patterns
- **Debugging**: Easier to trace issues with structured logs
- **Monitoring**: Better integration with log aggregation systems
- **Performance**: Automatic performance tracking and alerting
- **Context**: Rich contextual information in all logs

## Example Migration

See `/examples/logging_usage.py` for a complete example demonstrating all logging patterns and best practices.

## Support

For questions or issues during migration, please:
1. Check the example code in `/examples/logging_usage.py`
2. Review the logging configuration in `/src/claude_mpm/core/logging_config.py`
3. Open an issue with the `logging` tag for assistance