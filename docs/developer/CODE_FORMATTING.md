# Code Formatting Guide

Complete guide to code quality and formatting standards for Claude MPM.

## Quick Commands

```bash
# Complete development setup
make dev-complete

# Format code automatically
make format

# Fix linting issues
make lint-fix

# Run all quality checks
make quality

# Before committing
make pre-commit
```

## Formatting Tools

### Black - Code Formatting

**Standard Python code formatter** for consistent style:

```bash
# Format all code
black src/ tests/

# Check without modifying
black --check src/ tests/

# Via make
make format
```

**Configuration** (pyproject.toml):
```toml
[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311']
include = '\.pyi?$'
```

### isort - Import Sorting

**Automatically sort and organize imports**:

```bash
# Sort imports
isort src/ tests/

# Check without modifying
isort --check src/ tests/

# Via make
make format
```

**Configuration** (pyproject.toml):
```toml
[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
```

### Ruff - Fast Linting

**High-performance linter** replacing flake8:

```bash
# Run linting
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Via make
make lint
make lint-fix
```

**Configuration** (.ruff.toml):
```toml
[tool.ruff]
line-length = 100
target-version = "py38"
select = ["E", "F", "I", "N", "W"]
```

## Type Checking

### MyPy - Static Type Checking

**Enforce type hints** for better code quality:

```bash
# Run type checking
mypy src/

# Strict mode
mypy --strict src/

# Via make
make typecheck
```

**Configuration** (.mypy.ini):
```ini
[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

## Pre-commit Hooks

**Automated quality checks** before every commit:

### Setup

```bash
# Install pre-commit hooks
make setup-pre-commit

# Or manually
pip install pre-commit
pre-commit install
```

### Configuration

**.pre-commit-config.yaml**:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.270
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### Usage

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files (automatic on commit)
git commit

# Skip hooks (not recommended)
git commit --no-verify
```

## Code Style Guidelines

### Naming Conventions

**Files and Modules:**
- Use snake_case: `agent_registry.py`
- Private modules: `_internal.py`
- Test modules: `test_agent_registry.py`

**Classes:**
- Use PascalCase: `AgentRegistry`
- Interfaces: Prefix with `I`: `IAgentRegistry`
- Abstract classes: Prefix with `Abstract`: `AbstractService`

**Functions and Methods:**
- Use snake_case: `discover_agents()`
- Private: Prefix with `_`: `_load_config()`
- Test functions: `test_agent_discovery()`

**Constants:**
- Use UPPER_SNAKE_CASE: `MAX_RETRIES`
- Module-level: All caps
- Class-level: All caps

**Variables:**
- Use snake_case: `agent_name`
- Boolean: Prefix with `is_`, `has_`, `can_`: `is_enabled`
- Private: Prefix with `_`: `_cache`

### Type Hints

**Required for all public APIs:**

```python
from typing import List, Optional, Dict, Any

def discover_agents(path: Path) -> List[Agent]:
    """Discover agents in directory."""
    pass

def get_agent(name: str) -> Optional[Agent]:
    """Get agent by name."""
    pass

def process_config(config: Dict[str, Any]) -> None:
    """Process configuration."""
    pass
```

### Docstrings

**Required for all public APIs** (Google style):

```python
def discover_agents(path: Path, filter_func: Optional[Callable] = None) -> List[Agent]:
    """Discover all agents in directory.

    Args:
        path: Directory path to search
        filter_func: Optional filter function

    Returns:
        List of discovered agents

    Raises:
        ValueError: If path doesn't exist
        PermissionError: If path not readable

    Examples:
        >>> agents = discover_agents(Path("/path/to/agents"))
        >>> len(agents)
        15
    """
    pass
```

### Import Organization

**Order** (enforced by isort):
1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import os
from pathlib import Path
from typing import List, Optional

# Third-party
import click
from rich.console import Console

# Local
from claude_mpm.agents import AgentRegistry
from claude_mpm.services import ServiceContainer
```

## Quality Checks

### Before Every Commit

```bash
# Run all quality checks
make quality

# Or step by step:
make format      # Format code
make lint        # Check linting
make typecheck   # Type checking
make test        # Run tests
```

### Continuous Integration

GitHub Actions runs:
1. Code formatting check (Black, isort)
2. Linting (Ruff)
3. Type checking (MyPy)
4. Tests with coverage
5. Documentation build

## Development Workflow

### 1. Setup Development Environment

```bash
# Complete setup
make dev-complete

# Or step by step:
make setup-dev          # Install in dev mode
make setup-pre-commit   # Install hooks
```

### 2. Make Changes

- Follow naming conventions
- Add type hints
- Write docstrings
- Update tests

### 3. Format and Lint

```bash
# Auto-format and fix
make lint-fix

# Check everything
make quality
```

### 4. Commit

```bash
# Pre-commit hooks run automatically
git add .
git commit -m "feat: add feature"
```

## Editor Integration

### VS Code

**.vscode/settings.json**:
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm

1. Settings → Tools → Black → Enable on save
2. Settings → Tools → isort → Enable on save
3. Settings → Editor → Inspections → Python → Type checker: MyPy

### Vim/Neovim

With ALE or coc.nvim:
```vim
let g:ale_fixers = {
\   'python': ['black', 'isort', 'ruff'],
\}
let g:ale_fix_on_save = 1
```

## Makefile Targets

```bash
# Development setup
make setup-dev          # Install in dev mode
make setup-pre-commit   # Setup pre-commit hooks
make dev-complete       # Complete setup

# Code quality
make format             # Format code (Black, isort)
make lint               # Check linting (Ruff)
make lint-fix           # Fix linting issues
make typecheck          # Type checking (MyPy)
make quality            # All quality checks

# Testing
make test               # Run tests
make test-coverage      # Tests with coverage
make test-verbose       # Verbose test output

# Release
make safe-release-build # Quality gate + build
```

## Troubleshooting

### Pre-commit Hooks Fail

```bash
# Update hooks
pre-commit autoupdate

# Clear cache
pre-commit clean

# Reinstall
pre-commit uninstall
pre-commit install
```

### Type Checking Errors

```bash
# Install type stubs
pip install types-all

# Check specific file
mypy path/to/file.py

# Ignore line
# type: ignore
```

### Formatting Conflicts

```bash
# Black and isort conflict
# Black takes precedence
make format

# Manual resolution
black src/
isort --profile black src/
```

## See Also

- **[Developer Guide](README.md)** - Development documentation
- **[Contributing Guide](../reference/QA.md)** - Contribution guidelines
- **[Architecture](ARCHITECTURE.md)** - System architecture
- **[API Reference](api-reference.md)** - API documentation

---

**For CONTRIBUTING.md guidelines**: See [../CONTRIBUTING.md](../../CONTRIBUTING.md)
