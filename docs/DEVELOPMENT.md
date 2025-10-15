# Claude MPM Development Guide

**Version**: 4.2.2  
**Last Updated**: September 2, 2025

Complete guide for developing with Claude MPM, including setup, workflows, quality standards, and best practices.

## Table of Contents

- [Quick Setup](#quick-setup)
- [Development Environment](#development-environment)
- [Quality Workflow](#quality-workflow)
- [Testing Strategy](#testing-strategy)
- [Service Development](#service-development)
- [CLI Development](#cli-development)
- [Performance Guidelines](#performance-guidelines)
- [Troubleshooting](#troubleshooting)

## Quick Setup

### 1. Clone and Install

```bash
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Automated environment setup (uses venv)
./scripts/claude-mpm --setup

# Or manual setup
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -e .
```

### 2. Verify Installation

```bash
# Test the installation
./scripts/claude-mpm --version

# Run quick test
make test-quick

# Run all quality checks
make quality
```

### 3. First Development Session

```bash
# Start development server
./scripts/claude-mpm run

# In another terminal, run tests in watch mode
make test-watch

# Auto-fix code formatting during development
make lint-fix
```

## Development Environment

### Environment Management

Claude MPM uses Python virtual environments (venv) for dependency management:

```bash
# venv setup (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac (Windows: venv\Scripts\activate)
pip install -e .

# Or use the automated script
./scripts/claude-mpm --help  # Creates and activates venv automatically
```

### Development Tools

Required tools and configurations:

```bash
# Install development dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Install recommended VS Code extensions
code --install-extension ms-python.python
code --install-extension ms-python.black-formatter
```

### Project Structure Guidelines

**Critical File Placement Rules:**

1. **Scripts**: ALL scripts go in `/scripts/`, NEVER in project root
2. **Tests**: ALL tests go in `/tests/`, NEVER in project root
3. **Python modules**: Always under `/src/claude_mpm/`
4. **Documentation**: Organized in `/docs/` with clear hierarchy

```
claude-mpm/
├── src/claude_mpm/           # All Python source code
├── tests/                    # All test files
├── scripts/                  # All executable scripts
├── docs/                     # Documentation
└── examples/                 # Usage examples
```

## Quality Workflow

### Daily Development Commands

**Three essential commands for quality-first development:**

#### 1. `make lint-fix` - Auto-fix Issues

```bash
make lint-fix
```

**What it does:**
- Runs Black formatter for consistent code style
- Sorts imports with isort
- Fixes auto-fixable Ruff issues
- Safe to run anytime - only fixes, never breaks code

**Use during:** Active development, before commits

#### 2. `make quality` - Complete Quality Gate  

```bash
make quality
```

**What it does:**
- Comprehensive linting (Ruff, Black, isort, Flake8, mypy)
- Structure validation and code quality checks
- Dependency analysis and security checks
- **Must pass before every commit**

**Use before:** Every commit, pull requests

#### 3. `make safe-release-build` - Release Quality

```bash
make safe-release-build
```

**What it does:**
- Complete quality gate plus build process
- Ensures releases meet all quality standards
- Required for all release builds

**Use for:** Release builds, deployment preparation

### Quality Standards

- **Code Coverage**: Minimum 85% test coverage
- **Type Checking**: All public APIs must have type hints
- **Documentation**: All public functions/classes must be documented
- **Performance**: No regression in benchmark tests
- **Security**: Pass all security scans

## Testing Strategy

### Test Organization

```
tests/
├── unit/                     # Unit tests (fast, isolated)
├── integration/              # Integration tests (services working together)
├── e2e/                      # End-to-end tests (full workflows)
├── fixtures/                 # Test data and fixtures
└── test-reports/            # Test execution reports
```

### Running Tests

```bash
# Quick unit tests (fast feedback)
make test-unit

# Integration tests
make test-integration  

# End-to-end tests
make test-e2e

# All tests
make test

# Watch mode for development
make test-watch

# Coverage report
make coverage
```

### Test Categories

#### Unit Tests
- Test individual functions/classes in isolation
- Mock external dependencies  
- Fast execution (< 1 second per test)
- High coverage of business logic

```python
def test_agent_registry_discovery():
    """Test agent discovery functionality."""
    registry = AgentRegistry()
    agents = registry.discover_agents()
    assert len(agents) > 0
    assert "engineer" in agents
```

#### Integration Tests
- Test service interactions
- Use real dependencies where practical
- Test interface compliance
- Verify data flow between components

```python
async def test_agent_deployment_integration():
    """Test agent deployment with real services."""
    deployment_service = AgentDeploymentService()
    result = deployment_service.deploy_agents(force=True)
    assert result['success'] is True
```

#### End-to-End Tests
- Test complete user workflows
- Use real CLI commands
- Verify output and side effects
- Test happy paths and error scenarios

```bash
# E2E test script
./scripts/run_e2e_tests.sh
```

### Testing Best Practices

1. **Test Structure**: Use Arrange-Act-Assert pattern
2. **Naming**: Descriptive test names explaining what is tested
3. **Independence**: Tests should not depend on each other
4. **Speed**: Unit tests should be fast, integration tests moderate
5. **Coverage**: Focus on business logic and edge cases

## Service Development

### Creating a New Service

#### 1. Define Interface

```python
# src/claude_mpm/services/core/interfaces.py
from abc import ABC, abstractmethod

class IMyService(ABC):
    @abstractmethod
    async def my_operation(self, param: str) -> bool:
        """Perform my operation."""
        pass
```

#### 2. Implement Service

```python
# src/claude_mpm/services/domain/my_service.py
from claude_mpm.services.core.interfaces import IMyService
from claude_mpm.services.core.base import BaseService

class MyService(BaseService, IMyService):
    def __init__(self, dependency: IDependency):
        super().__init__("MyService")
        self.dependency = dependency
    
    async def initialize(self) -> bool:
        """Initialize service resources."""
        try:
            # Initialize resources
            self._initialized = True
            return True
        except Exception as e:
            self.log_error(f"Initialization failed: {e}")
            return False
    
    async def my_operation(self, param: str) -> bool:
        """Implementation of my operation."""
        # Service logic here
        return True
    
    async def shutdown(self) -> None:
        """Cleanup service resources."""
        # Cleanup logic here
        await super().shutdown()
```

#### 3. Register Service

```python
# Register in service container
container.register(IMyService, MyService, singleton=True)
```

#### 4. Add Tests

```python
# tests/services/test_my_service.py
import pytest
from claude_mpm.services.domain.my_service import MyService

@pytest.mark.asyncio
async def test_my_service_operation():
    """Test my service operation."""
    service = MyService(mock_dependency)
    result = await service.my_operation("test")
    assert result is True

def test_service_implements_interface():
    """Test service implements required interface."""
    service = MyService(mock_dependency)
    assert isinstance(service, IMyService)
```

### Service Development Guidelines

1. **Domain Organization**: Place services in appropriate domain directories
2. **Interface First**: Always define interfaces before implementations
3. **Dependency Injection**: Use constructor injection for dependencies
4. **Lifecycle Management**: Implement proper initialize/shutdown methods
5. **Error Handling**: Comprehensive error handling with logging
6. **Performance**: Consider caching and async patterns

## CLI Development

### CLI Architecture

The CLI uses a modular structure for maintainability:

```
src/claude_mpm/cli/
├── __init__.py               # Main entry point
├── parser.py                 # Argument parsing
├── utils.py                  # Shared utilities
└── commands/                 # Individual commands
    ├── run.py                # Main run command
    ├── agents.py             # Agent management
    ├── info.py               # System information
    └── ui.py                 # UI launcher
```

### Adding a New Command

#### 1. Create Command Module

```python
# src/claude_mpm/cli/commands/my_command.py
import argparse
from claude_mpm.cli.utils import setup_logging

def add_my_command_parser(subparsers):
    """Add my command to CLI parser."""
    parser = subparsers.add_parser('my-command', help='My command description')
    parser.add_argument('--option', help='Command option')
    parser.set_defaults(func=handle_my_command)

def handle_my_command(args):
    """Handle my command execution."""
    setup_logging(args.verbose)
    
    # Command implementation
    print(f"Executing my command with option: {args.option}")
    
    return 0  # Success
```

#### 2. Register Command

```python
# src/claude_mpm/cli/parser.py
from claude_mpm.cli.commands.my_command import add_my_command_parser

def create_parser():
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(description='Claude MPM CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Register existing commands
    add_run_parser(subparsers)
    add_agents_parser(subparsers)
    add_my_command_parser(subparsers)  # Add new command
    
    return parser
```

#### 3. Add Tests

```python
# tests/cli/test_my_command.py
from claude_mpm.cli.commands.my_command import handle_my_command
from unittest.mock import Mock

def test_my_command():
    """Test my command functionality."""
    args = Mock(option="test")
    result = handle_my_command(args)
    assert result == 0
```

## Performance Guidelines

### Performance Optimization Patterns

#### Lazy Loading

Use lazy imports for expensive modules:

```python
from claude_mpm.core.lazy import lazy_import

# Lazy import - module loaded only when accessed
ExpensiveService = lazy_import('my.expensive.module', 'ExpensiveService')
```

#### Caching Strategy

Implement intelligent caching:

```python
from claude_mpm.services.core.cache import CacheService

class OptimizedService:
    def __init__(self):
        self.cache = CacheService.get_instance()
    
    def expensive_operation(self, key):
        """Cache expensive operations."""
        cached = self.cache.get(key)
        if cached:
            return cached
        
        result = self._compute_expensive_result(key)
        self.cache.set(key, result, ttl=300)  # 5-minute TTL
        return result
```

#### Async Patterns

Use async/await for I/O operations:

```python
class AsyncService(BaseService):
    async def process_batch(self, items):
        """Process items concurrently."""
        tasks = [self._process_item(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def _process_item(self, item):
        """Process single item asynchronously."""
        async with aiofiles.open(item.path) as f:
            content = await f.read()
            return self._analyze_content(content)
```

### Performance Monitoring

Monitor performance metrics:

```python
from claude_mpm.services.infrastructure import PerformanceMonitor

monitor = PerformanceMonitor()

# Track operation timing
with monitor.timer("expensive_operation"):
    result = expensive_operation()

# Check performance metrics
metrics = monitor.get_metrics()
print(f"Average duration: {metrics['expensive_operation']['avg']}")
```

## Troubleshooting

### Common Development Issues

#### Import Errors

**Problem**: Module not found errors

**Solution**: 
```bash
# Ensure proper installation
pip install -e .

# Check PYTHONPATH includes src/
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Verify installation
python -c "import claude_mpm; print(claude_mpm.__file__)"
```

#### Hook Service Errors

**Problem**: Socket connection errors

**Solution**:
```bash
# Check port availability
netstat -an | grep 876[0-9]

# Kill existing processes
pkill -f "socketio_server"

# Restart with different port
./scripts/claude-mpm run --port 8766
```

#### Version Management Issues

**Problem**: Version inconsistencies

**Solution**:
```bash
# Check current version
./scripts/claude-mpm --version

# Rebuild version info  
python scripts/manage_version.py bump patch

# Verify version consistency
python -c "import claude_mpm; print(claude_mpm.__version__)"
```

#### Agent Deployment Issues

**Problem**: Agents not deploying correctly

**Solution**:
```bash
# Force redeploy all agents
./scripts/claude-mpm agents deploy --force

# Check agent validation
./scripts/claude-mpm agents validate

# Clear agent cache
rm -rf .claude-mpm/cache/
```

### Performance Issues

#### Slow Startup

**Diagnosis**:
```bash
# Profile startup time
python -m cProfile -s time -m claude_mpm run --help

# Check lazy loading
grep -r "lazy_import" src/
```

**Solutions**:
- Implement lazy loading for expensive imports
- Check cache warming strategies
- Optimize service initialization order

#### Memory Usage

**Diagnosis**:
```bash
# Monitor memory usage  
python -m memory_profiler scripts/claude-mpm

# Check for memory leaks
valgrind python -m claude_mpm run
```

**Solutions**:
- Implement proper resource cleanup
- Use weak references where appropriate
- Monitor service memory consumption

### Development Tools

#### Debugging

```bash
# Debug mode with verbose logging
./scripts/claude-mpm run --debug --verbose

# Python debugger
python -m pdb -m claude_mpm run

# Remote debugging with debugpy
python -m debugpy --listen 5678 -m claude_mpm run
```

#### Profiling

```bash
# CPU profiling
python -m cProfile -o profile.stats -m claude_mpm run
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('time').print_stats(20)"

# Memory profiling
python -m memory_profiler scripts/claude-mpm run
```

#### Code Analysis

```bash
# Static analysis with pylint
pylint src/claude_mpm/

# Type checking with mypy
mypy src/claude_mpm/

# Security analysis with bandit
bandit -r src/claude_mpm/
```

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and design
- [AGENTS.md](AGENTS.md) - Agent development guide
- [API.md](API.md) - API reference
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Extended troubleshooting guide