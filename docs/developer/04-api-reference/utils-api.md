# Utilities API Reference

This document provides a comprehensive API reference for the utility modules in Claude MPM.

## Table of Contents

1. [Overview](#overview)
2. [Logger Utilities](#logger-utilities)
3. [Subprocess Utilities](#subprocess-utilities)
4. [File Utilities](#file-utilities)
5. [Path Operations](#path-operations)
6. [Config Manager](#config-manager)
7. [Import Utilities](#import-utilities)

---

## Overview

The utilities package provides common functionality used throughout Claude MPM, including logging, subprocess management, path operations, and configuration handling.

---

## Logger Utilities

Centralized logging configuration and utilities.

### Location
`src/claude_mpm/utils/logger.py`

### get_logger()

```python
def get_logger(name: str, level: Optional[str] = None) -> logging.Logger
```

Get a configured logger instance.

**Parameters:**
- `name` (str): Logger name (typically `__name__`)
- `level` (Optional[str]): Override log level

**Returns:** Configured logger instance

**Example:**
```python
from claude_mpm.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Starting process")
logger.debug("Debug information")
```

### setup_logging()

```python
def setup_logging(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger
```

Set up logging configuration for the application.

**Parameters:**
- `level` (str): Log level (DEBUG, INFO, WARNING, ERROR)
- `log_dir` (Optional[Path]): Directory for log files
- `log_file` (Optional[str]): Log filename
- `format_string` (Optional[str]): Custom format string

**Returns:** Root logger instance

**Example:**
```python
from pathlib import Path
from claude_mpm.utils.logger import setup_logging

logger = setup_logging(
    level="DEBUG",
    log_dir=Path("./logs"),
    log_file="claude-mpm.log"
)
```

### Log Format

Default format:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

With debug enabled:
```
%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s
```

---

## Subprocess Utilities

Enhanced subprocess execution and management utilities with proper error handling, timeouts, and process cleanup.

### Location
`src/claude_mpm/utils/subprocess_utils.py`

### run_subprocess()

```python
def run_subprocess(
    cmd: List[str],
    timeout: Optional[float] = None,
    capture_output: bool = True,
    text: bool = True,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    **kwargs
) -> SubprocessResult
```

Run a subprocess with enhanced error handling and timeout support.

**Parameters:**
- `cmd` (List[str]): Command and arguments to execute
- `timeout` (Optional[float]): Maximum time to wait for completion (seconds)
- `capture_output` (bool): Whether to capture stdout/stderr
- `text` (bool): Whether to return text (True) or bytes (False)
- `cwd` (Optional[str]): Working directory for the subprocess
- `env` (Optional[Dict[str, str]]): Environment variables for the subprocess

**Returns:** SubprocessResult object with returncode, stdout, stderr

**Raises:** SubprocessError if the subprocess fails or times out

**Example:**
```python
from claude_mpm.utils.subprocess_utils import run_subprocess, SubprocessError

try:
    result = run_subprocess(["echo", "Hello World"], timeout=30)
    if result.success:
        print(f"Output: {result.stdout}")
    else:
        print(f"Failed with code: {result.returncode}")
except SubprocessError as e:
    print(f"Subprocess error: {e}")
```

### terminate_process_tree()

```python
def terminate_process_tree(pid: int, timeout: float = 5.0) -> int
```

Terminate a process and all its children gracefully.

**Parameters:**
- `pid` (int): Process ID to terminate
- `timeout` (float): Time to wait for graceful termination before force killing

**Returns:** Number of processes terminated

**Example:**
```python
from claude_mpm.utils.subprocess_utils import terminate_process_tree

# Terminate process and all children
terminated_count = terminate_process_tree(process.pid)
print(f"Terminated {terminated_count} processes")
```

### cleanup_orphaned_processes()

```python
def cleanup_orphaned_processes(pattern: str, max_age_hours: float = 1.0) -> int
```

Clean up orphaned processes matching a pattern.

**Parameters:**
- `pattern` (str): String pattern to match in process command line
- `max_age_hours` (float): Maximum age in hours before considering a process orphaned

**Returns:** Number of processes cleaned up

**Example:**
```python
from claude_mpm.utils.subprocess_utils import cleanup_orphaned_processes

# Clean up old hook handler processes
cleanup_count = cleanup_orphaned_processes('hook_handler.py', max_age_hours=0.5)
print(f"Cleaned up {cleanup_count} orphaned processes")
```

---

## File Utilities

Safe file operations with atomic writes, error handling, and directory management.

### Location
`src/claude_mpm/utils/file_utils.py`

### atomic_write()

```python
def atomic_write(
    path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8',
    create_dirs: bool = True
) -> None
```

Atomically write content to a file using a temporary file to prevent corruption.

**Parameters:**
- `path` (Union[str, Path]): File path to write
- `content` (str): Content to write
- `encoding` (str): Text encoding to use
- `create_dirs` (bool): Whether to create parent directories

**Example:**
```python
from claude_mpm.utils.file_utils import atomic_write

# Safely write configuration
atomic_write("config.json", json.dumps(config_data, indent=2))
```

### read_json_file() / write_json_file()

```python
def read_json_file(path: Union[str, Path]) -> Any
def write_json_file(path: Union[str, Path], data: Any, indent: int = 2, atomic: bool = True) -> None
```

Read and write JSON files safely with error handling.

**Example:**
```python
from claude_mpm.utils.file_utils import read_json_file, write_json_file

# Read JSON configuration
config = read_json_file("config.json")

# Write JSON data atomically
write_json_file("output.json", {"status": "complete"}, atomic=True)
```

---

## Path Operations

Utilities for path manipulation and validation.

### Location
`src/claude_mpm/utils/path_operations.py`

### resolve_path()

```python
def resolve_path(
    path: Union[str, Path],
    base_path: Optional[Path] = None,
    must_exist: bool = False
) -> Path
```

Resolve a path, optionally relative to a base path.

**Parameters:**
- `path` (Union[str, Path]): Path to resolve
- `base_path` (Optional[Path]): Base path for relative resolution
- `must_exist` (bool): Raise if path doesn't exist

**Returns:** Resolved Path object

**Example:**
```python
from claude_mpm.utils.path_operations import resolve_path

# Resolve relative to project root
config_path = resolve_path("config.yml", base_path=project_root)

# Ensure file exists
data_file = resolve_path("data.json", must_exist=True)
```

### ensure_directory()

```python
def ensure_directory(path: Union[str, Path], mode: int = 0o755) -> Path
```

Ensure a directory exists, creating if necessary.

**Parameters:**
- `path` (Union[str, Path]): Directory path
- `mode` (int): Directory permissions

**Returns:** Path object

### find_project_root()

```python
def find_project_root(
    start_path: Optional[Path] = None,
    markers: Optional[List[str]] = None
) -> Optional[Path]
```

Find project root directory by looking for marker files.

**Parameters:**
- `start_path` (Optional[Path]): Starting directory
- `markers` (Optional[List[str]]): Marker files (default: [".git", "pyproject.toml"])

**Returns:** Project root path or None

### safe_write()

```python
def safe_write(
    path: Union[str, Path],
    content: Union[str, bytes],
    backup: bool = True,
    encoding: str = "utf-8"
) -> Path
```

Safely write content to file with optional backup.

**Parameters:**
- `path` (Union[str, Path]): File path
- `content` (Union[str, bytes]): Content to write
- `backup` (bool): Create backup before writing
- `encoding` (str): Text encoding

**Returns:** Path to written file

---

## Config Manager

Configuration management utilities.

### Location
`src/claude_mpm/utils/config_manager.py`

### ConfigManager Class

```python
class ConfigManager:
    """Manage application configuration."""
    
    def __init__(
        self,
        config_file: Optional[Path] = None,
        defaults: Optional[Dict[str, Any]] = None
    )
```

### Key Methods

#### load()

```python
def load(self) -> Dict[str, Any]
```

Load configuration from file.

**Returns:** Configuration dictionary

#### save()

```python
def save(self, config: Dict[str, Any])
```

Save configuration to file.

#### get()

```python
def get(self, key: str, default: Any = None) -> Any
```

Get configuration value by key.

**Parameters:**
- `key` (str): Dot-notation key (e.g., "server.port")
- `default` (Any): Default value if not found

**Example:**
```python
from claude_mpm.utils.config_manager import ConfigManager

config = ConfigManager()
config.load()

# Get nested value
port = config.get("server.port", 8080)
model = config.get("claude.model", "opus")

# Update and save
config.set("claude.model", "sonnet")
config.save()
```

#### set()

```python
def set(self, key: str, value: Any)
```

Set configuration value.

#### merge()

```python
def merge(self, updates: Dict[str, Any])
```

Merge updates into configuration.

### Environment Variable Support

```python
def load_from_env(self, prefix: str = "CLAUDE_MPM_") -> Dict[str, Any]
```

Load configuration from environment variables.

**Example:**
```python
# Environment: CLAUDE_MPM_MODEL=sonnet
config.load_from_env()
model = config.get("model")  # "sonnet"
```

---

## Import Utilities

Utilities for dynamic imports and module loading.

### Location
`src/claude_mpm/utils/imports.py`

### import_module_from_path()

```python
def import_module_from_path(
    module_name: str,
    file_path: Union[str, Path]
) -> Any
```

Import a module from a file path.

**Parameters:**
- `module_name` (str): Name to give the module
- `file_path` (Union[str, Path]): Path to Python file

**Returns:** Imported module

**Example:**
```python
from claude_mpm.utils.imports import import_module_from_path

# Import custom hook
hook_module = import_module_from_path(
    "custom_hook",
    "/path/to/custom_hook.py"
)
hook_class = hook_module.CustomHook
```

### load_class()

```python
def load_class(class_path: str) -> Type
```

Load a class by dotted path.

**Parameters:**
- `class_path` (str): Dotted path (e.g., "mymodule.MyClass")

**Returns:** Class object

**Example:**
```python
from claude_mpm.utils.imports import load_class

# Load orchestrator class
OrchestratorClass = load_class("claude_mpm.orchestration.SubprocessOrchestrator")
orchestrator = OrchestratorClass()
```

### safe_import()

```python
def safe_import(
    module_name: str,
    fallback: Optional[Any] = None
) -> Any
```

Safely import a module with fallback.

**Parameters:**
- `module_name` (str): Module to import
- `fallback` (Optional[Any]): Fallback value on import error

**Returns:** Module or fallback value

---

## Utility Patterns

### Context Managers

```python
from contextlib import contextmanager
from claude_mpm.utils.path_operations import ensure_directory

@contextmanager
def temp_working_directory(path: Path):
    """Temporarily change working directory."""
    original = Path.cwd()
    try:
        ensure_directory(path)
        os.chdir(path)
        yield path
    finally:
        os.chdir(original)

# Usage
with temp_working_directory(Path("/tmp/work")):
    # Operations in temporary directory
    pass
```

### Decorators

```python
from functools import wraps
from claude_mpm.utils.logger import get_logger

def log_execution(func):
    """Log function execution."""
    logger = get_logger(func.__module__)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Executing {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}")
            raise
    
    return wrapper

# Usage
@log_execution
def process_data(data):
    # Function implementation
    pass
```

### Retry Logic

```python
from claude_mpm.utils import retry_with_backoff

@retry_with_backoff(max_attempts=3, backoff_factor=2.0)
def unreliable_operation():
    """Operation that might fail."""
    # Implementation
    pass
```

---

## Error Handling

Utilities implement consistent error handling:

1. **Validation Errors**: Raise ValueError with descriptive messages
2. **File System Errors**: Raise IOError or OSError
3. **Import Errors**: Return None or fallback values
4. **Process Errors**: Raise subprocess.CalledProcessError

### Example Error Handling

```python
from claude_mpm.utils.path_operations import resolve_path
from claude_mpm.utils.logger import get_logger

logger = get_logger(__name__)

try:
    config_path = resolve_path("config.yml", must_exist=True)
except FileNotFoundError as e:
    logger.error(f"Configuration file not found: {e}")
    # Use defaults or exit
except ValueError as e:
    logger.error(f"Invalid path: {e}")
    # Handle invalid input
```

---

## Best Practices

1. **Logging**:
   - Use appropriate log levels
   - Include context in log messages
   - Avoid logging sensitive information

2. **Path Operations**:
   - Use Path objects instead of strings
   - Always validate paths before operations
   - Use context managers for temporary operations

4. **Configuration**:
   - Provide sensible defaults
   - Support environment variable overrides
   - Validate configuration on load