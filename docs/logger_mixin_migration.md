# LoggerMixin Migration Guide

This guide shows how to migrate existing classes to use the new `LoggerMixin` for automatic logger initialization.

## Overview

The `LoggerMixin` eliminates duplicate logger initialization code by providing automatic logger setup through inheritance.

## Migration Example

### Before (Duplicate Pattern)
```python
import logging
from typing import Optional

class FrameworkProtector:
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("FrameworkProtector initialized")
```

### After (Using LoggerMixin)
```python
from claude_mpm.core import LoggerMixin
from typing import Optional
import logging

class FrameworkProtector(LoggerMixin):
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        self.config = config
        if logger:
            self.set_logger(logger=logger)
        self.logger.info("FrameworkProtector initialized")
```

## Key Benefits

1. **Eliminates Duplication**: No more `self.logger = logger or logging.getLogger(__name__)`
2. **Consistent Naming**: Automatic logger names based on module and class
3. **Lazy Initialization**: Logger created only when first accessed
4. **Flexible**: Supports custom logger names and pre-configured loggers

## Usage Patterns

### Basic Usage
```python
class MyService(LoggerMixin):
    def process(self):
        self.logger.info("Processing...")
```

### Custom Logger Name
```python
class MyService(LoggerMixin):
    def __init__(self):
        self._logger_name = "custom.service.name"
        self.logger.info("Using custom logger")
```

### Accepting Logger in Constructor
```python
class MyService(LoggerMixin):
    def __init__(self, logger: Optional[logging.Logger] = None):
        if logger:
            self.set_logger(logger=logger)
        self.logger.info("Service ready")
```

### Multiple Inheritance
```python
class BaseService:
    def __init__(self, config):
        self.config = config

class MyService(BaseService, LoggerMixin):
    def __init__(self, config):
        super().__init__(config)
        self.logger.info("Service initialized")
```

## Migration Steps

1. Add `LoggerMixin` to class inheritance
2. Remove `self.logger = logger or logging.getLogger(__name__)` line
3. If constructor accepts a logger parameter, add:
   ```python
   if logger:
       self.set_logger(logger=logger)
   ```
4. Update imports to include `from claude_mpm.core import LoggerMixin`

## Notes

- The mixin uses `@property` for lazy initialization
- Logger names follow the pattern: `module.ClassName`
- Multiple instances of the same class share the same logger
- Compatible with existing logging configuration