# Claude MPM Quality Assurance Guide

This document provides guidelines for testing claude-mpm to ensure quality and stability, especially after significant changes.

## Overview

Quality assurance for claude-mpm involves multiple levels of testing:
1. Unit tests - Test individual components
2. Integration tests - Test component interactions
3. End-to-end (E2E) tests - Test complete workflows
4. Manual testing - Verify user experience

## When to Run Tests

**Run the full test suite after:**
- Major feature additions or modifications
- Changes to core components (orchestrators, CLI, agents)
- Updates to the Claude launcher or subprocess handling
- Modifications to the framework loading system
- Before creating a new release

## Test Suite Components

### 1. Unit Tests

Located in `/tests/test_*.py` files (excluding `test_e2e.py`).

**Run unit tests:**
```bash
pytest tests/ -v --ignore=tests/test_e2e.py
```

### 2. End-to-End Tests

Located in `/tests/test_e2e.py`.

**Run E2E tests:**
```bash
./scripts/run_e2e_tests.sh
```

Or directly:
```bash
pytest tests/test_e2e.py -v
```

### 3. Full Test Suite

**Run all tests:**
```bash
./scripts/run_all_tests.sh
```

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
   - Subprocess orchestrator mode

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

- [ ] Unit tests pass: `pytest tests/ -v --ignore=tests/test_e2e.py`
- [ ] E2E tests pass: `./scripts/run_e2e_tests.sh`
- [ ] Interactive mode starts: `./claude-mpm` (then type `exit`)
- [ ] Non-interactive works: `./claude-mpm run -i "What is 2+2?" --non-interactive`
- [ ] Version shows: `./claude-mpm --version`
- [ ] No import errors in logs

## Testing Specific Components

### Testing Orchestrators

When modifying orchestrators:
```bash
# Test subprocess orchestrator
./claude-mpm run --subprocess -i "test prompt" --non-interactive

# Test system prompt orchestrator (default)
./claude-mpm run -i "test prompt" --non-interactive
```

### Testing Hook System

```bash
# Should show "Hook service started"
./claude-mpm run -i "test" --non-interactive 2>&1 | grep -i hook
```

### Testing Agent System

```bash
# Verify agent registry
python -c "from claude_mpm.core.agent_registry import AgentRegistryAdapter; a = AgentRegistryAdapter(); print('OK')"
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
1. Check port 8080-8099 availability
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

### Scenario 3: Subprocess Orchestration
```bash
# Test delegation detection
./claude-mpm run --subprocess -i "Create a TODO list for building a web app" --non-interactive
```

## Performance Testing

For performance regression testing:
```bash
# Time a simple command
time ./claude-mpm run -i "What is 2+2?" --non-interactive

# Check startup time
time ./claude-mpm --version
```

Expected performance:
- Version command: < 3 seconds
- Simple prompt: < 10 seconds
- Interactive startup: < 5 seconds

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

3. **Test all orchestrators**
   - Default (system prompt)
   - Subprocess
   - Interactive subprocess

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