# Coding Standards

This document defines the coding standards and conventions for the Claude MPM project. Following these standards ensures consistency, readability, and maintainability across the codebase.

## Python Style Guide

### PEP 8 Compliance

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these modifications:
- Line length: 88 characters (Black default)
- Use double quotes for strings
- Use trailing commas in multi-line structures

### Code Formatting

We use [Black](https://black.readthedocs.io/) for automatic code formatting:

```bash
# Format all code
black src/ tests/

# Check formatting without changes
black --check src/ tests/

# Black configuration in pyproject.toml
[tool.black]
line-length = 88
target-version = ['py38']
include = '\.pyi?$'
```

### Import Organization

Imports should be organized in the following order:

```python
# Standard library imports
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Third-party imports
import click
import yaml
from pydantic import BaseModel

# Local imports
from claude_mpm.core import ClaudeLauncher
from claude_mpm.orchestration import BaseOrchestrator
from claude_mpm.utils import logger
```

Use `isort` for automatic import sorting:

```bash
# Sort imports
isort src/ tests/

# Configuration in pyproject.toml
[tool.isort]
profile = "black"
line_length = 88
```

## Type Hints

### Required Type Hints

All public functions and methods must have type hints:

```python
# Good
def process_message(message: str, timeout: float = 30.0) -> Optional[str]:
    """Process a message with timeout."""
    ...

# Bad
def process_message(message, timeout=30.0):
    """Process a message with timeout."""
    ...
```

### Complex Type Hints

Use type aliases for complex types:

```python
from typing import Dict, List, Tuple, Union, TypeAlias

# Type aliases
MessageDict: TypeAlias = Dict[str, Union[str, int, float]]
AgentList: TypeAlias = List[Tuple[str, float]]

def process_agents(agents: AgentList) -> MessageDict:
    """Process a list of agents."""
    ...
```

### Optional and Union Types

```python
from typing import Optional, Union

# Optional for nullable types
def find_agent(name: str) -> Optional[Agent]:
    """Find an agent by name, returns None if not found."""
    ...

# Union for multiple types
def parse_config(data: Union[str, dict]) -> dict:
    """Parse configuration from string or dict."""
    if isinstance(data, str):
        return yaml.safe_load(data)
    return data
```

## Documentation

### Docstring Format

We use Google-style docstrings:

```python
def execute_agent(
    agent_name: str,
    task: str,
    context: Optional[dict] = None,
    timeout: float = 300.0
) -> AgentResult:
    """Execute an agent with the given task.
    
    This function creates a subprocess for the specified agent and
    executes the task with the provided context.
    
    Args:
        agent_name: Name of the agent to execute.
        task: Task description for the agent.
        context: Optional context dictionary containing additional
            information for the agent.
        timeout: Maximum execution time in seconds.
    
    Returns:
        AgentResult containing the execution output and metadata.
    
    Raises:
        AgentNotFoundError: If the specified agent doesn't exist.
        TimeoutError: If execution exceeds the timeout.
        SubprocessError: If the subprocess fails.
    
    Example:
        >>> result = execute_agent("engineer", "Create a function")
        >>> print(result.output)
    """
    ...
```

### Module Documentation

Every module should have a module-level docstring:

```python
"""Agent execution module.

This module provides functionality for executing agents as subprocesses,
managing their lifecycle, and collecting results.

Key components:
    - AgentExecutor: Main class for agent execution
    - AgentResult: Result container with metadata
    - execute_agent: Convenience function for single execution
"""
```

### Class Documentation

```python
class SubprocessOrchestrator(BaseOrchestrator):
    """Orchestrator that manages Claude as a subprocess.
    
    This orchestrator provides full control over Claude's execution,
    including I/O stream management, pattern detection, and resource
    monitoring.
    
    Attributes:
        process: The subprocess.Popen instance.
        config: Configuration dictionary.
        pattern_detector: Instance for detecting patterns in output.
        
    Example:
        >>> orchestrator = SubprocessOrchestrator(config)
        >>> orchestrator.start()
        >>> orchestrator.send_message("Hello")
        >>> response = orchestrator.receive_output()
    """
```

## Code Organization

### File Structure

```python
# Each file should have this structure:

"""Module docstring."""

# Imports
import ...

# Constants
DEFAULT_TIMEOUT = 300
MAX_RETRIES = 3

# Type aliases
MessageType: TypeAlias = Dict[str, Any]

# Exceptions
class CustomError(Exception):
    """Custom exception for this module."""
    pass

# Main classes
class MainClass:
    """Main class implementation."""
    pass

# Helper functions
def helper_function():
    """Helper function."""
    pass

# Module initialization (if needed)
__all__ = ['MainClass', 'helper_function']
```

### Class Organization

```python
class ExampleClass:
    """Example class showing organization."""
    
    # Class variables
    default_timeout = 300
    
    def __init__(self, config: dict):
        """Initialize the class."""
        # Instance variables
        self.config = config
        self._internal_state = None
        
    # Properties
    @property
    def timeout(self) -> float:
        """Get timeout value."""
        return self.config.get('timeout', self.default_timeout)
    
    # Public methods
    def public_method(self):
        """Public API method."""
        pass
    
    # Internal methods
    def _internal_method(self):
        """Internal implementation detail."""
        pass
    
    # Static/class methods
    @staticmethod
    def utility_method():
        """Utility method."""
        pass
    
    # Special methods
    def __str__(self):
        """String representation."""
        return f"ExampleClass(config={self.config})"
```

## Naming Conventions

### Variables and Functions

```python
# Use snake_case for variables and functions
user_name = "John"
def calculate_total(items: List[float]) -> float:
    pass

# Use descriptive names
# Good
def get_active_agents() -> List[Agent]:
    pass

# Bad
def get_agents() -> List[Agent]:  # Ambiguous
    pass
```

### Classes

```python
# Use PascalCase for classes
class AgentExecutor:
    pass

class HTTPClient:  # Acronyms in PascalCase
    pass

# Exception classes end with Error
class AgentNotFoundError(Exception):
    pass
```

### Constants

```python
# Use UPPER_SNAKE_CASE for constants
MAX_AGENTS = 10
DEFAULT_TIMEOUT = 300.0
SUPPORTED_LANGUAGES = ['python', 'javascript', 'go']

# Configuration constants
class Config:
    DEBUG_MODE = False
    LOG_LEVEL = "INFO"
    MAX_RETRIES = 3
```

### Private Members

```python
class Example:
    def __init__(self):
        # Single underscore for internal use
        self._internal_cache = {}
        
        # Double underscore for name mangling (rare)
        self.__private_key = "secret"
    
    def _internal_helper(self):
        """Internal method, not part of public API."""
        pass
```

## Error Handling

### Exception Handling

```python
# Be specific with exceptions
try:
    result = risky_operation()
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
    raise
except PermissionError as e:
    logger.error(f"Permission denied: {e}")
    return None
except Exception as e:
    # Catch-all should be last
    logger.exception(f"Unexpected error: {e}")
    raise

# Always include context
try:
    agent = self.registry.get_agent(name)
except AgentNotFoundError:
    raise AgentNotFoundError(
        f"Agent '{name}' not found. Available agents: {self.registry.list_agents()}"
    )
```

### Custom Exceptions

```python
class ClaudeMPMError(Exception):
    """Base exception for Claude MPM."""
    pass

class OrchestratorError(ClaudeMPMError):
    """Orchestrator-related errors."""
    pass

class AgentError(ClaudeMPMError):
    """Agent-related errors."""
    def __init__(self, agent_name: str, message: str):
        self.agent_name = agent_name
        super().__init__(f"Agent '{agent_name}': {message}")
```

## Logging

### Logging Standards

```python
import logging

# Get logger at module level
logger = logging.getLogger(__name__)

class Example:
    def process(self):
        logger.debug("Starting process")
        
        try:
            # Use appropriate log levels
            logger.info(f"Processing item: {item_id}")
            result = self._do_work()
            logger.debug(f"Result: {result}")
            
        except Exception as e:
            # Include context in error logs
            logger.error(
                f"Failed to process item {item_id}",
                exc_info=True,
                extra={'item_id': item_id, 'user': user}
            )
            raise
        
        logger.info(f"Successfully processed item: {item_id}")
```

### Log Levels

```python
# DEBUG: Detailed information for diagnosing problems
logger.debug(f"Subprocess PID: {process.pid}")

# INFO: General informational messages
logger.info("Agent execution completed successfully")

# WARNING: Something unexpected but not an error
logger.warning(f"Agent took {duration}s, approaching timeout")

# ERROR: Error occurred but application continues
logger.error(f"Failed to create ticket: {e}")

# CRITICAL: Serious error, application might stop
logger.critical("Cannot connect to Claude CLI")
```

## Testing

### Test Naming

```python
# Test files: test_<module>.py
test_orchestrator.py
test_agent_registry.py

# Test classes: Test<ClassName>
class TestSubprocessOrchestrator:
    pass

# Test methods: test_<what_is_being_tested>
def test_agent_execution_with_timeout():
    pass

def test_pattern_detection_finds_todos():
    pass
```

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch

class TestAgentExecutor:
    """Test AgentExecutor functionality."""
    
    @pytest.fixture
    def executor(self):
        """Create executor instance for tests."""
        return AgentExecutor(config={'max_workers': 2})
    
    @pytest.fixture
    def mock_agent(self):
        """Create mock agent for tests."""
        agent = Mock(spec=Agent)
        agent.name = "test_agent"
        return agent
    
    def test_execute_single_agent(self, executor, mock_agent):
        """Test executing a single agent."""
        # Arrange
        task = "Test task"
        expected_result = "Task completed"
        
        # Act
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value.communicate.return_value = (
                expected_result, ""
            )
            result = executor.execute_agent(mock_agent, task)
        
        # Assert
        assert result.output == expected_result
        assert result.success is True
        mock_popen.assert_called_once()
```

### Test Documentation

```python
def test_complex_scenario():
    """Test agent execution with timeout and retry.
    
    This test verifies that:
    1. Agent execution respects timeout
    2. Retry logic works correctly
    3. Proper errors are raised after max retries
    """
    ...
```

## Async Code

### Async/Await Usage

```python
import asyncio
from typing import List

async def process_agents_async(agents: List[Agent]) -> List[Result]:
    """Process multiple agents concurrently.
    
    Args:
        agents: List of agents to process.
        
    Returns:
        List of results from each agent.
    """
    tasks = [
        process_single_agent(agent)
        for agent in agents
    ]
    
    # Use gather for concurrent execution
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Agent {agents[i].name} failed: {result}")
            processed_results.append(ErrorResult(str(result)))
        else:
            processed_results.append(result)
    
    return processed_results
```

### Async Context Managers

```python
class AsyncOrchestrator:
    """Async orchestrator with context manager support."""
    
    async def __aenter__(self):
        """Enter async context."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        await self.stop()
        if exc_type:
            logger.error(f"Error in async context: {exc_val}")
        return False
```

## Performance

### Optimization Guidelines

```python
# Prefer list comprehensions for simple transformations
# Good
filtered_agents = [a for a in agents if a.active]

# Less efficient
filtered_agents = []
for a in agents:
    if a.active:
        filtered_agents.append(a)

# Use generators for large datasets
def process_large_file(filename: str):
    """Process large file line by line."""
    with open(filename) as f:
        for line in f:  # Generator, doesn't load entire file
            yield process_line(line)

# Cache expensive operations
from functools import lru_cache

@lru_cache(maxsize=128)
def get_agent_capabilities(agent_name: str) -> List[str]:
    """Get agent capabilities with caching."""
    # Expensive operation cached
    return load_agent_metadata(agent_name)['capabilities']
```

## Security

### Input Validation

```python
import re
from pathlib import Path

def validate_agent_name(name: str) -> str:
    """Validate and sanitize agent name.
    
    Args:
        name: Raw agent name input.
        
    Returns:
        Sanitized agent name.
        
    Raises:
        ValueError: If name is invalid.
    """
    # Check length
    if not 1 <= len(name) <= 50:
        raise ValueError("Agent name must be 1-50 characters")
    
    # Check characters (alphanumeric and underscore only)
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        raise ValueError("Agent name must be alphanumeric")
    
    return name.lower()

def validate_file_path(path: str) -> Path:
    """Validate file path for safety."""
    path_obj = Path(path).resolve()
    
    # Prevent path traversal
    if ".." in path_obj.parts:
        raise ValueError("Path traversal not allowed")
    
    # Check if within allowed directory
    allowed_dir = Path.cwd()
    if not path_obj.is_relative_to(allowed_dir):
        raise ValueError(f"Path must be within {allowed_dir}")
    
    return path_obj
```

### Secrets Handling

```python
import os
from typing import Optional

def get_api_key(key_name: str) -> Optional[str]:
    """Get API key from environment.
    
    Never hardcode secrets in code.
    """
    key = os.getenv(key_name)
    
    if not key:
        logger.warning(f"API key {key_name} not found in environment")
        return None
    
    # Never log the actual key
    logger.debug(f"Using API key {key_name} (length: {len(key)})")
    
    return key
```

## Comments

### When to Comment

```python
# Good: Explain WHY, not WHAT
# Use exponential backoff to avoid overwhelming the service
delay = min(2 ** attempt, 60)

# Bad: Obvious comment
# Increment counter by 1
counter += 1

# Good: Complex algorithm explanation
# We use a two-phase approach here:
# 1. First pass: collect all delegations
# 2. Second pass: execute in dependency order
# This prevents deadlocks when agents depend on each other
```

### TODO Comments

```python
# TODO(username): Brief description of what needs to be done
# TODO(john): Add retry logic for network failures

# FIXME(username): Something that needs fixing
# FIXME(jane): Handle Unicode in agent names

# NOTE: Important information
# NOTE: This function is called from multiple threads
```

## Git Commit Messages

### Commit Message Format

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `chore`: Changes to build process or auxiliary tools

### Examples

```bash
# Feature
feat(orchestrator): add subprocess timeout configuration

Add configurable timeout for subprocess orchestrator to prevent
hanging processes. Default timeout is 300 seconds.

Closes #123

# Bug fix
fix(agents): handle Unicode in agent names

Agent names with Unicode characters were causing encoding errors.
Added proper UTF-8 handling throughout the agent system.

Fixes #456

# Documentation
docs(api): update orchestrator API documentation

Added missing parameters and examples for the orchestrator API.
Clarified timeout behavior and error handling.
```

## Code Review Checklist

### Before Submitting PR

- [ ] Code follows style guidelines (run `black` and `flake8`)
- [ ] All functions have type hints
- [ ] Public APIs have docstrings
- [ ] Tests added/updated for changes
- [ ] No hardcoded values or secrets
- [ ] Error handling is appropriate
- [ ] Logging added for debugging
- [ ] Performance impact considered
- [ ] Security implications reviewed
- [ ] Documentation updated

### Reviewing Code

- [ ] Logic is correct and efficient
- [ ] Code is readable and maintainable  
- [ ] Tests adequately cover changes
- [ ] No obvious security issues
- [ ] Follows project conventions
- [ ] Comments explain complex parts
- [ ] Error messages are helpful
- [ ] Changes are focused and atomic

## Next Steps

1. Set up [pre-commit hooks](setup.md#install-pre-commit-hooks)
2. Review [testing guidelines](testing.md)
3. Learn [debugging techniques](debugging.md)
4. Read [architecture documentation](../01-architecture/)