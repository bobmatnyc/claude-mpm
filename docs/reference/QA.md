# Testing & QA Guide

Complete guide to testing standards and quality assurance for Claude MPM.

## Testing Standards

- **Coverage**: 85%+ code coverage required
- **Unit Tests**: All services must have unit tests
- **Integration Tests**: Critical workflows must have integration tests
- **Fixtures**: Reusable fixtures for common scenarios

## Quick Commands

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test
pytest tests/test_specific.py

# Run quality checks
make quality

# Fix linting issues
make lint-fix
```

## Test Structure

```
tests/
├── unit/                # Unit tests
│   ├── test_agents.py
│   ├── test_services.py
│   └── test_hooks.py
├── integration/         # Integration tests
│   ├── test_workflow.py
│   └── test_mcp.py
├── fixtures/            # Test fixtures
│   ├── agents/          # Test agents
│   └── data/            # Test data
└── conftest.py          # Pytest configuration
```

## Writing Tests

### Unit Tests

```python
import pytest
from claude_mpm.services import ServiceContainer

def test_service_registration():
    """Test service registration in DI container."""
    container = ServiceContainer()
    container.register(IMyService, MyServiceImpl)

    service = container.get(IMyService)
    assert isinstance(service, MyServiceImpl)
```

### Integration Tests

```python
import pytest
from claude_mpm.agents import AgentRegistry

def test_agent_workflow():
    """Test complete agent workflow."""
    registry = AgentRegistry()
    agents = registry.discover_agents()

    assert len(agents) > 0
    assert any(a.name == "pm" for a in agents)
```

### Fixtures

```python
@pytest.fixture
def sample_agent(tmp_path):
    """Create sample agent for testing."""
    agent_file = tmp_path / "test-agent.md"
    agent_file.write_text("""---
name: test-agent
version: 1.0.0
capabilities:
  - testing
---

# Test Agent

Test agent prompt.
""")
    return agent_file
```

## Quality Tools

### Code Formatting

- **Black**: Code formatting
- **isort**: Import sorting
- **Ruff**: Fast linting

```bash
# Format code
make format

# Check formatting
make lint
```

### Type Checking

- **MyPy**: Static type checking

```bash
# Run type checking
make typecheck
```

### Linting

- **Flake8**: Style guide enforcement
- **Ruff**: Fast linting

```bash
# Run linting
make lint

# Fix auto-fixable issues
make lint-fix
```

## Pre-commit Hooks

Automated code quality checks:

```bash
# Install pre-commit hooks
make setup-pre-commit

# Run manually
pre-commit run --all-files
```

## Coverage Requirements

- **Overall**: 85%+ required
- **Services**: 90%+ required
- **Critical Paths**: 95%+ required

```bash
# Generate coverage report
make test-coverage

# View HTML report
open htmlcov/index.html
```

## Continuous Integration

GitHub Actions runs:
1. Linting and formatting checks
2. Type checking
3. Unit tests
4. Integration tests
5. Coverage reporting

## See Also

- **[Developer Guide](../developer/README.md)** - Development documentation
- **[Contributing](../developer/extending.md)** - Contribution guidelines
- **[Architecture](../developer/ARCHITECTURE.md)** - System architecture
