# Claude MPM Quality Assurance Guide

This document provides comprehensive guidelines for testing claude-mpm to ensure quality and stability, especially after the TSK-0053 service layer refactoring.

## Overview

Quality assurance for claude-mpm involves multiple levels of testing following the modern service-oriented architecture:

1. **Unit tests** - Test individual services and components in isolation
2. **Integration tests** - Test service interactions and interfaces
3. **End-to-end (E2E) tests** - Test complete workflows and user scenarios
4. **Performance tests** - Verify caching, lazy loading, and optimization
5. **Security tests** - Validate input validation and security measures
6. **Manual testing** - Verify user experience and edge cases

## When to Run Tests

**Run the full test suite after:**
- Major feature additions or modifications
- Changes to core components (CLI, agents, services)
- Service layer or interface modifications
- Updates to the framework or agent system
- Modifications to dependency injection or service container
- Performance optimization changes
- Security framework updates
- Before creating a new release

## Architecture-Specific Testing

### Service Layer Testing
The new service-oriented architecture requires specific testing approaches:

- **Interface Testing**: Verify all services implement their contracts correctly
- **Dependency Injection Testing**: Ensure service resolution works properly
- **Service Lifecycle Testing**: Test initialization, operation, and shutdown
- **Cache Testing**: Verify caching behavior and invalidation
- **Security Testing**: Validate input validation and sanitization

## Test Suite Components

### 1. Unit Tests

Located in `/tests/unit/` and `/tests/test_*.py` files.

**Test Categories:**
- **Service Tests**: Individual service functionality
- **Interface Tests**: Interface contract compliance
- **Utility Tests**: Helper functions and utilities
- **Validation Tests**: Input validation and security

**Run unit tests:**
```bash
# All unit tests
pytest tests/unit/ -v

# Specific service tests
pytest tests/unit/services/ -v

# Legacy unit tests
pytest tests/ -v --ignore=tests/test_e2e.py --ignore=tests/integration/ --ignore=tests/performance/
```

### 2. Integration Tests

Located in `/tests/integration/`.

**Test Categories:**
- **Service Integration**: Inter-service communication
- **Database Integration**: Persistence layer testing
- **API Integration**: External service integration
- **Memory System Integration**: Agent memory testing

**Run integration tests:**
```bash
pytest tests/integration/ -v
```

### 3. End-to-End Tests

Located in `/tests/e2e/` and `/tests/test_e2e.py`.

**Run E2E tests:**
```bash
./scripts/run_e2e_tests.sh
```

Or directly:
```bash
pytest tests/e2e/ tests/test_e2e.py -v
```

### 4. Performance Tests

Located in `/tests/performance/`.

**Test Categories:**
- **Caching Performance**: Cache hit rates and response times
- **Lazy Loading**: Startup time optimization
- **Memory Optimization**: Memory usage and cleanup
- **Concurrent Operations**: Multi-threading and async performance

**Run performance tests:**
```bash
pytest tests/performance/ -v --benchmark-only
```

### 5. Security Tests

Located in `/tests/security/`.

**Test Categories:**
- **Input Validation**: Malicious input handling
- **Path Traversal**: File system security
- **Authentication**: Access control testing
- **Configuration Security**: Secure configuration handling

**Run security tests:**
```bash
pytest tests/security/ -v
```

### 6. Full Test Suite

**Run all tests:**
```bash
./scripts/run_all_tests.sh
```

**Run with coverage:**
```bash
pytest --cov=src/claude_mpm --cov-report=html --cov-report=term
```

### Script Organization and Compatibility

Scripts are organized in subdirectories under `/scripts/` for better organization:
- `scripts/development/` - Development and debugging tools
- `scripts/monitoring/` - Runtime monitoring utilities  
- `scripts/utilities/` - MCP and configuration tools
- `scripts/verification/` - System verification scripts

**Backward Compatibility**: Symbolic links maintain compatibility with existing documentation and workflows:
- `./scripts/run_e2e_tests.sh` → `./scripts/development/run_e2e_tests.sh`
- `./scripts/run_all_tests.sh` → `./scripts/development/run_all_tests.sh`
- `./scripts/run_lint.sh` → `./scripts/development/run_lint.sh`

Both the symlinked paths and the actual subdirectory paths work correctly.

## E2E Test Coverage

The E2E tests verify:

1. **Basic Commands**
   - Version display (`--version`)
   - Help information (`--help`)
   - Info command

2. **Non-Interactive Mode**
   - Simple prompts with `-i` flag
   - Reading from stdin
   - Various prompt types (math, facts, etc.)
   - Different execution modes

3. **Interactive Mode**
   - Startup without errors
   - Clean exit
   - Basic interaction flow

4. **Service Integration**
   - Hook service startup
   - Framework loading
   - Error handling

## Quick Test Checklist

Before committing significant changes, ensure:

### Core Functionality
- [ ] Unit tests pass: `pytest tests/unit/ -v`
- [ ] Integration tests pass: `pytest tests/integration/ -v`
- [ ] E2E tests pass: `./scripts/run_e2e_tests.sh`
- [ ] Performance tests pass: `pytest tests/performance/ -v`
- [ ] Security tests pass: `pytest tests/security/ -v`

### Service Architecture
- [ ] Service interfaces work: Test dependency injection resolution
- [ ] Lazy imports work: Verify backward compatibility
- [ ] Cache performance: Check cache hit rates > 90%
- [ ] Memory optimization: Verify memory usage within limits

### Basic Operations
- [ ] Interactive mode starts: `./claude-mpm` (then type `exit`)
- [ ] Non-interactive works: `./claude-mpm run -i "What is 2+2?" --non-interactive`
- [ ] Version shows: `./claude-mpm --version`
- [ ] Agent deployment: `./claude-mpm agents deploy`
- [ ] No import errors in logs

### Service-Specific Tests
- [ ] Service container resolves all interfaces
- [ ] Agent registry discovers agents correctly
- [ ] Memory services save/load properly
- [ ] Communication services start without errors

## Testing Specific Components

### Testing Service Layer

#### Service Container Testing
```bash
# Test service registration and resolution
python -c "
from claude_mpm.services.core import ServiceContainer
from claude_mpm.services.core.interfaces import IAgentRegistry
container = ServiceContainer()
print('Service container OK')
"
```

#### Interface Testing
```bash
# Test that services implement their interfaces
python -c "
from claude_mpm.services.agent.registry import AgentRegistry
from claude_mpm.services.core.interfaces import IAgentRegistry
registry = AgentRegistry()
assert isinstance(registry, IAgentRegistry)
print('Interface compliance OK')
"
```

#### Dependency Injection Testing
```bash
# Test service resolution
python -c "
from claude_mpm.services import AgentDeploymentService
service = AgentDeploymentService()
print('Service resolution OK')
"
```

### Testing Performance Optimizations

#### Cache Testing
```bash
# Test cache performance
python -c "
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache
cache = SharedPromptCache.get_instance()
cache.set('test', 'value')
assert cache.get('test') == 'value'
print('Cache functionality OK')
"
```

#### Lazy Loading Testing
```bash
# Test lazy imports
python -c "
import time
start = time.time()
from claude_mpm.services import AgentDeploymentService
load_time = time.time() - start
print(f'Lazy import time: {load_time:.3f}s')
assert load_time < 0.1, 'Import too slow'
"
```

### Testing Execution Modes

When modifying execution logic:
```bash
# Test non-interactive mode
./claude-mpm run -i "test prompt" --non-interactive

# Test interactive mode
./claude-mpm
```

### Testing Hook System

```bash
# Should show "Hook service started"
./claude-mpm run -i "test" --non-interactive 2>&1 | grep -i hook
```

### Testing Agent System

```bash
# Verify new agent registry
python -c "
from claude_mpm.services.agent.registry import AgentRegistry
import asyncio
async def test():
    registry = AgentRegistry()
    agents = await registry.discover_agents()
    print(f'Found {len(agents)} agents')
asyncio.run(test())
"

# Test agent deployment
python -c "
from claude_mpm.services.agent.deployment import AgentDeploymentService
deployment = AgentDeploymentService()
print('Agent deployment service OK')
"
```

### Testing Tree-Sitter Integration

```bash
# Verify tree-sitter installation
python -c "import tree_sitter; print(f'tree-sitter version: {tree_sitter.__version__}')"

# Verify language pack installation
python -c "import tree_sitter_language_pack; print('Language pack OK')"

# Test TreeSitterAnalyzer
python -c "
from claude_mpm.services.agent_modification_tracker.tree_sitter_analyzer import TreeSitterAnalyzer
analyzer = TreeSitterAnalyzer()
print(f'Supported languages: {len(analyzer.get_supported_languages())}')
"
```

### Testing Claude Launcher

```bash
# Test launcher directly
python -c "
from claude_mpm.core import ClaudeLauncher
launcher = ClaudeLauncher()
print(f'Claude found at: {launcher.claude_path}')
"
```

## Common Issues and Solutions

### Import Errors

If you see `ModuleNotFoundError`:
1. Check PYTHONPATH includes `src/`
2. Ensure virtual environment is activated
3. Run `pip install -e .` in project root

### Hook Service Errors

If hook service fails to start:
1. Check port 8765-8785 availability
2. Review hook service logs in `~/.claude-mpm/logs/`
3. Try with `--no-hooks` flag

### Interactive Mode Issues

If interactive mode has display issues:
1. Check terminal compatibility
2. Try different terminal emulators
3. Test with simplified prompts

### Tree-Sitter Issues

If tree-sitter functionality fails:
1. Verify installation: `pip show tree-sitter tree-sitter-language-pack`
2. Check version compatibility (requires tree-sitter>=0.21.0)
3. For import errors, reinstall: `pip install --force-reinstall tree-sitter tree-sitter-language-pack`
4. Language support issues: Ensure tree-sitter-language-pack>=0.20.0 is installed

## Manual Testing Scenarios

### Scenario 1: Basic Workflow
```bash
# 1. Start interactive mode
./claude-mpm

# 2. Ask a simple question
What is the capital of France?

# 3. Exit
exit
```

### Scenario 2: Non-Interactive Workflow
```bash
# Simple math
./claude-mpm run -i "What is 15 * 15?" --non-interactive

# From file
echo "Explain Python decorators" > prompt.txt
./claude-mpm run -i prompt.txt --non-interactive
```

### Scenario 3: Agent Delegation
```bash
# Test delegation to Research Agent
./claude-mpm run -i "Research best practices for REST API design" --non-interactive
```

## Performance Testing

### Performance Regression Testing
```bash
# Time a simple command
time ./claude-mpm run -i "What is 2+2?" --non-interactive

# Check startup time
time ./claude-mpm --version

# Check agent deployment time
time ./claude-mpm agents deploy --force
```

### Cache Performance Testing
```bash
# Test cache hit rates
python -c "
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache
cache = SharedPromptCache.get_instance()
# Warm cache
for i in range(100):
    cache.set(f'test_{i}', f'value_{i}')
# Test access
import time
start = time.time()
for i in range(100):
    cache.get(f'test_{i}')
duration = time.time() - start
print(f'Cache access time: {duration:.3f}s for 100 items')
metrics = cache.get_metrics()
print(f'Cache hit rate: {metrics.get(\"hit_rate\", 0):.2%}')
"
```

### Memory Usage Testing
```bash
# Monitor memory usage during operations
python -c "
import psutil
import os
from claude_mpm.services.agent.registry import AgentRegistry

process = psutil.Process(os.getpid())
start_memory = process.memory_info().rss / 1024 / 1024  # MB

# Perform operations
registry = AgentRegistry()
# ... more operations

end_memory = process.memory_info().rss / 1024 / 1024  # MB
print(f'Memory usage: {start_memory:.1f}MB -> {end_memory:.1f}MB')
print(f'Memory delta: {end_memory - start_memory:.1f}MB')
"
```

### Expected Performance (Post-Refactoring)
- **Version command**: < 1 second (improved from 3s)
- **Simple prompt**: < 5 seconds (improved from 10s)
- **Interactive startup**: < 2 seconds (improved from 5s)
- **Agent deployment**: < 2 seconds for 5 agents
- **Cache hit rate**: > 90% for frequently accessed data
- **Memory usage**: < 100MB baseline, < 500MB under load

## Release Testing

Before creating a release:

1. **Run full test suite**
   ```bash
   ./scripts/run_all_tests.sh
   ```

2. **Test installation**
   ```bash
   pip install -e .
   claude-mpm --version
   ```

3. **Test all execution modes**
   - Interactive (default)
   - Non-interactive
   - Debug mode

4. **Verify documentation**
   - README.md examples work
   - STRUCTURE.md is current
   - This QA.md is up to date

## Continuous Improvement

- Add tests for new features
- Update E2E tests for new commands
- Document any manual test scenarios
- Report flaky tests for investigation

## Test Development Guidelines

When adding new tests:
1. Use descriptive test names
2. Include timeout parameters
3. Clean up resources (processes, files)
4. Use appropriate assertions with clear messages
5. Consider parametrized tests for variations

Example:
```python
def test_feature_description(self):
    """Test that feature X works correctly with input Y."""
    result = run_command(["claude-mpm", "command"])
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "expected" in result.stdout, f"Missing expected output: {result.stdout}"
```